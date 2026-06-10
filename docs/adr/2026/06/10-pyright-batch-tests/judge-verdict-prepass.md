# Judge verdict — pre-pass

Style: concise, precise, no padding. Audience: smart LLM/human.

Phase: pre-pass (code). Base 8bee6b0..HEAD ff3700b. Round 1.
Notes: 2 reviewer files (slop: 4 findings; scope: no findings). Dispositions: 4, all Fixed. Fix commit: ff3700b.

## Added TODOs walk

No TODO-dispositioned findings; diff adds no `TODO(` comments (only the request.md text referencing the removed slug). `git grep pyright-batch-tests` outside docs/ returns nothing — TODO.md entry and code comments removed per request §6.

## Other findings walk

### slop-1 — Fixed
Claim: `_run_pyright_over_dir` docstring in `tests/test_clean_protocol_consumer_api.py` says "list of error diagnostics" but the function returns all severities; consequence is a maintainer skipping the severity filter and accepting warnings as clean.
Diff at `tests/test_clean_protocol_consumer_api.py:114-118`: docstring now reads "all diagnostics (warnings + errors); callers filter by severity", matching the `test_cst_protocol.py` copy. Code body confirms no severity filtering in the partition loop.
Assessment: fix matches behavior and the sibling copy. Accept.

### slop-2 — Fixed
Claim: three inline path-filter + severity-filter patterns in `tests/test_clean_protocol_consumer_api.py` duplicate `_diags_for_file` from `test_cst_protocol.py`; consequence is latent divergence on logic change.
Diff: `_diags_for_file` added at `tests/test_clean_protocol_consumer_api.py:169-174`; all three inline sites (now 296, 914, 992) replaced with helper calls. Reviewer's fix explicitly allowed in-file helper "(or import from a shared conftest)", so the local copy rather than a shared module is within the stated fix.
Assessment: all three sites converted; pattern now mirrors `test_cst_protocol.py`. Accept.

### slop-3 — Fixed
Claim: `_diags_for_file` docstring in `fltk/fegen/test_cst_protocol.py` restates the signature; consequence is filler that omits the non-obvious substring-vs-absolute-path detail.
Diff at `fltk/fegen/test_cst_protocol.py:85-88`: docstring replaced with "Matches by substring against pyright's absolute file paths. Bare filenames work for files written into a tmpdir." — exactly the requested content.
Assessment: Accept.

### slop-4 — Fixed
Claim: `_run_pyright` docstring carries a caller-reference sentence ("Used only for the real-repo-file test..."); consequence is helper docs coupled to the call graph, silently wrong on a second caller.
Diff at `tests/test_clean_protocol_consumer_api.py:91-92`: sentence removed; surviving one-liner "return list of error diagnostics" verified accurate (body filters `severity == "error"`).
Minor caveat, not blocking: the reviewer's fix also suggested relocating the repo-root-config/not-batchable constraint into `test_fltk2gsm_pyright_clean`'s docstring; that was not done (docstring at line 365 is unchanged). The stated consequence — call-graph coupling — is fully resolved by removal, and the constraint remains documented in `request.md` §2. Nit-level omission; does not warrant rework.
Assessment: Accept.

## Disputed items

None.

## Approved

4 findings: 4 Fixed verified. Scope reviewer reported no findings.

---

## Verdict: APPROVED

All dispositions acceptable. Fix commit ff3700b verified at named lines.
