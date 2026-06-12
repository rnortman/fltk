# Efficiency review — rust-cst-accessor-clone-efficiency

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Reviewed: 74adcf8..1eb2580 (HEAD 1eb2580). Scope: `fltk/fegen/gsm2tree_rs.py` four read-accessor emitters + six regenerated `.rs` outputs + `tests/test_rust_cst_poc.py` + `TODO.md`.

No findings.

Verified:

- All four emitted shapes now do O(matching) clones instead of O(total-children): `child()` clones at most one entry (zero on the error path), `children_<label>` collects only matching `Child` values, `child_<label>`/`maybe_<label>` clone only the first match. Strict improvement over base; this is exactly the work the TODO described.
- All Python work (`format!`-into-`PyValueError`, `into_pyobject`, `to_pyobject`) stays outside the read guard; guard-scope work is len/label-compare/`Child::clone` only. No new blocking work added to the per-read hot path.
- Generated diffs in all six output files contain only the four template substitutions (grep over diff confirmed no out-of-template lines); the spike crate `cp` copy is in sync.
- Removed dead work: the old error path in `child_<label>`/`maybe_<label>` called `to_pyobject` (registry insert + handle mint) before raising; new shape raises without converting.

Considered, not findings:

- `maybe_<label>` keeps scanning after count hits 2 (no early exit). Residual iterations are label compares only; design.md explicitly dispositions this for template uniformity with `child_<label>`'s exact-count message. Agree.
- `children_<label>` uses `PyList::empty` + per-element `append` rather than a presized list. `PyList::new` cannot express fallible per-element conversion without an intermediate handle Vec; design pins element-by-element error propagation. Negligible at realistic child counts.
- The intermediate `matching: Vec<_>` allocation is architecturally required by the no-Python-under-lock invariant (snapshot-then-convert); cannot be removed.
