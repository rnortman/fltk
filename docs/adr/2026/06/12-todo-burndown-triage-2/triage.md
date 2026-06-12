# TODO Burndown Triage — 2026-06-12 (second batch)

Style: concise, precise, no padding. Audience: someone who has not read the code and doesn't want to.

Scope: all entries in TODO.md. `bazel-rules-rust` skipped per user instruction. `example-placeholder` is by definition not a TODO. That leaves two real items, both validated against code by adversarial explorers (see `exploration-*.md` in this dir).

---

## 1. `empty-cn-underscore-rule`

### What the problem is (ELI5)

When you write a grammar, every rule name gets turned into a Rust class name by capitalizing the words between underscores: `my_rule` → `MyRule`. But if you name a rule just `_` (or `__`), there are no words between the underscores — so the class name comes out as the **empty string**. The generator doesn't notice; it cheerfully writes `pub struct  {` (a class with no name) into the output file, which is broken Rust. You don't find out until the Rust compiler chokes on the gibberish, with no hint that the cause was your weird rule name.

The validation pass confirmed every detail of the TODO, plus one thing it missed: **labels have the same hole**. A label named `_` collapses to an empty enum-variant name through the exact same code path, producing equally broken Rust.

For comparison, the Python backend isn't silent — it blows up with a raw `SyntaxError` during generation. Ugly and unhelpful, but at least it fails before emitting garbage.

### Why it matters

Silent generation of invalid output is a "robust as fuck" misalignment: the generator's job is to either produce valid code or tell you clearly why it can't. A downstream user who names a rule `_` gets a cryptic rustc error pointing at generated code they didn't write, with no clue that their grammar is the problem. Low likelihood (who names a rule `_`?), but the fix is tiny and the failure mode is maximally confusing when it does hit.

### What the work actually looks like

A few lines in `fltk/fegen/gsm2tree_rs.py` (`RustCstGenerator.__init__`, which already validates identifiers and reserved names): after deriving the class name, raise a clear `ValueError` if it's empty — and do the same for each label's derived variant name. Plus a small test for each case. The recent cross-rule collision check (commit 108ee61) does NOT cover this: it only fires when *two* rules collide; a *single* `_` rule passes silently.

Optional extension (not required): give the Python backend the same friendly check so it raises a clear `ValueError` instead of a raw `SyntaxError`. Cheap, same shape.

### The case for skipping

Underscore-only rule names are pathological; nobody has hit this. The Rust compiler does ultimately stop you — the failure is confusing, not silent data corruption.

### Recommendation: **Do** (reframed)

Do the reframed version: empty-derived-name check in `RustCstGenerator.__init__` for **both rule names and labels** (the original TODO covered rule names only), with clear error messages and tests. Include the Python-backend friendly check in the same pass since it's the same five lines. Small, self-contained, no design questions.

---

## 2. `extend-children-owned`

### What the problem is (ELI5)

When the generated Rust parser builds a tree node from a sub-piece (like the body of a `+`/`*` loop), it copies the sub-piece's children into the parent and then throws the sub-piece away. Children are held via reference-counted pointers (`Arc`), so "copy" means bumping a thread-safe counter up for each child — and then, when the sub-piece is thrown away a moment later, bumping each counter back down. That's two atomic operations per child that accomplish exactly nothing, on the parser's hottest path. The fix would be a "take, don't copy" variant (`extend_children_owned`) that moves the children over wholesale — a plain memory move, no counter traffic.

The validation pass confirmed everything, including the scary question: could the sub-piece secretly be shared with the memoization cache (in which case stealing its children would be wrong)? **No** — definitively. Sub-pieces at these call sites are plain values that never enter the cache; they are uniquely owned at every call site. The optimization is mechanically safe.

It also found the TODO's "blocked on gsm2tree_rs.py" framing is overstated — both generators live in this repo; it's just a coordinated two-file change in one commit, not an external dependency.

### Why it matters

Wasted atomic ref-count traffic per child node, per parse, on the hot path. The win is real and provably ≥ 0. But **nobody has measured it**: there is no benchmark harness or profiling data anywhere in the repo. Atomic increments on uncontended counters are cheap; this could be anywhere from "measurable speedup" to "lost in the noise."

### What the work actually looks like

Add `extend_children_owned(other: Self)` (using `Vec::append`) to the generated node `impl` in `gsm2tree_rs.py`, switch the two call sites in `gsm2parser_rs.py` to use it, regenerate fixtures, update the `.pyi`/protocol surface. Additive to the generated public API (new method — not a breaking change per CLAUDE.md rules). Mechanical, maybe a half-day with the review chain.

### The case for skipping

The TODO's own author wrote the policy into the entry: **"Re-open only with profiling evidence."** That evidence doesn't exist — there's no benchmark to even produce it. Doing this now is optimizing blind; you'd land a change whose benefit you can't state, and the precedent ("we do unmeasured micro-optimizations") is worse than the atomic ops.

### Recommendation: **Blocked**

Blocked on its own stated re-open condition: profiling/benchmark evidence that this Arc traffic matters. Concretely, the blocker is that no parser benchmark harness exists in-tree; until one exists and shows this path on a profile, the TODO stays parked. (If you'd rather just do it because it's provably safe and strictly non-negative, that's defensible — but the recommendation is to honor the profiling gate.)

---

## Summary

| Slug | Recommendation |
|------|----------------|
| `empty-cn-underscore-rule` | **Do** — reframed: empty-CN check for rule names AND labels, + Python-backend friendly error |
| `extend-children-owned` | **Blocked** — on profiling evidence (no benchmark harness exists); TODO's own re-open condition unmet |
| `bazel-rules-rust` | Skipped per user instruction |
| `example-placeholder` | Not a TODO (placeholder by design) |
