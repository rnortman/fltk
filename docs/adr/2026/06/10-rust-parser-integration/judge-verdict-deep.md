# Judge verdict — deep review

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Phase: deep. Base 8b3e92b..HEAD f62c1df (respond commit f62c1df on top of reviewed f1423a2). Round 1.
Notes: 7 reviewer files (security, quality, efficiency: no findings); 6 findings total.

## Added TODOs walk

No TODO dispositions; no TODOs added in 8b3e92b..f62c1df. Nothing to score.

## Other findings walk

### errhandling-1 — Fixed
Claim: partial-consume assertion at `tests/test_phase4_fegen_rust_backend.py:258` used bare `parser.error_message()`, which reports the error tracker's farthest failure — potentially well before `result.pos` — giving a misleading stall position on the hardest-to-diagnose failure (fegen.fltkg partial parse).
Diff at `tests/test_phase4_fegen_rust_backend.py:258-260`: message now `f"Partial parse: consumed {result.pos}/{len(text)} chars. Error tracker: {parser.error_message()}"`. Both the actual stall boundary and the tracker output are visible; matches the reviewer's suggested form.
Assessment: fix addresses the consequence at the named line. Accept.

### errhandling-2 — Fixed
Claim: unguarded `_FEGEN_FLTKG_PATH.read_text()` at line 277 turns a missing file into a context-free `FileNotFoundError` indistinguishable from infrastructure failure.
Diff at `tests/test_phase4_fegen_rust_backend.py:280-281`: `assert _FEGEN_FLTKG_PATH.exists(), f"fegen.fltkg not found at {_FEGEN_FLTKG_PATH}"` precedes the read — the reviewer's exact suggested pattern (mirrors `plumbing.py` defensive read).
Assessment: accept.

### correctness-1 — Fixed
Claim: ADR README cited nonexistent `tests/test_rust_parser_parity.py` for the load-bearing "parity tests are the contract" mitigation; ADR immutability would freeze the dangling pointer.
Verified: `docs/adr/2026/06/10-rust-parser-codegen/README.md:67-68` now names `tests/test_rust_parser_parity_fegen.py` and `tests/test_rust_parser_parity_fixture.py`; both files confirmed present in `tests/`. Edit lands before the ADR is merged as accepted, so immutability is not violated.
Assessment: accept.

### test-1 — Fixed
Claim: helper hands `result.result` (typed `Any` at the binding layer) to `Cst2Gsm.visit_grammar` without a type check; a future binding regression surfaces as an opaque `AttributeError` deep inside `Cst2Gsm` instead of at the parse boundary.
Diff at `tests/test_phase4_fegen_rust_backend.py:261`: `assert isinstance(result.result, fegen_rust_cst.Grammar), type(result.result)` immediately after the `result.pos` assertion — the reviewer's exact fix, correctly placed in the shared helper so all three tests get the pin.
Assessment: accept.

### test-2 — Fixed
Claim: `read_text()` with platform-default encoding risks a garbled-input parse failure (not an encoding error) on a non-UTF-8 CI locale.
Diff at `tests/test_phase4_fegen_rust_backend.py:281`: `read_text(encoding="utf-8")`.
Assessment: accept.

### reuse-1 — Won't-Do
Claim: `_assert_rust_parser_equals_python` hand-rolls the Parser → guard → `Cst2Gsm` composition that `plumbing.parse_grammar` (plumbing.py:113-175) already encapsulates; suggested collapsing to two `parse_grammar` calls. Consequence: silent divergence if `parse_grammar`'s composition evolves.
Rationale: design.md §2.2 commits to exercising the parser directly — the "Path under test" code block (design.md:62-73) is verbatim the direct composition, and design.md:86 states "No new fixtures, no plumbing.py changes (in-tree adoption is explicitly a follow-up)". Collapsing to `parse_grammar(text, rust_fegen_cst_module=...)` would reproduce `TestAC8RealCst2GsmRustBackend` (test file lines 68-88), which already exists, and would delete the only end-to-end coverage of the direct `fegen_rust_cst.Parser` surface — the composition an out-of-tree pure-Rust-parser consumer uses without plumbing.
Inspection: the reviewer's own note concedes the design's parser-direct goal is "a valid goal (testing a different composition)". The suggested simplification is not a refactor of the same coverage; it removes the distinct test surface the design deliberately ordered. This is an active-harm rationale, not "out of scope". The residual divergence cost is three lines of test-local composition guarded by the new isinstance pin and GSM equality against the independent Python path.
Assessment: Won't-Do sound. Accept.

## Approved

6 findings: 5 Fixed verified, 1 Won't-Do sound.

---

## Verdict: APPROVED

All dispositions acceptable. Round 1, no disputed items.
