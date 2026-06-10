# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/06/10-span-source-as-py-crosscdylib/design.md` (edited in place). Base 9db20de. Round 1.
Notes: `notes-design-design-reviewer.md` (1 reviewer, 4 findings). Dispositions: `dispositions-design.md`.
Concise. Precise. Complete. Unambiguous. Audience: smart LLM/human.

## Findings walk

### design-1 — Fixed
Claim: §3 misdescribed `test_merge_different_sources_raises` as using "genuinely different texts"; consequence is a false coverage record misleading future cross-backend-equivalence work (residual divergence is test-pinned, not untested).
Source check: `tests/test_rust_span.py:174-175` — `src1 = SourceText("hello"); src2 = SourceText("hello")` (same text, distinct objects); `test_intersect_different_sources_raises` at 209-215 is the "hello"/"world" case. Reviewer right.
Design now (§3): "Observable behavior change" bullet states the test "constructs two distinct same-text `SourceText("hello")` objects directly — the residual-divergence case below, not the accessor path; it stays green"; "Residual divergence" bullet records the divergence is "actively pinned as intended Rust behavior by `test_merge_different_sources_raises`" and warns equivalence work to revisit that test.
Assessment: fix addresses claim and consequence exactly. Accept.

### design-2 — Fixed
Claim: §3 skew limitation named only "local dev edits"; pyo3-resolution skew (likelier, marker-blind, → UB) unnamed; consequence is false operator confidence in a memory-safety boundary.
Source check: `tests/rust_cst_fixture/Cargo.toml` — `[workspace]` (line 3, standalone) and `pyo3 = { version = "0.23", ... }` caret (line 19). Reviewer's premise verified.
Design now: §3 version-skew bullet names "(a) **pyo3-resolution skew**, the likeliest real-world class" with the standalone-workspace mechanism, "(b)" local edits, notes `fltk-cst-core` is 0.1.0 and effectively never bumped, and states the §2.2 invariant is the contract / marker is "a partial detector, not a guarantee". §2.2 requires the emitted `TODO(crosscdylib-abi-sentinel)` comment to note "fold in pyo3 version and/or a layout hash — `CARGO_PKG_VERSION` alone does not cover pyo3-resolution skew"; §2.7 extends the `TODO.md` entry instruction to match. All three propagation points the finding asked for are covered.
Deferral of folding pyo3's version into the ABI string now: rationale (no compile-time pyo3 version constant accessible to a dependent crate without build.rs machinery) is sound — Cargo does not expose dependency versions to dependents — and the reviewer marked that part "optionally". `crosscdylib-abi-sentinel` exists in `TODO.md` and owns the derivation. Accept.

### design-3 — Fixed
Claim: design accepted the first pure-Python-reachable UB path without examining a non-forgeable carrier (PyCapsule classattr); suggested fix: switch to capsule **or** explicitly record why string was chosen.
Responder rebuttal: capsule prevents de-novo construction but not replay — `class Fake: _fltk_cst_core_abi = fltk._native.SourceText._fltk_cst_core_abi` passes a capsule-name gate identically. Adjudication: rebuttal is correct. The gate reads the marker via `getattr` on the object's type; any value-based comparison (name string, payload) accepts a replayed genuine capsule, and identity/payload-pointer comparison would reject the legitimate cross-cdylib case (each cdylib creates its own capsule from its own rlib copy). The only non-replayable gate is type identity, which the reviewer's own verification summary confirms is unavailable canonical→consumer. The capsule does not remove the pure-Python-reachable UB.
Design now: §2.2 "Marker carrier: string classattr, deliberately" paragraph records the capsule consideration, the replay argument, the rejection rationale (added API surface, no threat-model change), and names a fail-safe hardening avenue (`__basicsize__` sanity check) delegated to `crosscdylib-abi-sentinel`. This is the finding's own second suggested resolution, executed with a stronger argument than the finding anticipated. Accept.

### design-4 — Fixed
Claim: stale cite `src/cst_fegen.rs:317-319` for the canonical-type comment; trivial.
Source check: comment "Return a fltk._native.Span so consumers always get the canonical type" sits at `src/cst_fegen.rs:247, 633, 1078, ...` (grep-confirmed); 317-319 is not one of them.
Design now (§2.3): quotes the comment text and cites `src/cst_fegen.rs:633-634` — the span-getter instance, verified at 633. Accept.

## Disputed items

None.

## Approved

4 findings: 4 Fixed verified, 0 Won't-Do, 0 TODOs.

---

## Verdict: APPROVED

All four dispositions verified against source; design edits land exactly where the findings' consequences pointed; design-3's partial rebuttal of the capsule premise is correct and source-backed.
