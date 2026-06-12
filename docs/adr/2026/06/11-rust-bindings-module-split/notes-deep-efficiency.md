# Efficiency review — rust-bindings-module-split (3157b59..4fe645d)

No findings.

Scope checked: `crates/fltk-cst-core/src/py_module.rs` (`register_submodule`, `user_facing_name`), `src/lib.rs`, three fixture `lib.rs` files, `fltk/fegen/gsm2tree_rs.py` reserved-name check, `fltk/plumbing.py`, `fltk/fegen/genparser.py`, Makefile, new/updated tests. All changed runtime code executes once per extension import (2-4 `register_submodule` calls; each does one `sys` import, one `PyModule::new`, one `sys.modules` insert). `user_facing_name` is allocation-free borrowed-slice logic. The reserved-class-name check is O(rules) at generation time with cheap string ops. Parse-path code (span extraction/construction fast paths) is untouched. Collision fixture adds compile time to the test crate only — deliberate design tradeoff (§2.9) to avoid a new crate.
