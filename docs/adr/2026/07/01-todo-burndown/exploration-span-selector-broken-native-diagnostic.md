# Exploration: TODO(span-selector-broken-native-diagnostic)

Base commit: 8fd5ecf. All facts below are current working-tree state (`git status` clean, matches HEAD).

## Site 1: `fltk/fegen/pyrt/span.py`

Full file (21 lines), verified via `cat -n`:

```
1  """Backend selector: re-exports Span from Rust backend if available, else pure-Python.
2
3  Note: ``Span.with_source`` is intentionally excluded from ``SpanProtocol`` because
4  its signature is backend-concrete (Python accepts ``str | SourceText``; Rust accepts
5  only ``SourceText``).  The portable form is always ``Span.with_source(s, e, SourceText(text))``.
6  """
7
8  # TODO(span-selector-broken-native-diagnostic): `except Exception` swallows ANY native-import
9  # failure (ABI mismatch / corrupted .so / C init crash → OSError/SystemError), not just the
10 # expected absent-native ImportError, falling back silently with no diagnostic. Decide between
11 # narrowing the catch (propagate a genuinely broken extension) and logging the swallowed
12 # exception; keep the AnySpan block in span_protocol.py in lockstep. See TODO.md.
13 try:
14     from fltk._native import SourceText, Span, UnknownSpan  # type: ignore[assignment]
15 except Exception:
16     # Pure-Python install: the native backend is simply absent. Fall back silently to
17     # the pure-Python backend, matching span_protocol.py. There is nothing wrong with
18     # _native being missing, so no warning is emitted.
19     from fltk.fegen.pyrt.terminalsrc import SourceText, Span, UnknownSpan
20
21 __all__ = ["SourceText", "Span", "UnknownSpan"]
```

The `try` is at line 13, the sole `except Exception:` is at line 15, and the fallback import is line 19 — there is exactly one `try`/`except` pair, no duplicate except clause. The TODO comment (lines 8-12) sits immediately above the `try` block, matching the cited `span.py:8` location.

The catch clause is bare `except Exception:` — catches any `Exception` subclass, including `OSError`, `SystemError`, `ImportError`, `AttributeError`, etc. (not `BaseException`, so `KeyboardInterrupt`/`SystemExit` still propagate). No logging, no `warnings.warn`, no `exc_info` capture on the caught exception — the comment on lines 16-18 explicitly documents the silent-fallback intent for the absent-native case only, without narrowing the except clause itself.

## Site 2: `fltk/fegen/pyrt/span_protocol.py` (`AnySpan` block)

Lines 119-124:

```
119 try:
120     from fltk._native import Span as _RustSpan
121
122     AnySpan = _pymod.Span | _RustSpan
123 except Exception:
124     AnySpan = _pymod.Span  # type: ignore[assignment,misc]
```

Same shape: bare `except Exception:` at line 123, silent fallback assigning `AnySpan = _pymod.Span` (the pure-Python `terminalsrc.Span`) with no diagnostic. No TODO comment is attached at this site itself — the only `TODO(span-selector-broken-native-diagnostic)` comment in the repo is the one at `span.py:8-12`, which explicitly references this block ("keep the AnySpan block in span_protocol.py in lockstep").

## Who imports `fltk.fegen.pyrt.span` (the selector module) today

Searched all `*.py` under the repo (excluding `.claude/worktrees/*`, which contains a stale/different checkout and was excluded from all counts below) for actual import statements (not comments/strings):

- Real imports of the module: exactly one — `tests/test_span_protocol.py:10`: `import fltk.fegen.pyrt.span as _span_selector`.
- Every other hit of the string `fltk.fegen.pyrt.span` in the repo is either (a) a comment explaining that generated code must *not* import it, or (b) a test assertion string checking that generated/stub output does *not* contain the import line. These live in: `fltk/fegen/test_cst_protocol.py:600,626`, `fltk/fegen/test_genparser.py:209,222,225,228,247`, `fltk/unparse/test_is_span_guard.py:97,100,108,135,136`, `tests/test_gsm2tree_rs.py:1198-1200`, `tests/test_cst_mutators_parity.py:847` (constructs an `ast.parse` snippet as test fixture text, not a real import), plus explanatory comments in `fltk/fegen/genparser.py:113`, `fltk/fegen/gsm2tree.py:1026`, `fltk/fegen/gsm2tree_rs.py:341`, `fltk/unparse/gsm2unparser.py:1840`.
- `fltk/unparse/toy_trivia_parser.py` in the main repo does **not** import `fltk.fegen.pyrt.span` at all (confirmed by reading the file's imports directly: `errors`, `memo`, `terminalsrc`, `toy_cst` only). A copy under `.claude/worktrees/agent-ab295be24eef6e7ce/` does import it, but that worktree is a separate/stale checkout, not part of the current tree being evaluated.

`tests/test_span_protocol.py`'s `TestBackendSelectorSilentFallback.test_reload_without_native_emits_no_warning` (lines 22-39) is the only test that actually exercises the `except Exception:` branch in `span.py`: it force-sets `sys.modules["fltk._native"] = None` (which makes the `from fltk._native import ...` raise `ImportError`) and reloads the module, asserting no warning is emitted and that the fallback lands on `PySpan`/`PySourceText`. It does not construct a non-`ImportError` exception (e.g. `OSError`) to probe the broader catch.

## Who imports/uses `AnySpan` from `span_protocol.py`

- Definition site: `fltk/fegen/pyrt/span_protocol.py:122,124`.
- Only external consumer found: `tests/test_span_protocol.py:11` (`from fltk.fegen.pyrt.span_protocol import AnySpan, SpanProtocol`), used in `TestAnySpanPython` (lines 52-55, 65-67) via `isinstance(s, AnySpan)`.
- No other file in the repo (excluding the worktree) imports or references the `AnySpan` name. Files that import `span_protocol` for other reasons (`SpanProtocol`) — `fltk/fegen/fltk_cst.py`, `fltk/fegen/fltk_cst_protocol.py`, `fltk/fegen/regex_cst_protocol.py`, `fltk/unparse/toy_cst.py`, `fltk/fegen/pyrt/error_formatter.py`, `fltk/fegen/gsm2tree_rs.py`, `fltk/fegen/gsm2tree.py`, `fltk/fegen/regex_cst.py`, `fltk/fegen/pyrt/test_span_protocol_assignability.py`, `fltk/unparse/gsm2unparser.py`, `fltk/unparse/toy_cst_protocol.py`, `fltk/fegen/bootstrap_cst.py`, `fltk/fegen/bootstrap_cst_protocol.py`, `fltk/iir/context.py`, `fltk/unparse/test_is_span_guard.py`, `fltk/unparse/unparsefmt_cst_protocol.py`, `tests/rust_parser_fixture_cst_protocol.py`, `fltk/unparse/unparsefmt_cst.py`, `tests/test_gsm2tree_rs.py` — do not reference `AnySpan` specifically (grep for the bare token `AnySpan` across the repo turns up nothing in any of these files).

## TODO.md entry

`TODO.md:77` — `## \`span-selector-broken-native-diagnostic\`` header, with the body text (line 78 onward) verbatim-matching the text quoted in the task prompt, including the `Location:` line citing `fltk/fegen/pyrt/span.py:8` and `fltk/fegen/pyrt/span_protocol.py` (`AnySpan` block).

## All `TODO(span-selector-broken-native-diagnostic)` code comments

Exactly one in the whole repo: `fltk/fegen/pyrt/span.py:8`. `git grep -n "span-selector-broken-native-diagnostic"` (excluding worktrees) also matches:
- `TODO.md:77` (the master-list entry)
- `docs/adr/2026/06/26-pure-python-span-native-probe/judge-verdict-deep.md:9,76` (a prior review-chain judge verdict that dispositioned this as an acceptable TODO)
- `docs/adr/2026/06/26-pure-python-span-native-probe/dispositions-deep.md:13-14` (the disposition record that created this TODO)

No second `TODO(span-selector-broken-native-diagnostic)` comment exists at or near the `span_protocol.py` `AnySpan` block — that site is referenced only in prose by the `span.py` comment and the `TODO.md` entry, not by its own inline marker.
