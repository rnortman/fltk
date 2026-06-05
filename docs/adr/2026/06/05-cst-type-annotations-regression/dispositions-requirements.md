# Dispositions: requirements review — CST type annotations regression

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Round 1. Notes file: `notes-requirements-requirements-reviewer.md`. Fact-checked against request + exploration + working tree (Rust backend status was the load-bearing unknown; verified directly).

## Fact-check summary (working-tree verification)

The reviewer's central premise — "exploration does not confirm a compiled, injectable Rust CST exists" — is **partly wrong on existence, right on the gap that matters**:
- A compiled Rust/PyO3 extension `fltk._native` exists (`fltk/_native.abi3.so`, built from `src/cst_generated.rs` via `gsm2tree_rs.py`).
- It **is** injected into `Cst2Gsm`: `plumbing.py:171` runs `Cst2Gsm(..., cst=pr.cst_module)` on the `rust_fegen_cst_module` opt-in path. So the Rust path is real and run against `fltk2gsm`, not aspirational.
- BUT it is caller-opt-in (not default), loaded dynamically by dotted name, and **no stub/protocol generator exists anywhere** (`find ... *.pyi` → none in-tree; `gsm2tree_rs.py` has no stub/Protocol emission). The Rust CST is fully `Any` statically.
- `fltk_cst.py` is the default backend `fltk2gsm` runs against (`plumbing.py:144`), confirmed clean/unregenerated.

Net: requirements-1's existence claim is softened, but its scope-balloon risk and B4-untestability concern survive (the missing stub generator is the real cost). requirements-3 is fully confirmed and load-bearing.

---

requirements-1:
- Disposition: Fixed
- Action: Added section **B3a — Rust backend status (precondition, confirmed)** recording verified facts: Rust CST exists and is injected on the opt-in path, but no stub generator exists and the surface is statically `Any`. Scoped B4 Rust-surface verification as achievable-but-requiring-a-stub-generator, with explicit permission to make Rust `.pyi` emission thin/deferred. Edited B2 acceptance and B4 acceptance to make the Rust checks mandatory only if Rust stub generation is in scope this cycle; Python-backend checks remain mandatory.
- Severity assessment: High value. Without this, the designer could build a full Rust `.pyi`-generation + compile-and-import test harness this cycle when the in-spirit deliverable is a shared static type validated against the Python backend. The verification corrected the reviewer's "may not exist" to "exists but unstubbed," which sharpens rather than weakens the scope guidance.

requirements-2:
- Disposition: Fixed
- Action: Rewrote the **Dual-backend parity** constraint as **Dual-backend typeability** — the request-faithful weaker form ("`visit_*` annotations must typecheck for whichever backend is injected"), with single-shared-type demoted to *preferred*, not required.
- Severity assessment: Medium. The original near-design-decision could push the designer to unify Python-dataclass and PyO3 surfaces into one nominal hierarchy (non-trivial, possibly blocked by the missing Rust stub). Relaxing to a structural-Protocol-or-per-backend bar keeps the request satisfiable with less risk.

requirements-3:
- Disposition: TODO(fltk-cst-regen-squeeze)
- Action: Added open question **fltk-cst-regen-squeeze** to the requirements doc capturing the confirmed conflict: `fltk2gsm` runs by default against the clean-but-never-regenerated `fltk_cst.py`; B3 wants toolchain-generated artifacts; regenerating `fltk_cst.py` reintroduces Regression-2 style violations, breaking Backward-compat / `make check`. Laid out options (i) sidecar generated artifact leaving `fltk_cst.py` untouched [proposed default], (ii) pull in minimal style fix, (iii) one-off hand-edit. Needs user decision.
- Severity assessment: High. This is a genuine squeeze between B3 ("no manual post-generation editing"), Backward-compat, and the out-of-scope Regression-2 fix. Unresolved, the designer is forced to silently pick one of three paths with different scope/contract implications. Surfacing it at the next gate prevents an accidental `make check` break or an out-of-scope expansion.

requirements-4:
- Disposition: Fixed
- Action: Edited the B1 example to be mechanism-neutral — annotation spelling "per chosen mechanism — e.g. a bare imported `Grammar`, or an attribute-on-Protocol like `<CstType>.Grammar`; B1 does not prejudge this," cross-referencing the `mechanism` open question.
- Severity assessment: Low. The original `<CstType>.Grammar` subtly anchored on the Protocol-attribute form, mildly foreclosing the direct-import stub form. Neutralized to keep `mechanism` genuinely open.

requirements-5:
- Disposition: Fixed
- Action: Extended the **No runtime cost / no runtime import cycles** constraint to state CST-type annotations may rely on PEP 563 deferred / string-form evaluation, runtime evaluation is not required/forced, and a `TYPE_CHECKING`-only Protocol/stub import in an annotation must not raise `NameError` under the runtime `ModuleType` injection.
- Severity assessment: Low–medium. Pins an otherwise-implicit interaction (Protocol-typed `self.cst` annotation vs runtime `ModuleType` value) so the design can't accidentally produce a doc-compliant solution that typechecks but breaks import.

requirements-6:
- Disposition: Fixed
- Action: No structural change requested (reviewer affirms the project). Its one residual risk — Rust-backend present-existence/wiring — is resolved by the B3a section and routed through TODO(fltk-cst-regen-squeeze) and the `rust-stub-source` open question.
- Severity assessment: Low. Big-picture affirmation; the actionable sub-point folds into requirements-1/-3 dispositions above.
