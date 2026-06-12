## Increment 1 — filter-under-guard in `_generic_child`, `children_<label>`, `child_<label>`, `maybe_<label>` (commit 3d03b61)

- `fltk/fegen/gsm2tree_rs.py:1040-1065`: `_generic_child` — checks len and clones at most `children[0]` under guard; raises outside guard. TODO comment removed.
- `fltk/fegen/gsm2tree_rs.py:1413-1434`: `children_<label>` — filter+map+collect inside guard (matching children only); `to_pyobject` loop outside guard. TODO comment removed.
- `fltk/fegen/gsm2tree_rs.py:1436-1466`: `child_<label>` — count+first-clone loop inside guard; error raise and `to_pyobject` outside. Restructured to call `.to_pyobject(py)` directly on `first` (eliminates the `found: Option<PyObject>` variable). TODO comment removed.
- `fltk/fegen/gsm2tree_rs.py:1468-1497`: `maybe_<label>` — same count+first-clone pattern; match on `first` outside guard. TODO comment removed.
- `TODO.md:27`: deleted `rust-cst-accessor-clone-efficiency` entry.
- `make gencode` + `make fix`: regenerated all six `.rs` outputs; TODO comments absent from generated files.
- `tests/test_rust_cst_poc.py`: added `TestFilterUnderGuardRegression` class (7 tests) covering mixed-label filtering correctness, exact count in error messages, `child_<label>` unique-match, `maybe_<label>` unique-match, and node-child registry identity pin.
- All 1406 tests pass; `make check` clean.
