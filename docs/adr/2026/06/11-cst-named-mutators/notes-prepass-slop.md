slop-1. tests/rust_parser_fixture/src/collision_cst.rs, multiple `insert` pymethods (~line 600+).
`raw_idx.call_method0(pyo3::intern!(py, "__neg__"))?.extract::<i64>().map(|v| v > 0).unwrap_or(false)`
Stale generated file: the clamping bug (`__neg__` + `i64` extraction to detect sign of beyond-i64 indices) was found and fixed in `gsm2tree_rs.py` and all other generated files in commit 90cb790, but `collision_cst.rs` was not regenerated. It still contains the broken sign-detection logic that mis-clamps `insert(-10**25)` to the wrong end.
Consequence: `collision_cst.rs` diverges from the generator and from every other generated file; the fix claim in the commit log is incomplete. A reviewer looking at this file sees a known-wrong pattern the author already identified as a bug.
Fix: regenerate `tests/rust_parser_fixture/src/collision_cst.rs` from the corrected generator (run the same regen step that produced `src/cst_fegen.rs`, `tests/rust_cst_fegen/src/cst.rs`, etc.).

slop-2. fltk/fegen/gsm2tree.py, generator comment (~line 208).
`# sys is already imported at the top of this module.`
Narrative process comment describing the prior state of the generator file, not an invariant or intent of the emitted code. "Already imported" reads like LLM housekeeping notes.
Consequence: signals that the comment was written to justify an action taken during editing rather than to communicate anything durable to future readers.
Fix: remove the line, or fold its content into the preceding sentence: "sys is imported at the top of generated modules to support lazy native-Span resolution (§2.2)."

slop-3. fltk/fegen/gsm2tree.py, protocol stub (~line 899).
`remove_ret = child_ret  # same tuple shape as child()`
The inline comment is true, but `remove_ret` is a one-use alias for `child_ret` introduced solely to carry this comment. The name and comment together read as an LLM explaining its own reasoning rather than expressing a constraint that belongs in code.
Consequence: minor noise; the alias adds no abstraction and the comment adds no new information beyond what the type annotation already conveys.
Fix: inline `child_ret` directly and drop the alias, or if the equivalence is non-obvious, put it in the docstring.
