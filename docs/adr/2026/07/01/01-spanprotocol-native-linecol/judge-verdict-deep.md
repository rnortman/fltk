# Judge verdict — deep review

Phase: deep. Base 8adf9e3..HEAD 150a305 (reviewers examined ca06929; fix commit 150a305). Round 1.
Notes: 7 reviewer files; 5 report no findings (error-handling, security, test, reuse, efficiency).
4 finding IDs, 3 dispositions (correctness-1/quality-1 disposed jointly). All dispositioned Fixed.

## Added TODOs walk

No TODO dispositions this round; no new `TODO(slug)` comments in the diff (`git grep` for TODO
markers in the changed files at HEAD is clean).

## Other findings walk

### correctness-1 / quality-1 — Fixed
Claim: both native-import detection helpers in `test_span_protocol_native_free.py` recognized only
`ImportFrom module == "fltk._native"` and `Import fltk._native[...]`, missing `from fltk import
_native as X` and relative forms; consequence is that a TYPE_CHECKING-gated aliased import plus a
class-body string annotation makes the protocol surface native-stub-dependent while all four guard
tests stay green — a silent regression of the exact D5.1 property the guard exists to enforce.
quality-1 additionally flagged the predicate being duplicated across the two helpers.
Severity: blocker for a guard test (advertises a property it doesn't enforce; correctness reviewer
executed the bypass and confirmed all four tests pass on the violating shape).
Evidence at 150a305, `fltk/fegen/pyrt/test_span_protocol_native_free.py`:
- Single predicate `_native_import_infos(tree)` (lines 82–125); `_native_import_bound_names` and
  `_native_import_nodes` (lines 128–137) are now pure derivations — the duplication is gone.
- New `ImportFrom` handling covers `module_parts[:2] == ["fltk","_native"]`, relative
  `module_parts[-1] == "_native"` with `level > 0`, `module == "fltk"` with alias `_native`, and
  relative bare `from ... import _native` — exactly the reviewer-listed missed forms, matching
  quality-1's suggested "one predicate, two views" shape.
- Negative fixture `test_alias_channel_bypass_shapes_are_detected` (lines 205–233) pins the two
  bypass shapes (aliased fltk-package import; relative member import), as correctness-1's
  suggested fix asked.
Non-vacuity verified independently: I ran both `_BYPASS_SNIPPETS` against the ca06929 helper code
— old helpers return bound=∅, nodes=0, leaked=∅ on both shapes (the new test would have failed
pre-fix); at HEAD all 12 tests in the two touched test files pass, including both bypass
parametrizations. With the fixed helpers the original probe shape is now caught twice over:
test 3's TYPE_CHECKING assertion sees the aliased import node, and test 4 intersects `_rn`/`_RLC`
with class-body referenced names.
Assessment: fix addresses both the detection gap and the duplication, with the detector itself
pinned. Accept.

### quality-2 — Fixed
Claim: `_referenced_names` best-effort-parsed every string constant in the class body (docstrings
included), diverging from the annotation-scoping in `test_protocol_class_bodies_name_no_native`;
consequence is latent false positives (an expression-shaped docstring feeding phantom identifiers)
plus two operational definitions of "string annotation" in one module.
Severity: should-fix (latent, no live bug — matches responder's Low assessment).
Evidence at 150a305, lines 60–75: `ast.Name` ids from the full class-body walk; string identifier
tokens taken only from `ast.walk` over `_annotation_nodes(class_def)` results; signature narrowed
`ast.AST` → `ast.ClassDef` (both call sites pass a ClassDef). This is the reviewer's suggested fix
verbatim; the `SyntaxError` fallback in `_identifiers_in_string_annotation` is no longer
load-bearing for docstring tolerance. String-annotation extraction still functions — the bypass
fixture's leaked-set assertion depends on `_rn`/`_RLC` coming out of string annotations, and it
passes.
Assessment: accept.

### quality-3 — Fixed
Claim: bare `spanprotocol-native-linecol` slug tags in two shipped comments join to a now-deleted
TODO entry; consequence is grep-to-dead-artifact rot.
Severity: nit.
Evidence: diff removes the tag from the module docstring (`test_span_protocol_native_free.py:1`)
and the headline-pin comment (`test_span_protocol_assignability.py:41`); `git grep` for the slug
at HEAD over `fltk/` and `TODO.md` returns nothing (remaining occurrences are only in the ADR
workflow directory, which is expected). Surrounding prose still states the invariant in both
places.
Assessment: accept.

## Disputed items

None.

## Approved

4 finding IDs across 3 dispositions: 3 Fixed, all verified (1 blocker, 1 should-fix, 1 nit).
5 reviewers reported no findings.

---

## Verdict: APPROVED

All dispositions acceptable; every Fixed claim verified against the diff and by execution,
including independent confirmation that the new detector pin fails against the pre-fix helpers.
