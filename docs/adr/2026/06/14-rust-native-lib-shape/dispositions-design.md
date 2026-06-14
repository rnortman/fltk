# Dispositions — design review (round 1)

Design: `design.md`
Reviewer notes: `notes-design-design-reviewer.md`
All six findings fact-checked against source and the (already-revised) design. None refuted the design's thesis; all were gaps/inconsistencies and are now addressed in the design text.

---

design-1:
- Disposition: Fixed
- Action: §2.4 (design.md:212-222) and §4 (design.md:380-385) corrected. Every reference now reads `fltk/fegen/test_gsm2lib_rs.py` (not `tests/test_gsm2lib_rs.py`). §2.4 explicitly calls out that deleting `native_spec()` is a hard dependency for the file's line-7 top-level import (`from fltk.fegen.gsm2lib_rs import LibSpec, RustLibGenerator, Submodule, native_spec`), so `native_spec` must be dropped from that import or the whole module fails to collect. The `test_native_spec_*` block is now described as the ~129-246 range (eight-plus enumerated functions), not "a few cases."
- Severity assessment: Left uncorrected, an implementer searches a nonexistent path and may miss the import-line update, leaving `test_gsm2lib_rs.py` with a whole-file pytest collection error. Material under-specification of the test-update plan.

design-2:
- Disposition: Fixed
- Action: §2.3 (design.md:155-165) resolves the inconsistency by committing to one wiring: `register_submodule(m, "cst", cst::register_classes)`, matching every existing fixture, yielding `from poc_cst.cst import Identifier, Items`. The "register at top level" alternative is struck, with an explicit note that top-level registration would be a one-off contradicting the uniform-shape invariant. §4 (design.md:376-379) and the §3 edge case (design.md:329-334) updated to `from poc_cst.cst import ...`.
- Severity assessment: Left unresolved, the §4 test text and §2.3 lib.rs shape disagree; the implementer's import either fails or forces a non-standard second wiring convention — the opposite of the refactor's uniformity goal.

design-3:
- Disposition: Fixed
- Action: §2.1 (design.md:89-94) reframed. The `poc_cst` comment block (__init__.pyi:9-14) is now stated to be deleted **because it becomes factually false** post-refactor (it asserts PoC classes live at `fltk._native.poc_cst`, which §2.3 removes), not as cosmetic header trimming. Notes that leaving it would actively mislead.
- Severity assessment: Low. Misframing risked an implementer leaving a stub comment that falsely asserts `fltk._native.poc_cst` exists.

design-4:
- Disposition: Fixed
- Action: §2.5 (design.md:274-281) now explicitly requires a **fifth** `cargo deny --manifest-path tests/rust_poc_cst/Cargo.toml check --config deny.toml` line alongside the existing four, with the rationale that `tests/rust_poc_cst` is a standalone workspace (own `Cargo.lock`) and therefore not covered by the root deny check. The §3 edge case (design.md:349-352) retained as the drift backstop. Note: the design promotes the fegen crate to `crates/fegen-rust`, so the repointed deny line is `crates/fegen-rust`, not `rust_cst_fegen`.
- Severity assessment: Without the explicit fifth line, the new standalone crate silently escapes the supply-chain gate — the exact "drops a coverage lane" risk §3 warns about.

design-5:
- Disposition: Fixed
- Action: §2.3 (design.md:175-179) and §2.5 (design.md:249-262) reversed the prior "drop the cp" recommendation. The spike `cp` is now **kept**: the PoC fixture is canonical (python-on), the spike copies its `cst.rs` (python-off), preserving byte-identity at zero cost rather than relying on a diff-gate across two independent `gen-rust-cst` invocations. The §3 edge case (design.md:353-359) updated to state the spike copies from the fixture so the two are identical by construction, with `git diff` after `make gencode` as a backstop, not the primary guarantee. The design now explicitly acknowledges this is the one grammar where "exactly one generated CST" cannot be fully reached (python-on/off genuinely need two compiled copies).
- Severity assessment: Dropping the `cp` would relocate, not eliminate, the duplication-with-drift fragility the refactor criticizes — a robustness regression for the one grammar that must coexist in two build modes.

design-6:
- Disposition: Fixed
- Action: §2.2 (design.md:122-136) now treats stub resolvability as a first-class acceptance concern. It cites the actual pyright config (`include = ["fltk", "*.py"]`, `stubPath = ""`, pyproject.toml:50,52), notes the `--pyi-output` flag controls only the write path (not resolution), and requires the stub to land inside the `fltk` tree (recommended: `fltk/_stubs/fegen_rust_cst/cst.pyi`) with a matching `[tool.pyright]` `stubPath`/`extraPaths` edit. That `pyproject.toml` edit is declared part of this design's acceptance. The choice between option (a) and leaving the stub beside the crate with an `include`/`extraPaths` extension is surfaced as OQ-3 (design.md:410-419). §2.5 (design.md:242-246) and §3 (design.md:339-348) and §4 (design.md:386-389) updated to route `--pyi-output` to the pyright-resolved location and to verify resolution, not just emission.
- Severity assessment: Without confirmed pyright resolution, the relocated stub goes dead and the `fltk.fegen.fltk_cst_protocol` conformance check silently stops running — losing the stub's entire reason to exist.
