# Request: rust-cst-pyi

Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

**Type of work:** new feature (codegen + verification test); the largest item in this batch.

**Background.** FLTK emits Rust CST source from a grammar (`gen_rust_cst` command, `fltk/fegen/genparser.py:264-287`; generator `gsm2tree_rs.RustCstGenerator`). There is currently NO static type surface (`.pyi`) for the compiled Rust extension, and NO test that the real compiled PyO3 surface satisfies the shared `CstModule` Protocol (`fltk/fegen/fltk_cst_protocol.py:750+`). On the Rust path, nodes cross into typed code via a boundary cast (`cast("cst.Grammar", result.result)` in `plumbing.py`), which the type checker takes on faith — so a real mismatch between the Rust extension's surface and what consumers' typed code expects is invisible.

**Fix shape (chosen).** Two parts; **Part 1 is the priority, Part 2 may be deferred** (see open-question note):
- **Part 1 — `.pyi` emitter.** Add a generator (alongside `RustCstGenerator` / driven from the same GSM) that emits a `.pyi` stub mirroring the Rust PyO3 surface: one class per grammar rule with `kind`, `span`, `children`, and the per-label accessor methods; module-level `NodeKind`, `Span`, and a `CstModule`-conforming surface. Wire it into the `gen-rust-cst` CLI (emit the `.pyi` next to the `.rs`). All needed info is already in the GSM (node names, label names, accessor names, span presence).
- **Part 2 — B4 verification test.** A test that imports a built Rust CST extension and runs pyright asserting the surface satisfies `CstModule` WITHOUT a cast (i.e. the `.pyi`/real surface genuinely conforms). This needs the Rust toolchain in the test path and a decision on compile-on-the-fly vs. reusing a prebuilt extension.

**Load-bearing constraints.**
- The `.pyi` must reflect the *actual* PyO3 surface the Rust generator emits (cross-check against `gsm2tree_rs.py`'s emitted methods/fields), not the Python concrete backend's surface where they differ (e.g. Rust `Span` has no `.start`/`.end`; label-free nodes have no `Label`).
- `CstModule` is generated per-grammar by `gsm2tree.CstGenerator.gen_cst_module_protocol` and committed (e.g. `fltk_cst_protocol.py`); the `.pyi`'s job is to let pyright confirm the real Rust surface matches that Protocol.
- Keep the existing `gen-rust-cst` `.rs` output unchanged; the `.pyi` is additive.
- Designer/implementer should treat the related "Loose end A" (below) as a known inconsistency to AVOID relying on.

**Known inconsistency to account for (do not propagate).** Validation found ADR `2026/06/05-cst-type-annotations-regression` and a comment in `test_cst_protocol.py` describe a dependency-injection wiring — `Cst2Gsm(..., cst=pr.cst_module)` and a `_DEFAULT_CST` symbol in `fltk2gsm.py` — that does NOT exist in shipped code: `Cst2Gsm.__init__` takes only `terminals`, and both backends just `cast` and call `visit_grammar`. Do not design against that phantom wiring. (A separate cleanup of the stale references is being tracked outside this workflow.)

**Non-goals.** No change to the `.rs` generation. No change to the runtime parse path or the boundary cast itself (Part 2 only *verifies* it). Do not implement the phantom `cst=`/`_DEFAULT_CST` DI.

**OPEN QUESTION for the user (designer: surface explicitly).** Scope of Part 2 — should this workflow (i) do both Part 1 and Part 2 now, (ii) do Part 1 only and file Part 2 as a follow-up, or (iii) for Part 2, compile a Rust extension on-the-fly in the test vs. reuse the prebuilt `fegen_rust_cst`/`fltk._native` surfaces? The orchestrator flagged at triage that deferring Part 2 is entirely reasonable. Designer should lay out the options and a recommendation rather than silently picking.

**Verification.** `gen-rust-cst` emits a `.pyi` matching the real surface; pyright over the `.pyi` (and, if Part 2 in scope, over the compiled extension) confirms `CstModule` conformance without a cast; `uv run pytest && uv run pyright`. `TODO.md` entry and the `TODO(rust-cst-pyi)` comment (`genparser.py:279`) removed once the implemented scope lands (if Part 2 deferred, leave a narrowed follow-up TODO per the user's scope decision).

**Exploration:** `exploration.md` in this dir (full validation incl. the phantom-DI finding).
