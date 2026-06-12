# Judge verdict — prepass review (rust-generated-ident-collisions)

Style: concise, precise, no padding. Audience: smart LLM/human.

Phase: prepass (code). Base d2abc80..HEAD 4f66083. Round 1.
Notes: 2 reviewer files (slop: 3 findings; scope: no findings, 1 minor note). Dispositions: `dispositions-prepass.md`.

## Added TODOs walk

No TODOs added in d2abc80..4f66083 (diff grep: only deletion of the `rust-generated-ident-collisions` TODO entry, per design §4). Section empty.

## Other findings walk

### slop-1 — Fixed
Claim: `test_multiple_collisions_reported_at_once` hand-rolled four inline `gsm.Rule(...)` blobs duplicating `_make_two_rule_grammar`; consequence is repetition signalling inattention to the existing helper.
Evidence: diff at HEAD — the test calls `_make_two_rule_grammar("foo", "foo_child")` and `_make_two_rule_grammar("bar", "bar_child")` and merges `rules`/`identifiers` into one `gsm.Grammar` (`tests/test_gsm2tree_rs.py`, `test_multiple_collisions_reported_at_once`). No inline `gsm.Rule` blobs remain in that test. This is exactly the reviewer's proposed "call it twice and merge" fix. Test passes (`pytest TestCrossRuleIdentifierCollisions`: 10 passed).
Assessment: fix addresses the finding. Accept.

### slop-2 — Fixed
Claim: the `_RESERVED_CLASS_NAMES` invariant (no reserved name starts with `Py`, ends with `Child`/`Label`) was prose-only; consequence is a future editor adding e.g. `"PyNode"` silently loses cross-rule coverage.
Evidence: `fltk/fegen/gsm2tree_rs.py:50-53` — module-level `assert all(not n.startswith("Py") and not n.endswith("Child") and not n.endswith("Label") for n in _RESERVED_CLASS_NAMES)` with a message instructing seeding into the claims dict; comment above reads "Machine-checked:". This is the reviewer's second proposed remedy (startup assert) and fires at import time, before any generator runs. Current five reserved names satisfy the predicate.
Assessment: invariant is now machine-checked; consequence eliminated. Accept.

### slop-3 — Fixed
Claim: redundant local `from fltk.fegen.gsm2tree_rs import RustCstGenerator as _Gen  # noqa: PLC0415` inside `test_prediction_vs_output_consistency`; consequence is gratuitous noqa suppression / copy-paste slop.
Evidence: HEAD test body uses module-level `RustCstGenerator` directly (`RustCstGenerator.child_enum_name(cn)`, `RustCstGenerator._label_enum_rust_name(cn)`); `grep "_Gen"` over `tests/test_gsm2tree_rs.py` finds no local re-import of `RustCstGenerator` and no PLC0415 noqa for it (remaining PLC0415 noqas are unrelated pre-existing local imports).
Assessment: removed. Accept.

### scope note — No action required
Reviewer note (explicitly "not a scope gap", no consequence stated): drift-guard test uses a pure-regex grammar rather than one "with node-typed children" (design §Test plan item 3).
Inspection: the collision check's correctness depends on prediction matching the *definition* sites, and the test asserts every claimed identifier appears as its `pub struct`/`pub enum` definition for all rules including auto-added `_trivia` — the literal assertion set test plan item 3 specifies. Inline `Py{child_cls}` *reference* drift would produce a Rust compile error (unresolved ident), not a missed collision, and is covered by existing self-hosting/fixture regen tests on real grammars with node-typed children (design §Generated-output stability). Deviation from the design's phrasing does not weaken the guard.
Assessment: no consequence stated and the reviewer self-assessed no gap; responder's No-action disposition is sound. Accept.

## Disputed items

None.

## Approved

4 items: 3 Fixed verified, 1 No-action sound. 0 TODOs.

---

## Verdict: APPROVED

All dispositions verified against HEAD 4f66083; all three slop fixes match the reviewer's proposed remedies; new test class passes (10/10).
