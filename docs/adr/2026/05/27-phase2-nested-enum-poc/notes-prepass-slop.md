# Slop Prepass Notes

## slop-1

**File:** `src/cst_poc.rs:120–128, 299–303`

**Quote:**
```rust
// Generic methods

#[pyo3(signature = (child, label = None))]
fn append(&self, py: Python<'_>, child: PyObject, label: Option<PyObject>) -> PyResult<()> {
    let label_val = label.unwrap_or_else(|| py.None());
```

**What's wrong:** Section header comment `// Generic methods` and `// Per-label methods for NAME` / `// Per-label methods for ITEM` / `// Per-label methods for NO_WS` / `// Per-label methods for WS_ALLOWED` / `// Per-label methods for WS_REQUIRED` / `// Dunder methods` are section divider labels, not meaningful code comments. They describe organization, not behavior, invariants, or non-obvious intent. These read as LLM scaffolding commentary.

**Consequence:** Noise in a code review; signals the structure was narrated during generation rather than self-evident from method names. Not embarrassing on its own but accumulates.

**Suggested fix:** Delete all of these section-header comments. The method names already communicate the groupings.

---

## slop-2

**File:** `src/lib.rs:676`

**Quote:**
```rust
// Phase 2 PoC: CST node types
```

**What's wrong:** Task-context comment ("Phase 2 PoC") embedded in production source code. This refers to the implementation phase/ticket, not anything about the code's runtime behavior or invariants.

**Consequence:** When this code graduates beyond PoC status, the comment is actively misleading. Phase references belong in commit messages and ADRs, not in source.

**Suggested fix:** Remove the comment entirely, or replace with a brief description of what the block actually does (e.g., `// CST node types for parser output`).

---

## slop-3

**File:** `src/cst_poc.rs` — entire file structure

**What's wrong:** Massive verbatim duplication. The `Identifier` struct (lines ~88–258) and `Items` struct (lines ~264–656) are structurally identical except for type name and labels. Every method body (`append`, `extend`, `child`, `children_<label>`, `child_<label>`, `maybe_<label>`, `__eq__`, `__hash__`, `__repr__`) is copy-pasted verbatim. This is a 629-line file where ~500 lines are mechanical repetition.

**Consequence:** This is a PoC, so some duplication may be intentional to explore the pattern before abstracting. However, if this is being shipped as "the" implementation rather than a prototype, it is not ready: any bug fix must be applied in N places, and adding a new node type requires another full copy. The PoC framing (ADR path, implementation log) suggests this is intentional, but the code itself carries no comment acknowledging the duplication or marking where the abstraction should live.

**Suggested fix:** Either (a) add a `TODO(rust-cst-macro)` comment at the top of the file noting that the per-node boilerplate should be extracted into a proc-macro or generic helper, with a matching entry in `TODO.md`, or (b) extract the shared logic now. If this is genuinely a PoC not intended to be the final form, that should be stated in a code comment so reviewers don't flag it.

---

No silent fallbacks, swallowed errors, or workarounds found. All `PyResult` returns propagate errors correctly.
