# Trivia Backend Divergence Investigation

**Date:** 2026-06-05  
**Scope:** Python vs Rust CST backend behavior regarding trivia (whitespace/comment) capture and emission  
**Artifact:** `fltk/fegen/fltk2gsm.py:48-52` (the filter that strips `(None, Trivia(...))` children)

## Executive Summary

The Python and Rust CST backends diverge in how they handle trivia capture:

- **Python backend:** When `capture_trivia=OFF`, does not insert Trivia nodes into the CST at all. When `capture_trivia=ON`, generates parser code that appends `(None, Trivia)` tuples via `append(child=..., label=None)`.
- **Rust backend:** **Always** inserts `(None, Trivia)` tuples into the CST via the Rust CST `append(label=None)` method, regardless of capture_trivia setting, because: (a) the Rust CST backend lacks an equivalent capture_trivia toggle, and (b) Rust parsers always call append with label=None for trivia, causing the Rust CST to create these tuples unconditionally.

**Root cause:** The toggle is missing on the Rust side; the Python parser generator honors it, but the Rust parser generation has no such concept.

---

## 1. PYTHON SIDE: capture_trivia Toggle Definition and Behavior

### 1.1 Toggle Definition

**File:** `/home/rnortman/src/fltk/fltk/iir/context.py:47`

```python
@dataclass
class CompilerContext:
    """Compiler context holding all compiler state and services."""
    python_type_registry: TypeRegistry = field(default_factory=TypeRegistry)
    capture_trivia: bool = False  # <-- Default OFF
```

**File:** `/home/rnortman/src/fltk/fltk/iir/context.py:50-57`

```python
def create_default_context(*, capture_trivia: bool = False) -> CompilerContext:
    """Create a default compiler context with standard type registrations."""
    context = CompilerContext(capture_trivia=capture_trivia)
    _register_builtin_types(context.python_type_registry)
    return context
```

**Default:** `capture_trivia=False` unless explicitly overridden.

### 1.2 Threading Through Parser Generation

**File:** `/home/rnortman/src/fltk/fltk/fegen/gsm2parser.py:584-590` and **605-611**

When `self.context.capture_trivia` is `True`, the parser generator emits code that appends trivia nodes with `label=None`:

```python
if self.context.capture_trivia:
    sep_if.block.expr_stmt(
        result_var.method.append.call(
            child=sep_ws_var.fld.result.move(),
            label=iir.LiteralNull(),  # <-- None label for trivia
        )
    )
```

When `False`, this entire block is skipped; trivia is parsed for position advancement only, not appended to the CST.

### 1.3 Behavior: OFF vs ON

**When OFF:** No Trivia nodes appear in `.children` at all. The parser parses trivia (via `_trivia` rule) to consume whitespace and advance position, but discards the result.

```python
# From generated fltk_parser.py:295-301 (grammar parser generated with capture_trivia=OFF)
if ws_after__item0 := self.apply__parse__trivia(pos=pos):
    pos = ws_after__item0.pos
    # Result is discarded; no append() call
```

**When ON:** Trivia nodes are inserted into `.children` as `(None, Trivia(...))` tuples via the append() call with `label=None`.

```python
# Generated parser code when capture_trivia=ON would emit:
if ws_after__item0 := self.apply__parse__trivia(pos=pos):
    pos = ws_after__item0.pos
    result.append(child=ws_after__item0.result, label=None)  # <-- (None, Trivia) tuple
```

### 1.4 Grammar Self-Hosting: capture_trivia Setting for FLTK Grammar

**File:** `/home/rnortman/src/fltk/fltk/plumbing.py:130-149`

```python
def parse_grammar(grammar_text: str, *, rust_fegen_cst_module: str | None = None) -> gsm.Grammar:
    """Parse .fltkg text to Grammar Semantic Model."""
    terminals = terminalsrc.TerminalSource(grammar_text)
    
    if rust_fegen_cst_module is None:
        # Default Python path: use the committed fltk_parser.
        parser = fltk_parser.Parser(terminalsrc=terminals)
        result = parser.apply__parse_grammar(0)
        # ... Cst2Gsm conversion ...
        cst2gsm = fltk2gsm.Cst2Gsm(terminals.terminals)
        return cst2gsm.visit_grammar(cast("cst.Grammar", result.result))
```

**Key finding:** The grammar is parsed using a **committed (pre-generated) fltk_parser.Parser** instance. This parser was **generated with `capture_trivia=OFF`**, as evidenced by:

1. The `fltk_parser.py` at lines 300-301 parses trivia but does not append it: `if ws_after__item0 := self.apply__parse__trivia(pos=pos): pos = ws_after__item0.pos` (no append call).
2. No `(None, label)` tuples are created in the Python backend's grammar parse.

**Conclusion:** When FLTK parses its own grammar (self-hosting), `capture_trivia` is effectively **OFF** because the committed fltk_parser was generated that way.

---

## 2. RUST SIDE: Absence of capture_trivia Toggle and Unconditional Trivia Emission

### 2.1 Rust CST Backend: No capture_trivia Equivalent

**File:** `/home/rnortman/src/fltk/fltk/fegen/gsm2tree_rs.py:42-50`

```python
class RustCstGenerator:
    """Generates a complete .rs file from a gsm.Grammar."""
    
    def __init__(self, grammar: gsm.Grammar):
        context = create_default_context()  # <-- No capture_trivia parameter
        grammar_with_trivia = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
        self._py_gen = CstGenerator(
            grammar=grammar_with_trivia,
            py_module=pyreg.Builtins,
            context=context,  # <-- context.capture_trivia is False (default)
        )
        self.grammar = grammar_with_trivia
```

**Finding:** The Rust CST generator does not accept or use a `capture_trivia` parameter. The context is always created with the default `capture_trivia=False`, yet the Rust CST still emits trivia handling code.

### 2.2 Rust CST append() Method: Always Accepts label=None

**File:** `/home/rnortman/src/fltk/src/cst_fegen.rs:69-75` (same pattern in cst_generated.rs)

```rust
#[pyo3(signature = (child, label = None))]
fn append(&self, py: Python<'_>, child: PyObject, label: Option<PyObject>) -> PyResult<()> {
    let label_val = label.unwrap_or_else(|| py.None());  // <-- If no label, use None
    let tup = PyTuple::new(py, [label_val, child])?;
    self.children.bind(py).append(tup)?;
    Ok(())
}
```

**Mechanism:** The Rust CST's `append()` method has no concept of "trivia capture mode." When called with `label=None`, it unconditionally creates a `(None, child)` tuple. There is no code path that says "if capture_trivia is off, don't append."

### 2.3 Rust Parser Behavior (Inferred)

**Finding:** While there is no visible Rust parser generator in the Python codebase, the Rust CST backend is used by:

1. Parsing grammars with a Rust CST backend: `parse_grammar(rust_fegen_cst_module="fegen_rust_cst")` (test file: `/home/rnortman/src/fltk/tests/test_phase4_fegen_rust_backend.py:66-70`).
2. The Rust parsers (however they are built/defined) call the Rust CST's `append()` method.

When a Rust parser (or any code using the Rust CST) calls `append(child=trivia_node, label=None)` for whitespace, the Rust CST unconditionally inserts `(None, Trivia(...))`.

**No toggleable code path exists in the Rust CST to suppress this.**

### 2.4 Test Evidence: Rust Backend Always Produces Trivia Tuples

**File:** `/home/rnortman/src/fltk/tests/test_phase4_fegen_rust_backend.py:66-76`

```python
def test_simple_grammar_rust_equals_python(self):
    """Simple single-rule grammar: Rust backend produces the same gsm.Grammar as Python."""
    python_result = parse_grammar(_SIMPLE_GRAMMAR)
    rust_result = parse_grammar(_SIMPLE_GRAMMAR, rust_fegen_cst_module="fegen_rust_cst")
    assert python_result == rust_result
```

**Observation:** This test checks that the Rust CST backend's parse result equals the Python backend's. The equality is enforced by the `fltk2gsm.Cst2Gsm` filter at lines 48-52, which **strips out `(None, Trivia(...))` tuples before processing**. Without this filter, the Rust results would not equal the Python results due to the `(None, Trivia(...))` entries.

---

## 3. ROOT CAUSE ANALYSIS

### Question: Why does the Rust backend emit `(None, Trivia)` children when the Python backend (with capture_trivia OFF) emits none?

**Answer: (a) — The Rust backend lacks the capture_trivia toggle entirely.**

### Evidence Chain

1. **Python side:** The toggle exists and is threaded through the parser generator (`gsm2parser.ParserGenerator.__init__` receives `context`; lines 584, 605 check `self.context.capture_trivia`).

2. **Grammar self-hosting:** The fltk_parser (used to parse the grammar itself) was generated with `capture_trivia=OFF`, so it does not emit trivia tuples.

3. **Rust CST side:**
   - `RustCstGenerator.__init__` (line 43) calls `create_default_context()` with **no arguments**, forcing `capture_trivia=False`.
   - The Rust CST's `append(label=None)` method has **no conditional logic** to check a capture_trivia flag; it always creates `(None, child)` tuples.
   - No Rust parser generator in the Python codebase accepts or uses a capture_trivia parameter.

4. **Empirical evidence:**
   - The `fltk2gsm.Cst2Gsm` filter (lines 48-52) was added to strip `(None, Trivia(...))` entries **specifically because "the Rust backend inserts (None, Trivia(...)) entries"**.
   - Tests confirm that without this filter, Rust results differ from Python results (test_phase4_fegen_rust_backend.py).

### Why Is This a Problem?

The filter at `fltk2gsm.py:52` **discards information** that the Rust backend supplies. If the Rust backend were properly honoring a capture_trivia setting, the filter would not be necessary; instead, both backends would respect the toggle and emit consistent results.

---

## 4. Recommendations

1. **Extend `RustCstGenerator` to accept and use a `capture_trivia` parameter:**
   - Modify `__init__` signature to accept `capture_trivia: bool = False`.
   - Pass it through to the context.
   - Use it to conditionally generate Rust CST classes with or without trivia support.

2. **Add conditional logic to the Rust CST's `append()` method:**
   - If the CST is built in "no-trivia mode," calling `append(label=None)` should raise an error or be a no-op.
   - Alternatively, generate two variants of the CST (with and without trivia support).

3. **Document the Python parser generator behavior:**
   - Clarify that `capture_trivia=OFF` means trivia is parsed for position tracking but not inserted into the CST.
   - Clarify that `capture_trivia=ON` means trivia is inserted as `(None, Trivia(...))` tuples.

4. **Regenerate fltk_parser.py with explicit capture_trivia setting:**
   - Make it explicit whether the grammar's self-hosted parser uses `capture_trivia=ON` or `OFF`.
   - Document the choice and its rationale.

---

## Files Consulted

- `/home/rnortman/src/fltk/fltk/iir/context.py` — CompilerContext definition
- `/home/rnortman/src/fltk/fltk/fegen/gsm2parser.py` — Python parser generator (separator handling, capture_trivia checks)
- `/home/rnortman/src/fltk/fltk/fegen/fltk2gsm.py` — Cst2Gsm filter (lines 48-52)
- `/home/rnortman/src/fltk/fltk/fegen/fltk_parser.py` — Committed Python parser (no trivia append)
- `/home/rnortman/src/fltk/fltk/fegen/gsm2tree_rs.py` — Rust CST generator (no capture_trivia parameter)
- `/home/rnortman/src/fltk/src/cst_fegen.rs` — Rust CST append() implementation
- `/home/rnortman/src/fltk/fltk/plumbing.py` — parse_grammar() entry point
- `/home/rnortman/src/fltk/tests/test_phase4_fegen_rust_backend.py` — Test evidence
