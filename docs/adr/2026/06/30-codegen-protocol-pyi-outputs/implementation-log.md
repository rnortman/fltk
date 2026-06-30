# Implementation log: codegen protocol + .pyi outputs

Design: `design.md` (this directory). Requirements: `requirements.md` (this directory).

## Increment 1 — Python `generate`: protocol becomes opt-in (§2.1)

- `fltk/fegen/genparser.py:146-167`: added `--protocol` boolean flag (default `False`) to the `generate`
  subcommand, between `--protocol-only` and `--verbose`.
- `fltk/fegen/genparser.py:169-179`: updated docstring — protocol module moved out of the
  default-generated list into a "generated only when requested" note.
- `fltk/fegen/genparser.py:225-248`: gated the previously-unconditional protocol write block on
  `if protocol or protocol_only:`. The `--protocol-only` early-return is unchanged; its verbose echo now
  reconstructs the protocol path inline (rather than referencing the now-conditionally-bound
  `shared_cst_protocol`) so the variable is never read possibly-unbound.
- `fltk/fegen/test_genparser.py`: modified `test_generate_protocol_only_matches_full_run` full-run arm to
  pass `--protocol` (else the new default writes no protocol file). Added 3 tests:
  `test_generate_no_protocol_by_default`, `test_generate_protocol_writes_protocol_alongside`,
  `test_generate_protocol_matches_protocol_only`. All 49 module tests pass; ruff + pyright clean.

## Increment 2 — `RustCstGenerator.generate_protocol()` method (§2.2)

- `fltk/fegen/gsm2tree_rs.py:9`: added `import ast` (needed to unparse the protocol AST module).
- `fltk/fegen/gsm2tree_rs.py:426-456`: added `RustCstGenerator.generate_protocol(self) -> str`. Builds a
  dedicated `CstGenerator(grammar=self.grammar, py_module=pyreg.Module(["_protocol"]),
  context=create_default_context())` — a non-empty placeholder `py_module` so the per-rule
  `kind: typing.Literal[NodeKind.*]` discriminant is emitted (not the degraded `kind: object` form that
  the `pyreg.Builtins`-backed `self._py_gen` would produce, §1.2). Returns
  `"# ruff: noqa: N802\n" + ast.unparse(protocol_mod)`, mirroring the Python `generate --protocol` prefix
  (genparser.py:253). `self._py_gen` is left untouched.
- `tests/test_gsm2tree_rs.py:1110-1151`: added `TestGenerateProtocol` (4 tests): noqa header prefix,
  parses as valid Python, Literal discriminant present (degraded `kind: object` absent), deterministic
  across two generator instances. All pass; `gsm2tree_rs.py` ruff + pyright clean.
- Note: the 5 pyright errors reported when checking `tests/test_gsm2tree_rs.py` (Sequence[Rule] `+`
  operator and Grammar/protocol type mismatches) pre-exist on the base commit and lie outside the added
  region; not introduced here.
- The cross-path byte-identity guardrail (Rust `generate_protocol` vs Python `generate --protocol`) is a
  CLI-level test deferred to the `--protocol-output` wiring increment (§2.2, §4).

## Increment 3 — `gen-rust-cst` `--protocol-output` CLI wiring (§2.2)

- `fltk/fegen/genparser.py:350-377`: added `--protocol-output PATH` option (default `None`) to
  `gen_rust_cst`, after `--pyi-output`.
- `fltk/fegen/genparser.py:399-411`: added up-front validation `--protocol-output requires
  --protocol-module` (next to the existing `--pyi-output requires --protocol-module` check); docstring
  gains the `--protocol-output` note + example.
- `fltk/fegen/genparser.py:419-439`: generate protocol text via `gen.generate_protocol()` (increment 2)
  inside the pre-write try block, then write order `.rs` → protocol `.py` (`--protocol-output`) → `.pyi`,
  so a generation error leaves no partial files; protocol write reuses `_write_output_file` with the
  `"protocol module"` artifact label.
- Did NOT factor a shared `render_protocol_text` helper (design §2.2 "optionally"): `generate_protocol()`
  already mirrors the Python path's `"# ruff: noqa: N802\n" + ast.unparse(...)` sequence and the
  cross-path byte-identity test is the guardrail, so the refactor would add indirection without value.
- `fltk/fegen/test_genparser.py:534-678`: 4 tests — `--protocol-output` without `--protocol-module`
  rejected (nothing written); `--protocol-module X --protocol-output P` writes protocol `.py` + `.pyi` +
  `.rs`; cross-path byte-identity vs `generate --protocol` (with Literal-discriminant / no-`kind: object`
  guard, closing the increment-2 deferral); `.rs` unchanged with `--protocol-output`. 53 module tests
  pass; ruff + ruff format + pyright clean on genparser.py.

## Increment 4 — `render_stub_package_init` helper in `gsm2lib_rs.py` (§2.2)

- `fltk/fegen/gsm2lib_rs.py:13`: added `from collections.abc import Sequence` import.
- `fltk/fegen/gsm2lib_rs.py:26-67`: added grammar-independent `render_stub_package_init(extension_name,
  submodules) -> str` after `_validate_rust_ident`. Validates `extension_name` and each submodule entry
  via the module's existing `_validate_rust_ident`, then renders comment-only marker text (4 `#` lines,
  trailing newline) that names the extension and the comma-joined submodule list and preserves the
  "recognized stub package; top-level module exports nothing directly, only the listed submodules"
  explanation the in-tree markers carry. Pure comments + newline → byte-stable under ruff.
- Deviation (minor): the helper also rejects an empty `submodules` list with a `ValueError` ("requires
  at least one submodule"); design §2.2 specifies emptiness rejection only at the CLI layer, but an
  empty list would render a malformed "only submodules ." marker, so the guard is pushed into the
  shared helper.
- `fltk/fegen/test_gsm2lib_rs.py:5,9`: added `import ast` + `render_stub_package_init` to the import.
- `fltk/fegen/test_gsm2lib_rs.py:359-415`: 7 tests (§5) — names extension + each submodule; comment-only
  and parses as an empty `ast` module; newline-terminated; idempotent re-render; rejects bad extension
  name / bad submodule entry / empty submodules. 49 module tests pass; ruff + ruff format + pyright clean
  on both files.

## Increment 5 — `gen-rust-cst` stub-package `__init__.pyi` marker CLI wiring (§2.2)

- `fltk/fegen/genparser.py:366-401`: added `--init-pyi-output` / `--extension-name` / `--submodules`
  options (all default `None`) to `gen_rust_cst`, after `--protocol-output`; docstring gains a marker
  note + example.
- `fltk/fegen/genparser.py:490-516`: added module-level shared helper
  `_render_init_pyi(init_pyi_output, extension_name, submodules) -> str | None` next to
  `_validate_protocol_module`. Returns `None` when `--init-pyi-output` is unset; else CLI-errors if
  `--extension-name`/`--submodules` missing, splits the CSV (`name.strip()` per entry, no empties
  dropped — a trailing comma yields an empty entry that `render_stub_package_init` rejects), and renders
  via `gsm2lib_rs.render_stub_package_init` (increment 4), surfacing its `ValueError` as a CLI error.
  Placed as a shared helper because `gen_rust_unparser` reuses it in a later increment.
- `fltk/fegen/genparser.py:447-449`: call `_render_init_pyi(...)` up front (before grammar parse) so a
  malformed marker never reaches disk; `genparser.py:478-479`: write the marker via `_write_output_file`
  with the `"stub-package __init__.pyi"` artifact label after the `.rs`/protocol/`.pyi` writes.
- `fltk/fegen/test_genparser.py:667-799`: 4 tests — marker written + comment-only (parses to empty
  module) + independent of `--protocol-module`; marker + cst `.pyi` both written when `--protocol-module`
  given; `--init-pyi-output` without `--submodules` rejected (nothing written); malformed submodule entry
  rejected before any write. 57 module tests pass; ruff + ruff format + pyright clean on
  genparser.py/test_genparser.py.

## Increment 6 — `gen-rust-unparser` stub-package `__init__.pyi` marker CLI wiring (§2.2 / §2.7)

- `fltk/fegen/genparser.py:627-657`: added `--init-pyi-output` / `--extension-name` / `--submodules`
  options (all default `None`) to `gen_rust_unparser`, after `--pyi-output`, with help text mirroring the
  `gen_rust_cst` options; docstring gains a marker note + example.
- `fltk/fegen/genparser.py:694-696`: call the existing shared `_render_init_pyi(...)` helper (increment 5)
  up front — after `--protocol-module` validation, before the grammar parse — so a malformed marker never
  reaches disk.
- `fltk/fegen/genparser.py:710-711`: write the marker via `_write_output_file` with the
  `"stub-package __init__.pyi"` artifact label after the `.rs`/`.pyi` writes.
- Reused increment 5's `_render_init_pyi` helper and `gsm2lib_rs.render_stub_package_init` (increment 4)
  unchanged — no new helper; the unparser path is pure wiring over the already-tested CLI machinery.
- `fltk/fegen/test_genparser.py:1142-1264`: 4 tests mirroring the gen-rust-cst marker tests — marker
  written + comment-only (parses to empty module) + independent of `--protocol-module` (the §2.7 fixture
  routing); marker + unparser `.pyi` both written when `--protocol-module` given; `--init-pyi-output`
  without `--submodules` rejected (nothing written); malformed submodule entry rejected before any write.
  61 module tests pass; ruff + ruff format + pyright clean on genparser.py/test_genparser.py.

## Increment 7 — Bazel `generate_parser` opt-in protocol attr (§2.4)

- `rules.bzl:25-30`: in `_genparser_impl`, when `ctx.attr.protocol` is set, add `--protocol` to the
  `generate` action args and `declare_file({base_name}_cst_protocol.py)`, appending it to `outputs`
  (and thus `DefaultInfo`). When unset, nothing is declared/passed (status quo, additive opt-in).
- `rules.bzl:67-70`: added the `protocol` bool attr (default `False`) to the `generate_parser` rule.
- No test: per design §5 there is no Bazel-build test harness in the suite; the rule is simple wiring
  over the already-tested `--protocol` CLI behavior (increment 1) and is validated via `make gencode`
  drift detection. buildifier not installed in this environment, so no .bzl lint was run.

## Increment 8 — Bazel `generate_rust_parser` protocol/.pyi exposure (§2.5)

- `rust.bzl:113-167`: in `_generate_rust_parser_impl`, read the two new attrs and `fail()` at analysis
  time when `generate_protocol` is set but `protocol_module` is empty (mirrors the CLI
  `--protocol-output requires --protocol-module` check). Accumulate gen-rust-cst outputs in a
  `cst_outputs` list (starts `[cst_out]`). When `protocol_module` is non-empty, declare `{name}/cst.pyi`
  + `{name}/__init__.pyi` and add `--protocol-module {protocol_module} --pyi-output {name}/cst.pyi
  --init-pyi-output {name}/__init__.pyi --extension-name {name} --submodules cst,parser` to the one
  gen-rust-cst action (so `{name}/` is a complete stub package via the dogfooded `--init-pyi-output`
  path, not `ctx.actions.write`). When `generate_protocol` is also set, declare `{name}/cst_protocol.py`
  and add `--protocol-output {name}/cst_protocol.py`. `gen-rust-parser` action untouched.
- `rust.bzl:170` (return): `DefaultInfo(files = depset(cst_outputs + [parser_out]))` so the conditional
  artifacts flow into `DefaultInfo`.
- `rust.bzl:202-230`: added `protocol_module` (string, default "") + `generate_protocol` (bool, default
  False) attrs with doc strings; updated the rule doc to list the conditional `cst.pyi` / `__init__.pyi`
  / `cst_protocol.py` outputs and the opt-in example.
- No test: per design §5 there is no Bazel-build test harness; this is wiring over the already-tested
  `--protocol-module` / `--pyi-output` / `--protocol-output` / `--init-pyi-output` CLI behavior
  (increments 3, 5) and is validated by `make gencode` drift detection. buildifier is not installed in
  this environment; validated rust.bzl via a Python-syntax smoke-check (Starlark subset), which passed.

## Increment 9 — Makefile `gencode`: add `--protocol` to the five Python `generate` invocations (§2.1/§2.7)

- `Makefile:256,260,264,268,272`: added `--protocol` to the five Python `generate` calls (fltk,
  bootstrap, toy, unparsefmt, regex) so the committed `*_cst_protocol.py` files continue to regenerate
  now that increment 1 flipped the `generate` default to protocol-off. The `--protocol-only` fixture
  invocation (`Makefile:301-303`) is unchanged.
- Verified no drift: ran the five `generate --protocol` calls + the exact `gencode` ruff fix sequence
  (`ruff check --fix .` → `ruff format .` → `ruff check --fix .`) from the repo root; the regenerated
  `*_cst.py`, `*_cst_protocol.py`, `*_parser.py`, `*_trivia_parser.py` corpus is byte-identical to the
  committed files (`git status` shows only Makefile + this log modified). Confirms the protocol bytes are
  unchanged by the flag flip.

## Increment 10 — Makefile: dogfood the `fegen_rust_cst/__init__.pyi` marker (§2.7)

- `Makefile:283-287`: appended `--init-pyi-output fltk/_stubs/fegen_rust_cst/__init__.pyi
  --extension-name fegen_rust_cst --submodules cst,parser,unparser` to the `EXTRA_ARGS` of the existing
  `fegen` `gen-rust-cst` invocation (which already writes `cst.pyi`); updated the preceding comment to
  note the marker output.
- `fltk/_stubs/fegen_rust_cst/__init__.pyi`: regenerated through the dogfooded `--init-pyi-output`
  generator/CLI path (increment 5). Now generator-derived comment-only text that correctly lists
  `cst, parser, unparser` — fixing the pre-existing hand-authored staleness (was "only submodules cst
  and parser", though `crates/fegen-rust/src/lib.rs` also registers `unparser`). Parses to an empty
  `ast` module (body len 0).
- Drift verified: ran the exact fegen `gen-rust-cst` invocation + the `gencode` ruff fix sequence
  (`ruff check --fix .` → `ruff format .` → `ruff check --fix .`); `cst.rs` and `cst.pyi` regenerate
  byte-identical to committed (cst.pyi's raw unformatted generator form normalizes back under ruff),
  so the only net generated change is the marker. `git status` shows only Makefile, this log, and the
  regenerated marker.
- `tests/test_rust_unparser_pyi.py` (5 tests incl. `test_consumer_pyright_clean`) pass — the
  regenerated marker keeps fegen_rust_cst stub-package resolution working. No test asserts the fegen
  marker by content (grep-confirmed); the `make gencode` drift gate covers it.

## Increment 11 — Makefile: dogfood the `rust_parser_fixture/__init__.pyi` marker (§2.7)

- `Makefile:306-311`: appended `--init-pyi-output fltk/_stubs/rust_parser_fixture/__init__.pyi
  --extension-name rust_parser_fixture --submodules
  cst,parser,unparser,unparser_default,collision_cst,collision_parser` to the `EXTRA_ARGS` of the
  existing fixture `gen-rust-unparser` invocation (which already writes `unparser.pyi`); updated the
  preceding comment to note the marker now rides the unparser path (the fixture's `gen-rust-cst` writes
  no `cst.pyi`, Makefile:298, left unchanged — no new `cst.pyi` introduced).
- `fltk/_stubs/rust_parser_fixture/__init__.pyi`: regenerated through the dogfooded `--init-pyi-output`
  generator/CLI path (increment 6). Now generator-derived comment-only text listing
  `cst, parser, unparser, unparser_default, collision_cst, collision_parser`. Parses to an empty `ast`
  module.
- Drift verified: ran the exact fixture `gen-rust-unparser` invocation + the full `gencode` ruff fix
  sequence (`ruff check --fix .` → `ruff format .` → `ruff check --fix .`). `unparser.rs`/`unparser.pyi`
  regenerate byte-identical to committed (the wrapped `.pyi` signatures the generator emits normalize
  back to single-line under ruff's stub formatting), so the only net generated change is the marker.
  `git status` shows only Makefile, this log, and the regenerated marker.
- `make check` passes (lint, format-check, typecheck, test, all cargo lanes, cargo-deny) — final
  increment gate green. `tests/test_rust_unparser_pyi.py::test_committed_stub_artifacts_exist` (asserts
  the fixture marker is present) stays green; no test asserts the marker by content, the `make gencode`
  drift gate covers it.
