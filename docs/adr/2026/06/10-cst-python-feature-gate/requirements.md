# Requirements: cst-python-feature-gate

Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

Sources: `request.md`, `exploration.md` (same dir). Phase 1 of a multi-phase roadmap; roadmap decisions in the request are settled — do not relitigate.

## Goals

Make the Rust CST backend buildable and usable with no Python/pyo3 linkage via a cargo feature gate (default-on = today's behavior), and validate the pure-Rust API surface with a no-unsafe spike plus a gaps report feeding the future Rust-parser phase.

## In scope

1. Cargo feature gate on `fltk-cst-core` separating pyo3 surface from pure-Rust core.
2. Generator changes so generated CST code compiles in both feature modes.
3. Pure-Rust spike exercising CST construction/traversal with no Python linked and unsafe forbidden.
4. Gaps report (findings only) in this ADR dir.
5. CI coverage of the python-off configuration.

## Out of scope

- Rust parser generation or any parsing (in the spike or otherwise) — phase 2.
- Fixes for gaps the spike uncovers — record only.
- Moving generator implementation out of Python (`fltk/fegen/*` stays Python).
- Changes to Python-visible behavior, generated public symbol names, or type-annotation surface.
- Bazel support for the Rust extension (existing `TODO(bazel-rules-rust)` unaffected).

## System behavior

### 1. Feature gate on fltk-cst-core

- A cargo feature (working name `python`; final name/polarity is a design decision — see User-visible surface) controls pyo3 linkage.
- **Feature on (default):** byte-for-byte today's behavior. `Span`/`SourceText` are `#[pyclass]`es; `cross_cdylib` module and its re-exports present; pyo3 dependency active.
- **Feature off:**
  - No `pyo3` anywhere in the resolved dependency graph of `fltk-cst-core` (acceptance: `cargo tree --no-default-features` shows no `pyo3`).
  - `Span` and `SourceText` are plain Rust types; **all** existing pure-Rust methods remain available (per exploration: `Span::unknown`, `new_sourceless`, `new_with_source`, `start`, `end`, `source_full_text_str`; `SourceText::from_str` — list illustrative, not exhaustive), with `PartialEq`/`Hash`/`Clone` semantics unchanged (`Span` eq/hash over `(start, end)` only). Exception: `source_as_py` is inherently pyo3-bound and is python-on only.
  - `cross_cdylib.rs` compiles out entirely. Consequence: zero `unsafe` code reachable — enforced structurally (the file is gated), not by convention (exploration invariant 1: that file is the sole `unsafe` location).
  - The pure-Rust API additionally exposes, with no Python types in signatures: span text access (the `text` behavior currently locked inside `#[pymethods]`) and `merge`/`intersect` equivalents. Native error/return types for merge/intersect are a design decision (see Open questions).
- **Native surface is mode-independent.** All native (non-pyo3) API — existing and newly exposed — is available identically in both feature modes; the feature gates only the pyo3 surface. Rationale: the gate exists to define and stabilize the native API contract the phase-2 parser backend codes against, and roadmap mode 3 (Python apps with a Rust parser) runs that backend in python-**on** builds. A python-off-only native API is non-compliant.
- `crate-type` stays `rlib`; downstream cdylib crates' existing `extension-module` feature arrangement keeps working unchanged.

### 2. Generated CST code compiles in both modes

- Generator (`gsm2tree_rs.py` behavior, not its internals) emits output that:
  - **Feature on:** functionally identical to today's output for all Python-visible surface — node classes, label enums, accessor quintets, `children` getters, `append`/`extend`/`extend_children`, equality/hash/repr, `register_classes`. Byte-identical output preferred where achievable; functional identity required.
  - **Feature off:** compiles with no pyo3 dependency, providing at minimum: node construction (`new_native`), child append (`push_child_native`) and traversal (`children_native`), span access with source (`span_native` + text read), and structural equality (`PartialEq` on nodes and child enums). Label enums and `NodeKind` retain `Clone`/`PartialEq`/`Eq`/`Hash`.
- Mechanism (single cfg-gated output vs dual output) is the central design question — both acceptable per the request if argued; this doc does not constrain it beyond the acceptance criteria above and the regen-workflow constraints below.
- Applies to all generated artifacts on the standard regen path (`make gencode`): `src/cst_fegen.rs`, `src/cst_generated.rs`, and fixture outputs.

### 3. Pure-Rust spike

Per user direction (verbatim): "doesn't need to be a parser really but just Rust code that executes construction and traversal of CST without any python linked in at all and without unsafe operations."

- A test crate or `cargo test` target that, with the python feature off, programmatically builds a CST using generated nodes for the PoC grammar (`fltk/fegen/test_data/poc_grammar.fltkg`) — or an equivalently representative generated grammar if the designer argues for it — and asserts results.
- Must exercise: node construction; attaching source-bearing spans; appending labeled children; traversing the tree; reading span text; span `merge`/`intersect`; structural equality.
- Acceptance criteria:
  - Builds and passes under `cargo test` with the python feature off.
  - "No Python linked" verified mechanically (e.g. `cargo tree` for the spike shows no `pyo3`, or symbol inspection) — the check is automated, not eyeballed.
  - `#![forbid(unsafe_code)]` (or equivalent compiler-enforced mechanism) on the spike crate/module. (Not on `fltk-cst-core` itself, which retains `unsafe` for python-on mode.)
- No parsing in the spike.

### 4. Gaps report

- A findings document in `docs/adr/2026/06/10-cst-python-feature-gate/` recording whatever the pure-Rust API makes awkward or impossible for a future parser backend: span construction ergonomics, trivia handling, error/diagnostic types, anything a parser would need.
- Findings only — no fixes.
- May legitimately be short or empty; its **absence** is a scope failure (request, Verification expectations).

### 5. CI / automated gate

- The python-feature-off configuration (build + test, including the spike and the no-pyo3 mechanical check) is exercised by CI so it cannot rot.
- The same check is invocable locally via the standard precommit check entrypoint (or an equivalently documented single command) — rot prevention requires developers can reproduce the failure before push, not only discover it in CI. (Exploration: CI's substance today is `make check`, whose `cargo-test` covers only the workspace.)
- Existing CI path (default mode) unchanged in behavior.

## User-visible surface

Consumers here are out-of-tree developers who regenerate CST code and depend on `fltk-cst-core`.

- **Cargo feature**: name + polarity on `fltk-cst-core` (and on generated-code consumers' Cargo manifests as documented usage). Working name `python`, default-on; exploration recommends this as the idiomatic additive convention. Final name/polarity is delegated to design per the request — but whatever is chosen is public API from day one.
- **Pure-Rust API of `fltk-cst-core`**: the python-off exports (Span/SourceText constructors, accessors, text, merge/intersect equivalents) become a stabilizing contract the phase-2 parser backend will code against. New native names must not collide with or rename existing native methods (`new_native`, `push_child_native`, `span_native`, `children_native` are existing public generated API).
- **Generated code shape**: existing public symbols, Python-visible behavior, and annotation surface unchanged in default mode (CLAUDE.md breaking-change policy). New pure-Rust surface is additive.
- **Build workflows unchanged**: `maturin develop`, `uv run pytest`, `make gencode` (idempotent), and out-of-tree regeneration with current settings all behave identically by default. If the generator gains a mode/flag (dual-output design), the default invocation must produce today's result.
- **Automated checks**: python-off mode exercised in CI and reproducible via the standard local check entrypoint (or a documented single command).

## Constraints

- **Default behavior unchanged.** Feature defaults to python-on; every existing build path works identically. Default-mode generated output functionally identical; byte-identical preferred.
- **Generated output is public API** (CLAUDE.md): no renames, no annotation churn, no Python-visible behavior change. Absence of in-tree consumers is not evidence of safety.
- **No `unsafe` reachable in python-off configuration**, enforced structurally.
- **Rust-only applications pay no Python-associated costs** — no pyo3 in the dep graph, no GIL machinery, no Python-import-at-runtime paths (e.g. `Span::kind`'s `fltk.fegen.pyrt.terminalsrc` import is python-on only).
- TDD throughout per CLAUDE.md (full design-stage process — DTC/EDTC).
- Verification gates (from request): full suite green in default mode (`uv run --group dev maturin develop && uv run pytest`); `uv run ruff check . && uv run pyright`; `cargo clippy -- -D warnings` in **both** feature modes; `make gencode` idempotent; CI exercises both modes; gaps report exists.

## Open questions

1. **Native error type for `merge`/`intersect`** (exploration open question 1): today they return `PyResult`; python-off equivalents need a pure-Rust type. Options: `Result<Span, String>`, `Option<Span>` (for intersect), or a dedicated error enum. A dedicated error enum is the most forward-compatible for the phase-2 parser backend; this can be settled in design unless the user has a preference. The chosen type becomes public API.
2. **Spike location** (exploration open question 3): new workspace member crate vs `#[cfg(test)]` module in `fltk-cst-core` vs standalone fixture-style crate. Affects Makefile/CI integration and where `#![forbid(unsafe_code)]` lands. Design decision; requirements only demand `cargo test` coverage in CI with the mechanical no-pyo3 check.
3. **Native `Span::kind` equivalent** (exploration open question 5): the spike doesn't need it; `kind` is a Python-side discriminant. Proposed: out of scope for python-off mode; if the gaps report shows a parser would need it, that's phase-2 input. Redirect by saying "include a native kind" if a pure-Rust discriminant is wanted now.
4. **Feature name/polarity**: the request delegates this to the designer ("designer picks final name/polarity"); working name `python`, default-on, which exploration also recommends as the idiomatic additive convention. This doc treats that as the design default, not a requirements-level decision — the designer may deviate with rationale (e.g. `pyo3` to track the dependency name), keeping default-on behavior intact. Whatever is chosen is public API from day one.
