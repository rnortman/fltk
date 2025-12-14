# FLTK Rust Parser with Python Interface - Design Document

**Version:** 1.0
**Date:** 2025-12-14
**Status:** Design Proposal

## Executive Summary

This document outlines a design for generating Rust-based parsers from FLTK grammars that provide a Python-compatible API. The goal is to create a near drop-in replacement for FLTK's existing Python parsers that delivers significantly better performance while maintaining API compatibility.

### Key Design Goals

1. **Performance**: Leverage Rust's zero-cost abstractions and efficient memory management to achieve 10-100x speedup over pure Python parsers
2. **API Compatibility**: Provide CST node structures and parser APIs that are compatible with existing Python code
3. **Drop-in Replacement**: Minimize code changes required to switch from Python parsers to Rust parsers
4. **Maintainability**: Reuse existing FLTK grammar definitions and generation infrastructure

### Recommended Approach

Generate both Rust parsers and Python bindings from the same `.fltkg` grammar files using:
- **PyO3** for Rust-Python interop
- **Maturin** for packaging and distribution
- Extended **gsm2parser.py** and **gsm2tree.py** with Rust code generation backends
- Rust's **regex crate** for pattern matching
- Custom packrat implementation in Rust (based on existing Python algorithm)

### Expected Performance Gains

Based on real-world Rust-Python parser comparisons:
- **10-100x faster** for compute-intensive parsing operations
- **2-5x faster** for end-to-end parsing including Python FFI overhead
- **Minimal overhead** for CST node access (same as Python dataclass access)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Code Generation Strategy](#code-generation-strategy)
3. [API Compatibility Design](#api-compatibility-design)
4. [Performance Optimization Strategy](#performance-optimization-strategy)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Technical Challenges and Solutions](#technical-challenges-and-solutions)
7. [References and Resources](#references-and-resources)

---

## Architecture Overview

### Current FLTK Architecture

```
.fltkg grammar
    ↓
fltk_parser.py (parse grammar)
    ↓
fltk2gsm.py (convert to GSM)
    ↓
    ├─→ gsm2tree.py → Python CST classes
    └─→ gsm2parser.py → Python Parser class
    ↓
iir/py/compiler.py (compile to Python AST)
    ↓
Runtime Python modules
```

### Proposed Rust Architecture

```
.fltkg grammar
    ↓
fltk_parser.py (parse grammar)
    ↓
fltk2gsm.py (convert to GSM)
    ↓
    ├─→ gsm2tree_rs.py → Rust CST structs + PyO3 bindings
    └─→ gsm2parser_rs.py → Rust Parser struct + PyO3 bindings
    ↓
Direct Rust code generation (no IIR needed)
    ↓
    ├─→ Generated Rust source files
    ├─→ Cargo.toml configuration
    └─→ PyO3 module definitions
    ↓
cargo build / maturin build
    ↓
Python-importable .so/.pyd modules
```

### Dual-Mode Generation

The system should support both Python and Rust targets:

```python
# Generate Python parser (existing)
result = generate_parser(grammar, target="python", capture_trivia=True)

# Generate Rust parser with Python bindings
result = generate_parser(grammar, target="rust", capture_trivia=True)
# Returns: RustParserSpec with source files and build config

# Or generate both
result = generate_parser(grammar, target="both", capture_trivia=True)
```

---

## Code Generation Strategy

### 1. Rust Code Generation Modules

Create new modules parallel to existing Python generators:

```
fltk/fegen/
├── gsm2tree_rs.py       # Generate Rust CST structs
├── gsm2parser_rs.py     # Generate Rust parser
└── rsrt/                # Rust runtime templates
    ├── packrat.rs.template
    ├── terminalsrc.rs.template
    ├── errors.rs.template
    └── pyinterface.rs.template
```

### 2. Generated Rust Module Structure

For a grammar named `toy.fltkg`, generate:

```
generated/
├── Cargo.toml           # Project manifest
├── pyproject.toml       # Maturin configuration
└── src/
    ├── lib.rs           # PyO3 module entry point
    ├── cst.rs           # CST node structs
    ├── parser.rs        # Parser implementation
    ├── runtime/
    │   ├── mod.rs
    │   ├── packrat.rs   # Packrat memoization
    │   ├── terminalsrc.rs
    │   └── errors.rs
    └── pyinterface.rs   # Python API wrappers
```

### 3. Generation Algorithm

**Phase 1: Generate Core Rust Code**

```python
def generate_rust_parser(grammar: Grammar, capture_trivia: bool = False) -> RustParserSpec:
    # Generate CST structs
    cst_code = generate_rust_cst(grammar)

    # Generate parser implementation
    parser_code = generate_rust_parser_impl(grammar, capture_trivia)

    # Generate runtime support (copy from templates)
    runtime_code = copy_rust_runtime_templates()

    # Generate PyO3 bindings
    pyinterface_code = generate_pyo3_bindings(grammar)

    # Generate build configuration
    cargo_toml = generate_cargo_config(grammar)
    pyproject_toml = generate_maturin_config(grammar)

    return RustParserSpec(
        cst=cst_code,
        parser=parser_code,
        runtime=runtime_code,
        pyinterface=pyinterface_code,
        cargo_toml=cargo_toml,
        pyproject_toml=pyproject_toml,
    )
```

**Phase 2: Build Rust Extension**

```bash
# Using Maturin
cd generated
maturin build --release

# Or during development
maturin develop
```

**Phase 3: Import from Python**

```python
# Import Rust parser (drop-in replacement)
from toy_parser_rs import Parser, Expr, Term, Factor, Number, Trivia
from toy_parser_rs import TerminalSource, Span

# Use exactly like Python version
terminalsrc = TerminalSource("1 + 2 * 3")
parser = Parser(terminalsrc)
result = parser.apply__parse_expr(0)
```

---

## API Compatibility Design

### Python CST API to Replicate

Current Python CST node structure:

```python
@dataclasses.dataclass
class Expr:
    class Label(enum.Enum):
        PLUS = enum.auto()
        TERM = enum.auto()

    span: Span
    children: list[tuple[Label | None, Union[Term, Trivia, Span]]]

    # Generic methods
    def append(self, child, label=None) -> None: ...
    def extend(self, children, label=None) -> None: ...
    def child(self) -> tuple[Label | None, ...]: ...

    # Label-specific methods
    def append_term(self, child: Term) -> None: ...
    def children_term(self) -> Iterator[Term]: ...
    def child_term(self) -> Term: ...
    def maybe_term(self) -> Optional[Term]: ...
```

### Rust Implementation with PyO3

**Core Rust CST Structure:**

```rust
use pyo3::prelude::*;
use pyo3::types::PyList;

#[pyclass]
pub struct Span {
    #[pyo3(get, set)]
    pub start: usize,
    #[pyo3(get, set)]
    pub end: usize,
}

#[pymethods]
impl Span {
    #[new]
    fn new(start: usize, end: usize) -> Self {
        Span { start, end }
    }
}

#[pyclass]
#[derive(Clone)]
pub enum ExprLabel {
    Plus,
    Term,
}

// Enum for child types (using PyObject for flexibility)
#[pyclass]
pub struct ExprChild {
    label: Option<ExprLabel>,
    value: PyObject,  // Can hold Term, Trivia, or Span
}

#[pyclass]
pub struct Expr {
    #[pyo3(get, set)]
    pub span: Py<Span>,

    // Store children as PyObject for flexibility
    children: Vec<(Option<ExprLabel>, PyObject)>,
}

#[pymethods]
impl Expr {
    #[new]
    fn new(py: Python, span: Option<Py<Span>>) -> PyResult<Self> {
        let span = span.unwrap_or_else(|| {
            Py::new(py, Span::new(usize::MAX, usize::MAX)).unwrap()
        });
        Ok(Expr {
            span,
            children: Vec::new(),
        })
    }

    // Generic append method
    fn append(&mut self, child: PyObject, label: Option<ExprLabel>) {
        self.children.push((label, child));
    }

    // Generic extend method
    fn extend(&mut self, children: Vec<PyObject>, label: Option<ExprLabel>) {
        for child in children {
            self.children.push((label, child));
        }
    }

    // Get children as Python list
    #[pyo3(name = "children")]
    fn py_children(&self, py: Python) -> PyResult<PyObject> {
        let list = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj = match label {
                Some(l) => l.clone().into_py(py),
                None => py.None(),
            };
            list.append((label_obj, child.clone_ref(py)))?;
        }
        Ok(list.into())
    }

    // Label-specific methods
    fn append_term(&mut self, child: Py<Term>) {
        self.children.push((Some(ExprLabel::Term), child.into()));
    }

    fn children_term(&self, py: Python) -> PyResult<Vec<Py<Term>>> {
        let mut result = Vec::new();
        for (label, child) in &self.children {
            if matches!(label, Some(ExprLabel::Term)) {
                result.push(child.clone_ref(py).extract(py)?);
            }
        }
        Ok(result)
    }

    fn child_term(&self, py: Python) -> PyResult<Py<Term>> {
        let terms = self.children_term(py)?;
        if terms.len() != 1 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Expected one term child but have {}", terms.len())
            ));
        }
        Ok(terms[0].clone_ref(py))
    }

    fn maybe_term(&self, py: Python) -> PyResult<Option<Py<Term>>> {
        let terms = self.children_term(py)?;
        if terms.len() > 1 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Expected at most one term child but have {}", terms.len())
            ));
        }
        Ok(terms.first().map(|t| t.clone_ref(py)))
    }
}
```

**Alternative: Type-Safe Rust Enums**

For better performance, use Rust enums internally and convert to Python:

```rust
// Internal Rust representation (type-safe, efficient)
pub enum ExprChildInternal {
    Term(Box<Term>),
    Trivia(Box<Trivia>),
    Span(Span),
}

#[pyclass]
pub struct Expr {
    #[pyo3(get)]
    pub span: Span,

    // Internal storage (efficient)
    children_internal: Vec<(Option<ExprLabel>, ExprChildInternal)>,
}

#[pymethods]
impl Expr {
    // Expose children as Python objects
    #[getter]
    fn children(&self, py: Python) -> PyResult<Vec<(Option<ExprLabel>, PyObject)>> {
        self.children_internal
            .iter()
            .map(|(label, child)| {
                let py_child = match child {
                    ExprChildInternal::Term(t) => Py::new(py, t.as_ref().clone())?.into_py(py),
                    ExprChildInternal::Trivia(t) => Py::new(py, t.as_ref().clone())?.into_py(py),
                    ExprChildInternal::Span(s) => Py::new(py, *s)?.into_py(py),
                };
                Ok((label.clone(), py_child))
            })
            .collect()
    }
}
```

### Parser API Compatibility

**Python Parser API:**

```python
class Parser:
    def __init__(self, terminalsrc: TerminalSource): ...
    def apply__parse_expr(self, pos: int) -> ApplyResult[int, Expr] | None: ...
    def consume_literal(self, pos: int, literal: str) -> ApplyResult[int, Span] | None: ...
    def consume_regex(self, pos: int, regex: str) -> ApplyResult[int, Span] | None: ...
```

**Rust Implementation:**

```rust
#[pyclass]
pub struct Parser {
    terminalsrc: Py<TerminalSource>,
    packrat: Packrat,
    error_tracker: ErrorTracker,
    rule_names: Vec<String>,
    // Caches stored as internal Rust structures
    cache_expr: HashMap<usize, MemoEntry<Expr>>,
    cache_term: HashMap<usize, MemoEntry<Term>>,
    // ... etc
}

#[pymethods]
impl Parser {
    #[new]
    fn new(terminalsrc: Py<TerminalSource>) -> Self {
        Parser {
            terminalsrc,
            packrat: Packrat::new(),
            error_tracker: ErrorTracker::new(),
            rule_names: vec![
                "expr".to_string(),
                "term".to_string(),
                // ...
            ],
            cache_expr: HashMap::new(),
            cache_term: HashMap::new(),
        }
    }

    fn apply__parse_expr(&mut self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Expr>>>
    {
        self.packrat.apply(
            || self.parse_expr(py, pos),
            0,  // rule_id
            &mut self.cache_expr,
            pos,
        )
    }

    fn consume_literal(&mut self, py: Python, pos: usize, literal: &str)
        -> PyResult<Option<ApplyResult<Span>>>
    {
        let terminalsrc = self.terminalsrc.borrow(py);
        if let Some(span) = terminalsrc.consume_literal(pos, literal) {
            Ok(Some(ApplyResult { pos: span.end, result: span }))
        } else {
            self.error_tracker.fail_literal(
                pos,
                *self.packrat.invocation_stack.last().unwrap(),
                literal
            );
            Ok(None)
        }
    }

    // Internal parse methods
    fn parse_expr(&mut self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Expr>>>
    {
        self.parse_expr__alt0(py, pos)
    }

    fn parse_expr__alt0(&mut self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Expr>>>
    {
        let mut result = Expr::new(py, Some(Py::new(py, Span::new(pos, usize::MAX))?))?;
        let mut current_pos = pos;

        // Parse item0: term
        if let Some(item0) = self.parse_expr__alt0__item0(py, current_pos)? {
            current_pos = item0.pos;
            result.append_term(Py::new(py, item0.result)?);
        } else {
            return Ok(None);
        }

        // Parse whitespace
        if let Some(ws) = self.apply__parse__trivia(py, current_pos)? {
            current_pos = ws.pos;
        }

        // Parse item1: (plus "+" term)*
        if let Some(item1) = self.parse_expr__alt0__item1(py, current_pos)? {
            current_pos = item1.pos;
            // Inline children
            let item1_children = item1.result.children_internal;
            for (label, child) in item1_children {
                result.children_internal.push((label, child));
            }
        }

        // Update span
        result.span = Py::new(py, Span::new(pos, current_pos))?;

        Ok(Some(ApplyResult {
            pos: current_pos,
            result,
        }))
    }
}
```

### Runtime Support Structures

**TerminalSource:**

```rust
use regex::Regex;
use std::sync::Arc;

#[pyclass]
pub struct TerminalSource {
    terminals: String,
    terminals_len: usize,
    line_ends: Option<Vec<usize>>,
    // Cache compiled regexes
    regex_cache: Arc<DashMap<String, Regex>>,
}

#[pymethods]
impl TerminalSource {
    #[new]
    fn new(terminals: String) -> Self {
        let terminals_len = terminals.len();
        TerminalSource {
            terminals,
            terminals_len,
            line_ends: None,
            regex_cache: Arc::new(DashMap::new()),
        }
    }

    fn consume_literal(&self, pos: usize, literal: &str) -> Option<Span> {
        let literal_len = literal.len();
        if pos + literal_len > self.terminals_len {
            return None;
        }

        // Fast comparison using byte slices
        if &self.terminals[pos..pos + literal_len] == literal {
            Some(Span::new(pos, pos + literal_len))
        } else {
            None
        }
    }

    fn consume_regex(&mut self, pos: usize, regex_pattern: &str) -> PyResult<Option<Span>> {
        // Get or compile regex
        let regex = if let Some(re) = self.regex_cache.get(regex_pattern) {
            re.clone()
        } else {
            let re = Regex::new(regex_pattern)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid regex: {}", e)
                ))?;
            self.regex_cache.insert(regex_pattern.to_string(), re.clone());
            re
        };

        // Match from position
        if let Some(mat) = regex.find_at(&self.terminals, pos) {
            if mat.start() == pos {
                return Ok(Some(Span::new(pos, mat.end())));
            }
        }
        Ok(None)
    }

    fn pos_to_line_col(&mut self, pos: usize) -> PyResult<LineColPos> {
        // Implement line/column calculation (same algorithm as Python)
        // ...
    }
}
```

**Packrat Memoization:**

```rust
use std::collections::HashMap;

pub struct MemoEntry<T> {
    result: MemoResult<T>,
    final_pos: usize,
}

pub enum MemoResult<T> {
    Poison(Option<RecursionInfo>),
    Success(T),
    Failure,
}

pub struct RecursionInfo {
    rule_id: usize,
    involved: HashSet<usize>,
    eval_set: HashSet<usize>,
}

pub struct Packrat {
    pub invocation_stack: Vec<usize>,
    recursions: HashMap<usize, RecursionInfo>,
}

impl Packrat {
    pub fn new() -> Self {
        Packrat {
            invocation_stack: Vec::new(),
            recursions: HashMap::new(),
        }
    }

    pub fn apply<T, F>(
        &mut self,
        rule_callable: F,
        rule_id: usize,
        rule_cache: &mut HashMap<usize, MemoEntry<T>>,
        pos: usize,
    ) -> Option<ApplyResult<T>>
    where
        F: FnOnce() -> Option<ApplyResult<T>>,
        T: Clone,
    {
        // Implement packrat algorithm (port from Python version)
        // This is a direct translation of the Python algorithm
        // See fltk/fegen/pyrt/memo.py for reference

        // ... implementation follows Python algorithm exactly ...
    }
}
```

---

## Performance Optimization Strategy

### 1. Zero-Copy String Handling

```rust
// Store source as Arc<str> for cheap cloning
pub struct TerminalSource {
    terminals: Arc<str>,
    // ... other fields
}

// Spans just reference offsets, no string copying
pub struct Span {
    start: usize,
    end: usize,
}

// Extract text when needed
impl TerminalSource {
    pub fn span_text(&self, span: &Span) -> &str {
        &self.terminals[span.start..span.end]
    }
}
```

### 2. Regex Caching

```rust
use dashmap::DashMap;  // Thread-safe HashMap
use once_cell::sync::Lazy;

// Global regex cache (across all parser instances)
static REGEX_CACHE: Lazy<DashMap<String, Regex>> =
    Lazy::new(|| DashMap::new());

pub fn get_or_compile_regex(pattern: &str) -> Result<Regex> {
    if let Some(re) = REGEX_CACHE.get(pattern) {
        Ok(re.clone())
    } else {
        let re = Regex::new(pattern)?;
        REGEX_CACHE.insert(pattern.to_string(), re.clone());
        Ok(re)
    }
}
```

### 3. Arena Allocation for CST Nodes

```rust
use bumpalo::Bump;

pub struct Parser<'arena> {
    arena: &'arena Bump,
    // ... other fields
}

// Allocate nodes in arena for fast allocation and deallocation
impl<'arena> Parser<'arena> {
    fn allocate_expr(&self) -> &'arena mut Expr {
        self.arena.alloc(Expr::new())
    }
}
```

**Note:** Arena allocation conflicts with PyO3's lifetime requirements. Consider this optimization only for internal Rust-only parsers, not Python-exposed ones.

### 4. Inline Small Vectors

```rust
use smallvec::SmallVec;

// Most CST nodes have few children; avoid heap allocation
pub struct Expr {
    pub span: Span,
    // Store up to 4 children inline, then spill to heap
    pub children: SmallVec<[(Option<ExprLabel>, ExprChildInternal); 4]>,
}
```

### 5. Specialized Fast Paths

```rust
impl TerminalSource {
    // Fast path for single-character literals
    #[inline(always)]
    pub fn consume_char(&self, pos: usize, ch: char) -> Option<Span> {
        if pos < self.terminals_len {
            let bytes = self.terminals.as_bytes();
            if bytes[pos] == ch as u8 && ch.is_ascii() {
                return Some(Span::new(pos, pos + 1));
            }
        }
        None
    }

    // Fast path for ASCII-only literals
    #[inline(always)]
    pub fn consume_literal_ascii(&self, pos: usize, literal: &[u8]) -> Option<Span> {
        let len = literal.len();
        if pos + len <= self.terminals_len {
            let slice = &self.terminals.as_bytes()[pos..pos + len];
            if slice == literal {
                return Some(Span::new(pos, pos + len));
            }
        }
        None
    }
}
```

### 6. Parallel Parsing (Future Enhancement)

```rust
use rayon::prelude::*;

// Parse multiple independent files in parallel
pub fn parse_files(files: Vec<String>) -> Vec<ParseResult> {
    files.par_iter()
        .map(|source| {
            let terminalsrc = TerminalSource::new(source.clone());
            let mut parser = Parser::new(terminalsrc);
            parser.parse()
        })
        .collect()
}
```

---

## Implementation Roadmap

### Phase 1: Foundation (2-3 weeks)

**Week 1: Runtime Infrastructure**
- [ ] Implement Rust runtime support structures
  - [ ] `terminalsrc.rs`: TerminalSource with Span
  - [ ] `memo.rs`: Packrat memoization with left-recursion support
  - [ ] `errors.rs`: ErrorTracker and error formatting
- [ ] Create PyO3 bindings for runtime structures
- [ ] Write unit tests for runtime (port from Python tests)

**Week 2: Code Generation**
- [ ] Implement `gsm2tree_rs.py`: Generate Rust CST structs
  - [ ] Generate struct definitions with PyO3 decorators
  - [ ] Generate Label enums
  - [ ] Generate accessor methods (append_*, children_*, child_*, maybe_*)
- [ ] Implement `gsm2parser_rs.py`: Generate Rust parser
  - [ ] Generate parse_* methods following Python structure
  - [ ] Generate apply__parse_* methods with memoization
  - [ ] Handle trivia insertion at separators
- [ ] Generate Cargo.toml and pyproject.toml configuration

**Week 3: Testing and Validation**
- [ ] Test with toy.fltkg grammar
- [ ] Compare output with Python parser (CST structure match)
- [ ] Performance benchmarking
- [ ] Fix bugs and edge cases

### Phase 2: Full Feature Parity (2-3 weeks)

**Week 4-5: Complete Feature Set**
- [ ] Handle all quantifiers (?, +, *)
- [ ] Handle all dispositions (%, $, !)
- [ ] Handle all separators (., ,, :)
- [ ] Trivia capture modes (capture_trivia=True/False)
- [ ] Inline disposition support
- [ ] Sub-expression handling
- [ ] Error message formatting

**Week 6: Real-World Testing**
- [ ] Test with fegen.fltkg (self-hosting test)
- [ ] Test with user grammars
- [ ] Performance tuning
- [ ] Memory profiling

### Phase 3: Polish and Documentation (1-2 weeks)

**Week 7: Optimization**
- [ ] Implement regex caching
- [ ] Optimize hot paths
- [ ] Reduce allocations
- [ ] Profile and optimize

**Week 8: Documentation and Release**
- [ ] Write user documentation
- [ ] Create migration guide
- [ ] Package for PyPI via Maturin
- [ ] Release v0.1.0

### Phase 4: Advanced Features (Future)

- [ ] Incremental parsing support
- [ ] Parallel multi-file parsing
- [ ] WASM compilation for browser
- [ ] Language Server Protocol (LSP) support
- [ ] Syntax highlighting via Tree-sitter compatibility

---

## Technical Challenges and Solutions

### Challenge 1: Python Object Lifetime Management

**Problem:** Rust requires explicit lifetime management, but Python objects can live arbitrarily long.

**Solution:** Use `Py<T>` for all Python-exposed objects. This is PyO3's reference-counted pointer that doesn't carry a lifetime parameter:

```rust
#[pyclass]
pub struct Expr {
    pub span: Py<Span>,  // Not Span, not &Span
    children: Vec<(Option<ExprLabel>, PyObject)>,  // PyObject = Py<PyAny>
}
```

### Challenge 2: Heterogeneous Children Lists

**Problem:** Python allows `list[tuple[Label | None, Union[Term, Trivia, Span]]]` but Rust enums are more restrictive.

**Solution 1 (Simple):** Use `PyObject` for maximum flexibility:
```rust
children: Vec<(Option<ExprLabel>, PyObject)>
```

**Solution 2 (Performant):** Use Rust enum internally, convert to PyObject on access:
```rust
enum ChildInternal {
    Term(Box<Term>),
    Trivia(Box<Trivia>),
    Span(Span),
}

#[getter]
fn children(&self, py: Python) -> PyResult<Vec<(Option<ExprLabel>, PyObject)>> {
    // Convert on demand
}
```

**Recommendation:** Start with Solution 1, optimize to Solution 2 if profiling shows it's needed.

### Challenge 3: Mutable Parser State

**Problem:** Parser methods need `&mut self` but PyO3 methods take `&self` by default.

**Solution:** Use interior mutability with `RefCell` or `Mutex`:

```rust
#[pyclass]
pub struct Parser {
    // Immutable
    terminalsrc: Py<TerminalSource>,
    rule_names: Vec<String>,

    // Mutable state wrapped in RefCell
    state: RefCell<ParserState>,
}

struct ParserState {
    packrat: Packrat,
    error_tracker: ErrorTracker,
    caches: HashMap<usize, Box<dyn Any>>,
}

#[pymethods]
impl Parser {
    fn apply__parse_expr(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Expr>>>
    {
        let mut state = self.state.borrow_mut();
        // Now we have &mut access
    }
}
```

### Challenge 4: Generic Type Erasure for Caches

**Problem:** Each rule has a different cache type (`HashMap<usize, MemoEntry<Expr>>` vs `HashMap<usize, MemoEntry<Term>>`).

**Solution:** Use trait objects or type erasure:

```rust
trait MemoCache {
    fn get(&self, pos: usize) -> Option<Box<dyn Any>>;
    fn insert(&mut self, pos: usize, entry: Box<dyn Any>);
}

pub struct ParserState {
    caches: HashMap<usize, Box<dyn MemoCache>>,
}
```

**Alternative:** Generate separate cache fields per rule (simpler, no dynamic dispatch):

```rust
pub struct ParserState {
    cache_expr: HashMap<usize, MemoEntry<Expr>>,
    cache_term: HashMap<usize, MemoEntry<Term>>,
    // ... one per rule
}
```

**Recommendation:** Use separate fields (clearer, faster).

### Challenge 5: Regex Compilation Overhead

**Problem:** Regex compilation in Rust is expensive (~microseconds to milliseconds).

**Solution:** Cache compiled regexes globally:

```rust
use dashmap::DashMap;
use once_cell::sync::Lazy;

static REGEX_CACHE: Lazy<DashMap<String, Regex>> =
    Lazy::new(DashMap::new);

fn consume_regex(&self, pos: usize, pattern: &str) -> Option<Span> {
    let regex = REGEX_CACHE.entry(pattern.to_string())
        .or_insert_with(|| Regex::new(pattern).unwrap())
        .clone();
    // ... use regex
}
```

### Challenge 6: Error Handling Between Rust and Python

**Problem:** Rust uses `Result<T, E>` while Python uses exceptions.

**Solution:** PyO3 automatically converts:

```rust
// Rust panics → Python exceptions (catch with panic hook)
// Rust Result<T, PyErr> → Python exceptions (automatic)

fn parse_expr(&mut self, py: Python, pos: usize) -> PyResult<Option<ApplyResult<Expr>>> {
    // Return PyResult for Python compatibility
    // Use ? operator for error propagation
    let terminalsrc = self.terminalsrc.borrow(py);
    // ...
}
```

---

## References and Resources

### PyO3 Documentation
- [Python classes - PyO3 user guide](https://pyo3.rs/main/class.html)
- [PyO3 GitHub Repository](https://github.com/PyO3/pyo3)
- [Conversion traits - PyO3 user guide](https://pyo3.rs/main/conversions/traits)
- [GIL lifetimes, mutability and Python object types](https://pyo3.rs/v0.20.1/types)

### Performance References
- [Performance Comparison: Rust vs PyO3 vs Python](https://marshalshi.medium.com/performance-comparison-rust-vs-pyo3-vs-python-6480709be8d)
- [Making Python 100x faster with less than 100 lines of Rust](https://ohadravid.github.io/posts/2023-03-rusty-python/)
- [Performance - PyO3 user guide](https://pyo3.rs/main/performance)
- [Efficiently Extending Python: PyO3 and Rust in Action](https://www.blueshoe.io/blog/python-rust-pyo3/)

### Rust Parsing Libraries
- [rust-peg: PEG parser generator for Rust](https://github.com/kevinmehall/rust-peg)
- [Peginator: PEG parser generator for creating ASTs in Rust](https://github.com/badicsalex/peginator)
- [regex crate documentation](https://docs.rs/regex/latest/regex/)
- [Rust regex performance comparison](https://github.com/rust-leipzig/regex-performance)

### Real-World Examples
- [Ruff: Internals of a Rust-backed Python linter-formatter](https://compileralchemy.substack.com/p/ruff-internals-of-a-rust-backed-python)
- [Ruff v0.4.0: hand-written recursive descent parser for Python](https://astral.sh/blog/ruff-v0.4.0)
- [tree-sitter Rust bindings](https://github.com/tree-sitter/rust-tree-sitter)
- [tree_sitter_python crate](https://docs.rs/tree-sitter-python)

### Academic References
- [Packrat Parsing and Parsing Expression Grammars](https://bford.info/packrat/) - Original packrat parsing paper
- [Parsing Expression Grammars](https://en.wikipedia.org/wiki/Parsing_expression_grammar) - Background on PEG parsing

---

## Appendix: Example Generated Code

See `docs/rust-python-parser-examples.md` for complete examples of:
- Generated Rust CST structs
- Generated Rust parser implementation
- PyO3 module configuration
- Python usage examples
- Performance benchmarks
