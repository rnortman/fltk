# Judge verdict — design review

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Phase: design. Doc: `docs/adr/2026/06/11-rust-cst-debug-depth/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 3 numbered findings + 1 open-question assessment.

## Findings walk

### design-1 — Fixed
Claim: deep-tree teardown mechanism ("pop into a worklist") unimplementable — generated node fields module-private, no destructive child accessor; consequence is implementer stall or public-API scope creep.
Source check: `tests/rust_parser_fixture/src/cst.rs:250` reads "Not pub: use span() / children() / push_child() — the stable accessor API"; no `drain`/`clear`/`take_children` anywhere in `gsm2tree_rs.py`. Claim and consequence valid.
Design now (Edge cases, "Deep-tree test teardown"): specifies the retain-handles mechanism exactly — root-first `Vec<Shared<Expr>>` built during construction, drop root binding, drop handles front-to-back, refcount 2→1 per step so no recursion — and explicitly forbids adding a destructive child accessor ("public-API scope creep"). Test plan item 1 matches ("retaining each level in the teardown vec").
Assessment: fix is complete, mechanically correct (each handle drop deallocates exactly one node because the vec still holds the next level), and addresses the scope-creep consequence directly. Accept.

### design-2 — Fixed
Claim: depth rationale conflated frames with tree levels; 100 000 × 64 B ≈ 6.1 MiB < 8 MiB, so the arithmetic didn't prove overflow; consequence is a future depth "optimization" making the pre-fix demonstration vacuous.
Design now (Test plan item 1): per-level cost restated as ~5-10 frames/level through the old derive chain (`Shared::fmt` → derived node `fmt` → `debug_struct` → `Vec`/tuple → `ChildEnum` → next `Shared::fmt`), several hundred bytes to >1 KiB per level in debug builds, 100 000 levels comfortably exceeding 8 MiB; explicit guard added: "Do not lower the depth based on a per-frame (rather than per-level) estimate."
Assessment: restated rationale closes the arithmetic gap and pins the depth against the exact failure mode the reviewer named. Accept.

### design-3 — Fixed
Claim: "only fixture grammar with a self-recursive node type reachable programmatically" was false (`lval`/`rval`, `rec_via_sub`, `Shared<Alternatives>` in `tests/rust_cst_fegen`); consequence is a future reader treating the location as forced.
Source check: `rust_parser_fixture.fltkg:36-37` (`lval`/`rval` mutual recursion) and `:66` (`rec_via_sub`) confirmed.
Design now (Test plan item 1): "the simplest directly self-recursive node type (other recursive types exist: … `Expr` is chosen, not forced)".
Assessment: uniqueness claim removed, alternatives named, choice marked deliberate. Accept.

### Open-question assessment (unnumbered) — Incorporated
Reviewer concurred with filing `TODO(rust-cst-drop-depth)` and suggested comment locations. Design open question 1 now records "design author + design reviewer concur: file it" plus both suggested `TODO(slug)` sites (the `children: Vec<...>` field emission in `gsm2tree_rs.py`; the deep-tree test's iterative teardown), and keeps it a non-blocking user-decision item.
Assessment: incorporation matches the reviewer's text; correctly left as a user decision per TODO discipline rather than silently filed. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified. 1 open-question assessment incorporated.

---

## Verdict: APPROVED

All dispositions acceptable; all fixes verified in the design text and spot-checked against source.
