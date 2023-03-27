from abc import abstractmethod
from dataclasses import dataclass
import logging
from typing import cast, Callable, Dict, Final, Generic, List, MutableMapping, Optional, Protocol, Set, Tuple, TypeVar, Union

LOG: Final = logging.getLogger(__name__)


class ComparableProtocol(Protocol):
    @abstractmethod
    def __le__(self: "Comparable", other: "Comparable") -> bool:
        ...  # pragma: nocover


Comparable = TypeVar("Comparable", bound=ComparableProtocol)
ResultType = TypeVar("ResultType")
RuleId = TypeVar("RuleId")
PosType = TypeVar("PosType", bound=ComparableProtocol)


@dataclass
class RecursionInfo(Generic[RuleId]):
    """Record-keeping used during resolution of recursion.

    In the paper, this is called a "head".

    Attributes:
        rule_id: ID of the rule that first created a recursion (it's both the head and tail of the cycle)
        involved: Rules involved in the recursive cycle other that the head/tail rule.
        eval_set: Rules which are still due for a cache bypass during this growth cycle.
    """

    rule_id: RuleId
    involved: Set[RuleId]
    eval_set: Set[RuleId]


@dataclass
class Poison(Generic[RuleId]):
    """Cache poison entry to detect left recursion.

    In the paper, these are called "LR" and are placed onto a stack data structure representing the entire call stack.
    This turns out to be unnecessary; each potentially-recursive parser function just needs a local poison entry that
    only needs to exist while it's actually executing.

    Attributes:
        recursion_info: Active RecursionInfo, or None if no recursion in progress
    """

    recursion_info: Optional[RecursionInfo[RuleId]]


@dataclass
class MemoEntry(Generic[RuleId, PosType, ResultType]):
    result: Union[Poison[RuleId], Optional[ResultType]]
    final_pos: PosType


CacheType = MutableMapping[PosType, MemoEntry[RuleId, PosType, ResultType]]


@dataclass(frozen=True)
class ApplyResult(Generic[PosType, ResultType]):
    pos: PosType
    result: ResultType


RuleCallable = Callable[[PosType], Optional[ApplyResult[PosType, ResultType]]]


class Packrat(Generic[RuleId, PosType]):
    def __init__(self) -> None:
        self.invocation_stack: List[RuleId] = []
        self._recursions: Dict[PosType, RecursionInfo[RuleId]] = {}

    def apply(
        self,
        rule_callable: RuleCallable[PosType,
                                    ResultType],
        rule_id: RuleId,
        rule_cache: CacheType[PosType,
                              RuleId,
                              ResultType],
        pos: PosType
    ) -> Optional[ApplyResult[PosType,
                              ResultType]]:
        """Apply a parser rule with memoization and left-recursion support.
        """
        LOG.debug("apply_rule %d at %s", rule_id, pos)
        start_pos = pos
        memo: Optional[MemoEntry[RuleId,
                                 PosType,
                                 ResultType]] = self._recall(rule_callable,
                                                             rule_id,
                                                             rule_cache,
                                                             start_pos)
        LOG.debug("apply_rule memo %s", memo)
        if memo is not None:
            if isinstance(memo.result, Poison):
                # We hit a cache poison that a previous invocation put there for us.
                LOG.debug("apply_rule %d", rule_id)
                assert memo.final_pos == start_pos
                memo.result = cast(Poison[RuleId], memo.result)
                self._setup_recursion(rule_id, memo.result)
                LOG.debug("apply_rule %d", rule_id)
                # By failing here at the point of recursion, one of the parsers in the cycle will try an alternative to
                # generate a seed parse.
                return None
            # Nominal case: Use cached result and pos
            LOG.debug("apply_rule %d result %s", rule_id, memo)
            return ApplyResult(memo.final_pos, memo.result) if memo.result is not None else None

        # No cache yet; poison the cache and run the parser function
        poison: Poison[RuleId] = Poison(recursion_info=None)
        memo = MemoEntry(result=poison, final_pos=start_pos)
        rule_cache[start_pos] = memo

        self.invocation_stack.append(rule_id)
        LOG.debug("apply_rule %d stack %s", rule_id, self.invocation_stack)
        call_result = rule_callable(start_pos)
        LOG.debug("apply_rule %d result %s", rule_id, call_result)
        popped = self.invocation_stack.pop()
        assert popped == rule_id
        assert memo.result is poison

        new_pos: PosType
        if call_result is not None:
            new_pos, result = call_result.pos, call_result.result
        else:
            new_pos = start_pos
            result = None

        memo.final_pos = new_pos
        if poison.recursion_info is None:
            # Nominal case (no recursion)
            memo.result = result
            LOG.debug("apply_rule %d returning %s at %d", rule_id, result, new_pos)
            return ApplyResult(new_pos, result) if result is not None else None

        # There was a recursion into this rule
        #
        # The original paper had an overly complex routine here (LR-ANSWER) which was both unnecessary and buggy.  This
        # is substantially simpler.

        # At this point, we know that we were the head/tail of the recursive cycle
        assert poison.recursion_info.rule_id == rule_id

        memo.result = result
        if result is None:
            # Did not find a seed parse, so there's nothing to grow
            return None

        LOG.debug("apply_rule %d poison %s", rule_id, poison)
        grow_result = self._grow_seed(rule_callable, start_pos, memo, poison.recursion_info)
        LOG.debug("apply_rule %d memo %s poison %s", rule_id, memo, poison)
        return grow_result

    def _recall(
        self,
        rule_callable: RuleCallable[PosType,
                                    ResultType],
        rule_id: RuleId,
        rule_cache: CacheType[PosType,
                              RuleId,
                              ResultType],
        start_pos: PosType
    ) -> Optional[MemoEntry[RuleId,
                            PosType,
                            ResultType]]:
        """Retrieve cache entries with seed-growing support.

        In the nominal case (no growth cycle in progress), this just returns a cache entry if one exists, or else None.

        When a growth cycle is active (as indicated by an entry in self._recursions), this method implements the
        cache-bypass logic required to grow seeds. On each growth cycle, each rule involved in the recursion will be
        re-evaluated with cache bypass at most once (and that result will be cached); subsequent invocations of the rule
        will use the cached value.

        """
        memo = rule_cache.get(start_pos)
        recursion = self._recursions.get(start_pos)
        if recursion is None:
            # Nominal case
            return memo

        if memo is None and rule_id is not recursion.rule_id and rule_id not in recursion.involved:
            # This case is part of the paper but I don't understand why and I'm unable to create a test case
            # that exercises this code path.  It's better to fail than to execute untested, poorly understood code.
            #
            # FWIW, the paper's algorithm would return a failure MemoEntry here (with result=None).
            raise NotImplementedError("Untested corner case; see source code for more information.")  # pragma: nocover

        # A growth cycle is active and the original recursion involves this rule; therefore we know there must be a
        # cache entry.
        assert memo is not None

        if rule_id in recursion.eval_set:
            # This rule hasn't executed on this growth cycle yet; bypass cache
            recursion.eval_set.remove(rule_id)
            call_result = rule_callable(start_pos)
            if call_result:
                memo.result = call_result.result
                memo.final_pos = call_result.pos
            else:
                memo.result = None
                memo.final_pos = start_pos

        return memo

    def _setup_recursion(self, rule_id: RuleId, poison: Poison[RuleId]) -> None:
        """Initialize the left-recursion bookkeeping for a new recursion.

        Note: In the journal paper, this is called "SETUP-LR".  This executes once for each recursion, only at the time
        the recursion is detected.  It does not re-execute on each growth cycle.
        """
        LOG.debug("setup_recursion %d poison %s", rule_id, poison)
        assert poison.recursion_info is None
        poison.recursion_info = RecursionInfo(rule_id=rule_id, involved=set(), eval_set=set())
        LOG.debug("setup_recursion %d poison %s", rule_id, poison)
        LOG.debug("setup_recursion stack %s", self.invocation_stack)
        assert self.invocation_stack
        # Walk the stack backward to create list of involved rules
        idx = len(self.invocation_stack) - 1
        while self.invocation_stack[idx] != rule_id:
            poison.recursion_info.involved.add(self.invocation_stack[idx])
            idx -= 1
            assert idx >= 0
        LOG.debug("setup_recursion %d poison %s", rule_id, poison)

    def _grow_seed(
        self,
        rule_callable: RuleCallable[PosType,
                                    ResultType],
        start_pos: PosType,
        memo: MemoEntry[RuleId,
                        PosType,
                        ResultType],
        recursion: RecursionInfo[RuleId],
    ) -> ApplyResult[PosType,
                     ResultType]:
        """Grow a recursive seed until it stops growing.

        In the paper, this is called "GROW-LR".

        Returns: the longest parse result found
        """
        self._recursions[start_pos] = recursion
        while True:
            LOG.debug("grow_seed @%d %s", start_pos, recursion)
            recursion.eval_set = set(recursion.involved)
            call_result = rule_callable(start_pos)
            LOG.debug("grow_seed %s", call_result)
            new_pos, result = (call_result.pos, call_result.result) if call_result else (start_pos, None)
            if result is None or new_pos <= memo.final_pos:
                LOG.debug("grow_seed done %s %s", new_pos, memo.final_pos)
                break
            memo.result = result
            memo.final_pos = new_pos
        # Recursion done; clean up the bookkeeping
        del self._recursions[start_pos]
        assert not isinstance(memo.result, Poison)
        assert memo.result is not None
        return ApplyResult(memo.final_pos, memo.result)
