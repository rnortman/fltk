# Slop prepass — Phase 3 generator diff (6f82c48..aa73727)

## slop-1

**File:** `fltk/fegen/gsm2tree_rs.py`, lines inside `generate()` and `_node_block()`

**Quote:**
```python
        # Preamble
        parts.append(self._preamble())

        # Per-rule blocks
        for rule in self.grammar.rules:
        ...
        # register_classes function
```
and inside `_node_block`:
```python
        # Constructor
        lines.extend(self._new_method(class_name))
        # Label classattr (only if there are labels)
        ...
        # Generic append/extend/child
        ...
        # Per-label methods
        ...
        # __eq__, __hash__, __repr__
```

**What's wrong:** Self-explanatory narration comments that restate the next method call. `# Preamble` above `self._preamble()`, `# Constructor` above `self._new_method()`, `# Per-label methods` above `for label in labels`, and so on. None adds information the reader can't see instantly.

**Consequence:** Classic LLM writing tell — reads like generated commentary, not author intent. A human reviewer recognises it immediately and flags the PR.

**Fix:** Delete all of them. The section-divider comments (`# ----` boxes with names matching private method names) also narrate rather than explain, but are at least structurally useful for skimming a long file; they're borderline. The inline procedural comments above individual `lines.extend(...)` calls are clearly noise and should go.

---

## slop-2

**File:** `fltk/fegen/gsm2tree_rs.py`, lines ~99, ~142

**Quote:**
```python
        # Separator comment
        lines.append(f"// {'─' * 75}")
```

**What's wrong:** `# Separator comment` is a comment naming the thing it immediately precedes — a pure restatement. The three lines after it make it obvious what is being emitted.

**Consequence:** Same LLM tell as slop-1; looks like an author narrating their own actions.

**Fix:** Delete the `# Separator comment` lines.

---

## slop-3

**File:** `tests/test_gsm2tree_rs.py`, docstrings throughout

**Quote (representative):**
```python
    def test_register_classes_adds_identifier_label(self, poc_source: str) -> None:
        """register_classes calls add_class for Identifier_Label."""
        assert "module.add_class::<Identifier_Label>()?;" in poc_source
```
```python
    def test_identifier_struct_present(self, poc_source: str) -> None:
        """Identifier node struct is emitted."""
        assert "pub struct Identifier {" in poc_source
```

**What's wrong:** Every docstring in the test classes is an English restatement of the test name and/or its single assertion. `test_identifier_struct_present` / `"""Identifier node struct is emitted."""` — the docstring is the test name minus underscores. Dozens of occurrences.

**Consequence:** Pattern fills the file with noise. In a real code review this signals the docstrings were auto-generated to satisfy a linting rule rather than to document intent or non-obvious behaviour. Reviewers notice.

**Fix:** Either delete docstrings where the test name is fully self-describing (majority here), or replace with a sentence that adds something the name cannot — e.g. why this property matters, what edge case is exercised, or which AC it covers. The AC references (`"""AC-5: pub fn register_classes is present."""`) are the best ones; keep those, drop the pure restatements.

---

## slop-4

**File:** `src/lib.rs`, lines ~33–42 (new block in diff)

**Quote:**
```rust
    // CST node types (PoC grammar: Identifier, Items, Trivia)
    cst_generated::register_classes(m)?;

    // Fegen grammar classes in a submodule to avoid name collisions
    // (both grammars produce Identifier, Items, Trivia)
    let fegen_sub = PyModule::new(m.py(), "fegen_cst")?;
    cst_fegen::register_classes(&fegen_sub)?;
    m.add_submodule(&fegen_sub)?;

    // PyO3's add_submodule does NOT register in sys.modules, so
    // `from fltk._native.fegen_cst import X` would fail with
    // ModuleNotFoundError. Fix by inserting manually:
```

**What's wrong:** The comment `// CST node types (PoC grammar: Identifier, Items, Trivia)` is benign context; fine. The `// PyO3's add_submodule does NOT register in sys.modules` block is a legitimately useful explanation of a non-obvious PyO3 limitation — not slop. No findings here; this block is clean.

*(Noting explicitly so the reviewer knows it was examined.)*

---

No silent-fallback or error-swallowing issues visible in the diff. The `child_` / `maybe_` methods in generated Rust all propagate errors correctly via `?`. The `.expect()` calls in `_new_method` are on a once-cell that must be initialized before any node construction, which is the correct pattern for this codebase's PyO3 setup.
