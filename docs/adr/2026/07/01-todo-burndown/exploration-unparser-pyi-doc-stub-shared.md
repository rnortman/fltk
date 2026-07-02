# Exploration: `TODO(unparser-pyi-doc-stub-shared)`

Facts and source ground truth only. No prescriptions.

## 1. How many copies exist, and how big is the duplicated block?

The `class Doc:` block is emitted by `RustUnparserGenerator.generate_pyi` at
`fltk/unparse/gsm2unparser_rs.py:138-140`:

```python
lines.append("class Doc:")
lines.append("    def render(self, max_width: int = ..., indent_width: int = ...) -> str: ...")
lines.append("    def __repr__(self) -> str: ...")
```

That is exactly 3 lines of content (plus a trailing blank line separator at `:141`).

There are exactly two committed `unparser.pyi` files in the repo (confirmed via
`find ... -name unparser.pyi`):

- `fltk/_stubs/fegen_rust_cst/unparser.pyi:5-7`
- `fltk/_stubs/rust_parser_fixture/unparser.pyi:5-7`

Both contain the identical 3-line block verbatim:

```python
class Doc:
    def render(self, max_width: int = ..., indent_width: int = ...) -> str: ...
    def __repr__(self) -> str: ...
```

So the TODO's own count ("two copies of three lines") is accurate as stated, not an
exaggeration.

## 2. All `TODO(unparser-pyi-doc-stub-shared)` occurrences

Comment/source location (the only actual code comment):

- `fltk/unparse/gsm2unparser_rs.py:133` — the comment attached to the `class Doc:` emission
  in `generate_pyi`.

`TODO.md` entry:

- `TODO.md:105-107`.

Other mentions (documentation/workflow artifacts referencing the same slug, not separate
code-comment instances):

- `docs/adr/2026/06/30-codegen-protocol-pyi-outputs/exploration.md:163` and `:399`
- `docs/workflow/2026-06-27-rust-fltkfmt/dispositions-final-deep.md:108-109`
- `docs/workflow/2026-06-27-rust-fltkfmt/judge-verdict-final-deep.md:21` (records the finding
  as `reuse-1`, disposition: deferred to this TODO slug)

No other `class Doc:` emission site or second generator touches this block —
`gsm2unparser_rs.py` is the sole location that emits `.pyi` for the Rust unparser backend
(confirmed by `grep` across the repo for the slug and for `generate_pyi` in
`fltk/unparse/`).

## 3. How does the CST side actually share code across grammars?

The TODO's justification says to "mirror how the CST side shares `CstModule`." Checking
that claim against the CST protocol/stub generation machinery:

### `CstModule` is *not* imported/shared across grammars — it is regenerated per grammar

`CstModule` is emitted by `fltk/fegen/gsm2tree.py:1012-1023` (`_cst_module_protocol`), which
builds one `@property` per rule in the grammar (`for rule in self.rule_models`). Its member
set is therefore grammar-dependent by construction — a grammar with N rules produces a
`CstModule` with N properties named after those rules.

Grepping for `class CstModule` shows six independent definitions, one per grammar's own
protocol module, each with a different property list:

- `fltk/fegen/fltk_cst_protocol.py:950`
- `fltk/fegen/regex_cst_protocol.py:2198`
- `fltk/fegen/bootstrap_cst_protocol.py:997`
- `fltk/unparse/toy_cst_protocol.py:338`
- `fltk/unparse/unparsefmt_cst_protocol.py:2194`
- `tests/rust_parser_fixture_cst_protocol.py:1557`

None of these files imports `CstModule` from another file — each protocol module's only
imports are `enum`, `typing`, and `fltk.fegen.pyrt.terminalsrc` (confirmed by grepping
`^from|^import` across all six files: identical 3-line import block, no cross-protocol-module
import). `CstModule` is consumed only by downstream/test code that assigns a concrete backend
module to a `cstp.CstModule`-typed variable to check structural conformance (e.g.
`fltk/fegen/test_cst_protocol.py:226`, `tests/typecheck_fegen_cst_conformance.py:18`) — there
is no artifact literally shared by import for `CstModule` itself.

Separately, the per-grammar generated `cst.pyi` (e.g.
`fltk/_stubs/fegen_rust_cst/cst.pyi:1-8`) does not define its own `CstModule` at all — it
isn't present in `cst.pyi` or `__init__.pyi`. `cst.pyi` instead imports the grammar's own
protocol module (`import fltk.fegen.fltk_cst_protocol as _proto`) and reuses
`_proto.NodeKind`, `_proto.Grammar.Label`, etc. for its own annotations — i.e., the "sharing"
that exists on the CST side is grammar's protocol module ↔ grammar's own concrete stub, not
protocol-module-to-protocol-module sharing of a `CstModule`-shaped block. The unparser
`.pyi` already does the analogous thing: `generate_pyi` takes the same `protocol_module`
argument and emits `import {protocol_module} as _proto` (`gsm2unparser_rs.py:128`), reusing
each grammar's own protocol module for its `node: _proto.{ClassName}` parameter
annotations. The docstring at `gsm2unparser_rs.py:113-115` explicitly notes there is no
`UnparserModule` analog of `CstModule` — the unparser stub only borrows the CST protocol
module's node types, it does not need or use `CstModule`.

### The actual existing precedent for a grammar-independent shared type is `SpanProtocol`, not `CstModule`

A structurally identical situation to `Doc` (a small, grammar-independent typing surface
duplicated across all committed `.pyi`/protocol outputs) already exists on the CST side and
*is* handled via a literal shared import: `SpanProtocol`, defined once at
`fltk/fegen/pyrt/span_protocol.py:17-33` inside the `fltk` package itself
(`fltk.fegen.pyrt.span_protocol`). Every generated `cst.pyi` imports it directly —
`fltk/_stubs/fegen_rust_cst/cst.pyi:6`: `import fltk.fegen.pyrt.span_protocol`, referenced at
`:13` as `fltk.fegen.pyrt.span_protocol.SpanProtocol`. This import is unconditional
(independent of grammar), confirmed as an asserted invariant in
`docs/adr/2026/06/30-codegen-protocol-pyi-outputs/exploration.md:383-384` ("Tests at
~1143–1173: assert ... `import fltk.fegen.pyrt.span_protocol` ... `import {proto} as
_proto`").

Each grammar's *own* protocol module (`fltk_cst_protocol.py`, `regex_cst_protocol.py`, etc.)
additionally defines its own local `class Span(typing.Protocol)` (e.g.
`fltk/fegen/fltk_cst_protocol.py:945-947`) — a 2-line block duplicated per protocol module,
analogous in shape/size to the `Doc` situation, and *not* shared via import between protocol
modules. So even on the CST side there are two different patterns in play: `SpanProtocol`
(shared via import from an in-tree `fltk.fegen.pyrt` module) versus each protocol module's
local `Span` Protocol class and `CstModule` (both regenerated per grammar, never imported
across grammars).

## 4. Where would a shared file live for out-of-tree consumers?

Out-of-tree consumers already take a hard, unconditional dependency on
`fltk.fegen.pyrt.span_protocol` for every generated `cst.pyi`, regardless of which grammar
they generated from — this is enforced by the generator itself (the import line is emitted
unconditionally, not derived from the grammar). That means a downstream consumer's build
already assumes `fltk` (the library, not their own generated output) is importable at
type-check time and ships this particular shared protocol type.

`RustUnparserGenerator.generate_pyi`'s existing docstring
(`fltk/unparse/gsm2unparser_rs.py:117-118`) states: "Callers write this string next to the
generated `.rs` (`--pyi-output` overrides the path), exactly as the CST backend does" — i.e.
the unparser `.pyi` is written into the *consumer's own* package tree (their `mylang/`, not
FLTK's `fltk/_stubs/`), matching how `--pyi-output` places `cst.pyi` for the CST backend
(`fltk/fegen/genparser.py:446-450` shows the CLI examples: `--protocol-module
fltk.fegen.fltk_cst_protocol --pyi-output fltk/_native/fegen_cst.pyi` for an in-tree grammar,
`--protocol-module mylang.cst_protocol --protocol-output mylang/cst_protocol.py` for an
out-of-tree one).

The two committed `fltk/_stubs/*/unparser.pyi` files referenced by the TODO are themselves
FLTK's own in-tree fixtures/self-hosted grammars (`fegen_rust_cst` is FLTK's own grammar
compiled with the Rust backend; `rust_parser_fixture` is a test fixture under `tests/`) —
they are not examples of an out-of-tree consumer's generated output, so they don't
demonstrate what an out-of-tree consumer's directory layout would look like.

## 5. Summary of facts (no recommendation)

- Exactly 2 committed `unparser.pyi` files exist today; both carry the identical verbatim
  3-line `Doc` block. The TODO's stated count and block size match the code.
- The TODO's precedent claim ("mirroring how the CST side shares `CstModule`") does not
  correspond to any existing import-sharing mechanism for `CstModule` — `CstModule` is
  grammar-dependent and is independently regenerated in each of the six per-grammar protocol
  modules, never imported from a common file.
- A working precedent for a grammar-independent shared type *does* exist on the CST side,
  but it is `SpanProtocol` (`fltk.fegen.pyrt.span_protocol.SpanProtocol`, imported
  unconditionally by every `cst.pyi`), not `CstModule`.
- `.pyi` outputs (both CST's `cst.pyi` and the unparser's `unparser.pyi`) are written into
  the downstream consumer's own package tree via `--pyi-output`/`--protocol-output`, not into
  FLTK's `fltk/_stubs/`; the two committed `_stubs` files cited by the TODO are FLTK's own
  in-tree/test artifacts, not a downstream-consumer layout example.
