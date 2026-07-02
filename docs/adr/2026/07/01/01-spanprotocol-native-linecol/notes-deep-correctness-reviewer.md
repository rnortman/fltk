# Deep correctness review — `spanprotocol-native-linecol`

Reviewed: `git diff 8adf9e3..ca06929` (HEAD ca06929cd0c5f8589fe9589e7d4135f907b1f9d6).

Scope reviewed: `fltk/fegen/pyrt/span_protocol.py`, `fltk/fegen/pyrt/test_span_protocol_assignability.py`,
`fltk/fegen/pyrt/test_span_protocol_native_free.py`, plus surrounding sources (`terminalsrc.py`,
`fltk/_native/__init__.pyi`) read in full. Runtime behavior of `span_protocol.py` is unchanged
(annotation-only edits + preserved `LineColPos` re-export); the assignability pins construct valid
positions (`Span(0,1)` over `"x"` always resolves, so the `| None` slot is non-`None` at runtime and
the `isinstance` asserts are exercised, not vacuous). All 10 tests pass locally.

## Findings

### correctness-1: guard misses the `from fltk import _native as <alias>` import form — the alias channel it exists to close stays open

- **File:line:** `fltk/fegen/pyrt/test_span_protocol_native_free.py:78` (`_native_import_bound_names`) and `:91` (`_native_import_nodes`); consequently `test_native_imports_confined_to_try_fallback` (:129) and `test_no_native_bound_name_referenced_in_protocol_bodies` (:152).
- **What's wrong:** Both detection helpers recognize exactly two import forms: `ast.ImportFrom` with `node.module == "fltk._native"`, and `ast.Import` of `fltk._native[...]`. They do not recognize:
  1. `from fltk import _native as _rn` — an `ImportFrom` with `module == "fltk"` whose *alias name* is `_native`. This is a legal, working import of the extension (submodule-as-attribute) that pyright resolves against the `.pyi` stub.
  2. Relative forms, e.g. `from ..._native import LineColPos as X` from `fltk/fegen/pyrt/` (`module == "_native"`, `level == 3`).
- **Why (traced):** With `if TYPE_CHECKING: from fltk import _native as _rn` plus `-> "_rn.LineColPos | None"` inside a protocol class body:
  - `test_protocol_class_bodies_name_no_native` passes — the only class-body identifier is `_rn` (no `_native` substring in the `ast.Name` id, the `ast.Attribute` attr is `LineColPos`, and the string annotation contains no `_native` token).
  - `test_native_imports_confined_to_try_fallback` passes — `_native_import_nodes()` never matches the `module == "fltk"` `ImportFrom`, so the TYPE_CHECKING placement assertion never sees it (the pre-existing `AnySpan` try-import keeps the `assert native_imports` non-empty).
  - `test_no_native_bound_name_referenced_in_protocol_bodies` passes — `_native_import_bound_names()` returns only `{"_RustSpan"}`; `_rn` **is** collected by `_referenced_names` on the class body, but never intersects the bound set.
  Verified by executing the guard's helper logic verbatim against exactly this edited-module shape: test-2 violations `[]`, test-3 detects only the AnySpan import (the `_rn` import not detected), test-4 leaked set empty (probe at `/tmp/claude-1000/-home-rnortman-src-fltk/8c788b2d-ad36-4e8c-9e9d-478e2aa76290/scratchpad/probe_guard_gap.py`).
  This contradicts the module's own stated contract (docstring: "no name bound by **any** `fltk._native` import is referenced within either protocol class body") and the design's guard spec (design.md "Close the alias channel": "collect every name bound by any `fltk._native` import **anywhere in the module**"; and "a TYPE_CHECKING native import is exactly the leak … invisible at runtime"). Note the unaliased `from fltk import _native` variant *is* caught (the class-body root `ast.Name` id `_native` trips test 2), so the gap is specifically the aliased/relative forms.
- **Consequence:** A future edit using the aliased fltk-package attribute import (or a relative import) under `if TYPE_CHECKING:` makes `SpanProtocol`/`LineColPosProtocol`'s structural surface native-stub-dependent while every guard test stays green — precisely the stub-sensitivity regression class this new test module was added to make impossible. It is also invisible at runtime (TYPE_CHECKING-only) and invisible to the generated-file "names no native" scans, so the D5.1 stability property would silently regress; downstream generated pipelines type-checked without the native stub would break with no in-repo signal. The failure needs a deliberate-but-plausible edit, not adversarial intent: `from fltk import _native as _rn` is a natural way to spell a native reference.
- **Suggested fix:** Broaden both helpers to treat as a native import (a) any `ImportFrom` where `module == "fltk"` (or `module` is `None`/relative with resolution reaching `fltk`) and some `alias.name == "_native"` — binding `alias.asname or "_native"`; and (b) any `ImportFrom` whose resolved module path starts with `fltk._native` regardless of `level` (simplest conservative form: `node.module` splits to a path whose components include `_native`). Add the bypass shape above as a negative fixture case for the guard helpers (parse a literal snippet and assert the helpers flag it), so the detector itself is pinned.

## Non-findings (checked, clean)

- `_annotation_nodes` covers posonly/args/kwonly/vararg/kwarg/returns with `None` guards; `AnnAssign` via walk; lambdas cannot carry annotations. `isinstance(x, A | B)` union form is valid on the 3.10+ floor.
- `_identifiers_in_string_annotation`'s SyntaxError→∅ fallback cannot hide a *functioning* leak: a string annotation that doesn't parse as an expression also fails pyright, so it can't be a live native reference.
- A native import placed inside a Try nested under `if TYPE_CHECKING:` is caught (the If-walk sees descendants through the Try). A `from fltk._native import ... as X` alias used in a class body is caught by test 4 regardless of placement.
- `test_pyright_checked_slots_construct` correctly gates `_native_span_slot`/`_native_linecol_slot` references behind `_rust_available`, matching their conditional module-level definitions.
- `LineColPosProtocol` docstring semantics (0-based codepoint indices; `line_span` excludes trailing `\n`) match both `terminalsrc.Span.line_col` and the native `.pyi` docs. Forward reference `"SpanProtocol"` in a runtime_checkable protocol is never evaluated at runtime — no NameError path.
- The `LineColPos` re-export is genuinely preserved (plain import + noqa), so `span_protocol.LineColPos` keeps resolving for out-of-tree importers.
