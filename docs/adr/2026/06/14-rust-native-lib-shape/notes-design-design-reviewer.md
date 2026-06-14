# Design review notes — design-reviewer

Design: `docs/adr/2026/06/14-rust-native-lib-shape/design.md`
Spec: `request.md` (verbatim). Backward-compat / API-stability waived per task note;
no findings premised on those. Reviewed for: runtime-vs-codegen separation, mirroring
the Python backend, internal coherence, completeness, groundedness.

Verification baseline: every load-bearing code citation in the design was checked
against source at base commit. The structural claims are overwhelmingly accurate
(verified: `src/lib.rs`, `Cargo.toml`, `src/span.rs`, `gsm2lib_rs.py` LibSpec/native_spec/
generate, `genparser.py` gen-rust-cst/gen-rust-lib/gen-rust-native-lib, Makefile gencode
+ check lanes, `tests/rust_cst_fegen/`, `crates/fltk-cst-spike/`, BUILD.bazel, clockwork
roundtrip test). The core thesis — `_native` carries two CST submodules via `native_spec()`,
the fegen CST is byte-duplicated in `tests/rust_cst_fegen/src/cst.rs`, span surface is
correctly placed, no parser is linked — is all confirmed. Findings below are gaps and
inconsistencies, not refutations of the thesis.

---

## design-1 — Wrong path for the gsm2lib_rs test file (file does not exist at cited location)

Section: §2.4 and §4 ("`tests/test_gsm2lib_rs.py` (the `test_native_spec_*` cases …)";
"`tests/test_gsm2lib_rs.py` drops the `test_native_spec_*` cases").

What's wrong: The design repeatedly names `tests/test_gsm2lib_rs.py`. That file does not
exist. The actual file is `fltk/fegen/test_gsm2lib_rs.py` (verified: `find` returns only
`./fltk/fegen/test_gsm2lib_rs.py`; `tests/test_gsm2lib_rs.py` is absent). The design also
cites `exploration.md:44` as the source for "`test_native_spec_*` cases", but
`exploration.md:44` is about `test_gsm2lib_rs.py:177-181` without a directory — the design
invented the `tests/` prefix.

Why: Source-checked. The `test_native_spec_*` functions the design wants to delete really
do live in `fltk/fegen/test_gsm2lib_rs.py` (lines 133-246: `test_native_spec_contains_span_module`,
`…_poc_cst_registration`, `…_fegen_cst_registration`, `…_fn_name`,
`…_declaration_and_registration_order`, `…_output_ends_with_newline`, etc.). It also imports
`native_spec` directly (`test_gsm2lib_rs.py:7`), so deleting `native_spec()` breaks the import
for the whole module, not just the `test_native_spec_*` cases.

Consequence: An implementer following the design will look for `tests/test_gsm2lib_rs.py`,
not find it, and may either miss the test updates entirely (leaving a module that fails to
import `native_spec` → whole-file collection error under pytest) or waste time. The design's
test-update plan is under-specified on the actual file. Deleting `native_spec()` is a
hard dependency for `test_gsm2lib_rs.py:7`'s top-level import — that import line must be
updated too, which the design does not call out.

Suggested fix: Correct every reference to `fltk/fegen/test_gsm2lib_rs.py`; note that the
`from fltk.fegen.gsm2lib_rs import … native_spec` import (line 7) must drop `native_spec`,
and that the `test_native_spec_*` block is lines ~129-246, not just "a few cases".

---

## design-2 — PoC fixture import path is internally inconsistent (`from poc_cst import` vs a `cst` submodule)

Section: §2.3 ("registers a single `cst` worth of classes, or registers the toy classes
at top level. The Python imports become `from poc_cst import Identifier, Items`") and §4
("`tests/test_rust_cst_poc.py` retargets to `from poc_cst import Identifier, Items`").

What's wrong: The two registration options in §2.3 produce *different* import paths, and the
design then commits to one import path (`from poc_cst import Identifier`) without resolving
which registration option yields it. The generated `register_classes(module)` registers
classes *into the module it is handed* (verified: `src/cst_generated.rs:3177`
`pub fn register_classes(module: &Bound<PyModule>)`; gsm2tree_rs.py:2337). Every existing
fixture wires this as `register_submodule(m, "cst", cst::register_classes)` — producing a
`.cst` submodule (verified: `tests/rust_cst_fixture/src/lib.rs:22`,
`tests/rust_cst_fegen/src/lib.rs:21-22`). With that idiomatic wiring the import is
`from poc_cst.cst import Identifier`, NOT `from poc_cst import Identifier`. To get
`from poc_cst import Identifier` the `#[pymodule] fn poc_cst` body must call
`register_classes(m)` directly on the top-level module — a wiring no existing crate uses
and which the design never spells out.

Why: Source-checked against the register_classes signature and all three existing fixture
lib.rs files.

Consequence: An implementer picks the idiomatic `register_submodule(m, "cst", …)` wiring
(matching every other fixture and the design's own §2.2 "Shape: unchanged … `cst` submodule"
language for the fegen crate), then writes the lib.rs, then the design-mandated test
`from poc_cst import Identifier` fails at import. Or they hand-write a non-standard top-level
registration just for the PoC, creating a second, inconsistent wiring convention — the
opposite of the "one grammar per extension, uniform shape" invariant the refactor claims to
establish. Either way the §4 test text and the §2.3 lib.rs shape disagree.

Suggested fix: Pick one. Recommended: mirror the fegen crate exactly —
`register_submodule(m, "cst", cst::register_classes)` and `from poc_cst.cst import Identifier`
in the tests. Then §2.3's "or registers at top level" alternative should be struck so the
two halves of the design agree.

---

## design-3 — `__init__.pyi` poc_cst comment lives in the body, not the header lines the design cites; deletion scope understated

Section: §2.1 ("Its header comment about `poc_cst` (__init__.pyi:9-14) is removed").

What's wrong: The design says the poc_cst comment is at `__init__.pyi:9-14`. Verified: the
poc_cst comment block is actually lines 9-14 *describing it as the* `fltk._native.poc_cst`
*submodule* and pointing at `src/lib.rs; cst_generated::register_classes`. After the refactor
poc_cst is no longer a submodule of `_native` at all (it moves to a standalone `poc_cst`
extension per §2.3), so this comment is not merely "removed as a header note" — its factual
content (poc classes are in `fltk._native.poc_cst`) becomes *false*, which is the real reason
to delete it. Minor, but the design frames it as cosmetic header cleanup when it is a
correctness fix to a now-wrong statement.

Why: Source-checked (`fltk/_native/__init__.pyi:9-14`).

Consequence: Low. If an implementer treats it as optional header trimming they might leave a
stub comment asserting `fltk._native.poc_cst` exists — actively misleading after the move.
Worth stating that the comment is being deleted because it is wrong post-refactor, not for
tidiness.

---

## design-4 — `cargo-deny` lane for the fegen crate is enumerated for repointing but the design's §2.5 list omits it from one place / double-check the fixture deny set

Section: §2.5 ("`make check` sub-targets that reference `tests/rust_cst_fegen` by path —
`cargo-clippy` (Makefile:129), `cargo-test-no-python` (Makefile:139),
`cargo-clippy-no-python` (Makefile:147), `check-no-pyo3` (Makefile:166-168),
`cargo-deny` (Makefile:177) — are repointed to `crates/fegen-rust`") and §3 ("cargo-deny /
clippy path drift").

What's wrong: The enumeration is essentially correct and the line numbers verify
(`Makefile:129,139,147,166-168,177` all name `tests/rust_cst_fegen/Cargo.toml`). One gap:
the design says new `tests/rust_poc_cst` entries are "added to the python-off clippy/test/deny
lanes to keep coverage parity with the spike," but the existing `cargo-deny` target
(Makefile:174-177) checks four fixture manifests by explicit path (rust_cst_fegen,
rust_cst_fixture, rust_parser_fixture, and root) — adding a new standalone `tests/rust_poc_cst`
crate means a *fifth* `cargo deny --manifest-path tests/rust_poc_cst/Cargo.toml` line is
required, which the design does not explicitly call out (it only says "deny lanes" generically).
The spike (`fltk-cst-spike`) is in the root workspace so it is covered by the root deny check;
a new standalone `tests/rust_poc_cst` workspace is NOT, mirroring the per-fixture explicit
deny lines.

Why: Source-checked (`Makefile:174-177` cargo-deny target; `tests/rust_cst_fegen/Cargo.toml:1-3`
confirms standalone workspace, hence the explicit per-manifest deny).

Consequence: If the implementer adds `tests/rust_poc_cst` as a standalone workspace (consistent
with §2.3 "standalone maturin extension") but does not add an explicit `cargo-deny --manifest-path
tests/rust_poc_cst/Cargo.toml` line, the new crate silently escapes the supply-chain gate —
exactly the "silently drops a coverage lane" risk §3 warns about, but for deny specifically,
which the design's mitigation ("§2.5 enumerates every such line") does not actually enumerate.

Suggested fix: Add an explicit "new `cargo deny --manifest-path tests/rust_poc_cst/Cargo.toml`
line" to the §2.5 cargo-deny bullet, alongside the clippy/test additions.

---

## design-5 — Spike crate is python-OFF (rlib, no pymodule); the design's "regenerate spike directly from poc_grammar" is sound, but the PoC fixture and spike now diverge in build mode — drift gate must compare generated source, and the design's drift mitigation is correct only if both stay file-identical

Section: §2.3 / §2.5 ("the fixture and the spike both regenerate from `poc_grammar.fltkg`
directly … Default: regenerate directly; drop the `cp`") and §3 ("PoC fixture python-off
coverage … both must stay generated from the same `poc_grammar.fltkg`").

What's wrong: This is mostly fine and well-reasoned, but one subtlety the design glosses:
today `crates/fltk-cst-spike/src/cst.rs` is *guaranteed byte-identical* to the PoC because it
is a literal `cp src/cst_generated.rs` (Makefile:280, verified — both files are 3188 lines,
identical NodeKind IDENTIFIER/ITEMS/TRIVIA). The spike compiles this file python-OFF
(`crate-type=["rlib"]`, `default=[]`, no pyo3 — verified `crates/fltk-cst-spike/Cargo.toml`,
`src/lib.rs` has no `#[pymodule]`), exercising the `#[cfg(feature="python")]`-gated code in
the OFF configuration. The new PoC fixture (§2.3) is python-ON (a maturin cdylib). If the
design drops the `cp` and has *two independent* `gen-rust-cst` invocations write the same
content to two files, they can only stay identical if the generator is deterministic AND both
invocations use identical flags. The fegen crate's analogous "must match" coupling
(Makefile:265-267) existed precisely because two copies are fragile; the design removes the
fegen duplication (good) but *introduces a new* two-copy situation (spike cst.rs + poc fixture
cst.rs) for the PoC grammar, justified only by "git diff after make gencode surfaces drift."
That is the same fragility, relocated — not eliminated.

Why: Source-checked (spike Cargo.toml/lib.rs python-off; Makefile:280 cp; identical line counts).

Consequence: The refactor's stated win is "exactly one generated CST per grammar, in one place."
For the fegen grammar that is achieved. For the PoC grammar it is NOT — there remain two
generated copies (spike rlib + poc cdylib fixture), reproducing the very duplication-with-drift-
gate pattern the design criticizes for fegen. If the implementer drops the `cp` without keeping
a hard identity link, drift between the two PoC copies is possible whenever generator flags
differ (e.g. one gets `--protocol-module`, the other not). Keeping the `cp` (spike copies from
the fixture) preserves byte-identity at zero cost and is strictly safer than two independent
regenerations; the design's "preferred: regenerate, drop the cp" recommendation trades
guaranteed identity for a diff-gate, which is a regression in robustness for the one grammar
where two copies must coexist.

Suggested fix: Keep the single-source-of-truth `cp` for the PoC (fixture is canonical; spike
`cp`s from it), OR explicitly note that both regenerations must share the exact same flags and
the drift gate is the only guarantee. Do not present "drop the cp" as strictly preferable —
it weakens the identity guarantee the spike relies on.

---

## design-6 — `__init__.pyi` is the surviving hand-maintained stub, but the design does not address that deleting `fegen_cst.pyi` leaves a `fltk/_native/` dir whose remaining contents must still typecheck; and the new `fegen_rust_cst/cst.pyi` stub-package location is unverified against pyright resolution

Section: §2.1 ("`fltk/_native/fegen_cst.pyi` is deleted") and §2.2 ("re-emitted as the new
crate's `cst.pyi` stub (`crates/fegen-rust/fegen_rust_cst/cst.pyi`)").

What's wrong: The design asserts pyright resolves the relocated stub at
`crates/fegen-rust/fegen_rust_cst/cst.pyi` and that this is "the canonical stub-package layout
the `gen-rust-cst --pyi-output` flag already supports (genparser.py:281-296)". The flag does
support an arbitrary `--pyi-output` path (verified, genparser.py:281-296 + write at
~`stub_path.write_text`). But whether pyright *resolves* `fegen_rust_cst.cst` to a stub at
`crates/fegen-rust/fegen_rust_cst/cst.pyi` depends on that directory being on pyright's
search path / configured as a stub package — which is a pyproject/pyright config concern the
design does not verify or address. Today the stub sits at `fltk/_native/fegen_cst.pyi`, inside
the importable `fltk` package tree. A path under `crates/fegen-rust/` is outside the Python
package tree entirely; nothing in the design confirms pyright is configured to look there.
The design's §3 edge-case ("`.pyi` resolution by import name") restates the requirement but
does not verify the config satisfies it for the new location.

Why: Source-checked the flag plumbing (genparser.py gen-rust-cst --pyi-output); the pyright
search-path config for a `crates/`-rooted stub is not shown in the design and was not asserted
against any verified pyproject/pyrightconfig entry.

Consequence: If the implementer relocates the stub under `crates/fegen-rust/` and pyright is
not configured to resolve stubs from there, the fegen CST PyO3 surface silently loses its
type-checking against `fltk.fegen.fltk_cst_protocol` — the stub becomes dead, and the protocol
conformance the design says "keeps validating" (§2.2) is no longer validated. This is the
infrastructure-before-features concern: the stub's value is the pyright check, and the design
moves it to a location whose resolvability it never confirms.

Suggested fix: Either keep the fegen stub somewhere pyright already resolves (an importable
`fegen_rust_cst/` stub package on the path), or have the design explicitly add the pyright
search-path / stub-package config entry for the new `crates/fegen-rust/` location and cite the
config file it edits.

---

## Coverage / consistency notes (not blocking)

- Requirement mapping: the spec's two hard demands — (a) `_native` contains nothing
  grammar-specific (no CST, no parsers), (b) fegen parser+CST live in their own module
  mirroring the Python `fltk/fegen/fltk_*` split — are both covered (§2.1 removes both CST
  submodules; §2.2 relocates fegen CST+parser to a committed standalone crate). The spec's
  "refactor as heavily as needed" is honored (deleting `native_spec()` + `gen-rust-native-lib`,
  §2.4). No scope-creep features detected; OQ-1/OQ-2 correctly defer cosmetic choices.
- Verified accurate and not flagged: `_native` carries `poc_cst`+`fegen_cst` via native_spec()
  (src/lib.rs:25-26, gsm2lib_rs.py:174-182); `LibSpec.validate()` already permits zero
  submodules when span/unknown_span set (gsm2lib_rs.py:81-83 — confirmed); fegen byte-dup
  (cst_fegen.rs == tests/rust_cst_fegen/src/cst.rs, both 15515 lines); clockwork only uses
  `fltk._native.Span` (confirmed, no fegen_cst/poc_cst refs); BUILD.bazel globs src/**/*.rs so
  source-set needs no rule change (BUILD.bazel:35), only the crate_features comment
  (BUILD.bazel:39-42) — all correct.
- §2.4 proposes new `gen-rust-lib` flags `--register-span-types --unknown-span-static --no-cst`.
  These do not exist today (verified: gen-rust-lib only has `--module-name`/`--no-parser`,
  genparser.py:400-443; LibSpec.standard always emits a `cst` submodule). The design correctly
  frames these as additions, and LibSpec already has the underlying boolean fields
  (`register_span_types`, `unknown_span_static`, gsm2lib_rs.py:56-60) — so the CLI work is
  surfacing existing knobs plus a `--no-cst`/submodule-selection. Grounded and feasible.
