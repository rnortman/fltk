# Deep correctness review — codegen-rust-lib-boilerplate

Commits reviewed: fltk 7200d9c..25bbfef, clockwork 6ede250..ea34388

## Findings

No correctness findings.

### Verification performed (logic/control/data flow)

- **Generator output vs committed `src/lib.rs`**: traced `RustLibGenerator.generate()`
  line-emission order for `native_spec()` and compared byte-for-byte against the
  committed `git show 25bbfef:src/lib.rs`. They match exactly (imports, blank
  separators, `mod span; mod cst_generated; mod cst_fegen;`, the `use span::{...}`,
  the UNKNOWN_SPAN comment+static, the `#[pymodule]` body, the single blank line
  between the `.expect(...)` once-init and the first `register_submodule`, trailing
  newline). The diff to the old `src/lib.rs` is comment removal + `mod` reordering
  only — semantically identical, compiles equivalently.

- **Blank-line separator logic**
  (`if (register_span_types or unknown_span_static) and spec.submodules`): correct
  for both standard (condition false; body starts directly with registrations, no
  stray leading blank) and native (condition true; one blank before registrations).
  No empty-`submodules` path is reachable from `standard()` (always includes cst)
  or `native_spec()`.

- **`--no-parser` control flow**: single `with_parser` flag drives both the
  `Submodule("parser",...)` append and (transitively) the `mod parser;` /
  registration emission. Omitting one without the other is impossible — the design's
  stated "fails to compile if split" hazard cannot occur.

- **recursion_limit double-injection**: generated standard/native output contains no
  `#![recursion_limit]`; the assembly genrule (rust.bzl:242) prepends it. No double
  attribute. Confirmed by `test_standard_output_no_recursion_limit`.

- **Bazel genrule wiring** (rust.bzl:207-218): `name + "_gen_lib"` target with single
  out `name + "_gen_lib/lib.rs"`; `lib_rs = ":" + name + "_gen_lib"` resolves to that
  single output via `$(location {lib_rs})` at rust.bzl:243. No collision with
  `name + "_crate_root/lib.rs"`. `$@` expands to the single out. `crate_name = name`,
  `--module-name name`, and `#[pymodule] fn <name>` stay consistent (→ correct
  `PyInit_<name>` symbol). `.format(module_name = name)` is a plain Starlark string.

- **Validation**: `_RUST_IDENT_RE = ^[A-Za-z_][A-Za-z0-9_]*$` identical in genparser.py
  and gsm2lib_rs.py. CLI validates `--module-name` then `LibSpec.standard().validate()`
  re-validates inside the generator (redundant, not buggy). Empty/`1bad`/`has space`/
  `a-b` all rejected; `_native` (underscore prefix) accepted.

- **Write-after-generate ordering** (genparser.py): both new commands generate the
  string first, then `write_text` — a generation `ValueError` leaves no partial file.

### Non-correctness observation (out of lane — quality)

- `LibSpec.cfg_python_gate` is declared but never read in `generate()`. Dead config
  field, not a wrong-behavior bug. Defer to quality-reviewer.
