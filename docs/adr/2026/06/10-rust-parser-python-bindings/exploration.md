# Exploration: Phase 3 — Python Bindings + Parity

Style note: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

---

## 1. What Phase 3 specifies (from controlling design)

From `docs/adr/2026/06/10-rust-parser-codegen/design.md` §3.3, §5 item 3, §6:

Phase 3 delivers:
- Generated `PyParser` / `PyApplyResult` surface in the same `.rs` file as the pure-Rust parser, behind `#[cfg(feature = "python")]`, identical to the CST's `python` feature gate pattern.
- A cross-backend parity test suite (Python/pytest) running a corpus through the Python-generated parser and the Rust parser (via bindings), asserting structural CST equality and error-position equivalence.
- Both `capture_trivia` settings tested against the corresponding Python parser variant.

Key design choices already decided:
- `PyParser` is **not** frozen: `pymethods` take `&mut self`; pyo3 runtime borrow checking handles aliasing (no `Shared`/registry — parsers never cross boundaries or need identity stability).
- Constructor: `Parser(text: str, capture_trivia: bool = False)` — simpler than Python's `Parser(terminalsrc=TerminalSource(text))`.
- Per memoized rule: `apply__parse_<rule>(pos: int) -> PyApplyResult | None`. Names match Python so `plumbing.py` call sites (`parser.apply__parse_grammar(0)`, plumbing.py:135,162) port with minimal churn.
- `PyApplyResult` is a tiny `#[pyclass]` with `.pos: int` and `.result: PyObject`; `.result` is the canonical CST handle via `Py<Node>::to_py_canonical` (registry identity rules unchanged from CST phase).
- `rule_names() -> list[str]` getter, `error_message() -> str`, `error_position() -> int | None`.
- `error_tracker` attribute is **not** replicated; `error_position()` returns the scalar farthest-failure codepoint (or `None`).
- Python boundary validates `pos >= 0` and `pos <= len` → `ValueError` instead of silent `None` (controlling design §4).
- `register_classes` function `#[cfg(feature = "python")]` exposes `PyParser` and `PyApplyResult` to the pymodule (matching `cst.rs` pattern).
- Pure-Rust consumers (no python feature) pay nothing: feature wiring is the fixture pattern in `tests/rust_cst_fegen/Cargo.toml`.

Parity test comparator (controlling design §5 item 3):
- Walk both trees recursively asserting kind/label/span-start/span-end equality.
- Node-level cross-backend `__eq__` is not assumed.
- Error cases: both fail at same farthest position (`error_position()` on Rust side; Python: `parser.error_tracker.longest_parse_len`).
- Error message equality is up to within-rule line order (runtime-phase-1-design §2.4): within-rule "Expected" lines treated as unordered set; byte-identical comparison valid only for single-token rule groups.

---

## 2. CST Python binding pattern already in place

The CST `python` feature gate is the model. Concretely:

### 2.1 Feature wiring (`tests/rust_cst_fegen/Cargo.toml:1-22`)

```toml
[features]
default = ["extension-module"]
extension-module = ["python", "pyo3/extension-module"]
python = ["dep:pyo3", "fltk-cst-core/python"]

[dependencies]
pyo3 = { version = "0.23", features = ["abi3-py310"], optional = true }
fltk-cst-core = { path = "../../crates/fltk-cst-core", default-features = false }
fltk-parser-core = { path = "../../crates/fltk-parser-core" }
```

Pure-Rust consumers: `default-features = false` → no pyo3 linked. `tests/rust_parser_fixture/Cargo.toml` declares the `python` feature (required for `#[cfg(feature = "python")]` in generated `cst.rs` to compile under `-D warnings`/`unexpected_cfgs`) but never enables it by default (`crate-type = ["rlib"]`, no default features).

### 2.2 Generated CST binding structure (`tests/rust_cst_fegen/src/cst.rs`)

Per node type, the generator emits:

- Dual `NodeKind` enums: `#[cfg(feature = "python")] #[pyclass(frozen, name = "NodeKind")]` (cst.rs:27) and `#[cfg(not(feature = "python"))]` bare derive (cst.rs:60-77).
- Dual label enums per class: `#[cfg(feature = "python")] #[pyclass(frozen, name = "Grammar_Label")]` (cst.rs:134) + `#[cfg(not(feature = "python"))]` (cst.rs:141).
- `PyGrammar` handle struct: `#[cfg(feature = "python")] #[pyclass(frozen, weakref, name = "Grammar")]` (cst.rs:413-420) — `frozen` because all mutation goes through `inner: Shared<Grammar>` with its `RwLock`.
- `PyGrammar::to_py_canonical(py, &Shared<Grammar>) -> PyResult<Py<PyGrammar>>` (cst.rs:432-439): registry lookup/insert, ensuring identity-stability across calls.
- `#[pymethods] impl PyGrammar` (cst.rs:443): `#[new]`, `span` getter/setter, `kind`, `Label` classattr, `children`, `push_child`, `set_span`, `append_<lbl>`, `extend_<lbl>`, `child_<lbl>`, `children_<lbl>`, `maybe_<lbl>`, `__eq__`, `__hash__`, `__repr__`.
- `pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()>` (cst.rs:11055-11084): `#[cfg(feature = "python")]`, called by `#[pymodule]` fn in `lib.rs`.

### 2.3 Module wiring (`tests/rust_cst_fegen/src/lib.rs:1-22`)

```rust
#[cfg(feature = "python")]
#[pymodule]
fn fegen_rust_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    cst::register_classes(m)?;
    Ok(())
}
```

Phase 3 adds `parser::register_classes(m)?` here (or equivalent call) to expose `PyParser` and `PyApplyResult`.

---

## 3. Python backend parse API (the parity target)

### 3.1 Parser constructor and fields (`fltk/fegen/fltk_parser.py:11-77`)

```python
class Parser:
    def __init__(self, terminalsrc: fltk.fegen.pyrt.terminalsrc.TerminalSource) -> None:
        self.terminalsrc = terminalsrc
        self._source_text = fltk.fegen.pyrt.span.SourceText(text=terminalsrc.terminals)
        self.packrat: Packrat[int, int] = Packrat()
        self.error_tracker: ErrorTracker[int] = ErrorTracker()
        self.rule_names: Sequence[str] = ["grammar", "rule", ...]
        self._cache__parse_grammar: MutableMapping[int, MemoEntry[int,int,Grammar]] = {}
        # ... one cache field per rule ...
```

Constructor takes `terminalsrc: TerminalSource`, not raw text. The Rust `PyParser` takes `text: str` directly (controlling design §3.3).

Python's `TerminalSource` (`fltk/fegen/pyrt/terminalsrc.py:162-165`):
```python
class TerminalSource:
    def __init__(self, terminals: str):
        self.terminals: Final = terminals
        self.terminals_len: Final = len(terminals)
```

### 3.2 Call pattern in `plumbing.py` (the parity test's reference)

`fltk/plumbing.py:130-148` (Python parser path):
```python
parser = fltk_parser.Parser(terminalsrc=terminals)
result = parser.apply__parse_grammar(0)
if not result or result.pos != len(terminals.terminals):
    error_msg = errors.format_error_message(
        parser.error_tracker, terminals,
        lambda rule_id: parser.rule_names[rule_id],
    )
    raise ValueError(...)
```

`apply__parse_grammar` returns `ApplyResult(pos=int, result=Grammar) | None`. `result.pos` compared to `len(terminals.terminals)` (codepoint count for Python's `str` is just `len()`).

For Rust parser via parity test: `parser.apply__parse_grammar(0)` returns `PyApplyResult | None`. `result.pos` compared to `parser.terminals().len()` (Rust) or equivalently `len(text)` in Python (for ASCII; for Unicode codepoints both agree since Python `len()` is also codepoints).

### 3.3 Python-backend `apply__parse_<rule>` signature (fltk_parser.py:103-108)

```python
def apply__parse_grammar(self, pos: int) -> ApplyResult[int, Grammar] | None:
    return self.packrat.apply(
        rule_callable=self.parse_grammar, rule_id=0,
        rule_cache=self._cache__parse_grammar, pos=pos
    )
```

`ApplyResult` is `memo.ApplyResult` from `fltk/fegen/pyrt/memo.py` — a dataclass with `.pos: int` and `.result: T`.

### 3.4 Python-side error API (plumbing.py:138-140, 165-167, 315-318)

`errors.format_error_message(parser.error_tracker, terminals, lambda rule_id: parser.rule_names[rule_id])` → `str`.

`parser.error_tracker` is a public attribute (`fltk_parser.py:18`), type `ErrorTracker[int]`, with `.longest_parse_len: int` (initialized to -1, `errors.py:26`).

The Rust-side `error_position()` returns `Option<i64>` (`None` when `longest_parse_len == -1`, i.e. no failure recorded). Python equivalent is `parser.error_tracker.longest_parse_len` raw.

### 3.5 Two Python parser variants (genparser.py:85 path; controlling design §3.2)

Python generates two parser modules: one `capture_trivia=False` and one `=True` (different committed artifacts: `fltk_parser.py` and `fltk_trivia_parser.py`). The Rust generator emits one `Parser` with a runtime `capture_trivia: bool` flag. Parity tests run both flag values comparing against both Python modules.

---

## 4. Phase 2 generated parser: public API that Phase 3 wraps

### 4.1 `Parser` struct and constructors (`tests/rust_cst_fegen/src/parser.rs:31-91`)

```rust
pub struct Parser {
    terminals: TerminalSource,
    packrat: PackratState,
    error_tracker: ErrorTracker,
    capture_trivia: bool,
    cache__parse_grammar: Cache<Shared<cst::Grammar>>,
    // ... one cache field per rule ...
}

impl Parser {
    pub fn new(text: &str, capture_trivia: bool) -> Self { ... }
    pub fn from_source_text(source: SourceText, capture_trivia: bool) -> Self { ... }
    pub fn terminals(&self) -> &TerminalSource { &self.terminals }
    pub fn capture_trivia(&self) -> bool { self.capture_trivia }
    pub fn rule_names(&self) -> &'static [&'static str] { &RULE_NAMES }
    pub fn error_message(&self) -> String { ... }
    pub fn error_position(&self) -> Option<i64> { ... }
}
```

### 4.2 Per-rule entry points (parser.rs:113-115, example)

```rust
pub fn apply__parse_grammar(&mut self, pos: i64) -> Option<ApplyResult<Shared<cst::Grammar>>> {
    apply(self, 0u32, pos, |p| &mut p.packrat, |p| &mut p.cache__parse_grammar, Self::parse_grammar)
}
```

Return type: `Option<ApplyResult<Shared<cst::NodeT>>>`. `ApplyResult` from `fltk-parser-core`: `pub struct ApplyResult<T> { pub pos: i64, pub result: T }`.

### 4.3 `error_message` and `error_position` (parser.rs:85-91)

```rust
pub fn error_message(&self) -> String {
    fltk_parser_core::format_error_message(&self.error_tracker, &self.terminals, &RULE_NAMES)
}
pub fn error_position(&self) -> Option<i64> {
    (self.error_tracker.longest_parse_len >= 0).then_some(self.error_tracker.longest_parse_len)
}
```

These already exist in Phase 2 — Phase 3's `PyParser` delegates to them directly.

### 4.4 `RULE_NAMES` constant (parser.rs:19)

```rust
pub const RULE_NAMES: [&str; 14] = ["grammar", "rule", "alternatives", ...];
```

Same order as Python `fltk_parser.py:19-34`. This identity is load-bearing for error-message parity.

---

## 5. How the Python bindings should be gated (the CST model, applied to parser)

### 5.1 Generated parser `#[cfg(feature = "python")]` block

In the same generated `.rs` file, after the closing `}` of `impl Parser`, the generator emits a gated block:

```rust
#[cfg(feature = "python")]
mod python_bindings {
    use pyo3::prelude::*;
    use super::{Parser, RULE_NAMES};
    use fltk_cst_core::Shared;
    // ...

    #[pyclass(name = "ApplyResult")]
    pub struct PyApplyResult { pub pos: i64, pub result: PyObject }

    #[pymethods]
    impl PyApplyResult {
        #[getter] fn pos(&self) -> i64 { self.pos }
        #[getter] fn result(&self, py: Python<'_>) -> PyObject { self.result.clone_ref(py) }
    }

    #[pyclass(name = "Parser")]
    pub struct PyParser { pub inner: Parser }

    #[pymethods]
    impl PyParser {
        #[new]
        #[pyo3(signature = (text, capture_trivia = false))]
        fn new(text: &str, capture_trivia: bool) -> Self { ... }

        pub fn apply__parse_grammar(&mut self, py: Python<'_>, pos: i64) -> PyResult<Option<PyApplyResult>> { ... }
        // ... per rule ...

        pub fn rule_names(&self) -> Vec<&'static str> { self.inner.rule_names().to_vec() }
        pub fn error_message(&self) -> String { self.inner.error_message() }
        pub fn error_position(&self) -> Option<i64> { self.inner.error_position() }
    }

    pub fn register_classes(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_class::<PyApplyResult>()?;
        m.add_class::<PyParser>()?;
        Ok(())
    }
}
#[cfg(feature = "python")]
pub use python_bindings::register_classes;
```

(Exact structure is the implementer's decision; the above is the conceptual shape from controlling design §3.3.)

Key detail: `PyParser` is **not** `frozen` (unlike `PyGrammar` which is frozen). `pymethods` take `&mut self`. pyo3 handles aliasing at runtime. No registry involvement — parsers have no identity-stability requirement.

### 5.2 `.result` in `PyApplyResult`

`apply__parse_grammar` returns `Option<ApplyResult<Shared<cst::Grammar>>>`. The Python object for `.result` is obtained via `cst::PyGrammar::to_py_canonical(py, &result.result)` (cst.rs:432), which looks up the registry and returns a `Py<PyGrammar>`. This is the same canonical handle machinery the CST phase built; the parser binding reuses it without modification.

### 5.3 `lib.rs` wiring change

`tests/rust_cst_fegen/src/lib.rs:17` currently:
```rust
fn fegen_rust_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Span>()?;
    m.add_class::<SourceText>()?;
    cst::register_classes(m)?;
    Ok(())
}
```

Phase 3 adds `parser::register_classes(m)?;` after `cst::register_classes(m)?;`.

---

## 6. Parity / cross-backend test infrastructure already in place

### 6.1 Existing parity tests

`tests/test_phase4_fegen_rust_backend.py` is the structural model for Phase 3's parity suite:
- Skips if `fegen_rust_cst` not importable (`pytest.importorskip`, line 29).
- `parse_grammar(text)` (Python backend) vs `parse_grammar(text, rust_fegen_cst_module="fegen_rust_cst")` (Rust CST + Python IIR-generated parser).
- Asserts `python_result == rust_result` on the GSM output — **not** raw CST structural comparison.

Phase 3's parity test is at a different level: raw CST structural comparison (kind/label/span) between Python-generated parser's CST and Rust-parser's CST, before any semantic processing. The `test_phase4_fegen_rust_backend.py` tests are a higher-level integration target (self-hosting, Phase 4).

### 6.2 `test_cross_backend_label_equality.py`

`tests/test_cross_backend_label_equality.py`: exercises Label and NodeKind equality/hash across three backends (`py`, `emb`, `ext`). Parametrized over `_BACKEND_PAIRS`. The same Label cross-backend equality contract means Phase 3's parity comparator can compare labels from Python CST nodes against labels from Rust CST nodes directly (no canonicalization needed, since `py_label == rust_label` by design).

### 6.3 Regression test corpus (inputs for parity suite)

All in `fltk/fegen/`:
- `test_regression_toplevel_recursion.py` — left recursion on top-level rule, invocation-stack during growth
- `test_regression_recursive_inlining.py` — recursive rules that inline to parent
- `test_regression_empty_nary.py` — empty `*`/`+` quantifier cases
- `test_regression_error_reporting.py` — error tracker and message format
- `test_regression_line_col_error.py` — line/col in error output
- `test_regression_ws_required.py` — `WS_REQUIRED` (`:`) separator failure
- `test_regression_subexpr_separators.py` — separators inside sub-expressions
- `test_leading_separators.py` — leading separator handling
- `test_trivia_capture.py` — `capture_trivia=True` trivia node presence
- `test_trivia_whitespace_capture.py` — whitespace capture variant

These tests each build a GSM and parse with the Python backend. Their inputs and grammars feed the Phase 3 corpus; both Python and Rust parsers are run on each.

`fltk/fegen/fegen.fltkg` itself is also a corpus input (the self-hosting grammar, already used in `native_parser_tests.rs` line 17).

Multibyte cases: not present in existing test files — Phase 3 adds dedicated inputs covering non-ASCII literals, regexes, and error line/col over multibyte text (controlling design §4).

### 6.4 Structural CST comparator

No existing cross-backend CST tree comparator exists that walks raw CST nodes (Python vs Rust). `test_cross_backend_label_equality.py` checks Label/NodeKind equality only — not node trees. Phase 3 writes this comparator from scratch.

The comparison protocol:
- Python node `.kind` and Rust node `.kind`: cross-backend equal by label-equality design (§6.2 above).
- Python node `.span.start`, `.span.end` vs Rust node `.span.start()`, `.span.end()`: both `i64` codepoint indices; direct `==`.
- Python node `.children` is a list of `(label|None, child)` tuples (fltk_cst.py dataclass attribute). Rust node `.children` is also a Python list of `(label|None, child)` tuples (cst.rs:492-509 via `#[getter] fn children`). Same structure; direct iteration.
- Labels: `py_label == rust_label` by cross-backend equality design.
- Recursion on child nodes (both are either `Span` or node objects).

### 6.5 Build wiring for the Python-on test

`make build-fegen-rust-cst` (Makefile:99-100):
```
cd tests/rust_cst_fegen && uv run --group dev maturin develop
```
Builds the `fegen_rust_cst` cdylib with default features (= `extension-module` = python+pyo3). Phase 3's parity tests require this artifact (same as `test_phase4_fegen_rust_backend.py`). No new Makefile target is needed — Phase 3 imports `fegen_rust_cst` (with `PyParser` added to it) the same way.

Phase 3 parity tests are Python (`pytest`), run under `make test`. The `pytest.importorskip("fegen_rust_cst")` pattern skips automatically if the artifact is not built.

---

## 7. Open factual questions

1. **`PyApplyResult` name collision**: cst.rs already exposes `ApplyResult` as a pyo3 class name? No — the CST module has no `ApplyResult`; it is parser-only. No collision.

2. **`parser::register_classes` visibility**: The generated parser `.rs` does not currently define `register_classes`. The `lib.rs` currently only calls `cst::register_classes`. Phase 3 must add the parser call in `lib.rs` (gated `#[cfg(feature = "python")]`).

3. **Current `parser.rs` has no python-gated blocks**: confirmed — `grep` finds zero `#[cfg(feature = "python")]` in `tests/rust_cst_fegen/src/parser.rs`. The generator (`gsm2parser_rs.py`) does not yet emit the python-gated block. Phase 3's sole generator change is adding that emission.

4. **Python `fltk_trivia_parser.py` vs `fltk_parser.py`**: the parity test's `capture_trivia=True` comparison target is a separate Python-generated file. It exists in `fltk/fegen/` alongside `fltk_parser.py`. Confirmed by `genparser.py` `generate` command emitting `<base>_trivia_parser.py` (genparser.py:250-252).

5. **`pos` validation boundary in Python pymethod**: controlling design §4 specifies the Python boundary validates `pos >= 0 && pos <= len` → `ValueError`. The existing Python parser does no such validation (fltk_parser.py:103 — takes `pos: int` unchecked). This is a deliberate addition for the Rust boundary (the pure-Rust path returns `None` for out-of-range; the Python boundary converts to a clean error instead).
