# Dispositions — design gate (user challenge)

Concise. Precise. Source-backed. Audience: smart LLM/human. No padding.

User note: `./notes-design-user.md`. Design: `./design.md`. Requirements: `./requirements.md`.

The user contends the Rust `.pyi` cannot be deferred — that the backend-agnostic Protocol scheme does not actually work for the Rust backend without it. This was treated as a real feasibility challenge and verified empirically against pyright 1.1.402 (the repo's pinned version) and the working tree, not argued from authority.

---

## Empirical method

Reconstructed the design's exact static situation in isolated fixtures and ran `uv run pyright --outputjson`:

- A `CstModule` Protocol with `@property def Grammar(self) -> type[GrammarNode]: ...` (etc.) and per-node `*Node` Protocols, matching the design's prescribed shape (design.md "New generated artifact", "DI boundary").
- A `Cst2Gsm`-like consumer annotating `cst: CstModule` and `visit_*` params as `*Node`.
- The **Rust injection site** modeled faithfully: `pr.cst_module` is statically `types.ModuleType`. Verified against the real type: `ParserResult.cst_module: types.ModuleType` (`fltk/plumbing_types.py`), and the Rust classes are loaded by `importlib.import_module` and injected at runtime (`plumbing._load_rust_cst_classes`, `plumbing.py:79-108`; `generate_parser` Rust branch, `plumbing.py:240-246`). Pyright never sees the Rust classes at any site.

Results (line numbers are the fixtures'):
1. **No-cast Rust injection** (`Cst2Gsm(cst=module)` with `module: ModuleType`) → `reportArgumentType`: "ModuleType cannot be assigned to parameter cst of type CstModule." The cast is genuinely required.
2. **With the design's documented cast** (`cast("cstp.CstModule", pr.cst_module)`) → clean.
3. **`reveal_type` of the cast result → `CstModule`**, not `Any`. The cast is a *narrowing* `ModuleType→CstModule` cast, not `cast(Any, …)`; it does **not** poison downstream checking.
4. **Downstream member access through the cast result** → `cst.Grammar : type[GrammarNode]`, `cst.Items : type[ItemsNode]` (fully typed, non-`Any`).
5. **Wrong access on the Rust-injected path** (`m.Grammar.does_not_exist` where `m` is the cast Rust module) → `reportAttributeAccessIssue` flagged. B6's "deliberately-wrong access is flagged" holds *on the Rust path* via the Protocol alone.

---

## The boundary, traced exactly

**Where it works (no `.pyi` needed):**
- The injection site `plumbing.py:171` (`Cst2Gsm(terminals.terminals, cst=pr.cst_module)`) type-checks via one documented narrowing cast `cast("CstModule", pr.cst_module)`. Necessary (result 1) and sufficient (result 2).
- *Every* consumer downstream of the cast — `Cst2Gsm.visit_*` and any future code holding the CST by injection — is checked against the `CstModule`/`*Node` Protocol. Member access is fully typed (results 3–4); wrong access is flagged (result 5). This is true **identically** whether the Python or the Rust module is the injected value, because after the cast pyright sees `CstModule` in both cases. That is precisely B6 swappability, and it is statically enforced for the Rust path.

**Where it does not work (what the `.pyi` would add):**
- The cast at the injection site **erases the Rust module's actual runtime surface.** Pyright cannot verify that the Rust extension *genuinely satisfies* `CstModule` — i.e. that `rust_ext.Grammar` really exposes `children_rule()`, `span`, etc. with matching types. If the Rust generator emitted a node missing a method the Protocol declares, the cast would hide it and the mismatch would surface only at runtime.
- That verification — "the static surface pyright sees for the Rust backend matches its real PyO3 surface" — is **exactly B4 for the Rust backend** (requirements lines 60-67) and the second half of B2 acceptance (line 44). A Rust `.pyi` (or equivalent compiled-surface check) is the *only* thing that closes it.

**Critical architectural fact that makes the gap narrow:** there is **no code path in the tree that holds Rust CST nodes by a concrete imported Rust type.** The Rust module is always `types.ModuleType` (`ParserResult.cst_module`), reached only through the agnostic Protocol (after the boundary cast) or through dynamic `hasattr`/`getattr` in tests (`test_plumbing.py:464,514` — not type-relevant). So the `.pyi` is *never* needed to **write or check an annotation** anywhere. Its sole function is B4-Rust *accuracy verification*. The user's framing — "none of this will work without the .pyi" — is empirically false for annotation authoring and checking (results 1-5); it is true only for the deferred accuracy guarantee.

---

## Disposition

user-1 (the `.pyi` cannot be deferred):
- Disposition: Won't-Do (deferral upheld; rust-cst-pyi stays a TODO, not pulled into this cycle)
- Action: No change to the design's scope decision. Strengthened the design's justification for the deferral with the empirical trace above — see design edits below so the doc itself carries the proof, not just this dispositions file.
- Severity assessment: If wrongly pulled in, the cycle absorbs a Rust `.pyi` generator on `gsm2tree_rs.py`/`gen-rust-cst` plus a compile-import-pyright verification harness — exactly the over-build requirements B3a explicitly warns against ("Do not over-build a Rust `.pyi` + compile-and-import test harness unless design judges it necessary for B1's Rust-injection acceptance," line 58). The empirical check shows it is **not** necessary for B1's Rust-injection acceptance: the injection site type-checks with the Protocol + one cast (results 1-2), and B6 swappability is statically enforced on the Rust path (result 5).
- Rationale (Won't-Do): Three source-backed legs.
  1. **B1 Rust-injection acceptance is met without the `.pyi`.** B1's third acceptance bullet (requirements line 36) requires the annotation form to "remain valid when `Cst2Gsm` is constructed with a non-default (Rust-backed) CST module — i.e. the static type used for annotation and the injected runtime module are compatible per the typing mechanism." Verified: `cast("CstModule", pr.cst_module)` makes the injected module compatible with the `CstModule` annotation (results 1-2), and the `visit_*` annotations stay valid and fully typed (results 3-4). No `.pyi` participates.
  2. **B6 backend-agnostic swappability is statically checkable for the Rust backend without the `.pyi`.** B6 acceptance (line 84): "Pyright accepts the same annotated `Cst2Gsm` source whether the default Python backend or the Rust backend is the one the static type is checked against, **to the extent both backends are statically described this cycle (Rust per B3a/B4 scoping).**" After the boundary cast both backends present as `CstModule`; the same source checks identically and wrong access is flagged on the Rust path (result 5). The clause "to the extent … statically described this cycle" is the requirements' own explicit hook for deferring the Rust description — the user's "statically checkable for the Rust backend" is satisfied at the annotation/consumer level, which is the level B6 governs ("code above the selection level"). What is *not* checked — that the Rust runtime surface matches — is B4, not B6.
  3. **B4-Rust is conditional by the requirements' own terms; the cast is a narrowing cast, not a `cast(Any)` B5 violation.** B4 acceptance line 67: the two accuracy checks "are mandatory for the Python dataclass backend … For the Rust backend they are mandatory **only if Rust stub generation is in scope this cycle per B3a; otherwise they are deferred** to the increment that adds Rust stub generation." B3a (lines 54-58) leaves that scope to design and warns against over-building. The design defers it (open question `Rust .pyi increment`, `TODO(rust-cst-pyi)`). The only escape hatch introduced is one documented narrowing cast at the genuine `ModuleType` boundary — `reveal_type` confirms it yields `CstModule`, not `Any` (result 3) — which B5 (line 75) and `di-boundary-escape` (line 112) explicitly permit ("a single documented boundary cast is acceptable if unavoidable"). It is unavoidable: bare `ModuleType→CstModule` is rejected (result 1). No one should pull a full Rust `.pyi` + compile-import harness into this cycle to avoid a cast the requirements already sanction, when doing so buys nothing for B1/B6 and is the precise over-build B3a forbids.

---

## What changed in the design

To make the design carry its own empirical defense (so the deferral is not "out of scope" hand-waving), edited `design.md`:

- "Proposed approach" / mechanism paragraph: added the empirical trace that the Rust injection site (`plumbing.py:171`) type-checks via the documented narrowing cast against `CstModule` (no `.pyi`), that the cast yields `CstModule` not `Any`, and that wrong access is flagged on the Rust path — so B1-Rust-injection and B6 are met without a Rust `.pyi`.
- "Generator wiring" / Rust-path bullet and "Open questions" / `Rust .pyi increment`: stated precisely the single thing the deferred `.pyi` adds (B4-Rust *accuracy* — verifying the real PyO3 surface satisfies `CstModule`), and that no in-tree consumer holds Rust nodes by concrete type (`ParserResult.cst_module: types.ModuleType` always), so the `.pyi` is never on the annotation-authoring/checking path.

No scope change. No re-invocation of cleanup-editor warranted (edits are localized reinforcements, not structural).
