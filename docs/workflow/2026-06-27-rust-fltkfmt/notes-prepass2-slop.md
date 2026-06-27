# Slop review — increments 4-6 (prepass 2)

Commit reviewed: c52d998a09e4ce433289872be91a3ce7c249dca0

---

## slop-1

**File:** `crates/fltk-fmt-cli/src/lib.rs` — `is_stdin`

**Quote:**
```rust
/// Is this path the stdin sentinel (`-`)?
fn is_stdin(path: &Path) -> bool {
```

**What's wrong:** Docstring restates the function name verbatim. Every word in the comment (`is`, `this`, `path`, `stdin`, `sentinel`) is already in the identifier.

**Consequence:** Noise that signals LLM-written copy; a reviewer scanning for meaningful documentation will slow down here looking for the non-obvious information that isn't there.

**Fix:** Delete the docstring. If there is a non-obvious invariant (e.g. that the sentinel is case-sensitive, or must be a bare `-` rather than `--`), document that instead.

---

## slop-2

**File:** `crates/fltk-fmt-cli/src/lib.rs` — `validate`

**Quote:**
```
The rejected combinations are exactly those listed
in the design's "CLI behavior summary": ...
```

**What's wrong:** Design-document citation in production code. The phrase "the design's 'CLI behavior summary'" is a reference to an external artifact that out-of-tree readers cannot follow and that will not stay synchronized with the code.

**Consequence:** For downstream consumers reading rustdoc or grepping the source, the reference is dead noise. It also signals that the comment was written to satisfy a task checklist rather than to inform a maintainer — a classic LLM tell.

**Fix:** Remove the citation. The enumerated list of rejected combinations that follows it is the correct documentation; the sentence "The rejected combinations are exactly those listed in the design's 'CLI behavior summary'" can be dropped entirely.

---

## slop-3

**File:** `crates/fltk-fmt-cli/src/lib.rs` — `write_atomic`

**Quote:**
```
See design §3 "`--in-place` write atomicity".
```

**What's wrong:** Another design-document cross-reference — `§3` is opaque without the document in hand. The two sentences before it already explain the atomic-write rationale completely.

**Consequence:** Dead citation for any reader without the design document (all out-of-tree consumers, anyone after the document moves or is superseded). Reads as an LLM citing its own sources.

**Fix:** Drop the `See design §3 ...` sentence. The preceding explanation ("A crash mid-write leaves the original intact") stands on its own.

---

## slop-4

**File:** `crates/fltk-fmt-cli/src/lib.rs` — `fltk_formatter_main!` docstring

**Quote:**
```
/// This is the "easy reuse" surface from the design: a consumer crate writes a single
/// invocation naming its grammar's concrete `Parser`/`Unparser` types ...
```

**What's wrong:** "This is the 'easy reuse' surface from the design" is process narrative — the LLM is describing its task artifacts, not the API. A caller reading rustdoc has no design document and no reason to care what the design called this.

**Consequence:** Public API docstring (this is `#[macro_export]`) opens with LLM self-talk. Out-of-tree consumers see this in generated docs.

**Fix:** Replace the opening sentence with a direct description of what the macro does: e.g. "Generates `fn main()` for a standalone FLTK formatter binary using the proven parse → unparse → render pipeline."

---

## slop-5

**File:** `crates/fltkfmt/src/main.rs` — module doc

**Quote:**
```
//! Almost all of the work lives in the reusable `fltk-fmt-cli` scaffolding crate. This
//! crate is the scaffolding's first consumer: ...
```

**What's wrong:** "First consumer" records the moment of development (this was the first crate to use the scaffolding), not a durable property of the code. It will be wrong — and confusing — the moment a second consumer exists.

**Consequence:** Module doc in a shipped binary will read as incorrect or mysterious to any reader after the second consumer appears. It is a process diary entry, not documentation.

**Fix:** Drop "first consumer" framing. The useful part — that any FLTK grammar formatter is a single macro invocation — should be the lead sentence instead.
