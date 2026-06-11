# Judge verdict — design review

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Phase: design. Doc: `docs/adr/2026/06/11-parse-depth-limit/design.md`. Round 1.
Notes: `notes-design-design-reviewer.md` (1 reviewer, 2 findings). Dispositions: `dispositions-design.md`.

## Findings walk

### design-1 — Fixed
Claim: Test plan placed T5-T7 in `tests/test_rust_parser_bindings.py`, which guards/tests only `fegen_rust_cst` (no `nest` rules); consequence is AttributeError or error-instead-of-skip, forcing mid-implementation rework. Severity: should-fix (design-internal inconsistency, real rework cost, caught pre-implementation).
Verification against design text:
- Test plan bindings section now reads "**new file** `tests/test_rust_parser_fixture_bindings.py` with its own `importorskip(\"rust_parser_fixture\")` guard" and carries the explicit rationale ("Not `tests/test_rust_parser_bindings.py`: that file guards and tests only `fegen_rust_cst` ... would error instead of skip when only one extension is built") — matches the reviewer's suggested fix verbatim in substance.
- §8 table row: `tests/test_rust_parser_fixture_bindings.py (new) | binding-level depth tests (T5, T6) against rust_parser_fixture, own importorskip` — replaced as claimed.
- T7 unchanged (asserts existing suites pass; no new file needed) — consistent.
Assessment: fix addresses the finding's consequence at the named sections. Accept.

### design-2 — Fixed
Claim: §1 claimed compile compatibility for old-generated-parser + new-core without addressing behavioral semantics; consequence is silent truncated-`Some` corruption / unexplainable `None`s for out-of-tree consumers upgrading the core without regenerating — exactly the incidental breakage CLAUDE.md forbids. Severity: blocker for a design doc (unowned breaking behavior change for the project's primary consumer class).
Verification against design text:
- New subsection "Versioning: old-generated parser + new core is a deliberate behavior break" (end of §2) exists and states both regression shapes ((a) success→`None`, (b) truncated-`Some` silent corruption), matching the finding's mechanics.
- Declares the change semver-breaking with `fltk-parser-core` `0.1.0` → `0.2.0` (0.x breaking signal, blocks silent `cargo update` mixing) — the reviewer's suggested disposition.
- Lockstep-regeneration rule assigned to the `memo.rs` doc rewrite (§7); §1 bullet now cross-references ("Compile compatibility is *not* behavior compatibility for the mixed-version case — see 'Versioning' below"); Edge cases gains the mixed-versions bullet; §8 gains the `Cargo.toml` version-bump row. All five claimed edits present.
- Minor: §7's own bullet text does not restate the lockstep rule, but the Versioning subsection explicitly scopes it into the §7 rewrite ("Lockstep rule documented in the `memo.rs` `apply`/module docs (§7 rewrite)"), so the implementer instruction is unambiguous. Not disputed.
Assessment: finding resolved as a deliberate, documented versioning decision — the exact bar CLAUDE.md and the reviewer set. Accept.

## Disputed items

None.

## Approved

2 findings: 2 Fixed verified.

---

## Verdict: APPROVED
