# Dispositions — prepass (slop + scope)

## slop-1
- Disposition: Fixed
- Action: Replaced the three-line redundant/self-contradictory comment above `_RUST_IDENT_RE` with a single accurate one-liner (`fltk/fegen/gsm2lib_rs.py:15`). Committed in 25bbfef.
- Severity assessment: Cosmetic only; no behavioral impact. Leaves a confusing comment in the source that would puzzle readers.

## slop-2
- Disposition: Fixed
- Action: Moved the five-line UNKNOWN_SPAN rationale prose from emitted generated output into a Python comment above the emission block in `gsm2lib_rs.py` (lines 120-124). The generated `src/lib.rs` now carries only the concise one-line description. `src/lib.rs` regenerated to match. Committed in 25bbfef.
- Severity assessment: Moderate: design-rationale prose describing current codebase state was baked into generated output, making it visible to readers of generated files and subject to going stale. Moved to its correct home (the generator source).

## slop-3
- Disposition: Fixed
- Action: Removed the stale "(verbatim from src/lib.rs)" parenthetical from the `# --- UNKNOWN_SPAN static ---` section header comment in `gsm2lib_rs.py:119`. Committed in 25bbfef.
- Severity assessment: Cosmetic only; no behavioral impact. The parenthetical described an earlier authoring action, not the code's intent.

## slop-4
- Disposition: Won't-Do
- Action: No change.
- Severity assessment: A `// @generated` header would help future maintainers recognize that `src/lib.rs` must not be hand-edited. However, the peer generated `.rs` files in this repo (`src/cst_generated.rs`, `src/cst_fegen.rs`) carry no such header; adding one only to `src/lib.rs` would be inconsistent with the established convention. The design (§2.7) explicitly models `src/lib.rs` after those files' same "drift posture." Adding `@generated` markers to generated `.rs` files generally is a separate, out-of-scope decision.
- Rationale (Won't-Do): `src/cst_generated.rs` and `src/cst_fegen.rs` — the canonical generated `.rs` artifacts in this repo — have no `@generated` header (verified by reading both files). The design §2.7 says `src/lib.rs` "becomes generated output with the **same drift posture** as the other generated `.rs` files." Applying `@generated` only to `src/lib.rs` violates that parity. Adopting it repo-wide would be a distinct decision; this finding does not justify the inconsistency.

## scope (notes-prepass-scope.md)
- No findings.
