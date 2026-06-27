# Dispositions — deep review, round 1

Scope: `crates/fltk-unparser-core/src/{doc,accumulator,resolve}.rs` (batch 1).
All 64 crate tests pass; `cargo clippy` and `cargo fmt --check` clean.

`notes-deep-errhandling-r1.md` and `notes-deep-security-r1.md` reported no findings;
nothing to dispose there.

---

correctness-1:
- Disposition: Fixed
- Action: `crates/fltk-unparser-core/src/doc.rs` — removed the `thread_local! { DROP_SENTINEL }`
  block and changed `take_children` (the `Group`/`Nest`/`AfterSpec`/`BeforeSpec` and
  `Join.separator` arms) to swap single-child slots with `std::mem::replace(content,
  Rc::new(Doc::Nil))` instead of cloning the TLS sentinel. Comment added explaining the
  TLS-teardown panic hazard and the no-TLS-in-drop CST precedent.
- Severity assessment: Real but low-likelihood: a `Doc` dropped during thread-local
  destruction ordering after `DROP_SENTINEL` is gone would make `LocalKey::with` panic,
  and a panic out of `drop` mid-unwind aborts the process. No in-crate trigger, but the
  fix is trivial and removes the window entirely.

test-1:
- Disposition: Fixed
- Action: `resolve.rs` test `text_newline_before_separator_becomes_hardline` —
  `Text("\n") + SeparatorSpec(spacing=Some(_))` resolves to `HardLine{0}`.
- Severity assessment: `mutate_text_newline` was entirely unexercised; a wrong field/string
  comparison would have gone undetected.

test-2:
- Disposition: Fixed
- Action: `resolve.rs` — ported the four missing `_extract_boundary_specs` edge cases
  (`extract_boundary_specs_only_leading`/`_only_trailing`/`_all_specs`/`_empty_list`).
- Severity assessment: Only-leading, all-specs, and empty paths of `extract_boundary_specs`
  were uncovered — exactly the boundaries the linearization fix (quality-2) touches.

test-3:
- Disposition: Fixed
- Action: `resolve.rs` `#[should_panic]` test `separator_without_trivia_or_spacing_in_triple_panics`
  driving an `After/Sep(None,None)/Before` triple through `resolve_spacing`.
- Severity assessment: The "neither preserved trivia nor spacing" assert (the only guard
  against silent output corruption for a malformed triple) had no test.

test-4:
- Disposition: Fixed
- Action: `accumulator.rs` `#[should_panic(expected = "Expected Nest")]` test
  `pop_nest_rejects_wrong_nesting`.
- Severity assessment: The `pop_nest` wrong-nesting guard (symmetric to the tested
  `pop_group`/`pop_join` cases) was the only one unverified.

test-5:
- Disposition: Fixed
- Action: `resolve.rs` — ported all eight multi-level / consecutive-spec extraction tests
  from `test_resolve_specs.py` (`nested_group_nest_extraction`, `multiple_nested_groups`,
  `complex_multilevel_extraction`, `empty_group_with_specs`, `consecutive_groups_with_specs`,
  `deeply_nested_empty_structures`, `consecutive_specs_inside_group`,
  `consecutive_leading_specs_in_group`). All pass against the existing port.
- Severity assessment: These cover the subtle pass-ordering interactions (boundary
  extraction × consecutive-spec merging) most likely to re-regress; `consecutive_leading_specs_in_group`
  is the original regression target. They pass, confirming the port is faithful here.

test-6:
- Disposition: Fixed
- Action: `resolve.rs` test `separator_hardline_blank_lines_win_over_after_spec` —
  `sep(Some(hardline(2)))` beats a flanking `after(line())`.
- Severity assessment: The `pick_spacing_with_blank_lines` "separator HardLine wins" branch
  was unexercised; a wrong comparison would silently emit fewer blank lines.

test-7:
- Disposition: Won't-Do
- Action: no change (`accumulator.rs` `add_trivia_sets_flag` kept).
- Severity assessment: Style/brittleness only — no behavioral risk.
- Rationale: Same-module access to a private field is the idiomatic purpose of Rust's
  in-module `#[cfg(test)] mod tests`; this is not improper coupling. The test uniquely
  covers `add_non_trivia` *clearing* the flag — `pop_propagates_trivia_state_to_parent`
  only exercises `add_trivia` then `pop`, so deleting `add_trivia_sets_flag` would drop
  direct coverage of the `add_non_trivia` reset, and `last_was_trivia` is not observable
  through the rendered `Doc` by any other means (the only alternative is an equally
  white-box read after a `pop`). The brittleness cost (one assertion if the field type
  ever changes) is negligible versus the lost coverage, so removing it would mildly harm
  the suite for no real benefit.

test-8:
- Disposition: Fixed
- Action: `doc.rs` — added `deep_nest_chain_drops_without_stack_overflow`,
  `deep_afterspec_chain_drops_without_stack_overflow`,
  `deep_beforespec_chain_drops_without_stack_overflow` (200k deep, mirroring the existing
  group/concat/join cases).
- Severity assessment: The single-child `take_children` arm (shared by Nest/AfterSpec/
  BeforeSpec) was only verified via `Group`; a future refactor bypassing that arm for the
  others would have gone uncaught (uncatchable stack overflow).

reuse-1:
- Disposition: Won't-Do
- Action: no change (`doc::concat` and `resolve::concat_rc` kept separate).
- Severity assessment: Low — both are tiny, carry bidirectional doc-comment references,
  and are pinned together by the comprehensive cross-backend parity suite.
- Rationale: Unifying would pessimize a public-API hot path. `concat` (called per
  rule/level via `DocAccumulator::doc()` over the whole CST) moves nested-`Concat`
  children out via `&mut` (`flattened.append(inner)`); routing it through the `Rc`-based
  `concat_rc` would instead clone each child `Rc` (`inner.iter().cloned()`) and wrap/drop
  a temporary `Rc` for every `Nil` element — net per-unparse refcount churn on the hottest
  path. The two functions also differ irreducibly in element/return type (`Doc` for
  generated callers vs `Rc<Doc>` for internal sharing), so a shared body needs generics
  for no behavioral gain. The divergence risk the finding describes is already controlled
  by the cross-references and parity tests, so I won't trade a real hot-path cost for it.

reuse-2:
- Disposition: Fixed
- Action: `resolve.rs` test module — replaced the four redefined helpers with
  `use crate::doc::{hardline, line, nil, softline, text};`.
- Severity assessment: Low (test-only); removes silent-divergence risk if a constructor's
  signature changes in `doc.rs`.

quality-1:
- Disposition: Fixed
- Action: `resolve.rs:39` — `resolve_spacing_specs` now takes `Doc` by value;
  `Rc::new(doc)` replaces `Rc::new(doc.clone())`. In-crate call sites updated (drop `&`).
  Deviation from design §2.1 recorded in `implementation-log.md` (Review round — deep r1).
- Severity assessment: Real per-unparse cost — the old signature transiently doubled the
  Doc tree (full deep clone) on the hot path that runs once per top-level unparse, scaling
  with source size. Owning the input eliminates it.

quality-2:
- Disposition: Fixed
- Action: `resolve.rs` `extract_boundary_specs` — trailing run popped from the end +
  one `reverse()`; leading run taken via `take_while().count()` + `drain(..k)`. Behavior
  byte-identical (covered by test-2's new edge cases). Deviation from the "literal port"
  framing noted in the log.
- Severity assessment: O(n²) front-shifting on Concat levels with many consecutive trivia
  regions (the normal comment-preserving case); now linear. Parity tests wouldn't catch
  the slowdown because CPython's own `pop(0)` overhead masks it.

efficiency-1:
- Disposition: Fixed
- Action: `accumulator.rs` `doc()` — chain walked by borrow (`&self.head` / `&node.tail`);
  only `node.doc` is cloned.
- Severity assessment: ~2N refcount bump/drop pairs per call removed on a hot path
  (`doc()` runs per `add_accumulator`/`pop`/`pop_join`), N = items at the nesting level.

efficiency-2:
- Disposition: TODO(unparser-join-sep-resolve)
- Action: `TODO(unparser-join-sep-resolve)` comment at `resolve.rs` `expand_joins`
  (the `Some(separator.clone())` site) + matching entry in `TODO.md`.
- Severity assessment: A `Join` separator is resolved M-1 times (once per gap) with
  byte-identical results; cost scales with join length. Bounded today because the
  generator rejects group/nest/join separators, so each redundant run is small — hence
  deferred rather than fixed in this batch.

efficiency-3:
- Disposition: Fixed
- Action: Same change as quality-2 (`extract_boundary_specs` front-shift removal).
- Severity assessment: See quality-2 — identical finding from the efficiency lens.

efficiency-4:
- Disposition: Fixed
- Action: Same change as quality-1 (`resolve_spacing_specs` takes `Doc` by value; the
  wasted top-node clone is gone).
- Severity assessment: See quality-1 — identical finding; the entry clone of the top node
  (O(W) for a width-W top Concat) was discarded immediately by `expand_joins`.
