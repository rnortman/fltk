# Deep quality review — spanprotocol-native-linecol

Reviewed: `8adf9e3..ca06929` (HEAD ca06929cd0c5f8589fe9589e7d4135f907b1f9d6)

Overall: the change itself is clean — the protocol addition is minimal, the docstrings carry
load-bearing rationale (why property members), the `LineColPos` re-export is preserved
deliberately, and the guard test enforces a property that was previously only documented.
Findings below are all in the new guard test module plus one comment-hygiene item.

## quality-1 — native-import predicate duplicated in two helpers, and both miss the `from fltk import _native` form

- File: `fltk/fegen/pyrt/test_span_protocol_native_free.py:70-94`
  (`_native_import_bound_names`, `_native_import_nodes`)
- Issue: the "is this a `fltk._native` import?" predicate (`ImportFrom.module ==
  "fltk._native"`, or `Import` alias `== / startswith "fltk._native"`) is written out twice,
  once per helper. Both copies also miss `from fltk import _native [as X]` (an `ImportFrom`
  with `module == "fltk"`) and the relative form (`from ... import _native` from within
  `fltk/fegen/pyrt/`). Concretely: `from fltk import _native as _nat` under `if
  TYPE_CHECKING:` plus a class-body annotation `-> "_nat.LineColPos"` passes all four guard
  tests — the confinement test never sees the import (module isn't `"fltk._native"`), the
  bound-names set doesn't contain `_nat`, and the string `"_nat.LineColPos"` contains no
  `_native` substring. That is precisely the alias-channel stub-sensitivity leak the guard
  exists to close (the design's §"Close the alias channel" motivation), reachable via one
  plausible import-form variation.
- Consequence: the guard advertises a property it doesn't fully enforce, so a future
  regression can land silently — the worst failure mode for a guard test. And because the
  predicate lives in two places, any future tightening must be applied twice or the two tests
  drift into enforcing different definitions of "native import".
- Fix: single source of truth — keep `_native_import_nodes()` as the one predicate (extend it
  to treat `ImportFrom` as native when `module == "fltk._native"`, OR `module in ("fltk", None
  with level>0 resolving into fltk) and any alias name == "_native"`), and derive
  `_native_import_bound_names()` by iterating the nodes that helper returns. One predicate,
  two views of it.

## quality-2 — `_referenced_names` scans all string constants, contradicting the annotation-scoping the sibling test (and implementation report) establish

- File: `fltk/fegen/pyrt/test_span_protocol_native_free.py:58-67` (`_referenced_names`), used
  by `test_no_native_bound_name_referenced_in_protocol_bodies` (line 153).
- Issue: the implementation report's one substantive deviation is that string-`_native`
  checks are scoped to actual annotation expressions via `_annotation_nodes` so docstrings
  don't false-positive — and `test_protocol_class_bodies_name_no_native` does exactly that.
  But `_referenced_names` walks *every* string constant in the class body (docstrings
  included) and best-effort-parses each as an expression, relying on prose docstrings
  happening to be `SyntaxError`s. The module now contains two different operational
  definitions of "string annotation" side by side.
- Consequence: latent false positives (a short docstring that parses as an expression — e.g.
  a one-word or `a.b`-shaped docstring — feeds phantom identifiers into the alias check), and
  a maintenance trap: a future editor tightening one definition will reasonably assume the
  other matches. The `_annotation_nodes` helper already exists to express the correct scope.
- Fix: in `_referenced_names`, take string identifiers only from `_annotation_nodes(...)`
  results (plus `ast.Name`/attribute roots from the full body walk), mirroring
  `test_protocol_class_bodies_name_no_native`. Then the `SyntaxError` fallback in
  `_identifiers_in_string_annotation` stops being load-bearing for docstring tolerance.

## quality-3 — comment hygiene: workflow-slug tags left in shipped comments/docstrings

- Files: `fltk/fegen/pyrt/test_span_protocol_native_free.py:1` ("...(spanprotocol-native-linecol).")
  and `fltk/fegen/pyrt/test_span_protocol_assignability.py:41` ("...(spanprotocol-native-linecol).").
- Issue: this change deletes the `spanprotocol-native-linecol` entry from `TODO.md` and the
  `TODO(...)` comment block — the slug is the join key of a now-closed work item — yet two new
  comments embed the bare slug as a parenthetical tag. It reads like a `TODO(slug)` reference
  that joins to nothing; its only remaining referent is the ephemeral workflow design doc
  under `docs/adr/2026/07/01/01-spanprotocol-native-linecol/`.
- Consequence: exactly the rot the TODO system avoids — a future reader greps the slug,
  finds no TODO entry, and lands in workflow artifacts instead of an explanation. The
  surrounding prose in both places already states the invariant fully; the tags add nothing.
- Fix: drop both parenthetical slug tags. (If a durable pointer is wanted, the ADR *decision*
  doc is the right referent — but the prose stands on its own without one.)

No findings in `span_protocol.py` itself: the protocol placement, forward-reference cycle
handling, re-export treatment, and the untouched `AnySpan` block all match the module's
existing patterns; no redundant state, parameter sprawl, or workaround patterns observed.
