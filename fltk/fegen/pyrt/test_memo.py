"""Unit tests for memo.py"""

# ruff: noqa: S101, PLR2004

import logging
from typing import Callable, Final, Optional, Sequence, Tuple, TypeVar, Union

from fltk.fegen.pyrt import memo

LOG: Final = logging.getLogger(__name__)

ResultType = TypeVar("ResultType")


def memoize(
    rule_id: int,
    get_rule_cache: Callable[["Parser"], memo.CacheType[int, int, ResultType]],
) -> Callable[
    [Callable[["Parser", int], Optional[memo.ApplyResult[int, ResultType]]]],
    Callable[["Parser", int], Optional[memo.ApplyResult[int, ResultType]]],
]:
    def deco(
        func: Callable[["Parser", int], Optional[memo.ApplyResult[int, ResultType]]]
    ) -> Callable[["Parser", int], Optional[memo.ApplyResult[int, ResultType]]]:
        def wrapper(self: "Parser", pos: int) -> Optional[memo.ApplyResult[int, ResultType]]:
            result = self.packrat.apply(lambda pos: func(self, pos), rule_id, get_rule_cache(self), pos)
            LOG.debug("result %s at %d", result, pos)
            return result

        return wrapper

    return deco


ExprType = Union[int, str, Tuple["ExprType", str, int], Tuple["ExprType", str]]


class Parser:
    """Grammar:
    expr := expr "+" num | num
    """

    def __init__(self, tokens: Sequence[str]):
        self.tokens = tokens
        self.packrat: memo.Packrat[int, int] = memo.Packrat()
        self._cache0: memo.CacheType[int, int, ExprType] = {}
        self._cache1: memo.CacheType[int, int, ExprType] = {}
        self._cache2: memo.CacheType[int, int, ExprType] = {}
        self._cache3: memo.CacheType[int, int, ExprType] = {}

    @memoize(0, lambda self: self._cache0)
    def rule_expr(self, pos: int) -> Optional[memo.ApplyResult[int, ExprType]]:
        LOG.info("rule_expr starting %d %s", pos, self.tokens)
        start_pos = pos
        result = self.rule_expr(pos)
        LOG.info("result %s", result)
        if result is not None:
            pos, result0 = result.pos, result.result
            LOG.info("rule_expr recursive call succeeded %d", pos)
            if pos >= len(self.tokens):
                return None
            if self.tokens[pos] != "+":
                LOG.info("rule_expr no +")
                return None
            pos += 1
            try:
                LOG.info("'%s'@%d", self.tokens[pos], pos)
                num = int(self.tokens[pos])
            except ValueError:
                LOG.info("rule_expr check")
                return None
            pos += 1
            LOG.info("rule_expr check")
            return memo.ApplyResult(pos, (result0, "+", num))
        pos = start_pos
        try:
            LOG.info("rule_expr check")
            num = int(self.tokens[pos])
        except ValueError:
            LOG.info("rule_expr check")
            return None
        pos += 1
        LOG.info("rule_expr check %d", num)
        return memo.ApplyResult(pos, num)

    #
    # Grammar for indirect:
    #
    # a := b "+" num
    # b := a | num

    @memoize(1, lambda self: self._cache1)
    def indirect_a(self, pos: int) -> Optional[memo.ApplyResult[int, ExprType]]:
        LOG.info("indirect_a starting %d %s", pos, self.tokens)
        result = self.indirect_b(pos)
        LOG.info("result %s", result)
        if result is not None:
            pos, result0 = result.pos, result.result
            LOG.info("indirect_a recursive call succeeded %d", pos)
            if pos >= len(self.tokens):
                return None
            if self.tokens[pos] != "+":
                LOG.info("indirect_a no +")
                return None
            pos += 1
            try:
                LOG.info("'%s'@%d", self.tokens[pos], pos)
                num = int(self.tokens[pos])
            except ValueError:
                LOG.info("indirect_a check")
                return None
            pos += 1
            LOG.info("indirect_a check")
            return memo.ApplyResult(pos, (result0, "+", num))
        return None

    @memoize(2, lambda self: self._cache2)
    def indirect_b(self, pos: int) -> Optional[memo.ApplyResult[int, ExprType]]:
        LOG.info("indirect_b starting %d %s", pos, self.tokens)
        result = self.indirect_a(pos)
        if result is not None:
            return result
        LOG.info("result %s", result)
        try:
            LOG.info("indirect_b check")
            num = int(self.tokens[pos])
        except ValueError:
            LOG.info("indirect_b check")
            return None
        pos += 1
        LOG.info("indirect_b check %d", num)
        return memo.ApplyResult(pos, num)

    #
    # Grammar for multi-path recursion:
    #
    # a := b | c | d
    # b := a "b"
    # c := a "c"
    # d := "d"

    @memoize(0, lambda self: self._cache0)
    def multi_a(self, pos: int) -> Optional[memo.ApplyResult[int, ExprType]]:
        LOG.info("multi_a starting %d %s", pos, self.tokens)
        result = self.multi_b(pos) or self.multi_c(pos) or self.multi_d(pos)
        LOG.info("result %s", result)
        return result
        if result is not None:
            return result
        result = self.multi_c(pos)
        if result is not None:
            return result

            pos, result0 = result.pos, result.result
            LOG.info("multi_a recursive call succeeded %d", pos)
            if pos >= len(self.tokens):
                return None
            if self.tokens[pos] != "+":
                LOG.info("multi_a no +")
                return None
            pos += 1
            try:
                LOG.info("'%s'@%d", self.tokens[pos], pos)
                num = int(self.tokens[pos])
            except ValueError:
                LOG.info("multi_a check")
                return None
            pos += 1
            LOG.info("multi_a check")
            return memo.ApplyResult(pos, (result0, "+", num))
        return None

    @memoize(1, lambda self: self._cache1)
    def multi_b(self, pos: int) -> Optional[memo.ApplyResult[int, ExprType]]:
        LOG.info("multi_b starting %d %s", pos, self.tokens)
        result = self.multi_a(pos)
        LOG.info("result %s", result)
        if result is None:
            return None
        pos, result0 = result.pos, result.result
        if pos >= len(self.tokens):
            return None
        if self.tokens[pos] != "b":
            return None
        pos += 1
        return memo.ApplyResult(pos, (result0, "b"))

    @memoize(2, lambda self: self._cache2)
    def multi_c(self, pos: int) -> Optional[memo.ApplyResult[int, ExprType]]:
        LOG.info("multi_c starting %d %s", pos, self.tokens)
        result = self.multi_a(pos)
        LOG.info("result %s", result)
        if result is None:
            return None
        pos, result0 = result.pos, result.result
        if pos >= len(self.tokens):
            return None
        if self.tokens[pos] != "c":
            return None
        pos += 1
        return memo.ApplyResult(pos, (result0, "c"))

    @memoize(3, lambda self: self._cache3)
    def multi_d(self, pos: int) -> Optional[memo.ApplyResult[int, ExprType]]:
        LOG.info("multi_d starting %d %s", pos, self.tokens)
        if pos >= len(self.tokens):
            return None
        if self.tokens[pos] != "d":
            return None
        pos += 1
        return memo.ApplyResult(pos, "d")


def test_direct() -> None:
    test = Parser("0+1+2+3+4+i")
    apply_result = test.rule_expr(0)
    LOG.info("parse result: '%s'", apply_result)
    assert apply_result is not None
    assert apply_result.result == ((((0, "+", 1), "+", 2), "+", 3), "+", 4)
    assert apply_result.pos == 9


def test_indirect() -> None:
    test = Parser("0+1+2+3+4+i")
    apply_result = test.indirect_a(0)
    LOG.info("parse result: '%s'", apply_result)
    assert apply_result is not None
    assert apply_result.result == ((((0, "+", 1), "+", 2), "+", 3), "+", 4)
    assert apply_result.pos == 9


def test_multi_b() -> None:
    test = Parser("db")
    apply_result = test.multi_a(0)
    LOG.info("parse result: '%s'", apply_result)
    assert apply_result is not None
    assert apply_result.result == ("d", "b")
    assert apply_result.pos == 2


def test_multi_c() -> None:
    test = Parser("dc")
    apply_result = test.multi_a(0)
    LOG.info("parse result: '%s'", apply_result)
    assert apply_result is not None
    assert apply_result.result == ("d", "c")
    assert apply_result.pos == 2


def test_fail() -> None:
    test = Parser("a")
    apply_result = test.indirect_a(0)
    LOG.info("parse result: '%s'", apply_result)
    assert apply_result is None
