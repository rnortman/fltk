# Judge verdict — deep review, cst-named-mutators, round 2

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Phase: deep. Base dd52073..HEAD 46c5dfe (rework commit 46c5dfe on top of round-1 state 47306b5). Round 2 — APPROVED or ESCALATE only.
Scope: round-1 verdict (`judge-verdict-deep.md`) disputed four items: reuse-1, reuse-2, efficiency-4 (TODO dispositions failing rubric Q2 — do-now), and quality-4 (false leftover comment). All other 23 findings were accepted in round 1 and are not re-walked.
Verification: read rework diff `47306b5..46c5dfe` in full (generators, regenerated artifacts, TODO.md); inspected current generator source; ran `tests/test_cst_mutators_parity.py`, `tests/test_cst_mutators_identity.py`, `tests/test_gsm2tree_py.py`, `tests/test_gsm2tree_rs.py` — 346 passed. Working tree clean for all reviewed paths at HEAD.

## Disputed-items walk

### reuse-1 — was TODO(mutator-rs-resolve-index-dedup), now Fixed
Round-1 requirement: extract the resolve-index block now, remove the TODO.
Code: `_emit_resolve_index_stmts()` static method added at `gsm2tree_rs.py:1289-1311`; both `_generic_remove_at` and `_generic_replace_at` splice it via `*self._emit_resolve_index_stmts()`. TODO comment removed from the `_generic_remove_at` docstring; `TODO.md` entry removed; `grep` confirms no `mutator-rs-resolve-index-dedup` slug remains anywhere outside this ADR dir. The rework diff touches **no** generated `.rs` file — extraction is byte-identical output, exactly the round-1 verdict's acceptance criterion.
Assessment: accept.

### reuse-2 — was TODO(mutator-py-bounds-check-dedup), now Fixed
Round-1 requirement: same, Python side.
Code: `_emit_bounds_check_stmts(method_name)` inner function added inside `_emit_py_mutators` (`gsm2tree.py:554-570`); `remove_fn` and `replace_fn` both call it, each followed only by its diverging final statement (`pop` vs slice assignment). The shared block carries `method_name` into the pinned `IndexError` format — the single-edit-point goal of the finding. TODO comment and `TODO.md` entry removed; no stale slug anywhere. Regenerated Python artifacts (`fltk_cst.py`, `bootstrap_cst.py`, `toy_cst.py`, `unparsefmt_cst.py`) show semantically identical emitted bodies.
Assessment: accept.

### efficiency-4 — was TODO(mutator-py-cache-allowed-types), now Fixed
Round-1 requirement: memoized native-span lookup + hoisted tuple, now.
Code: `_emit_py_mutators` emits `_MUTATOR_ALLOWED_CHILD_TYPES = None` as a plain (unannotated) class-body assignment — correctly invisible to `dataclasses`. `_check_child_type_for_mutators` lazily initialises it to the static tuple on first call and memoises; native Span is appended once on first sighting of `fltk._native` (`if _ns is not None and _ns not in _allowed` — never unloads, positive memoisation sound). Generated form verified at `fltk_cst.py` (`Items`, `Disposition`). After warm-up the hot path is one class-attr read + the `_get_native_span_type()` call that exits via the memoised branch. TODO comment and `TODO.md` entry removed; tests pass.
Residual: the reviewer's finding had a second bullet — multi-type non-span classes still evaluate `isinstance(child, A | B)` per call, constructing a fresh `types.UnionType` (`gsm2tree.py:477-486`; e.g. generated `fltk_cst.py` `Rule._check_child_type_for_mutators`). Not addressed by the rework. Severity: one small allocation per call on the interpreter-bound backend; the reviewer's own framing of the whole finding was "minor", and the dominant cost (per-call tuple build + `sys.modules` probe on span-typed classes) is eliminated. Nit-grade residual; does not invalidate the Fixed disposition and does not warrant arbitration.
Assessment: accept, residual noted.

### quality-4 — Won't-Do (comment corrected)
Round-1 requirement: delete or correct the false "no explicit clamping is needed" comment.
Code: comment at `gsm2tree.py:527-530` now reads "Explicit clamping is required: CPython's list.insert raises OverflowError for indices beyond ssize_t (e.g. 10**25), so we clamp after operator.index to match Rust's behaviour for arbitrarily-large ints (§3, pinned by test_insert_clamp_large_positive)." Accurate (round-1 verdict empirically confirmed the `OverflowError`), consistent with the retained clamp and with the Won't-Do rationale. The Won't-Do itself was already accepted in round 1.
Assessment: accept.

## Notes (no action required for this verdict)

- **Nondeterministic union/tuple member ordering in generated Python output.** `ItemsModel.types` is a `set` (`gsm2tree.py:25`); `unique_classes` preserves set-iteration order, which is hash-randomized across interpreter runs. Observable: the rework regen reordered members with no emitter-logic change (`fltk_cst.py:107` `Trivia | Rule` → `Rule | Trivia`, et al.). Functionally harmless (isinstance is order-insensitive; parity unaffected) but causes spurious regen diffs and makes any regen-diff gate flaky. Introduced by this iteration's mutator emission; no reviewer finding covers it, so it is outside this adjudication — recommend a follow-up (sort `unique_classes` deterministically) outside this review.

## Approved

All 4 round-1 disputed items resolved: 3 former TODOs done now and de-listed (reuse-1, reuse-2, efficiency-4 with nit residual), quality-4 comment corrected. Combined with round 1: 27 findings — 24 Fixed verified, 1 Won't-Do sound, 2 TODOs acceptable (errhandling-4, efficiency-3). 346 tests pass at HEAD.

---

## Verdict: APPROVED

Round 2. All dispositions acceptable; rework verified against code, regenerated artifacts, and tests at 46c5dfe.
