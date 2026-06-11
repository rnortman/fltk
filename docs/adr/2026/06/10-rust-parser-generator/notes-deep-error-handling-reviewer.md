# Error Handling Review: Phase 2 Rust Parser Generator

Style note: concise, precise, complete, unambiguous. No padding.

Commit reviewed: b95f772

---

## errhandling-1

**File:** `fltk/fegen/gsm2parser_rs.py:648`

**Broken error path:** `self._parsers[(rule_name,)]` — bare dict key lookup with no existence check.

**Why:** The first pass (`__init__`) registers exactly the rules in `self._grammar.rules`. If a rule body contains a `gsm.Identifier` term referencing a rule name not present in the grammar (e.g., a forward reference that `fltk2gsm` left dangling, or a hand-constructed `gsm.Grammar` under test), the lookup raises a raw `KeyError`. This propagates out of `generate()` uncaught. The `gen_rust_parser` CLI handler catches `(ValueError, RuntimeError, NotImplementedError)` — `KeyError` is none of those, so it escapes the handler entirely, producing an unformatted Python traceback on stderr and exit code 1 with no `Error:` prefix.

**Consequence:** On-call sees a raw Python traceback instead of a structured error message. The rule name that caused the failure is embedded in the `KeyError` key but buried in a frame deep in the traceback. Worse, the exception bypasses the CLI's `typer.echo(f"Error: {e}", ...)` path, so any log scraper watching for `"Error:"` lines on stderr will miss this failure mode entirely.

**What must change:** Either (a) validate that every `gsm.Identifier` term in every rule body names a rule that appears in the grammar, raising `ValueError` with the referencing rule name and missing identifier — do this in `__init__` alongside the existing `gsm2tree_rs` validation, or (b) convert the bare lookup to `self._parsers.get((rule_name,))` and raise `ValueError` explicitly when `None`. Option (a) is preferable: it produces the error at construction time alongside the other validation and matches the `NotImplementedError` shape for unsupported terms. The CLI already catches `ValueError`; no change to `genparser.py` is needed.

---

## errhandling-2

**File:** `fltk/fegen/gsm2parser_rs.py:506–508` (separator on `alt.initial_sep`)

**Broken error path:** `_gen_separator_code` returns `""` for `gsm.Separator.NO_WS` (handled), `WS_ALLOWED` (handled), and `WS_REQUIRED` (handled), but the `Separator` enum may in future have additional variants. More concretely today: neither `_gen_separator_code` nor `_gen_alternative` has a branch for an unrecognized `Separator` value. The `else` branch in `_gen_separator_code` falls through to the `WS_REQUIRED` handler because the Python if/elif/else structure reads:

```python
if sep == gsm.Separator.NO_WS:
    return ""
...
if sep == gsm.Separator.WS_ALLOWED:
    return (...)
else:  # WS_REQUIRED
    return (...)
```

The outer `if sep == NO_WS: return ""` guard at the top means only `WS_ALLOWED` and `WS_REQUIRED` are handled below. Any new `Separator` variant that is not `NO_WS` silently falls through to the `WS_REQUIRED` code path — it generates wrong output (a required-whitespace barrier where none was intended), with no compile error and no diagnostic.

**Consequence:** A new `Separator` variant introduced elsewhere in the GSM would silently generate incorrect parser logic — missing or wrong separators — only discoverable via behavioral test failures. No message, no traceback.

**What must change:** Add an explicit `else: raise NotImplementedError(f"Unhandled separator: {sep!r}")` after the `WS_REQUIRED` branch. The `gen_rust_parser` CLI already catches `NotImplementedError`.

---

## No further findings.

The `expect()` calls in the generated `consume_literal` / `consume_regex` (invocation_stack sentinel) are structurally unreachable as documented and are not findings. The `regex_at` `panic!` is input-independent (patterns are compile-time constants) and is caught by the generated regex compile test. The `_parse_grammar_raw` / `_read_and_parse_grammar` pipeline is validated upstream before `gen_rust_parser` receives the grammar object.
