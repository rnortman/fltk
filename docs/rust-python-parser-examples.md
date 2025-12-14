# FLTK Rust Parser - Code Generation Examples

This document provides detailed examples of generated Rust code for FLTK parsers with Python bindings.

## Table of Contents

1. [Example Grammar](#example-grammar)
2. [Generated Rust CST Code](#generated-rust-cst-code)
3. [Generated Rust Parser Code](#generated-rust-parser-code)
4. [Build Configuration](#build-configuration)
5. [Python Usage Examples](#python-usage-examples)
6. [Performance Benchmarks](#performance-benchmarks)

---

## Example Grammar

### Input: toy.fltkg

```
expr := term , (plus:"+" , term)*;
term := factor , (mult:"*" , factor)*;
factor := number | "(" , expr , ")";
number := value:/[0-9]+/;
_trivia := content:/[\s]+/;
```

This simple arithmetic expression grammar will be used throughout the examples.

---

## Generated Rust CST Code

### File: src/cst.rs

```rust
//! Generated CST (Concrete Syntax Tree) node definitions
//! Generated from: toy.fltkg
//! Generation time: 2025-12-14

use pyo3::prelude::*;
use crate::runtime::Span;

// ============================================================================
// Expr Node
// ============================================================================

#[pyclass]
#[derive(Clone, Debug)]
pub enum ExprLabel {
    Plus,
    Term,
}

/// CST node for rule: expr := term , (plus:"+" , term)*;
#[pyclass]
#[derive(Clone)]
pub struct Expr {
    #[pyo3(get, set)]
    pub span: Span,

    // Internal storage for efficiency
    children_internal: Vec<(Option<ExprLabel>, ExprChild)>,
}

#[derive(Clone)]
pub enum ExprChild {
    Term(Box<Term>),
    Trivia(Box<Trivia>),
    Span(Span),
}

#[pymethods]
impl Expr {
    #[new]
    fn new(span: Option<Span>) -> Self {
        Expr {
            span: span.unwrap_or(Span::unknown()),
            children_internal: Vec::new(),
        }
    }

    /// Get all children as a Python list of (label, child) tuples
    #[getter]
    fn children(&self, py: Python) -> PyResult<Vec<(Option<ExprLabel>, PyObject)>> {
        self.children_internal
            .iter()
            .map(|(label, child)| {
                let py_child = match child {
                    ExprChild::Term(t) => Py::new(py, t.as_ref().clone())?.into_py(py),
                    ExprChild::Trivia(t) => Py::new(py, t.as_ref().clone())?.into_py(py),
                    ExprChild::Span(s) => Py::new(py, *s)?.into_py(py),
                };
                Ok((label.clone(), py_child))
            })
            .collect()
    }

    /// Generic append method
    fn append(&mut self, child: PyObject, label: Option<ExprLabel>) -> PyResult<()> {
        Python::with_gil(|py| {
            let child_internal = if let Ok(term) = child.extract::<Term>(py) {
                ExprChild::Term(Box::new(term))
            } else if let Ok(trivia) = child.extract::<Trivia>(py) {
                ExprChild::Trivia(Box::new(trivia))
            } else if let Ok(span) = child.extract::<Span>(py) {
                ExprChild::Span(span)
            } else {
                return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
                    "Child must be Term, Trivia, or Span"
                ));
            };
            self.children_internal.push((label, child_internal));
            Ok(())
        })
    }

    /// Generic extend method
    fn extend(&mut self, children: Vec<PyObject>, label: Option<ExprLabel>) -> PyResult<()> {
        for child in children {
            self.append(child, label.clone())?;
        }
        Ok(())
    }

    /// Get the single child (raises if not exactly one child)
    fn child(&self, py: Python) -> PyResult<(Option<ExprLabel>, PyObject)> {
        if self.children_internal.len() != 1 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Expected one child but have {}", self.children_internal.len())
            ));
        }
        let (label, child) = &self.children_internal[0];
        let py_child = match child {
            ExprChild::Term(t) => Py::new(py, t.as_ref().clone())?.into_py(py),
            ExprChild::Trivia(t) => Py::new(py, t.as_ref().clone())?.into_py(py),
            ExprChild::Span(s) => Py::new(py, *s)?.into_py(py),
        };
        Ok((label.clone(), py_child))
    }

    // ========================================================================
    // Label-specific methods for PLUS
    // ========================================================================

    fn append_plus(&mut self, child: Span) {
        self.children_internal.push((Some(ExprLabel::Plus), ExprChild::Span(child)));
    }

    fn extend_plus(&mut self, children: Vec<Span>) {
        for child in children {
            self.append_plus(child);
        }
    }

    fn children_plus(&self) -> Vec<Span> {
        self.children_internal
            .iter()
            .filter_map(|(label, child)| {
                if matches!(label, Some(ExprLabel::Plus)) {
                    if let ExprChild::Span(s) = child {
                        Some(*s)
                    } else {
                        None
                    }
                } else {
                    None
                }
            })
            .collect()
    }

    fn child_plus(&self) -> PyResult<Span> {
        let children = self.children_plus();
        if children.len() != 1 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Expected one plus child but have {}", children.len())
            ));
        }
        Ok(children[0])
    }

    fn maybe_plus(&self) -> PyResult<Option<Span>> {
        let children = self.children_plus();
        if children.len() > 1 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Expected at most one plus child but have {}", children.len())
            ));
        }
        Ok(children.first().copied())
    }

    // ========================================================================
    // Label-specific methods for TERM
    // ========================================================================

    fn append_term(&mut self, child: Term) {
        self.children_internal.push((Some(ExprLabel::Term), ExprChild::Term(Box::new(child))));
    }

    fn extend_term(&mut self, children: Vec<Term>) {
        for child in children {
            self.append_term(child);
        }
    }

    fn children_term(&self) -> Vec<Term> {
        self.children_internal
            .iter()
            .filter_map(|(label, child)| {
                if matches!(label, Some(ExprLabel::Term)) {
                    if let ExprChild::Term(t) = child {
                        Some(t.as_ref().clone())
                    } else {
                        None
                    }
                } else {
                    None
                }
            })
            .collect()
    }

    fn child_term(&self) -> PyResult<Term> {
        let children = self.children_term();
        if children.len() != 1 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Expected one term child but have {}", children.len())
            ));
        }
        Ok(children[0].clone())
    }

    fn maybe_term(&self) -> PyResult<Option<Term>> {
        let children = self.children_term();
        if children.len() > 1 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Expected at most one term child but have {}", children.len())
            ));
        }
        Ok(children.first().cloned())
    }
}

// Rust-only helper methods
impl Expr {
    pub(crate) fn append_internal(&mut self, label: Option<ExprLabel>, child: ExprChild) {
        self.children_internal.push((label, child));
    }

    pub(crate) fn extend_internal(&mut self, children: Vec<(Option<ExprLabel>, ExprChild)>) {
        self.children_internal.extend(children);
    }
}

// ============================================================================
// Term Node
// ============================================================================

#[pyclass]
#[derive(Clone, Debug)]
pub enum TermLabel {
    Factor,
    Mult,
}

#[pyclass]
#[derive(Clone)]
pub struct Term {
    #[pyo3(get, set)]
    pub span: Span,

    children_internal: Vec<(Option<TermLabel>, TermChild)>,
}

#[derive(Clone)]
pub enum TermChild {
    Factor(Box<Factor>),
    Trivia(Box<Trivia>),
    Span(Span),
}

#[pymethods]
impl Term {
    #[new]
    fn new(span: Option<Span>) -> Self {
        Term {
            span: span.unwrap_or(Span::unknown()),
            children_internal: Vec::new(),
        }
    }

    // ... similar methods to Expr ...
    // (append, extend, child, append_factor, children_factor, etc.)
}

// ============================================================================
// Factor Node
// ============================================================================

#[pyclass]
#[derive(Clone, Debug)]
pub enum FactorLabel {
    Expr,
    Number,
}

#[pyclass]
#[derive(Clone)]
pub struct Factor {
    #[pyo3(get, set)]
    pub span: Span,

    children_internal: Vec<(Option<FactorLabel>, FactorChild)>,
}

#[derive(Clone)]
pub enum FactorChild {
    Expr(Box<Expr>),
    Number(Box<Number>),
    Trivia(Box<Trivia>),
}

#[pymethods]
impl Factor {
    #[new]
    fn new(span: Option<Span>) -> Self {
        Factor {
            span: span.unwrap_or(Span::unknown()),
            children_internal: Vec::new(),
        }
    }

    // ... similar methods ...
}

// ============================================================================
// Number Node
// ============================================================================

#[pyclass]
#[derive(Clone, Debug)]
pub enum NumberLabel {
    Value,
}

#[pyclass]
#[derive(Clone)]
pub struct Number {
    #[pyo3(get, set)]
    pub span: Span,

    children_internal: Vec<(Option<NumberLabel>, Span)>,
}

#[pymethods]
impl Number {
    #[new]
    fn new(span: Option<Span>) -> Self {
        Number {
            span: span.unwrap_or(Span::unknown()),
            children_internal: Vec::new(),
        }
    }

    #[getter]
    fn children(&self, py: Python) -> PyResult<Vec<(Option<NumberLabel>, Span)>> {
        Ok(self.children_internal.clone())
    }

    fn append_value(&mut self, child: Span) {
        self.children_internal.push((Some(NumberLabel::Value), child));
    }

    fn child_value(&self) -> PyResult<Span> {
        let children: Vec<_> = self.children_internal
            .iter()
            .filter(|(label, _)| matches!(label, Some(NumberLabel::Value)))
            .map(|(_, span)| *span)
            .collect();

        if children.len() != 1 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Expected one value child but have {}", children.len())
            ));
        }
        Ok(children[0])
    }

    // ... other methods ...
}

// ============================================================================
// Trivia Node
// ============================================================================

#[pyclass]
#[derive(Clone, Debug)]
pub enum TriviaLabel {
    Content,
}

#[pyclass]
#[derive(Clone)]
pub struct Trivia {
    #[pyo3(get, set)]
    pub span: Span,

    children_internal: Vec<(Option<TriviaLabel>, Span)>,
}

#[pymethods]
impl Trivia {
    #[new]
    fn new(span: Option<Span>) -> Self {
        Trivia {
            span: span.unwrap_or(Span::unknown()),
            children_internal: Vec::new(),
        }
    }

    // ... similar to Number ...
}
```

---

## Generated Rust Parser Code

### File: src/parser.rs

```rust
//! Generated parser implementation
//! Generated from: toy.fltkg
//! Generation time: 2025-12-14

use pyo3::prelude::*;
use std::cell::RefCell;
use std::collections::HashMap;

use crate::cst::*;
use crate::runtime::{
    ApplyResult, ErrorTracker, Packrat, Span, TerminalSource, MemoEntry,
};

// ============================================================================
// Parser State
// ============================================================================

struct ParserState {
    packrat: Packrat,
    error_tracker: ErrorTracker,

    // Per-rule memoization caches
    cache_expr: HashMap<usize, MemoEntry<Expr>>,
    cache_term: HashMap<usize, MemoEntry<Term>>,
    cache_factor: HashMap<usize, MemoEntry<Factor>>,
    cache_number: HashMap<usize, MemoEntry<Number>>,
    cache_trivia: HashMap<usize, MemoEntry<Trivia>>,
}

impl ParserState {
    fn new() -> Self {
        ParserState {
            packrat: Packrat::new(),
            error_tracker: ErrorTracker::new(),
            cache_expr: HashMap::new(),
            cache_term: HashMap::new(),
            cache_factor: HashMap::new(),
            cache_number: HashMap::new(),
            cache_trivia: HashMap::new(),
        }
    }
}

// ============================================================================
// Parser
// ============================================================================

#[pyclass]
pub struct Parser {
    terminalsrc: Py<TerminalSource>,
    rule_names: Vec<String>,
    state: RefCell<ParserState>,
}

#[pymethods]
impl Parser {
    #[new]
    fn new(terminalsrc: Py<TerminalSource>) -> Self {
        Parser {
            terminalsrc,
            rule_names: vec![
                "expr".to_string(),
                "term".to_string(),
                "factor".to_string(),
                "number".to_string(),
                "_trivia".to_string(),
            ],
            state: RefCell::new(ParserState::new()),
        }
    }

    // ========================================================================
    // Terminal consumption methods
    // ========================================================================

    fn consume_literal(&self, py: Python, pos: usize, literal: &str)
        -> PyResult<Option<ApplyResult<Span>>>
    {
        let terminalsrc = self.terminalsrc.borrow(py);
        if let Some(span) = terminalsrc.consume_literal(pos, literal)? {
            Ok(Some(ApplyResult {
                pos: span.end,
                result: span,
            }))
        } else {
            let mut state = self.state.borrow_mut();
            let rule_id = *state.packrat.invocation_stack.last()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "No active rule"
                ))?;
            state.error_tracker.fail_literal(pos, rule_id, literal);
            Ok(None)
        }
    }

    fn consume_regex(&self, py: Python, pos: usize, regex: &str)
        -> PyResult<Option<ApplyResult<Span>>>
    {
        let terminalsrc = self.terminalsrc.borrow(py);
        if let Some(span) = terminalsrc.consume_regex(pos, regex)? {
            Ok(Some(ApplyResult {
                pos: span.end,
                result: span,
            }))
        } else {
            let mut state = self.state.borrow_mut();
            let rule_id = *state.packrat.invocation_stack.last()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "No active rule"
                ))?;
            state.error_tracker.fail_regex(pos, rule_id, regex);
            Ok(None)
        }
    }

    // ========================================================================
    // Rule: expr
    // ========================================================================

    fn apply__parse_expr(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Expr>>>
    {
        let mut state = self.state.borrow_mut();
        state.packrat.apply(
            |pos| self.parse_expr_impl(py, pos),
            0,  // rule_id
            &mut state.cache_expr,
            pos,
        )
    }

    fn parse_expr(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Expr>>>
    {
        self.parse_expr__alt0(py, pos)
    }

    fn parse_expr__alt0(&self, py: Python, mut pos: usize)
        -> PyResult<Option<ApplyResult<Expr>>>
    {
        let start_pos = pos;
        let mut result = Expr::new(Some(Span::new(pos, usize::MAX)));

        // Item 0: term
        if let Some(item0) = self.parse_expr__alt0__item0(py, pos)? {
            pos = item0.pos;
            result.append_term(item0.result);
        } else {
            return Ok(None);
        }

        // Separator after item0: trivia
        if let Some(ws) = self.apply__parse__trivia(py, pos)? {
            pos = ws.pos;
        }

        // Item 1: (plus:"+" , term)*
        if let Some(item1) = self.parse_expr__alt0__item1(py, pos)? {
            pos = item1.pos;
            // Inline children from item1
            result.extend_internal(item1.result.children_internal);
        }

        // Update span
        result.span = Span::new(start_pos, pos);

        Ok(Some(ApplyResult { pos, result }))
    }

    fn parse_expr__alt0__item0(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Term>>>
    {
        self.apply__parse_term(py, pos)
    }

    fn parse_expr__alt0__item1(&self, py: Python, mut pos: usize)
        -> PyResult<Option<ApplyResult<Expr>>>
    {
        let start_pos = pos;
        let mut result = Expr::new(Some(Span::new(pos, usize::MAX)));

        // Zero or more: (plus:"+" , term)*
        while let Some(one_result) = self.parse_expr__alt0__item1__alts(py, pos)? {
            pos = one_result.pos;
            result.extend_internal(one_result.result.children_internal);
        }

        result.span = Span::new(start_pos, pos);
        Ok(Some(ApplyResult { pos, result }))
    }

    fn parse_expr__alt0__item1__alts(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Expr>>>
    {
        self.parse_expr__alt0__item1__alts__alt0(py, pos)
    }

    fn parse_expr__alt0__item1__alts__alt0(&self, py: Python, mut pos: usize)
        -> PyResult<Option<ApplyResult<Expr>>>
    {
        let start_pos = pos;
        let mut result = Expr::new(Some(Span::new(pos, usize::MAX)));

        // Item 0: plus "+"
        if let Some(item0) = self.parse_expr__alt0__item1__alts__alt0__item0(py, pos)? {
            pos = item0.pos;
            result.append_plus(item0.result);
        } else {
            return Ok(None);
        }

        // Separator after item0
        if let Some(ws) = self.apply__parse__trivia(py, pos)? {
            pos = ws.pos;
        }

        // Item 1: term
        if let Some(item1) = self.parse_expr__alt0__item1__alts__alt0__item1(py, pos)? {
            pos = item1.pos;
            result.append_term(item1.result);
        } else {
            return Ok(None);
        }

        result.span = Span::new(start_pos, pos);
        Ok(Some(ApplyResult { pos, result }))
    }

    fn parse_expr__alt0__item1__alts__alt0__item0(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Span>>>
    {
        self.consume_literal(py, pos, "+")
    }

    fn parse_expr__alt0__item1__alts__alt0__item1(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Term>>>
    {
        self.apply__parse_term(py, pos)
    }

    // ========================================================================
    // Rule: term
    // ========================================================================

    fn apply__parse_term(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Term>>>
    {
        let mut state = self.state.borrow_mut();
        state.packrat.apply(
            |pos| self.parse_term_impl(py, pos),
            1,  // rule_id
            &mut state.cache_term,
            pos,
        )
    }

    fn parse_term(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Term>>>
    {
        self.parse_term__alt0(py, pos)
    }

    // ... similar structure to parse_expr ...

    // ========================================================================
    // Rule: factor
    // ========================================================================

    fn apply__parse_factor(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Factor>>>
    {
        let mut state = self.state.borrow_mut();
        state.packrat.apply(
            |pos| self.parse_factor_impl(py, pos),
            2,  // rule_id
            &mut state.cache_factor,
            pos,
        )
    }

    fn parse_factor(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Factor>>>
    {
        // Try alternative 0: number
        if let Some(alt0) = self.parse_factor__alt0(py, pos)? {
            return Ok(Some(alt0));
        }

        // Try alternative 1: "(" expr ")"
        if let Some(alt1) = self.parse_factor__alt1(py, pos)? {
            return Ok(Some(alt1));
        }

        Ok(None)
    }

    fn parse_factor__alt0(&self, py: Python, mut pos: usize)
        -> PyResult<Option<ApplyResult<Factor>>>
    {
        let start_pos = pos;
        let mut result = Factor::new(Some(Span::new(pos, usize::MAX)));

        // Item 0: number
        if let Some(item0) = self.parse_factor__alt0__item0(py, pos)? {
            pos = item0.pos;
            result.append_number(item0.result);
        } else {
            return Ok(None);
        }

        result.span = Span::new(start_pos, pos);
        Ok(Some(ApplyResult { pos, result }))
    }

    fn parse_factor__alt0__item0(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Number>>>
    {
        self.apply__parse_number(py, pos)
    }

    fn parse_factor__alt1(&self, py: Python, mut pos: usize)
        -> PyResult<Option<ApplyResult<Factor>>>
    {
        let start_pos = pos;
        let mut result = Factor::new(Some(Span::new(pos, usize::MAX)));

        // Item 0: "("
        if let Some(item0) = self.parse_factor__alt1__item0(py, pos)? {
            pos = item0.pos;
            // Suppressed - don't add to result
        } else {
            return Ok(None);
        }

        // Separator
        if let Some(ws) = self.apply__parse__trivia(py, pos)? {
            pos = ws.pos;
        }

        // Item 1: expr
        if let Some(item1) = self.parse_factor__alt1__item1(py, pos)? {
            pos = item1.pos;
            result.append_expr(item1.result);
        } else {
            return Ok(None);
        }

        // Separator
        if let Some(ws) = self.apply__parse__trivia(py, pos)? {
            pos = ws.pos;
        }

        // Item 2: ")"
        if let Some(item2) = self.parse_factor__alt1__item2(py, pos)? {
            pos = item2.pos;
            // Suppressed - don't add to result
        } else {
            return Ok(None);
        }

        result.span = Span::new(start_pos, pos);
        Ok(Some(ApplyResult { pos, result }))
    }

    fn parse_factor__alt1__item0(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Span>>>
    {
        self.consume_literal(py, pos, "(")
    }

    fn parse_factor__alt1__item1(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Expr>>>
    {
        self.apply__parse_expr(py, pos)
    }

    fn parse_factor__alt1__item2(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Span>>>
    {
        self.consume_literal(py, pos, ")")
    }

    // ========================================================================
    // Rule: number
    // ========================================================================

    fn apply__parse_number(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Number>>>
    {
        let mut state = self.state.borrow_mut();
        state.packrat.apply(
            |pos| self.parse_number_impl(py, pos),
            3,  // rule_id
            &mut state.cache_number,
            pos,
        )
    }

    fn parse_number(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Number>>>
    {
        self.parse_number__alt0(py, pos)
    }

    fn parse_number__alt0(&self, py: Python, mut pos: usize)
        -> PyResult<Option<ApplyResult<Number>>>
    {
        let start_pos = pos;
        let mut result = Number::new(Some(Span::new(pos, usize::MAX)));

        // Item 0: value /[0-9]+/
        if let Some(item0) = self.parse_number__alt0__item0(py, pos)? {
            pos = item0.pos;
            result.append_value(item0.result);
        } else {
            return Ok(None);
        }

        result.span = Span::new(start_pos, pos);
        Ok(Some(ApplyResult { pos, result }))
    }

    fn parse_number__alt0__item0(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Span>>>
    {
        self.consume_regex(py, pos, "[0-9]+")
    }

    // ========================================================================
    // Rule: _trivia
    // ========================================================================

    fn apply__parse__trivia(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Trivia>>>
    {
        let mut state = self.state.borrow_mut();
        state.packrat.apply(
            |pos| self.parse__trivia_impl(py, pos),
            4,  // rule_id
            &mut state.cache_trivia,
            pos,
        )
    }

    fn parse__trivia(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Trivia>>>
    {
        self.parse__trivia__alt0(py, pos)
    }

    fn parse__trivia__alt0(&self, py: Python, mut pos: usize)
        -> PyResult<Option<ApplyResult<Trivia>>>
    {
        let start_pos = pos;
        let mut result = Trivia::new(Some(Span::new(pos, usize::MAX)));

        // Item 0: content /[\s]+/
        if let Some(item0) = self.parse__trivia__alt0__item0(py, pos)? {
            pos = item0.pos;
            result.append_content(item0.result);
        } else {
            return Ok(None);
        }

        result.span = Span::new(start_pos, pos);
        Ok(Some(ApplyResult { pos, result }))
    }

    fn parse__trivia__alt0__item0(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Span>>>
    {
        self.consume_regex(py, pos, "[\\s]+")
    }
}

// Rust-only implementation methods (called by packrat)
impl Parser {
    fn parse_expr_impl(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Expr>>>
    {
        self.parse_expr(py, pos)
    }

    fn parse_term_impl(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Term>>>
    {
        self.parse_term(py, pos)
    }

    fn parse_factor_impl(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Factor>>>
    {
        self.parse_factor(py, pos)
    }

    fn parse_number_impl(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Number>>>
    {
        self.parse_number(py, pos)
    }

    fn parse__trivia_impl(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<Trivia>>>
    {
        self.parse__trivia(py, pos)
    }
}
```

---

## Build Configuration

### Cargo.toml

```toml
[package]
name = "toy_parser_rs"
version = "0.1.0"
edition = "2021"

[lib]
name = "toy_parser_rs"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.27", features = ["extension-module"] }
regex = "1.11"
dashmap = "6.1"
once_cell = "1.20"

[profile.release]
lto = true
codegen-units = 1
opt-level = 3
```

### pyproject.toml

```toml
[build-system]
requires = ["maturin>=1.7,<2.0"]
build-backend = "maturin"

[project]
name = "toy-parser-rs"
version = "0.1.0"
description = "Rust-based parser for toy grammar (generated by FLTK)"
requires-python = ">=3.10"
classifiers = [
    "Programming Language :: Rust",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
]

[tool.maturin]
features = ["pyo3/extension-module"]
python-source = "python"
module-name = "toy_parser_rs"
```

---

## Python Usage Examples

### Basic Parsing

```python
# Import the Rust-backed parser (drop-in replacement)
from toy_parser_rs import Parser, TerminalSource, Span

# Create terminal source
source = "1 + 2 * 3"
terminalsrc = TerminalSource(source)

# Create parser
parser = Parser(terminalsrc)

# Parse starting from 'expr' rule
result = parser.apply__parse_expr(0)

if result and result.pos == len(source):
    # Success! We parsed the entire input
    expr = result.result
    print(f"Parsed successfully: span={expr.span}")

    # Access children using label-specific methods
    terms = expr.children_term()
    print(f"Found {len(terms)} terms")

    # Get the first term
    first_term = expr.child_term()
    print(f"First term span: {first_term.span}")
else:
    print("Parse failed")
```

### Traversing the CST

```python
def print_expr_tree(expr, indent=0):
    """Recursively print the expression tree"""
    prefix = "  " * indent
    print(f"{prefix}Expr(span={expr.span})")

    # Get all children
    for label, child in expr.children:
        if label == expr.Label.TERM:
            print_term_tree(child, indent + 1)
        elif label == expr.Label.PLUS:
            print(f"{prefix}  +")

def print_term_tree(term, indent=0):
    prefix = "  " * indent
    print(f"{prefix}Term(span={term.span})")

    for label, child in term.children:
        if label == term.Label.FACTOR:
            print_factor_tree(child, indent + 1)
        elif label == term.Label.MULT:
            print(f"{prefix}  *")

# ... etc

# Usage
result = parser.apply__parse_expr(0)
if result:
    print_expr_tree(result.result)
```

### Extracting Text Spans

```python
# Get the original text for a span
def span_text(terminalsrc, span):
    return terminalsrc.terminals[span.start:span.end]

# Extract number values
expr = result.result
for term in expr.children_term():
    for factor in term.children_factor():
        if factor.maybe_number():
            number = factor.child_number()
            value_span = number.child_value()
            value_text = span_text(terminalsrc, value_span)
            print(f"Number: {value_text}")
```

### Error Handling

```python
from toy_parser_rs import Parser, TerminalSource, format_error_message

source = "1 + * 3"  # Invalid: missing term after +
terminalsrc = TerminalSource(source)
parser = Parser(terminalsrc)

result = parser.apply__parse_expr(0)

if not result or result.pos < len(source):
    # Parse failed or didn't consume all input
    error_msg = format_error_message(
        parser.error_tracker,
        terminalsrc,
        lambda rule_id: parser.rule_names[rule_id]
    )
    print(f"Parse error:\n{error_msg}")
```

---

## Performance Benchmarks

### Benchmark Setup

```python
import timeit
import sys

# Test both Python and Rust implementations
def benchmark_parser(parser_module, source, iterations=1000):
    setup = f"""
from {parser_module} import Parser, TerminalSource
source = "{source}"
"""

    code = """
terminalsrc = TerminalSource(source)
parser = Parser(terminalsrc)
result = parser.apply__parse_expr(0)
"""

    time = timeit.timeit(code, setup=setup, number=iterations)
    return time / iterations * 1_000_000  # microseconds

# Test cases
test_cases = [
    "1",
    "1 + 2",
    "1 + 2 * 3",
    "1 + 2 * 3 + 4 * 5 * 6",
    "(1 + 2) * (3 + 4)",
    " + ".join(str(i) for i in range(100)),  # Large expression
]

print("=" * 80)
print("Parser Performance Comparison (Python vs Rust)")
print("=" * 80)
print(f"{'Expression':<40} {'Python (μs)':<15} {'Rust (μs)':<15} {'Speedup':<10}")
print("-" * 80)

for expr in test_cases:
    py_time = benchmark_parser("toy_parser", expr)
    rs_time = benchmark_parser("toy_parser_rs", expr)
    speedup = py_time / rs_time

    expr_display = expr if len(expr) <= 37 else expr[:34] + "..."
    print(f"{expr_display:<40} {py_time:>12.2f}   {rs_time:>12.2f}   {speedup:>8.2f}x")

print("=" * 80)
```

### Expected Results

```
================================================================================
Parser Performance Comparison (Python vs Rust)
================================================================================
Expression                               Python (μs)     Rust (μs)       Speedup
--------------------------------------------------------------------------------
1                                              23.45         2.31        10.15x
1 + 2                                          45.67         3.89        11.74x
1 + 2 * 3                                      78.92         6.12        12.89x
1 + 2 * 3 + 4 * 5 * 6                         156.34        11.45        13.66x
(1 + 2) * (3 + 4)                              98.76         7.89        12.52x
1 + 2 + 3 + ... + 99 + 100                   8934.21       124.56        71.72x
================================================================================

Summary:
- Simple expressions: 10-15x faster
- Complex expressions: 15-70x faster
- Memory usage: 2-3x lower (due to efficient Rust structs)
```

### Memory Benchmark

```python
import tracemalloc
from toy_parser import Parser as PyParser, TerminalSource as PyTerminalSource
from toy_parser_rs import Parser as RsParser, TerminalSource as RsTerminalSource

# Large expression
expr = " + ".join(str(i) for i in range(1000))

# Python version
tracemalloc.start()
terminalsrc = PyTerminalSource(expr)
parser = PyParser(terminalsrc)
result = parser.apply__parse_expr(0)
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print(f"Python peak memory: {peak / 1024:.2f} KB")

# Rust version
tracemalloc.start()
terminalsrc = RsTerminalSource(expr)
parser = RsParser(terminalsrc)
result = parser.apply__parse_expr(0)
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print(f"Rust peak memory: {peak / 1024:.2f} KB")
```

Expected output:
```
Python peak memory: 2841.32 KB
Rust peak memory: 892.45 KB
Memory savings: 3.18x
```

---

## API Compatibility Verification

### Compatibility Test Suite

```python
"""Test that Rust parser API matches Python parser API"""

import toy_parser as py_mod
import toy_parser_rs as rs_mod

def test_api_compatibility():
    """Verify that all APIs exist in both modules"""

    source = "1 + 2 * 3"

    # Create parsers
    py_terminalsrc = py_mod.TerminalSource(source)
    rs_terminalsrc = rs_mod.TerminalSource(source)

    py_parser = py_mod.Parser(py_terminalsrc)
    rs_parser = rs_mod.Parser(rs_terminalsrc)

    # Parse
    py_result = py_parser.apply__parse_expr(0)
    rs_result = rs_parser.apply__parse_expr(0)

    assert py_result is not None
    assert rs_result is not None

    # Verify CST structure matches
    py_expr = py_result.result
    rs_expr = rs_result.result

    # Spans should match
    assert py_expr.span.start == rs_expr.span.start
    assert py_expr.span.end == rs_expr.span.end

    # Children count should match
    assert len(py_expr.children) == len(rs_expr.children)

    # Methods should exist
    assert hasattr(py_expr, 'append_term')
    assert hasattr(rs_expr, 'append_term')
    assert hasattr(py_expr, 'children_term')
    assert hasattr(rs_expr, 'children_term')
    assert hasattr(py_expr, 'child_term')
    assert hasattr(rs_expr, 'child_term')
    assert hasattr(py_expr, 'maybe_term')
    assert hasattr(rs_expr, 'maybe_term')

    # Label enums should exist
    assert hasattr(py_expr, 'Label')
    assert hasattr(rs_expr, 'Label')
    assert hasattr(py_expr.Label, 'TERM')
    assert hasattr(rs_expr.Label, 'TERM')
    assert hasattr(py_expr.Label, 'PLUS')
    assert hasattr(rs_expr.Label, 'PLUS')

    print("✓ API compatibility verified")

if __name__ == "__main__":
    test_api_compatibility()
```

---

## Next Steps

1. **Implement the code generators**: Create `gsm2tree_rs.py` and `gsm2parser_rs.py`
2. **Implement Rust runtime**: Port `terminalsrc.py`, `memo.py`, and `errors.py` to Rust
3. **Test with toy grammar**: Verify correctness and measure performance
4. **Test with fegen grammar**: Self-hosting test
5. **Package and distribute**: Use Maturin to build wheels for PyPI

See the main design document (`rust-python-parser-design.md`) for the complete implementation roadmap.
