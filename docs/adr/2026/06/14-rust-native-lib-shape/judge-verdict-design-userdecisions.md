# Judge verdict — design (user-decision application)

Phase: design. Doc: `docs/adr/2026/06/14-rust-native-lib-shape/design.md`. Round 1.
Decisions source: `notes-design-user.md` (3 authoritative user calls). Dispositions: `dispositions-design-userdecisions.md`.

## Other findings walk

### user-decision-1 — OQ-1 (no rename; keep `fegen_rust_cst`) — Fixed
User decision: "No rename yet. Keep the existing import name."
Disposition claim: hedge removed in §2.2 and §5; name deliberately retained.
Evidence:
- §2 settled-decisions paragraph (design.md:73-74): "the relocated fegen crate **keeps** its importable name `fegen_rust_cst`."
- §2.2 "Module name" bullet (design.md:122-125): keep `fegen_rust_cst`; "no rename in this refactor." States the name is deliberately retained, not posed as a question.
- §5 entry (design.md:402-404): "keep `fegen_rust_cst`. No rename."
- Grep for "OQ-1"/"revisits"/"open question" over design.md: zero residual OQ-1 hedges.
- Consistency with the kept name: §2.2 (123), §3 (337-338), §4 (374) all use `fegen_rust_cst.cst`/`.parser`; matches the asserted importable name and the existing `tests/test_module_split.py:31-44` import sites.
Assessment: decision applied exactly; no residual hedge; downstream import references consistent. Accept.

### user-decision-2 — OQ-2 (promote out of `tests/` into `crates/fegen-rust/`) — Fixed
User decision: "Yes — move it out of tests/ into a real `crates/` crate."
Disposition claim: move stated directly; Makefile, make-check lanes, Bazel, cargo-deny all repointed to `crates/fegen-rust`; no residual destination paths under `tests/rust_cst_fegen`.
Evidence:
- §2 (design.md:74-75) and §2.2 Location bullet (design.md:106-117): "move `tests/rust_cst_fegen/` → `crates/fegen-rust/`" stated as decided, with rationale (Rust peer of `fltk/fegen/fltk_cst.py`). No "OQ-2 / recommended default" hedge.
- §2.5 build targets (design.md:269-270): `build-fegen-rust-cst`/`build-fegen-rust-parser` repointed `tests/rust_cst_fegen` → `crates/fegen-rust`. Verified these targets exist at Makefile:198-199 and 217-219 as cited.
- §2.5 gencode repoint (design.md:242-243): `RS_OUT=tests/rust_cst_fegen/src/cst.rs` → `crates/fegen-rust/src/cst.rs`. Verified the source line exists in the live `gencode` recipe (Makefile, fegen `cst.rs` step).
- §2.5 make-check lanes (design.md:273-276): every cited line verified present and currently naming `tests/rust_cst_fegen` — cargo-clippy (Makefile:129), cargo-test-no-python (Makefile:139), cargo-clippy-no-python (Makefile:147), check-no-pyo3 (Makefile:166-168), cargo-deny (Makefile:177). All five are enumerated for repointing; §3 (design.md:351-353) reiterates the full set. No lane omitted.
- §2.6 Bazel (design.md:301): `crates/fegen-rust` is a standalone maturin workspace, not a root Bazel target — consistent with the live fixture being a separate workspace.
- Grep confirms no residual `tests/rust_cst_fegen` *destination* path; remaining mentions are historical source references ("move from", before/after framing) — exactly as the disposition claims.
Assessment: decision applied; all enumerated downstream consequences (layout, Makefile build + gencode + make-check lanes, Bazel, cargo-deny) verified against the live files at the cited lines. Accept.

### user-decision-3 — OQ-3 (Option A: emit `.pyi` to `fltk/_stubs/fegen_rust_cst/cst.pyi` + pyright edit) — Fixed
User decision: "Option A — keep codegenning the CST `.pyi`, route output to `fltk/_stubs/fegen_rust_cst/cst.pyi`, add matching `stubPath`/`extraPaths` to `[tool.pyright]`."
Disposition claim: hedge removed; concrete emit target + required pyproject.toml edit stated as decided in §2.2/§2.5/§3/§4/§5.
Evidence:
- §2.2 `.pyi` bullet (design.md:126-138): emit target `fltk/_stubs/fegen_rust_cst/cst.pyi`, with the "matching `stubPath`/`extraPaths` entry added to `[tool.pyright]`," and "that `pyproject.toml` edit is part of this design's acceptance." No "(OQ-3, option a)" / "decides between (a) and (b)" hedge.
- Factual basis verified: pyproject.toml:50,52 are exactly `include = ["fltk", "*.py"]` and `stubPath = ""` as the design cites. The design's reasoning — a stub under `crates/fegen-rust/` is outside the `fltk` search tree and never resolved — is correct against the live config.
- §2.5 gencode flag (design.md:244-247): concrete `--pyi-output fltk/_stubs/fegen_rust_cst/cst.pyi` on the surviving fegen-CST gen step. Verified the live `gencode` recipe currently emits `--pyi-output fltk/_native/fegen_cst.pyi` (Makefile fegen step) with the `--protocol-module` flag — design repoints exactly this.
- §3 edge case (design.md:341-350) and §4 drift gate (design.md:390) cite the concrete path, not "(OQ-3)."
- §5 entry (design.md:409-414): Option A recorded; pyproject.toml edit named as acceptance.
- "Keep codegenning" preserved: design retains the `--pyi-output` emit (not dropped), matching the user's "keep codegenning the CST `.pyi`." Stub package location `fltk/_stubs/` is new (verified absent today); design correctly treats its creation as part of the work.
Assessment: decision applied exactly, including the user's explicit `[tool.pyright]` edit and the "keep codegenning" qualifier; supporting pyright-config facts verified true. Accept.

## Approved

3 user decisions: 3 Fixed verified (no-rename, crates/ promotion, Option A stub routing). All hedges removed; all enumerated downstream consequences (crates/ layout, Makefile build/gencode/make-check lanes, Bazel notes, cargo-deny, pyright stub path) verified consistent against the live source files at the cited lines.

---

## Verdict: APPROVED

All three user decisions are correctly and consistently reflected in design.md with no residual open-question framing and no contradictory references. Downstream consequences were spot-checked against pyproject.toml and Makefile at the cited lines and match.
