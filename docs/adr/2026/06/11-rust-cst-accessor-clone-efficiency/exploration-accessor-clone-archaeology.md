Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

# Archaeology: `rust-cst-accessor-clone-efficiency` vs. `rust-idiomatic-cst-api` work

## Question

Did the `rust-idiomatic-cst-api` work (commits `7e39dfb`..`5d05d7f`, branch
`rust-idiomatic-cst-api`, ADR at `docs/adr/2026/06/10-rust-idiomatic-cst-api/`) claim to fix
the accessor clone-efficiency problem? If so, what exactly was fixed, what was not, and was the
remaining gap recorded or silently dropped?

---

## Timeline of facts

### Commit `7e39dfb` — Phase 1: handle/data split (2026-06-10)

**Introduced** the TODO. The commit message explicitly states:

> Resolves TODO(rust-cst-child-node-identity); adds TODO(rust-cst-accessor-clone-efficiency)
> tied to the benchmark gate.

`TODO.md` diff at this commit: added the `rust-cst-accessor-clone-efficiency` entry with text
"Deferred pending the §6 item 8 benchmark gate results".

`gsm2tree_rs.py` diff at this commit: introduced **four** `TODO(rust-cst-accessor-clone-efficiency)`
code comments into the generator. All four are in `_per_label_methods` (the `#[pymethods]` block
emitter) and `_generic_child` (the generic Python-callable `child()` method):
- `gsm2tree_rs.py:532` — `_generic_child`, `child()` pymethod snapshot
- `gsm2tree_rs.py:584` — `_per_label_methods`, `children_<label>` pymethod snapshot
- `gsm2tree_rs.py:603` — `_per_label_methods`, `child_<label>` pymethod snapshot
- `gsm2tree_rs.py:621` — `_per_label_methods`, `maybe_<label>` pymethod snapshot

At this point there were **no** native (GIL-free) per-label accessor methods — those were introduced
in Phase 2. The TODO was scoped entirely to pymethods.

The design doc (`design.md:218`) simultaneously mandated the snapshot pattern for pymethods:
> "never construct or call Python objects while holding a node lock — **snapshot what is needed
> (Arc clones of children, `Span` clone)**, drop the guard, then build Python objects"

So the snapshot in pymethods was not an oversight — it was the prescribed lock-discipline pattern
to prevent GIL↔lock deadlocks. The TODO tracks doing it more efficiently (filter inside guard
rather than cloning the full Vec), not eliminating the snapshot.

---

### `design.md` §6 item 8 — benchmark gate

`design.md:499-501`:
> "8. **Benchmark sanity** (informational gate, spike crate): build + traverse micro-benchmark
> before/after the `Box`→`Shared` switch; expectation is uncontended-lock overhead within the
> same order of magnitude. A surprising regression reopens the parking_lot question (§5) before
> Phase 2 builds on the new ownership."

The benchmark gate was about the `Box`→`Shared<T>` lock-overhead regression check — not about
the accessor clone efficiency. The TODO's "deferred pending §6 item 8" language meant: confirm
the RwLock overhead is acceptable before investing in optimizing the accessors that sit on top
of it. If the benchmark gate had failed (regression too large), the parking_lot alternative
would be revisited, potentially changing the whole accessor shape.

---

### Commit `5d05d7f` — Phase 2: idiomatic Rust accessor surface + CstError (2026-06-10)

This commit introduced `_native_per_label_methods` — a **new** generator function producing GIL-free
native Rust accessors (`child_<lbl>`, `maybe_<lbl>`, `children_<lbl>`, `append_<lbl>`, `extend_<lbl>`)
on the data struct directly (no `#[pymethods]`, no `py: Python<'_>` parameter).

The **initial** implementation of these native methods in this commit used the allocating `Vec`
snapshot pattern — same as the pymethods. This was caught by the deep efficiency reviewer
(`notes-deep-efficiency-reviewer.md:6-26`, finding `efficiency-1`), who noted the native methods
allocated a temporary `Vec` per call via `let matching: Vec<_> = ...collect()`, while the
union-label branches of the same function already used the zero-alloc `(it.next(), it.next())`
pattern. The reviewer also noted (`notes-deep-efficiency-reviewer.md:20-21`):

> "The existing `rust-cst-accessor-clone-efficiency` TODO covers only the pymethod (handle)
> side — this new native-side allocation is untracked."

The deep-review disposition `efficiency-1 (Phase 2)` (`dispositions-deep.md:341-345`) recorded
a **fix** for the native side:

> "Action: `fltk/fegen/gsm2tree_rs.py` `_native_per_label_methods` — replaced
> `let matching: Vec<_> = ...collect()` in `child_<lbl>` and `maybe_<lbl>` for single-node and
> span-typed label branches with the alloc-free `let mut it = ...; match (it.next(), it.next())`
> pattern. Recount via `filter().count()` on error path only. Regenerated all five outputs."

The `reuse-8 (Phase 2)` disposition (`dispositions-deep.md:323-327`) records:

> "Action: The `TODO(rust-cst-accessor-clone-efficiency)` scope concern is moot: `child_<lbl>`
> and `maybe_<lbl>` native methods now use zero-alloc iterator match (efficiency-1 fix). No
> allocation to annotate."

The prepass disposition `scope-1` (`dispositions-prepass.md:24-26`) records the benchmark result:

> "Ran release build benchmark 2026-06-10 (x86_64 Linux): traverse/256 ~2.0 µs (~7.9 ns/child
> uncontended RwLock read). Gate verdict PASSED — ~8 ns per read is within the same order of
> magnitude as a Box deref. parking_lot contingency not triggered.
> `rust-cst-accessor-clone-efficiency` TODO updated to remove the 'pending §6 item 8' blocker
> language."

`TODO.md` at `5d05d7f` reflects this: the entry's deferral reason changed from "pending §6 item 8"
to "The §6 item 8 benchmark (gate passed 2026-06-10) measured ~8 ns per uncontended read; fixing
this accessor inefficiency is an independent cleanup not blocked by the gate result."

---

## What was fixed vs. what remained

### Fixed in Phase 2 (commit `5d05d7f` + deep-review fix commits)

Native (GIL-free) per-label accessors in `_native_per_label_methods`:
- `child_<lbl>` for single-node and span branches: zero-alloc `(it.next(), it.next())` pattern.
  `gsm2tree_rs.py:1158-1176` (single-node), `1179-1197` (span).
- `maybe_<lbl>` for single-node and span branches: same zero-alloc pattern.
  `gsm2tree_rs.py:1226-1249` (single-node), `1253-1276` (span).
- `children_<lbl>` was already lazy/zero-alloc by design (returns an iterator over `self.children`,
  no snapshot). `gsm2tree_rs.py:1106-1119` (single-node), `1127-1138` (span), `1142-1146` (union).
- Union-label `child_<lbl>` and `maybe_<lbl>`: also zero-alloc.

The `rust-cst-accessor-clone-efficiency` TODO was **not** annotated on the native methods because
it did not apply after the efficiency-1 fix.

### NOT fixed — remained open after all Phase 1+2 work

Python-callable pymethods in `_per_label_methods` (`#[pymethods]` block):
- `children_<label>`: `gsm2tree_rs.py:1387-1404` still uses full-Vec snapshot + filter outside guard.
- `child_<label>`: `gsm2tree_rs.py:1410-1435` still uses full-Vec snapshot + iterate to find.
- `maybe_<label>`: `gsm2tree_rs.py:1440-1459` still uses full-Vec snapshot + iterate to find.
- Generic `child()` pymethod (`_generic_child`): `gsm2tree_rs.py:1011-1036` still snapshots full Vec.

All four locations carry `TODO(rust-cst-accessor-clone-efficiency)` comments in the current
working tree.

The design mandate (`design.md:218`) requires a snapshot before Python calls while holding no
guard, which is why these methods still snapshot. The TODO tracks doing the snapshot more
efficiently — filter inside the guard (clone only matching entries) rather than cloning the full
Vec unconditionally. The full-Vec clone is O(total-children) Arc/Span/label clones per call
regardless of how many match.

---

## Was this gap recorded or silently dropped?

**Recorded.** The distinction between native and pymethod sides is explicit:

1. The efficiency reviewer (`notes-deep-efficiency-reviewer.md:20-21`) explicitly noted the scope
   gap: the existing TODO covered pymethods only; the native side was separately fixed by
   efficiency-1.

2. The reuse-8 disposition (`dispositions-deep.md:325-327`) states the TODO's native-side scope
   concern is "moot" (because efficiency-1 fixed it), implicitly confirming the TODO remains for
   the pymethod side.

3. `TODO.md` at HEAD still carries the entry pointing to `_generic_child` and `_per_label_methods`
   — the pymethod emitters — not the native emitters.

4. The benchmark gate (scope-1) removed the "blocked" language from the TODO but did not close it.

---

## Summary

| Artifact | State after Phase 1+2 | Evidence |
|---|---|---|
| Native `child_<lbl>` / `maybe_<lbl>` | Zero-alloc iterator match | `gsm2tree_rs.py:1158-1276`; dispositions-deep.md efficiency-1 |
| Native `children_<lbl>` | Always was lazy iterator, zero-alloc | `gsm2tree_rs.py:1106-1146` |
| Pymethod `children_<label>` | Still full-Vec snapshot | `gsm2tree_rs.py:1387-1404`; TODO comment line 1388 |
| Pymethod `child_<label>` | Still full-Vec snapshot | `gsm2tree_rs.py:1410-1435`; TODO comment line 1411 |
| Pymethod `maybe_<label>` | Still full-Vec snapshot | `gsm2tree_rs.py:1440-1459`; TODO comment line 1441 |
| Generic `child()` pymethod | Still full-Vec snapshot | `gsm2tree_rs.py:1011-1036`; TODO comment line 1014 |
| TODO.md entry | Remains open; blocker language removed | TODO.md:27-29 |

The `rust-idiomatic-cst-api` work fixed the **native** side as a side-effect of Phase 2's
deep review (efficiency-1 disposition). It did not fix the **pymethod** side. This was deliberate:
the pymethod snapshot is architecturally required by the lock-discipline rule (design.md:217-219),
and the TODO tracks a more granular snapshot (filter-inside-guard), not elimination of the snapshot.
The gap between native (fixed) and pymethod (not fixed) is documented in dispositions-deep.md and
in the current TODO.md entry. No part of this was silently dropped.
