<!-- Concise. Precise. Complete. Unambiguous. No padding. -->

# Judge verdict — ship-gate (user-revision)

Phase: ship-gate user-revision. Base 854e1ad..HEAD f1d9745. Round 1.
Directive: notes-shipgate-user.md (authoritative). Disposition: dispositions-shipgate.md.

## Other findings walk

### shipgate-user — Fixed (the lone directive)
Directive: label-compare sites in `fltk2gsm.py` must read as clean `cst.Items.Label.NO_WS` — no `_cst_const` alias. Consequence (stated): `_cst_const` form is the visible counterexample to AC10's promise of clean downstream user code; while it stands, the in-tree proof of clean user code is false, so the phase is not done.

Disposition: Fixed. Mechanism — drop the `fltk_cst as _cst_const` runtime alias and the `_DEFAULT_CST` cast; import `fltk_cst as cst` unconditionally; keep the `if TYPE_CHECKING: import fltk_cst_protocol as cst` shadow so pyright sees the Protocol type while runtime gets the concrete enum. `from __future__ import annotations` (head line 1) makes the redefinition lazy/safe.

Evidence (diff `fltk/fegen/fltk2gsm.py`, range 854e1ad..f1d9745):
- The exact site the user flagged now reads `cst.Items.Label.NO_WS` / `WS_ALLOWED` / `WS_REQUIRED` (diff lines 46-48). Directive met verbatim.
- All 10 prior `self.cst.` / `_cst_const.` label-compare sites (`Items.Label.*`, `Disposition.Label.*`, `Quantifier.Label.*`) now read `cst.X.Label.Y`.
- Head import block confirmed: `from fltk.fegen import fltk_cst as cst` unconditional; `fltk_cst_protocol as cst` under `TYPE_CHECKING`.
- Whole-tree `_cst_const` sweep: `grep -rn _cst_const` (excluding docs/adr) returns nothing. Alias fully removed, not merely renamed at one site.
- Signature change `Cst2Gsm(terminals, cst=...)` → `Cst2Gsm(terminals)` does not break callers: all 11 call sites (`plumbing.py`, `genparser.py`, `genunparser.py`, `runbs.py`, tests) already passed terminals-only; none injected `cst`. No collateral regression.
- Runtime-protocol guard intact: `test_fltk2gsm_does_not_import_protocol_at_runtime` (`fltk/fegen/test_cst_protocol.py:442`) still present; runtime `cst` binds to concrete `fltk_cst`, protocol absent from runtime namespace.
- Independently-verified gate: make check exit 0 (852 passed, 0 pyright errors, ruff clean).

Assessment: fix addresses the directive's consequence at the named line and across the tree; type-checker separation preserved (Protocol shadow retained); no caller breakage; gate green. Accept.

## Disputed items

None.

## Approved

1 directive: 1 Fixed verified.

---

## Verdict: APPROVED

User directive satisfied. Label-compare sites read clean `cst.Items.Label.NO_WS`; `_cst_const` removed tree-wide; Protocol/concrete type separation preserved; make check exit 0. HEAD f1d9745.
