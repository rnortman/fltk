# FLTK Rust Parser - Implementation Guide

This document provides detailed technical guidance for implementing the Rust parser generator with Python bindings.

## Table of Contents

1. [Code Generator Architecture](#code-generator-architecture)
2. [Runtime Implementation Details](#runtime-implementation-details)
3. [PyO3 Integration Patterns](#pyo3-integration-patterns)
4. [Testing Strategy](#testing-strategy)
5. [Performance Optimization Techniques](#performance-optimization-techniques)
6. [Deployment and Distribution](#deployment-and-distribution)
7. [Maintenance and Evolution](#maintenance-and-evolution)

---

## Code Generator Architecture

### Generator Module Structure

```
fltk/fegen/
├── gsm.py                    # Grammar Semantic Model (unchanged)
├── gsm2tree_rs.py           # NEW: Generate Rust CST structs
├── gsm2parser_rs.py         # NEW: Generate Rust parser
├── rs_codegen/              # NEW: Rust code generation utilities
│   ├── __init__.py
│   ├── struct_gen.py        # Struct/enum generation
│   ├── impl_gen.py          # Implementation block generation
│   ├── pyo3_gen.py          # PyO3 attribute generation
│   └── formatting.py        # Code formatting utilities
└── rsrt/                    # NEW: Rust runtime templates
    ├── packrat.rs
    ├── terminalsrc.rs
    ├── errors.rs
    └── lib_template.rs
```

### gsm2tree_rs.py Implementation

```python
"""Generate Rust CST node structs from Grammar Semantic Model"""

from dataclasses import dataclass
from typing import List, Set
from fltk.fegen.gsm import Grammar, Rule, Item, Term, Quantifier
from fltk.fegen.rs_codegen import (
    RustStruct, RustEnum, RustImpl, RustAttribute,
    format_rust_code
)

@dataclass
class RustCSTSpec:
    """Generated Rust CST code specification"""
    source_code: str
    node_types: List[str]
    imports: List[str]

def generate_rust_cst(grammar: Grammar, capture_trivia: bool = False) -> RustCSTSpec:
    """
    Generate Rust CST node definitions from grammar.

    Args:
        grammar: Parsed grammar
        capture_trivia: Whether to include trivia nodes in CST

    Returns:
        RustCSTSpec with generated code
    """
    imports = [
        "use pyo3::prelude::*;",
        "use crate::runtime::{Span, UnknownSpan};",
    ]

    nodes = []
    node_types = []

    for rule in grammar.rules:
        # Skip trivia rules if not capturing
        if not capture_trivia and is_trivia_rule(grammar, rule):
            continue

        # Generate node struct
        node = generate_node_struct(grammar, rule, capture_trivia)
        nodes.append(node)
        node_types.append(rule.name.title())

    source_code = format_rust_code(
        header_comment(grammar),
        "\n".join(imports),
        "\n\n".join(nodes)
    )

    return RustCSTSpec(
        source_code=source_code,
        node_types=node_types,
        imports=imports
    )

def generate_node_struct(grammar: Grammar, rule: Rule, capture_trivia: bool) -> str:
    """Generate a single CST node struct for a rule"""

    struct_name = rule.name.title()
    labels = collect_labels(rule)
    child_types = collect_child_types(grammar, rule)

    parts = []

    # 1. Generate Label enum if there are labels
    if labels:
        label_enum = generate_label_enum(struct_name, labels)
        parts.append(label_enum)

    # 2. Generate Child enum for type-safe internal storage
    child_enum = generate_child_enum(struct_name, child_types)
    parts.append(child_enum)

    # 3. Generate main struct
    struct_def = generate_struct_definition(struct_name, labels)
    parts.append(struct_def)

    # 4. Generate #[pymethods] impl block
    pymethods_impl = generate_pymethods_impl(struct_name, labels, child_types)
    parts.append(pymethods_impl)

    # 5. Generate Rust-only helper impl block
    helpers_impl = generate_helpers_impl(struct_name, labels, child_types)
    parts.append(helpers_impl)

    return "\n\n".join(parts)

def generate_label_enum(struct_name: str, labels: List[str]) -> str:
    """Generate the Label enum for a node"""
    variants = [label.upper() for label in labels]

    return f"""
#[pyclass]
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum {struct_name}Label {{
    {', '.join(variants)},
}}
"""

def generate_child_enum(struct_name: str, child_types: Set[str]) -> str:
    """Generate the Child enum for type-safe internal storage"""

    variants = []
    for child_type in sorted(child_types):
        if child_type == "Span":
            variants.append(f"    Span(Span)")
        else:
            variants.append(f"    {child_type}(Box<{child_type}>)")

    return f"""
#[derive(Clone)]
pub enum {struct_name}Child {{
{chr(10).join(variants)}
}}
"""

def generate_struct_definition(struct_name: str, labels: List[str]) -> str:
    """Generate the main struct definition"""

    label_type = f"{struct_name}Label" if labels else "PhantomLabel"
    child_type = f"{struct_name}Child"

    return f"""
#[pyclass]
#[derive(Clone)]
pub struct {struct_name} {{
    #[pyo3(get, set)]
    pub span: Span,

    children_internal: Vec<(Option<{label_type}>, {child_type})>,
}}
"""

def generate_pymethods_impl(
    struct_name: str,
    labels: List[str],
    child_types: Set[str]
) -> str:
    """Generate the #[pymethods] implementation block"""

    methods = []

    # Constructor
    methods.append(f"""
    #[new]
    fn new(span: Option<Span>) -> Self {{
        {struct_name} {{
            span: span.unwrap_or(UnknownSpan),
            children_internal: Vec::new(),
        }}
    }}
""")

    # children getter
    methods.append(generate_children_getter(struct_name, labels))

    # Generic append/extend/child methods
    methods.append(generate_generic_append(struct_name, labels, child_types))
    methods.append(generate_generic_extend(struct_name, labels))
    methods.append(generate_generic_child(struct_name, labels))

    # Label-specific methods for each label
    for label in labels:
        # Determine the type for this label
        label_child_type = infer_label_type(label, child_types)

        methods.append(generate_append_label(struct_name, label, label_child_type))
        methods.append(generate_extend_label(struct_name, label, label_child_type))
        methods.append(generate_children_label(struct_name, label, label_child_type))
        methods.append(generate_child_label(struct_name, label, label_child_type))
        methods.append(generate_maybe_label(struct_name, label, label_child_type))

    impl_block = f"""
#[pymethods]
impl {struct_name} {{
{chr(10).join(methods)}
}}
"""
    return impl_block

def generate_children_getter(struct_name: str, labels: List[str]) -> str:
    """Generate the children getter that converts to Python objects"""

    label_type = f"{struct_name}Label" if labels else "None"

    return f"""
    #[getter]
    fn children(&self, py: Python) -> PyResult<Vec<(Option<{label_type}>, PyObject)>> {{
        self.children_internal
            .iter()
            .map(|(label, child)| {{
                let py_child = match child {{
                    {struct_name}Child::Span(s) => Py::new(py, *s)?.into_py(py),
                    {struct_name}Child::Term(t) => Py::new(py, t.as_ref().clone())?.into_py(py),
                    {struct_name}Child::Factor(f) => Py::new(py, f.as_ref().clone())?.into_py(py),
                    // ... other variants
                }};
                Ok((label.clone(), py_child))
            }})
            .collect()
    }}
"""

def generate_append_label(struct_name: str, label: str, child_type: str) -> str:
    """Generate append_{label} method"""

    label_upper = label.upper()
    label_lower = label.lower()

    if child_type == "Span":
        return f"""
    fn append_{label_lower}(&mut self, child: Span) {{
        self.children_internal.push((
            Some({struct_name}Label::{label_upper}),
            {struct_name}Child::Span(child)
        ));
    }}
"""
    else:
        return f"""
    fn append_{label_lower}(&mut self, child: {child_type}) {{
        self.children_internal.push((
            Some({struct_name}Label::{label_upper}),
            {struct_name}Child::{child_type}(Box::new(child))
        ));
    }}
"""

def generate_children_label(struct_name: str, label: str, child_type: str) -> str:
    """Generate children_{label} iterator method"""

    label_upper = label.upper()
    label_lower = label.lower()

    if child_type == "Span":
        return f"""
    fn children_{label_lower}(&self) -> Vec<Span> {{
        self.children_internal
            .iter()
            .filter_map(|(lbl, child)| {{
                if matches!(lbl, Some({struct_name}Label::{label_upper})) {{
                    if let {struct_name}Child::Span(s) = child {{
                        Some(*s)
                    }} else {{
                        None
                    }}
                }} else {{
                    None
                }}
            }})
            .collect()
    }}
"""
    else:
        return f"""
    fn children_{label_lower}(&self) -> Vec<{child_type}> {{
        self.children_internal
            .iter()
            .filter_map(|(lbl, child)| {{
                if matches!(lbl, Some({struct_name}Label::{label_upper})) {{
                    if let {struct_name}Child::{child_type}(t) = child {{
                        Some(t.as_ref().clone())
                    }} else {{
                        None
                    }}
                }} else {{
                    None
                }}
            }})
            .collect()
    }}
"""

def generate_child_label(struct_name: str, label: str, child_type: str) -> str:
    """Generate child_{label} method (exactly one)"""

    label_lower = label.lower()

    return f"""
    fn child_{label_lower}(&self) -> PyResult<{child_type}> {{
        let children = self.children_{label_lower}();
        if children.len() != 1 {{
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Expected one {label_lower} child but have {{}}", children.len())
            ));
        }}
        Ok(children[0].clone())
    }}
"""

def generate_maybe_label(struct_name: str, label: str, child_type: str) -> str:
    """Generate maybe_{label} method (at most one)"""

    label_lower = label.lower()

    return f"""
    fn maybe_{label_lower}(&self) -> PyResult<Option<{child_type}>> {{
        let children = self.children_{label_lower}();
        if children.len() > 1 {{
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Expected at most one {label_lower} child but have {{}}", children.len())
            ));
        }}
        Ok(children.first().cloned())
    }}
"""

def collect_labels(rule: Rule) -> List[str]:
    """Collect all labels used in a rule"""
    labels = set()

    for alternative in rule.alternatives:
        for item in alternative.items:
            if item.label:
                labels.add(item.label)

    return sorted(labels)

def collect_child_types(grammar: Grammar, rule: Rule) -> Set[str]:
    """
    Collect all possible child types for a rule.

    A child can be:
    - A Span (for literals and regexes)
    - Another CST node type (for identifiers)
    - Trivia nodes (if capturing trivia)
    """
    child_types = set()

    for alternative in rule.alternatives:
        for item in alternative.items:
            if isinstance(item.term, Identifier):
                # Reference to another rule
                child_types.add(item.term.name.title())
            elif isinstance(item.term, (Literal, Regex)):
                # Terminals become Spans
                child_types.add("Span")
            elif isinstance(item.term, SubExpr):
                # Sub-expression: need to analyze recursively
                # For now, assume it can produce any child type from that sub-expression
                pass  # TODO: implement sub-expression analysis

    # Always add Trivia if it exists in the grammar
    if has_trivia(grammar):
        child_types.add("Trivia")

    return child_types

def infer_label_type(label: str, child_types: Set[str]) -> str:
    """
    Infer the type associated with a label.

    Heuristics:
    - If label matches a node type name, use that type
    - If label is like "value", "content", etc., it's likely a Span
    - Otherwise, try to infer from context
    """
    label_title = label.title()

    if label_title in child_types:
        return label_title

    # Common terminal labels
    terminal_labels = {"value", "content", "name", "text", "literal"}
    if label.lower() in terminal_labels:
        return "Span"

    # Default: try to find a matching type
    for child_type in child_types:
        if child_type.lower() == label.lower():
            return child_type

    # Last resort: Span
    return "Span"

# ... more helper functions ...
```

### gsm2parser_rs.py Implementation

```python
"""Generate Rust parser from Grammar Semantic Model"""

from dataclasses import dataclass
from typing import List
from fltk.fegen.gsm import Grammar, Rule, Alternative, Item, Term, Quantifier, Separator

@dataclass
class RustParserSpec:
    """Generated Rust parser specification"""
    source_code: str
    rule_names: List[str]

def generate_rust_parser(grammar: Grammar, capture_trivia: bool = False) -> RustParserSpec:
    """
    Generate Rust parser implementation from grammar.

    The generated parser follows the same structure as the Python parser:
    - apply__parse_{rule}: Memoized entry point
    - parse_{rule}: Main rule parser
    - parse_{rule}__alt{n}: Alternative parsers
    - parse_{rule}__alt{n}__item{m}: Item parsers
    """

    imports = [
        "use pyo3::prelude::*;",
        "use std::cell::RefCell;",
        "use std::collections::HashMap;",
        "use crate::cst::*;",
        "use crate::runtime::*;",
    ]

    rule_names = [rule.name for rule in grammar.rules]

    # Generate parser state struct
    state_struct = generate_parser_state_struct(grammar)

    # Generate main parser struct
    parser_struct = generate_parser_struct(grammar)

    # Generate #[pymethods] impl block
    pymethods_impl = generate_parser_pymethods(grammar, capture_trivia)

    # Generate internal impl block
    internal_impl = generate_parser_internal(grammar, capture_trivia)

    source_code = format_rust_code(
        header_comment(grammar),
        "\n".join(imports),
        state_struct,
        parser_struct,
        pymethods_impl,
        internal_impl
    )

    return RustParserSpec(
        source_code=source_code,
        rule_names=rule_names
    )

def generate_parser_state_struct(grammar: Grammar) -> str:
    """Generate the ParserState struct that holds mutable state"""

    cache_fields = []
    for i, rule in enumerate(grammar.rules):
        node_type = rule.name.title()
        cache_fields.append(
            f"    cache_{rule.name}: HashMap<usize, MemoEntry<{node_type}>>,"
        )

    return f"""
struct ParserState {{
    packrat: Packrat,
    error_tracker: ErrorTracker,

    // Per-rule memoization caches
{chr(10).join(cache_fields)}
}}

impl ParserState {{
    fn new() -> Self {{
        ParserState {{
            packrat: Packrat::new(),
            error_tracker: ErrorTracker::new(),
{chr(10).join(f'            cache_{rule.name}: HashMap::new(),' for rule in grammar.rules)}
        }}
    }}
}}
"""

def generate_parser_struct(grammar: Grammar) -> str:
    """Generate the main Parser struct"""

    return f"""
#[pyclass]
pub struct Parser {{
    terminalsrc: Py<TerminalSource>,
    rule_names: Vec<String>,
    state: RefCell<ParserState>,
}}
"""

def generate_parser_pymethods(grammar: Grammar, capture_trivia: bool) -> str:
    """Generate the #[pymethods] implementation block"""

    methods = []

    # Constructor
    rule_name_list = ", ".join(f'"{rule.name}".to_string()' for rule in grammar.rules)
    methods.append(f"""
    #[new]
    fn new(terminalsrc: Py<TerminalSource>) -> Self {{
        Parser {{
            terminalsrc,
            rule_names: vec![{rule_name_list}],
            state: RefCell::new(ParserState::new()),
        }}
    }}
""")

    # consume_literal and consume_regex
    methods.append(generate_consume_literal())
    methods.append(generate_consume_regex())

    # For each rule, generate apply__parse_{rule} method
    for i, rule in enumerate(grammar.rules):
        methods.append(generate_apply_parse_rule(i, rule))

    impl_block = f"""
#[pymethods]
impl Parser {{
{chr(10).join(methods)}
}}
"""
    return impl_block

def generate_consume_literal() -> str:
    """Generate consume_literal method"""
    return """
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
"""

def generate_consume_regex() -> str:
    """Generate consume_regex method"""
    return """
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
"""

def generate_apply_parse_rule(rule_id: int, rule: Rule) -> str:
    """Generate apply__parse_{rule} method"""

    node_type = rule.name.title()

    return f"""
    fn apply__parse_{rule.name}(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<{node_type}>>>
    {{
        let mut state = self.state.borrow_mut();
        state.packrat.apply(
            |pos| self.parse_{rule.name}_impl(py, pos),
            {rule_id},
            &mut state.cache_{rule.name},
            pos,
        )
    }}
"""

def generate_parser_internal(grammar: Grammar, capture_trivia: bool) -> str:
    """Generate internal implementation methods"""

    methods = []

    for rule in grammar.rules:
        # parse_{rule}
        methods.append(generate_parse_rule(grammar, rule, capture_trivia))

        # parse_{rule}__alt{n} for each alternative
        for i, alternative in enumerate(rule.alternatives):
            methods.append(
                generate_parse_alternative(grammar, rule, i, alternative, capture_trivia)
            )

            # parse_{rule}__alt{n}__item{m} for each item
            for j, item in enumerate(alternative.items):
                methods.append(
                    generate_parse_item(grammar, rule, i, j, item, capture_trivia)
                )

    impl_block = f"""
impl Parser {{
    // Wrapper methods called by packrat
{chr(10).join(f'    fn parse_{rule.name}_impl(&self, py: Python, pos: usize) -> PyResult<Option<ApplyResult<{rule.name.title()}>>> {{ self.parse_{rule.name}(py, pos) }}'
              for rule in grammar.rules)}

{chr(10).join(methods)}
}}
"""
    return impl_block

def generate_parse_rule(grammar: Grammar, rule: Rule, capture_trivia: bool) -> str:
    """Generate parse_{rule} method that tries all alternatives"""

    node_type = rule.name.title()
    alternatives = "\n        ".join(
        f"if let Some(alt{i}) = self.parse_{rule.name}__alt{i}(py, pos)? {{\n"
        f"            return Ok(Some(alt{i}));\n"
        f"        }}"
        for i in range(len(rule.alternatives))
    )

    return f"""
    fn parse_{rule.name}(&self, py: Python, pos: usize)
        -> PyResult<Option<ApplyResult<{node_type}>>>
    {{
        {alternatives}
        Ok(None)
    }}
"""

def generate_parse_alternative(
    grammar: Grammar,
    rule: Rule,
    alt_index: int,
    alternative: Alternative,
    capture_trivia: bool
) -> str:
    """Generate parse_{rule}__alt{n} method for one alternative"""

    node_type = rule.name.title()
    rule_name = rule.name
    alt_name = f"parse_{rule_name}__alt{alt_index}"

    # Generate code to parse each item
    item_parsers = []
    for i, item in enumerate(alternative.items):
        item_parser = generate_item_parsing_code(
            grammar, rule_name, alt_index, i, item, alternative, capture_trivia
        )
        item_parsers.append(item_parser)

    return f"""
    fn {alt_name}(&self, py: Python, mut pos: usize)
        -> PyResult<Option<ApplyResult<{node_type}>>>
    {{
        let start_pos = pos;
        let mut result = {node_type}::new(Some(Span::new(pos, usize::MAX)));

{chr(10).join(item_parsers)}

        result.span = Span::new(start_pos, pos);
        Ok(Some(ApplyResult {{ pos, result }}))
    }}
"""

def generate_item_parsing_code(
    grammar: Grammar,
    rule_name: str,
    alt_index: int,
    item_index: int,
    item: Item,
    alternative: Alternative,
    capture_trivia: bool
) -> str:
    """Generate code to parse a single item in an alternative"""

    item_name = f"parse_{rule_name}__alt{alt_index}__item{item_index}"

    # Check quantifier
    if isinstance(item.quantifier, Quantifier.REQUIRED):
        required = True
        multiple = False
    elif isinstance(item.quantifier, Quantifier.NOT_REQUIRED):
        required = False
        multiple = False
    elif isinstance(item.quantifier, Quantifier.ONE_OR_MORE):
        required = True
        multiple = True
    elif isinstance(item.quantifier, Quantifier.ZERO_OR_MORE):
        required = False
        multiple = True

    # Generate parsing code based on quantifier
    if multiple:
        # Loop: *, +
        loop_code = f"""
        // Item {item_index}: {item.label or 'unlabeled'} ({item.quantifier})
        while let Some(item_result) = self.{item_name}(py, pos)? {{
            pos = item_result.pos;
            // Handle disposition and label
            {generate_append_child_code(item, 'item_result.result')}
        }}
"""
        if required:
            # Check that we got at least one
            loop_code += f"""
        if pos == start_pos {{
            return Ok(None);  // No matches for +
        }}
"""
        return loop_code
    else:
        # Single: ?, no quantifier
        if required:
            return f"""
        // Item {item_index}: {item.label or 'unlabeled'} (required)
        if let Some(item{item_index}) = self.{item_name}(py, pos)? {{
            pos = item{item_index}.pos;
            {generate_append_child_code(item, f'item{item_index}.result')}
        }} else {{
            return Ok(None);
        }}

        // Separator after item{item_index}
        {generate_separator_code(alternative, item_index, capture_trivia)}
"""
        else:
            return f"""
        // Item {item_index}: {item.label or 'unlabeled'} (optional)
        if let Some(item{item_index}) = self.{item_name}(py, pos)? {{
            pos = item{item_index}.pos;
            {generate_append_child_code(item, f'item{item_index}.result')}

            // Separator after item{item_index}
            {generate_separator_code(alternative, item_index, capture_trivia)}
        }}
"""

def generate_append_child_code(item: Item, value_expr: str) -> str:
    """Generate code to append a child based on disposition and label"""

    if item.disposition == Disposition.SUPPRESS:
        # Suppressed - don't add to result
        return "// Suppressed"

    if item.disposition == Disposition.INLINE:
        # Inline - extend children from child node
        return f"result.extend_internal({value_expr}.children_internal);"

    if item.label:
        # Labeled - use append_{label} method
        label_lower = item.label.lower()
        return f"result.append_{label_lower}({value_expr});"
    else:
        # Unlabeled - use generic append
        return f"result.append_internal(None, {value_expr});"

def generate_separator_code(alternative: Alternative, item_index: int, capture_trivia: bool) -> str:
    """Generate code to handle separator after an item"""

    if item_index >= len(alternative.sep_after):
        return ""

    separator = alternative.sep_after[item_index]

    if separator == Separator.NO_WS:
        # No whitespace allowed
        return ""
    elif separator in (Separator.WS_ALLOWED, Separator.WS_REQUIRED):
        # Parse trivia if present
        if capture_trivia:
            return """
        if let Some(ws) = self.apply__parse__trivia(py, pos)? {
            pos = ws.pos;
            result.append_trivia(ws.result);
        }
"""
        else:
            return """
        if let Some(ws) = self.apply__parse__trivia(py, pos)? {
            pos = ws.pos;
        }
"""

    return ""

# ... more helper functions ...
```

---

## Runtime Implementation Details

### Packrat Memoization in Rust

```rust
//! Packrat memoization with left-recursion support
//! Ported from fltk/fegen/pyrt/memo.py

use std::collections::{HashMap, HashSet};
use pyo3::prelude::*;

pub struct RecursionInfo {
    pub rule_id: usize,
    pub involved: HashSet<usize>,
    pub eval_set: HashSet<usize>,
}

pub enum MemoResult<T> {
    Poison(Option<RecursionInfo>),
    Success(T),
    Failure,
}

pub struct MemoEntry<T> {
    pub result: MemoResult<T>,
    pub final_pos: usize,
}

#[derive(Clone, Debug)]
pub struct ApplyResult<T> {
    pub pos: usize,
    pub result: T,
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
    ) -> PyResult<Option<ApplyResult<T>>>
    where
        F: FnOnce(usize) -> PyResult<Option<ApplyResult<T>>>,
        T: Clone,
    {
        // Implementation follows Python algorithm exactly
        // See fltk/fegen/pyrt/memo.py:Packrat.apply for reference

        // Step 1: Recall (check cache with seed-growing support)
        if let Some(memo) = self.recall(rule_callable, rule_id, rule_cache, pos)? {
            match &memo.result {
                MemoResult::Poison(poison) => {
                    // Hit recursion
                    self.setup_recursion(rule_id, poison);
                    return Ok(None);
                }
                MemoResult::Success(result) => {
                    return Ok(Some(ApplyResult {
                        pos: memo.final_pos,
                        result: result.clone(),
                    }));
                }
                MemoResult::Failure => {
                    return Ok(None);
                }
            }
        }

        // Step 2: Poison cache and invoke rule
        let poison = MemoResult::Poison(None);
        let mut memo = MemoEntry {
            result: poison,
            final_pos: pos,
        };
        rule_cache.insert(pos, memo.clone());

        self.invocation_stack.push(rule_id);
        let call_result = rule_callable(pos)?;
        self.invocation_stack.pop();

        // Step 3: Process result
        let (new_pos, result) = match call_result {
            Some(ar) => (ar.pos, Some(ar.result)),
            None => (pos, None),
        };

        memo.final_pos = new_pos;

        // Check if poison was updated (recursion detected)
        if let MemoResult::Poison(Some(recursion_info)) = &memo.result {
            // Recursion occurred
            if recursion_info.rule_id == rule_id {
                // We are the head/tail of the cycle
                memo.result = if let Some(r) = result {
                    MemoResult::Success(r)
                } else {
                    MemoResult::Failure
                };

                if memo.result.is_success() {
                    // Grow seed
                    self.invocation_stack.push(rule_id);
                    let grow_result = self.grow_seed(rule_callable, pos, &mut memo, recursion_info.clone())?;
                    self.invocation_stack.pop();
                    return Ok(grow_result);
                } else {
                    return Ok(None);
                }
            }
        }

        // Normal case
        memo.result = if let Some(r) = result {
            MemoResult::Success(r)
        } else {
            MemoResult::Failure
        };

        rule_cache.insert(pos, memo.clone());

        match &memo.result {
            MemoResult::Success(r) => Ok(Some(ApplyResult {
                pos: memo.final_pos,
                result: r.clone(),
            })),
            _ => Ok(None),
        }
    }

    fn recall<T, F>(
        &mut self,
        rule_callable: F,
        rule_id: usize,
        rule_cache: &HashMap<usize, MemoEntry<T>>,
        pos: usize,
    ) -> PyResult<Option<MemoEntry<T>>>
    where
        F: FnOnce(usize) -> PyResult<Option<ApplyResult<T>>>,
        T: Clone,
    {
        // Implementation of recall with seed-growing support
        // See Python version for details
        // ...
    }

    fn setup_recursion(&mut self, rule_id: usize, poison: &Option<RecursionInfo>) {
        // Implementation of recursion setup
        // See Python version for details
        // ...
    }

    fn grow_seed<T, F>(
        &mut self,
        rule_callable: F,
        pos: usize,
        memo: &mut MemoEntry<T>,
        recursion: RecursionInfo,
    ) -> PyResult<Option<ApplyResult<T>>>
    where
        F: Fn(usize) -> PyResult<Option<ApplyResult<T>>>,
        T: Clone,
    {
        // Implementation of seed growing
        // See Python version for details
        // ...
    }
}

impl<T> MemoResult<T> {
    fn is_success(&self) -> bool {
        matches!(self, MemoResult::Success(_))
    }
}
```

### TerminalSource in Rust

```rust
//! Terminal source management
//! Ported from fltk/fegen/pyrt/terminalsrc.py

use pyo3::prelude::*;
use regex::Regex;
use dashmap::DashMap;
use once_cell::sync::Lazy;
use std::sync::Arc;

// Global regex cache
static REGEX_CACHE: Lazy<DashMap<String, Regex>> =
    Lazy::new(DashMap::new);

#[pyclass]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
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

    fn __repr__(&self) -> String {
        format!("Span({}, {})", self.start, self.end)
    }
}

impl Span {
    pub fn unknown() -> Self {
        Span {
            start: usize::MAX,
            end: usize::MAX,
        }
    }
}

pub const UnknownSpan: Span = Span {
    start: usize::MAX,
    end: usize::MAX,
};

#[pyclass]
pub struct LineColPos {
    #[pyo3(get)]
    pub line: usize,
    #[pyo3(get)]
    pub col: usize,
    #[pyo3(get)]
    pub line_span: Span,
}

#[pyclass]
pub struct TerminalSource {
    #[pyo3(get)]
    pub terminals: String,

    terminals_len: usize,
    line_ends: Option<Vec<usize>>,
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
        }
    }

    fn consume_literal(&self, pos: usize, literal: &str) -> PyResult<Option<Span>> {
        let literal_len = literal.len();

        if pos + literal_len > self.terminals_len {
            return Ok(None);
        }

        // Fast byte-level comparison
        if &self.terminals[pos..pos + literal_len] == literal {
            Ok(Some(Span::new(pos, pos + literal_len)))
        } else {
            Ok(None)
        }
    }

    fn consume_regex(&mut self, pos: usize, regex_pattern: &str) -> PyResult<Option<Span>> {
        // Get or compile regex
        let regex = if let Some(re) = REGEX_CACHE.get(regex_pattern) {
            re.clone()
        } else {
            let re = Regex::new(regex_pattern)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid regex '{}': {}", regex_pattern, e)
                ))?;
            REGEX_CACHE.insert(regex_pattern.to_string(), re.clone());
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
        if pos > self.terminals.len() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("pos {} beyond end of terminals", pos)
            ));
        }

        let mut pos = pos;
        if pos == self.terminals.len() && pos > 0 {
            pos -= 1;
        }

        // Lazily compute line ends
        if self.line_ends.is_none() {
            let mut ends = Vec::new();
            for (idx, ch) in self.terminals.char_indices() {
                if ch == '\n' {
                    ends.push(idx);
                }
            }
            if ends.is_empty() || *ends.last().unwrap() != self.terminals.len() - 1 {
                ends.push(self.terminals.len().saturating_sub(1));
            }
            self.line_ends = Some(ends);
        }

        let line_ends = self.line_ends.as_ref().unwrap();

        // Binary search for line
        let idx = line_ends.binary_search(&pos).unwrap_or_else(|x| x);

        let (line, col, line_span) = if idx > 0 {
            let line_start = line_ends[idx - 1] + 1;
            let line_end = line_ends[idx];
            (
                idx,
                pos - line_start,
                Span::new(line_start, line_end)
            )
        } else {
            let line_end = line_ends[0];
            (
                0,
                pos,
                Span::new(0, line_end)
            )
        };

        Ok(LineColPos {
            line,
            col,
            line_span,
        })
    }
}
```

---

## PyO3 Integration Patterns

### Module Definition

```rust
//! PyO3 module entry point
//! File: src/lib.rs

use pyo3::prelude::*;

mod runtime;
mod cst;
mod parser;

use runtime::{Span, TerminalSource, LineColPos, ApplyResult};
use cst::*;
use parser::Parser;

#[pymodule]
fn toy_parser_rs(py: Python, m: &PyModule) -> PyResult<()> {
    // Runtime types
    m.add_class::<Span>()?;
    m.add_class::<TerminalSource>()?;
    m.add_class::<LineColPos>()?;

    // CST nodes
    m.add_class::<Expr>()?;
    m.add_class::<ExprLabel>()?;
    m.add_class::<Term>()?;
    m.add_class::<TermLabel>()?;
    m.add_class::<Factor>()?;
    m.add_class::<FactorLabel>()?;
    m.add_class::<Number>()?;
    m.add_class::<NumberLabel>()?;
    m.add_class::<Trivia>()?;
    m.add_class::<TriviaLabel>()?;

    // Parser
    m.add_class::<Parser>()?;

    // Module constants
    m.add("UnknownSpan", Span::unknown())?;

    Ok(())
}
```

### Error Handling Patterns

```rust
// Convert Rust errors to Python exceptions

// Pattern 1: Use ? with PyResult
fn parse_something(&self, py: Python) -> PyResult<Expr> {
    let result = self.some_operation()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Operation failed: {}", e)
        ))?;
    Ok(result)
}

// Pattern 2: Raise exceptions directly
fn validate(&self) -> PyResult<()> {
    if self.is_invalid() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Validation failed"
        ));
    }
    Ok(())
}

// Pattern 3: Handle Option
fn maybe_get(&self) -> PyResult<Option<Value>> {
    Ok(self.internal_get())
}
```

---

## Testing Strategy

### Unit Tests for Rust Runtime

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_span_creation() {
        let span = Span::new(0, 5);
        assert_eq!(span.start, 0);
        assert_eq!(span.end, 5);
    }

    #[test]
    fn test_terminalsrc_literal() {
        let src = TerminalSource::new("hello world".to_string());
        assert_eq!(src.consume_literal(0, "hello"), Ok(Some(Span::new(0, 5))));
        assert_eq!(src.consume_literal(6, "world"), Ok(Some(Span::new(6, 11))));
        assert_eq!(src.consume_literal(0, "goodbye"), Ok(None));
    }

    #[test]
    fn test_terminalsrc_regex() {
        let mut src = TerminalSource::new("123 abc".to_string());
        assert_eq!(src.consume_regex(0, r"\d+"), Ok(Some(Span::new(0, 3))));
        assert_eq!(src.consume_regex(4, r"[a-z]+"), Ok(Some(Span::new(4, 7))));
    }

    #[test]
    fn test_packrat_memoization() {
        // Test that memoization works correctly
        // ...
    }

    #[test]
    fn test_packrat_left_recursion() {
        // Test left-recursion handling
        // ...
    }
}
```

### Integration Tests - Python Side

```python
"""Integration tests for Rust parser"""

import pytest
from toy_parser_rs import Parser, TerminalSource, Span

def test_simple_parse():
    """Test parsing a simple expression"""
    src = TerminalSource("1 + 2")
    parser = Parser(src)
    result = parser.apply__parse_expr(0)

    assert result is not None
    assert result.pos == 5
    expr = result.result
    assert expr.span.start == 0
    assert expr.span.end == 5

def test_nested_parse():
    """Test parsing nested expressions"""
    src = TerminalSource("(1 + 2) * 3")
    parser = Parser(src)
    result = parser.apply__parse_expr(0)

    assert result is not None
    assert result.pos == 11

def test_parse_error():
    """Test that parse errors are handled correctly"""
    src = TerminalSource("1 + + 2")
    parser = Parser(src)
    result = parser.apply__parse_expr(0)

    # Should fail or not consume entire input
    assert result is None or result.pos < len(src.terminals)

@pytest.mark.parametrize("expr,expected_value", [
    ("1", 1),
    ("1 + 2", 3),
    ("2 * 3", 6),
    ("1 + 2 * 3", 7),
    ("(1 + 2) * 3", 9),
])
def test_evaluation(expr, expected_value):
    """Test that parsed expressions evaluate correctly"""
    src = TerminalSource(expr)
    parser = Parser(src)
    result = parser.apply__parse_expr(0)

    assert result is not None
    value = evaluate_expr(result.result)
    assert value == expected_value

def evaluate_expr(expr):
    """Evaluate an Expr CST node"""
    # Implement simple evaluation logic
    # ...
```

### Compatibility Tests

```python
"""Test API compatibility between Python and Rust parsers"""

import toy_parser as py_mod
import toy_parser_rs as rs_mod

TEST_CASES = [
    "1",
    "1 + 2",
    "1 + 2 * 3",
    "(1 + 2) * 3",
    "1 + 2 + 3 + 4",
]

def compare_spans(py_span, rs_span):
    """Compare Python and Rust spans"""
    assert py_span.start == rs_span.start
    assert py_span.end == rs_span.end

def compare_cst_nodes(py_node, rs_node):
    """Recursively compare Python and Rust CST nodes"""
    # Compare spans
    compare_spans(py_node.span, rs_node.span)

    # Compare children
    assert len(py_node.children) == len(rs_node.children)

    for (py_label, py_child), (rs_label, rs_child) in zip(py_node.children, rs_node.children):
        # Compare labels
        if py_label is None:
            assert rs_label is None
        else:
            assert py_label.name == rs_label.name

        # Compare child nodes recursively
        if isinstance(py_child, py_mod.Span):
            compare_spans(py_child, rs_child)
        else:
            compare_cst_nodes(py_child, rs_child)

@pytest.mark.parametrize("expr", TEST_CASES)
def test_cst_structure_matches(expr):
    """Test that Python and Rust parsers produce identical CST structures"""

    # Parse with Python
    py_src = py_mod.TerminalSource(expr)
    py_parser = py_mod.Parser(py_src)
    py_result = py_parser.apply__parse_expr(0)

    # Parse with Rust
    rs_src = rs_mod.TerminalSource(expr)
    rs_parser = rs_mod.Parser(rs_src)
    rs_result = rs_parser.apply__parse_expr(0)

    # Both should succeed
    assert py_result is not None
    assert rs_result is not None

    # Both should consume same amount
    assert py_result.pos == rs_result.pos

    # CST structures should match
    compare_cst_nodes(py_result.result, rs_result.result)
```

---

## Performance Optimization Techniques

### Profiling Rust Code

```toml
# Cargo.toml - Enable profiling
[profile.release]
debug = true  # Include debug symbols for profiling

[profile.bench]
debug = true
```

```bash
# Profile with perf
cargo build --release
perf record --call-graph=dwarf ./target/release/benchmark
perf report

# Profile with flamegraph
cargo install flamegraph
cargo flamegraph --bench parse_benchmark

# Profile with valgrind/cachegrind
valgrind --tool=cachegrind ./target/release/benchmark
```

### Benchmarking with Criterion

```rust
// benches/parse_benchmark.rs

use criterion::{black_box, criterion_group, criterion_main, Criterion};
use toy_parser_rs::{Parser, TerminalSource};

fn bench_simple_parse(c: &mut Criterion) {
    c.bench_function("parse 1 + 2", |b| {
        b.iter(|| {
            let src = TerminalSource::new(black_box("1 + 2".to_string()));
            let mut parser = Parser::new(src);
            parser.apply__parse_expr(0)
        })
    });
}

fn bench_complex_parse(c: &mut Criterion) {
    let expr = (0..100).map(|i| i.to_string()).collect::<Vec<_>>().join(" + ");

    c.bench_function("parse large expression", |b| {
        b.iter(|| {
            let src = TerminalSource::new(black_box(expr.clone()));
            let mut parser = Parser::new(src);
            parser.apply__parse_expr(0)
        })
    });
}

criterion_group!(benches, bench_simple_parse, bench_complex_parse);
criterion_main!(benches);
```

---

## Deployment and Distribution

### Building with Maturin

```bash
# Development build (debug)
maturin develop

# Release build
maturin build --release

# Build for multiple Python versions
maturin build --release --interpreter python3.10 python3.11 python3.12

# Build manylinux wheels (for PyPI)
docker run --rm -v $(pwd):/io \
  ghcr.io/pyo3/maturin \
  build --release --manylinux 2014
```

### PyPI Publishing

```toml
# pyproject.toml
[project]
name = "fltk-rust-parsers"
version = "0.1.0"
description = "Rust-accelerated parsers for FLTK"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
keywords = ["parser", "peg", "packrat", "rust"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Rust",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
```

```bash
# Publish to PyPI
maturin publish
```

---

## Maintenance and Evolution

### Keeping Rust and Python in Sync

1. **Shared test suite**: All tests should pass for both Python and Rust implementations
2. **API compatibility checks**: Automated tests verify API surface matches
3. **Version parity**: Rust parser version should track Python parser version
4. **Documentation**: Keep both implementations documented with cross-references

### Future Enhancements

1. **Incremental parsing**: Save parser state, re-parse only changed portions
2. **Parallel parsing**: Parse multiple files concurrently
3. **WASM target**: Compile to WebAssembly for browser-based parsing
4. **Tree-sitter compatibility**: Generate Tree-sitter grammars for editor integration
5. **LSP support**: Build Language Server Protocol support on top of parsers

---

## Conclusion

This implementation guide provides a roadmap for creating high-performance Rust parsers with Python-compatible APIs. The key principles are:

1. **Maintain API compatibility** - Rust parsers should be drop-in replacements
2. **Follow established patterns** - Port the proven Python algorithms to Rust
3. **Optimize carefully** - Profile before optimizing, focus on hot paths
4. **Test thoroughly** - Ensure correctness before pursuing performance

With this approach, FLTK can offer users a choice: pure Python parsers for simplicity and portability, or Rust-accelerated parsers for maximum performance.
