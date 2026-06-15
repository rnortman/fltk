# Judge verdict — fix-forged-abi-segfault (design phase)

Phase: burndown design. Design doc:
`docs/adr/2026/06/14-rust-backend-assessment/burndown/fix-forged-abi-segfault/design.md`.
Round 1.
Notes: 1 reviewer file (design-reviewer); 6 findings, all dispositioned Fixed.

Ground truth checked against `crates/fltk-cst-core/src/cross_cdylib.rs`,
`crates/fltk-cst-core/src/span.rs`, `tests/test_rust_span.py`, and the design doc.
(No code phase, so this is an other-findings-only walk — no Added-TODOs section.)

## Other findings walk

### design-1 — Fixed
Claim: §4.3 listed only `TestSpanPathAbiGate` and omitted the `extract_source_text`
direct-call suite (forged `FakeSource` objects, the exact path the change edits);
consequence is ~6 pinned-message tests silently flipping to the basicsize message (or
being loosened) if an implementer runs the basicsize gate before `check_abi_pair`.
Consequence is real: it pins a load-bearing ordering constraint the original design only
implied.
Evidence: §4.3 (design.md:354-388) now splits into (a) the direct-call suite enumerated by
file:line with pinned substrings and (b) the Span-path suite. It mandates
`check_abi_pair` run **before** the basicsize gate. Cross-checked: cited tests exist at
`test_rust_span.py` 314/331/347/363/399/789/803/815/827 (308 is the `pytest.raises`
line of `test_with_source_unchecked_str_raises_type_error`, a trivial citation drift, not
a wrong reference). `grep __slots__` over the test file returns nothing — every
`FakeSource*` is a plain class body, so basicsize is 32 ≠ 24 and the basicsize gate would
indeed also reject them with a different message. The ordering claim is grounded in source:
`cross_cdylib.rs:93` runs `check_abi_pair` and the design inserts the basicsize gate after
it. Ordering also restated in §2.B/§2.D.
Assessment: fix addresses the consequence; ordering is now explicit and source-accurate. Accept.

### design-2 — Fixed
Claim: §4.1's `test_padded_forge_still_rejected_or_documented` pinned a UB runtime
outcome ("whatever it is") as a contract; consequence is a flaky or actively-lying test on
the one residual the design is honest about.
Consequence is real: §2.A itself states the padded forge is "still UB if cast"; UB has no
stable value to pin.
Evidence: §4.1 (design.md:313-327) replaced it with
`test_padded_forge_passes_basicsize_gate_boundary`, which pins only
`type(forge).__basicsize__ == SourceText._fltk_cst_core_abi_layout` and explicitly does
**not** call `_with_source_unchecked` on the padded forge; a comment records the
crossing as UB/out-of-contract. §4.4 guarantee 3 updated to "tested fact," not "pinned
contract." This pins the gate boundary (a deterministic value) without asserting any
post-cast behavior — exactly the reviewer's suggested-fix option (b).
Assessment: addresses the consequence cleanly. Accept.

### design-3 — Fixed
Claim: §2.C marketed the `extract_span` basicsize gate as removing a "parallel latent
hazard," but the cast there is reached only after `is_instance` against the canonical,
non-subclassable Span whose layout skew is already caught by `check_abi_pair::<Span>` —
so the gate adds no rejection power; consequence is speculative code on the hot span-read
path.
Consequence verified in source: `cross_cdylib.rs:321` gates the `cast_unchecked` at
:331 behind `is_instance(&native_span_type)`; `get_span_type` runs `check_abi_pair::<Span>`
at :362; `Span` is `#[pyclass(frozen, eq, hash, from_py_object)]` with no `subclass`
(`span.rs`). Reviewer's near-tautology argument holds.
Evidence: §2.C (design.md:205-224) rewritten to "deferred (no hazard to remove)" with the
true rationale and `TODO(forged-abi-extract-span-uniformity)`; OQ2 marked resolved/deferred;
§2.D notes the helper is generic but not called there.
Assessment: correctly deferred with honest rationale. Accept. (Note: the new
`TODO(forged-abi-extract-span-uniformity)` is a design-internal deferral marker, not a
code TODO this phase commits — it carries a uniform-helper consistency item that fails
neither rubric question harmfully: not worth doing now, requires a future trigger. Acceptable.)

### design-4 — Fixed
Claim: §2.A/§3 presented `getattr("__basicsize__")` and `PyType_GetSlot(Py_tp_basicsize)`
as co-equal "both abi3-safe," but the FFI return is `Py_ssize_t` reinterpreted as a
pointer (must be `as usize`, never dereferenced/null-checked, requires `unsafe`);
consequence is a mis-sized gate (spurious reject breaks Requirements item 1, or spurious
accept defeats the gate).
Consequence is real and the trap is correctly described.
Evidence: §2.A (design.md:139-150) now mandates
`get_type().getattr("__basicsize__").extract::<usize>()`, explicitly rejects
`PyType_GetSlot` as a co-equal alternative with the ssize-as-pointer caveat; §2.D helper
spec and §3 abi3 bullet (design.md:279-283) updated to the single mandated path,
removing the contradictory co-equality.
Assessment: footgun removed, single safe path mandated. Accept.

### design-5 — Fixed
Claim: §4.2's only new cross-cdylib test (`node.span` read) duplicates existing
`test_with_source_unchecked_foreign_cdylib_works` (:399) /
`test_source_bearing_span_reads_from_consumer_cdylib` (:777) and asserts only the
end-to-end outcome, not that the genuine object passed the *new gate* specifically;
consequence is a mis-placed/bypassed gate could still pass CI. Reviewer flags this himself
as lower severity (existing tests already cover the accept path).
Evidence: §4.2 (design.md:329-352) now states the end-to-end accept path is already covered
(reuse, do not duplicate) and adds one focused
`test_foreign_source_text_basicsize_matches_native_layout` pinning the gate's
accept-branch precondition (`type(foreign_st).__basicsize__ == native layout`). Both cited
tests exist at :399 and :777. §4.4 guarantee 2 updated.
Assessment: closes the gap cheaply without duplicating. Accept.

### design-6 — Fixed
Claim: §2.B made basicsize a seeding precondition but did not state that the cache-hit
`cast_unchecked` branch is unchanged and relies entirely on the invariant "only
basicsize-validated types are ever cached" — which holds only if the gate runs *before*
`get_or_init`; consequence is that wrong ordering reopens the broader pre-fix residual (any
`check_abi_pair`-passing forge seeds the cell, after which instances hit `cast_unchecked`
with no attribute check).
Consequence verified in source: `cross_cdylib.rs:82-91` is a pointer-identity-only
`cast_unchecked` cache-hit branch; `get_or_init` seeds at :97 immediately after
`check_abi_pair` with no basicsize gate today. Ordering is genuinely load-bearing.
Evidence: §2.B (design.md:187-203) adds an explicit "Ordering invariant (load-bearing —
state it in the SAFETY comment)" paragraph (gate before `get_or_init`, gate is the seeding
condition, cache-hit branch left unchanged) plus a "Residual parity with §2.A" paragraph
clarifying §2.B narrows the cache residual to the *same* padded-forge residual rather than
fully closing it. Honest and matches the source structure.
Assessment: invariant made explicit and correct; residual honesty preserved. Accept.

## Disputed items

None. All six dispositions are Fixed via design-doc edits that are present in the doc,
address the stated consequence, and are consistent with the source ground truth.

## Approved

6 findings: 6 Fixed verified (design-1 ordering enumerated + mandated; design-2 UB-outcome
test replaced with gate-boundary pin; design-3 §2.C deferred with honest rationale;
design-4 single safe `__basicsize__` access path mandated; design-5 focused precondition
pin added without duplication; design-6 cache-seeding ordering invariant made explicit).

The design's core approach (basicsize-genuineness gate before `cast_unchecked`,
`check_abi_pair` demoted to version-skew diagnostic and ordered first, cache-seeding gated,
honest about the padded-`__slots__` residual carried to `TODO(forged-abi-capsule-hardening)`
in Open Q1) is sound and source-grounded. The two binding spec obligations (reject
pure-Python forge / accept genuine foreign SourceText; subprocess-isolated regression
test) are both covered.

---

## Verdict: APPROVED

All six dispositions acceptable. Fixes verified present in the design and consistent with
`cross_cdylib.rs`, `span.rs`, and `test_rust_span.py`.
