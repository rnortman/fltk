# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/06/14-rust-native-lib-shape/design.md`. Round 1.
Notes: 1 reviewer file (design-reviewer); 6 findings, all dispositioned Fixed.

## Other findings walk

### design-1 — Fixed
Claim: design names `tests/test_gsm2lib_rs.py`, a path that does not exist; the real file is `fltk/fegen/test_gsm2lib_rs.py`, which imports `native_spec` at line 7 and holds the `test_native_spec_*` block. Consequence: implementer searches a nonexistent path, misses the line-7 import update, leaves a whole-file pytest collection error.
Source check: `find` returns only `./fltk/fegen/test_gsm2lib_rs.py`. Line 7 is `from fltk.fegen.gsm2lib_rs import LibSpec, RustLibGenerator, Submodule, native_spec`. Eleven `test_native_spec_*` functions span 133-244. Reviewer's facts confirmed.
Design now: §2.4 (212-222) reads `fltk/fegen/test_gsm2lib_rs.py`, parenthetically warns "(not `tests/test_gsm2lib_rs.py`)", states deleting `native_spec()` is a hard dependency for the line-7 import (quoting it verbatim), and describes the block as "~129-246". §4 (380-381) says "drops the `test_native_spec_*` cases (and the `native_spec` name from its line-7 import)".
Assessment: fix addresses the consequence at the named locations. "~129-246" overshoots the verified 133-244 harmlessly. Accept.

### design-2 — Fixed
Claim: §2.3 offered two registration options yielding different import paths, then committed to `from poc_cst import Identifier` without resolving which option produces it; the idiomatic `register_submodule(m, "cst", …)` wiring (used by every fixture) yields `from poc_cst.cst import`. Consequence: implementer picks idiomatic wiring, mandated test import fails, or a non-standard second wiring convention is introduced.
Source check: `tests/rust_cst_fegen/src/lib.rs:21` and `tests/rust_cst_fixture/src/lib.rs:22` both use `register_submodule(m, "cst", cst::register_classes)` → `.cst` submodule. Confirmed.
Design now: §2.3 (155-165) commits to `register_submodule(m, "cst", cst::register_classes)`, explicitly states "We deliberately do **not** register the classes at top level," yielding `from poc_cst.cst import Identifier, Items`. §4 (378) and §3 (333) agree; top-level alternative struck.
Assessment: inconsistency resolved toward the idiomatic wiring source confirms; §2.3/§3/§4 now agree. Accept.

### design-3 — Fixed
Claim: §2.1 framed the `__init__.pyi:9-14` poc_cst comment deletion as cosmetic, when post-refactor its content (poc classes live at `fltk._native.poc_cst`) becomes false. Consequence (low): implementer leaves an actively-misleading stub comment.
Design now: §2.1 (89-94) states the block is "**deleted because it becomes factually false**, not as cosmetic header trimming" and "Leaving the comment would actively mislead."
Assessment: reframed exactly as requested. Accept.

### design-4 — Fixed
Claim: §2.5 said new `tests/rust_poc_cst` entries go to "deny lanes" generically, but cargo-deny checks four manifests by explicit path; a new standalone workspace needs an explicit fifth line. Consequence: omit it and the new crate silently escapes the supply-chain gate.
Source check: cargo-deny target has exactly four explicit `--manifest-path` lines (root, rust_cst_fegen, rust_cst_fixture, rust_parser_fixture); comment confirms separate workspaces checked explicitly. Confirmed.
Design now: §2.5 (276-281) requires "an explicit **fifth** line `cargo deny --manifest-path tests/rust_poc_cst/Cargo.toml check --config deny.toml` … alongside the existing four" with the standalone-workspace rationale.
Assessment: explicit fifth line added with correct manifest list and rationale matching source. Accept.

### design-5 — Fixed
Claim: prior "drop the `cp`" recommendation would replace the spike↔PoC byte-identity guarantee with a drift-gate across two independent `gen-rust-cst` invocations — relocating, not eliminating, the duplication fragility the refactor criticizes. Consequence: drift possible whenever flags differ; robustness regression for the one grammar needing both python-on and python-off copies.
Source check: spike is python-off (`crate-type=["rlib"]`, no `#[pymodule]`); PoC fixture is python-on; both compile the same generated CST; the `cp` is the zero-cost identity guarantee. Reasoning sound.
Design now: §2.3 (175-179) and §2.5 (249-262) **keep** the `cp` (fixture canonical, spike copies), explicitly acknowledging "this is the one grammar where the 'exactly one generated CST per grammar' goal cannot be fully reached." §3 (353-359) makes `git diff` a backstop, not primary guarantee.
Assessment: prior recommendation reversed to preserve byte-identity; design states the limitation honestly rather than overclaiming. Accept.

### design-6 — Fixed
Claim: §2.2 asserted pyright resolves the relocated stub at `crates/fegen-rust/fegen_rust_cst/cst.pyi`, outside the importable `fltk` tree, without verifying pyright config. Consequence: stub goes dead, `fltk.fegen.fltk_cst_protocol` conformance check silently stops running.
Source check: `[tool.pyright]` is `include = ["fltk", "*.py"]`, `stubPath = ""` — exactly as the design now cites. A `crates/`-rooted stub is outside that tree. Confirmed.
Design now: §2.2 (122-136) cites the real config verbatim, distinguishes `--pyi-output` write-path from pyright resolution, requires the stub inside the `fltk` tree (recommended `fltk/_stubs/fegen_rust_cst/cst.pyi`) with a matching `[tool.pyright]` edit "declared part of this design's acceptance," and surfaces the (a)/(b) choice as OQ-3. §2.5/§3/§4 route to the resolved location.
Assessment: resolvability is now a first-class acceptance concern with the actual config cited; the open sub-choice deferred to OQ-3 rather than guessed. Accept.

## Approved

6 findings: 6 Fixed verified. All six were genuine gaps/inconsistencies with stated consequences (no bogus-reviewer findings); each disposition's design edit was checked against both the design text and the cited source (test-file path, fixture wiring idiom, cargo-deny manifest set, pyright config). All sound.

Note: the three open questions (OQ-1 name, OQ-2 crate location, OQ-3 stub-config approach) are deliberately-deferred owner choices surfaced in the design, not unresolved findings — appropriate for a design doc, not grounds for rework.

---

## Verdict: APPROVED

All six dispositions acceptable; each Fixed claim verified against design text and source.
