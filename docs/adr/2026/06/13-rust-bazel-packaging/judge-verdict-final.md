# Judge verdict — final review round

Phase: final (build-fix addendum). Round 1.
Repos:
- fltk: base `fafa6d7` .. HEAD `332742a`
- Clockwork: base `ece332a` .. HEAD `ed3d9f0`
Notes: 7 reviewer files. Findings: correctness-1; errhandling-1..4; test-1..3;
reuse-1..2; quality-1..3; security-1; efficiency (none).
Ground truth: code (both repos) + `design.md` + `design-buildfix.md` (which mandates
the pyo3-collision robustness generalization in §2.4/§2.5/§9).

## Added TODOs walk

### errhandling-4 — TODO(native-submodule-error-context) at clockwork/dsl/clockwork_native_lib.rs:18
Rubric Q1 (worth doing): yes, eventually — annotating the propagated error with the
submodule name ("cst"/"parser") turns a bare pyo3 `ImportError` at
`import clockwork_native` into a diagnostic that names the culprit. Low value (the
reviewer itself graded it low/QoL), but a real, concrete improvement.
Rubric Q2 (design/owner input required): yes — the clean fix is upstream in
`fltk-cst-core::register_submodule` (cross-repo FLTK-core API change affecting every
consumer), versus a per-call `.map_err` in each consumer lib.rs. Where the
responsibility lives (shared helper vs. per-call) is a small but genuine design call
spanning two repos; not a mechanical edit a POC just does in place. The reviewer's own
"What must change" frames it as a choice between two approaches, confirming the design
content.
Iteration-created check: NO. The missing error context is a property of the
pre-existing `register_submodule` helper's signature (`fn(_, _, _) -> PyResult<_>`);
this iteration merely *used* that helper. The consumer lib.rs is new POC scaffolding,
but the diagnostic gap it exposes was not created or worsened here. The "cannot
silently defer" clause does not bind.
TODO-convention check: FLTK's CLAUDE.md requires `TODO.md` entry + `TODO(slug)` comment
joined by slug. This TODO comment lives in the **Clockwork** repo, which uses
ticket-ID-style TODOs (`TODO(DX-1394)`, `TODO(OI-3052)`), has **no** `TODO.md`, and has
no TODO-system section in its CLAUDE.md. The FLTK TODO.md requirement therefore does not
apply to a comment in Clockwork. Minor stylistic note: the descriptive slug differs from
Clockwork's ticket-ID style, but the pre-existing intentional `TODO(fltk-pin-finalize)`
in this same work uses a descriptive slug too — precedent exists; not a defect.
Assessment: Q1 yes + Q2 yes + not iteration-created → TODO acceptable.

## Other findings walk

### correctness-1 — Fixed
Claim: the de-glob robustness upgrade (design-buildfix §2.4) misses one unqualified
Py-prefixed type-namespace import — the trait `pyo3::PyTypeInfo` (imported unqualified in
the cst.rs preamble, used at `{Label}::type_object`). A rule `type_info` → CN `TypeInfo`
→ handle `PyTypeInfo` collides (rustc E0255), silent miscompile in generated PUBLIC API.
Consequence: out-of-tree consumer with a `type_info` rule gets uncompilable cst.rs.
Verification (task-flagged: confirm the fix is the generalized model, not a one-off):
- `gsm2tree_rs.py:_preamble` (lines 503–515) emits an explicit
  `use pyo3::prelude::{Python, Py, Bound, IntoPyObject, ...method traits, pyclass,
  pymethods};` list — the glob is gone — and `use pyo3::PyTypeInfo;` is **absent**. The
  fix follows the same systematic qualify-at-emission rule already applied to
  PyAny/PyResult/PyRef, with an explanatory comment block (506–510).
- Single call site `_label_classattr` (gsm2tree_rs.py:1299) now emits UFCS
  `<{enum_name} as pyo3::PyTypeInfo>::type_object(py)...` — no unqualified `PyTypeInfo`
  needed.
- All five generated/fixture cst.rs regenerated: grep confirms zero
  `use pyo3::PyTypeInfo;`, zero `use pyo3::prelude::*`, zero
  `use pyo3::types::{PyList...}` across `src/cst_generated.rs`, `src/cst_fegen.rs`,
  `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`,
  `tests/rust_parser_fixture/src/cst.rs`; the UFCS `as pyo3::PyTypeInfo>::type_object`
  appears in all five.
- `type_info` is now a recovered legal rule name, pinned by
  `test_type_info_rule_accepted` (test-file diff line 297).
Assessment: this is the generalized model — the reserved-or-qualified discipline over
the full enumerable import set — not a two-name patch. Fix addresses the consequence at
the named lines and the gap is closed structurally. Accept.

### errhandling-1 — Fixed
Claim: `_bad_reserved` module-load guard covers only `_RESERVED_CLASS_NAMES`, not
`_RESERVED_CLASS_NAMES_SEEDED`; a future `Child`/`Label`-suffixed seeded entry escapes
diagnosis. Consequence: silent mis-shaped seed blocks grammars with no clear error.
Code: `_bad_reserved_seeded` list comprehension (gsm2tree_rs.py:130) checks the seeded
dict for `endswith("Child")`/`endswith("Label")` and `raise RuntimeError` at 131–136
(explicit if/raise, survives `-O`). Addresses the consequence at the named location.
Accept.

### errhandling-2 — Fixed
Claim: unguarded copy loop in `_assemble_crate` genrule yields cryptic Bazel
"declared output not created" if cst.rs/parser.rs are missing. Consequence: significant
CI debug time, no diagnostic naming the missing file.
Code: rust.bzl:231–232 add `test -f $$OUTDIR/cst.rs || { echo "ERROR: cst.rs not
produced by rs_srcs ..."; exit 1; }` and the same for parser.rs. Converts the silent
failure into a named diagnostic. Accept.

### errhandling-3 — Fixed
Claim: `cmd = "cp $< $@"` assumes the `.so` is the first prerequisite; if rules_rust
emits extra files the wrong file is copied → silent build success, runtime ImportError.
Code: both rename genrules now use explicit `$(location ...)`: `rust.bzl:279`
(`cp $(location :{cdylib}) $@`) and `BUILD.bazel:64` (`cp $(location :native) $@`), with
comments explaining the positional-ambiguity avoidance. Accept.

### test-1 — Fixed
Claim: neither rejection path for `_RESERVED_CLASS_NAMES_SEEDED` (direct per-rule check;
cross-rule claims-seeding) is tested. Consequence: regression in either path silently
re-allows uncompilable grammars.
Code: `test_seeded_reserved_cn_rejected_directly` parametrized over the five seeded names
(direct path) and `test_seeded_reserved_handle_rejected_cross_rule` for rule
`any_methods` (cross-rule path) added to `TestReservedClassNameRejection` (test-file diff
275–296). Both paths now covered. Accept.

### test-2 — Fixed
Claim: parser.rs `register_classes` qualified-`pyo3::types::PyModule` change has no
direct generator test. Consequence: silent revert to bare `PyModule` would not be caught.
Code: production change verified present in `gsm2parser_rs.py:961` and fixtures
(`tests/rust_parser_fixture/src/parser.rs:1642`,
`tests/rust_cst_fegen/src/parser.rs:1649`).
`test_register_classes_signature_uses_qualified_pymodule` (test-file diff 363) instantiates
`RustParserGenerator` and asserts the qualified signature string. Accept.

### test-3 — Fixed
Claim: combined `#[cfg(all(feature="python", feature="test-introspection"))]` gate for
`pyfunction`/`wrap_pyfunction` is unasserted; collapse to the plain python gate would go
undetected (unused-import warnings in non-introspection builds).
Code: `test_required_use_declarations` now asserts the combined-gate import is present and
that `pyfunction`/`wrap_pyfunction` do NOT appear under the plain python gate (test-file
diff 35–42). Accept.

### reuse-2 — Fixed
Claim: two adjacent collision-check branches duplicate the identical `ValueError` f-string;
divergence risk if one is updated.
Code: merged to a single `collision_target = _RESERVED_CLASS_NAMES.get(class_name) or
_RESERVED_CLASS_NAMES_SEEDED.get(class_name)` with one raise (gsm2tree_rs.py:181–184).
Duplication eliminated. Accept.

### quality-1 — Fixed
Claim: `desc[:40]` truncation in the seeded-claims comprehension cuts off the reason a
name is reserved, forcing consumers to read generator source. Consequence: recurring
friction for every consumer who hits a seeded-trait collision.
Code: gsm2tree_rs.py:223 now emits `f"pyo3 method trait import: {desc}"` — full
description, no slice. Accept.

### quality-2 — Fixed
Claim: Bazel BUILD hardcodes `crate_features = ["python"]` while Cargo.toml documents
python as optional; silent trap for a future pure-Rust Bazel consumer.
Code: comment added at `crates/fltk-cst-core/BUILD.bazel:6–11` explaining the hardcode
(all current Bazel consumers are PyO3 cdylibs) and that a config_setting variant is needed
for a pure-Rust consumer. Documents the honest restriction. Accept.

### quality-3 — Fixed
Claim: the assembly loop copies every rs_srcs file by basename after writing lib.rs; a
label emitting `lib.rs` silently overwrites the assembled crate root (loses
recursion_limit). Consequence: cryptic E0275 / unexpected binary.
Code: WARNING note added to the `rs_srcs` arg docstring (rust.bzl ~182–189) describing the
overwrite hazard and instructing callers to pass a `generate_rust_parser` target. Accept.

### reuse-1 — Won't-Do
Claim: two `cp $(location ...) $@` abi3-rename genrules (`BUILD.bazel` native_so;
`rust.bzl` step 3) duplicate the recipe; suggests a `_abi3_rename` Starlark helper.
Consequence (reviewer): divergence *if* rename semantics ever change.
Rationale: different targets/BUILD contexts; a helper introduces `load` coupling to an
internal symbol; the duplicated unit is a single trivial `cp` line; rule-of-three —
revisit when a third site appears.
Assessment: nit severity. The consequence is conditional/speculative ("if semantics ever
change") over a one-line `cp`. Rule-of-three is a sound, established position; a
nit-grade reuse finding does not meet the bar to override it. Accept Won't-Do.

### security-1 — Won't-Do
Claim: `recursion_limit` is `.format()`-interpolated into a single-quoted shell `printf`;
a non-int value with `'`/`$()`/`;` could break out and run shell at build time.
Consequence (reviewer's own words): build-time exec **only** for someone who already
authors the BUILD file and controls the entire genrule/cmd surface — "No privilege
boundary is crossed; this is not an exploitable injection... No action required from a
security standpoint." Default `512` is an int literal and safe.
Rationale (responder): identical — producer is the BUILD author who already controls the
build action surface; no boundary crossed; int() coercion adds no security in this trust
domain.
Assessment: per severity calibration, a security finding is a blocker only on input
crossing a trust boundary; the reviewer itself states none is crossed and no action is
required. Won't-Do matches the reviewer's own analysis. Accept.

## Disputed items

None.

## Approved

13 findings (+ efficiency: no findings): 9 Fixed verified (correctness-1, errhandling-1/2/3,
test-1/2/3, reuse-2, quality-1/2/3), 2 Won't-Do sound (reuse-1, security-1), 1 TODO
acceptable (errhandling-4).

---

## Verdict: APPROVED

All dispositions acceptable. correctness-1's fix is the generalized de-glob model
(task-flagged): `PyTypeInfo` qualified via UFCS, glob removed, all five fixtures
regenerated, `type_info` recovered as a legal rule name with a pinning test — not a
one-off. The two KNOWN/INTENTIONAL items (local_path_override + TODO(fltk-pin-finalize);
hand-written crate-root lib.rs) were excluded from review per task framing and not
re-litigated. errhandling-4's TODO passes both rubric questions and was not
iteration-created. Both Won't-Dos align with the reviewers' own stated (low/no-action)
severity.

fltk HEAD: 332742a
Clockwork HEAD: ed3d9f0
