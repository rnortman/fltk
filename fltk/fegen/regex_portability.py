"""Portability checker for grammar regex patterns.

Validates that a ``gsm.Regex.value`` string belongs to the portable regex subset --
the set of regex constructs that behave identically on Python ``re`` and Rust
``regex-automata``.  The portable subset is defined by ``fltk/fegen/regex.fltkg``
(an FLTK grammar of the allowed subset); this module is a thin wrapper around the
generated ``regex_parser.Parser`` so callers do not duplicate the parse-and-check
boilerplate.

Usage::

    from fltk.fegen.regex_portability import check_regex_portable

    issue = check_regex_portable(pattern)
    if issue is not None:
        raise ValueError(f"Non-portable regex at offset {issue.offset}: {issue.detail}")

The checker is wired into the Rust parser generator (``gsm2parser_rs.py``) so that
every grammar regex is validated at Rust generation time.  The Python generator is not
checked (the Python ``re`` semantics are the stable baseline; see design §5.3).

Documented limits (constructs admitted by syntax but with a non-ASCII semantic
residual):
  ``\\d``/``\\w``/``\\s`` and their negations -- Unicode-class tables differ by engine DB.
  ``(?i)`` case-folding over non-ASCII -- fold tables differ by engine DB version.
  ``\\b``/``\\B`` word boundaries -- defined in terms of ``\\w``, same residual.
These are admitted as ASCII-portable; the divergence is documented-only and cannot
be caught by a static syntax checker (any static approach shares this limit).
TODO(regex-unicode-class-divergence): track the full non-ASCII residual ledger.
"""

from __future__ import annotations

from dataclasses import dataclass

from fltk.fegen.pyrt import terminalsrc
from fltk.fegen.regex_parser import Parser as _RegexParser

_TAIL_PREVIEW_LEN = 20  # characters to show from the unrecognised tail in error messages


@dataclass(frozen=True)
class RegexPortabilityIssue:
    """Describes a portability problem found in a grammar regex pattern.

    Attributes:
        pattern: The offending pattern string (the ``gsm.Regex.value``).
        offset:  Codepoint offset of furthest progress (``error_tracker.longest_parse_len``
                 clamped to ``>= 0``).  The raw ``longest_parse_len`` sentinel ``-1``
                 ("no terminal was reached") is normalised to ``0`` at construction so
                 callers never see a negative offset.
        detail:  Human-readable context for the error message.
    """

    pattern: str
    offset: int
    detail: str


def check_regex_portable(pattern: str) -> RegexPortabilityIssue | None:
    """Return an issue if *pattern* is outside the portable regex subset, else None.

    Parses *pattern* with the generated ``regex_parser.Parser`` (derived from
    ``fltk/fegen/regex.fltkg``).  A pattern is portable iff the start rule both
    matches AND consumes the entire input.

    Two reject shapes both map to "non-portable":

    - *Hard fail*: the start rule returns ``None`` (matched nothing -- e.g. first
      char unrecognised).
    - *Short parse*: the start rule returns an ``ApplyResult`` with
      ``pos < len(pattern)`` (matched a prefix, stopped at a non-portable construct).

    The reported ``offset`` is always ``parser.error_tracker.longest_parse_len``
    (the furthest position any terminal reached before failing, design §5.2).
    This is the right offset for a recogniser that deliberately *does not* match an
    excluded tail: it points at the deepest position the subset grammar could push
    before stalling -- the location a human wants.  It is populated independently of
    labels/dispositions by the runtime's ``error_tracker.fail_regex``/``fail_literal``
    calls on every terminal-consume failure.

    An empty pattern string is treated as portable (it contains no construct) and
    returns ``None`` without invoking the parser.
    """
    if not pattern:
        return None

    ts = terminalsrc.TerminalSource(pattern)
    parser = _RegexParser(terminalsrc=ts)
    result = parser.apply__parse_regex(0)

    if result is not None and result.pos == len(pattern):
        return None  # Portable: start rule consumed entire input.

    # Non-portable: either hard fail (result is None) or short parse (pos < len).
    # Report the furthest-progress offset from the error tracker.
    # Clamp to 0: the initial sentinel value -1 ("no terminal fired") is not a
    # meaningful codepoint offset and must not be exported on RegexPortabilityIssue.
    offset = max(parser.error_tracker.longest_parse_len, 0)
    if result is None:
        detail = (
            f"the regex grammar could not start parsing at offset {offset} "
            f"(first unrecognised construct); pattern: {pattern!r}"
        )
    else:
        stopped = result.pos
        detail = (
            f"the regex grammar parsed only {stopped} of {len(pattern)} characters "
            f"(furthest progress: offset {offset}); "
            f"unrecognised tail starting at {stopped}: "
            f"{pattern[stopped : stopped + _TAIL_PREVIEW_LEN]!r}"
            f"{'...' if len(pattern) - stopped > _TAIL_PREVIEW_LEN else ''}; "
            f"pattern: {pattern!r}"
        )

    return RegexPortabilityIssue(
        pattern=pattern,
        offset=offset,
        detail=detail,
    )
