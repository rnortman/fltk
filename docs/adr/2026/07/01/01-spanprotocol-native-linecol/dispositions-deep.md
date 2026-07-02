# Dispositions — deep review, spanprotocol-native-linecol (round 1)

Reviewers with no findings: error-handling, security, test, reuse, efficiency.

correctness-1 and quality-1 are the same defect (alias-channel gap in the guard helpers),
disposed together. quality-2 and quality-3 handled individually.

---

correctness-1 / quality-1:
- Disposition: Fixed
- Action: `fltk/fegen/pyrt/test_span_protocol_native_free.py`. Unified the "is this a
  `fltk._native` import, and what does it bind?" predicate into a single source of truth,
  `_native_import_infos()` (test_span_protocol_native_free.py:78-135); `_native_import_nodes()`
  and `_native_import_bound_names()` now derive from it. Broadened detection to catch the
  previously-missed forms: `from fltk import _native as X` (ImportFrom, module `fltk`, alias
  `_native`) and relative forms (`from ... import _native`, `from ..._native import Name`).
  Added a parametrized negative fixture `test_alias_channel_bypass_shapes_are_detected`
  (native_free.py:~193) that parses literal bypass snippets (aliased fltk-package import and
  relative member import, each under `if TYPE_CHECKING:` and referenced in a protocol class-body
  annotation) and asserts the helpers flag them, pinning the detector itself.
- Severity assessment: High for a guard test. The guard exists specifically to close the
  alias/stub-sensitivity channel; a plausible edit (`from fltk import _native as _rn` plus a
  class-body annotation `-> "_rn.LineColPos | None"`) made the protocol surface native-stub
  dependent while passing all four guard tests and staying invisible to runtime and to the
  generated-file "names no native" scans — a silent regression of exactly the D5.1 property.
  Verified the pre-fix helpers missed the aliased form and the post-fix helpers catch it.

quality-2:
- Disposition: Fixed
- Action: `_referenced_names` (test_span_protocol_native_free.py:60-75) now takes only
  `ast.Name` ids (which cover attribute-chain roots) from a full class-body walk, and string
  identifiers only from `_annotation_nodes(...)` results — mirroring the scoping in
  `test_protocol_class_bodies_name_no_native`. It no longer best-effort-parses arbitrary
  docstrings/string constants. Signature changed from `ast.AST` to `ast.ClassDef`.
- Severity assessment: Low. Latent false-positive risk (a docstring parsing as an expression
  could feed a phantom identifier into the alias check) plus two divergent operational
  definitions of "string annotation" in one module. No live bug today, but a maintenance trap;
  fix removes the inconsistency.

quality-3:
- Disposition: Fixed
- Action: Removed the bare `spanprotocol-native-linecol` slug tags from the guard module
  docstring (test_span_protocol_native_free.py:1) and from the native-pin comment
  (test_span_protocol_assignability.py:41). Surrounding prose already states the invariant.
- Severity assessment: Low. Comment hygiene; the slug is a now-closed TODO join key that
  resolves to nothing, so leaving it invites a future grep to dead workflow artifacts.
