# Judge verdict — design review

Style: concise, precise, complete, unambiguous. No padding. All docs in this workflow follow this style.

Phase: design. Doc: `docs/adr/2026/06/11-cst-named-mutators/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 4 findings, all dispositioned Fixed. No TODOs, no Won't-Dos.

## Findings walk

### design-1 — Fixed
Claim: §2.6 regenerated-artifact list named 5 files; `gsm2tree.py`/`gsm2tree_rs.py` changes touch every generated CST module (~13 artifacts per Makefile gencode target). Consequence: partial regeneration commits generator/artifact drift; `make check` cheat-detection and `rust_cst_fegen` staleness check fail, inviting hand-patching of generated code.
Design §2.6 now: "run `make gencode` (Makefile:147-186)", full enumerated set (4 Python CST+protocol pairs: fegen, bootstrap, toy, unparsefmt; 6 Rust outputs: `src/cst_fegen.rs`+`fegen_cst.pyi`, `src/cst_generated.rs`, `rust_cst_fixture`, `rust_cst_fegen`, `rust_parser_fixture`, `fltk-cst-spike` cp), plus explicit do-not-regenerate-a-subset warning naming both failure gates.
Cross-checked against Makefile:147-186: enumeration matches the target's CST/protocol/pyi outputs. Fix complete; reviewer's suggested shape adopted (both the `make gencode` directive and the enumeration).
Assessment: accept.

### design-2 — Fixed
Claim: §2.2 "Mirror of Rust behavior" misstated span acceptance as symmetric; Python accepts both span types, Rust (`extract_span`, `cross_cdylib.rs:256-281`) accepts native only. Consequence: shared rejects-foreign-span parity test fails on Python, or divergence ships undocumented.
Design §2.2 now: dedicated paragraph "Node classes are symmetric; span acceptance is deliberately asymmetric" — states Python accepts both (justified by the `pyrt.span` backend selector), Rust native-only with the exact TypeError, asymmetry forced by representation. §4.2 final bullet excludes span hand-in from the parity matrix and specifies per-backend span-acceptance tests.
Assessment: matches reviewer's suggested fix on all three points (explicit statement, justification, parity-matrix exclusion). Accept.

### design-3 — Fixed
Claim: accepted i64-overflow divergence (`OverflowError` on Rust vs clamp/`IndexError` on Python) contradicted request.md "index semantics must match between backends and be pinned by shared tests"; a cheap conforming alternative existed.
Design now adopts the conforming alternative rather than ratifying the deviation: §2.3 shared index-handling paragraph (`index: &Bound<PyAny>`, `__index__` normalization, sign-based overflow handling — insert clamps, remove_at/replace_at raise the pinned IndexError, no OverflowError escapes); §2.4 `operator.index` on Python; §2.2 table non-index-able row updated; §3 beyond-`i64` bullet rewritten as identical cross-backend behavior; §4.2 adds beyond-`i64` parity cases (`±10**25`); §5 divergence entry removed ("None" open questions).
Assessment: stronger than the minimum (removes the deviation instead of escalating it for ratification); all six touch points present and internally consistent. Accept.

### design-4 — Fixed
Claim: §4.3 GC-sanity test was vacuous — weak-valued registry (`registry.rs:32-34`) collects an unreferenced handle whether or not `clear()` ran; the test passed identically with `clear()` deleted.
Design §4.3 now: registry-eviction test asserting entry present in `_registry_snapshot()` before, absent after `clear()` + handle drop + GC, plus weakref-dead check, with explicit statement of the two properties pinned (no leaked strong refs; self-eviction). §2.3 adds the required `#[pyfunction] _registry_snapshot()` per generated module (per-cdylib registry static), test/debug-only, omitted from `.pyi`.
Verified the responder's new claim: `registry::snapshot` is `pub` at `crates/fltk-cst-core/src/registry.rs:137`; `src/lib.rs` contains no registry/snapshot binding (grep empty) — the binding addition is necessary, and its discovery confirms the original test was unimplementable as specified.
Assessment: reviewer's suggested fix adopted and made implementable. Accept.

### Additional non-finding fixes
Stale cross-references corrected (§2.1→§4.1 collision test; §2.5→§4.3 identity tests). Both references resolve correctly in the current doc. In-scope cleanup, no new content.

## Disputed items

None.

## Approved

4 findings: 4 Fixed verified.

---

## Verdict: APPROVED

All four dispositions verified against the revised design and source. No disputes.
