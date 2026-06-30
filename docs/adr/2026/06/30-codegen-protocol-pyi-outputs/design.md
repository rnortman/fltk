# Design: codegen protocol + .pyi outputs

Status: draft (design phase)

Requirements: `requirements.md` (this directory). Exploration: `exploration.md` (this directory).

This design covers the two changes in `requirements.md`:

- **Change 1** — make protocol-module generation an opt-in capability of *both* the Python
  (`generate`) and Rust (`gen-rust-cst`) code-generation paths, off by default for each, and expose
  that opt-in through the corresponding Bazel rules (`generate_parser`, `generate_rust_parser`).
- **Change 2** — have the Rust CST generator emit the `.pyi` stub whenever the protocol module's dotted
  import path is supplied explicitly (via `--protocol-module`) — a required input, never auto-derived
  from co-generating the protocol (resolved per `notes-design-user.md`; see §6). Expose that `.pyi`,
  together with a generator-derived stub-package `__init__.pyi`, through `generate_rust_parser`. The
  `__init__.pyi` marker is produced through the same generator/CLI path as the other stubs (not a
  Bazel-local fixed body) and is dogfooded by the two in-tree `fltk/_stubs/*/__init__.pyi` markers
  (§2.2, §2.5–§2.7; resolved per `notes-design-user.md` item 3). No new Bazel rule.

---

## 1. Root cause / context

### 1.1 Python protocol generation is unconditional; Rust cannot generate it at all

The Python `generate` subcommand writes `{base_name}_cst_protocol.py` **unconditionally**
(`genparser.py:225-242`) — the write is not gated on any flag and happens even under `--trivia-only`
/ `--no-trivia-only`. There is no way to run `generate` and *not* get the protocol file. The
`--protocol-only` flag (`genparser.py:146-156`) only goes the other direction (skip CST + parsers,
still write the protocol).

The Rust `gen-rust-cst` subcommand cannot produce the protocol module at all. Its `--protocol-module`
option (`genparser.py:321-332`) names an *already-existing, externally-generated* protocol module by
import path and uses it solely to drive `.pyi` emission (`genparser.py:398-399`); it never writes a
protocol `.py`.

The requirement inverts the Python default (protocol becomes opt-in, off by default) and adds a new
capability to the Rust path (it can now *produce* the protocol). Both are then exposed through Bazel.

### 1.2 The protocol module is backend-agnostic and must be byte-identical across paths

The protocol module is produced by `CstGenerator.gen_protocol_module()` (`gsm2tree.py:719-798`). It is
structurally independent of the concrete CST: it emits `typing.Protocol` classes, a runtime `NodeKind`
enum, nested `Label` sentinels, a `Span` protocol, and a `CstModule` protocol — all derived only from
the grammar's rule models. Requirements §"The protocol module" states it is "equally valid as a type
contract for the Python-backed CST and the Rust-backed CST."

`RustCstGenerator` already owns a `CstGenerator` instance — `self._py_gen` (`gsm2tree_rs.py:177-181`) —
so the protocol-generation machinery is already reachable from the Rust path. **But there is a trap:**
`gen_protocol_module()` gates the per-rule `kind` discriminant on `self.py_module.import_path`
truthiness (`gsm2tree.py:891`):

```python
if rule_name and self.py_module.import_path:
    member = self.node_kind_member_name(rule_name)
    klass.body.append(pygen.stmt(f"kind: typing.Literal[NodeKind.{member}] = NodeKind.{member}"))
else:
    klass.body.append(pygen.stmt("kind: object"))   # degraded form
```

`RustCstGenerator` builds `self._py_gen` with `py_module=pyreg.Builtins` (`gsm2tree_rs.py:178-180`), and
`pyreg.Builtins = Module(import_path=())` (`fltk/iir/py/reg.py:16`) — an empty, falsy `import_path`. So
calling `self._py_gen.gen_protocol_module()` directly would emit the degraded `kind: object` form for
every rule, producing a protocol module that **differs** from the one the Python `generate` path
commits (which always passes a non-empty `cst_module_name`, e.g. `fltk.fegen.fltk_cst`).

The value of `import_path` never appears in protocol output — only its *truthiness* gates the `kind`
Literal. The only `self.py_module` uses are `gsm2tree.py:76,90` (the concrete-CST annotation path,
which the protocol does not use) and `:891` (the truthiness gate). The protocol's own annotation path,
`protocol_annotation_for_model_types` (`gsm2tree.py:658-688`), emits bare quoted class names for rule
refs (`:674`) and resolves library types through `typemodel.lookup_type` (`:677`), never consulting
`self.py_module`. So byte-identity across paths is achievable as long as the Rust path constructs its
protocol generator with a **non-empty** `py_module` (any non-empty value yields identical bytes). The
design makes this explicit (§2.2) and pins it with a cross-path byte-identity test (§4).

No existing test depends on the degraded `kind: object` form, but the two `gen_protocol_module()` unit
callers do **not** both use a non-empty module path — and one *does* exercise the degraded form:

- `test_cst_protocol.py:62-73` constructs with a non-empty path (`pyreg.Module(["fltk", "fegen",
  "fltk_cst"])`), so it emits the `Literal` discriminant.
- `tests/test_gsm2tree_py.py:239-240` goes through `tests/gsm2tree_helpers.py:69` `make_generator`,
  which constructs with `py_module=pyreg.Builtins` (`import_path=()`, falsy — `reg.py:16`) and therefore
  emits the degraded `kind: object` form.

Byte-identity is still safe because neither test asserts on `kind` (there is no `kind` reference anywhere
in `tests/test_gsm2tree_py.py`), so nothing depends on either form. **Implementer hazard:** the
protocol-generation machinery is reachable through the `pyreg.Builtins`-backed `make_generator` helper,
which yields the degraded form; the new `generate_protocol()` (§2.2) and any supporting test
infrastructure must therefore *not* be built on `make_generator` / `pyreg.Builtins`.

### 1.3 The `.pyi` stub structurally depends on the protocol import path

`RustCstGenerator.generate_pyi(protocol_module)` (`gsm2tree_rs.py:321-424`) interpolates the dotted
import path verbatim into `import {protocol_module} as _proto` (`:345`) and references `_proto.*`
throughout. The stub cannot be generated without that import path. This is the structural reason
Change 2 is gated on "the protocol path being known," not unconditional.

### 1.4 Bazel rules do not expose protocol or `.pyi` today

- `generate_parser` (`rules.bzl:1-72`) declares `_cst.py` / `_parser.py` / `_trivia_parser.py` but
  **not** `_cst_protocol.py` (`rules.bzl:7-27`). The CLI writes the protocol into the Bazel action
  dir, but because Bazel does not `declare_file` it, it is untracked and unexposed. So today's Bazel
  consumers never received the protocol as a tracked output — making the Change-1 opt-in purely
  *additive* at the Bazel layer (no Bazel consumer can be relying on a protocol output that was never
  declared).
- `generate_rust_parser` (`rust.bzl:100-196`) runs `gen-rust-cst` with no `--protocol-module` /
  `--pyi-output` (`rust.bzl:120-131`) and declares only `cst.rs` / `parser.rs` (`:149`). No protocol,
  no `.pyi`.

---

## 2. Proposed approach

### 2.1 Python `generate`: protocol becomes opt-in (off by default)

Add one boolean flag to `generate` (`genparser.py:127-158`):

- `--protocol` (default `False`): when set, write `{base_name}_cst_protocol.py` alongside the CST and
  parsers. When unset, **do not** write the protocol module.

Behavior matrix after the change:

| Invocation | CST | parsers | protocol |
| --- | --- | --- | --- |
| `generate g b c` | ✓ | ✓ | ✗ (was ✓) |
| `generate g b c --protocol` | ✓ | ✓ | ✓ |
| `generate g b c --protocol-only` | ✗ | ✗ | ✓ (unchanged) |

`--protocol-only` is unchanged and continues to imply protocol emission; it remains mutually exclusive
with `--trivia-only` / `--no-trivia-only` (`genparser.py:185-191`). `--protocol` combined with
`--protocol-only` is redundant; treat `--protocol-only` as authoritative (it already short-circuits at
`genparser.py:244-248`), so no new validation is required, but `--protocol-only` continues to win.

Implementation: move the unconditional protocol write block (`genparser.py:225-242`) behind
`if protocol or protocol_only:`. The protocol-only early-return path is unaffected.

**This is a deliberate breaking change to the raw CLI default**, explicitly requested by
`requirements.md` ("It would not be enabled by default for either of them"). Per `CLAUDE.md`'s
generated-output-is-public-API guidance, the migration surface is called out:

- The `make gencode` recipe (`Makefile:256-274`) must add `--protocol` to all five Python `generate`
  invocations (fltk, bootstrap, toy, unparsefmt, regex) so the committed `*_cst_protocol.py` files
  continue to regenerate. The `--protocol-only` fixture invocation (`Makefile:301-303`) is unchanged.
- Direct, out-of-tree CLI callers that relied on the protocol file as a side effect of `generate` must
  add `--protocol`. Bazel `generate_parser` consumers are **not** affected (the protocol was never a
  declared Bazel output — see §1.4); they instead gain a new opt-in attr (§2.4).

### 2.2 Rust `gen-rust-cst`: can now produce the protocol module

Add one option to `gen-rust-cst` (`genparser.py:317-348`):

- `--protocol-output PATH` (default `None`): when set, write the generated protocol `.py` module to
  `PATH`. Requires `--protocol-module` (which supplies the protocol's dotted import path). When set,
  the `.pyi` is also emitted (driven, as today, by `--protocol-module` being present), so opting into
  protocol output yields **both** the protocol `.py` and the `.pyi` — no separate `.pyi` opt-in is
  needed. (This is not a *lone* opt-in: `--protocol-module` is still required; see the deviation note
  below.)

This keeps `--protocol-module`'s existing meaning intact (import path → emit `.pyi`; no protocol `.py`
written) so the existing fegen/Makefile flow that references the Python-generated
`fltk.fegen.fltk_cst_protocol` (`Makefile:284-285`) is unchanged. `--protocol-output` is purely
additive.

Mapping to requirements §"Change 2":

- **Condition 1** (Rust produces the protocol): `--protocol-module X --protocol-output P`. The Rust
  generator writes the protocol `.py` to `P` and the `.pyi` referencing `X`. At the Bazel layer this
  requires **two coupled knobs** — `protocol_module = X` *and* `generate_protocol = True` (§2.5) — not a
  single opt-in.
- **Condition 2** (import path supplied, protocol exists elsewhere): `--protocol-module X` alone
  (existing behavior, unchanged) — `.pyi` only.
- **Neither**: no `--protocol-module`, no `--protocol-output` → no `.pyi`, no protocol (unchanged).

**Deliberate deviation from requirement Change-2 condition 1 (user-confirmed).** The requirement states
the caller "does not separately pass a `--protocol-module` flag; enabling protocol output on the Rust
generator is sufficient to also get the `.pyi`." This design does **not** honor that literally: producing the protocol
still requires the dotted import path (`--protocol-module` / Bazel `protocol_module`) *in addition to*
the protocol-output opt-in (`--protocol-output` / `generate_protocol`). Both conditions therefore reduce
to "the import path is supplied," with the protocol-output opt-in only additionally writing the `.py`.
The reason is structural: the `.pyi`'s `import {protocol_module} as _proto` line (§1.3) needs the
*dotted import path*, which is not derivable from the protocol output *file path* — they are independent
strings (cf. the Makefile pairing `--protocol-module fltk.fegen.fltk_cst_protocol --pyi-output
fltk/_stubs/fegen_rust_cst/cst.pyi`). The requirement's "single opt-in" model is thus under-specified for
the CLI. **User-confirmed resolution (`notes-design-user.md`):** the protocol import path is required
input, specified separately via `--protocol-module` (Bazel `protocol_module`), rather than auto-derived
from co-generating the protocol; the two-flag coupling is the accepted design, not provisional.

New validation in `gen_rust_cst`, added next to the existing `--pyi-output requires --protocol-module`
check (`genparser.py:382-384`):

- `--protocol-output` without `--protocol-module` → CLI error, write nothing. Rationale: the protocol
  `.py` and its `.pyi` are a matched pair; producing the `.py` without the import path needed for the
  `.pyi` would be a half-configured state, and the requirement is that enabling protocol output also
  yields the `.pyi`.

New generator method on `RustCstGenerator` (`gsm2tree_rs.py`):

- `generate_protocol(self) -> str`: returns the complete protocol-module source text, **byte-identical
  to the Python `generate --protocol` output for the same grammar**, including the
  `# ruff: noqa: N802\n` file-level prefix (`genparser.py:236`). Internally it builds the protocol via
  a `CstGenerator` whose `py_module` has a non-empty `import_path` (so the `kind` Literal discriminant
  is emitted — §1.2), then `"# ruff: noqa: N802\n" + ast.unparse(...)`. Because the `import_path`
  *value* never appears in protocol output, any non-empty placeholder yields identical bytes; the
  method does not require the caller to supply a CST module name.

  Note: `RustCstGenerator.__init__`'s existing `self._py_gen` (with `pyreg.Builtins`) is left
  untouched — it backs `.rs` and `.pyi` generation and must not change. `generate_protocol()`
  constructs its own protocol generator (or threads a non-empty `py_module` through a private helper)
  rather than mutating `self._py_gen`.

To keep the two CLI paths from drifting, factor the protocol text production into one shared helper so
`generate` and `gen-rust-cst` render protocol bytes through a single code path (e.g. a module-level
`render_protocol_text(grammar) -> str` in `genparser.py`, or `generate` delegating to the same
`CstGenerator.gen_protocol_module()` + prefix sequence that `generate_protocol()` uses). The byte-
identity test (§4) is the guardrail regardless of the exact factoring chosen.

`gen_rust_cst` write ordering (preserving the existing "generate all text before opening any file"
contract at `genparser.py:395-408`): generate `.pyi` text (when `--protocol-module`), protocol text
(when `--protocol-output`), and `.rs` text first; only then write `.rs`, then the protocol `.py` (to
`--protocol-output`), then the `.pyi`. A generation error leaves no partial files. The protocol `.py`
write reuses the existing `_write_output_file` helper (`genparser.py:301-314`) with an artifact label.

#### Stub-package `__init__.pyi` marker (shared by `gen-rust-cst` and `gen-rust-unparser`)

Both `.pyi`-producing subcommands gain a small, grammar-independent capability to emit the stub-package
marker alongside the `.pyi` they already write, so the marker is dogfooded through the same
generator/CLI path as every other stub (resolved per `notes-design-user.md` item 3, **superseding** the
earlier "in-tree markers stay hand-authored / generation is Bazel-only via `ctx.actions.write`" plan
recorded in the prior §2.5–§2.7/§6). Three new options, shared between `gen_rust_cst`
(`genparser.py:317-348`) and `gen_rust_unparser` (`genparser.py:470-580`):

- `--init-pyi-output PATH` (default `None`): when set, also write the stub-package `__init__.pyi` to
  `PATH`.
- `--extension-name NAME` (default `None`): the compiled extension's importable name (e.g.
  `fegen_rust_cst`), interpolated into the marker comment. Required when `--init-pyi-output` is set.
- `--submodules CSV` (default `None`): comma-separated names of the submodules the extension registers
  (e.g. `cst,parser,unparser`), interpolated into the marker comment. Required when `--init-pyi-output`
  is set.

Validation up front, before any file is written (matching `_validate_protocol_module`,
`genparser.py:429-441`): `--init-pyi-output` requires both `--extension-name` and `--submodules`; the
extension name and each `--submodules` entry must be a valid identifier (reusing `gsm2lib_rs`'s existing
`_validate_rust_ident`). The marker is **independent of `--protocol-module`** — it references no
protocol and only describes package structure — so it can be attached to whichever invocation already
writes a `.pyi` for a given stub package. This independence is what lets `rust_parser_fixture` (whose
`gen-rust-cst` passes no `--protocol-module` and so emits no `cst.pyi`) still obtain its marker, from its
`gen-rust-unparser` invocation instead (§2.7).

The marker text is produced by a new grammar-independent helper,
`render_stub_package_init(extension_name: str, submodules: Sequence[str]) -> str`, in `gsm2lib_rs.py` —
the existing home for module-layout/submodule templating, which already owns `_validate_rust_ident` and
the `Submodule`/`LibSpec` abstractions and has no grammar dependency. It returns **comment-only** `.pyi`
text that names the extension and its submodules and preserves the informative explanation the in-tree
markers carry (a recognized stub package whose top-level module exports nothing directly, only the
listed submodules). Because the output is pure comments plus a trailing newline, it is stable under
`make fix` (ruff format/check leave it byte-identical), keeping the `make gencode` drift check clean
(§2.7, §5). Both subcommands render this text before opening any file, preserving the same
"generate all artifact text before writing" contract as the `.pyi`/protocol writes above.

### 2.3 The `.rs` output is unaffected

The generated `.rs` does not change with any protocol/`.pyi` flag — this invariant is already asserted
for `--protocol-module` (`test_gen_rust_cst_rs_unchanged_with_protocol_module`,
`test_genparser.py:422-448`) and is extended to cover `--protocol-output` (§4).

### 2.4 Bazel `generate_parser` (Python): expose opt-in protocol

Add one attribute to `generate_parser` (`rules.bzl:41-72`):

- `protocol` (bool, default `False`): when `True`, pass `--protocol` to the `generate` action and
  `ctx.actions.declare_file(ctx.attr.base_name + "_cst_protocol.py")`, appending it to `outputs` (and
  thus to `DefaultInfo`). When `False`, nothing is declared or passed (status quo).

This is the Bazel-level opt-in for Change 1, Python side. It is additive and default-off, so existing
`generate_parser` targets are unchanged.

### 2.5 Bazel `generate_rust_parser` (Rust): expose `.pyi` and opt-in protocol

Add two attributes to `generate_rust_parser` (`rust.bzl:151-175`):

- `protocol_module` (string, default `""`): the protocol's dotted import path. When non-empty, the
  `gen-rust-cst` action (`rust.bzl:120-131`) gains `--protocol-module {protocol_module}` and
  `--pyi-output {name}/cst.pyi`; the rule `declare_file`s `{name}/cst.pyi` and adds it to the outputs
  (`rust.bzl:116-117,149`). The **same `gen-rust-cst` action** additionally gains
  `--init-pyi-output {name}/__init__.pyi --extension-name {name} --submodules cst,parser` (§2.2), and
  the rule `declare_file`s `{name}/__init__.pyi` as a third output of that one action, so the `{name}/`
  directory is a complete, self-contained stub package in the Bazel output tree (§2.6). The marker is
  produced through the same generator/CLI path as the dogfooded in-tree markers (§2.2, §2.7) — **not** a
  Bazel-local `ctx.actions.write` fixed body — so the marker content stays a single maintenance point
  shared with the in-tree stubs (resolved per `notes-design-user.md` item 3). The submodule list is
  `cst,parser` because that is what `generate_rust_parser` produces (cst.rs + parser.rs); `{name}`
  doubles as the stub-package import name (the convention already used for `{name}/cst.pyi`) and is
  passed as `--extension-name`. This is the primary ask: "Generating a Rust CST should just
  automatically generate the `.pyi` and the bazel rules should expose this."
- `generate_protocol` (bool, default `False`): when `True` (requires `protocol_module` non-empty), the
  `gen-rust-cst` action additionally gains `--protocol-output {name}/cst_protocol.py`; the rule
  `declare_file`s `{name}/cst_protocol.py` and adds it to the outputs. This is the Bazel-level opt-in
  for Change 1, Rust side (off by default).

Resulting `gen-rust-cst` flag/output combinations from the rule:

| `protocol_module` | `generate_protocol` | flags added | declared outputs (beyond cst.rs/parser.rs) |
| --- | --- | --- | --- |
| `""` | `False` | none | none |
| set | `False` | `--protocol-module`, `--pyi-output` | `cst.pyi`, `__init__.pyi` |
| set | `True` | `--protocol-module`, `--pyi-output`, `--protocol-output` | `cst.pyi`, `__init__.pyi`, `cst_protocol.py` |
| `""` | `True` | — | rule-time error: `generate_protocol` requires `protocol_module` |

Validation: the rule's `impl` fails (via `fail()`) when `generate_protocol = True` and
`protocol_module` is empty, mirroring the CLI's `--protocol-output requires --protocol-module` check
and surfacing the misconfiguration at analysis time.

No new Bazel rule is introduced (requirements §"Change 1" / §"Change 2"). The `gen-rust-parser` action
(`rust.bzl:133-147`) is untouched.

### 2.6 `fltk_pyo3_cdylib` interaction and the stub-package `__init__.pyi`

**Stub-package `.pyi` files flow into the assembly genrule, harmlessly.** The `fltk_pyo3_cdylib` macro
(`rust.bzl:200-391`) assembles `.rs` sources into a crate. Once §2.5 adds `cst.pyi` and `__init__.pyi`
to `generate_rust_parser`'s `DefaultInfo` depset, a downstream `fltk_pyo3_cdylib(rs_srcs = <that
target>)` *does* pull both into its crate-assembly genrule: the genrule takes `srcs = [lib_rs, rs_srcs]`
(`rust.bzl:318`) and its copy loop `for f in $(locations {rs_srcs}); do cp $$f $$OUTDIR/$$(basename $$f)`
(`rust.bzl:324-326`) expands `rs_srcs` to the whole `DefaultInfo` files set, so the `.pyi` files are
copied into the crate gendir. This is benign: the genrule's `outs` are only `lib.rs` / `cst.rs` /
`parser.rs` (`rust.bzl:319`), so the stray `.pyi` files are undeclared sandbox files Bazel discards;
rustc compiles only `mod cst;` / `mod parser;` (it never reads `.pyi`); and the `test -f cst.rs/parser.rs`
guards (`rust.bzl:327-328`) still pass. The implementer should confirm the `fltk_pyo3_cdylib` round-trip
still builds with the `.pyi` files present in `rs_srcs`; if a future maintainer needs `rs_srcs` to yield
only `.rs`, filter the `.pyi` files out of what flows into the genrule rather than relying on discard.

**Stub-package `__init__.pyi` is generated and declared (resolved).** Per `notes-design-user.md`
(items 1 and 3), `generate_rust_parser` generates the stub-package `__init__.pyi` alongside `cst.pyi`
(§2.5) whenever `protocol_module` is set, via the shared `--init-pyi-output` generator/CLI path (§2.2)
— not a Bazel-local fixed body. Declaring both `{name}/__init__.pyi` and `{name}/cst.pyi` as tracked
outputs makes `{name}/` a complete stub package inside the Bazel sandbox, so pyright stub-package
resolution does not depend on a separately hand-authored marker. The marker's comment text is
generator-derived from the extension name (`{name}`) and submodule list (`cst,parser`); it carries no
grammar-derived rule data, so the action's only grammar inputs remain the `.rs`/`.pyi` it already
generates. This design's Bazel scope remains limited to `generate_parser` and `generate_rust_parser`
exposing these artifacts as declared outputs; placing the resulting stub-package directory onto a
particular consumer's pyright stub path remains that consumer's build-integration step.

### 2.7 Makefile — dogfood the in-tree stub-package markers

`make gencode` (`Makefile:253-324`) is updated to keep the committed corpus regenerating and to
**dogfood** the two in-tree stub-package markers (resolved per `notes-design-user.md` item 3,
**superseding** the earlier "markers stay hand-authored / generation is Bazel-only" plan):

- Add `--protocol` to the five Python `generate` invocations (§2.1).
- The Rust `gen-rust-cst` / `gen-rust-unparser` `--protocol-module` / `--pyi-output` flags are unchanged
  for `.pyi` emission (condition 2); the new `--protocol-output` is exercised by tests, not required by
  the in-tree corpus, because in-tree protocols are committed via the Python path.
- Emit `fltk/_stubs/fegen_rust_cst/__init__.pyi` from the existing `fegen` `gen-rust-cst` invocation
  (`Makefile:284-285`, which already writes `cst.pyi`) by appending
  `--init-pyi-output fltk/_stubs/fegen_rust_cst/__init__.pyi --extension-name fegen_rust_cst
  --submodules cst,parser,unparser` (§2.2). The regenerated marker now correctly lists `unparser` as a
  submodule, fixing a pre-existing staleness in the hand-authored marker (which currently says "only
  submodules cst and parser", though `crates/fegen-rust/src/lib.rs` also registers `unparser`).
- Emit `fltk/_stubs/rust_parser_fixture/__init__.pyi` from the existing fixture `gen-rust-unparser`
  invocation (`Makefile:306-307`, which already writes `unparser.pyi`) by appending
  `--init-pyi-output fltk/_stubs/rust_parser_fixture/__init__.pyi --extension-name rust_parser_fixture
  --submodules cst,parser,unparser,unparser_default,collision_cst,collision_parser` (§2.2). This routes
  the marker through the one fixture invocation that already writes a `.pyi`; the fixture's
  `gen-rust-cst` call (`Makefile:296`) passes no `--protocol-module`, writes no `cst.pyi`, and is left
  unchanged — **no new `cst.pyi` is introduced** for the fixture. (This is the wrinkle the user flagged:
  the fixture's `.pyi` comes from the unparser path, not the CST path.)
- Both regenerated markers are comment-only and ruff-stable (§2.2), so the regen → `make fix` → commit
  flow leaves them byte-identical and the `make gencode` drift check (committed vs generated) now covers
  them like every other stub.
- `fltk/_native/__init__.pyi` is **not** a package marker but a substantive hand-written type stub
  (`Span` / `SourceText` / `UnknownSpan`); no `gencode` step generates it and it is left untouched
  (`notes-design-user.md` item 3, "out of scope").

---

## 3. Files / interfaces touched

- `fltk/fegen/genparser.py`
  - `generate`: add `--protocol` flag; gate the protocol write on `protocol or protocol_only`.
  - `gen_rust_cst`: add `--protocol-output` option; add `--protocol-output requires --protocol-module`
    validation; write the protocol `.py` (via `gen.generate_protocol()`) when set. Add the shared
    `--init-pyi-output` / `--extension-name` / `--submodules` options and marker write (§2.2).
  - `gen_rust_unparser`: add the same `--init-pyi-output` / `--extension-name` / `--submodules` options
    and marker write (§2.2), so the fixture's unparser invocation can emit its package marker.
  - Shared marker validation (`--init-pyi-output` requires `--extension-name` + `--submodules`;
    identifier checks on the extension name and each submodule entry).
  - Possibly a shared `render_protocol_text(grammar)` helper to keep `generate` and `gen-rust-cst`
    protocol bytes on one code path (§2.2).
- `fltk/fegen/gsm2tree_rs.py`
  - `RustCstGenerator.generate_protocol(self) -> str`: new method; emits protocol text byte-identical
    to the Python path (non-empty `py_module`, `# ruff: noqa: N802` prefix).
- `fltk/fegen/gsm2lib_rs.py`
  - `render_stub_package_init(extension_name, submodules) -> str`: new grammar-independent helper that
    renders the comment-only, ruff-stable stub-package `__init__.pyi` marker text (§2.2). Reuses the
    module's `_validate_rust_ident`.
- `rules.bzl`
  - `generate_parser`: add `protocol` bool attr; conditionally declare `{base_name}_cst_protocol.py`
    and pass `--protocol`.
- `rust.bzl`
  - `generate_rust_parser`: add `protocol_module` string + `generate_protocol` bool attrs; conditional
    `--protocol-module` / `--pyi-output` / `--protocol-output` flags; declared outputs `cst.pyi` +
    `__init__.pyi` when `protocol_module` is set, plus `cst_protocol.py` when `generate_protocol`. The
    `__init__.pyi` is produced by the same `gen-rust-cst` action via
    `--init-pyi-output {name}/__init__.pyi --extension-name {name} --submodules cst,parser` (§2.5) — **not**
    `ctx.actions.write`. `fail()` on `generate_protocol` without `protocol_module`.
- `Makefile`
  - `gencode`: add `--protocol` to the five Python `generate` calls; append the marker flags to the
    `fegen` `gen-rust-cst` call and the `rust_parser_fixture` `gen-rust-unparser` call so both in-tree
    `__init__.pyi` markers regenerate (§2.7).
- Test files (§5): `fltk/fegen/test_genparser.py`, `fltk/fegen/test_gsm2lib_rs.py`,
  `fltk/fegen/test_cst_protocol.py`, `tests/test_gsm2tree_rs.py`.

No generated public symbol is renamed and no annotation surface changes (CLAUDE.md constraint): the
protocol module and `.pyi` content are unchanged in shape; only *when* they are produced changes. The
in-tree `__init__.pyi` markers change in *comment text only* (now generator-rendered, and the `fegen`
marker gains the previously-omitted `unparser` submodule) — they carry no symbols or annotations, so no
downstream type-annotation or call-site surface is affected.

---

## 4. Edge cases / failure modes

- **Rust protocol silently diverges from Python protocol.** The central risk (§1.2). If
  `generate_protocol()` used `pyreg.Builtins`, every rule would emit `kind: object` instead of the
  `Literal` discriminant, and a consumer regenerating the same grammar's protocol via the Rust path
  would get a structurally weaker contract. Mitigation: `generate_protocol()` uses a non-empty
  `py_module`; pinned by a byte-identity test (below).
- **`--protocol-output` without `--protocol-module`.** Rejected at the CLI before any write
  (§2.2); analogously, `generate_protocol=True` without `protocol_module` fails at Bazel analysis
  time (§2.5).
- **Partial files on generation error.** Preserved invariant: all artifact text is generated before
  any file is opened (`genparser.py:395-408` pattern extended to the protocol `.py`).
- **Invalid `--protocol-module` value.** Still validated up front by `_validate_protocol_module`
  (`genparser.py:429-441`) before any file is written, including the new protocol `.py`.
- **Default-off protocol breaks an out-of-tree direct CLI caller.** Accepted, explicit per
  requirements; migration is "add `--protocol`" (§2.1). Bazel consumers are insulated (§1.4).
- **`generate_rust_parser` with `protocol_module` but the protocol module does not actually exist at
  that import path** (condition 2, `generate_protocol=False`). The `.pyi` is still emitted; the import
  resolves only when the consumer also provides the protocol module (e.g. via the Python
  `generate_parser` rule). This matches today's `--protocol-module` contract and is the consumer's
  responsibility — the rule does not verify importability.
- **Stub-package resolution in a Bazel sandbox.** Resolved: `generate_rust_parser` generates and
  declares `{name}/__init__.pyi` next to `{name}/cst.pyi` (§2.5–§2.6), so the stub package is complete
  in the sandbox and pyright resolves it without a separately committed marker.
- **`--init-pyi-output` without `--extension-name` / `--submodules`.** Rejected at the CLI before any
  write (§2.2); the extension name and each submodule entry are validated as identifiers up front, so a
  malformed marker never reaches disk.
- **A package's `.pyi` comes from the unparser path, not the CST path** (the `rust_parser_fixture`
  wrinkle). The marker is independent of `--protocol-module`, so it is emitted from whichever invocation
  already writes a `.pyi` for that package — `gen-rust-unparser` for the fixture (§2.7) — and **no new
  `cst.pyi` is introduced** for the fixture. If both a package's `gen-rust-cst` and `gen-rust-unparser`
  invocations were ever given `--init-pyi-output` for the same path, the later write would win; the
  Makefile attaches the flag to exactly one invocation per package to avoid that.
- **Generated marker drifts under `make fix`.** The marker is pure comments plus a trailing newline, so
  ruff format/check leave it byte-identical; the `make gencode` drift check (committed vs generated) now
  covers both in-tree markers (§2.7, §5).

---

## 5. Test plan

After this change the following tests exist (extending the suites surveyed in `exploration.md` §6):

**`fltk/fegen/test_genparser.py`** (Python `generate`):

- `generate` (no `--protocol`) writes `_cst.py` + both parsers but **not** `_cst_protocol.py`
  (the new default).
- `generate --protocol` writes `_cst.py` + both parsers + `_cst_protocol.py`.
- `generate --protocol` and `generate --protocol-only` emit byte-identical `_cst_protocol.py`. This
  **modifies** `test_generate_protocol_only_matches_full_run` (`test_genparser.py:287-319`): its full-run
  arm (`:300`, a bare `generate`) must gain `--protocol`, otherwise the new default (§2.1) writes no
  protocol file and the `full_dir / "simple_cst_protocol.py"` read (`:317`) raises `FileNotFoundError`.
- The genuinely-unchanged `--protocol-only` tests still pass as-is:
  `test_generate_protocol_only_emits_only_protocol` (`test_genparser.py:258-284`) and
  `test_generate_protocol_only_rejects_trivia_flags` (`test_genparser.py:322-341`). (Only the `:287-319`
  test in that range changes — see the prior bullet.)

**`fltk/fegen/test_genparser.py`** (Rust `gen-rust-cst`):

- `--protocol-output` without `--protocol-module` → non-zero exit, no `.rs`, no `.py`, no `.pyi`
  written.
- `--protocol-module X --protocol-output P` writes the protocol `.py` to `P`, writes the `.pyi`, and
  writes the `.rs`.
- **Cross-path byte-identity:** `gen-rust-cst --protocol-module X --protocol-output P` produces a
  protocol `.py` byte-identical to `generate --protocol` (and `--protocol-only`) for the same grammar.
  This is the guardrail for §1.2 / §2.2.
- `.rs` output is identical with and without `--protocol-output` (extends
  `test_gen_rust_cst_rs_unchanged_with_protocol_module`, `test_genparser.py:422-448`).
- Existing `gen-rust-cst` `--protocol-module` / `--pyi-output` tests
  (`test_genparser.py:349-463`) still pass unchanged.

**`fltk/fegen/test_genparser.py`** (stub-package `__init__.pyi` marker, §2.2):

- `gen-rust-cst ... --init-pyi-output P --extension-name N --submodules cst,parser` writes a comment-only
  `__init__.pyi` at `P` that names `N` and lists the submodules, and still writes the `.rs` (and the
  `.pyi` when `--protocol-module` is also given).
- `--init-pyi-output` without `--extension-name` (or without `--submodules`) → non-zero exit, nothing
  written.
- `--init-pyi-output` with a malformed `--extension-name` / `--submodules` entry (non-identifier) →
  non-zero exit before any write.
- `gen-rust-unparser ... --init-pyi-output P --extension-name N --submodules ...` writes the marker too
  (the `rust_parser_fixture` routing, §2.7): same assertions, exercised on the unparser subcommand.

**`fltk/fegen/test_gsm2lib_rs.py`**: a unit test that
`render_stub_package_init("fegen_rust_cst", ["cst", "parser", "unparser"])` returns comment-only text
that names the extension and each submodule, parses as a valid (empty) Python module, and is idempotent
under a re-render — i.e. the generator-derived marker is stable. (Byte-stability under `make fix` is a
property of the comment-only output and is additionally covered by the `make gencode` drift check.)

**`fltk/fegen/test_cst_protocol.py`**: `ALL_PROTOCOL_MODULES` (`test_cst_protocol.py:567`) and the
committed protocol corpus are unchanged in content (the committed files still come from the Python
path with `--protocol`), so the existing structural assertions
(`test_committed_protocol_source_names_no_native_no_selector`, `:585`) continue to hold.

**`tests/test_gsm2tree_rs.py`**: a unit test that `RustCstGenerator.generate_protocol()` returns text
beginning with `# ruff: noqa: N802`, parses as valid Python, and contains the `kind:
typing.Literal[NodeKind.*]` discriminant form (not the degraded `kind: object`). Existing `.pyi`
structural tests (`test_gsm2tree_rs.py:~1104+`) are unaffected.

**`make gencode` drift (in-tree marker dogfooding, §2.7):** after `make gencode` + `make fix`, the two
regenerated markers `fltk/_stubs/fegen_rust_cst/__init__.pyi` and
`fltk/_stubs/rust_parser_fixture/__init__.pyi` must equal their committed contents (the existing `git
diff` drift gate now covers them). The existing
`tests/test_rust_unparser_pyi.py::test_committed_stub_artifacts_exist` (`:134-146`) already asserts
`fltk/_stubs/rust_parser_fixture/__init__.pyi` is present and stays green because the marker is still
committed at that path — only its provenance (now generated) changes, not its existence. That test
asserts presence, not content, so the comment-text change does not break it.

**Bazel** (`rules.bzl` / `rust.bzl`): there is currently no automated Bazel-build test in the suite
(exploration §5 notes the regen path is the gate, not a Bazel round-trip). The rule changes are
validated by `make gencode` drift detection and by the CLI-level tests above, which exercise the exact
flag combinations the rules emit — including the `--init-pyi-output` marker path the rule now invokes
(§2.5), so the generated `__init__.pyi` *does* have generator-level behavior, and it is unit-tested via
the CLI/helper tests above rather than re-tested through Bazel. Adding a Bazel analysis test is out of
scope here (no existing Bazel test harness to extend); the rule attrs, the marker flags, and the
`fail()` paths are simple wiring over tested CLI behavior.

---

## 6. Resolved decisions

The user's decisions (`notes-design-user.md`) are folded into the sections above and recorded here for
the audit trail.

1. **Bazel stub-package `__init__.pyi` for `.pyi` resolution — resolved: generate it (item 1), via the
   dogfooded generator/CLI path (item 3).** `generate_rust_parser` generates and declares the
   stub-package `__init__.pyi` alongside `cst.pyi` whenever `protocol_module` is set (§2.5, §2.6), so the
   `{name}/` directory is a complete, tracked stub package and pyright stub-package resolution does not
   depend on a separately hand-authored marker. Per item 3 (below), the marker is produced through the
   shared `--init-pyi-output` generator/CLI path (§2.2) — **not** `ctx.actions.write` — with
   generator-derived content. Placing the resulting stub-package directory onto a particular consumer's
   pyright stub path remains that consumer's build-integration step.

2. **Requirement Change-2 condition 1's "single opt-in" vs the two-flag coupling — resolved: require the
   import path separately.** The protocol's dotted import path is a required input, supplied explicitly
   via `--protocol-module` (Bazel `protocol_module`), and is **not** auto-derived from co-generating the
   protocol (option (a) of the prior question). The `.pyi` is emitted whenever that import path is
   supplied; `--protocol-output` / `generate_protocol` only additionally writes the protocol `.py`. This
   is the two-flag coupling described in §2.2; the requirement's "single opt-in" wording is treated as
   under-specified for the CLI because the `.pyi`'s `import {protocol_module} as _proto` line needs the
   dotted import path, which is independent of any output file path.

3. **Dogfood the `__init__.pyi` markers — resolved: route marker generation through the generator/CLI
   path and regenerate the in-tree markers; supersedes the prior "hand-authored / Bazel-only" plan.**
   Per `notes-design-user.md` item 3, the stub-package marker is produced by the same generator/CLI path
   as the other stubs, with **generator-derived** content (the extension name plus the submodule list it
   produces), via the shared `--init-pyi-output` / `--extension-name` / `--submodules` options on
   `gen-rust-cst` and `gen-rust-unparser` and the `render_stub_package_init` helper in `gsm2lib_rs.py`
   (§2.2). The Bazel `generate_rust_parser` rule reuses that same CLI path instead of a fixed
   `ctx.actions.write` body (§2.5–§2.6). `make gencode` regenerates both in-tree markers
   (`fltk/_stubs/fegen_rust_cst/__init__.pyi` from the `fegen` `gen-rust-cst` invocation;
   `fltk/_stubs/rust_parser_fixture/__init__.pyi` from the fixture `gen-rust-unparser` invocation, since
   that fixture's `gen-rust-cst` passes no `--protocol-module` and writes no `cst.pyi`), so both are
   dogfooded like every other stub (§2.7). This **supersedes** the prior §2.5–§2.7/§6 decision that the
   in-tree markers stay hand-authored and that generation is scoped to the Bazel rule. Out of scope per
   the same note: `fltk/_native/__init__.pyi`, a substantive hand-written type stub (not a package
   marker), is left untouched.
