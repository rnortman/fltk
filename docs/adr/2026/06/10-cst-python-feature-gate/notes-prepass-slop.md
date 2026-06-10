## slop-1

File: `crates/fltk-cst-spike/src/cst.rs:956-960`

```rust
return Err(PyTypeError::new_err(format!(
    "Identifier.append: label argument is not a Identifier_Label; got {}",
```

The `extend` method on `Items` (line ~1352) and `Trivia` (line ~1916) emits the same error message with `"Identifier.append:"` and `"Trivia.append:"` respectively — but these are copy-paste errors in generated code: `Items.extend` reads `"Items.append:"` (correct), `Trivia.extend` also says `"Trivia.append:"` (technically wrong label for `extend`, but the same mistake is present in the source generator and emitted into `src/cst_fegen.rs` and the fixture). The actual pattern is the `extend` method emitting an error saying `.append:` in its body. This is a copy-paste slop in the generator (`gsm2tree_rs.py`) that was replicated across all generated files.

What's wrong: `extend` error messages say `NodeName.append:` instead of `NodeName.extend:`. Visible in `crates/fltk-cst-spike/src/cst.rs` for all three node types and confirmed in `src/cst_fegen.rs` and `src/cst_generated.rs`.

Consequence: When `extend` rejects a label, the error message names the wrong method. Downstream consumers debugging type errors will see misleading information blaming `append` when `extend` was called. Ships with diagnostically incorrect error strings.

Suggested fix: In `gsm2tree_rs.py` `_extend_method` (or equivalent), use the actual method name in the error string rather than hardcoding the `append` name.

---

## slop-2

File: `crates/fltk-cst-spike/src/cst.rs:885-888`

```rust
/// Return a fltk._native.Span so consumers always get the canonical type
/// regardless of which cdylib the node is defined in.
/// Preserve source via span_to_pyobject: O(1) Arc clone, no string copy.
span_to_pyobject(py, &self.span)
```

The same three-line comment block (`Return a fltk._native.Span...`) is repeated verbatim for every `span` getter across all three node types in `cst.rs` (Identifier, Items, Trivia), and identically in `src/cst_generated.rs`, `src/cst_fegen.rs`, and `tests/rust_cst_fixture/src/cst.rs`. The comment is also repeated for `to_pyobject` Span arms:

```rust
// span_to_pyobject: O(1) Arc clone, no string copy; preserves
// Arc-sharing so multiple reads of the same span merge without error.
```

What's wrong: Same comment block copied into N spans across multiple files. Each is self-explanatory from context and the function name. This is generated code, but the duplication is in the generator template — the comment exists because an LLM inserted it during generation rather than because it documents non-obvious behavior.

Consequence: Noise in code review and future diffs. Reviewers reading diffs must process identical comments at each occurrence. Minor embarrassment indicator that this is LLM-authored.

Suggested fix: Remove or trim the inline comments in the generator template; the function name `span_to_pyobject` documents what it does, and the O(1) arc-clone property belongs in the function's own docstring, not at every call site.

---

## slop-3

File: `crates/fltk-cst-core/src/lib.rs:143`

```rust
/// --- Native Span API tests (§4 item 2 from design) ---
```

The comment `§4 item 2 from design` is a reference to a task or design document, not to code behavior. It tells the reader "this test suite was written to satisfy a design requirement" rather than describing what is being tested or why the behavior matters.

What's wrong: Narrative comment referencing an external design document section. Code comments should be self-contained; a design reference is PR description material.

Consequence: The comment ages poorly (the design doc numbering will drift) and reads as LLM scaffolding left in production code.

Suggested fix: Replace with a plain description of what the test block covers, e.g. `// Tests for the native (non-Python) Span API`.

---

No other slop findings. The structural changes (cfg gates, dual-enum blocks, feature forwarding) are mechanically correct and well-explained. The `check-no-pyo3` positive-control guard is a good practice. The implementation-log and gaps documents are appropriately explicit about deviations.
