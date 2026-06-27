# Judge verdict — deep review (deep3)

Phase: deep. Base 78eacab..HEAD c2caadb. Round 1.
Notes: 7 reviewer files (error-handling, correctness, security, test, reuse, quality, efficiency).
Findings: 5 distinct (errhandling-1/test-1 are one finding double-reported; test-2, reuse-1, quality-1, efficiency-1). Correctness + security: no findings.
Diff scope: `Makefile` (6 lines, check-gating for `crates/fltkfmt`), `tests/test_fltkfmt_parity.py` (new), `tests/unparser_parity.py` (helper), `tests/test_rust_unparser_parity_fixture.py` (import + ID call), implementation-log.md.

## Added TODOs walk

No TODO comments added in this diff. The only TODO referenced by reviewers
(`TODO(fltkfmt-integration-tests)`) is pre-existing, outside this diff, and explicitly
not flagged per the deferred-item instruction. Nothing to score.

## Other findings walk

### errhandling-1 / test-1 — Fixed
Claim: `proc.stdout.decode("utf-8")` (orig line 129) has no `errors=` mode; non-UTF-8 `fltkfmt` output raises a bare `UnicodeDecodeError` before `assert py_out == rust_out` runs, yielding an opaque traceback with no corpus file / config context. Consequence: a non-UTF-8 output bug surfaces undiagnosably instead of as the `[file w= i=] mismatch` assertion message.
HEAD: `rust_out = proc.stdout.decode("utf-8", "replace")`, and the return-code assertion's stderr decode is `proc.stderr.decode("utf-8", "replace")` — consistent. Bad bytes now flow into the comparison as `�` and the assertion produces full `[name w= i=]` context.
Assessment: addresses the consequence at the named line; matches the reviewer's `errors="replace"` option. Test-only error path, low severity. Accept.

### test-2 — Fixed
Claim: `_CONFIGS` comment said "...plus the CLI default (width 80 / indent 2)", implying a nonexistent third config; misleads a reader about the coverage set. Consequence: documentation confusion, no behavior.
HEAD (lines 53-54): "Wide (80/2, which is also the CLI default) and narrow (40/4), so the flat-vs-break decisions are exercised cross-backend." Exactly the reviewer's suggested rewrite; the false "plus" phrasing is gone.
Assessment: trivial doc nit, fixed correctly. Accept.

### reuse-1 — Fixed
Claim: the `[f"w{w}i{i}" for (w,i) in _CONFIGS]` ID formula was duplicated verbatim in both parity modules; a one-sided change to the format string silently diverges and breaks CI test-ID filters. Consequence: latent ID drift across modules.
HEAD: `render_config_ids(configs)` added to `tests/unparser_parity.py` (shared helper module), returning the identical `[f"w{w}i{i}" for (w,i) in configs]`. Both modules import it and call it (`test_fltkfmt_parity.py:57`, `test_rust_unparser_parity_fixture.py:168`); per-module `_CONFIGS` lists stay local. Formula is byte-identical to the prior inline version, so existing test IDs are unchanged — no ID churn introduced by the fix.
Assessment: single-sources the format string exactly as flagged, behavior-preserving. Low severity, correct. Accept.

### quality-1 — Fixed
Claim: `_py_unparser_result` called the cached `_py_parser_result()` twice (once for `.grammar`, once for `.cst_module_name`); reads as two generations and becomes a real double-generation if the cache decorator is later removed. Consequence: latent regression on refactor.
HEAD: binds `parser_result = _py_parser_result()` once, then reads `.grammar`/`.cst_module_name` off it. Matches the reviewer's fix. Responder kept `parser_result.grammar` (not `_grammar()`) to preserve the original post-generation-grammar semantics — sound and conservative.
Assessment: trivial, fixed correctly. Accept.

### efficiency-1 — Fixed
Claim: `_py_format` ran the full parse → unparse → render pipeline per (input, config); parse+unparse depend only on `text`, so 8 of 16 cases redo the heavy pure-Python parse for no added coverage. Consequence: redundant test-suite wall time, growing linearly with configs.
HEAD: new `@functools.cache def _py_doc(text)` does parse+unparse (config-independent); `_py_format` reduces to `render_doc(_py_doc(text), RendererConfig(...))`. Matches the reviewer's fix direction.
Correctness check (the one fix with a safety implication — a shared Doc is rendered under multiple configs): verified `Renderer.render` (renderer.py:47-145) is read-only over the Doc — it builds a fresh `result` list and work queue, wraps input in a new `Group(doc)` (line 74), reads only `.content`/`.docs`/`.indent`/`.blank_lines`, never assigns to a Doc field; `_fits` operates on queue copies; config lives on the Renderer, not the Doc. Caching one Doc across configs is safe. The efficiency reviewer independently vouched for the same read-only property.
Assessment: correct and safe, low severity. Accept.

## Disputed items

None.

## Approved

5 findings (6 reviewer entries; errhandling-1/test-1 deduped): all Fixed, all verified — errhandling-1/test-1, test-2, reuse-1, quality-1, efficiency-1. No TODO or Won't-Do dispositions. Correctness + security: no findings.

---

## Verdict: APPROVED

Every disposition is Fixed and verified present in HEAD against its finding; the one fix with a correctness implication (efficiency-1's shared-Doc caching) is sound — the renderer does not mutate the Doc. No disputed items.
