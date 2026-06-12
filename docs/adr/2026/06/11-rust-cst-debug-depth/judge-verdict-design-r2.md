# Judge verdict — design review r2

Phase: design (doc). Doc: `docs/adr/2026/06/11-rust-cst-debug-depth/design.md`. Round 1 (re-review of revised design).
Notes: `notes-design-design-reviewer-r2.md` (2 findings). Dispositions: `dispositions-design-r2.md`.

Style: concise, precise, complete, unambiguous. No padding.

## Added TODOs walk

None — doc phase; no TODO dispositions.

## Other findings walk

### design-1 — Fixed
Claim: `DropWorklistItem` with one variant per node class produces never-constructed variants for never-child classes (e.g. `Items`, `Grammar`, 11/21 fixture classes); private-enum `dead_code` fails `make check`'s `cargo clippy -- -D warnings` gate (Makefile:51-54). Consequence: design as written does not compile through the gate; implementer forced into an unreviewed mid-implementation fix.
Disposition claims adoption of reviewer option (a). Verified in design.md:
- Variant-set paragraph (piece 2) now states the child-class-union rule: variants only for classes appearing as a node-typed variant in any child enum; never-child classes get no variant, with the `dead_code` rationale stated explicitly.
- Secondary effect handled: `into_drop_item` gated on "class has an `impl Drop` or a `DropWorklistItem` variant (its only two call sites)"; span-only never-child classes get neither (piece 3 and generator-changes item 3).
- Degenerate empty-union case covered: `_drop_block` skipped entirely; consistent since no `Drop` impls or `into_drop_item` methods exist then either (piece 2 and generator-changes item 4).
- Generator-changes item 4 specifies the `generate()` pre-pass to compute the union.
- New edge-case bullet "Never-child root classes": their own `impl Drop` seeds the worklist directly.
- Code-comment cleanup landed: worklist enum comment reads "one variant per node class that appears as a node-typed child"; drain_into arm comment reads "uniform arm per worklist variant".
Internal consistency spot-check: a span-only class that does appear as a child keeps its variant; its `drain_into` arm calls its child enum's `into_drop_item`, which is emitted (the class has a worklist variant) and matches only `Span(_) => None` — compiles, called, no `dead_code`. Sound.
Assessment: fix complete and deliberate, as the finding required. Accept.

### design-2 — Fixed
Claim: root-cause section cited `exploration.md` §5, whose supporting bound (post-limit depth ≈ `max_depth`) the evaluation showed false; consequence is a future reader re-deriving a ~1000-depth bound and weakening the 100 000-depth tests or re-litigating the Drop fix.
Verified in design.md:
- Root-cause section now states the left-recursion mechanism inline ("deepens the CST one level per `grow_seed` loop iteration at ~constant `apply` depth, so parser-produced tree depth scales with input length, not `max_depth`") and cites `evaluation-drop-depth-reachability.md` §2, explicitly marking it as superseding the flawed `exploration.md` §5 argument. Matches the evaluation's own recommendation ("if revised, cite the left-recursion mechanism above instead" — evaluation line 35).
- Went beyond the suggested "note non-adoption": adopted the evaluation §4 optional test as test 5 (parse `"1" + "+1"*100_000` at default `max_depth`; assert success, bounded Debug, clean drop), pinning reachability-via-parsing in CI; subsequent tests renumbered (spike smoke = 6, suites-clean = 7).
Assessment: fix addresses the consequence at the cited location and strengthens the test plan. Accept.

## Disputed items

None.

## Approved

2 findings: 2 Fixed verified, 0 Won't-Do, 0 TODOs.

---

## Verdict: APPROVED

Both dispositions verified against the revised design. No open questions remain in the doc.
