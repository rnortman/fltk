# Dispositions: design review round 1 — cst-named-mutators

Style: concise, precise, complete, unambiguous. No padding. All docs in this workflow follow this style.

Findings from `notes-design-design-reviewer.md`. All four verified against source before disposition (Makefile:147-186 gencode target; `crates/fltk-cst-core/src/cross_cdylib.rs:256-281` `extract_span`; `gsm2tree_rs.py` `extract_from_pyobject` span branch at 575; `registry.rs:32-34,137` weak-valued dict + `snapshot`). All accurate.

design-1:
- Disposition: Fixed
- Action: §2.6 rewritten — replaced the five-file list with "run `make gencode` (Makefile:147-186)" plus the full enumerated artifact set (4 Python CST+protocol pairs, 6 Rust CST outputs incl. `fegen_cst.pyi` and the `fltk-cst-spike` cp), and an explicit warning that partial regeneration fails `make check` cheat-detection and the `rust_cst_fegen` staleness check.
- Severity assessment: Without the fix, an implementer regenerating only the listed files commits generator/artifact drift across ~8 files; caught by `make check` but invites hand-patching generated code to "fix" the diff.

design-2:
- Disposition: Fixed
- Action: §2.2 — replaced the inaccurate "Mirror of Rust behavior" sentence with a dedicated paragraph: node classes are symmetric; span acceptance is deliberately asymmetric (Python accepts `terminalsrc.Span` + `fltk._native.Span` because the `pyrt.span` backend selector can place native spans in Python-backend trees; Rust accepts only native spans via `extract_span` and rejects `terminalsrc.Span` with the unsupported-child-type TypeError). §4.2 — added a bullet excluding span hand-in from the exact-parity matrix and specifying per-backend span-acceptance tests instead.
- Severity assessment: Verified real: `extract_span` accepts only the local pyclass or cross-cdylib `fltk._native.Span`; a `terminalsrc.Span` falls to the generic TypeError. Unfixed, a parity-test author following the "mirror" framing writes a shared rejects-foreign-span test that fails on Python, or ships an undocumented divergence in API sold on exact parity.

design-3:
- Disposition: Fixed
- Action: Adopted the conforming alternative rather than ratifying the divergence. §2.3 — new shared index-handling paragraph: pymethods take `index: &Bound<PyAny>`, normalize via `__index__` semantics, attempt `i64`; on overflow, sign decides (insert clamps; remove_at/replace_at raise the pinned IndexError formatting the original value via `str()`); no `OverflowError` escapes. §2.4 — Python side converts via `operator.index` to match. §2.2 table — non-index-able index row updated. §3 — beyond-`i64` bullet rewritten as identical cross-backend behavior. §4.2 — beyond-`i64` cases added to the parity matrix. §5 — "divergence accepted" removed.
- Severity assessment: Request's "index semantics must match between backends and be pinned by shared tests" was violated by the accepted `OverflowError` divergence; practically negligible per-tree, but downstream `except IndexError` portability broke on Rust for the edge. The fix costs one normalization step per call and removes the requirements deviation entirely.

design-4:
- Disposition: Fixed
- Action: §4.3 GC-sanity item replaced with a registry-eviction test: assert the child's entry is present in a registry snapshot before, then absent after `clear()` + handle drop + GC (plus the weakref-dead check, which now pins that `clear()` leaks no strong handle refs). Verification during fix found `registry::snapshot` has no Python binding anywhere (`src/lib.rs` exports none); §2.3 gains an emitted `#[pyfunction] _registry_snapshot()` per generated module (per-cdylib registry static; test/debug-only, omitted from `.pyi`).
- Severity assessment: Reviewer correct: the weak-valued registry collects the handle whether or not `clear()` ran, so the original test was vacuous — false confidence in the §2.5 no-corruption claim. The replacement actually observes self-eviction; the missing-binding discovery means the original test was not merely vacuous but unimplementable as specified.

Additional fixes made during response (not reviewer findings): stale internal cross-references §5.1→§4.1 (collision test) and §5.2→§4.3 (identity tests).
