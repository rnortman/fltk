# Design review findings: registry GC/eviction/ABA tests

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Verification performed: all cited registry.rs line ranges confirmed (`crates/fltk-cst-core/src/registry.rs` — ABA claim 19-22, `register_if_absent` 66-74, caller contract 87-91, `force_register` 92-97, unreachable arm 120-125, TODO 128-130, `snapshot` 136-142, `#[cfg(test)]` PyDict import 29-30). `py_new` → `force_register` confirmed (`tests/rust_cst_fixture/src/cst.rs:406` and per-class repeats). Fixture is a standalone workspace (`tests/rust_cst_fixture/Cargo.toml:3`), so the per-cdylib `CANONICAL_REGISTRY` argument and the feature-unification claim hold. `python = ["fltk-cst-core/python"]` feature exists as described. Generated API names used in §3 (`Entry`, `Identifier`, `append_key`, `child_key`, `children`, `append`) all exist (cst.rs:987, 1326, 1362, 4844-4861; test_phase4_rust_fixture.py:383-505). importorskip preamble is at test_phase4_rust_fixture.py:28-31 as cited. `TODO.md` `registry-unit-tests` entry heading at line 31. Requirements coverage: all four request gaps, the stress variant, TODO resolution, and all constraints map to design sections; no scope creep found. The cfg-gate + feature plumbing is minimal and clearly test-only as required.

## design-1

Section 6 (Verification): "`make check` clean (includes `cargo-check`/`clippy` over the modified `fltk-cst-core`)."

What's wrong: `make check` includes a `cargo-test` step (`Makefile:9-10,46-47`) that runs workspace `cargo test -q`; `fltk-cst-core` is a root-workspace member (`Cargo.toml:2`). Verified live on this machine: `cargo test -p fltk-cst-core --no-run` fails with `rust-lld: error: unable to find library -lpython3.10` (`/usr/lib64` has only `libpython3.10.so.1.0`, no unversioned symlink). Design §1 itself cites this link failure (sourced from exploration §2), then §6 asserts a clean `make check` without reconciling the two.

Consequence: the stated verification gate cannot pass on this machine for reasons unrelated to the change; the implementer will either misattribute the failure to their work or silently skip the gate.

Suggested fix: in §6, note the pre-existing dev-symlink prerequisite for the `cargo-test` step and enumerate the steps that must pass regardless (`make build-test-user-ext`, `uv run pytest`, `make fix`, `cargo clippy` lanes), or instruct fixing the symlink first.

## design-2

Section 3 (Tests): tests construct `Entry()` / `Identifier()` but the design never says how the new file obtains the classes.

What's wrong: the referenced sibling file gets them via module-level `parse_grammar_file` + `generate_parser(..., rust_cst_module="phase4_roundtrip_cst")` plumbing (`tests/test_phase4_rust_fixture.py:48-57`) — exactly the kind of module-level registry-occupying state the design's own delta-assertion rationale (§2.3) treats as hostile. The classes are directly importable: `register_classes` adds them to the extension module with Python names `Entry`, `Identifier`, etc. (`tests/rust_cst_fixture/src/cst.rs:4844-4861`), and the importorskip return value is the module object.

Consequence: an implementer copying the sibling file's full preamble imports `fltk.plumbing` and adds parser-generation module state to the GC-sensitive test module — unnecessary registry occupancy and import weight in the one file designed to avoid it.

Suggested fix: one sentence in §2.3: classes are taken as attributes of the importorskip'd `phase4_roundtrip_cst` module; no `fltk.plumbing` / `generate_parser` machinery in this file.

## design-3

Section 2.2 vs 2.3: wrapper doc comments promise "synthetic low addresses (< 4096)" while the allocator is an unbounded module-level `itertools.count(1)`.

What's wrong: nothing enforces the documented bound; the two sections state different contracts for the same addresses ("< 4096" vs "1..N sub-page").

Consequence: minor — the doc contract silently drifts false if direct tests ever consume ≥ 4096 synthetic addresses; safety is unaffected in practice (heap Arc addresses are far above either bound), but the safety argument as written stops matching the code.

Suggested fix: phrase the doc contract as "small integers far below any heap address; weak eviction cleans them up regardless," or assert `addr < 4096` in the allocator helper.
