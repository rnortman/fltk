# Prepass slop notes — commit 6ddec55

## slop-1

**File:** `crates/fltk-cst-spike/src/spike_tests.rs:1633`

**Quote:**
```rust
/// Phase 2 API: label enum rename (`IdentifierLabel` → `IdentifierLabel`, etc.),
```

**What's wrong:** The arrow shows the same name on both sides — `IdentifierLabel` → `IdentifierLabel`. The rename was `Identifier_Label` → `IdentifierLabel` (removing the underscore). The comment documents the wrong thing as the old name.

**Consequence:** The module-level docblock for the test file permanently misrecords what changed, undermining its value as a phase history. A reviewer spotting this wonders what else in the doc is wrong.

**Suggested fix:** `/// Phase 2 API: label enum rename (\`Identifier_Label\` → \`IdentifierLabel\`, etc.),`

---

## slop-2

**File:** `fltk/fegen/gsm2tree_rs.py` (generator) and all generated `.rs` files (`crates/fltk-cst-spike/src/cst.rs`, `src/cst_fegen.rs`), label enum docstring

**Quote (generator line 2030, emitted verbatim into every label enum):**
```python
lines.append("/// Rust consumers use the CamelCase `{enum_name}` name.")
```

**What's wrong:** The f-string prefix is absent. `{enum_name}` is a Python format placeholder, but without the `f` prefix it is emitted literally as `{enum_name}` into the generated Rust doc comment instead of the actual enum name (e.g. `IdentifierLabel`). The generated files already show this bug: every label enum docstring contains the literal text `{enum_name}`.

**Consequence:** Every generated label enum has a doc comment that reads "Rust consumers use the CamelCase `{enum_name}` name." — literally, with braces. This is visibly broken in `rustdoc` output and makes the doc noise rather than signal. Reviewers of downstream generated crates will see it.

**Suggested fix:** Change to `lines.append(f"/// Rust consumers use the CamelCase \`{enum_name}\` name.")` (add `f` prefix and escape the backticks).

---

## slop-3

**File:** `fltk/fegen/gsm2tree_rs.py:2231`

**Quote:**
```python
_, total_child_variants = self._child_variants_for_rule(rule_name)
child_class_names, has_span = self._child_variants_for_rule(rule_name)
```

**What's wrong:** `_child_variants_for_rule` is called twice on the same `rule_name` with the results split across two lines. The first call assigns `_` (discarded) and `total_child_variants` which is then never used — `total_enum_variants` on the next line is computed from `child_class_names` and `has_span` from the second call. The first call is dead code.

**Consequence:** Dead assignment signals the function was written by assembling parts without checking whether the pieces interact. A reviewer will wonder why `total_child_variants` is computed and discarded. The double call also wastes a traversal.

**Suggested fix:** Remove the first call entirely. `total_child_variants` is never read; the variable is unused.

---

## slop-4

**File:** All generated and hand-maintained node struct docstrings (`crates/fltk-cst-spike/src/cst.rs`, `src/cst_fegen.rs`, and generator `fltk/fegen/gsm2tree_rs.py`)

**Quote (generated for every node type, verbatim identical across Identifier, Items, Trivia, Grammar, Rule, Alternatives, …):**
```rust
/// **Clone semantics**: `Clone` on this struct is *shallow* — node-typed children
/// are [`Shared<T>`] (`Arc<RwLock<T>>`); cloning bumps the reference count,
/// it does NOT deep-copy the subtree. This matches the Python backend's
/// reference semantics: two clones of the same node share identity and
/// mutations through one are visible through the other.
///
/// **Accessing node children**: call `read()` on a `Shared<T>` child to borrow
/// its data, or `write()` to mutate. Never hold a guard while calling into Python.
```

**What's wrong:** Eight lines of identical boilerplate are emitted for every node type. No per-type information is present. This exact contract is already documented on `Shared<T>`. Copying it verbatim to every generated struct is documentation inflation — the previous base commit's slop review already flagged this pattern, and this commit makes it worse by expanding the block from ~five lines to eight.

**Consequence:** Mechanical repetition of identical docstrings is a LLM-generation tell visible to any reviewer skimming the file. Future corrections require a template change and full regeneration across all generated files. It dilutes trust in the rest of the doc quality.

**Suggested fix:** Replace the eight-line block with one line per node: `/// CST data struct for \`{class_name}\`. See [\`fltk_cst_core::Shared\`] for clone/equality/reference semantics.` Keep the full explanation on `Shared<T>` only.
