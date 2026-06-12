slop-1. `tests/test_gsm2tree_rs.py` lines ~1800–1870 (`test_multiple_collisions_reported_at_once`).
Four inline `gsm.Rule(...)` blobs hand-rolling identical structure — the same six-line Items/Item pattern copy-pasted four times. `_make_two_rule_grammar` already exists for exactly this pattern; the test should construct two two-rule grammars and merge, or extend `_make_two_rule_grammar` to accept N names.
**Consequence**: Volume of repetition reads as LLM padding; a reviewer will question whether the author noticed `_make_two_rule_grammar` exists. Signals inattention.
**Fix**: Extend `_make_two_rule_grammar` to accept `*rule_names` (varargs), or call it twice and merge `rules`/`identifiers`.

slop-2. `fltk/fegen/gsm2tree_rs.py` line ~108 (INVARIANT comment on `_RESERVED_CLASS_NAMES`).
```
# INVARIANT: no reserved name here starts with "Py", ends with "Child", or ends with
# "Label" — the derived per-rule identifiers Py{CN}, {CN}Child, {CN}Label would need
# seeding into the cross-rule `claims` dict to gain collision coverage if that changed.
```
This comment describes an implementation contract between two sections of the same `__init__` that the code does not enforce. Nothing stops a future editor from adding, say, `"PyNode"` to `_RESERVED_CLASS_NAMES` and silently breaking the invariant. The cross-rule check should either seed reserved names into `claims`, making the invariant unnecessary, or an assertion should guard it at startup.
**Consequence**: The invariant is stated in prose but not machine-checked; the comment signals the author knew there was a gap and left it as documentation rather than code.
**Fix**: Either pre-seed `_RESERVED_CLASS_NAMES` keys into `claims` (eliminating the invariant entirely) or add a startup `assert` that no reserved name has the offending prefixes/suffixes.

slop-3. `tests/test_gsm2tree_rs.py` lines ~1877–1913 (`test_prediction_vs_output_consistency`).
```python
from fltk.fegen.gsm2tree_rs import RustCstGenerator as _Gen  # noqa: PLC0415
```
`RustCstGenerator` is already imported at module scope in this test file (used throughout). The redundant local import with `# noqa` is LLM boilerplate — it suggests the author copy-pasted a snippet without checking the top-of-file imports.
**Consequence**: Gratuitous `noqa` suppression for a problem that doesn't exist; minor but visible as slop.
**Fix**: Remove the local import; use the module-level `RustCstGenerator` directly.
