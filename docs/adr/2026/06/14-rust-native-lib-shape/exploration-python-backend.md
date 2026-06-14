# Exploration: Python backend's runtime-vs-codegen split (reference for Rust refactor)

Scope: how FLTK's **Python** parser-generation backend separates (a) the shared,
grammar-agnostic runtime from (b) per-grammar codegenned parser + CST. This is the layout the
Rust side is meant to match, per the governing principle:

> "fltk._native contains the runtime for all fltk-generated parsers. It contains nothing specific
> to any specific grammar. No parsers. No cst. The fegen.fltkg parser and cst go into their own
> module somewhere. This is exactly how the python code is structured -- we 100% codegen the python
> fegen parser and cst, and the runtime stuff is all in completely separate modules that are not
> codegen."

All claims are anchored to current code with file:line.

---

## Q1 — Where does the shared, grammar-agnostic Python runtime live?

The runtime is the package **`fltk/fegen/pyrt/`** ("pyrt" = Python runtime). It is hand-written,
not codegenned, and contains nothing about any specific grammar. There is no `__init__.py` in it
(confirmed: `ls fltk/fegen/pyrt/__init__.py` → absent), so it is an implicit namespace package;
its modules are imported by full dotted path.

The runtime modules and what each provides:

- `fltk/fegen/pyrt/terminalsrc.py` — the **span / source-text types** plus the literal/regex
  terminal matcher. All hand-written, fully grammar-agnostic:
  - `SourceText` (`terminalsrc.py:8-22`) — immutable wrapper over a source string; mirrors the
    Rust `SourceText` Python surface.
  - `SpanKind` enum (`terminalsrc.py:24-45`) — discriminant for `Span.kind`.
  - `Span` (`terminalsrc.py:48-149`) — half-open `[start, end)` range with `text()`,
    `text_or_raise()`, `has_source()`, `len()`, `is_empty()`, `merge()`, `intersect()`,
    `with_source()`.
  - `UnknownSpan: Final = Span(-1, -1)` (`terminalsrc.py:152`) — the sentinel.
  - `LineColPos` (`terminalsrc.py:155-159`) and `TerminalSource` (`terminalsrc.py:162-205`) —
    `consume_literal`, `consume_regex`, `pos_to_line_col`.
- `fltk/fegen/pyrt/span.py` — the **backend-selector** module. Re-exports `SourceText`, `Span`,
  `UnknownSpan` from the pure-Python `terminalsrc`, then attempts to override them with the Rust
  `fltk._native` versions, warning on failure (`span.py:10-20`). This is the seam where the Python
  CST/parser pick up either the Python or Rust span backend.
- `fltk/fegen/pyrt/span_protocol.py` — `SpanProtocol` (`span_protocol.py:8-56`), the structural
  protocol both backends satisfy, and `AnySpan` union (`span_protocol.py:59-64`). Backend-agnostic.
- `fltk/fegen/pyrt/memo.py` — the **packrat parsing runtime**: `Packrat` (`memo.py:77-257`) with
  `apply()` (memoized + left-recursion), `MemoEntry`, `Poison`, `RecursionInfo`, `ApplyResult`
  (`memo.py:27-74`). Fully generic over `RuleId`/`PosType`; no grammar specifics.
- `fltk/fegen/pyrt/errors.py` — **error types / error formatting**: `ErrorTracker` and `ParseContext`
  (`errors.py:24-49`), `TokenType` (`errors.py:12-15`), `escape_control_chars` (`errors.py:96-123`,
  cross-backend byte-pinned to `crates/fltk-cst-core/src/escape.rs`), `format_error_message`
  (`errors.py:126-152`).

There is **no CST base class** in `pyrt`: each grammar's CST node classes are standalone generated
dataclasses (see Q2). The only "base"-like shared types CST nodes reference are `Span`/`SourceText`
from `terminalsrc`/`span`.

---

## Q2 — Where do the codegenned, per-grammar artifacts live?

For FLTK's own grammar (`fltk/fegen/fltk.fltkg`), the generated artifacts are **plain `.py` files
checked in next to the grammar**, in the same `fltk/fegen/` package but as separate modules with a
naming convention — never inside `pyrt`:

- `fltk/fegen/fltk_cst.py` — generated CST node classes. Header
  (`fltk_cst.py:1-13`): `from __future__ import annotations`, `import dataclasses/enum/...`,
  `import fltk.fegen.pyrt.terminalsrc`, and under `TYPE_CHECKING` `import fltk._native` +
  `import fltk.fegen.pyrt.span`. Defines `NodeKind` enum (`fltk_cst.py:16+`) and ~14 node
  dataclasses (`Grammar`, `Rule`, `Alternatives`, `Items`, `Item`, `Term`, ...).
- `fltk/fegen/fltk_cst_protocol.py` — generated CST `Protocol` module (the typing surface that both
  Python and Rust CSTs must satisfy).
- `fltk/fegen/fltk_parser.py` — generated parser (no-trivia). Header (`fltk_parser.py:1-8`) imports
  the runtime + the CST: `import fltk.fegen.fltk_cst`, `fltk.fegen.pyrt.errors`,
  `fltk.fegen.pyrt.memo`, `fltk.fegen.pyrt.span`, `fltk.fegen.pyrt.terminalsrc`. `class Parser`
  at `fltk_parser.py:11`.
- `fltk/fegen/fltk_trivia_parser.py` — generated trivia-preserving parser variant.

Naming/separation convention (from `genparser generate`, `genparser.py:120-253`):
`{base_name}_cst.py`, `{base_name}_cst_protocol.py`, `{base_name}_parser.py`,
`{base_name}_trivia_parser.py` (`genparser.py:150-153,176,195,220,234`). The runtime in `pyrt/`
is fully separate from these per-grammar files; the only relationship is imports (Q3).

Note on `bootstrap_*`: `fltk/fegen/bootstrap_cst.py`, `bootstrap_parser.py`, etc. are the
analogous generated artifacts for the bootstrap grammar (`bootstrap.fltkg`) — same convention,
also outside `pyrt`.

The Python package `fltk/_native/` is **not** a Python codegen output and **not** the Python
runtime — it is the stub directory for the compiled Rust pyo3 extension `fltk/_native.abi3.so`
(`fltk/_native/__init__.pyi:1-14`). The Python runtime is `pyrt`, not `_native`.

---

## Q3 — Import / dependency direction

Confirmed: **generated parser/CST import FROM the runtime; the runtime imports nothing
grammar-specific.**

Generated → runtime (proof):

- `fltk/fegen/fltk_parser.py:1-8` imports `fltk.fegen.fltk_cst` and the four runtime modules
  (`pyrt.errors`, `pyrt.memo`, `pyrt.span`, `pyrt.terminalsrc`). Body uses them, e.g.
  `fltk.fegen.pyrt.span.SourceText(...)`, `fltk.fegen.pyrt.memo.Packrat()`,
  `fltk.fegen.pyrt.errors.ErrorTracker()` (`fltk_parser.py:15-18`).
- `fltk/fegen/fltk_cst.py:9` imports `fltk.fegen.pyrt.terminalsrc`; node `span` fields are typed
  `fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span` defaulting to
  `fltk.fegen.pyrt.terminalsrc.UnknownSpan` (e.g. `fltk_cst.py:88,199,335,...`). The `fltk._native`
  side of that union is `TYPE_CHECKING`-only (`fltk_cst.py:12`); at runtime the concrete span type
  is resolved via `_get_native_span_type()` (`fltk_cst.py:63-64,477,...`) and
  `fltk.fegen.pyrt.span` (`fltk_cst.py:13`, gen at `gsm2tree.py:194-196`).

Runtime imports (proof it pulls in nothing grammar-specific):

- `pyrt/terminalsrc.py:1-5` — only `bisect, enum, re, dataclasses, typing`.
- `pyrt/memo.py:1-12` — only stdlib (`logging`, `collections.abc`, `dataclasses`, `enum`, `typing`).
- `pyrt/errors.py:1-7` — stdlib + `from fltk.fegen.pyrt import terminalsrc` (runtime → runtime only).
- `pyrt/span.py:8-13` — stdlib + `from fltk.fegen.pyrt.terminalsrc import ...` and the optional
  `from fltk._native import ...` (a backend, not a grammar). No import of any `*_cst` or `*_parser`.
- `pyrt/span_protocol.py:1-5` — stdlib + `fltk.fegen.pyrt.terminalsrc`.

So the direction is strictly generated-artifacts → `pyrt` (runtime) → stdlib/other-`pyrt`. The
runtime never imports `fltk_cst`, `fltk_parser`, or any grammar module.

---

## Q4 — What writes the generated Python files, and what governs output paths?

Entry point: the typer CLI `fltk/fegen/genparser.py`, command `generate`
(`genparser.py:120-253`). It writes four files into `output_dir` (default `.`,
`genparser.py:165-168`):

- CST: `genparser.py:176` `shared_cst = output_dir / f"{base_name}_cst.py"`. Built by
  `gsm2tree.CstGenerator(...).gen_py_module()` (`genparser.py:184-186`), unparsed via
  `ast.unparse` and written (`genparser.py:187-193`).
- CST protocol: `genparser.py:195` `{base_name}_cst_protocol.py`, via
  `cstgen.gen_protocol_module()` (`genparser.py:199-209`).
- Parsers: `generate_parser(...)` (`genparser.py:73-117`), called for the no-trivia file
  `{base_name}_parser.py` (`genparser.py:220-230`) and trivia file `{base_name}_trivia_parser.py`
  (`genparser.py:234-244`). Uses `gsm2parser.ParserGenerator` (`genparser.py:93`),
  `compiler.compile_class` + `pygen.module` + `ast.unparse` (`genparser.py:96-114`).

Generators:

- `fltk/fegen/gsm2tree.py` — `class CstGenerator` (`gsm2tree.py:33`); `gen_py_module()`
  (`gsm2tree.py:171`) emits the CST module, `gen_protocol_module()` (`gsm2tree.py:721`) the protocol.
- `fltk/fegen/gsm2parser.py` — `class ParserGenerator` (`gsm2parser.py:17`); registers the runtime
  import deps (`pyrt.memo` `:57`, `pyrt.terminalsrc` `:70`, `pyrt.span` `:81`).

What governs where output goes / how modules are named:

- **Filesystem path**: purely the `output_dir` + `{base_name}_*.py` template in `genparser.generate`
  (`genparser.py:176,195,220,234`). There is no path encoded in the generators themselves.
- **Logical import path baked into emitted code**: a `pyreg.Module(import_path=tuple[str,...])`
  (`fltk/iir/py/reg.py:11-13`). The CST module's import name is
  `pyreg.Module(cst_module_name.split("."))` (`genparser.py:91,183`), passed to `CstGenerator` as
  `py_module` (`gsm2tree.py:34-36`) and used to qualify generated type references
  (`gsm2tree.py:76,90,894`). The parser's import list (including the CST module and the four `pyrt`
  modules) is fixed in `generate_parser` (`genparser.py:97-105`). So *where files land* = CLI
  `output_dir`/`base_name`; *what import strings the generated code uses* = the `cst_module_name`
  argument + hardcoded `fltk.fegen.pyrt.*` runtime paths.

The Rust counterparts (`gsm2tree_rs.py`, `gsm2parser_rs.py`, `gsm2lib_rs.py`) are invoked via the
separate `gen-rust-cst` / `gen-rust-parser` / `gen-rust-lib` / `gen-rust-native-lib` commands and
take explicit output `Path` arguments (`genparser.py:265-473`).

---

## Q5 — Mapping onto the Rust side as it exists today

Correspondence (Python concept → current Rust location), per the prior exploration
(`docs/adr/2026/06/14-rust-native-lib-shape/exploration.md`) and the cited Rust files:

| Python (model) | Rust analog today |
| --- | --- |
| `fltk/fegen/pyrt/` (runtime: span types, packrat, errors) — hand-written, grammar-agnostic | Split across crates: `crates/fltk-cst-core/` (span/source types — `span.rs:56` `SourceText`, `:157` `Span`, `:196` `Span::unknown()`; cross-cdylib helpers `fltk-cst-core/src/lib.rs:12-13`) and `crates/fltk-parser-core/` ("pure-Rust runtime for FLTK-generated parsers", `fltk-parser-core/src/lib.rs:1`: `apply`, `Cache`, `PackratState`, `TerminalSource`, `ErrorTracker`). These two crates ARE the true runtime analog of `pyrt`. |
| Generated per-grammar CST (`fltk/fegen/fltk_cst.py`) | `tests/rust_cst_fegen/src/parser.rs` etc. for fixtures; **but FLTK's real fegen CST currently lives at `src/cst_fegen.rs`**, compiled into the `_native` cdylib and exported as the `fltk._native.fegen_cst` submodule (`src/lib.rs:18-19,26`; `gsm2lib_rs.py:178`). |
| Generated per-grammar parser (`fltk/fegen/fltk_parser.py`) | Generated parser code lives only in `tests/` fixtures (`tests/rust_cst_fegen/src/parser.rs`, `tests/rust_parser_fixture/src/parser.rs`, both `use fltk_parser_core::{...}`). FLTK's own fegen parser is **not** built into `_native` (root `Cargo.toml:14-16` lacks `fltk-parser-core`). |
| `fltk._native` = compiled-extension **stub for the runtime backend** (in Python it owns only span types via the selector `pyrt/span.py`) | The Rust `fltk._native` cdylib (`fltk-native` crate). Per the principle it should host ONLY the grammar-agnostic runtime surface (the canonical `Span`/`SourceText`/`UnknownSpan`), no CST, no parser. |

What the Python model says vs. where Rust currently puts things — the mis-placements:

1. **`fegen_cst` (FLTK's real grammar CST) is inside `fltk._native`.** Rust:
   `src/cst_fegen.rs` is registered as the `fltk._native.fegen_cst` submodule
   (`src/lib.rs:18-19,26`; declared in `native_spec()` at `gsm2lib_rs.py:178` as
   `Submodule("cst_fegen", "fegen_cst")`). Python model: FLTK's own grammar CST is a *separate*
   module (`fltk/fegen/fltk_cst.py`), **not** inside the runtime package `pyrt`. So under the
   principle, fegen CST should move OUT of `_native` into its own module/crate.

2. **`poc_cst` (toy PoC CST) is inside `fltk._native`.** Rust: `src/cst_generated.rs`, a 3-rule
   throwaway grammar (`cst_generated.rs:31-37`), registered as the `fltk._native.poc_cst`
   submodule (`src/lib.rs:17,25`; `native_spec()` `gsm2lib_rs.py:177`
   `Submodule("cst_generated", "poc_cst")`). Python model has **no** equivalent — there is no toy
   CST baked into any runtime module; it would be just another generated `*_cst.py` if it existed.
   So `poc_cst` is grammar-specific (test/PoC) content living in the runtime module, contrary to
   the principle.

3. **Span re-exports / canonical-span registration in `fltk._native`.** Rust: `src/span.rs:1-2`
   re-exports `fltk_cst_core::{SourceText, Span}`, and `src/lib.rs:11-24` registers `Span`,
   `SourceText`, `UnknownSpan` + the `UNKNOWN_SPAN` `PyOnceLock` static (driven by
   `native_spec()` flags `register_span_types=True`, `unknown_span_static=True`,
   `gsm2lib_rs.py:180-181`). This MATCHES the Python model: the runtime backend (`pyrt/span.py`,
   selecting `fltk._native`) is exactly the place that owns the canonical span types. So the span
   surface in `_native` is correctly placed; it is the CST submodules (`poc_cst`, `fegen_cst`)
   compiled into the same cdylib that violate "no cst" in `_native`.

4. **Parser placement is already model-consistent.** No parser is compiled into `_native` (root
   `Cargo.toml:14-16`); the parser runtime is the separate `fltk-parser-core` crate, mirroring
   Python's `pyrt.memo`/`pyrt.errors` being separate from any generated parser. Generated
   parsers live elsewhere (fixtures), as generated `*_parser.py` files live outside `pyrt`.

Net: to match the Python structure, `fltk._native` (Rust) should retain only the grammar-agnostic
runtime surface (span types + the `UnknownSpan` static, i.e. the `fltk-cst-core`/`fltk-parser-core`
re-export layer). The two CST submodules currently inside it — `poc_cst` (`src/cst_generated.rs`)
and `fegen_cst` (`src/cst_fegen.rs`) — are the mis-placed, grammar-specific pieces, declared by
`native_spec()` (`gsm2lib_rs.py:174-182`); in the Python model those would be standalone generated
modules outside the runtime package, analogous to `fltk/fegen/fltk_cst.py`.

---

## Open factual questions

- Where the Rust fegen CST/parser *should* land (which crate / module path) is a design choice not
  fixed by current code; this report only states the Python-model constraint (out of `_native`, in
  their own module) and the current Rust placement.
- Whether `poc_cst` is to be deleted vs. relocated is not determinable from code (noted in the
  prior exploration's open questions, `exploration.md:147-149`).
