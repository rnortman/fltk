# Judge verdict — requirements review

Style: concise, precise, no padding. Audience: smart LLM/human.

Phase: requirements (doc phase — no TODO walk). Doc: `requirements.md`. Round 1.
Notes: 1 reviewer file (`notes-requirements-requirements-reviewer.md`); 4 findings.

## Findings walk

### requirements-1 — Fixed
Claim: new native surface (span `text`, native `merge`/`intersect`) specified only under "Feature off"; consequence is a designer could gate it `#[cfg(not(feature = "python"))]`, defeating phase-2's purpose (parser backend runs in python-on builds per roadmap mode 3) and forcing a later breaking unification.
Consequence verified: request sequencing point (a) ("defines and stabilizes the native API contract the parser backend will code against") and roadmap mode 3 confirm it. Blocker-level for a requirements doc.
Fix verified: `requirements.md` "System behavior > 1" now carries a dedicated bullet — "**Native surface is mode-independent.** All native (non-pyo3) API — existing and newly exposed — is available identically in both feature modes; the feature gates only the pyo3 surface" — with the roadmap rationale and an explicit "A python-off-only native API is non-compliant."
Assessment: fix addresses the exact ambiguity, in the named section, with the requested explicitness. Accept.

### requirements-2 — Fixed
Claim: "all native methods (...)" parenthetical read as exhaustive but omitted `source_full_text_str`; consequence is silent loss of a working native accessor in python-off builds.
Consequence verified: exploration (span.rs notes) lists `source_full_text_str` among native methods and `source_as_py` as pyo3-bound. Real omission.
Fix verified: bullet now reads "**all** existing pure-Rust methods remain available (per exploration: ... `source_full_text_str`; `SourceText::from_str` — list illustrative, not exhaustive)" plus "Exception: `source_as_py` is inherently pyo3-bound and is python-on only."
Assessment: both prongs of the suggested fix applied (completed list + illustrative marker + `source_as_py` note). Accept.

### requirements-3 — Fixed
Claim: python-off coverage required only in `.github/workflows/ci.yml`; consequence is a CI-only step developers can't reproduce locally (rot caught at push, not prevented), plus file-path design leakage.
Consequence verified: request says "so the configuration can't rot"; exploration confirms `make check` / `cargo-test` cover workspace only today.
Fix verified: section retitled "5. CI / automated gate"; now requires CI exercise (build + test incl. spike and no-pyo3 mechanical check) AND local invocability "via the standard precommit check entrypoint (or an equivalently documented single command)." User-visible surface bullet replaced with path-neutral "Automated checks"; no `ci.yml` file-path prescription remains in the doc.
Assessment: both the rot-prevention substance and the leakage removal applied. Accept.

### requirements-4 — Fixed
Claim: feature name/polarity pre-settled at requirements stage ("settled-unless-redirected") though the request delegates it ("designer picks final name/polarity"). Low severity.
Consequence verified: request Scope item 1 confirms the delegation.
Fix verified: Open questions §4 now states the request delegates the decision; `python` default-on is the design default per exploration's recommendation, "not a requirements-level decision," designer may deviate with rationale (e.g. `pyo3`) keeping default-on behavior; public-API-from-day-one note retained. Consistent with "System behavior > 1" ("final name/polarity is a design decision") and User-visible surface ("delegated to design per the request").
Assessment: recommendation kept, framing corrected, internally consistent across all three mentions. Accept.

## Approved

4 findings: 4 Fixed verified.

---

## Verdict: APPROVED

All dispositions acceptable; every fix lands in the named section and matches the reviewer's requested remedy. Round 1.
