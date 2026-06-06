# Trivia Divergence Root Cause Analysis (v2)

**Date:** 2026-06-05  
**Scope:** Verify the architecture claim that Rust CST backend captures trivia "unconditionally" vs the PARSER's capture_trivia gate.  
**Finding:** The prior investigation was CORRECT in blaming the PARSER, but INCOMPLETE about *which* parser. The Rust path uses a **separately generated parser with capture_trivia=True**, while the Python path uses a **committed parser generated with capture_trivia=False**.

---

## 1. PARSER CODEGEN GATE: capture_trivia Controls Trivia Appends

**Claim:** The decision to append `(None, trivia)` is made by the PARSER, not the CST sink, controlled by `context.capture_trivia`.

**Evidence:** `/home/rnortman/src/fltk/fltk/fegen/gsm2parser.py:584-590` and `605-611`

```python
# Lines 584-590: BOTH inline trivia paths check capture_trivia
if self.context.capture_trivia:
    sep_if.block.expr_stmt(
        result_var.method.append.call(
            child=sep_ws_var.fld.result.move(),
            label=iir.LiteralNull(),  # <-- Generic path: ANY unlabeled child gets (None, child)
        )
    )
```

**Conclusion (1):** ✓ **CONFIRMED.** The parser generator **gates trivia appends on `capture_trivia`** (lines 584, 605). When False, trivia is parsed but discarded (no append call). When True, `append(child=trivia, label=None)` is emitted unconditionally. The `append(label=None)` path is NOT trivia-specific; it's the generic mechanism for any unlabeled child.

---

## 2. WHICH PARSER RUNS FOR THE RUST BACKEND?

**The Crux:** There are TWO DISTINCT parser paths:

### 2.1 **PYTHON Path** (default, no rust_fegen_cst_module)

**Code:** `/home/rnortman/src/fltk/fltk/plumbing.py:132-135`

```python
if rust_fegen_cst_module is None:
    # Default Python path: use the committed fltk_parser.
    parser = fltk_parser.Parser(terminalsrc=terminals)
    result = parser.apply__parse_grammar(0)
```

**Parser:** The **committed (pre-generated) `fltk_parser.Parser`** class at `/home/rnortman/src/fltk/fltk/fegen/fltk_parser.py`.

**Evidence that it was generated with `capture_trivia=False`:**

- `/home/rnortman/src/fltk/fltk/fegen/fltk_parser.py:301-302`:
  ```python
  if ws_after__item0 := self.apply__parse__trivia(pos=pos):
      pos = ws_after__item0.pos
      # <-- NO append() call; trivia parsed but discarded
  ```

### 2.2 **RUST Path** (rust_fegen_cst_module="fegen_rust_cst")

**Code:** `/home/rnortman/src/fltk/fltk/plumbing.py:158-162`

```python
_fegen_rust_parser_cache[rust_fegen_cst_module] = generate_parser(
    fegen_grammar, rust_cst_module=rust_fegen_cst_module
)
pr = _fegen_rust_parser_cache[rust_fegen_cst_module]
parser = pr.parser_class(terminalsrc=terminals)
```

**Parser:** A **freshly generated** parser class, created by `generate_parser(fegen_grammar, rust_cst_module=rust_fegen_cst_module)`.

**Critical Detail:** This call does NOT pass `capture_trivia`, so it defaults to **`capture_trivia=True`** (line 211):

- `/home/rnortman/src/fltk/fltk/plumbing.py:208-211`:
  ```python
  def generate_parser(
      grammar: gsm.Grammar,
      *,
      capture_trivia: bool = True,  # <-- DEFAULT: True
      rust_cst_module: str | None = None,
  ) -> ParserResult:
  ```

**Conclusion (2):** ✓ **CONFIRMED.** The Rust path generates a **separate Python parser** via `generate_parser(..., capture_trivia=True)` (line 232). This parser is NOT the committed fltk_parser.py; it is dynamically created and cached. The Python path reuses the committed fltk_parser, which was generated with `capture_trivia=False`.

---

## 3. ROOT CAUSE: Parser Generation Settings Diverge

**The Contradiction Resolved:** Why do Rust and Python backends diverge?

### The Answer: **(i) The Rust path uses a parser generated WITH capture_trivia=True**

**Evidence Chain:**

1. **Python Path:**
   - Uses committed parser: `fltk_parser.Parser()`
   - Generated once, committed to repo, generated with **capture_trivia=False**
   - Trivia is parsed but NOT appended → no `(None, Trivia)` in CST

2. **Rust Path:**
   - Calls `generate_parser(fegen_grammar, rust_cst_module="fegen_rust_cst")`
   - No `capture_trivia` argument passed → defaults to **capture_trivia=True** (line 211)
   - Generated parser appends trivia → `(None, Trivia)` entries appear in CST

3. **CST Sink is Passive:**
   - Python CST (dataclass): `append(label, child)` is a generic method, stores `(label, child)` tuple
   - Rust CST (PyO3 binding): `append(child, label=None)` is equally generic, stores `(label, child)` tuple
   - Neither CST has conditional logic to reject `(None, child)` tuples; they are passive sinks

4. **Empirical Evidence (Test):**
   - `/home/rnortman/src/fltk/tests/test_phase4_fegen_rust_backend.py:66-70`:
     ```python
     python_result = parse_grammar(_SIMPLE_GRAMMAR)
     rust_result = parse_grammar(_SIMPLE_GRAMMAR, rust_fegen_cst_module="fegen_rust_cst")
     assert python_result == rust_result
     ```
   - This assertion would fail without the `fltk2gsm.Cst2Gsm` filter (lines 48-52) that strips `(None, Trivia)` entries BEFORE semantic processing.

**Conclusion (3):** ✓ **DEFINITIVELY RESOLVED.** The Rust backend emits `(None, Trivia)` because its parser is **generated with `capture_trivia=True`**, while the Python backend's committed parser was **generated with `capture_trivia=False`**. The decision is made at **parser generation time**, not at CST construction time. The filter at `fltk2gsm.py:48-52` is necessary because the two backends produce **structurally different CST inputs** to `Cst2Gsm`.

---

## 4. Why This Matters

The prior investigation's conclusion was **correct but underspecified:**

- ✓ Trivia capture is a PARSER decision, not a CST decision.
- ✗ BUT: The CST's `append(label=None)` is not "unconditional" in the sense of being outside the capture_trivia gate; it's **unconditional IN ITS OWN METHOD**, but the **parser generator gates whether it is called at all**.
- **The Real Issue:** The two parser paths use **different capture_trivia settings**, not because the CST is broken, but because the **Rust path defaults to capture_trivia=True** while the **Python path uses a pre-generated parser with capture_trivia=False**.

---

## 5. Source Files and Line References

| File | Lines | Finding |
|------|-------|---------|
| `/home/rnortman/src/fltk/fltk/fegen/gsm2parser.py` | 584-590, 605-611 | Parser generator gates trivia appends on `capture_trivia` |
| `/home/rnortman/src/fltk/fltk/plumbing.py` | 208-211 | `generate_parser()` defaults to `capture_trivia=True` |
| `/home/rnortman/src/fltk/fltk/plumbing.py` | 132-135 | Python path uses committed fltk_parser.Parser |
| `/home/rnortman/src/fltk/fltk/plumbing.py` | 158-162 | Rust path calls `generate_parser(..., capture_trivia=True)` |
| `/home/rnortman/src/fltk/fltk/fegen/fltk_parser.py` | 301-302 | Committed parser parses trivia but does NOT append |
| `/home/rnortman/src/fltk/fltk/fegen/fltk2gsm.py` | 48-52 | Filter strips `(None, Trivia)` before semantic processing |
| `/home/rnortman/src/fltk/src/cst_fegen.rs` | 69-75 | Rust CST `append()` is passive sink; no conditional logic |
| `/home/rnortman/src/fltk/tests/test_phase4_fegen_rust_backend.py` | 66-70 | Test confirms Rust and Python results are equal after filtering |

---

## 6. Recommendation

To avoid backend divergence:

1. **Explicitly set capture_trivia in the Rust path:** Change line 158 to pass `capture_trivia=False`:
   ```python
   _fegen_rust_parser_cache[rust_fegen_cst_module] = generate_parser(
       fegen_grammar, rust_cst_module=rust_fegen_cst_module, capture_trivia=False
   )
   ```
   This would make Rust and Python paths use the **same capture_trivia setting**.

2. **Or document the deliberate divergence:** Add a comment explaining why the Rust path uses `capture_trivia=True` by default (e.g., for future Rust codegen work).

3. **Or regenerate the committed fltk_parser with capture_trivia=True** for consistency, then remove the `fltk2gsm` filter.
