# Design: Phase 2 — Rust Parser Generator, Pure-Rust Output

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Controlling design: `docs/adr/2026/06/10-rust-parser-codegen/design.md` (§2 decides direct emission; §3.2 sketches this generator; §6 defines Phase 2). Requirements: `docs/adr/2026/06/10-rust-parser-codegen/request.md`. Phase 1 runtime (implemented): `docs/adr/2026/06/10-rust-parser-runtime-crate/design.md`, `crates/fltk-parser-core/`. Facts: `exploration.md` in this directory. This doc is the detailed implementation plan for Phase 2 only — `gsm2parser_rs.py`, the `gen-rust-parser` CLI, fixture parser crates, and Rust-side parse tests. No Python bindings (Phase 3), no parity corpus (Phase 3), no self-hosting test (Phase 4).

---

## 1. Context

Phase 1 delivered `fltk-parser-core`: `apply` (generic packrat memoizer), `TerminalSource` (codepoint-indexed, source-bearing spans), `ErrorTracker` + `format_error_message` (crates/fltk-parser-core/src/lib.rs:24-26). Phase 2 makes fltk emit a `.rs` parser per grammar that drives that runtime and builds CSTs through the generated data-struct API (`tests/rust_cst_fegen/src/cst.rs`). The Python generator `gsm2parser.py` (832 lines) and its generated output `fltk_parser.py` are the behavioral reference; `gsm2tree_rs.py` (RustCstGenerator) is the structural precedent for a direct-emission generator.

Deliverables: `fltk/fegen/gsm2parser_rs.py`, `gen-rust-parser` command in `genparser.py`, generated `parser.rs` in two fixture crates (fegen grammar + a new feature-coverage grammar) compiling python-off and python-on, Rust-side parse tests, regen/build wiring sufficient to land green.

---

## 2. Proposed approach

### 2.1 Generator: `fltk/fegen/gsm2parser_rs.py`

Class `RustParserGenerator`:

```python
class RustParserGenerator:
    def __init__(self, grammar: gsm.Grammar, cst_mod_path: str = "super::cst",
                 source_name: str | None = None): ...
    def generate(self) -> str: ...
```

- Takes the **raw** grammar (CLI uses `_parse_grammar_raw`, genparser.py:254). Internally composes `self._cst = gsm2tree_rs.RustCstGenerator(grammar)`, which applies `add_trivia_rule_to_grammar` + `classify_trivia_rules` and validates all rule names and labels (gsm2tree_rs.py:47-81). The parser generator works from `self._cst.grammar` (the processed grammar) and queries the CST generator for every type decision — class names (`self._cst._py_gen.class_name_for_rule_node`), label typing (`self._cst._label_type_info`, gsm2tree_rs.py:1038), child variant sets (`self._cst._child_variants_for_rule`, gsm2tree_rs.py:110). Composition makes parser/CST emission agree by construction: the appended-to enum variants are computed by the same code that emitted them. The three queried underscore methods are in-package use of module-internal API; no refactor of `gsm2tree_rs.py` (their docstrings already specify their contracts).
- Mirrors `gsm2parser.py`'s decomposition and naming for side-by-side auditability (controlling design §2.7): `RustParserFn` dataclass (≈ `ParserFn`, gsm2parser.py:19-26), `self.parsers: dict[tuple[str, ...], RustParserFn]` keyed by the same path tuples, two passes (first `_make_parser_info` per top-level rule assigning `rule_id` = index in `grammar.rules`, then `gen_alternatives_parser` per rule), and the same method-family names: `gen_alternatives_parser`, `gen_alternative_parser`, `gen_item_parser`, `gen_item_parser_single_or_optional`, `gen_item_parser_multiple`, `_gen_separator_handling`, `_gen_consume_term_expr`. Bodies emit Rust source strings instead of IIR. Module doc comment names `gsm2parser.py` as the reference (Phase 1 convention).

```python
@dataclass
class RustParserFn:
    name: str                 # "parse_grammar", "parse_items__alt0__item0__alts", ...
    apply_name: str           # "apply__parse_grammar" iff memoized, else == name
    cache_field: str | None   # "cache__parse_grammar" iff memoized
    result: ResultTy          # Span | Node(class_name); memoized ⇒ Shared<Node> in signatures
    rule_id: int | None       # index into grammar.rules iff memoized
    inline_to_parent: bool
```

`ResultTy` is a tiny tagged type (`span` vs `node(class_name)`); this is the GSM-type-directed information the IIR could not carry (controlling design §2.1).

- **Regex table**: patterns deduplicated in first-occurrence order into `self.regex_patterns: list[str]` / `self.regex_index: dict[str, int]`. The trivia-rule separator pattern `r"\s+"` (gsm2parser.py:643) goes through the same table. Patterns and literals are rendered into Rust string literals by one helper `_rust_str_lit(s)`: escape `\`, `"`, and chars `< 0x20` plus `\x7f` as `\u{...}`; all other chars (incl. non-ASCII) verbatim. One escaping path for everything; raw strings rejected for uniformity (correctness over prettiness in generated code).
- **Unsupported terms**: `gsm.Invocation` / `gsm.Expression` raise `NotImplementedError` at generation time with the same message shape as gsm2parser.py:374-375. `gsm.Disposition.INLINE` items raise `NotImplementedError` (mirror gsm2parser.py:768-770).
- Output is deterministic (insertion-ordered dicts, grammar-order iteration).

### 2.2 Generated file anatomy

One `.rs` file, sections in order. Method and field names keep the Python scheme exactly (`parse_<rule>`, `apply__parse_<rule>`, `parse_<rule>__alt<N>__item<M>`, `cache__parse_<rule>`); double underscores are valid snake_case, no lint fires.

**1. Header + imports.** `//!` doc: "Generated by fltk gen-rust-parser from `<source_name>`. Do not edit. Reference implementation: gsm2parser.py / the Python-generated parser." `source_name` is the constructor parameter (§2.1); the CLI passes the grammar file name. When `None`, the "from `<source_name>`" clause is omitted (unit tests constructing from in-memory GSM need no fake filename).

```rust
use std::sync::OnceLock;
use fltk_cst_core::{Shared, SourceText, Span};
use fltk_parser_core::regex::Regex;
use fltk_parser_core::{ApplyResult, Cache, ErrorTracker, PackratState, TerminalSource};
use super::cst;   // path from --cst-mod-path; `as cst` alias appended when the path's last segment is not `cst`
```

All CST references go through the `cst::` path (`cst::Grammar`, `cst::GrammarChild::Rule`), so a single generator knob (`cst_mod_path`) controls them and generated identifiers can never collide with CST type names.

**2. Rule names + regex table.**

```rust
pub const RULE_NAMES: [&str; 14] = ["grammar", "rule", /* grammar.rules order */];

const REGEX_PATTERNS: [&str; R] = ["[_a-z][_a-z0-9]*", "\\s+", /* first-occurrence order */];
static REGEX_CELLS: [OnceLock<Regex>; R] = [OnceLock::new(), OnceLock::new(), /* R literal items */];

fn regex_at(idx: usize) -> &'static Regex {
    REGEX_CELLS[idx].get_or_init(|| {
        Regex::new(REGEX_PATTERNS[idx])
            .unwrap_or_else(|e| panic!("invalid regex pattern {:?}: {e}", REGEX_PATTERNS[idx]))
    })
}
```

The cell array is emitted as a literal list of `OnceLock::new()` (a `const fn`; no `[const {...}; N]` — works on every toolchain, trivially emitted). The regex table, `regex_at`, and `consume_regex` are emitted only when the grammar has at least one regex (`consume_literal` likewise only when a literal exists) — unconditional emission of unused private items fails the `-D warnings` clippy lanes via `dead_code`. The corresponding imports are conditional under the same predicate: `use std::sync::OnceLock;` and `use fltk_parser_core::regex::Regex;` are emitted only with the regex table (otherwise `unused_imports` fails the same lanes); every other import in the §item-1 block is used unconditionally. The zero-regex case is reachable: a grammar with its own literal-only `_trivia` rule suppresses the default `[\s]+` rule (gsm.py:380-401), and the `\s+` separator pattern enters the table only via separators inside trivia rules (gsm2parser.py:641-650). `RULE_NAMES` order must equal the Python parser's `rule_names` (fltk_parser.py:19-34) — same source (`grammar.rules` after trivia processing), same order; this is what makes Phase 3 error-message parity possible.

**3. Parser struct + constructor.**

```rust
pub struct Parser {
    terminals: TerminalSource,
    packrat: PackratState,
    error_tracker: ErrorTracker,
    capture_trivia: bool,
    cache__parse_grammar: Cache<Shared<cst::Grammar>>,
    /* ... one cache field per rule, grammar order ... */
}

impl Parser {
    pub fn new(text: &str, capture_trivia: bool) -> Self { /* TerminalSource::new */ }
    pub fn from_source_text(source: SourceText, capture_trivia: bool) -> Self { /* no copy */ }
    pub fn terminals(&self) -> &TerminalSource { ... }
    pub fn capture_trivia(&self) -> bool { self.capture_trivia }
    pub fn rule_names(&self) -> &'static [&'static str] { &RULE_NAMES }
    pub fn error_message(&self) -> String {
        fltk_parser_core::format_error_message(&self.error_tracker, &self.terminals, &RULE_NAMES)
    }
    pub fn error_position(&self) -> Option<i64> {
        (self.error_tracker.longest_parse_len >= 0).then_some(self.error_tracker.longest_parse_len)
    }
    ...
}
```

`PackratState::default()`, `ErrorTracker::default()`, empty caches. One parser, runtime `capture_trivia` flag (controlling design §3.2, replacing Python's two generated modules). `error_message`/`error_position` are generated in Phase 2: the Rust-side tests need them and Phase 3's pyclass merely delegates. `from_source_text` exists because `TerminalSource::from_source_text` does (terminalsrc.rs:55) and the parser's fields are private. The `capture_trivia()` getter doubles as the structural guarantee that the field is always read (a grammar whose separators are all `NO_WS` has no capture sites; without the getter, `dead_code` would fire).

**Visibility**: `pub` = constructors, accessors above, and `apply__parse_<rule>` per rule. Everything else (`parse_*` bodies, item/alt parsers, `consume_*`) is private. This makes the Python invariant "all entry is via `apply__*`" (controlling design §3.2) *structural* in Rust: the invocation stack is provably non-empty at every `consume_*` failure site, so the `.expect()` below is unreachable rather than input-dependent — consistent with the no-panic contract (controlling design §4) and Phase 1's assertion policy.

**4. `consume_literal` / `consume_regex`** (≈ fltk_parser.py:78-96, minus the `with_source` re-wrap — Phase 1's `TerminalSource` returns source-bearing spans already, Phase 1 design §2.3):

```rust
fn consume_literal(&mut self, pos: i64, literal: &'static str) -> Option<ApplyResult<Span>> {
    if let Some(span) = self.terminals.consume_literal(pos, literal) {
        return Some(ApplyResult { pos: span.end(), result: span });
    }
    let rule_id = *self.packrat.invocation_stack.last()
        .expect("consume_literal outside apply__* frame (unreachable: all pub entry is via apply__*)");
    self.error_tracker.fail_literal(pos, rule_id, literal);
    None
}

fn consume_regex(&mut self, pos: i64, regex_idx: usize) -> Option<ApplyResult<Span>> {
    if let Some(span) = self.terminals.consume_regex(pos, regex_at(regex_idx)) {
        return Some(ApplyResult { pos: span.end(), result: span });
    }
    let rule_id = *self.packrat.invocation_stack.last().expect(/* as above */);
    self.error_tracker.fail_regex(pos, rule_id, REGEX_PATTERNS[regex_idx]);
    None
}
```

`consume_regex` takes the table index so the error tracker reports the verbatim grammar pattern (`&'static str`, errors.rs:64) — identical to the string Python reports, which Phase 3 message parity requires. For auditability, call sites carry the pattern in a `//` comment on the preceding line (newlines in the pattern escaped; a trailing `/* ... */` form is ruled out because a pattern may itself contain `*/`).

**5. Per-rule memoizer + rule body** (≈ fltk_parser.py:98-108):

```rust
pub fn apply__parse_grammar(&mut self, pos: i64) -> Option<ApplyResult<Shared<cst::Grammar>>> {
    fltk_parser_core::apply(self, 0, pos, |p| &mut p.packrat, |p| &mut p.cache__parse_grammar, Self::parse_grammar)
}

fn parse_grammar(&mut self, pos: i64) -> Option<ApplyResult<Shared<cst::Grammar>>> {
    if let Some(alt0) = self.parse_grammar__alt0(pos) {
        return Some(ApplyResult { pos: alt0.pos, result: Shared::new(alt0.result) });
    }
    None
}
```

Non-capturing closures coerce to the `fn` projectors `apply` requires (memo.rs:102-109). The `Shared::new` wrap happens once, in the rule body: alternatives build nodes by value; the memo boundary is where Python's object-sharing semantics start mattering, and `Cache<Shared<NodeT>>` makes every cache hit an Arc clone (controlling design §3.2). Multi-alternative rules chain `if let` blocks in order, exactly like fltk_parser.py:706-715.

**6. Alternative bodies** (≈ fltk_parser.py:150-182; gen_alternative_parser, gsm2parser.py:722-831):

```rust
fn parse_rule__alt0(&mut self, mut pos: i64) -> Option<ApplyResult<cst::Rule>> {
    let span_start = pos;
    let mut result = cst::Rule::new(Span::new_with_source(pos, -1, self.terminals.source_text()));
    // initial_sep handling here when != NO_WS (gsm2parser.py:754)
    if let Some(item0) = self.parse_rule__alt0__item0(pos) {
        pos = item0.pos;
        result.append_name(item0.result);          // append shape: see §2.3
    } else {
        return None;                                // required item
    }
    if let Some(ws) = self.apply__parse__trivia(pos) {   // WS_ALLOWED separator
        pos = ws.pos;
        if self.capture_trivia {
            result.push_child(None, cst::RuleChild::Trivia(ws.result));
        }
    }
    /* ... remaining items + separators ... */
    result.set_span(Span::new_with_source(span_start, pos, self.terminals.source_text()));
    Some(ApplyResult { pos, result })
}
```

- Optional items (`?`): same `if let` without the `else { return None }` (gsm2parser.py:784, 802-804).
- `WS_REQUIRED` separators: add `else { return None; }` to the trivia `if let` (gsm2parser.py:682-683).
- Trivia-rule bodies (`rule.is_trivia_rule`): separators use `self.consume_regex(pos, <idx of "\s+">)` instead of `apply__parse__trivia` (gsm2parser.py:641-659); the capture append is `result.push_child(None, cst::TriviaChild::Span(ws.result))`. `TriviaChild` has a `Span` variant and non-trivia child enums have `Trivia(Shared<Trivia>)` variants exactly where separators permit trivia — the CST model adds them unconditionally of `capture_trivia` (verified: tests/rust_cst_fegen/src/cst.rs `GrammarChild`/`RuleChild`/.../`TermChild` carry `Trivia`, `TriviaChild` carries `Span`), which is what makes the single-parser/runtime-flag design compile.
- Suppressed items (`Disposition.SUPPRESS`, and Python's unlabeled-literal default): advance `pos`, no append (gsm2parser.py:788).

**7. Item parsers.** Single/optional delegate (≈ fltk_parser.py:184-187):

```rust
fn parse_rule__alt0__item0(&mut self, pos: i64) -> Option<ApplyResult<Shared<cst::Identifier>>> {
    self.apply__parse_identifier(pos)
}
```

Return type per term: Identifier → the referenced rule's memoized type `Shared<cst::T>`; Literal/Regex → `Span` via `consume_*`; sub-expression (`Sequence`) → a generated non-memoized `parse_<path>__alts` returning the **parent** node type by value, `inline_to_parent = true` (gsm2parser.py:355-372).

Multiple (`+`/`*`) item parsers (≈ fltk_parser.py:127-140; gsm2parser.py:505-604):

```rust
fn parse_grammar__alt0__item0(&mut self, mut pos: i64) -> Option<ApplyResult<cst::Grammar>> {
    let span_start = pos;
    let mut result = cst::Grammar::new(Span::new_with_source(pos, -1, self.terminals.source_text()));
    while let Some(one_result) = self.apply__parse_rule(pos) {
        pos = one_result.pos;
        result.append_rule(one_result.result);
    }
    if pos == span_start {       // emitted only for `+` (min != ZERO, gsm2parser.py:581-585)
        return None;
    }
    result.set_span(Span::new_with_source(span_start, pos, self.terminals.source_text()));
    Some(ApplyResult { pos, result })
}
```

Inline-to-parent loop bodies use `result.extend_children(&one_result.result);` instead of the labeled append (gsm2parser.py:568-573); `extend_children(&Self)` clones `(label, child)` pairs — Arc clones for nodes (cst.rs:339).

### 2.3 Append-site selection (type-directed, the core of the design)

One generator helper decides every append statement from the GSM item + the CST model. Inputs: `current_rule.name`, `item` (label, disposition, term), the item parser's `ResultTy` and `inline_to_parent`. Decision table (disposition `SUPPRESS` already filtered out; `inline_to_parent` already handled via `extend_children`):

| Item shape | CST model fact (via `_label_type_info`) | Emitted statement |
|---|---|---|
| labeled, span result | label is span-typed | `result.append_<lbl>(itemN.result)` — matches `append_<lbl>(&mut self, span: Span)` (cst.rs:2438) |
| labeled, node result | label single-node-typed | `result.append_<lbl>(itemN.result)` — `Shared<T>` satisfies `impl Into<Shared<T>>` (cst.rs:403) |
| labeled, node result | label union-typed (multi-type) | `result.append_<lbl>(cst::<X>Child::<ClassName>(itemN.result))` — union appends take the child enum (gsm2tree_rs.py:1331) |
| labeled, span result | label union-typed | `result.append_<lbl>(cst::<X>Child::Span(itemN.result))` |
| unlabeled INCLUDE, span result | — | `result.push_child(None, cst::<X>Child::Span(itemN.result))` |
| unlabeled INCLUDE, node result | — | `result.push_child(None, cst::<X>Child::<ClassName>(itemN.result))` |
| trivia capture (separator), non-trivia rule | child enum has `Trivia` variant | `result.push_child(None, cst::<X>Child::Trivia(ws.result))` |
| trivia capture (separator), trivia rule | child enum has `Span` variant | `result.push_child(None, cst::<X>Child::Span(ws.result))` |

Child-enum variant names equal CST class names (`Rule`, `Trivia`) or `Span` — the same naming `gsm2tree_rs.py` emits, obtained from the same `class_name_for_rule_node`. If a grammar ever produced an append into a variant the CST model lacks, the generated file fails to compile — a loud, pre-runtime failure mode, acceptable by design.

(Note: unlabeled INCLUDE node items are rare — `fltk2gsm` assigns implicit labels to identifier terms, e.g. `append_item` in fltk_parser.py:318 — but the row costs nothing and keeps the table total over GSM.)

### 2.4 Generated regex compile test

Appended to the generated file (controlling design §3.1 enforcement of the `regex`-crate subset; user answer A1):

```rust
#[cfg(test)]
mod generated_regex_tests {
    #[test]
    fn all_regex_patterns_compile() {
        for pat in super::REGEX_PATTERNS.iter() {
            if let Err(e) = fltk_parser_core::regex::Regex::new(pat) {
                panic!("grammar regex {pat:?} is not supported by the regex crate: {e}");
            }
        }
    }
}
```

Emitted only when the regex table exists (§2.2). It runs under each fixture's `cargo test` and under every downstream consumer's `cargo test`, naming the offending pattern.

### 2.5 CLI: `gen-rust-parser`

In `genparser.py`, parallel to `gen-rust-cst` (genparser.py:264-344):

```
genparser gen-rust-parser <grammar.fltkg> <output.rs> [--cst-mod-path super::cst]
```

- Parses via `_parse_grammar_raw` (no trivia processing — `RustParserGenerator` does it internally, same contract as `RustCstGenerator`).
- Catches `ValueError`, `RuntimeError`, `NotImplementedError` from construction/generation → `typer.echo(..., err=True)` + `Exit(1)` (gen-rust-cst pattern plus `NotImplementedError` for unsupported GSM terms).
- Generates the full text before opening the output file (no partial artifacts, genparser.py:186 precedent).
- `--cst-mod-path` is interpolated into the `use` statement; validated against `^[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_][A-Za-z0-9_]*)*$` (the pattern already admits `super`/`crate`/`self` segments). Same injection rationale as the identifier validation, gsm2tree_rs.py:57-60.

### 2.6 Fixture crates

**A) Extend `tests/rust_cst_fegen`** (fegen grammar; the Phase 3 parity vehicle):

- `Cargo.toml`: add `fltk-parser-core = { path = "../../crates/fltk-parser-core" }`; make pyo3 optional (`optional = true`) and rewire features: `python = ["dep:pyo3", "fltk-cst-core/python"]`, `extension-module = ["python", "pyo3/extension-module"]`, `default = ["extension-module"]` unchanged. Today pyo3 is unconditional (tests/rust_cst_fegen/Cargo.toml:20), which would put pyo3 in the python-off graph and make the eventual no-pyo3 assertion (Phase 4, controlling design §3.4) impossible; this is the minimal honest fix and matches "pure-Rust consumers build with default-features = false and link no pyo3" (controlling design §3.3).
- `src/lib.rs`: gate the pyo3 `use` and `#[pymodule]` with `#[cfg(feature = "python")]`; add `pub mod parser;` and `mod native_parser_tests;`.
- `src/parser.rs`: generated by `gen-rust-parser fltk/fegen/fegen.fltkg tests/rust_cst_fegen/src/parser.rs` (default cst-mod-path).
- `src/native_parser_tests.rs`: hand-written `#[cfg(test)]` tests (pattern: tests/rust_cst_fixture/src/native_tests.rs) — see §4.

**B) New `tests/rust_parser_fixture`** (feature-coverage grammar; the pure-Rust consumer template):

fegen.fltkg does not exercise left recursion, non-trivia `WS_REQUIRED`, explicit dispositions, union labels, or multibyte text — and the Python regression suite covers those via dynamically compiled grammars, which Rust cannot do. So Phase 2 adds one purpose-built grammar, `fltk/fegen/test_data/rust_parser_fixture.fltkg`, covering: direct + indirect left recursion (the generated-wiring complement to Phase 1's toy-parser memo tests), `WS_REQUIRED` (`:`) separators in a non-trivia rule, `?`/`+`/`*`, `%`-suppressed and `$`-included items, an unlabeled included literal, a union label (two node types under one label, like phase4_roundtrip.fltkg's `value_node`), nested sub-expression alternatives, and a multibyte literal + a regex matching multibyte text.

Crate layout mirrors the existing standalone-workspace fixtures (`[workspace]` header, excluded from root): `src/cst.rs` (gen-rust-cst) + `src/parser.rs` (gen-rust-parser) + `src/lib.rs` (`pub mod cst; pub mod parser; mod native_tests;`) + `src/native_tests.rs`. `crate-type = ["rlib"]`. Dependencies: `fltk-cst-core` (default-features = false), `fltk-parser-core`, and `pyo3` **optional** with `python = ["dep:pyo3", "fltk-cst-core/python"]` declared but never enabled — the feature must be declared because the generated `cst.rs` contains `#[cfg(feature = "python")]` blocks and undeclared features trip `unexpected_cfgs` under `-D warnings`. Default features: none. Default `cargo tree` shows no pyo3; this crate is the documented template for out-of-tree pure-Rust consumers.

(Why not extend `tests/rust_cst_fixture`/phase4_roundtrip.fltkg: that grammar is pinned to the Phase-4 CST roundtrip tests; growing it would churn committed CST artifacts and conflate fixtures' purposes.)

### 2.7 Build wiring (Phase 2's minimal, landable slice)

Phase 4 owns consolidated `make check` wiring and the no-pyo3 `cargo tree` stanzas (controlling design §6); Phase 2 adds only what landing green requires:

- Makefile `gen-rust-parser` target: `uv run python -m fltk.fegen.genparser gen-rust-parser $(GRAMMAR) $(RS_OUT)` (mirrors `gen-rust-cst`, Makefile:99-100).
- `gencode`: three additions — `parser.rs` for `tests/rust_cst_fegen`, and `cst.rs` + `parser.rs` for `tests/rust_parser_fixture`. Regen → `make fix` → commit flow unchanged (generated `.rs` is not touched by ruff; the generator's output must be committed as emitted).
- `cargo-test-no-python`: add `cargo test -q --manifest-path tests/rust_parser_fixture/Cargo.toml` and `cargo test -q --manifest-path tests/rust_cst_fegen/Cargo.toml --no-default-features`.
- `cargo-clippy-no-python`: clippy `-D warnings` for both of the above (same feature settings).
- `cargo-check`: add `cargo check -q --manifest-path tests/rust_cst_fegen/Cargo.toml` (default features) — the "compiles python-on" gate without linking an interpreter-specific artifact in CI. (`tests/rust_parser_fixture` has no python-on configuration to check.)

These lanes run inside existing `make check` steps, so Phase 2 lands with its artifacts gated. The generated `.rs` must be clippy-clean under both lanes (precedent: committed `cst.rs`); the generator may include narrowly-scoped `#[allow]`s only where a lint is structurally unavoidable, each with a comment.

### 2.8 Convenience surface (user answer A2)

No plumbing.py analogue. The generated `Parser::new(text, capture_trivia)` + `apply__parse_<rule>(0)` + `terminals().len()` + `error_message()` is the whole pure-Rust boilerplate story, and the fixture `native_tests.rs` demonstrates it. Anything more is out of scope per A2.

---

## 3. Edge cases / failure modes

- **Append/variant mismatch** (generator emits an append the CST enum lacks): impossible by construction while both generators consult the same `CstGenerator` model through the same composed instance; if the invariant ever breaks, the failure is a Rust compile error in generated code, not silent misbehavior.
- **Empty-match inner loop divergence**: a `*`/`+` item whose inner term matches empty at a fixed position loops forever — in Python too (fltk_parser.py:134 has no in-loop progress guard; only `+` checks net progress *after* the loop). Deliberately mirrored, not fixed: divergence here would be a cross-backend behavior change. Recorded in the generator docstring.
- **Method-name collisions from path mangling**: rule names like `x__alt0` can collide with generated `parse_x__alt0`. Python silently shadows (later `def` wins); Rust fails to compile (duplicate method). Fail-loudly divergence, acceptable; not worth a validation pass for a pathology the Python backend doesn't reject either.
- **Invocation-stack `.expect`**: unreachable while all `pub` parse entry points are `apply__*` (private rule bodies cannot be called from outside). Not input-reachable; consistent with the no-panic contract (controlling design §4) — the reachable panics remain memo.py:181's ported corner and regex-table init (pre-empted by the generated compile test).
- **Out-of-range / negative `pos` at `apply__parse_<rule>`**: never panics, never indexes out of bounds. Inner `consume_*`/`apply__*` calls fail via Phase 1 §2.3 bounds checks (memo keys are plain `i64`), so a rule that cannot match empty returns `None`. A nullable rule (alternative whose items are all `?`/`*`; no progress check is emitted when `min == ZERO`, gsm2parser.py:581-585) returns `Some` with an empty span at *any* `pos`, including `-1` and `len+1` — identical to Python; not rejected. Covered by fixture tests calling `apply__parse_<rule>(-1)` and `(len+1)` on a non-nullable rule (asserting `None`) and on a nullable rule (asserting the empty match, pinning Python-equivalent behavior).
- **Multibyte input**: positions are codepoint indices end-to-end; the generated code only moves `pos` via `ApplyResult.pos` and `span.end()`, both codepoint-valued. Fixture grammar includes multibyte literals/regex; spans are asserted against expected codepoint offsets.
- **`capture_trivia` and span equality**: trivia children change `children` but not node spans (Python identical). Fixture tests assert the only tree difference between flag settings is the unlabeled `Trivia`/`Span` children.
- **Cached-node sharing**: two parse paths reaching the same `(rule, pos)` share one `Shared` node (Arc clone on hit). Fixture test asserts `Shared::ptr_eq` across two `apply__parse_<rule>` calls at the same position on the same parser.
- **Stale generated artifacts**: `gencode` regenerates both fixtures; drift between committed `parser.rs` and generator output shows as a `git diff` after `make gencode` (existing cheat-detection convention, Makefile:102-107).
- **`--cst-mod-path` injection**: validated (§2.5); invalid paths are a CLI error, never emitted.

---

## 4. Test plan

After completion:

1. **Python generator unit tests** (`fltk/fegen/test_gsm2parser_rs.py`, TDD-first):
   - Validation: invalid rule name / label rejected (via composed `RustCstGenerator`); invalid `--cst-mod-path` rejected.
   - `NotImplementedError` for `gsm.Invocation` term and INLINE disposition.
   - Regex table: dedup, first-occurrence order, `\s+` included for trivia separators; `_rust_str_lit` escaping (backslashes, quotes, control chars, multibyte passthrough).
   - Structural assertions on generated text for a small in-test GSM: `pub fn apply__parse_<rule>` present per rule, private rule bodies, `RULE_NAMES` order, capture sites guarded by `if self.capture_trivia`, `WS_REQUIRED` else-return, `+` progress check, union-label append uses child enum, deterministic output (two runs byte-equal).
2. **CLI tests** (extend `fltk/fegen/test_genparser.py`): `gen-rust-parser` happy path writes the file; missing grammar file → exit 1; generation error → exit 1, no partial file.
3. **Generated-parser Rust tests**:
   - `tests/rust_parser_fixture/src/native_tests.rs`: left recursion (direct + indirect) parses with correct associativity/nesting and terminates; `+` zero-progress failure; `*` empty success; `?` both ways; `WS_REQUIRED` failure at the right position; SUPPRESS absent from children / INCLUDE span present unlabeled; union-label variants; sub-expression inlining (`extend_children` results); multibyte spans; `capture_trivia` on/off tree delta; memo sharing via `Shared::ptr_eq`; `error_position()`/`error_message()` on failure inputs; out-of-range and negative `pos` (non-nullable rule → `None`; nullable rule → empty match, per §3); the generated regex-compile test.
   - `tests/rust_cst_fegen/src/native_parser_tests.rs`: parse fegen-grammar snippets (a rule, alternatives with `|`, comments/trivia) asserting tree shape via CST accessors; parse the real `fegen.fltkg` (`include_str!` via `CARGO_MANIFEST_DIR`-relative path) to completion: `apply__parse_grammar(0)` succeeds with `pos == terminals().len()`, both `capture_trivia` settings.
4. **Build gates**: `make check` green with §2.7 lanes — both fixtures' `cargo test`/`clippy` python-off, `cargo check` python-on for `rust_cst_fegen`; `make gencode` produces no diff against committed artifacts.

TDD order: 1 and 2 first (red against module skeleton); then generator implementation; then fixture generation + 3 (the Rust tests are written against the expected generated API before first successful generation, then iterated).

---

## 5. Open questions

None. The judgment calls — composing `RustCstGenerator` rather than refactoring shared helpers out of it (§2.1), regex-by-index `consume_regex` (§2.2), one new feature-coverage fixture crate rather than extending phase4_roundtrip (§2.6), making pyo3 optional in `rust_cst_fegen` (§2.6), and pulling minimal build wiring into Phase 2 ahead of Phase 4's consolidation (§2.7) — are decided above with rationale. None changes public Python API or any committed generated Python artifact.
