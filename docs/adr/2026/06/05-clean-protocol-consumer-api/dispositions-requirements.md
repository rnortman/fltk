# Dispositions: requirements review — Clean Protocol-Only Consumer API

> Concise. Precise. Complete. Unambiguous. Round 1.

All six findings fact-checked against exploration.md and request. All grounded; none hallucinated. All Fixed.

## requirements-1
- Disposition: Fixed
- Action: In scope — promoted the traversal/narrowing bullet to **(Load-bearing.)**, stated it is a *new typed traversal/narrowing surface* distinct from enum-value work, and cited exploration §3 line 208 / §5 line 204 establishing that enum values alone do not remove the `:63`/`:75` casts. System behavior §"Clean interleaved traversal" — added a bullet stating the narrowing is delivered by that surface, not by enum values.
- Severity assessment: High. Without this, a designer ships additive enum values, satisfies AC 6/7, and still leaves the gating-example cast in place — gating criterion violated, two hard requirements jointly unmet.

## requirements-2
- Disposition: Fixed
- Action: Open questions `protocol-label-type-change` — replaced "Default assumed: A" with a "Status: A is target, NOT a settled default; must be validated in design" block. Names the two validation conditions (canonical-name round-trip with `object`-typed member; `test_boundary_probe_documents_label_mismatch` kept passing — test is in play for A, not only B) and requires explicit user sign-off before any A→B fallback.
- Severity assessment: High. "Structural change" + "non-breaking" are in co-located tension; an unvalidated default-A lets a designer silently flip to an unaccepted break or ship a forbidden in-module suppression.

## requirements-3
- Disposition: Fixed
- Action: Acceptance criteria — added AC 11 asserting the capabilities proven on `fltk2gsm.py` (AC 1-5, 8) are general protocol-module properties available to any protocol-only consumer, with `fltk2gsm.py` as worked instance not special case.
- Severity assessment: Medium. AC 1-5 were file-bound; without the general AC, a point solution could pass acceptance while the request's primary intent (general out-of-tree consumers) is under-delivered.

## requirements-4
- Disposition: Fixed
- Action: Constraints "No runtime-cost regression" — reworded from absolute ("dependency that was previously absent") to the intended bar: no eager *concrete-backend* import, no non-trivial cost; explicitly permits the protocol module's own lightweight enum value objects.
- Severity assessment: Low. Absolute phrasing could be read to forbid the feature's own necessary (light) runtime footprint or invite over-engineered laziness.

## requirements-5
- Disposition: Fixed
- Action: Out of scope — added a bullet excluding making `fltk2gsm.py` *execute* against Rust CST (no Rust baseline exists; it consumes the Python backend per exploration line 107). AC 9 — rescoped to the backend it actually consumes; cross-backend guarantee confined to AC 7 (equality/hash).
- Severity assessment: Medium. "Under both backends" had no Rust baseline for `fltk2gsm.py`; risked silent scope creep (Rust-portability work in a cleanup task) or an unverifiable, quietly-dropped criterion.

## requirements-6
- Disposition: Fixed
- Action: Gating criterion section — added "Substitution does not satisfy the criterion": trading a CST-forced `cast` for `# type: ignore` / `# pyright: ignore` / `# noqa` is still a CST-forced suppression and fails the gate. Mirrored in System behavior §"Clean interleaved traversal".
- Severity assessment: Low-Medium. Without naming the failure mode, a designer could swap a cast for an ignore comment, claim AC 2 (zero casts), and violate the spirit of AC 3.
