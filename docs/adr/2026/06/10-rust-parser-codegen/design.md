# Design: Rust Parser Codegen

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Requirements: `request.md` in this directory. Facts: `exploration.md`. This doc decides the codegen approach (re-examining the 2026-05-25 ADR analysis), the architecture, and the implementation sequence.

---

## 1. Context

The Rust CST is complete: `gsm2tree_rs.py` emits a `.rs` file per grammar with handle/data split, `Shared<T>` ownership, and a `python` feature gate (`fltk/fegen/gsm2tree_rs.py`; `crates/fltk-cst-core`). Nothing exists for parser generation: no `gsm2parser_rs.py`, no Rust parser runtime, no `gen-rust-parser` CLI (exploration.md §6).

Goal: fltk generates Rust parsers usable from pure Rust (no pyo3 linked) or from Python. The parser class need not match the Python-generated `Parser` API — parsers don't cross the language boundary; CSTs do (request.md). The Python parser pipeline stays unchanged.

The CST data-struct API was explicitly designed as the parser's construction interface: `new(span)`, `set_span`, `push_child`, `append_<lbl>`, `extend_children` — all GIL-free (exploration.md §3.7; ADR 2026/06/10-rust-idiomatic-cst-api design §2 R4).

A Rust **unparser** generator will follow this work (out of scope here) and bears on the codegen-approach decision (§2.6).

---

## 2. Codegen approach: direct Rust emission, not an IIR→Rust compiler

**Decision: write `gsm2parser_rs.py` emitting Rust source strings directly (the `gsm2tree_rs.py` pattern). Do not build a Rust IIR compiler backend.**

The 2026-05-25 synthesis (`docs/adr/2026/05/25-rust-backend-exploration/synthesis.md`) made no recommendation itself; it presented Path 1 (IIR backend, ~3.3-4.6k LoC vs ~5.2-6k for per-language generators — Analysis 1's recommendation) as the lowest-LoC option, on the theory that the IIR is language-neutral and a Rust compiler is a thin syntax-directed translator reusing `gsm2parser.py` unchanged. That analysis predates the Rust CST and does not survive contact with it. Re-examination, point by point:

### 2.1 The IIR encodes the *Python* CST API, and the Rust CST API is structurally different

`gsm2parser.py` emits IIR like `result.append(child=..., label=None)` and `Construct.make(node_type, span=...)` (gsm2parser.py:653-659, 742-748). The Rust CST equivalents are not renamings — they are type-directed:

- Unlabeled span append → `node.push_child(None, GrammarChild::Span(span))`: the compiler must know the node's child-enum name and pick the variant from the *runtime type* of the child, information absent from the IIR call site.
- Node-typed append → `append_<lbl>(impl Into<Shared<T>>)` (tests/rust_cst_fegen/src/cst.rs:403): requires knowing the child is node-typed (wrap in `Shared`) vs span-typed (pass by value).
- Memoized results must be cached as `Shared<T>` so cache hits are Arc clones, mirroring Python's object-sharing semantics (§3.3). The IIR has no concept of this; the *generator* would have to change to express it.

So the "thin compiler" becomes a semantic transpiler carrying the GSM type model — or `gsm2parser.py` itself must be modified to emit backend-conditional IIR. Either way, the headline benefit ("reuse 2,305 generator lines unchanged") evaporates.

### 2.2 The IIR's structural decisions are Python-shaped at the ownership level

The memoizer body (gsm2parser.py:454-463):

```python
self.packrat.apply(rule_callable=self.parse_X.bind(), rule_id=N, rule_cache=self._cache__parse_X, pos=pos)
```

Translated literally to Rust, this is three simultaneous `&mut self` borrows (packrat state, bound method over all caches, one specific cache). It cannot compile. The Rust packrat must be restructured (generic `apply` with field-projection functions, recursion bookkeeping living in cache entries rather than aliased stack locals — §3.3). The IIR cannot express that restructuring; the structure would again have to come from generator changes or compiler intelligence.

### 2.3 "RefType becomes meaningful for free" is false in practice

synthesis.md §1 claims the generators already annotate mutability correctly. They don't: `consume_literal` is declared `mutable_self=False` (gsm2parser.py:152) yet mutates `self.error_tracker` (gsm2parser.py:171-180) and `parse_<rule>` bodies mutate memo caches transitively. Correct for Python; wrong for Rust. An IIR path requires auditing and fixing annotations across the working Python-path generators — exactly the "untouched existing code" the path was supposed to guarantee.

### 2.4 Rust needs constructs the IIR cannot represent

- Pre-compiled regexes as `static` items with `OnceLock` (the Python generator compiles at call time; gsm2parser.py:341 already has `# TODO pre-compile regexes`). IIR has no module-level items.
- `#[cfg(feature = "python")]` gating, dual-cfg enum blocks, `#[pymethods]`, registry wiring. `gsm2tree_rs.py` shows this surface is substantial and idiosyncratic (pyo3 0.23 attr-validation workarounds, gsm2tree_rs.py:340-345). A parser generated via IIR would still need a direct-emission companion for its Python bindings — two idioms in one artifact.

### 2.5 Precedent and consistency

`gsm2tree_rs.py` (1,533 lines) proves direct emission produces clean, reviewable, compilable output at this scale, and it already reuses the shared front-end: `gsm.classify_trivia_rules`, `CstGenerator` rule models for type info, `naming` helpers (gsm2tree_rs.py:46-54). `gsm2parser_rs.py` reuses the same front-end the same way. One codegen idiom in the codebase.

### 2.6 The future unparser does not rescue the IIR path

The IIR path's residual payoff would be "Rust unparser for free" by reusing `gsm2unparser.py` (~80 IIR call sites). But every mismatch above recurs there, amplified: the unparser is mutation-heavy (accumulator threading), uses raw `BinOp(op="is")` (synthesis.md §5), and its Rust runtime (~1.5-2k lines) dominates the work regardless of IR. Choosing direct emission here does commit the unparser to a future `gsm2unparser_rs.py` — that is the right commitment, for the same reasons, and consistency between parser and unparser codegen paths is itself worth something.

### 2.7 The honest cost of direct emission, and mitigation

Cost: the structural logic of `gsm2parser.py` (~830 lines: rule/alternative/item decomposition, memo wiring, separator handling, quantifiers, inline-to-parent) is re-expressed in `gsm2parser_rs.py`. Two generators can drift behaviorally.

Mitigations:
- **Parity tests are the contract** (§5): the same corpus through both parsers must produce structurally equal CSTs and equivalent failures. Drift becomes a test failure, not a latent divergence.
- `gsm2parser_rs.py` deliberately mirrors `gsm2parser.py`'s decomposition and naming (`parse_<rule>`, `apply__parse_<rule>`, `parse_<rule>__alt<N>__item<M>`, same path-tuple bookkeeping) so the two are side-by-side auditable.
- Shared front-end (GSM, trivia classification, `CstGenerator` models) means grammar *interpretation* is single-sourced; only code *rendering* is duplicated.

Path 3 (shared codegen-plan + thin renderers) is rejected now for the reason synthesis.md gives: it refactors working code for no immediate benefit. Revisit only if a third backend appears.

---

## 3. Architecture

### 3.1 New runtime crate: `crates/fltk-parser-core`

Workspace member. Depends on `fltk-cst-core` (default-features = false; for `Span`, `SourceText`) and `regex`. **Contains no pyo3 code at all** — no `python` feature needed. The generated parser's Python surface lives in the generated file and uses `fltk-cst-core`'s python-gated machinery. This keeps `fltk-cst-core` free of a `regex` dependency for CST-only consumers, and makes the pure-Rust-build guarantee trivial (`cargo tree` check, mirroring `check-no-pyo3`).

Contents (ports of `fltk/fegen/pyrt/`, ~600-900 lines per synthesis.md §3):

- **`ApplyResult<T> { pos: i64, result: T }`**, `MemoEntry`, and a `MemoResult<T>` enum (`Poison(Option<RecursionInfo>)` / `Value(T)` / `Failure`).
- **`TerminalSource`**: holds a `SourceText` (the single owner of the input text — `SourceText` is `Arc<SourceInner>`, span.rs:58-76) plus a codepoint-index table derived from it. The parser's spans are built against `&SourceText` obtained *from* the `TerminalSource`, so the text the spans reference is by construction the text being parsed, with no second copy. **Positions are codepoint indices (`i64`)**, matching the Python parser and `Span` semantics (exploration.md §7 Q6). Internally maps codepoint→byte offset (a `Vec<usize>` built once at construction). `consume_literal` compares chars; `consume_regex` calls `Regex::find_at(full_text, byte_pos)` and requires `match.start() == byte_pos` — searching the full haystack preserves look-behind context (`\b`/`\B`, and Python's pos-is-not-slicing `^` semantics), exactly reproducing Python `re.match(pos=...)` accept/reject behavior; worst case it scans-and-rejects where Python anchors (a perf difference, not correctness). Out-of-range `pos` in any `consume_*` returns `None` (parse failure), never panics or indexes out of bounds. `pos_to_line_col` ports the bisect logic (terminalsrc.py:183-205).
- **Regex handling**: the generated parser owns a static regex table (`OnceLock<Regex>` per distinct pattern); `TerminalSource::consume_regex` takes `&Regex`. `fltk-parser-core` re-exports the crate (`pub use regex;`) and generated code references `fltk_parser_core::regex::Regex` exclusively, so consumer crates need no direct `regex` dependency and runtime/generated-code version coherence is structural. Patterns are written in Python `re` syntax in grammars; the supported set is the common subset with the Rust `regex` crate (no lookaround/backreferences). Enforcement: the generator emits a `#[test]` asserting every pattern compiles, so unsupported patterns fail at `cargo test` time with the pattern named (generation-time validation from Python is deferred — it would require adding a `regex` dependency and binding to `fltk._native`; the generated `#[test]` suffices). Documented in the generator's docstring and ADR README.
- **`Packrat`** (the Warth/Douglass/Millstein seed-grow variant, memo.py:82-257), restructured for the borrow checker:
  - `PackratState { invocation_stack: Vec<u32>, recursions: HashMap<i64, RecursionInfo> }` is a field of the generated `Parser`.
  - `apply` is a generic free function parameterized over the parser type: `apply<P, T: Clone>(parser: &mut P, rule_id, pos, state: fn(&mut P) -> &mut PackratState, cache: fn(&mut P) -> &mut Cache<T>, rule: fn(&mut P, i64) -> Option<ApplyResult<T>>)`. All state access re-borrows through `parser`, so the rule callable can recurse freely.
  - Python mutates a `Poison` object aliased between stack frames (memo.py:112-122, 206-226). Rust instead keeps the poison/recursion info inside the cache entry and re-fetches the entry from the map after the rule call returns. Same algorithm, ownership-safe expression.
  - The deliberately-unimplemented corner case (memo.py:181-187, `NotImplementedError`) becomes a `panic!` with the same explanation — matching Python's fail-loudly choice.
- **`ErrorTracker`** + `format_error_message` port (errors.py): farthest-failure tracking and the same human-readable format, as plain Rust returning `String`.

TDD vehicle: `fltk/fegen/pyrt/test_memo.py` cases (direct/indirect/multi left recursion, failure) port to Rust unit tests against a hand-written toy parser before any codegen exists.

### 3.2 Generator: `gsm2parser_rs.py` + `gen-rust-parser` CLI

- Class `RustParserGenerator(grammar)` mirroring `RustCstGenerator`'s shape: validates identifiers, reuses `CstGenerator` rule models for child-type info, emits one complete `.rs` string.
- CLI command `gen-rust-parser <grammar.fltkg> <output.rs> [--cst-mod-path super::cst]` in `genparser.py`, parallel to `gen-rust-cst` (genparser.py:264). The `--cst-mod-path` option parameterizes the `use` path to the generated CST module, since consumer crates control their own module layout (fixture layout: `src/cst.rs` + `src/parser.rs`, `mod` declared in `lib.rs`).
- Generated structure mirrors the Python parser (exploration.md §2.3): `pub struct Parser` holding `TerminalSource` (which owns the `SourceText`; span construction borrows it via accessor — §3.1), `PackratState`, `ErrorTracker`, `capture_trivia: bool`, and one typed cache field per memoized rule (`HashMap<i64, MemoEntry<Shared<NodeT>>>`). Methods keep the Python naming scheme (`parse_<rule>`, `apply__parse_<rule>`, `parse_<rule>__alt<N>__item<M>`) for cross-backend auditability; all take `&mut self, pos: i64` and return `Option<ApplyResult<...>>`.
- **Result types**: memoized rule parsers return `ApplyResult<Shared<NodeT>>` — the node is wrapped in `Shared` at the memoization boundary, cached as `Shared`, and cache hits Arc-clone. This reproduces Python's semantics where a cached node *object* is appended into multiple parents (DAG sharing), which `Shared<T>` children represent natively (exploration.md §3.3). Non-memoized item/alternative parsers return nodes by value or `Span` for terminals; at inline-to-parent sites the parent calls `extend_children(&result)`, which Arc-clones the children, and the by-value local is then dropped.
- **Child appends are fully type-directed at generation time**: the generator knows from the rule model whether an item is span-typed (`append_<lbl>(span)` / `push_child(None, XChild::Span(s))`), single-node-typed (`append_<lbl>(shared)` via `Into<Shared<T>>`), or a union label (construct the explicit `XChild` variant). This is the information the IIR path could not carry (§2.1).
- **Trivia handling: one parser, runtime flag.** Python generates two modules differing only in `context.capture_trivia` (genparser.py:85; exploration.md §2.2). The Rust generator emits a single `Parser` with a `capture_trivia: bool` constructor parameter; the trivia-append sites become `if self.capture_trivia { ... }`. Rationale: the divergence between the two Python variants is a handful of append statements; a runtime branch costs nothing measurable, halves generated code, and no compatibility constraint exists (no Rust parser consumers yet; request.md explicitly frees the parser API). Parity tests run the flag both ways against both Python variants.
- Errors mirror Python: `consume_literal`/`consume_regex` failures report `rule_id = invocation_stack.last()` to the tracker (gsm2parser.py:171-180); top-level entry is always via `apply__*`, so the stack is non-empty at failure sites (same invariant as Python).

### 3.3 Python bindings (generated, `#[cfg(feature = "python")]`)

In the same generated parser `.rs`, gated like the CST's handle layer:

- `#[pyclass(name = "Parser")] struct PyParser` holding the native `Parser` directly. Unlike the CST handles, this pyclass is *not* `frozen`: pymethods take `&mut self` and pyo3's runtime borrow checking handles aliasing. No `Shared`/registry machinery — parsers never cross the boundary or need identity stability.
- Constructor `Parser(text: str, capture_trivia: bool = False)`. Simpler than the Python backend's `Parser(terminalsrc=TerminalSource(text))`; permitted by request.md ("different parser classes ... acceptable").
- Per memoized rule: `apply__parse_<rule>(pos: int) -> ApplyResult | None`. Method names match the Python parser so downstream call sites (`parser.apply__parse_grammar(0)`, plumbing.py:135) port with minimal churn even though the class differs. The returned object is a tiny generated `#[pyclass] ApplyResult { pos: i64, result: PyObject }` with `.pos`/`.result` getters; `.result` is the canonical CST handle via `Py<Node>::to_py_canonical` (registry identity rules apply unchanged).
- `rule_names` getter, `error_message() -> str` (Rust-side `format_error_message`), and `error_position() -> int | None` (farthest-failure codepoint position, `None` if no failure recorded). The Python backend's `error_tracker` attribute is *not* replicated; consumers on the Rust parser use `error_message()`/`error_position()`. This is the one deliberate API divergence beyond the constructor; the scalar position accessor gives parity tests and programmatic consumers what they need without exposing tracker internals across the boundary.
- The crate-level feature plumbing is the existing fixture pattern (tests/rust_cst_fegen/Cargo.toml): pure-Rust consumers build with `default-features = false` and link no pyo3.

### 3.4 Build/tooling integration

- `crates/fltk-parser-core` joins the workspace; `cargo-test` covers it; a `check-no-pyo3`-style assertion confirms it never pulls pyo3.
- Fixture crates (`tests/rust_cst_fegen`, new or extended) gain `src/parser.rs` generated by `gen-rust-parser`; Makefile targets `gen-rust-parser` (regeneration) and build/test wiring mirror `gen-rust-cst`. Regen → `make fix` → commit flow unchanged.
- `fltk._native` is untouched in early phases; in-tree adoption (Rust fegen parser inside test fixtures) exercises the full path without changing shipped modules.

---

## 4. Edge cases / failure modes

- **Multibyte input**: codepoint/byte confusion is the highest-risk correctness bug. `TerminalSource` unit tests and parity corpus must include non-ASCII inputs (literals, regexes, and error line/col reporting over multibyte text).
- **Regex semantics drift**: beyond compile failures (caught by the generated test, §3.1), the same pattern can match differently (Python `re` vs `regex` crate Unicode classes). Both are Unicode-aware for `\s`/`\d`/`\w` by default; parity tests over grammar-realistic inputs are the backstop. Context-sensitive assertions (`\b`/`\B`, `^`) are handled correctly by the `find_at`-on-full-haystack design (§3.1) — slicing at `pos` would have silently diverged for out-of-tree grammars the in-tree parity corpus cannot see. Patterns using unsupported syntax fail loudly at `cargo test`.
- **Left-recursion fidelity**: the restructured cache-entry-based poison bookkeeping must replicate memo.py exactly. Ported `test_memo.py` cases plus the recursive-grammar regression inputs (`test_regression_toplevel_recursion.py`, `test_regression_recursive_inlining.py`) gate this.
- **Cached-node sharing**: a memo hit Arc-clones `Shared<NodeT>` into a parent; if that alternative later fails, the clone is dropped — no cache corruption. Mutating nodes *after* parse mutates cache-shared structure identically to Python (same object); not a divergence.
- **`+` quantifier zero-progress check** (gsm2parser.py:581-585), WS_REQUIRED failure (gsm2parser.py:682-683), leading separators, empty-nary, trailing-character behavior: each has an existing Python regression test whose inputs feed the parity corpus.
- **Panics**: the parser must not panic on any *input or position argument* — the pure-Rust entry points (`apply__parse_<rule>(pos: i64)`) are first-class API for out-of-tree consumers, where an unwind across a cdylib boundary can abort. Contract: out-of-range or negative `pos` at any native entry point or `consume_*` is a parse failure (`None`), enforced by the bounds checks in `TerminalSource` (§3.1); the Python boundary additionally validates `pos >= 0 && pos <= len` to give a clean `ValueError` instead of a silent failure. The only panics are the documented memo.py:181 corner (also a crash in Python) and regex-table initialization (caught by the generated compile test before any input is parsed).
- **`i64` positions**: negative positions are sentinel-only (`Span(-1,-1)`); position handling never goes through `as usize` wraparound — codepoint→byte lookup is bounds-checked per the contract above.
- **Unsupported GSM terms**: `gsm.Invocation`/`Expression` raise `NotImplementedError` in the Python generator (gsm2parser.py:374-375); `gsm2parser_rs.py` raises identically at generation time.

---

## 5. Test plan

After completion, the following exist:

1. **Runtime unit tests (Rust, `fltk-parser-core`)**: `TerminalSource` (ASCII + multibyte literals/regex/line-col), `Packrat` (ports of all `test_memo.py` cases via a hand-written toy parser), `ErrorTracker` + message formatting.
2. **Generated-parser Rust tests**: fixture crate parses fegen-grammar snippets pure-Rust (no Python in the loop), asserting tree shape via the CST data-struct accessors; the generated regex-compile `#[test]`.
3. **Cross-backend parity tests (Python, pytest)**: a corpus (inputs from every `test_regression_*.py`, `test_trivia_capture.py`, `test_leading_separators.py`, fegen.fltkg itself, multibyte cases) parsed by the Python-generated parser and the Rust parser (via bindings); a structural comparator walks both trees asserting kind/label/span-start/span-end equality recursively (node-level cross-backend `__eq__` is not assumed). Failure cases assert both backends fail at the same farthest position (Rust side via the `error_position()` accessor, §3.3) and that `error_message()` matches the Python-side `format_error_message` output. Both `capture_trivia` settings, compared against the corresponding Python variant.
4. **Self-hosting integration**: extend the phase-4 pattern (`tests/test_phase4_fegen_rust_backend.py`): Rust parser → Rust CST → real `Cst2Gsm` over fegen.fltkg produces a GSM equal to the Python path's.
5. **Build checks**: workspace `cargo test`; no-pyo3 assertion for `fltk-parser-core` and for the fixture parser crate built `--no-default-features`; `make check` green including regenerated committed artifacts.

---

## 6. Implementation sequence

Each phase is independently landable and TDD-able:

1. **Phase 1 — runtime crate** (`fltk-parser-core`): types, `TerminalSource`, `Packrat`, `ErrorTracker`; toy-parser tests incl. ported memo tests. No codegen.
2. **Phase 2 — generator, pure-Rust output**: `gsm2parser_rs.py`, `gen-rust-parser` CLI, fixture crate `parser.rs` compiling python-off and python-on, Rust-side parse tests (test plan item 2).
3. **Phase 3 — Python bindings + parity**: generated `PyParser`/`ApplyResult` surface, parity corpus and comparator (test plan item 3).
4. **Phase 4 — integration**: Makefile/`make check` wiring, no-pyo3 checks, self-hosting test (items 4-5), ADR README recording the §2 decision.

---

## 7. Open questions

1. **Regex escape hatch**: if a downstream grammar's pattern is outside the `regex`-crate subset (lookaround/backreferences), is "fails the generated compile test; rewrite the pattern" an acceptable permanent answer, or should the generator grow an opt-in `fancy_regex` mode later? Proposed default: subset-only, documented; revisit on demand. (No in-tree grammar is affected.)

USER A1. Simple `regex` is fine so long as we get an error at compile time for anything unsupported. We will address this in the future if a need arises for fancier regex.

2. **Adoption scope**: should `plumbing.py` / the Python test harness gain a selectable "Rust parser" backend in this effort (beyond the parity/self-host tests), or is in-tree adoption a separate follow-up? Phasing above assumes follow-up.

USER A2. plumbing.py is a convenience tool for boilerplate reduction in common cases, heavily used in unit tests for example to reduce boilerplate. Rust will likely need boilerplate reduction, but it need not fit the plumbing.py shape. And the boilerplate for direct Rust callers will be different than the boilerplate for Python callers of the wrapped Rust parsers. So: Convenience functions for boilerplate reduction yes, fitting plumbing.py exactly is not a requirement (and since we can't really do dynamic Rust compilation we really can't fit that shape anyway.) Boilerplate reduction can be considered out of scope for this design, except to the extent that we need it for our own unit tests anyway (in which case definitely do it).
