# Quality review — demote-cst-spike

Commit reviewed: be08c47

---

## quality-1

**File:line** `tests/rust_poc_cst/src/spike_tests.rs`, module-level doc comment, line 4.

**Issue** The module-level doc comment still says:

> These tests must pass under `cargo test -p fltk-cst-spike` (python feature off).

`fltk-cst-spike` is deleted. The correct invocation is now
`cargo test --manifest-path tests/rust_poc_cst/Cargo.toml --no-default-features`.

**Consequence** The next person who edits these tests, or who needs to run just the spike suite
in isolation, follows a dead command and gets a confusing cargo error. The mismatch will also
accumulate as the comment drifts further from reality with each future rename.

**Fix** Replace the stale crate reference with the current invocation:

```
/// These tests must pass under
/// `cargo test --manifest-path tests/rust_poc_cst/Cargo.toml --no-default-features`
/// (python feature off).
```

---

## quality-2

**File:line** `Makefile`, `cargo-clippy-no-python` target (HEAD line ~142–147); old target also
had `cargo clippy -q -p fltk-cst-spike --features python -- -D warnings`.

**Issue** Before this change, `cargo-clippy-no-python` explicitly clippy-checked the spike crate
with `--features python` enabled (python-on code paths, pyo3 bindings). After the migration those
paths live in `tests/rust_poc_cst` but `cargo-clippy-no-python` only checks
`tests/rust_poc_cst/Cargo.toml --no-default-features`. The python-on clippy of `rust_poc_cst` is
handled by `cargo-clippy` (which runs with default features = `extension-module = python`), so
coverage is not actually lost — but the pre-existing python-on check was inside the
`cargo-clippy-no-python` target for a reason (the comment there is about feature isolation, not
the direction of the flag). The new arrangement silently relies on `cargo-clippy` picking up the
python-on check, and the `cargo-clippy-no-python` comment no longer mentions this asymmetry.

**Consequence** Anyone auditing `cargo-clippy-no-python` will see only the python-off side and
may incorrectly conclude that python-on clippy for `rust_poc_cst` is missing entirely and add a
redundant or wrong invocation. Over time, the implicit dependency between `cargo-clippy` and
`cargo-clippy-no-python` for full coverage of `rust_poc_cst` becomes invisible.

**Fix** Add a comment to `cargo-clippy-no-python` (after the `rust_poc_cst` line) noting that
the python-on path is covered by `cargo-clippy` via default features, to make the coverage split
explicit:

```makefile
	# python-on clippy for rust_poc_cst is covered by cargo-clippy (default features = extension-module)
```
