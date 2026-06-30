# Exploration: codegen protocol + .pyi outputs

Scope: CLI subcommands, Python/Rust generators, Bazel rules, committed artifacts, and tests relevant to
(1) making Rust CST generation automatically emit `.pyi` and expose it in the Bazel Rust rule, and
(2) giving both `generate_parser` (Python Bazel rule) and `gen-rust-cst` (Rust Bazel rule) the ability
to produce the protocol module output, opt-in, off by default for each.

---

## 1. CLI surface — `fltk/fegen/genparser.py`

### `generate` (Python path) — lines 127–288

Flags: `grammar_file` (positional), `base_name` (positional), `cst_module_name` (positional),
`--output-dir / -o`, `--trivia-only`, `--no-trivia-only`, `--protocol-only`, `--verbose`.

**No `--protocol-module` flag exists on `generate`.**

Output-file behaviour:

- `{base_name}_cst_protocol.py` is **ALWAYS written**, unconditionally, even when `--trivia-only` or
  `--no-trivia-only` is set. The write happens at lines 225–242, before any parser emission, and is NOT
  gated on a flag.
- `{base_name}_cst.py` is skipped only under `--protocol-only` (lines 210–224).
- `{base_name}_parser.py` is skipped under `--trivia-only` or `--protocol-only`.
- `{base_name}_trivia_parser.py` is skipped under `--no-trivia-only` or `--protocol-only`.

The `--protocol-only` flag skips CST and parsers but still writes the protocol module:

```python
# genparser.py:225-248
shared_cst_protocol = output_dir / f"{base_name}_cst_protocol.py"
...
protocol_text = "# ruff: noqa: N802\n" + ast.unparse(protocol_mod)
...
if protocol_only:
    ...
    return
```

The protocol module emits the `# ruff: noqa: N802` prefix (line 236); this is the only file-level
suppression, asserted by `tests/test_clean_protocol_consumer_api.py:330-345`.

### `gen-rust-cst` — lines 317–408

Flags: `grammar_file` (positional), `output_file` (positional), `--protocol-module` (optional str),
`--pyi-output` (optional Path).

- Without `--protocol-module`: only the `.rs` is written; no `.pyi` emitted (line 397).
- With `--protocol-module`: `.pyi` is also generated via `gen.generate_pyi(protocol_module)` and written
  to `pyi_output` or `output_file.with_suffix(".pyi")` (lines 397-408).
- `--pyi-output` without `--protocol-module` is rejected at line 382–384.
- `--protocol-module` is validated as a dotted Python identifier path at lines 426–441
  (`_PROTOCOL_MODULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")`).
- The `.rs` output is **identical** with or without `--protocol-module` (tested by
  `test_gen_rust_cst_rs_unchanged_with_protocol_module` in `fltk/fegen/test_genparser.py:422`).
- Both `.pyi` and `.rs` are generated before either file is opened (lines 395-408), so a generation
  error leaves no partial files.

### `gen-rust-parser` — lines 444–467

Flags: `grammar_file` (positional), `output_file` (positional), `--cst-mod-path` (default `super::cst`).

No `--protocol-module`, no `--pyi-output`. Only writes the `.rs`.

### `gen-rust-unparser` — lines 470–580

Flags: `grammar_file` (positional), `output_file` (positional), `--cst-mod-path`, `--format-config`,
`--protocol-module` (optional), `--pyi-output` (optional).

Identical opt-in pattern to `gen-rust-cst`: without `--protocol-module` no `.pyi`; with it, `.pyi` is
emitted from `gen.generate_pyi(protocol_module)` at lines 569-580.

### `gen-rust-lib` — lines 583–664

Flags: `output_file`, `--module-name`, `--no-parser`, `--unparser`, `--no-cst`,
`--register-span-types`, `--unknown-span-static`.

No grammar file, no protocol/pyi capability at all.

---

## 2. Generators

### `gsm2tree.py:CstGenerator.gen_protocol_module()` — line 719

Signature: `def gen_protocol_module(self) -> ast.Module`

Takes no external inputs beyond `self.grammar`, `self.py_module`, `self.context`, and `self.rule_models`
(populated in `__init__`). Emits:

- `from __future__ import annotations` (line 723)
- `import enum`, `import typing`, `import fltk.fegen.pyrt.terminalsrc` (lines 724-726)
- `import fltk.fegen.pyrt.span_protocol` under `TYPE_CHECKING` (lines 727-740)
- A protocol-local `NodeKind` enum + canonical-name assignments (lines 747-749)
- `_ProtocolLabelMember` sentinel class (line 751)
- One `typing.Protocol` class per grammar rule (lines 753-757)
- A `Span` protocol class (line 759)
- A `CstModule` protocol class (line 760)
- An `__all__` list (lines 763-796)

The generated `CstModule` protocol has one `@property` per rule returning `type[NodeName]` (lines
988-1003).

### `gsm2tree.py:CstGenerator.gen_py_module()` — line 171

Generates the concrete CST dataclass module. References `fltk.fegen.pyrt.span_protocol` under
`TYPE_CHECKING` (lines 190-201), and includes a runtime `_get_native_span_type()` helper for lazy native
Span resolution (lines 212-221).

### `gsm2tree_rs.py:RustCstGenerator.generate_pyi(protocol_module: str)` — line 321

Signature: `def generate_pyi(self, protocol_module: str) -> str`

Inputs:
- `protocol_module`: dotted Python import path (e.g. `"fltk.fegen.fltk_cst_protocol"`), interpolated as
  `import {protocol_module} as _proto` at line 345.
- Internally reads `self._rule_info()` (grammar-derived) and `self._py_gen.rule_models` (populated in
  `__init__`).

Header emitted (lines 337-349):
```python
# ruff: noqa: N802
from __future__ import annotations
import typing
import fltk.fegen.pyrt.span_protocol
import {protocol_module} as _proto

NodeKind = _proto.NodeKind
```

Per-rule class stubs reference `_proto.{ClassName}`, `_proto.NodeKind.{MEMBER}`, and
`_proto.{ClassName}.Label` (lines 355-416). The stub file does NOT import `fltk._native`,
`fltk.fegen.pyrt.terminalsrc`, or the span selector (asserted by
`tests/test_gsm2tree_rs.py:1153-1164`).

`generate_pyi` is independent of `generate()` — calling one does not affect the other. Both can be called
on the same instance in any order.

`RustCstGenerator.__init__` accepts a **raw** grammar (not trivia-processed) and applies trivia
internally at lines 176-177:
```python
grammar_with_trivia = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
```

### `gsm2unparser_rs.py:RustUnparserGenerator.generate_pyi(protocol_module: str)` — line 95

Signature: `def generate_pyi(self, protocol_module: str) -> str`

Emits a stub for `Unparser` (with `unparse_{rule}(node, max_width, indent_width) -> str | None` and
`unparse_{rule}_doc(node) -> Doc | None` per rule) and `Doc` (with `render` and `__repr__`).

Header (lines 121-128):
```python
from __future__ import annotations
import {protocol_module} as _proto
```

Each `unparse_{rule}` method's `node` parameter is typed `_proto.{ClassName}` (lines 148-153). Does NOT
import `typing` (uses `str | None` PEP 604 form to avoid a spurious F401 after `ruff --fix`, comment at
line 123).

The `Doc` class stub is emitted verbatim into every per-grammar `.pyi` (TODO(unparser-pyi-doc-stub-shared)
in `TODO.md`).

---

## 3. Bazel Python rule — `rules.bzl`

### `generate_parser` rule — lines 41–72

Attrs:
- `src`: label, single file, mandatory — the `.fltkg` grammar file.
- `base_name`: string, mandatory — base name for output files.
- `cst_mod_path`: string, mandatory — base module name for CST classes.
- `trivia_only`: bool, default False.
- `no_trivia_only`: bool, default False.
- `_gen_tool`: label, default `Label(":genparser")`, exec cfg.

`ctx.actions.declare_file(...)` calls:
- `cst_file = ctx.actions.declare_file(ctx.attr.base_name + "_cst.py")` (line 7) — always.
- `parser_file = ctx.actions.declare_file(ctx.attr.base_name + "_parser.py")` (line 22) — unless `trivia_only`.
- `trivia_parser_file = ctx.actions.declare_file(ctx.attr.base_name + "_trivia_parser.py")` (line 26) — unless `no_trivia_only`.

**`{base_name}_cst_protocol.py` is NOT declared as an output.** The CLI always writes it alongside the
CST (lines 225-242 of genparser.py), but because Bazel doesn't declare it, Bazel cannot track or expose
it as an artifact.

Arg construction (lines 1-15): passes `generate`, `src`, `base_name`, `cst_mod_path`, `--output-dir`,
and optionally `--trivia-only` / `--no-trivia-only`. No `--protocol-only`, `--protocol-module`, or
`--pyi-output` flag is ever passed.

To slot in a protocol output, a `protocol_only` attr and corresponding `ctx.actions.declare_file(ctx.attr.base_name + "_cst_protocol.py")` and `args.add("--protocol-only")` would need to be added. Alternatively, declaring the protocol file as a normal output alongside the CST (since the CLI always writes it) would require no new flag but would always expose it.

---

## 4. Bazel Rust rules — `rust.bzl`

### `generate_rust_parser` rule — lines 100–196

Attrs: `src` (grammar label), `cst_mod_path` (string, default `"super::cst"`), `_gen_tool`.

Two actions:
1. `gen-rust-cst {grammar} {cst_out}` — declares `{name}/cst.rs` (line 116), passes NO
   `--protocol-module`, NO `--pyi-output`.
2. `gen-rust-parser {grammar} {parser_out} --cst-mod-path {cst_mod_path}` — declares `{name}/parser.rs`
   (line 117).

Outputs declared: `[cst_out, parser_out]` (line 149). No `.pyi`, no protocol file.

To add `.pyi` emission, the rule needs:
- A new `protocol_module` string attr (optional, empty default).
- A `pyi_output` file declaration (e.g. `{name}/cst.pyi`).
- The `gen-rust-cst` action gaining `--protocol-module {protocol_module}` and `--pyi-output {pyi_out}`
  when `protocol_module` is non-empty.
- The `.pyi` added to the `DefaultInfo` outputs.

### `generate_rust_lib` rule — lines 23–98

One action: `gen-rust-lib {lib_out} --module-name {module_name} [flags...]`. No grammar, no pyi.
Output: `{name}/lib.rs`.

### `fltk_pyo3_cdylib` macro — lines 200–391

Step 1 (assembly genrule, lines 295–335): declares three outputs:
```python
crate_lib_rs = name + "_crate_root/lib.rs"
crate_cst_rs = name + "_crate_root/cst.rs"
crate_parser_rs = name + "_crate_root/parser.rs"
```
The genrule copies all files from `rs_srcs` by basename into the crate gendir (line 325). It then
asserts `cst.rs` and `parser.rs` exist (lines 327-328 — `test -f` guards).

`TODO(bazel-lib-rs-no-cst)` at `rust.bzl:311-315` notes the unconditional declaration of `cst.rs` and
`parser.rs` as required outputs.

No `.pyi` is declared or copied by the assembly genrule. The macro has no `protocol_module` or
`pyi_output` parameter.

Step 2 (cdylib): `rust_shared_library` with `crate_features = ["extension-module", "python"] + crate_features`, deps `fltk-cst-core`, `fltk-parser-core`, `pyo3`.

Step 3 (ABI3 rename): `lib{name}.so` → `{name}.abi3.so`.

Step 4 (py_library): wraps `.abi3.so`, carries `@fltk//:native_py` as dep.

There is **no `generate_rust_unparser` rule** in `rust.bzl`.

---

## 5. Makefile gencode canonical invocations — `Makefile:253–324`

Python path (lines 256–274) — unconditional protocol output (CLI always writes it):
```makefile
uv run python -m fltk.fegen.genparser generate \
    fltk/fegen/fegen.fltkg fltk fltk.fegen.fltk_cst \
    --output-dir fltk/fegen
```
Produces: `fltk_cst.py`, `fltk_cst_protocol.py`, `fltk_parser.py`, `fltk_trivia_parser.py`.

Similarly for `bootstrap`, `toy`, `unparsefmt`, `regex` grammars — all under their respective `--output-dir` directories with no extra flags.

Rust CST with `.pyi` (Makefile:283–285):
```makefile
$(MAKE) gen-rust-cst GRAMMAR=fltk/fegen/fegen.fltkg RS_OUT=crates/fegen-rust/src/cst.rs \
    EXTRA_ARGS="--protocol-module fltk.fegen.fltk_cst_protocol \
                --pyi-output fltk/_stubs/fegen_rust_cst/cst.pyi"
```

Rust unparser for fegen with `.pyi` (Makefile:290–294):
```makefile
$(MAKE) gen-rust-unparser GRAMMAR=fltk/fegen/fegen.fltkg \
    RS_OUT=crates/fegen-rust/src/unparser.rs \
    EXTRA_ARGS="--format-config fltk/fegen/fegen.fltkfmt \
                --protocol-module fltk.fegen.fltk_cst_protocol \
                --pyi-output fltk/_stubs/fegen_rust_cst/unparser.pyi"
```

Protocol-only for fixture (Makefile:299–303):
```makefile
uv run python -m fltk.fegen.genparser generate --protocol-only \
    fltk/fegen/test_data/rust_parser_fixture.fltkg rust_parser_fixture rust_parser_fixture_cst \
    --output-dir tests
```
Produces: `tests/rust_parser_fixture_cst_protocol.py`.

Fixture unparser `.pyi` (Makefile:305–307):
```makefile
$(MAKE) gen-rust-unparser GRAMMAR=fltk/fegen/test_data/rust_parser_fixture.fltkg \
    RS_OUT=tests/rust_parser_fixture/src/unparser.rs \
    EXTRA_ARGS="--format-config ... \
                --protocol-module tests.rust_parser_fixture_cst_protocol \
                --pyi-output fltk/_stubs/rust_parser_fixture/unparser.pyi"
```

There is **no `gen-rust-cst --pyi-output` invocation for the `rust_parser_fixture` grammar** (only the
unparser stub exists for that fixture).

The `make gencode` convention: run generators, then `make fix` (ruff check --fix + ruff format), then
commit. `make check` (the precommit gate) enforces that the committed generated code is formatting-clean.
No automated test does a round-trip regen + byte-comparison gate for the full gencode corpus (this gap is
noted by `TODO(regex-portability-roundtrip-test)` in `TODO.md`, and the comment at `Makefile:250-252`).

---

## 6. Committed generated artifacts and tests

### Protocol modules (all under their source grammar's output-dir)

- `fltk/fegen/bootstrap_cst_protocol.py`
- `fltk/fegen/fltk_cst_protocol.py`
- `fltk/fegen/regex_cst_protocol.py`
- `fltk/unparse/toy_cst_protocol.py`
- `fltk/unparse/unparsefmt_cst_protocol.py`
- `tests/rust_parser_fixture_cst_protocol.py` (protocol-only, no CST module at `tests/rust_parser_fixture_cst.py`)

### `.pyi` stubs

```
fltk/_stubs/
  fegen_rust_cst/
    __init__.pyi   — stub-package marker only (4 lines); comment states "generated by make gencode"
    cst.pyi        — generated by gen-rust-cst --protocol-module fltk.fegen.fltk_cst_protocol
    unparser.pyi   — generated by gen-rust-unparser --protocol-module fltk.fegen.fltk_cst_protocol
  rust_parser_fixture/
    __init__.pyi   — stub-package marker
    unparser.pyi   — generated by gen-rust-unparser --protocol-module tests.rust_parser_fixture_cst_protocol
```

There is **no `fltk/_stubs/rust_parser_fixture/cst.pyi`** — the Rust CST `.pyi` was never generated for
the fixture grammar.

The `__init__.pyi` for both stub packages is hand-authored (not generated); it exists only to make
pyright recognize the directory as a stub package.

### Tests enforcing these artifacts

**`fltk/fegen/test_cst_protocol.py`** (T1–T5):

- `ALL_PROTOCOL_MODULES` at line 567 hardcodes 5 paths (`bootstrap_cst_protocol.py`,
  `fltk_cst_protocol.py`, `regex_cst_protocol.py`, `toy_cst_protocol.py`,
  `unparsefmt_cst_protocol.py`). Adding a new protocol module requires updating this list.
- `test_committed_protocol_source_names_no_native_no_selector` (line 585): parametrized over
  `ALL_PROTOCOL_MODULES`; asserts no `fltk._native` reference and no span-selector import in any
  committed protocol file; asserts `import fltk.fegen.pyrt.span_protocol` is present.
- `test_committed_cst_source_imports_no_native_no_selector` (line 607): same structural check for
  `ALL_CONCRETE_CST_MODULES` (also a hardcoded list at line 575).
- `test_protocol_module_has_one_class_per_rule`, `test_protocol_node_has_required_members`,
  `test_cst_module_protocol_has_property_per_rule`: unit-test `gen_protocol_module()` against the live
  fegen grammar; do not check committed file content.

**`tests/test_clean_protocol_consumer_api.py`** (AC 1–12):

- Imports `fltk_cst_protocol` directly; tests cross-backend equality/hash with `fegen_rust_cst.cst` (gated
  on `_FEGEN_RUST_CST_AVAILABLE`).
- `test_protocol_module_no_new_file_level_suppressions` (line 330): reads `PROTOCOL_MODULE_PATH =
  fltk/fegen/fltk_cst_protocol.py`; asserts exactly one `# ruff: noqa: N802` line and no inline
  `# type: ignore`.
- `test_protocol_import_does_not_import_concrete_backends` (line 380): subprocess check that importing
  `fltk_cst_protocol` does not pull in `fltk_cst` or `fltk._native`.
- `test_fltk2gsm_single_cst_import`, `test_fltk2gsm_pyright_clean`, etc.: structural checks on `fltk2gsm.py`.

**`fltk/fegen/test_genparser.py`** (lines 258–463 for protocol/pyi tests):

- `test_generate_protocol_only_emits_only_protocol` (line 258): asserts `--protocol-only` writes only the
  protocol file, not CST or parsers.
- `test_generate_protocol_only_matches_full_run` (line 287): asserts `--protocol-only` output is
  byte-identical to the protocol file from a full `generate` run.
- `test_gen_rust_cst_no_protocol_module_no_pyi` (line 349): no `.pyi` without `--protocol-module`.
- `test_gen_rust_cst_protocol_module_emits_pyi` (line 361): `.pyi` is written with `--protocol-module`.
- `test_gen_rust_cst_pyi_output_override` (line 396): `--pyi-output` overrides default path.
- `test_gen_rust_cst_rs_unchanged_with_protocol_module` (line 422): `.rs` bytes identical with/without
  `--protocol-module`.
- `test_gen_rust_cst_invalid_protocol_module` (line 451): bad `--protocol-module` value rejected before
  any file write.
- `test_gen_rust_unparser_no_protocol_module_no_pyi` (line 667), `test_gen_rust_unparser_protocol_module_emits_pyi`
  (line 677), `test_gen_rust_unparser_pyi_output_override` (line 700): analogous for gen-rust-unparser.

**`tests/test_gsm2tree_rs.py`** (pyi section starting ~line 1104):

- `test_pyi_two_calls_produce_identical_strings` (line 804): determinism of `generate_pyi`.
- Per-fixture `fegen_pyi` / `poc_pyi` / `minimal_pyi` / `zero_label_pyi` fixtures (lines 1111–1139).
- Tests at ~1143–1173: assert `from __future__ import annotations`, `import typing`, `import
  fltk.fegen.pyrt.span_protocol`, no `fltk.fegen.pyrt.terminalsrc`, no span selector, no `fltk._native`,
  `import {proto} as _proto`, `# ruff: noqa: N802` header, `NodeKind = _proto.NodeKind`.

---

## 7. TODOs and ADRs

### Relevant TODO entries (`TODO.md`)

- **`bazel-rules-rust`**: Add `rules_rust` to `MODULE.bazel`; implementation in progress at
  `docs/adr/2026/06/13-rust-bazel-packaging/`. Location: `MODULE.bazel`.
- **`verify-pyo3-ext-module`**: Confirm `extension-module` is active on `@fltk_crates//:pyo3` after
  `crate_universe` resolution. Location: `MODULE.bazel`.
- **`bazel-lib-rs-no-cst`**: Assembly genrule unconditionally declares `cst.rs` and `parser.rs` even
  when `lib_rs=None`. Split into grammar and span-only variants when a runtime-only crate is needed.
  Location: `rust.bzl` (the `native.genrule` call at line 316, with the `test -f` guard at lines 327-328).
- **`unparser-pyi-doc-stub-shared`**: `Doc` class stub emitted verbatim into every per-grammar
  `unparser.pyi`; factor into a shared stub. Location: `fltk/unparse/gsm2unparser_rs.py`
  (`generate_pyi`, the `class Doc:` emission).

### Relevant ADRs

- **`docs/adr/2026/06/13-rust-bazel-packaging/README.md`**: The decision on how FLTK's Rust reaches
  out-of-tree consumers via Bazel (`generate_rust_parser` + `fltk_pyo3_cdylib`). Notes under "Deferred
  work" that "FLTK should generate the cdylib crate root / `#[pymodule]` entry point" and that
  `gen-rust-lib` was subsequently added. Does **not** address `.pyi` or protocol module exposure in the
  Bazel layer.
- **`docs/adr/2026/06/05-clean-protocol-consumer-api/`**: Requirements and design for the protocol
  module consumer API (Shape 1 + Shape 2, AC 1–12). This is the source of the existing protocol
  generation contract.
- **`docs/adr/2026/06/06-rust-cst-pyi/`**: ADR for the Rust CST `.pyi` stub generation.

---

## 8. Regen conventions

From `CLAUDE.md` and `Makefile`:

- Generated code is not expected to pass ruff formatting straight from the generator.
- Intended workflow: run `make gencode` (regenerates all generated files), then `make fix` (ruff check
  --fix + ruff format), then commit.
- `make check` (the precommit gate) enforces that committed generated code is formatting-clean.
- There is no automated round-trip regen + byte-comparison test for the full generated corpus; drift is
  detected via `git diff --stat` after `make gencode`.

---

## Open factual questions

- Does `rules.bzl:generate_parser` need to declare `{base_name}_cst_protocol.py` as an output even for
  the non-`--protocol-only` path, given the CLI always writes it? (Currently it is silently written to
  the Bazel gendir but not tracked.)
- The `fltk/_stubs/fegen_rust_cst/__init__.pyi` and `fltk/_stubs/rust_parser_fixture/__init__.pyi` are
  hand-authored. If the Bazel Rust rule auto-generates the `.pyi`, does the `__init__.pyi` also need to
  be generated or declared as a Bazel output for pyright stub-package resolution to work in a Bazel
  sandbox?
- `generate_rust_parser` in `rust.bzl` is the only Rust codegen rule exposed. There is no
  `generate_rust_unparser` rule in `rust.bzl`. If the unparser `.pyi` is also relevant to Bazel
  consumers, that is a separate gap.
