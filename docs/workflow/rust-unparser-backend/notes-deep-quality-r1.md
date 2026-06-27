# Quality Review — rust-unparser-backend batch 1

Commit reviewed: 285064a9a37c76f56f6fa1b44d4c553c34f49bcc

## quality-1

**File:** `crates/fltk-unparser-core/src/resolve.rs:39-42`

```rust
pub fn resolve_spacing_specs(doc: &Doc) -> Doc {
    let resolved = resolve_rc(&Rc::new(doc.clone()));
    rc_to_owned(resolved)
}
```

The public entry point takes `&Doc` and immediately deep-clones the entire tree to construct the `Rc<Doc>` the internal passes need. The design's stated rationale for using `Rc<Doc>` internally is "unchanged subtrees are shared by refcount bump" — but that sharing only applies to rewrites *within* a single resolve call; the initial `doc.clone()` always allocates a full second copy of the tree.

The natural callers described in the design have an owned `Doc` from `accumulator.doc()` (which itself returns `Doc` by value), so they do `resolve_spacing_specs(&r.accumulator.doc())` — creating a temporary, passing a reference, and triggering the O(tree-size) clone inside. Taking ownership avoids it entirely.

**Consequence:** Every resolve call transiently doubles Doc tree memory. This is the hot path: every generated unparser rule calls this once per unparse operation. The cost scales with source file size. Downstream consumers who benchmark will find unexplained memory pressure here, with no obvious fix visible from the call site.

**Fix:** Change the signature to `pub fn resolve_spacing_specs(doc: Doc) -> Doc` and replace `Rc::new(doc.clone())` with `Rc::new(doc)`. Call sites drop the leading `&`.

---

## quality-2

**File:** `crates/fltk-unparser-core/src/resolve.rs:197-215`

```rust
fn extract_boundary_specs(mut docs: Vec<Rc<Doc>>) -> BoundarySplit {
    let mut trailing_specs: Vec<Rc<Doc>> = Vec::new();
    while docs.last().is_some_and(...) {
        // Prepend so original order is preserved as we pop from the end.
        trailing_specs.insert(0, docs.pop().expect("last() was Some"));
    }

    let mut leading_specs: Vec<Rc<Doc>> = Vec::new();
    while docs.first().is_some_and(...) {
        leading_specs.push(docs.remove(0));
    }
    ...
}
```

Both loops are O(n²). `trailing_specs.insert(0, x)` shifts every existing element right on each insertion — for T trailing specs this is O(T²). `docs.remove(0)` shifts the remaining `docs` left on each removal — for L leading specs this is O(N·L) where N is the initial docs length. Both patterns were ported directly from Python's identically-named `list.insert(0, x)` and `list.pop(0)`, which have the same O(n)-per-call cost in CPython but are implemented in tight C loops whose constant factor masks the quadratic growth. In Rust, both generate visible `memmove` calls.

The `VecDeque` was already chosen for `resolve_concat_patterns`' working set (the same file, 25 lines above) precisely to avoid this class of problem. The inconsistency is jarring.

**Consequence:** Formatted source files with many consecutive trivia regions — the normal case for a code formatter preserving comments — can trigger the quadratic path. The issue propagates: every future caller of `extract_boundary_specs` inherits the O(n²) behavior without any indication it is there. The Python tests that drive cross-backend parity won't catch it because Python's CPython overhead dominates.

**Fix:** For trailing specs: `trailing_specs.push(docs.pop()...)` inside the loop, then `trailing_specs.reverse()` after — O(T) total. For leading specs: determine the count with `docs.iter().take_while(|d| ...).count()`, then `docs.drain(..count).collect()` — O(N) total (one `memmove` for the remainder, not one per removal).
