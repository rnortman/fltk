# Slop pre-pass notes

Commits reviewed: fltk fafa6d7..353d24c, clockwork ece332ad..0bf463b

---

## slop-1

**File:line**: `clockwork/dsl/clockwork_rust_roundtrip_test.py:33-38`

**Quote**:
```python
span_fallback_warnings = [
    w for w in caught if "span" in str(w.message).lower() or "fltk" in str(w.filename).lower()
]
```

**What's wrong**: The warning-filter heuristic is fragile and silently wrong in two directions. `str(w.message)` on a `warnings.WarningMessage` yields the repr of the warning object, not its text — the actual message string is at `w.message.args[0]`. `w.filename` matches any file that happens to contain "fltk" in its path (e.g. system dirs). These bugs could make the test pass vacuously (no warning caught because the filter never matches) even when the fallback fires.

**Consequence**: The test is meant to be a hard gate that the pure-Python span fallback is not active. If the filter silently misses the warning, the test gives a false green. A reviewer shipping this PR ships a test that may not actually catch the failure it was designed for.

**Suggested fix**: Filter on `issubclass(w.category, UserWarning)` and `"fltk.fegen.pyrt.span" in w.filename` (the module path the fallback actually lives in, per the docstring). Use `str(w.message.args[0]).lower()` if content matching is also desired.

---

## slop-2

**File:line**: `clockwork/dsl/clockwork_rust_roundtrip_test.py:1`

**Quote**: module docstring — `Acceptance criteria (design §5, AC #3 + #4): ...`; function docstring — `The pure-Python fallback in fltk/fegen/pyrt/span.py emits a warnings.warn when it activates.`

**What's wrong**: These are task-tracking / caller-referencing comments embedded in production test code. The module docstring names a design-doc section number and acceptance criteria IDs. The function docstring explains the architecture of a module the test doesn't directly test. Both belong in the PR description or the design doc, not the committed test file.

**Consequence**: Reads as an LLM narrating the writing process. Section numbers rot the moment the design doc is revised. A later reader has no way to look up "design §5, AC #3 + #4" without hunting for the design doc.

**Suggested fix**: Replace the module docstring with one sentence describing what the test validates and how to run it. Replace the function docstring with a single sentence stating the invariant being checked ("asserts that fltk._native.Span resolves via the Rust extension, not the pure-Python fallback"). Remove design-doc references.

---

## slop-3

**File:line**: `rust.bzl:55` (comment block above `cst_out`/`parser_out` declarations)

**Quote**:
```
# The fixed basenames are load-bearing: fltk_pyo3_cdylib assembles them
# alongside lib.rs and the bare `mod cst;` / `mod parser;` declarations
# in lib.rs rely on these exact names.
```

And immediately in the rule doc:
```
The fixed basenames (cst.rs / parser.rs) are load-bearing: a consumer lib.rs
that contains `mod cst;` and `mod parser;` relies on these exact names.
```

**What's wrong**: The same sentence appears verbatim twice — once in the inline implementation comment and once in the rule's `doc` string seven lines away. Duplicate comments diverge over time and the implementation comment adds nothing beyond what the rule doc already says.

**Consequence**: Minor but visible duplication that flags as generated/copy-pasted. Not embarrassing on its own, but combined with the other findings it adds to the "LLM wrote this" signal.

**Suggested fix**: Keep the constraint in the `doc` string (canonical reference for rule users). Drop the inline implementation comment or replace it with a one-line note pointing to the doc.

---

No silent fallbacks or workaround-for-bugs findings in the build rules or Rust source on this diff.
