# Deep correctness review — rust-cst-eq-depth

Commit reviewed: 44458c5 (base b02cb8f).
Style note: concise, precise, no padding (per reviewer charter).

Scope verified (no findings in these areas):

- Iterative `PartialEq` driver (`gsm2tree_rs.py:836-856`) checks the same conjuncts as the old
  recursive `self.span == other.span && self.children == other.children` (span eq → Vec len eq →
  per-index tuple eq: label then child variant/value). Pure boolean, no side effects → reordered
  traversal (LIFO pop, rightmost-first descent) is unobservable. Result-equivalent.
- Emission coherence: `eq_shallow_enqueue` gated on `needs_drop_item` (`gsm2tree_rs.py:626`) covers
  every call site — `EqWorklistItem::compare` arms call it only for child-union members; the
  iterative driver calls it only when `child_classes` non-empty (which implies `needs_drop_item`).
  `EqWorklistItem` is emitted iff `child_union` non-empty, which holds whenever any
  `eq_shallow_enqueue` body references it. Flat grammars emit none of it.
- Match exhaustiveness: wildcard `_ => false` emitted only when `num_variants > 1`, matching the
  existing `ChildEnum::PartialEq` guard; single-node-variant enums (e.g. `EntryChild`,
  `tests/rust_cst_fixture/src/cst.rs:182`) and span-only enums are exhaustive without it. Verified
  in regenerated fixtures.
- `_worklist` underscore convention applied exactly when `child_classes` empty (no `worklist.push`
  emitted in that case) — no unused-variable / undefined-name mismatch possible.
- Lock discipline: per worklist item, exactly two read guards (`ga`, `gb`), never the same lock
  twice (ptr_eq-equal pairs are never enqueued; the seed loop and `eq_shallow_enqueue` both skip
  them). With `Shared::eq` at the root: two guard pairs max, as the updated shared.rs doc states.
  No new deadlock vs. the old full-ancestor-path locking (strictly smaller lock set).
- No O(n²): node-typed child pairs are enqueued, never compared via `ChildEnum::eq` inside the
  driver or `compare`.
- Early-`false` worklist drop: items hold Arc clones of nodes still owned by the borrowed trees
  (`eq(&self, &other)` → trees outlive the call), so drop is refcount decrement only; and node
  `Drop` is itself iterative regardless.
- Span-only node classes keep the one-line eq — their `ChildEnum` is Span-only, non-recursive;
  equivalent to the `compare` arm shallow check.
- All 7 regenerated .rs outputs contain the expected constructs and match the generator
  (spot-checked `src/cst_generated.rs`, `tests/rust_cst_fixture/src/cst.rs`).
- shared.rs: doc-only change as designed; ptr_eq short-circuit code unchanged.
- Tests EQ-1/2/3/5/6 build/exercise what their comments claim (EQ-4: see correctness-2).

## correctness-1

- **File:line:** `/home/rnortman/src/fltk/fltk/fegen/gsm2tree_rs.py:2091` (emitted comment), and the
  copy in all 7 regenerated files (e.g. `/home/rnortman/src/fltk/src/cst_fegen.rs:15299`,
  `/home/rnortman/src/fltk/src/cst_generated.rs` `EqWorklistItem::compare`).
- **What's wrong:** The generated comment in `EqWorklistItem::compare` reads "Guards are held only
  for the duration of one arm and dropped before any push." The second clause is false: pushes
  happen *while* `ga`/`gb` are held — `eq_shallow_enqueue(cb, worklist)` is called inside the
  `for` loop over `ga.children`/`gb.children`, which borrows from the live guards, and it executes
  `worklist.push(...)` there.
- **Why:** Trace `_emit_eq_arm` (`gsm2tree_rs.py:2042-2054`): `let ga = a.read(); let gb = b.read();`
  then the child loop calls `eq_shallow_enqueue`, whose node arms push. Guards drop at arm end,
  *after* all pushes. The design doc itself states the opposite of the comment (design.md §2.2b:
  "pushes under the guards are plain `Vec` pushes + `Arc` clones, no lock acquisition").
- **Consequence:** Code behavior is correct (the pushes take no locks, so no hazard exists today),
  but the comment documents a lock-window invariant that does not hold. A maintainer extending
  `eq_shallow_enqueue` or `compare` with lock-taking work (e.g. eager child comparison) and
  trusting "guards dropped before any push" would introduce a real same-thread RwLock re-entry
  deadlock — exactly the failure class this code exists to manage — with the comment certifying
  it safe.
- **Suggested fix:** In `_eq_block` (`gsm2tree_rs.py:2091`) reword to: "Pushes occur while the
  pair's guards are held; they are plain Vec pushes + Arc clones and take no locks. Guards drop at
  arm end." Regenerate (`make gencode` → `make fix`).

## correctness-2

- **File:line:** `/home/rnortman/src/fltk/tests/rust_parser_fixture/src/native_tests.rs:228-258`
  (`test_multi_child_eq_worklist`, doc comment at :230).
- **What's wrong:** The test's doc comment (and design.md §5 item 4) says the unequal variant has
  "one rhs differs". The implementation differs only at the deepest *lhs-spine* leaf:
  `build_multi_child_tree(leaf_span)` threads `leaf_span` solely into the bottom `Num` under the
  lhs chain (:234), while every rhs `Atom`/`Num` is always `Span::unknown()` (:246-248).
- **Why:** `let c = build_multi_child_tree(Span::new_sourceless(0, 1))` — the only use of the
  parameter is `cst::Num::new(leaf_span)` at the chain bottom; the rhs construction inside the
  loop ignores it.
- **Consequence:** The claimed coverage — a mismatch detected in an rhs branch, i.e. in a worklist
  entry that is not on the deepest pending path — is not exercised; the mismatch sits at the end
  of the lhs spine, the same shape EQ-2 already covers. The equal-case half does exercise
  multi-pair worklists, so the suite still demonstrates the fix; only the unequal half tests less
  than it states. A future regression that mishandles `false` from a non-final worklist item
  (e.g. in rhs subtrees) would not be caught.
- **Suggested fix:** Build the unequal variant by mutating one rhs atom's `Num` span at a mid-level
  (or add a `rhs_leaf_span` parameter), or correct the comment to "differs at the deepest lhs
  leaf".

## correctness-3

- **File:line:** `/home/rnortman/src/fltk/fltk/fegen/gsm2tree.py:407` (`for mt in model.types`,
  feeding the "deduplicate while preserving order" list at :417-421); churn visible in this diff in
  `/home/rnortman/src/fltk/fltk/fegen/bootstrap_cst.py`, `fltk/fegen/fltk_cst.py`,
  `fltk/unparse/toy_cst.py`, `fltk/unparse/unparsefmt_cst.py`.
- **What's wrong:** Regenerating for this change produced semantically-neutral reorderings of
  `isinstance(child, A | B | C)` unions and `_MUTATOR_ALLOWED_CHILD_TYPES` tuples in four Python
  generated files this change does not touch logically. The "order-preserving dedup" preserves the
  iteration order of `model.types`, which is a `set` (built via `|=` at `gsm2tree.py:638`); `str`
  hashing is per-process randomized, so the emitted order varies run to run. The generator's
  emission is nondeterministic, contradicting its own "for deterministic output" comment at :416.
- **Why:** Set iteration order of `set[str]` depends on `PYTHONHASHSEED`; two `make gencode` runs
  on identical input can emit differently ordered (behaviorally identical) source.
- **Consequence:** No runtime behavior change (isinstance unions and membership tuples are
  order-insensitive). But every regeneration can dirty committed generated files at random,
  injecting unrelated churn into commits (as it did here), obscuring real generated-code diffs in
  review, and making the regen-then-compare flow (`make check` cleanliness) seed-dependent —
  a commit that is "clean" under one hash seed can appear stale under another.
- **Suggested fix:** Sort the collected child-type names (or iterate `sorted(model.types, key=...)`)
  before emission in `gsm2tree.py` `_check_child_type_for_mutators` generation, then regenerate
  once to pin the order. Pre-existing defect, not introduced by this change — surfaced by its
  regeneration; out of scope to fix here but worth a TODO.
