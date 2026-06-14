# Dispositions — codegen-rust-lib-boilerplate (design review, round 1)

All six findings fact-checked against source (fltk @ 7200d9c, clockwork worktree).
All confirmed accurate; all Fixed.

---

design-1:
- Disposition: Fixed
- Action: Rewrote the formatting-gate language in §2.2 (the "Standard output"
  intro and the "Note on shape" paragraph) and §4 (fltk integration bullet) and
  §2.7. The design no longer claims generated `.rs` is "clean after `make fix`"
  or that `make check` gates its formatting. It now states `.rs` output is not
  normalized by any formatter (no rustfmt/`cargo fmt` step exists) and the real
  "done" gate is compilation (cargo check/clippy for fixtures; maturin
  `build-native` for `src/lib.rs`).
- Severity assessment: Confirmed — `make fix` is ruff-only (Makefile:85-87) and
  a repo-wide grep for `rustfmt|cargo fmt|fmt --check` returns nothing. Left
  uncorrected, the implementer would chase rustfmt-cleanliness and write an
  unverifiable formatting-cleanliness test with no backing gate.

design-2:
- Disposition: Fixed
- Action: Reworded §2.7 and the §4 fltk integration bullet. Drift detection is
  now explicitly described as the manual `make gencode` + `git diff --stat` step
  (Makefile:233-234), not part of `make check`; `make check` is stated to gate
  only compilation. Removed the overstated "gated by `make check` like the other
  generated files" framing and replaced it with "same drift posture as the other
  generated `.rs` files."
- Severity assessment: Confirmed — `check-common` (Makefile:39-51) does not run
  `gencode`; the cheat-detection comment (Makefile:233-234) is documentation of
  a manual step. Left uncorrected, the reader would assume `make check` enforces
  no-drift, which it does not.

design-3:
- Disposition: Fixed
- Action: Promoted the `TODO(fltk-pyo3-cdylib-smoke)` wiring from optional to
  in-scope. Added §2.5 step 4 (wire the smoke target to a no-`lib_rs`
  `fltk_pyo3_cdylib` driven by `bootstrap_rust_srcs`) and rewrote the §4 Bazel
  macro bullet to make in-repo coverage of the no-`lib_rs` branch mandatory,
  with the acceptance-criterion justification.
- Severity assessment: Confirmed — the only `fltk_pyo3_cdylib` consumer is
  clockwork (out of repo); BUILD.bazel:117-122 carries the smoke TODO. Without
  in-repo coverage the most novel Bazel branch would regress silently until
  clockwork's separate build breaks.

design-4:
- Disposition: Fixed
- Action: Dropped the Bazel `cst_only`/`with_parser` macro attribute from the
  design. Rewrote §2.5 step 3 (removed) and added an explicit "CST-only is not
  wired into Bazel" paragraph explaining the unreconciled coupling
  (`generate_rust_parser` always emits both outputs, rust.bzl:39-40; assembly
  requires both, rust.bzl:231-232). `--no-parser` is retained as a CLI flag only
  (§2.3). Tightened §2.1 `cst-only-mode` to say CLI/generator-only and point at
  §2.5.
- Severity assessment: Confirmed — the macro attribute would have controlled
  only lib.rs shape while the parser output and presence check stayed
  unconditional, an unreconciled coupling with no in-scope consumer. Keeping it
  would have shipped a half-wired, possibly-broken CST-only Bazel path.

design-5:
- Disposition: Fixed
- Action: Updated §3 (Orphaned TODO bullet) and §4 (TODO handling) to require
  adding the matching `native-submodule-error-context` entry to fltk `TODO.md`
  when relocating the inline comment to `crates/fltk-cst-core/src/py_module.rs:87`,
  per CLAUDE.md's two-part convention — or adjudicating the TODO for removal.
  Merely relocating the comment is no longer presented as sufficient.
- Severity assessment: Confirmed — grep shows the slug has no `TODO.md` entry in
  either repo (only `fltk-pyo3-cdylib-smoke` exists). Relocating the comment
  alone perpetuates a convention-violating orphan TODO.

design-6:
- Disposition: Fixed
- Action: Rewrote §2.5 to spell out the concrete Bazel mechanism: `lib_rs`
  defaults to `None`; when `None`, instantiate a `name + "_gen_lib"` genrule
  that runs `$(location //:genparser) gen-rust-lib $@ --module-name <name>` with
  `//:genparser` in `tools`, then set `lib_rs = ":" + name + "_gen_lib"`.
  Replaced the "exactly as a consumer-authored one today" gloss with an explicit
  note that the assembly genrule's `lib_rs` input now resolves to a generated
  target (the one wiring change), and noted `generate_rust_parser` cannot host
  this because `gen-rust-lib` takes no grammar.
- Severity assessment: Confirmed — `lib_rs` is currently a mandatory param
  (rust.bzl:126) fed as a genrule src and `$(location {lib_rs})`
  (rust.bzl:222,227). Low risk of being built wrong, but the mechanism was
  underspecified; naming it removes implementer guesswork.
