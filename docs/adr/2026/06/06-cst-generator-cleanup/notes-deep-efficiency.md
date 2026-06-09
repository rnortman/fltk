No findings.

(Style note carried per author protocol: concise, precise, no padding.) Scope reviewed: 2dd27f0..b72aea6 — `fltk/fegen/gsm2tree.py` quintet extraction + label-free gating + `__all__` emission, regenerated `*_cst_protocol.py` artifacts, `tests/test_gsm2tree_py.py`. All changed code is offline build-time generation; per-label work is unchanged in shape, the `__all__` insertion scan is a one-time O(module-body) pass per regeneration, generated runtime code only shrinks (dead label-free `Label` enum removed), and new tests use class-scoped fixtures (generator built once per class).
