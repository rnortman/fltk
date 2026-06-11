# Design review notes: non-recursive Debug for generated CST node structs

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Verified against source at base commit 7ddec4a. Confirmed accurate: `gsm2tree_rs.py:638-640` TODO comment + `#[derive(Clone, Debug)]` emit; `_preamble()` at line 261 (no existing `use std::fmt;` in generated outputs — addition is safe and used unconditionally since every output emits ≥1 node Debug impl); `_child_enum_block` derive at line 504; NodeKind/label dual-cfg derives at 356/364/445/453; `_repr_method` at 1500-1511; `Shared<T>::Debug` at `shared.rs:98-102` and cycle contract at `shared.rs:36-40`; `Span` manual shallow Debug at `crates/fltk-cst-core/src/span.rs:155-163` (start/end/has_source — matches design's example output); spike smoke tests at `spike_tests.rs:364-378`; TODO.md entry at lines 84-86; `make gencode` regenerates exactly the six outputs listed (Makefile, incl. `cp src/cst_generated.rs crates/fltk-cst-spike/src/cst.rs`); `expr := lhs:expr . "+" . rhs:atom | atom:atom` at `fltk/fegen/test_data/rust_parser_fixture.fltkg:32` with `ExprChild::Expr(Shared<Expr>)` at `tests/rust_parser_fixture/src/cst.rs:5080-5083`; `tests/rust_parser_fixture/src/native_tests.rs` exists and is wired via `mod native_tests;` in lib.rs. Requirements coverage: all constraints (`__repr__`, `Clone`, `Shared<T>` untouched; TODO removal) and all verification expectations map to design sections. Scope is disciplined; one-level child-enum delegation argument is sound (derived enum Debug → `Shared<T>::Debug` → manual node Debug terminates at constant depth). `format_args!` inside `.field(...)` is a valid inline-temporary pattern; `Arguments`' Debug forwards to Display, so the elision marker prints unquoted as shown.

## Findings

### design-1

Section: "Edge cases / failure modes" — "The new test must tear the chain down iteratively (pop one level at a time into a worklist)".

What's wrong: the teardown mechanism is underspecified and the obvious reading (drain children out of each node) is impossible. Generated node fields are private to the `cst` module (`tests/rust_parser_fixture/src/cst.rs` — "Not pub: use span() / children() / push_child()"), and the public API has no destructive child accessor (no `drain`/`clear`/`take`; only `children()` returning `&[...]`, `push_child`, `extend_children`, per-label read accessors). `native_tests.rs` is a sibling module — it cannot touch `self.children`.

Why: API surface verified in `tests/rust_parser_fixture/src/cst.rs` (e.g. lines 1388-1437 pattern repeated per node); no removal method exists anywhere in `gsm2tree_rs.py`'s emitted native impl.

Consequence: an implementer following "pop into a worklist" literally either gets stuck or adds a destructive child API to the generator — scope creep into the public generated API that this hardening fix must not cause.

Suggested fix: specify the working mechanism explicitly. Two options that need no new API: (a) during construction, retain a `Vec<Shared<Expr>>` of every level ordered root-first; after the Debug assertion, drop the root binding, then drop the vec front-to-back — each drop deallocates exactly one node because the next level is still held by the vec; or (b) walk down via `children()`, cloning the child `Shared` before dropping the current node (clone-then-drop: parent dealloc decrements child refcount 2→1, no recursion). Either is O(1) recursion depth per step.

### design-2

Section: "Test plan" item 1 — "Depth rationale: 100 000 frames × ~64-256 bytes/frame exceeds the 8 MiB default stack under the old derive".

What's wrong: the arithmetic conflates frames with tree levels and, taken at face value, does not prove overflow: 100 000 × 64 B = ~6.1 MiB < 8 MiB. The actual reason 100 000 overflows is that each tree level costs *multiple* stack frames under the old derive (`Shared::fmt` → node derived `fmt` → `debug_struct` machinery → `Vec` Debug → tuple Debug → `ChildEnum` derived Debug → next `Shared::fmt`), so per-level cost is several hundred bytes to >1 KiB, especially in debug builds.

Why: chain structure verified at `shared.rs:98-102` plus the derived impls described in exploration §2; the per-frame figure is copied from exploration §5, which made the same level/frame conflation.

Consequence: as written, the load-bearing claim "the test proves the fix" rests on arithmetic that doesn't close at its own low end; if someone later "optimizes" the depth down using the same 64 B/frame figure (e.g. to 10 000 levels — exploration §5 calls that "feasible"), the pre-fix demonstration could become vacuous and the post-fix Drop-teardown requirement could be wrongly dropped.

Suggested fix: restate as "~5-10 frames per tree level under the old derive → multi-hundred-byte per-level cost → 100 000 levels comfortably exceeds the 8 MiB test-thread stack". Conclusion (100 000 is the right depth) stands.

### design-3

Section: "Test plan" item 1 — "the only fixture grammar with a self-recursive node type reachable programmatically".

What's wrong: factually incorrect. `tests/rust_cst_fegen/src/cst.rs` (fegen grammar) also has programmatically reachable recursive node types (e.g. `Shared<Alternatives>` reachable from term/sub-expression nodes, `cst.rs:779`), and within `rust_parser_fixture.fltkg` itself `lval`/`rval` (mutual recursion, lines 36-37) and `rec_via_sub` (line 66) are also recursive.

Why: verified by grep of `tests/rust_cst_fegen/src/cst.rs` and the fixture grammar file.

Consequence: none material — `Expr` is still the simplest direct self-recursion and a fine choice — but a false uniqueness claim invites a future reader to treat the location as forced rather than chosen. Reword to "simplest directly self-recursive node type" or similar.

## Open question assessment (recursive Drop TODO)

Design open question 1 asks whether to file `TODO(rust-cst-drop-depth)` for the pre-existing recursive-Drop exposure. Assessment: **file it**. Verified facts: (a) the exposure is real — dropping the last `Arc` of a depth-N chain recurses through `Expr` drop glue → `Vec` → `ChildEnum` → `Arc` per level, unbounded, uncatchable, same attacker-controlled-depth threat model as the Debug fix; (b) it is pre-existing (Phase 1 `Shared` ownership model), not introduced by this change; (c) no existing slug covers it — repo grep for `rust-cst-drop-depth` returns nothing, and the `apply-depth-limit`/`parser-depth-limit` entries (TODO.md:45-52, 76-78) gate parse admission only, the same gap exploration §5 documents for Debug; (d) it satisfies the TODO.md discipline test (concrete thing, obvious "done": iterative/worklist Drop or documented mitigation). Suggested `TODO(slug)` comment locations: the struct emission in `gsm2tree_rs.py` (where the `children: Vec<...>` field is emitted — the recursion seat) and the new deep-tree test's iterative teardown (the in-tree demonstration of the workaround). This is a user-decision item per TODO discipline, but the design's recommendation is sound; it should not block this fix.
