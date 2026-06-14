# Efficiency review — final (rust-bazel-packaging)

Commits reviewed: fltk fafa6d7..9657025, Clockwork ece332a..6717614.
Scope per task: efficiency only. KNOWN/INTENTIONAL items (Clockwork
local_path_override + TODO(fltk-pin-finalize); hand-written cdylib lib.rs) not
flagged.

## Surface of the change

The non-doc code changes are three kinds, none of which sit on a runtime hot
path:

1. **Generator string-template edits** (`gsm2tree_rs.py`, `gsm2parser_rs.py`):
   qualify pyo3 type references (`PyAny` → `pyo3::PyAny`, etc.) and replace the
   `use pyo3::prelude::*` glob with an explicit import list. These build the
   emitted Rust source text once per codegen invocation. They add a fixed,
   constant number of reserved-name dict entries and one seeded-claims dict
   comprehension at `RustCstGenerator.__init__` — O(reserved-set size), a small
   constant. The module-load `_bad_reserved` check runs once at import over the
   reserved set (constant). No new per-rule or per-node nested work; the
   qualifications are flat substitutions in already-existing emission sites.

2. **Bazel build wiring** (`BUILD.bazel`, `crates/*/BUILD.bazel`, `rust.bzl`):
   `rust_library` / `rust_shared_library` / genrule targets. Build-time, cached
   by Bazel's action cache. The `_assemble_crate` genrule shell loop iterates
   exactly two generated files (cst.rs, parser.rs). The two codegen actions in
   `generate_rust_parser` are independent and already split into two
   `ctx.actions.run` calls — Bazel schedules them concurrently; no forced
   serialization.

3. **Clockwork test** (`clockwork_rust_roundtrip_test.py`): one parse of a
   16-char source string. Trivial.

## Findings

No findings.

Rationale notes (not findings, just why nothing was flagged):

- The generated `cst.rs` preamble carries a large block of explanatory comments
  now. These are emitted into generated source, but generated-code comment
  volume is not a runtime cost and the file is produced once per build; rustc
  discards comments at lex. Not an efficiency issue.
- `generate_rust_parser` re-runs `genparser` (a Python process startup) twice
  per grammar (once for cst, once for parser) rather than once with a shared
  `--output-dir`. This is forced by the CLI surface (the Rust subcommands take a
  positional output and have no `--output-dir`; design §3.4), the two actions
  run concurrently under Bazel, and each is cached. The duplicated interpreter
  startup is a fixed, small, build-time-only cost paid once per grammar change,
  not per build (action cache) and not at runtime. Not worth a finding given the
  CLI constraint, but noted for the record.
- No unbounded structures, no listener/handle leaks, no repeated I/O, no
  no-op-update loops, no broad reads-that-could-be-slices in the changed code.
