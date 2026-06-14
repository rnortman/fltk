# Exploration: shape of fltk._native's Rust lib.rs

Scope: `fltk._native` is the production pyo3 cdylib (`fltk-native` crate, `Cargo.toml:6-12`,
`[lib] name = "fltk_native" crate-type = ["cdylib"]`). Its `src/lib.rs` is *generated* by
`fltk/fegen/gsm2lib_rs.py` via `genparser gen-rust-native-lib` (`genparser.py:446-473`). Findings
below cite the generated file `src/lib.rs` and the generator that emits it.

## Code surface

- `src/lib.rs:1-28` — generated `#[pymodule] fn _native`. Registers, in order:
  - `Span`, `SourceText` classes at top level (`lib.rs:17-18`)
  - `UnknownSpan` module attr + `UNKNOWN_SPAN` `PyOnceLock` static (`lib.rs:12,19-24`)
  - submodule `"poc_cst"` from `mod cst_generated` (`lib.rs:25`)
  - submodule `"fegen_cst"` from `mod cst_fegen` (`lib.rs:26`)
- `src/span.rs:1-2` — two-line re-export: `pub use fltk_cst_core::{SourceText, Span};`
- `src/cst_generated.rs` — generated CST for a 3-rule toy grammar (NodeKind = IDENTIFIER, ITEMS,
  TRIVIA; `cst_generated.rs:31-37`; 6 `pub struct`s). Registered as `poc_cst`.
- `src/cst_fegen.rs` — generated CST for FLTK's *real* fegen grammar (NodeKind = GRAMMAR, RULE,
  ALTERNATIVES, ITEMS, ITEM, ...; `cst_fegen.rs:31+`; 28 `pub struct`s). Registered as `fegen_cst`.
- `fltk/fegen/gsm2lib_rs.py:167-182` — `native_spec()`, the factory that hardcodes this layout.
- `fltk/fegen/gsm2lib_rs.py:62-74` — `LibSpec.standard()`, the consumer-facing factory.

## Q1 — Why does `_native` include `poc_cst`? (test/PoC code in a production module)

`poc_cst` is the Python submodule name for the **proof-of-concept toy CST** generated into
`src/cst_generated.rs`. It contains only `Identifier`, `Items`, `Trivia` — a 3-rule throwaway
grammar (`cst_generated.rs:31-37`), distinct from FLTK's real grammar which lives in `cst_fegen.rs`
(28 node structs). The only things that consume `poc_cst` are **tests**:

- `tests/test_rust_cst_poc.py:8` — `from fltk._native.poc_cst import Identifier, Items`
- `tests/test_module_split.py:47-291` — a whole "§4.6 -- fltk._native.poc_cst" block asserting the
  PoC classes are reachable at `fltk._native.poc_cst` and *absent* from the `_native` top level.

No non-test code anywhere imports `poc_cst`. It is PoC/test fixture material that is nonetheless
compiled into and exported from the production `_native` module.

How it got into `lib.rs` — traced exactly: it is **not** an incidental artifact and **not**
hardcoded as a string literal in the `lib.rs` template. It is **declared as data in
`native_spec()`**: `gsm2lib_rs.py:177` constructs `Submodule("cst_generated", "poc_cst")`, and the
generator at `gsm2lib_rs.py:150-151` turns every `Submodule` into a
`register_submodule(m, "<submodule_name>", <mod_name>::register_classes)` line. So `lib.rs:25`'s
`register_submodule(m, "poc_cst", cst_generated::register_classes)` is the faithful rendering of
that one `native_spec()` entry. The file/name mismatch (file stem `cst_generated` → Python name
`poc_cst`) is deliberate and even has a dedicated test: `test_gsm2lib_rs.py:177-181`
(`test_native_spec_poc_cst_registration`, docstring "file/name mismatch"). The docstring at
`gsm2lib_rs.py:170-172` and the genparser help at `genparser.py:452-454` both describe this two-CST
layout as the intended, fixed shape of `_native`.

Assessment: `poc_cst` is test/PoC code that has been deliberately wired into the production
`_native` module by `native_spec()`. It is not leaking by accident — the generator input
explicitly lists it, and tests pin its presence — but its only consumers are FLTK's own tests, and
`native_spec()` is the single point where it is declared.

## Q2 — Why are Span / SourceText / UnknownSpan / UNKNOWN_SPAN here?

Where they are actually defined:

- `Span`, `SourceText` are defined in `crates/fltk-cst-core/src/span.rs` (`span.rs:56` struct
  SourceText, `span.rs:157` struct Span). `fltk-cst-core/src/lib.rs:18` re-exports them:
  `pub use span::{SourceText, Span, SpanError};`.
- `src/span.rs` (the root crate's module) is a 2-line pass-through re-export of those:
  `pub use fltk_cst_core::{SourceText, Span};` (`span.rs:1-2`). So `_native` does NOT define them;
  it pulls them from `fltk-cst-core`.
- `UnknownSpan` is a *module attribute* (a `Py<PyAny>` instance), not a type — created at module
  init from `Span::unknown()` (`lib.rs:19-20`; `Span::unknown()` is defined in
  `fltk-cst-core/src/span.rs:196`).
- `UNKNOWN_SPAN` is a crate-local `PyOnceLock<Py<PyAny>>` static declared inline in `lib.rs:12` and
  set once at init (`lib.rs:21-23`).

How/why they appear in `_native`'s lib.rs: `native_spec()` sets `register_span_types=True` and
`unknown_span_static=True` (`gsm2lib_rs.py:180-181`). The generator emits the `mod span;` +
`use span::{SourceText, Span};` block when `register_span_types` is set (`gsm2lib_rs.py:106-115`),
the `m.add_class` registrations in the pymodule body (`gsm2lib_rs.py:135-138`), and the
`UNKNOWN_SPAN` static + once-init when `unknown_span_static` is set
(`gsm2lib_rs.py:122-127,140-145`).

Necessity vs incidence: co-locating them with `_native`'s CST is a **deliberate canonicalization
decision, not incidental**. The generator comment at `gsm2lib_rs.py:117-121` and `lib.rs:11,16`
state the intent: the "canonical" `Span`/`SourceText`/`UnknownSpan` "live at the top level" of
`fltk._native`, and *other* extension cdylibs (downstream consumers) cache the sentinel at runtime
by importing `fltk._native.UnknownSpan` through their own `PyOnceLock` (`gsm2lib_rs.py:118-121`).
In other words, `_native` is intended to be the one module that *owns and exports* the canonical
span types across the pyo3 cdylib boundary (see `fltk-cst-core/src/cross_cdylib.rs`, re-exported at
`fltk-cst-core/src/lib.rs:12-13` as `extract_span`/`get_span_type`/`span_to_pyobject`). The actual
type *definitions* live in `fltk-cst-core` and are merely re-exported; what is genuinely tied to
`_native` is the *registration as the canonical Python-visible instance*, which is intentional.

## Q3 — Where is the parser?

FLTK's own generated parser is **not in `src/` at all**. `src/` contains only `lib.rs`, `span.rs`,
`cst_generated.rs`, `cst_fegen.rs` (no `parser.rs`). The parser runtime is a separate crate:

- `crates/fltk-parser-core/` — "pure-Rust runtime for FLTK-generated parsers"
  (`crates/fltk-parser-core/src/lib.rs:1`), providing `apply`, `Cache`, `PackratState`,
  `TerminalSource`, `ErrorTracker`, regex, etc.
- Generated *parser code* that uses that runtime exists only under `tests/` fixtures, e.g.
  `tests/rust_cst_fegen/src/parser.rs` and `tests/rust_parser_fixture/src/parser.rs`
  (both `use fltk_parser_core::{apply, ApplyResult, Cache, ErrorTracker, PackratState, TerminalSource};`).
- The root `fltk-native` crate (the `_native` cdylib) does **not** even depend on
  `fltk-parser-core`: root `Cargo.toml:14-16` lists only `pyo3` and `fltk-cst-core`. So no parser is
  compiled into `_native`.

The parser *generator* is `fltk/fegen/gsm2parser_rs.py` (the Rust counterpart to `gsm2parser.py`);
`genparser.py` exposes `gen-rust-parser` separately from `gen-rust-cst`.

## Q4 — Why does `_native` expose CST but not parser? (the asymmetry)

The asymmetry is real and **deliberate, governed entirely by `native_spec()`**:
`native_spec()` (`gsm2lib_rs.py:174-182`) lists exactly two submodules — `cst_generated→poc_cst`
and `cst_fegen→fegen_cst` — and **no parser submodule**. There is no `Submodule("parser", ...)` in
the `_native` spec, and the root crate carries no `fltk-parser-core` dependency, so the parser is
omitted by construction, not by oversight.

Contrast with the standard consumer path: `LibSpec.standard()` (`gsm2lib_rs.py:62-74`) defaults to
`with_parser=True` and appends `Submodule("parser", "parser")` alongside `Submodule("cst", "cst")`.
So a normal downstream extension built via `genparser gen-rust-lib --module-name X` gets *both* a
`cst` and a `parser` submodule (`genparser.py:431`), and can opt out with `--no-parser`. `_native`
does not use that path at all — it uses the bespoke `gen-rust-native-lib` command
(`genparser.py:446-461`) which always calls `native_spec()`.

Why `_native` omits the parser: `_native` exists to host (a) the canonical span types and (b) CST
node classes for FLTK's self-hosting — including the toy PoC CST. FLTK's actual parser exercising
is done in `tests/` fixture crates that pull `fltk-parser-core` directly. The pieces governing the
choice are: `native_spec()`'s submodule tuple (which CST modules) plus its
`register_span_types`/`unknown_span_static` flags (the span surface). Nothing in `native_spec()`
requests a parser, and the crate's `Cargo.toml` deps confirm none is linked.

## Forked vs config-driven: `native_spec()` vs the standard consumer path

The two paths share the *same* engine, `RustLibGenerator.generate()` (`gsm2lib_rs.py:86-159`),
which is fully data-driven off a `LibSpec` (submodule list + two booleans). `native_spec()` is
therefore **config-driven, not a forked code path** — it is just a second `LibSpec` factory
(`gsm2lib_rs.py:167-182`) that sets non-default values: two custom-named submodules with a
file/Python-name mismatch (`cst_generated→poc_cst`, `cst_fegen→fegen_cst`), plus
`register_span_types=True` and `unknown_span_static=True`, which `LibSpec.standard()` leaves at
their `False` defaults (`gsm2lib_rs.py:56-60`). The genuinely "special" parts of `_native` are
expressed purely as data: the span/UnknownSpan flags are first-class `LibSpec` knobs, and the
two-CST-no-parser shape is just a different submodule tuple. The only fork is at the CLI surface —
two separate typer commands (`gen-rust-lib` parameterized by `--module-name`/`--no-parser` vs the
parameterless `gen-rust-native-lib`) — and `native_spec()` being a hardcoded constant factory
rather than something a downstream consumer would call. So: the *layout is bespoke* (FLTK-internal,
fixed) but the *mechanism is shared and config-driven*; downstream consumers go through
`LibSpec.standard()` and never touch `native_spec()`.

## Open factual questions

- Whether `poc_cst` is intended to be removed before/after the Rust backend ships, or kept
  permanently as a self-hosting artifact — not determinable from code; `TODO.md` was not searched
  for a relevant slug here.
