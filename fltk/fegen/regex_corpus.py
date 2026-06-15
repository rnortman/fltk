"""General-purpose regex extraction and classification tool for FLTK grammars.

This module is the single source of truth for:

1. ``collect_regexes(grammar)`` — walk any ``gsm.Grammar`` and return every distinct
   regex body (the raw body string as stored in ``gsm.Regex.value``, i.e. already
   stripped of the outer ``/.../`` delimiters) that appears in the grammar.

2. ``classify_pattern(pattern)`` — run a single regex body through the generated
   ``fltk.fegen.regex_parser`` and return True (accepted, pattern is in the portable
   subset) or False (rejected, pattern contains a non-portable construct or is
   otherwise unrecognised by the grammar).

Both the committed corpus tests (``tests/test_regex_grammar_corpus.py``) and the
grammar-agnostic CLI entry point (``__main__`` block below) import from here so there
is exactly one copy of the enumeration and oracle logic.

CLI usage (grammar-agnostic; pass any .fltkg path):

    uv run python -m fltk.fegen.regex_corpus <path/to/grammar.fltkg>

Exit code is 0 if every extracted pattern is accepted, non-zero otherwise.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from fltk.fegen import gsm
from fltk.fegen.regex_portability import check_regex_portable
from fltk.plumbing import parse_grammar_file


def collect_regexes(grammar: gsm.Grammar) -> list[str]:
    """Return the distinct regex bodies present in *grammar*, in encounter order.

    Each returned string is a ``gsm.Regex.value`` — the raw pattern body with the
    outer ``/.../`` delimiters already stripped, exactly as ``gsm.Regex`` stores it.
    Duplicates are removed (a pattern that appears in multiple rules is returned
    once); the first-encountered order is preserved.

    The walk uses ``gsm._for_each_item`` which recurses into ``Sequence[Items]``
    sub-expressions, so regexes nested inside parenthesised alternatives are also
    collected.
    """
    seen: dict[str, None] = {}  # ordered-insertion dedup (dict preserves order, set does not)

    def _collect_items(items: gsm.Items) -> None:
        def _visit(_idx: int, item: gsm.Item) -> None:
            if isinstance(item.term, gsm.Regex):
                seen[item.term.value] = None
            # gsm._for_each_item recurses into Sequence[Items] terms, so sub-expressions
            # are handled by the same visitor without extra recursion here.

        gsm._for_each_item(items, _visit)  # TODO(gsm-for-each-item-public): promote to public API

    for rule in grammar.rules:
        for alternative in rule.alternatives:
            _collect_items(alternative)

    return list(seen.keys())


def classify_pattern(pattern: str) -> bool:
    """Return True if *pattern* is accepted by the regex grammar, False otherwise.

    Delegates to ``check_regex_portable`` from ``regex_portability`` -- the canonical
    single home for the accept/reject predicate.  Returns ``True`` iff
    ``check_regex_portable`` returns ``None`` (no issue found, pattern is portable).

    A returned False means either (a) the parser matched only a prefix (short parse,
    e.g. a non-portable construct stalled the grammar early) or (b) the parser produced
    no result at all.  Both are ``reject`` from the portable-subset perspective.
    """
    return check_regex_portable(pattern) is None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def run_cli(argv: Sequence[str]) -> int:
    """Main for ``python -m fltk.fegen.regex_corpus <grammar.fltkg>``.

    Returns the process exit code: 0 if all patterns accepted, 1 otherwise.
    """
    if len(argv) != 1:
        print("Usage: python -m fltk.fegen.regex_corpus <grammar.fltkg>", file=sys.stderr)  # noqa: T201
        return 2

    grammar_path = Path(argv[0])
    if not grammar_path.exists():
        print(f"error: grammar file not found: {grammar_path}", file=sys.stderr)  # noqa: T201
        return 2

    try:
        grammar = parse_grammar_file(grammar_path)
    except (ValueError, OSError) as exc:
        # OSError covers FileNotFoundError, PermissionError, UnicodeDecodeError (subclass of
        # ValueError, but listed for clarity), and any other I/O failure from Path.open().
        print(f"error: could not parse grammar {grammar_path}: {exc}", file=sys.stderr)  # noqa: T201
        return 2

    patterns = collect_regexes(grammar)
    any_rejected = False
    for pattern in patterns:
        accepted = classify_pattern(pattern)
        status = "ACCEPT" if accepted else "REJECT"
        print(f"{status}  {pattern!r}")  # noqa: T201
        if not accepted:
            any_rejected = True

    print(f"\n{len(patterns)} distinct regex(es) found in {grammar_path.name}.")  # noqa: T201
    if any_rejected:
        print("One or more patterns were REJECTED — see output above.")  # noqa: T201

    return 1 if any_rejected else 0


if __name__ == "__main__":
    sys.exit(run_cli(sys.argv[1:]))
