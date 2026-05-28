# Phase 4 Runtime Integration: Dispositions vs User Directive (re-design pass)

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Authoritative directive: `notes-design-user.md`. *FLTK generates parsers/CST that live
in a **user application**; users control module name, build process, everything. The
docs were narrowly focused on dogfooding FLTK's own grammar with Rust CST — that is just
one test case of the general capability.*

Each finding fact-checked against source (lib.rs, Cargo.toml, gsm2tree_rs.py, span.rs,
plumbing.py, fltk2gsm.py) before disposition. Findings are framed as the directive's
implications ("ud-N").

---

ud-1 (CORE DEFECT — user CST packaged under `fltk._native`):
- Disposition: Fixed
- Action: Replaced the prior `artifact-build-mechanism` decision (Option A/E — compile
  user CST into `fltk._native` as a submodule, hand-edit FLTK's `lib.rs`) with **Option B
  — a standalone, user-named, user-built extension** that depends on `fltk._native` only
  at runtime (for the `UnknownSpan` sentinel). See design "artifact-build-mechanism →
  Option B" and "Root Cause / Context". The runtime selector now references a
  **user-supplied dotted module name** (`rust_cst_module: str`), not a `fltk._native.*`
  submodule. Makefile targets are re-scoped as FLTK-internal test/dogfooding only; the
  user build is documented, not FLTK-encoded.
- Severity assessment: Critical — the prior design made every user's grammar CST live
  under FLTK's namespace, named by FLTK, requiring edits to FLTK's own `lib.rs` and a full
  `fltk._native` rebuild per grammar. That is the exact anti-pattern the directive names;
  it makes FLTK unusable as a framework whose output lives in user applications.

ud-2 (cross-extension `crate::UNKNOWN_SPAN` linkage — the deferred TODO, now forced):
- Disposition: Fixed (resolved, not deferred)
- Action: Resolved via the key source fact that the generated node stores `span:
  PyObject` and `children: Py<PyList>` (`gsm2tree_rs.py:194,196`) and performs all span
  ops through duck-typed Python dispatch (`gsm2tree_rs.py:426-432`). The **only**
  crate-internal dependency is the default sentinel `UNKNOWN_SPAN.get(py)`
  (`gsm2tree_rs.py:232-235`), and that sentinel is already exposed as a Python object
  `fltk._native.UnknownSpan` (`lib.rs:25`). Design specifies the `gsm2tree_rs.py` change:
  drop `use crate::UNKNOWN_SPAN;` (`:127`), emit a module-local `GILOnceCell` cache, and
  fetch `py.import("fltk._native")?.getattr("UnknownSpan")` lazily in `#[new]`. No
  Rust-level linkage to FLTK's crate is needed; a user extension is a plain independent
  `cdylib`. Concrete options + tradeoffs surfaced: Option B chosen; Option C (rlib/C-ABI)
  and Option D (shared `fltk-cst-common` rlib + workspace) documented with tradeoffs, D
  recorded as `TODO(rust-cst-shared-rlib)` for the future if Rust-level shared types are
  ever needed.
- Severity assessment: Critical — this is the single fact that previously "forced" the
  unacceptable submodule design. Verified: `Cargo.toml:8` is `cdylib`-only (no rlib);
  `lib.rs:10` `UNKNOWN_SPAN` is `pub(crate)`; `span.rs` `Span` ops are PyO3 methods callable
  duck-typed. The directive's demand is satisfiable with a small, localized generator
  change — not a build-system restructure.

ud-3 (generator was held out of Phase-4 scope; directive overrides):
- Disposition: Fixed (with USER flag)
- Action: Design now modifies `gsm2tree_rs.py` (two methods) and regenerates the committed
  `src/cst_fegen.rs` + `src/cst_generated.rs` under the new sentinel scheme. Flagged as
  **R-CONFLICT-1** (requirements-level) and in Open Question `requirements-realignment`:
  the prior requirements/design framing placed the generator out of Phase-4 scope, and
  req line 29 deferred `crate::UNKNOWN_SPAN` linkage as "not a requirement here." The
  directive makes a standalone artifact a requirement, so that Out-of-Scope clause must be
  narrowed. NOT silently rewritten — surfaced for USER decision.
- Severity assessment: Moderate — the scope boundary is real but is subordinate to the
  authoritative directive. Touching the generator is unavoidable to honor the directive;
  the change is small and preserves the Python-visible CST API.

ud-4 (AC5 / static-consumer dogfodding treated as THE binding goal):
- Disposition: Fixed (with USER flag)
- Action: Reframed the binding API-Contract verification to a **non-FLTK** generated Rust
  module (`test_rust_cst_contract_non_fltk` against the standalone `phase4_roundtrip_cst`
  fixture) as the PRIMARY case — the general capability — with the FLTK-CST contract pass
  (`test_rust_fegen_cst_contract`) kept as a SECONDARY dogfooding case. Retained the prior
  round's correct finding that the *real* `fltk2gsm.py` cannot run against Rust nodes
  (`fltk2gsm.py:4` static `from fltk.fegen import fltk_cst as cst`, no injection seam;
  re-export out of scope per req line 27, edit forbidden per req line 116) →
  hand-written contract tests, `TODO(rust-cst-fltk-reexport)`. Flagged as **R-CONFLICT-3**
  and in `requirements-realignment` for USER decision.
- Severity assessment: Moderate-High — AC5/AC7 are designated the binding contract
  verification (req lines 99, 131). Anchoring them on FLTK's own grammar makes the test
  suite prove dogfooding rather than the general capability the directive insists is the
  actual goal. Verified: PyO3 `fegen_cst.Item` and dataclass `fltk_cst.Item` are distinct
  type objects, so the static consumer cannot dispatch on Rust nodes without a seam.

ud-5 (Tier-2 artifact = FLTK's own `fegen_cst`, not a user extension):
- Disposition: Fixed
- Action: The PRIMARY Tier-2 artifact is now a **standalone user-extension fixture** —
  grammar `fltk/fegen/test_data/phase4_roundtrip.fltkg`, a separate `cdylib` crate under
  `tests/rust_cst_fixture/` with its own `Cargo.toml` and `#[pymodule]` init calling
  `register_classes`, importable under a user-style name (NOT `fltk._native.*`), built by
  `make build-test-user-ext`. `fltk._native.fegen_cst` is demoted to a SECONDARY dogfooding
  case. AC2/AC3/AC5/AC7 are exercised against the standalone extension. Flagged as
  **R-CONFLICT-4**.
- Severity assessment: Moderate — without a committed standalone-extension fixture, the
  test suite would only ever exercise the in-crate submodule path and never prove the
  user-facing capability the directive requires.

ud-6 (selector shape / module-name-stability tied to submodule reasoning):
- Disposition: Fixed (with USER flag)
- Action: Resolved `selector-shape` to a single `rust_cst_module: str | None = None`
  **user-controlled dotted module name** and `module-name-stability` to "user-named
  importable module." The requirements' coupling-note reasoning (path-based fails because
  the artifact is a `fltk._native.*` submodule) is now moot for the opposite reason: under
  a standalone user extension the artifact is a user-controlled importable name. Flagged
  as **R-CONFLICT-2**; `selector-surface-form` open question retained for the
  enum-vs-string surface choice.
- Severity assessment: Moderate — the user must be able to name and locate their own
  module; a `fltk._native.*`-shaped selector would re-impose FLTK's namespace on the user.

ud-7 (new runtime dependency + version-skew, introduced by Option B):
- Disposition: Fixed (consequence documented; pinning deferred with TODO)
- Action: Documented that a Rust-backed parser's process must have `fltk._native`
  importable (the user extension lazily imports it for `UnknownSpan`). Added Edge Cases
  for sentinel-import timing (surfaces at first node construction, loud), missing
  `fltk._native` at runtime, and `fltk._native`/user-extension version skew. No pinning in
  Phase 4; recorded `TODO(rust-cst-abi-pinning)` for a future ABI-version handshake.
- Severity assessment: Low-to-moderate — Option B trades the submodule coupling for a
  documented runtime import dependency. Benign in practice (any FLTK runtime has
  `fltk._native`), but must be stated so the user is not surprised, and skew is flagged.

ud-8 (carry-forward of prior valid review findings):
- Disposition: Fixed (preserved)
- Action: Retained the correct resolutions from the prior round that survive the
  re-design: `except ImportError` (not `except Exception`) in `_load_rust_cst_classes`;
  the `public` = class-names-only `parser_globals` contract note; the `*_Label`
  backend-parity note; the hard-error-before-`sys.modules`-set ordering for AC4; the
  no-double-trivia caveat in `gen-rust-cst`; and the dual-piece TODO obligation
  (`TODO(slug)` comment + `TODO.md` entry per CLAUDE.md). These were correct independent of
  the directive and remain.
- Severity assessment: Low — these are sound prior-round fixes; dropping them would
  regress already-resolved defects.

---

## Requirements-level flags (NOT silently rewritten — USER decision required)

These are recorded in the design under "Requirements-level conflicts" (R-CONFLICT-1..4)
and in the `requirements-realignment` open question. The design proceeds on the
directive-aligned reading; `requirements.md` is unmodified.

- **R-CONFLICT-1** — `artifact-build-mechanism` (req lines 156-161) + Out-of-Scope clause
  (req line 29): requirements frame submodule-of-`fltk._native` as the no-architectural-
  change landing and defer `crate::UNKNOWN_SPAN` linkage as out of scope. The directive
  makes a standalone artifact a requirement and the linkage resolution in-scope, and
  requires modifying `gsm2tree_rs.py` (prior scope held the generator out).
- **R-CONFLICT-2** — `selector-shape` / `module-name-stability` / coupling note (req lines
  141, 149-168): the path-vs-submodule reasoning is moot under a user-named module;
  selection is by user-controlled dotted module name.
- **R-CONFLICT-3** — AC5 + "Static-consumer immutability" (req lines 116, 131): the binding
  contract verification is reframed from "real `fltk2gsm.py` against Rust FLTK CST" to
  "API Contract against a non-FLTK generated module (primary) + FLTK-CST dogfooding
  (secondary)."
- **R-CONFLICT-4** — FLTK's `fegen_cst` submodule is a dogfooding test fixture, not the
  general-capability artifact the runtime contract is designed around.

---

## Verdict

The core defect is **resolved**, not merely flagged: user-grammar Rust CST is now a
standalone, user-named, user-built extension, and the cross-extension
`crate::UNKNOWN_SPAN` problem (the deferred `TODO(rust-cst-standalone-so)`) is **resolved
in-design** via Option B (runtime-import sentinel + module-local cache), grounded in the
verified fact that node `span` is an opaque `PyObject` so no Rust-level linkage to FLTK's
crate is required. Options C/D are documented with tradeoffs; D is recorded as a forward
TODO. Four requirements-level conflicts are flagged for USER decision and NOT silently
rewritten. The design is internally consistent after cleanup.
