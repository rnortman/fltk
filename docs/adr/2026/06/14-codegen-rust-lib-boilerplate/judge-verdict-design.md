# Judge verdict — design review

Phase: design. Doc: `docs/designs/codegen-rust-lib-boilerplate/design.md`. Round 1.
Notes: 1 reviewer file (design-design-reviewer); 6 findings, all dispositioned Fixed.

(Design phase — no Added TODOs walk.)

## Other findings walk

### design-1 — Fixed
Claim: design asserted generated `lib.rs` must be "clean after `make fix`" and that `make check` gates its formatting; false for a `.rs` file — `make fix` is ruff-only and no rustfmt/`cargo fmt` step exists. Consequence: implementer chases unverifiable rustfmt-cleanliness, writes a formatting-cleanliness test with no backing gate; the real gate is compilation.
Severity: should-fix (spec correctness — would misdirect implementer toward an unverifiable acceptance target).
Source check: `make fix` = `ruff check --fix` + `ruff format` (Makefile:85-87), Python-only. `check-common` step list (Makefile:39-51) carries no rustfmt gate. Repo grep `rustfmt|cargo fmt|fmt --check` over Makefile + `.github` returns nothing. Confirmed.
Fix verification: §2.2 (lines 144-150) now states `.rs` output is **not** normalized by `make fix` (which runs only ruff), that no rustfmt step exists, and the "done" gate is **compilation** (cargo check/clippy for fixtures; maturin `build-native` for `src/lib.rs`). §2.7 (lines 305-312) reframes to "same drift posture as the other generated `.rs` files" / "gates that it *compiles*." No "clean after make fix" language survives.
Assessment: fix addresses the consequence at the named sections; corrected gate is the one the source supports. Accept.

### design-2 — Fixed
Claim: design framed drift detection as part of the verification gate, but `make check`/`check-common` never invokes `gencode` or a diff; the `git diff --stat` drift check is a manual developer step only. Consequence: false belief that `make check` enforces no-drift; the §2.7 "gated by make check like the other generated files" framing overstates the guarantee.
Severity: should-fix (overstated guarantee in acceptance language).
Source check: `check-common` step list (Makefile:39-51) contains no `gencode`/`git diff`. Makefile:233-234 is a comment describing the manual cheat-detection step. Confirmed.
Fix verification: §2.7 (lines 308-312) now states "`check-common` (Makefile:39-51) never invokes `gencode`. Drift ... is caught only by the manual `make gencode` + `git diff --stat` workflow ... exactly how `cst_generated.rs` / `cst_fegen.rs` are handled today." §4 fltk bullet (lines 408-412) matches: "Drift detection is **not** part of `make check`." Overstated framing removed.
Assessment: reworded exactly as the finding's consequence demanded; matches source. Accept.

### design-3 — Fixed
Claim: design left wiring the in-tree smoke target optional, so the new no-`lib_rs` Bazel codepath (most mechanically novel) ships with zero automated coverage inside fltk, despite the requirement listing it as an fltk-side acceptance criterion. Consequence: macro regression caught only by clockwork's out-of-repo build later.
Severity: should-fix (missing in-repo coverage of an acceptance-criterion codepath).
Source check: sole `fltk_pyo3_cdylib` consumer is clockwork (out of repo); BUILD.bazel:117-122 carries `TODO(fltk-pyo3-cdylib-smoke)`. Confirmed in dispositions; consistent with prior exploration.
Fix verification: §2.5 step 4 (lines 259-263) now headed "**Smoke coverage (in scope):**" — wire the TODO to a no-`lib_rs` `fltk_pyo3_cdylib` driven by `bootstrap_rust_srcs`. §4 Bazel bullet (lines 420-427) headed "**In scope (not optional):**" with the acceptance-criterion justification.
Assessment: promoted from optional to in-scope at both the design and test-plan sections; addresses the coverage gap. Accept.

### design-4 — Fixed
Claim: `generate_rust_parser` always emits both `cst.rs` and `parser.rs`, and the assembly genrule requires both present; a `--no-parser`/`cst_only` macro attribute would control only lib.rs shape, leaving an unreconciled coupling (orphan `parser.rs`, mandatory presence check still runs). Consequence: a CST-only Bazel path that is half-wired and possibly broken, with no in-scope consumer.
Severity: should-fix (speculative scope introducing an unreconciled coupling).
Source check: rust.bzl:39-40 declares both outputs unconditionally; rust.bzl:231-232 asserts both present; no `cst_only` switch on `generate_rust_parser`. Confirmed directly.
Fix verification: §2.5 (lines 265-276) now carries an explicit "**CST-only is not wired into Bazel.**" paragraph citing rust.bzl:39-40 and :231-232, drops the macro attribute, and retains `--no-parser` as a CLI flag only (§2.3). §2.1 `cst-only-mode` (lines 67-71) tightened to CLI/generator-only, pointing at §2.5.
Assessment: the unreconciled coupling is removed by dropping the attribute and confining CST-only to the CLI; matches source. Accept.

### design-5 — Fixed
Claim: relocating the `TODO(native-submodule-error-context)` inline comment without adding the `TODO.md` entry still violates CLAUDE.md's two-part TODO convention. Consequence: post-implementation the repo retains a `TODO(slug)` with no `TODO.md` anchor — the exact non-conformance the convention forbids.
Severity: should-fix (would perpetuate a convention-violating orphan the design explicitly touches).
Source check: fltk `TODO.md` grep — only `fltk-pyo3-cdylib-smoke` present (TODO.md:13); no `native-submodule-error-context` entry in either repo. Confirmed.
Fix verification: §3 (lines 359-371) and §4 TODO-handling (lines 429-438) now require, on relocation, adding the matching `native-submodule-error-context` entry to fltk `TODO.md` (alongside moving the comment to `crates/fltk-cst-core/src/py_module.rs:87`), **or** adjudicating the TODO for removal per the check-todos rubric. "Merely moving the comment" is explicitly called insufficient.
Assessment: the design now satisfies (or explicitly defers via adjudication) the two-part convention; addresses the orphan. Accept.

### design-6 (minor) — Fixed
Claim: "the assembly genrule consumes the generated lib.rs exactly as a consumer-authored one today" understates the wiring change; `lib_rs` is currently mandatory and `gen-rust-lib` (no grammar) needs a Bazel action distinct from the grammar-driven `generate_rust_parser`. Consequence: underspecified Bazel mechanism the implementer would invent from scratch.
Severity: nit/should-fix (low risk of being built wrong; underspecification only).
Source check: rust.bzl:123-131 — `lib_rs` mandatory (no default), fed as genrule `srcs` + `$(location {lib_rs})` (rust.bzl:222,227). §2.3 states `gen-rust-lib` takes no grammar, so `generate_rust_parser` (grammar-driven) cannot host it. Confirmed.
Fix verification: §2.5 (lines 241-258) now spells out the concrete mechanism: change `lib_rs` to default `None` (step 1); when `None`, instantiate a genrule `name + "_gen_lib"` running `$(location //:genparser) gen-rust-lib $@ --module-name <name>` with `//:genparser` in `tools` (step 2); the assembly genrule then consumes that label, explicitly noted as the one wiring change (step 3); and a note that `generate_rust_parser` cannot host it because `gen-rust-lib` takes no grammar.
Assessment: concrete mechanism now named exactly as the suggested fix; removes implementer guesswork. Accept.

## Disputed items

None.

## Approved

6 findings: 6 Fixed verified (all addressed at the cited sections, all consequences source-confirmed). No bogus-reviewer findings — each finding stated a real consequence backed by source.

---

## Verdict: APPROVED

All six findings were accurate (consequences source-confirmed against Makefile, rust.bzl, TODO.md) and all six Fixed dispositions land at the cited sections and address the stated consequence. No disposition wrong; nothing disputed.
