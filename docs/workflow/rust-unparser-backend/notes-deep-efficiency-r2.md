# Efficiency review — rust-unparser-backend batch 2

Commit reviewed: e65e4f66bf2d466637df6f94744fa85abc7d239c (base d5914359)
Scope: crates/fltk-unparser-core/src/{render.rs,result.rs,lib.rs},
fltk/unparse/gsm2unparser_rs.py, tests/test_rust_unparser_generator.py.

No findings.

Checked and clear:
- `render.rs` is a faithful port of `renderer.py` and, where it differs, is cheaper:
  it moves `test_queue` into `fits` (Python copies it) and `str::split('\n')` yields
  slices instead of Python's allocated substring list. `fits` is bounded by
  `max_width` per call (early return on `column > width`; a flat-fitting group's
  total width is `<= width`), so render is O(n * max_width) — same complexity class
  as the Python source, no quadratic blowup on nested groups.
- Rc clones in the render/fits queues are non-atomic refcount bumps matching the
  doc.rs design; no per-render deep copies. Root wrapping clone is one shallow node.
- `result.rs` `doc()` is a thin convenience accessor; generated PyO3 path calls it
  once. No leaks (Doc is an acyclic Rc tree).
- `gsm2unparser_rs.py` `generate()` is memoized and build-time only.
