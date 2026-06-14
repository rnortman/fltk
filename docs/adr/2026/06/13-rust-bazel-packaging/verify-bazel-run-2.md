# Bazel POC Verification Run 2

**Verdict: GREEN**

Date: 2026-06-13

## Context

Confirming the FLTK-Rust / Clockwork Bazel POC still builds GREEN after two changes landed:

1. fltk generators now fully-qualify all pyo3-prelude type references.
2. `#![recursion_limit]` moved from Clockwork's hand-written `lib.rs` into fltk's `fltk_pyo3_cdylib` macro.

## Repos / HEADs

- fltk: `/home/rnortman/src/fltk` — HEAD `9657025`
- Clockwork: `/home/rnortman/tps/clockwork` — HEAD `6717614` (temporary `local_path_override` pointing at the local fltk checkout, so it builds against fltk's working tree)

Both HEADs confirmed at run time.

## Per-target results

| Target | Result |
|---|---|
| `//clockwork/dsl:clockwork_rust_roundtrip_test` | PASS — 1 of 1 test passes |
| `@@fltk+//:bootstrap_rust_srcs` | PASS — build completed successfully |

### `//clockwork/dsl:clockwork_rust_roundtrip_test`

```
INFO: Build completed successfully, 9 total actions
Executed 1 out of 1 test: 1 test passes.
```

The `clockwork_native_cdylib` (and the fltk `native` cdylib it depends on) compiled
cleanly — no recursion_limit errors, no duplicate/missing crate attributes, no pyo3
symbol collisions. Elapsed ~76s (cold-ish Rust compile of the cdylibs).

### `@@fltk+//:bootstrap_rust_srcs`

```
Target @@fltk+//:bootstrap_rust_srcs up-to-date:
  bazel-bin/external/fltk+/bootstrap_rust_srcs/cst.rs
  bazel-bin/external/fltk+/bootstrap_rust_srcs/parser.rs
INFO: Build completed successfully, 3 total actions
```

## Failure detail

None. Both targets built/passed.

## Notes (non-blocking, pre-existing)

- `SyntaxWarning: invalid escape sequence` emitted from the generated `genparser`
  tool — pre-existing, unrelated to the two changes under test.
- `UserWarning: fltk._native could not be loaded; falling back to pure-Python Span
  backend` during the generator step — expected; the generator host process runs
  without the compiled native extension and falls back to pure Python. Does not
  affect the Rust cdylib build/test path.

No fixes were made (verification-only run, as instructed).
