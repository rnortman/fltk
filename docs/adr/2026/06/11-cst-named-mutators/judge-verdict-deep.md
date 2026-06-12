# Judge verdict — deep review, cst-named-mutators

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Phase: deep. Base dd52073..HEAD 47306b5 (review at f904540, fixes at c51eab1). Round 1.
Notes: 7 reviewer files (security: no findings); 27 findings; 5 TODO dispositions, 21 Fixed, 1 Won't-Do.
Verification: full read of generators + fix diff; spot-checked regenerated artifacts (no stale `call_method0("__index__")` anywhere); ran `tests/test_cst_mutators_parity.py`, `tests/test_cst_mutators_identity.py`, `tests/test_gsm2tree_py.py`, `tests/test_gsm2tree_rs.py` — 346 passed (the tightened TypeError-only and message-parity tests pass against the built extension, so the binary reflects the fixes).

## Added TODOs walk

### errhandling-4 — TODO(mutator-remove-at-oob-atomicity) at gsm2tree_rs.py:1294
Q1 (worth doing): yes — documented atomicity-contract violation (`remove_at` mutates then errors on `to_pyobject` failure), though the trigger is OOM-only.
Q2 (design/owner input required): yes — two candidate strategies (clone-Arc + wrap-out-before-remove vs remove + re-insert-on-failure) carry per-call cost / second-lock tradeoffs on a hot path; choosing one is a design call, and whether the atomicity contract under OOM matters at all is plausibly an owner call.
This-iteration-created rule: satisfied — not silent (code comment + TODO.md:44 + disposition), and it passes Q2.
Assessment: TODO acceptable.

### reuse-1 — TODO(mutator-rs-resolve-index-dedup) at gsm2tree_rs.py:1296
Q1: yes — the resolve-index block carries the pinned error-message format; divergence between the two copies is a real risk (parity tests catch it only at runtime).
Q2: no — the fix is fully specified by the reviewer and by the TODO.md entry itself: extract `_emit_resolve_index_stmts(class_name, method_name)`, call from both emitters. Generator-internal refactor; correct extraction yields byte-identical generated output, verified by `make check`'s regen-diff. No design choice, no owner input.
Assessment: Q2 fails → do-now. Disposition wrong. The responder's rationale ("maintenance cost") never claims design work is required.

### reuse-2 — TODO(mutator-py-bounds-check-dedup) at gsm2tree.py:535
Q1: yes — same parity-message duplication risk, Python side.
Q2: no — identical shape to reuse-1: a helper emitter method producing the shared `operator.index`/bounds-check/`IndexError` block, byte-identical output. Mechanical.
Assessment: Q2 fails → do-now. Disposition wrong.

### efficiency-3 — TODO(mutator-rs-fast-path-int-index) at gsm2tree_rs.py:1234,1298
Q1: yes-ish — fixed per-call Python dispatch (import+getattr+call) on the hot rewrite path; reviewer concedes it is "practically bounded by Python interpreter overhead anyway."
Q2: yes — a fast path on the index-normalization code must re-prove semantic equivalence with `operator.index` across int subclasses, bool, evil `__index__`, and the `orig_str` error-message contract — exactly the parity surface where this review found three live bugs (correctness-3, correctness-4, errhandling-2). Note `index.extract::<i64>()` on the original object goes through `PyLong_AsLongLong`, which itself can invoke `__index__` — the "fast" path is not trivially semantics-free. A design pass is warranted before touching freshly-debugged pinned-contract code for marginal gain.
Assessment: TODO acceptable.

### efficiency-4 — TODO(mutator-py-cache-allowed-types) at gsm2tree.py:427
Q1: yes — per-call tuple construction + `sys.modules` probe on every Python-backend `insert`/`replace_at`; real, minor.
Q2: no — the reviewer's finding fully resolves the only judgment call: memoize the native-span lookup positively (`fltk._native` never unloads) and hoist the static tuple; laziness/§2.2 importability is preserved per the finding. The remaining wrinkle (class-definition ordering forces lazy first-call caching rather than a class-body constant) is implementation detail, not design. Responder's own rationale is "Deferred as polish" — the rubric's prohibited "not now."
Assessment: Q2 fails → do-now. Disposition wrong.

## Other findings walk

### errhandling-1 — Fixed
Claim: Python child-type message adds `.{method}` that Rust lacks; design §2.2 pins Rust's text.
Code: `gsm2tree.py:441,452,464` now emit `"{class_name}: unsupported child type {type}"`; `method` param removed from `_check_child_type_for_mutators` signature and call sites. `TestMessageParity.test_bad_child_type_insert_message_parity` asserts `py_msg == emb_msg`; passes.
Assessment: accept.

### errhandling-2 — Fixed
Claim: Rust `call_method0("__index__")` raises `AttributeError` for non-indexables; Python `operator.index` raises `TypeError`; "type pinned" violated.
Code: all three Rust pymethods now route through `py.import("operator")?.getattr("index")?.call1((index,))` (gsm2tree_rs.py:1252-1255 et al.; generated `src/cst_fegen.rs:712,750,818`). `test_non_index_*` tightened to `pytest.raises(TypeError)`; pass on both backends.
Assessment: accept.

### errhandling-3 — Fixed
Claim: validation order diverges (Python index→label→child vs Rust child→label→index), contradicting design §3.
Code: Python `insert`/`replace_at` reordered to child → label → index (gsm2tree.py emitted bodies). `test_bad_child_wins_over_bad_label_insert/_replace_at` added, parametrized over both backends, assert the child message wins; pass.
Assessment: accept.

### correctness-1 — Fixed
Claim: TOCTOU in Rust `insert` — clamp under one write guard, `Vec::insert` under a second.
Code: `_generic_insert` now computes `is_negative_big`/`raw_i64` before any lock, then one `self.inner.write()` scope covers len-read + clamp + `Vec::insert`. Guarded region is pure Rust.
Assessment: accept.

### correctness-2 — Fixed
Claim: TOCTOU in `remove_at`/`replace_at` — bounds check under read lock, mutation under later write lock.
Code: both use a single write lock for resolve + bounds-check + `Vec::remove`/`mem::replace`. `remove_at` carries `n` out via `Result<_, usize>` and formats the `IndexError` after guard release; `replace_at` constructs the error inside the guard scope but from pure-Rust values (`orig_str` String + `n`; PyO3 `new_err` is lazy — exception materializes after the trampoline, guard already dropped). No Python work under either guard.
Assessment: accept.

### correctness-3 — Fixed (with errhandling-2)
Claim: non-`int` `__index__` return silently clamps in `insert` / raises `IndexError` in `remove_at`/`replace_at` where `TypeError` is pinned.
Code: `operator.index` raises `TypeError` for non-int `__index__` returns per CPython semantics; routed before any lock.
Assessment: accept.

### correctness-4 — Fixed
Claim: Rust `IndexError` formats `raw_idx.str()` (normalized) instead of the caller's original.
Code: `orig_str = index.str()?` captured before normalization in both `remove_at` and `replace_at` (generated `src/cst_fegen.rs:745,814`) and used in the error format. No bool-index message-parity test was added (reviewer noted the matrix uses plain ints), but the finding's "what must change" is fully implemented.
Assessment: accept.

### correctness-5 — Fixed (same as errhandling-3). Accept.

### correctness-6 — Fixed
Claim: Python label-error message uses dynamic `type(self).__name__`, naming nonexistent `{Subclass}_Label` for downstream subclasses and diverging from Rust's static text.
Code: `_cn = "{class_name}"` static literal at gsm2tree.py:485.
Assessment: accept.

### correctness-7 — Fixed (subsumed by correctness-1/2/3)
Claim: Python calls (`raw_idx.lt(0i64)`, `extract` reachable via `__index__`) under the lock; same-thread deadlock path.
Code: `lt` and all extraction now precede any lock acquisition in all three methods; `raw_idx` is the `operator.index` result (guaranteed exact int), so `extract::<i64>` is C-level. Guarded regions are pure Rust.
Assessment: accept.

### test-1 — Fixed. `test_bad_child_type_insert_message_parity` added; passes. Accept.

### test-2 — Fixed
Claim: "no labels defined" path entirely untested; fix asked for both backends.
Code: `TestLabelFreeNodeErrors` added — two tests against a dynamically-compiled label-free `Foo` (Python backend only). Verified no compiled Rust fixture contains a label-free node (`grep "no labels defined"` across all generated `.rs`: zero hits), so exercising the Rust runtime path would require a new compiled fixture grammar — infrastructure work beyond this finding's scope; the limitation is documented in the test class docstring, and the Rust emission text is generator-controlled.
Assessment: accept — Python-only runtime coverage is the cheapest available test; remaining Rust-runtime gap is noted, not blocking.

### test-3 — Fixed (with errhandling-2). Tests tightened to `TypeError` only; pass against built extension (proving option B, not the doc-only option A). Accept.

### test-4 — Fixed. `TestMixedOpsNodeChildren` added: insert/remove_at/replace_at/clear on `Alternatives` with node-typed `Items` children, both backends, label-sequence parity. Covers the flagged gap. Accept.

### test-5 — Fixed. `test_remove_at_then_drop_evicts_registry_entry` added, mirrors the `clear` eviction test (discard return value, drop handle, GC, assert registry eviction). Accept.

### test-6 — Fixed. `test_replace_at_large_negative_out_of_range` with `big = -(10**25)`, exact-message assertion. Accept.

### quality-1 — Fixed (subsumed by correctness-1/7). `lt` call outside all locks. Accept.

### quality-2 — Fixed (same as errhandling-3). Accept.

### quality-3 — Fixed (same as errhandling-1). Accept.

### quality-4 — Won't-Do
Claim: explicit Python-side clamping in `insert` is redundant; `list.insert` clamps natively.
Rationale: the design's "CPython gives clamping for free" is false for beyond-`ssize_t` ints — `list.insert` raises `OverflowError`; removal was attempted and reverted (`test_insert_clamp_large_positive` fails).
Verification: empirically confirmed — `[1,2].insert(10**25, 3)` raises `OverflowError: Python int too large to convert to C ssize_t`. The reviewer's premise (and design §2.4's claim) is false; the clamp is load-bearing for the §3 pinned beyond-`i64` behavior.
Assessment: Won't-Do correct — finding's premise is wrong. **However**, the fix commit added a comment at gsm2tree.py:508-511 asserting the opposite: "CPython's list.insert handles all index clamping natively (negative, out-of-range, beyond-i64), so no explicit clamping is needed after operator.index normalization" — directly above retained clamping code. This is a leftover from the attempted-and-reverted removal, contradicts both the code beneath it and this Won't-Do's own rationale, and invites a future maintainer to delete the load-bearing clamp. Incomplete revert; flagged in Disputed.

### efficiency-1 — Fixed (subsumed by correctness-1). One write lock per `insert`. Accept.

### efficiency-2 — Fixed (subsumed by correctness-2). One write lock per `remove_at`/`replace_at`. Accept.

(Note, no action required: the fix introduces an unconditional `index.str()` per `remove_at`/`replace_at` call — happy path included — to satisfy the format-after-lock constraint. Defensible tradeoff; post-dates the reviews; nit at most.)

## Disputed items

1. **reuse-1 / TODO(mutator-rs-resolve-index-dedup)** — fails rubric Q2: mechanical generator-internal extraction, fully specified, byte-identical output. Do it now and remove the TODO, or state specifically what design decision blocks it.
2. **reuse-2 / TODO(mutator-py-bounds-check-dedup)** — same: do it now or justify as design work.
3. **efficiency-4 / TODO(mutator-py-cache-allowed-types)** — fails rubric Q2: the reviewer's finding resolves the laziness question; remaining work is mechanical (memoized lookup + hoisted tuple, regen, `make fix`). "Deferred as polish" is the rationale the rubric rejects. Do it now or justify as design work.
4. **quality-4 (comment only)** — delete or correct the false comment at `fltk/fegen/gsm2tree.py:508-511` ("no explicit clamping is needed"); it contradicts the retained clamp and the Won't-Do rationale. The Won't-Do itself stands.

## Approved

23 of 27 findings fully accepted: 21 Fixed verified (code + tests inspected; 346 tests pass), 2 TODOs acceptable (errhandling-4, efficiency-3). quality-4's Won't-Do is sound on the merits (disputed only for the leftover contradictory comment).

---

## Verdict: REWORK

Three TODO dispositions fail the acceptability rubric (do-now items: reuse-1, reuse-2, efficiency-4) and quality-4's fix pass left a comment contradicting its own Won't-Do rationale. Round 1.
