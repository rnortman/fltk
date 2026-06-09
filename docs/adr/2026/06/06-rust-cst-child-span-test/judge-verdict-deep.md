# Judge verdict — deep review

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Phase: deep. Base c505f3c..HEAD 7b1855d. Round 1.
Notes: 7 reviewer files; 7 findings (4 marked "no findings"). Dispositions: `dispositions-deep.md`.
Note: reviewers reviewed 7a288b6; HEAD 7b1855d is the respond commit. Diff verified against 7b1855d.

## Added TODOs walk

### reuse-1 — TODO(child-span-params-dedup) at tests/test_phase4_fegen_rust_backend.py:115
Q1 (worth doing): yes — `_CHILD_SPAN_PARAMS` re-enumerates the three `_span`-factory rows of `CLASS_LABEL_INFO` (`tests/test_fegen_rust_cst.py:55-57`); a label rename updated in one list and not the other leaves the new tests pinning a stale method name. Real, stated consequence.
Q2 (design/owner input required): yes — verified by inspection: the two lists are not directly shareable. `CLASS_LABEL_INFO` holds **class objects from `fltk._native.fegen_cst`** (embedded backend, `test_fegen_rust_cst.py:12-27`); `_CHILD_SPAN_PARAMS` holds classes from the **standalone `fegen_rust_cst` cdylib**, gated by module-level `importorskip` (line 29). Only the name strings are common. Dedup requires a names-only shared catalogue with per-module resolution, plus a home for it — `tests/` has no `__init__.py` and no `conftest.py`, and a conftest-level `importorskip` would over-skip. That is shared-test-infrastructure design, not a mechanical move. Responder's "cross-file imports are fragile" understates it; the module-object mismatch makes naive import actively wrong.
Iteration-created check: the duplication was created this iteration, but it passes Q2 and is not silent — TODO comment at the site (`:115`) + `TODO.md:31` entry, slugs in sync, old `rust-cst-child-span-test` slug fully retired (no remaining references).
Assessment: TODO acceptable.

## Other findings walk

### correctness-1 — Fixed
Claim: in `test_append_rejects_terminalsrc_span`, `tsrc.Span(3, 9)` constructed inside `pytest.raises(TypeError)` with no `match=`; a future constructor/arity `TypeError` would pass the test vacuously — exactly the drift scenarios the design's "deliberate contract pin" exists to catch.
Diff at `tests/test_phase4_fegen_rust_backend.py:163-167` (HEAD): `bad = tsrc.Span(3, 9)` constructed before the block; `with pytest.raises(TypeError, match="unsupported child type"):` wraps only `getattr(node, append_method)(bad)`. Matches the suggested fix exactly. Message string confirmed against `extract_from_pyobject` rejection ("unsupported child type", `src/cst_fegen.rs:4325-4338`). File runs green at HEAD: 31 passed.
Assessment: fix complete at the named lines. Accept.

### test-1 — Won't-Do
Claim: `child_method` param unused in the rejection test (suppressed via `noqa: ARG002`). Reviewer's own consequence: nil — "cosmetic", "no behavior gap", "fix: none required".
Inspection: param comes from the shared `_CHILD_SPAN_PARAMS` parametrize; removing it breaks the binding. `noqa: ARG002` present at `:163`.
Assessment: no consequence stated by reviewer; responder wins by default, and the rationale is independently sound. Accept.

### test-2 — Won't-Do
Claim: sourceless test doesn't directly verify `terminals[result.start:result.end]` usability. Reviewer's own conclusion: "this is not a gap" — `result.start == 3` integer equality pins the type.
Assessment: confirmatory finding, nil consequence. Accept.

### test-3 — Won't-Do
Claim: source-bearing roundtrip test — "No gap." Confirmatory only.
Assessment: nil consequence. Accept.

### test-4 — Won't-Do
Claim: `Rule.child_name()` → `Identifier` path — "This is not an omission"; covered via the `Identifier` param. Confirmatory only.
Assessment: nil consequence. Accept.

### test-5 — Won't-Do
Claim: absence of `match=` is "acceptable"; consequence nil per reviewer. Conflicts with correctness-1, which is the correct analysis (vacuous-pass risk).
Inspection: the correctness-1 fix adds `match="unsupported child type"` anyway, so test-5's subject is moot at HEAD.
Assessment: Won't-Do correct — no separate action existed; the substantive concern is fixed under correctness-1. Accept.

## Disputed items

None.

## Approved

7 findings: 1 Fixed verified, 5 Won't-Do sound (all nil-consequence/confirmatory), 1 TODO acceptable.

---

## Verdict: APPROVED

All dispositions acceptable. Test file green at HEAD (31 passed); TODO slugs in sync.
