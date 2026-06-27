# Reuse Review — batch 1 (base 8a29f254, HEAD 285064a9)

## reuse-1

**File:line**: `crates/fltk-unparser-core/src/resolve.rs:73–87`

**What's duplicated**: `concat_rc` implements the same three-step normalization as `doc::concat` — flatten nested `Concat`s, drop `Nil`s, collapse a single survivor to the element itself (or `Nil` for empty). The only difference is the element type (`Rc<Doc>` vs `Doc`) and the return type (`Rc<Doc>` vs `Doc`).

**Existing function**: `pub fn concat(docs: Vec<Doc>) -> Doc` at `crates/fltk-unparser-core/src/doc.rs:199`.

**Consequence**: The normalization rules live in two places. If a rule changes in one — for example a new short-circuit, a change to how a single-element list is unwrapped, or a future `Nil`-equivalence added to `Doc` — the other won't be updated automatically. Since `concat` is the public API used by generated callers and `concat_rc` is the internal path used by every structural pass in `resolve.rs` (five call sites), a divergence would mean generated code and the resolver see different normalizations of the same logical tree, a silent correctness gap. The implementation log acknowledges this as a deliberate type-driven choice (increment 3 deviations); the risk is real regardless.

---

## reuse-2

**File:line**: `crates/fltk-unparser-core/src/resolve.rs:722–733` (inside `#[cfg(test)] mod tests`)

**What's duplicated**: Four test-local helpers — `line()`, `softline()`, `hardline(blank_lines: u32)`, `nil()` — are redefined verbatim; each is a one-line constructor returning the corresponding `Doc` variant. The test module imports `use crate::doc::text` explicitly but not the others.

**Existing functions**: `pub fn line() -> Doc` (`doc.rs:143`), `pub fn softline() -> Doc` (`doc.rs:153`), `pub fn hardline(blank_lines: u32) -> Doc` (`doc.rs:164`), `pub fn nil() -> Doc` (`doc.rs:159`).

**Consequence**: If a constructor's signature or semantics changes in `doc.rs` (e.g., `hardline` gains an extra parameter, or `nil` is removed in favour of something else), the local copies in the test module silently diverge: the tests continue to compile against the local stub while the production path uses the new API. The fix is a single `use crate::doc::{line, softline, hardline, nil};` import replacing the four function bodies.
