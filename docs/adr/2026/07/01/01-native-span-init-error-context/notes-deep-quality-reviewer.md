# Quality review — native-span-init-error-context

Reviewed: `git diff f8f3428..b60f8c7` (HEAD b60f8c7873249598598... = b60f8c7).
Verified before writing: full `fltk/fegen/test_gsm2lib_rs.py` suite passes (52 passed),
the drift-pin test holds byte-for-byte against committed `src/lib.rs`, and
`_span_only_spec()` matches the Makefile `gen-rust-lib` invocation
(Makefile:276-277: `--module-name _native --register-span-types --unknown-span-static
--no-cst --no-parser`).

## quality-1

- **Where:** `fltk/fegen/test_gsm2lib_rs.py:310-312`
  (`test_committed_lib_rs_matches_generator`).
- **Issue:** The drift-pin test — whose entire purpose is to catch *silent* divergence —
  can itself go silent. It `pytest.skip`s whenever `src/lib.rs` is absent, with no
  distinction between "running outside a repo checkout" (the intended skip case per the
  design) and "running inside the repo but the file moved". If a future build-system
  reorg relocates `src/lib.rs` (this repo has already reshuffled its Rust layout more
  than once: `crates/`, `tests/rust_*`), the gate evaporates as a permanently-skipped
  test rather than a failure, and skips are exactly the kind of signal nobody reads.
  The Makefile `gencode` comment would still point at the old path too.
- **Consequence:** The one automatic drift gate regresses to the pre-change state
  (manual "eyeball `git diff` after gencode") without anyone being told — recreating
  the original bug's detection gap while the test suite stays green. A guard that fails
  open is worse than no guard, because it also ends the conversation ("we have a test
  for that").
- **Fix:** Skip only when genuinely outside a checkout; fail when inside one but the
  file is missing. E.g.:

  ```python
  repo_root = Path(__file__).parents[2]
  lib_rs = repo_root / "src" / "lib.rs"
  if not (repo_root / "pyproject.toml").exists():
      pytest.skip(f"not a repo checkout: {repo_root}")
  assert lib_rs.exists(), "src/lib.rs missing — drift pin must move with it (see Makefile gen-rust-lib)"
  ```

  (Any stable repo marker works; the point is that relocation of the pinned file
  produces a red test naming the pin, not a skip.)

## Checked and passed (no findings)

- **Sibling-pattern fidelity:** the emitted `map_err` block matches the established
  handwritten pattern in `crates/fltk-cst-core/src/py_module.rs:155-159` (closure-block
  shape, fully-qualified `pyo3::exceptions::PyRuntimeError`, `{e}` interpolation).
  Fourth inline occurrence of the pattern overall; centralizing into an fltk-cst-core
  helper would add public crate API for marginal gain — inline is the right call here.
- **Comment hygiene:** the TODO removal is properly two-sided (`TODO.md` entry +
  `TODO(native-span-init-error-context)` code comment deleted together); no design-doc
  references or changelog-style comments introduced in code.
- **Generator style:** line-by-line `body.append()` for the wrap block matches the
  file's uniform emission style; the single f-string with `{{e}}` escaping is covered
  by both the exact-message test and the byte-for-byte drift pin.
- **`_native` vs `fltk._native` in the message/comment:** deliberate, design-adjudicated
  decision (design.md §3); not re-raised.
- **Systemic gencode-drift gap** (other generated files still rely on manual
  post-gencode `git diff`): acknowledged in-code by the Makefile `gencode` comment
  (Makefile:251-252) and deliberately scoped out by the approved design; not a
  workaround-without-callout.
- **Test coverage of the new surfaces:** positive assertions in both span-registering
  spec shapes, negative (`"LineColPos" not in src`) in both standard-output tests,
  exact pinned message, old unwrapped form asserted absent.
