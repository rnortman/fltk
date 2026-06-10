# Dispositions: design review round 1 — span-source-as-py-crosscdylib

Concise. Precise. Complete. Unambiguous. Audience: smart LLM/human.
Notes: `notes-design-design-reviewer.md`. Design: `design.md` (edited in place). All findings independently fact-checked against base 9db20de before disposition.

design-1:
- Disposition: Fixed
- Action: §3 "Observable behavior change" parenthetical corrected — verified `tests/test_rust_span.py:174-175` uses two distinct same-text `SourceText("hello")` objects (reviewer right; "genuinely different texts" was `test_intersect_different_sources_raises`, lines 209-215). §3 "Residual divergence" bullet now records that the divergence is actively pinned by `test_merge_different_sources_raises` and warns future cross-backend-equivalence work to revisit that test. Design conclusion (test stays green; no test pins the accessor-path raise) unchanged — verified still true.
- Severity assessment: Documentation-accuracy bug with downstream risk: a future cross-backend-equivalence pass trusting the ADR would believe the residual divergence is untested when it is test-pinned. No implementation-plan impact.

design-2:
- Disposition: Fixed
- Action: §3 version-skew bullet rewritten to name pyo3-resolution skew as the likeliest same-marker/different-layout class (verified: `tests/rust_cst_fixture/Cargo.toml` is a standalone workspace with caret `pyo3 = "0.23"`; `fltk-cst-core` is `0.1.0`), state explicitly that the §2.2 invariant is the contract and the marker is a partial detector, and require the emitted `TODO(crosscdylib-abi-sentinel)` comment to name pyo3 skew. §2.2 TODO-comment instruction and §2.7 `TODO.md`-extension instruction updated to match (fold pyo3 version / layout hash into the strengthened derivation). Folding pyo3's version into the ABI string *now* was considered and deferred to the sentinel TODO: pyo3 exposes no compile-time version constant, so it needs build.rs machinery — squarely the sentinel's "strengthen the derivation" work, already owned there.
- Severity assessment: §3 previously implied skew now fails cleanly in general; the most plausible real-world skew class still reaches UB with a matching marker. False operator confidence in a memory-safety boundary; worth fixing in-doc and propagating into the emitted TODO text.

design-3:
- Disposition: Fixed
- Action: §2.2 gains a "Marker carrier: string classattr, deliberately" decision paragraph (the finding's own suggested alternative resolution: record why string over capsule). The capsule premise is partly wrong: a capsule prevents de-novo construction from pure Python, but the marker must be readable from `fltk._native` to be checked, and anything readable is replayable — `class Fake: _fltk_cst_core_abi = fltk._native.SourceText._fltk_cst_core_abi` defeats a capsule-name gate identically to a copied string defeating the string gate. The only non-replayable gate is type identity, unavailable in this direction per §2.1 (which the reviewer's own verification summary confirms). So the capsule buys no removal of pure-Python-reachable UB at added API/typing cost; the deliberate string choice is now recorded, and a fail-safe hardening avenue (`__basicsize__` sanity check before the cast) is named and delegated to `crosscdylib-abi-sentinel`, which owns the gate mechanism.
- Severity assessment: Real gap — the design accepted a new pure-Python-reachable UB path without examining the obvious alternative carrier; if the capsule had actually closed the hole, shipping the string would have been the wrong call. Examination shows carrier choice doesn't change the threat model (replay), so the fix is recording the decision, not changing the mechanism.

design-4:
- Disposition: Fixed
- Action: §2.3 stale cite replaced — verified at 9db20de that `src/cst_fegen.rs:317-319` is append/extend code and the canonical-type comment sits at lines 247, 633, 1078, … (grep-confirmed). Cite now quotes the comment text and points at the span-getter instance `src/cst_fegen.rs:633-634`.
- Severity assessment: Trivial; constraint itself real and verified. An implementer following the cite would land in unrelated code and re-grep.

No Won't-Do or TODO dispositions. Cleanup-editor not re-invoked: edits are fact corrections and rationale additions, no approach or structure change.
