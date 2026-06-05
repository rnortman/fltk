# Judge verdict — design gate (user challenge)

Concise. Precise. Source-backed. No padding. Audience: smart LLM/human.

Phase: design (user-challenge adjudication). Doc: `./design.md`. Requirements: `./requirements.md`. User note: `./notes-design-user.md`. Round 1.

Challenge (user-1): the Rust `.pyi` cannot be deferred — "none of this will work without that." Disposition: Won't-Do (deferral upheld), with an empirical pyright trace added to the design.

## Findings walk

### user-1 — Won't-Do (deferral upheld)

**User's claim + implied consequence.** The backend-agnostic Protocol scheme does not actually function for the Rust backend without a Rust `.pyi`; consequence (implied) = B1 Rust-injection acceptance and B6 swappability are unmet, so deferral ships a broken feature.

**Disposition.** Won't-Do; `rust-cst-pyi` stays a TODO. Justified by an empirical pyright 1.1.402 trace (dispositions §"Empirical method", design.md:21) plus three requirements-sourced legs.

**Verification against code (ground truth):**
- `ParserResult.cst_module: types.ModuleType` — confirmed verbatim (`plumbing_types.py`, `cst_module: types.ModuleType`). Pyright sees a bare module, never a Rust class.
- Rust classes are loaded by `importlib.import_module(module_name)` and `setattr` onto a runtime `types.ModuleType` (`plumbing.py:97`, `232-246`, `_load_rust_cst_classes` :79-108). Dynamic load → pyright-invisible at every site. Confirmed.
- Injection site is exactly `plumbing.py:171`: `Cst2Gsm(terminals.terminals, cst=pr.cst_module)` where `pr.cst_module` is statically `ModuleType`. Confirmed.
- `Cst2Gsm.__init__(self, terminals, cst: ModuleType = _default_cst)` (`fltk2gsm.py:9`); runtime CST access is all on `self.cst` (`self.cst.Items.Label.NO_WS`, etc., :44-48). The annotation surface the design adds sits only on params; runtime stays on the injected module. Confirmed.

The architectural premise that makes the five fixture results follow — Rust CST is *only ever* held as `ModuleType`, reached through the agnostic Protocol after one boundary cast, never by a concrete imported Rust type — is independently true in the tree. Given that premise, a `ModuleType → CstModule` narrowing cast is the necessary and sufficient mechanism, and every downstream consumer is checked against the Protocol identically for both backends. The `.pyi`'s sole residual function is verifying the Rust *runtime* surface genuinely satisfies `CstModule` (that the cast masks no missing Rust member).

**Verification against requirements (the deferral hooks the disposition invokes are faithful, not bent):**
- B1 line 36: validity requires the static type and injected module be "compatible **per the typing mechanism**" — not that the Rust runtime surface be verified. The cast delivers exactly this compatibility. Faithful.
- B2 line 44: "If Rust stub generation is deferred per B3a, the shared static type must still be *defined* such that the Rust backend can satisfy it." Requirements explicitly contemplate deferral and demand only definability-satisfiability, which the Protocol meets. Faithful.
- B3a line 58: "Do not over-build a Rust `.pyi` + compile-and-import test harness unless design judges it necessary for B1's Rust-injection acceptance." The disposition shows it is not necessary for B1-injection (cast suffices). Faithful.
- B4 line 67: Rust accuracy checks "mandatory only if Rust stub generation is in scope this cycle per B3a; otherwise they are deferred." Faithful.
- B6 line 84: swappability accepted "to the extent both backends are statically described this cycle (Rust per B3a/B4 scoping)." The clause is the requirements' own deferral hook; the disposition does not over-read it. Faithful.
- B5 line 75 / `di-boundary-escape` line 112: "a single documented boundary cast is acceptable if unavoidable." The cast is unavoidable (bare `ModuleType → CstModule` is rejected — fixture result 1) and is a narrowing cast yielding `CstModule`, not `cast(Any)` (result 3), so it does not poison downstream checking and is not a B5 violation. Faithful.

**Is the rationale hand-wavy or does it leave the user's concern unaddressed?** No.
- The disposition concedes precisely the part of the user's concern that is correct — the cast erases the Rust runtime surface, so pyright *cannot* confirm the real PyO3 extension satisfies `CstModule` (dispositions §"Where it does not work"; design.md:21). It does not hide behind "out of scope." It pins the surviving gap to B4-Rust accuracy and shows B4-Rust is conditional by the requirements' own terms.
- The rest of the user's framing ("none of this will work") is shown false for the load-bearing capabilities: annotation authoring/checking (results 1-4) and B6 swappability with wrong-access flagged on the Rust path (result 5) all function via Protocol + one cast, no `.pyi`.

**Severity / rubric on the deferred work.** Worth doing (yes — B4-Rust accuracy is real). Requires a real increment (yes — a Rust-surface stub generator on `gsm2tree_rs.py`/`gen-rust-cst` plus a compile-import-pyright harness; B3a line 58 explicitly warns against over-building it now). Not a do-now one-liner. Critically, this cycle does **not** create or worsen the Rust-accuracy gap: the Rust module was already fully `Any` pre-cycle (B3a line 56); this cycle strictly improves matters (adds the Protocol, fully verifies the Python backend). So the "problem this iteration created cannot be silently deferred" rule does not apply. Deferral is legitimate.

**TODO bookkeeping.** `TODO(rust-cst-pyi)` is not yet in `TODO.md` (current entries end at `rust-cst-child-span-test`). This is a design gate, not a code phase: design.md:119-121 "TODOs introduced" commits to adding both the `TODO.md` entry and the `TODO(rust-cst-pyi)` comment at the `gen-rust-cst` emission site when implemented. Forward commitment, correctly scoped to implementation. No present-gate defect.

**Assessment.** The justification holds against the user's concern and the requirements. The deferral is sourced (code-confirmed premise + requirements-sanctioned hooks), the surviving gap is named honestly and bounded to B4-Rust accuracy, and pulling the `.pyi` in now is the precise over-build B3a forbids. User-1 Won't-Do is correct.

## Disputed items

None.

## Approved

1 finding (user-1): Won't-Do sound — deferral upheld. Design edits (design.md:21, :60, :111, :119-121) carry the empirical defense in-doc; localized reinforcement, no scope change.

---

## Verdict: APPROVED

The designer's deferral of the Rust `.pyi` withstands the user's challenge. Code confirms the load-bearing premise (`cst_module: types.ModuleType`, dynamic Rust load, injection at `plumbing.py:171`); requirements B2/B3a/B4/B6 contain explicit deferral hooks the disposition invokes faithfully; the surviving gap is correctly scoped to B4-Rust accuracy, which this cycle does not worsen. Not hand-wavy; the user's valid sub-point is conceded, the overreaching part refuted with sourced evidence.
