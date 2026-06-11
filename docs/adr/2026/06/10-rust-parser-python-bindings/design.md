# Design: Phase 3 — Python Bindings + Parity

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Controlling design: `docs/adr/2026/06/10-rust-parser-codegen/design.md` (§3.3 sketches the binding surface; §5 item 3 the parity suite; §6 defines Phase 3). Requirements: `docs/adr/2026/06/10-rust-parser-codegen/request.md`. Implemented predecessors: Phase 1 (`docs/adr/2026/06/10-rust-parser-runtime-crate/design.md`, `crates/fltk-parser-core`), Phase 2 (`docs/adr/2026/06/10-rust-parser-generator/design.md`, `fltk/fegen/gsm2parser_rs.py`, fixture crates). Facts: `exploration.md` in this directory. This doc is the detailed implementation plan for Phase 3 only — the generated `PyParser`/`PyApplyResult` surface and the cross-backend parity suite. No `make check` consolidation or self-hosting test (Phase 4).

---

## 1. Context

Phase 2's generated parsers are pure-Rust: `tests/rust_cst_fegen/src/parser.rs` and `tests/rust_parser_fixture/src/parser.rs` contain zero `#[cfg(feature = "python")]` blocks (exploration.md §7 Q3). The generated CST already has the full python-gated handle layer (`PyGrammar::to_py_canonical`, registry identity, `register_classes` — exploration.md §2). Phase 3 delivers:

1. **Generated Python bindings** for the parser, in the same `.rs` file, gated like the CST: a `Parser` pyclass wrapping the native parser, an `ApplyResult` pyclass, and `register_classes` wiring. Pure-Rust consumers pay nothing — the block compiles only under the `python` feature (request.md: "the python bindings should only be linked in with a python consumer").
2. **Cross-backend parity tests** (pytest): a corpus parsed by the Python-generated parser and the Rust parser via bindings, asserting structural CST equality (kind/label/span), final-position equality, and error-position/message equivalence — both `capture_trivia` settings. Parity is the contract that makes generator drift a test failure (controlling design §2.7).

The Phase 2 native `Parser` API the bindings wrap is already complete: `new(text, capture_trivia)`, `apply__parse_<rule>(pos) -> Option<ApplyResult<Shared<T>>>`, `terminals()`, `rule_names()`, `error_message()`, `error_position()` (parser.rs:31-91; exploration.md §4). The pyclass delegates; no native-surface change is needed.

---

## 2. Proposed approach

### 2.1 Generator change: emit a python-gated bindings module (`gsm2parser_rs.py`)

One new emission method, `_gen_python_bindings() -> str`, appended by `generate()` as the final section (after the regex compile test). Emitted unconditionally for every grammar (the `#[cfg]` gate does the conditioning — same policy as cst.rs). All interpolated names are validated identifiers/class names already (RustCstGenerator validation, gsm2tree_rs.py:60-80); no new escaping paths.

Shape (one gated inner module, not per-item gates):

```rust
#[cfg(feature = "python")]
mod python_bindings {
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    use super::cst;
    use super::Parser;

    #[pyclass(frozen, name = "ApplyResult")]
    pub struct PyApplyResult {
        pos: i64,
        result: PyObject,
    }

    #[pymethods]
    impl PyApplyResult {
        #[getter]
        fn pos(&self) -> i64 { self.pos }
        #[getter]
        fn result(&self, py: Python<'_>) -> PyObject { self.result.clone_ref(py) }
    }

    #[pyclass(name = "Parser")]
    pub struct PyParser {
        inner: Parser,
    }

    impl PyParser {
        fn check_pos(&self, pos: i64) -> PyResult<()> {
            let len = self.inner.terminals().len();
            if pos < 0 || pos > len {
                return Err(PyValueError::new_err(format!(
                    "pos {pos} out of range for input of length {len}"
                )));
            }
            Ok(())
        }
    }

    #[pymethods]
    impl PyParser {
        #[new]
        #[pyo3(signature = (text, capture_trivia = false))]
        fn new(text: &str, capture_trivia: bool) -> Self {
            PyParser { inner: Parser::new(text, capture_trivia) }
        }

        #[getter]
        fn capture_trivia(&self) -> bool { self.inner.capture_trivia() }

        #[getter]
        fn rule_names(&self) -> Vec<&'static str> { self.inner.rule_names().to_vec() }

        fn error_message(&self) -> String { self.inner.error_message() }

        fn error_position(&self) -> Option<i64> { self.inner.error_position() }

        // ── one per memoized rule, grammar order ──
        pub fn apply__parse_grammar(&mut self, py: Python<'_>, pos: i64) -> PyResult<Option<PyApplyResult>> {
            self.check_pos(pos)?;
            match self.inner.apply__parse_grammar(pos) {
                Some(r) => {
                    let handle = cst::PyGrammar::to_py_canonical(py, &r.result)?;
                    Ok(Some(PyApplyResult { pos: r.pos, result: handle.into_any() }))
                }
                None => Ok(None),
            }
        }
        /* ... apply__parse_<rule> for every rule, including the trivia rule
               (apply__parse__trivia), each canonicalizing via cst::Py<ClassName> ... */
    }

    pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
        module.add_class::<PyApplyResult>()?;
        module.add_class::<PyParser>()?;
        Ok(())
    }
}
#[cfg(feature = "python")]
pub use python_bindings::register_classes;
```

Decisions, with rationale:

- **One inner `mod python_bindings`** instead of cst.rs's per-item `#[cfg]` gates: the parser's gated surface is one self-contained cluster (two pyclasses + registration), unlike the CST where gated and ungated code interleave per node type. A single gate keeps the generator change small and makes python-off compilation trivially clean (no per-item `unused_imports`/`dead_code` accounting). `use super::cst;` inside the inner module resolves to the parser module's own `cst` import binding (parent-module private items are visible to child modules), so the `--cst-mod-path` knob needs no second interpolation site.
- **`PyParser` is not frozen** (controlling design §3.3): pymethods take `&mut self`; pyo3's runtime borrow flag handles aliasing. No registry/`Shared` machinery — parsers never cross the boundary and have no identity-stability requirement. `Parser` is `Send` (all fields are `HashMap`/`Vec`/`Arc`-based), which non-frozen pyclasses require; if a future field ever broke `Send`, the failure is a compile error in generated code — loud, pre-runtime.
- **`PyApplyResult` is frozen**: an immutable value object (`pos` + canonical handle). Divergence from the Python backend's mutable `memo.ApplyResult` dataclass is permitted — parser-side classes are explicitly free (request.md). It is always truthy (no `__bool__`/`__len__`), so the downstream idiom `if not result or result.pos != len(text)` (plumbing.py:137) ports unchanged.
- **Eager canonicalization**: `.result` is converted to the canonical CST handle inside the pymethod via the existing `to_py_canonical` (cst.rs:432). Memoized nodes are `Shared`; a second `apply__parse_<rule>` at the same position Arc-clones the same allocation and the registry returns the *same Python object* — identity stability across calls comes for free and is pinned by a test (§4.3).
- **`pos` validation** (controlling design §4): `pos < 0 || pos > len` → `ValueError` at the Python boundary, instead of the native path's silent `None`/empty-match. `pos == len` remains valid (nullable rules match empty at EOF, both backends). A Python `int` outside `i64` raises `OverflowError` from pyo3 extraction before `check_pos` — acceptable; the corpus never goes there and the Python backend has no contract for such positions either.
- **Method/attribute names match the Python parser** where they exist there: `apply__parse_<rule>(pos)`, `rule_names` as an attribute (getter, matching `parser.rule_names[rule_id]` indexing in plumbing.py:141). `error_message()`/`error_position()` replace the `error_tracker` attribute — the one deliberate divergence, decided in the controlling design §3.3.
- **GIL stays held during parse.** `py.allow_threads` around the native call would require restructuring the `&mut self` borrow for no Phase 3 benefit (parity, not throughput, is the goal). No TODO: no concrete trigger.
- **Generator structure**: per-rule emission iterates `self._grammar.rules` and reads `self._parsers[(rule.name,)]` for `apply_name` and `self._class_name(rule.name)` for the handle type — the same metadata Phase 2's struct emission uses, so binding and native signatures agree by construction.

### 2.2 Extension wiring: two importable modules

**A) `tests/rust_cst_fegen` (`fegen_rust_cst`)** — already a maturin extension with python-on defaults. One line in `src/lib.rs` after `cst::register_classes(m)?`:

```rust
parser::register_classes(m)?;
```

`make build-fegen-rust-cst` then produces a `fegen_rust_cst` module exposing `Parser` and `ApplyResult` alongside the CST classes (no name collisions — exploration.md §7 Q1). This is the parity vehicle for the fegen grammar.

**B) `tests/rust_parser_fixture` (`rust_parser_fixture`) becomes buildable as an extension — non-default.** The fegen grammar exercises neither left recursion, nor `WS_REQUIRED` in non-trivia rules, nor union labels, nor explicit dispositions, nor multibyte terminals. The fixture grammar (`fltk/fegen/test_data/rust_parser_fixture.fltkg`) was purpose-built for exactly those (Phase 2 design §2.6) — but cross-backend parity for them is only testable if the fixture's Rust parser is importable from Python. Without it, those constructs would have Rust-native tests (Phase 2) and Python-backend tests (regression suite) but no test that the two backends produce *equal trees* — unacceptable when parity is first-class. Changes:

- `Cargo.toml`: `crate-type = ["rlib", "cdylib"]`; add `extension-module = ["python", "pyo3/extension-module"]` to `[features]`. **Default features stay empty** — the crate's documented role as the pure-Rust consumer template is unchanged: `cargo test`/`cargo tree` with default features still build and link zero pyo3 (the existing `cargo-test-no-python`/`cargo-clippy-no-python` lanes keep gating this; the `cargo tree` no-pyo3 stanza for fixtures remains Phase 4's, per controlling design §6).
- `src/lib.rs`: gated `#[pymodule] fn rust_parser_fixture(...)` registering `Span`, `SourceText`, `cst::register_classes`, `parser::register_classes` (mirror of rust_cst_fegen/src/lib.rs; the pymodule fn name must equal the lib target name, which Cargo derives as `rust_parser_fixture`).
- Makefile target `build-rust-parser-fixture`: `cd tests/rust_parser_fixture && uv run --group dev maturin develop --features extension-module` (explicit features because defaults are empty; maturin builds from Cargo.toml metadata, same as the fegen crate which has no pyproject.toml).

Both extensions statically link their own `fltk-cst-core`, so each has its own registry — irrelevant here: parity tests never mix nodes across modules, and span comparison is by value.

### 2.3 Regenerated artifacts

`make gencode` regenerates both fixtures' `parser.rs` (targets already exist, Makefile:113-114, 166); Phase 3's generator change adds the gated block to both committed files. Regen → `make fix` → commit, the standard flow. Drift between generator and committed artifacts shows as a diff after `make gencode` (cheat-detection convention).

### 2.4 Parity test infrastructure

New helper module `tests/parser_parity.py` (not `test_`-prefixed; imported by the test modules):

**`assert_cst_equal(py_node, rust_node)`** — recursive structural comparator (controlling design §5 item 3; node-level cross-backend `__eq__` is not assumed):

- `py_node.kind == rust_node.kind` — holds cross-backend via `_fltk_canonical_name` equality, for the committed `fltk_cst` and for plumbing-generated dynamic CST modules alike (gsm2tree emits the same canonical-name machinery it committed into fltk_cst.py; canonical names depend only on class/label names, identical for the same grammar).
- Span equality: `.span.start`/`.span.end` as plain ints on both sides (Python `terminalsrc.Span` attributes; Rust handle `span` getter). Same for `Span`-typed children.
- Children: both sides expose `children` as a list of `(label|None, child)` tuples (Python dataclass field; Rust getter, cst.rs `children`). Compare length, then pairwise: label `None`-ness and cross-backend label equality (`py_label == rust_label`, the contract pinned by `test_cross_backend_label_equality.py`), then child species (span vs node — discriminate by `hasattr(child, "children")`, true only for nodes on both backends: dataclass field fltk_cst.py:82, Rust getter cst.rs:492; spans expose no `children` on either backend. **Not** `hasattr(child, "kind")`: spans deliberately expose `kind` on both backends — `terminalsrc.Span.kind` defaults to `SpanKind.SPAN` (terminalsrc.py:55) and the Rust `Span` pyclass has a `kind` getter returning the same object (span.rs ~564)), then recurse / compare span endpoints.
- Failures report the tree path for diagnosis.

**`assert_error_equiv(py_parser, rust_parser, terminals)`** — error parity per the Phase 1 §2.4 ordering analysis:

- Position: `rust_parser.error_position()` is `None` ⇔ `py_parser.error_tracker.longest_parse_len == -1`, else equal ints.
- Message: Python side rendered via `errors.format_error_message(py_parser.error_tracker, terminals, lambda rid: py_parser.rule_names[rid])`; Rust side `rust_parser.error_message()`. Compared structurally, not byte-wise: header block (the `Syntax error at line...` / line text / caret / `Expected:` lines) byte-equal; `From rule "..."` group headers byte-equal in order (both backends use first-occurrence rule order); within-group token lines compared as *sets* (Python iterates a `set` — hash-seed-nondeterministic; Rust dedupes in first-occurrence order). Byte-identical comparison is valid only for single-token groups; the helper encodes this so no test hand-rolls it.

**Per-grammar drivers.** Python side: for the fegen grammar, the committed `fltk_parser.Parser` / `fltk_trivia_parser.Parser` (the two trivia variants, exploration.md §3.5); for the fixture grammar, `plumbing.generate_parser(grammar, capture_trivia=...)` with `grammar = parse_grammar_file(rust_parser_fixture.fltkg)`, instantiated directly (`pr.parser_class(terminalsrc=...)`) so the test owns the parser and can reach `error_tracker` — `plumbing.parse_text` hides it. Rust side: `module.Parser(text, capture_trivia=flag)` + `getattr(parser, f"apply__parse_{rule}")(pos)`. These few-line drivers are the in-scope boilerplate reduction per user answer A2; nothing ships in `fltk/`.

**Corpus entries** are declarative: `(rule, input, expect: SUCCESS | PARTIAL(pos) | FAIL)`. SUCCESS asserts both backends succeed with `result.pos == len(input)` and equal trees; PARTIAL asserts both succeed at the same `pos < len` with equal trees; FAIL asserts both return falsy/None at top level and `assert_error_equiv`. An entry where the backends *disagree on outcome* always fails — the expectation flag prevents a both-backends-broken corpus from passing vacuously.

### 2.5 Parity corpus and test modules

Two pytest modules under `tests/`, each with module-level `pytest.importorskip` for its extension (the `test_phase4_fegen_rust_backend.py` pattern, including the docstring note that an all-skipped CI lane is a failure signal):

**`tests/test_rust_parser_parity_fegen.py`** (`fegen_rust_cst`), parametrized over `capture_trivia ∈ {False, True}` against the matching committed Python module:

- `fegen.fltkg` full text (the self-hosting input).
- Grammar snippets: single rule, multi-alternative rules, quantifiers/dispositions in grammar syntax, line/block comments (trivia-rich), raw strings, regexes.
- Multibyte: non-ASCII inside grammar string literals and comments; multibyte content preceding a syntax error (line/col + caret line parity over multibyte text).
- Failure inputs adapted from `test_regression_error_reporting.py` / `test_regression_line_col_error.py` scenarios (unterminated rule, bad token mid-line, multi-line input failing on a later line, empty input).
- Trailing-character behavior (controlling design §4; `test_trailing_character_bug.py`): at least one SUCCESS entry whose input ends in a non-whitespace terminal with no trailing whitespace/newline — `result.pos == len(input)` on both backends pins the end-of-input final-position class of bug.
- One non-start-rule entry (`apply__parse_rule`, `apply__parse_identifier`) to exercise per-rule binding wiring against the Python parser's same method.

**`tests/test_rust_parser_parity_fixture.py`** (`rust_parser_fixture`), same `capture_trivia` matrix against plumbing-generated Python parsers. Corpus maps each Python regression scenario onto the fixture grammar:

| Regression source | Corpus entries |
|---|---|
| `test_regression_toplevel_recursion.py` | direct + indirect left-recursive inputs, nested several levels; tree shape asserts associativity equality |
| `test_regression_recursive_inlining.py` | recursion through an inlining sub-expression |
| `test_regression_empty_nary.py` | `*` matching empty (SUCCESS), `+` matching empty (FAIL/PARTIAL), at start and mid-rule |
| `test_regression_ws_required.py` | `:` separator absent → FAIL at the separator position |
| `test_regression_subexpr_separators.py` | separators inside sub-expression alternatives |
| `test_leading_separators.py` | `initial_sep` (leading separator) present/absent |
| `test_trivia_capture.py` / `test_trivia_whitespace_capture.py` | whitespace-bearing inputs; the `capture_trivia=True` runs assert trivia children parity, `False` runs assert their absence on both sides |
| `test_trailing_character_bug.py` (controlling design §4) | the trailing-character pair mapped onto the fixture grammar: the same input with and without a trailing whitespace character (`"x+"`-style — historically parsed one position short without trailing whitespace), each with its explicit SUCCESS/PARTIAL expectation; plus a SUCCESS entry ending in a non-whitespace terminal |
| (fixture-specific) | suppressed (`%`) and included (`$`) items, unlabeled included literal, union-label inputs hitting each variant, multibyte literal + multibyte regex matches, multibyte error line/col |

The audit against this table is done: the committed `rust_parser_fixture.fltkg` covers quantifiers, dispositions, union labels, `WS_REQUIRED`, direct + indirect left recursion, and multibyte — but contains **no leading `initial_sep` and no sub-expression term at all** (its `paren_expr` uses literal parens, not a grammar sub-expression), so subexpr-separators and recursion-through-inline are uncovered. Phase 3 extends the grammar with: an alternative with a leading separator, a sub-expression term with internal separators, and a rule recursing through an inlining sub-expression; then regenerates both fixture artifacts (`cst.rs` + `parser.rs`) and extends the Phase 2 native tests alongside. Extending this grammar is its designed purpose (Phase 2 design §2.6).

### 2.6 Binding-surface tests

`tests/test_rust_parser_bindings.py` (`fegen_rust_cst`; surface behavior with no Python-backend counterpart):

- Constructor: positional + keyword forms, `capture_trivia` default `False`, `capture_trivia` getter; non-`str` text → `TypeError`.
- `pos` validation: `-1` and `len+1` → `ValueError` (both nullable and non-nullable rules — the boundary check fires before any parse); `pos == len` → no error (nullable rule matches empty, non-nullable returns `None`).
- `ApplyResult`: `.pos` int, `.result` is an instance of the module's CST class (`fegen_rust_cst.Grammar`); truthiness; `.result` accessed twice returns the identical object.
- Canonical identity: two `apply__parse_<rule>` calls at the same position on the same parser return the same `.result` object (memo Arc + registry).
- `rule_names`: equals `fltk_parser.Parser(terminalsrc=...).rule_names` element-wise (the load-bearing order identity for error parity); supports indexing.
- `error_position()` is `None` and `error_message()` renders the no-failure form on a fresh parser; both populated after a failed parse.

### 2.7 Build wiring (Phase 3's minimal slice; consolidation is Phase 4)

- Makefile: `build-rust-parser-fixture` (§2.2B); add it to `.PHONY`.
- `cargo-check` lane: add `cargo check -q --manifest-path tests/rust_parser_fixture/Cargo.toml --features python` — the python-on compile gate for the second grammar's generated bindings (rust_cst_fegen is already checked python-on via its default features).
- `cargo-clippy` lane: add `cargo clippy -q --manifest-path tests/rust_cst_fegen/Cargo.toml -- -D warnings` and `cargo clippy -q --manifest-path tests/rust_parser_fixture/Cargo.toml --features python -- -D warnings`. The bindings block is new generated code that no existing lane lints python-on; committed generated code must be clippy-clean (Phase 2 §2.7 precedent). Narrowly-scoped `#[allow]`s only where structurally unavoidable, each with a comment.
- Parity/binding pytest modules run under the existing `make test`; they self-skip when extensions are unbuilt (importorskip), same as the Phase 4 tests. CI must run `build-fegen-rust-cst` and `build-rust-parser-fixture` before pytest for the lanes to be meaningful.

---

## 3. Edge cases / failure modes

- **Reentrancy under `&mut self`**: canonicalization runs Python code (registry, `Py::new`) while the parser is mutably borrowed; a pathological callback (GC/weakref) re-entering a parser method gets pyo3's `RuntimeError: already borrowed`, not UB. Accepted; parsing itself never calls into Python.
- **Mutation of returned CST then re-parse**: memo caches hold `Shared` nodes; mutating a returned tree mutates cached structure, and a later `apply__` at the same position returns the mutated node. Identical to the Python backend's cached-object sharing (controlling design §4) — not a divergence; the parity comparator never reuses a parser across mutations.
- **`ValueError` vs Python-backend silence at out-of-range `pos`**: deliberate, decided divergence (controlling design §4). The corpus only uses in-range positions, so parity tests are unaffected; the binding tests pin the `ValueError` itself.
- **Error-message nondeterminism**: Python's within-rule line order is hash-seed-dependent; byte-comparing whole messages would flake. The structural `assert_error_equiv` (§2.4) is the only comparison path tests may use.
- **Vacuous comparator**: a comparator bug that never recurses or never fails would green the whole corpus. §4.4 requires negative self-tests (deliberately unequal trees and messages must fail).
- **Fixture extension erodes the pure-Rust template**: guarded by keeping default features empty; the existing no-python test/clippy lanes build the crate default-featured every `make check`. The `cargo tree` assertion stays Phase 4.
- **Skip-pattern false green**: if an extension is not built, its parity module skips silently. Mirrored from the established Phase 4 convention, including the documented "all-skipped lane is a failure signal"; Phase 4 owns CI consolidation.
- **`rule_names` returns a fresh list per access** (Python backend exposes one stable list attribute). Read-only consumers (indexing by rule id) are unaffected; identity of the list object is not part of any contract.
- **Two cdylibs, two registries**: handles from `fegen_rust_cst` and `rust_parser_fixture` are unrelated types. Parity tests never mix them; spans compare by value (`.start`/`.end` ints).
- **Codepoint positions**: `result.pos` and `error_position()` are codepoint indices; Python `len(text)` and `longest_parse_len` agree by construction. Multibyte corpus entries pin this end-to-end including the caret/line rendering.

---

## 4. Test plan

After completion:

1. **Generator unit tests** (`fltk/fegen/test_gsm2parser_rs.py` extensions, TDD-first): generated text contains the `#[cfg(feature = "python")] mod python_bindings` block with `PyParser`/`PyApplyResult`; one `apply__parse_<rule>` pymethod per rule (including the trivia rule) canonicalizing via the correct `cst::Py<ClassName>`; `check_pos` validation present; `register_classes` registers exactly the two classes; gated `pub use` re-export present; output remains deterministic (two runs byte-equal); block emitted even for a zero-regex grammar.
2. **Compile gates**: both fixture crates compile and are clippy-clean python-on and python-off (§2.7 lanes); `make gencode` produces no diff against committed artifacts.
3. **Binding-surface tests**: §2.6 list.
4. **Comparator self-tests** (in `tests/test_rust_parser_parity_fegen.py` — they construct Rust-side nodes via the `fegen_rust_cst` CST constructors, so they share that module's importorskip): `assert_cst_equal` fails on kind, span, label, child-count, deep-child, and species mismatches (a span child paired with a node child, in both directions — pins the `hasattr(child, "children")` discrimination of §2.4); `assert_error_equiv` fails on differing positions, headers, group order, and token sets — constructed from hand-built unequal inputs.
5. **Parity corpus**: §2.5 — fegen module (committed Python parsers, both trivia variants) and fixture module (plumbing-generated Python parsers, both `capture_trivia` values), every entry with an explicit expected outcome; SUCCESS/PARTIAL entries assert tree equality + position, FAIL entries assert error equivalence.

TDD order: 1 (red against the generator), then the generator change + regen; 4 (comparator self-tests red against helper skeleton), then helpers; 3 and 5 against the built extensions.

---

## 5. Open questions

None. The judgment calls — single gated inner module rather than cst.rs-style per-item gates (§2.1), frozen `PyApplyResult` (§2.1), making `rust_parser_fixture` an opt-in extension to get full-feature parity coverage (§2.2B), structural rather than byte-wise error-message comparison (§2.4), and extending the fixture grammar to close its audited coverage gaps (§2.5) — are decided above with rationale. The binding-surface decisions themselves (constructor shape, `error_tracker` replacement, `pos` `ValueError`) were already made in the controlling design §3.3-§4 and are implemented, not revisited, here.
