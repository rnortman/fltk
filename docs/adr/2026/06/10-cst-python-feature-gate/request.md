# Request: cst-python-feature-gate

Style: concise, precise, no padding, no preamble. Audience: smart LLM/human. This doc is self-contained — the executing session has no context from the session that authored it. Run your own exploration; file citations below are starting points, not verified-at-HEAD line numbers.

**Type**: new feature (cargo feature gate on the Rust CST) + spike (pure-Rust consumer exercise). Phase 1 of a multi-phase roadmap; later phases are out of scope here.

## Roadmap context (product-owner decisions — do not relitigate)

FLTK's ultimate goal is to support all three of:

1. **Pure Python applications** — works today (Python parser + Python or Rust CST).
2. **Pure Rust applications** — no Python linked at all.
3. **Python applications with a Rust parser** — parser in Rust producing Rust CST, crossing the Python boundary once per parse instead of per node.

User direction, verbatim: "I expect *generation* to stay in Python; python generates rust." The generator toolchain (`fltk/fegen/*`) remains Python; only the generated artifacts and runtime crates gain a Python-free mode.

Sequencing decision: the feature gate comes **before** the Rust parser backend, because (a) it defines and stabilizes the native API contract the parser backend will code against, (b) it surfaces API gaps cheaply via the spike below, (c) it gives CI a pure-Rust build target that prevents pyo3 entanglement creep during the longer parser effort, and (d) it lets the future parser backend iterate under plain `cargo test`. Rust parser generation is out of scope here; this prepares the CST backend for later pure-Rust applications.

## Background

The Rust CST backend (`fltk/fegen/gsm2tree_rs.py`) generates node structs whose core data model is pure Rust (`Vec<(Option<Label>, Child)>`, `Box<Child>` ownership, native API: `new_native`, `push_child_native`, `span_native`, `children_native`, used internally by e.g. `extend_children`). But everything is currently pyo3-entangled:

- `crates/fltk-cst-core` (`crate-type = ["rlib"]`): `Span` and `SourceText` are `#[pyclass]`; `src/cross_cdylib.rs` is entirely Python-boundary code (`extract_span`, `extract_source_text`, `span_to_pyobject`, ABI-marker gate, GILOnceCell type caches) — including all the `unsafe` in this area. See `docs/adr/2026/06/10-preamble-helpers-into-cst-core/` and `docs/adr/2026/06/10-span-source-as-py-crosscdylib/` for why that module exists and how it works.
- Generated files (`src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fixture/src/cst.rs`): node structs carry `#[pyclass]`, large `#[pymethods]` blocks (per-label accessor quintets, `to_pyobject`/`extract_from_pyobject` child conversion, Python `children` getters), `register_classes`, and `use pyo3::...` preambles.
- PoC grammar with the standard regen path: `fltk/fegen/test_data/poc_grammar.fltkg` → `src/cst_generated.rs` via `make gencode`.

In a Python-free build none of the pyo3 surface is needed, and — important — none of the `unsafe` is either: the unsafe exists solely to smuggle layout-identical values past CPython's per-cdylib nominal type identity. One crate, one type, safe `Arc` clones.

## Scope

1. **Feature-gate `fltk-cst-core`.** A cargo feature (working name `python`, default-on; designer picks final name/polarity) such that with the feature off: no pyo3 dependency, `Span`/`SourceText` are plain Rust types, `cross_cdylib.rs` compiles out entirely. With the feature on: byte-for-byte today's behavior.
2. **Feature-gate generated CST code.** The generator emits output that compiles in both modes (e.g. `#[cfg(feature = "python")]` around pyclass attrs / pymethods blocks / registration / preamble imports — mechanism is the central design question; alternatives like dual-output modes are acceptable if argued). The pure-Rust subset must include: node construction, child append/traversal, spans with source, structural equality.
3. **Pure-Rust spike** (the validation artifact). User direction, verbatim: it "doesn't need to be a parser really but just Rust code that executes construction and traversal of CST without any python linked in at all and without unsafe operations." Concretely: a test crate (or `cargo test` target) that, with the python feature off, builds a CST for the PoC grammar programmatically — construct nodes, attach source-bearing spans, append labeled children, traverse the tree, read span text, exercise merge/intersect — and asserts results. Verify "no Python linked" mechanically (e.g. the dependency tree contains no `pyo3`, or symbol inspection), and `#![forbid(unsafe_code)]` (or equivalent) on the spike.
4. **Gaps report.** The spike doubles as exploration for the parser-backend phase. Record in this ADR dir whatever the pure-Rust API makes awkward or impossible (span construction ergonomics, trivia handling, error/diagnostic types, anything a parser would need) — findings only, no fixes; that's the next phase's input.
5. **CI.** Add the python-feature-off build/test to CI so the configuration can't rot.

## Constraints / non-goals

- **Default behavior unchanged.** Feature defaults on; every existing build path (`maturin develop`, `uv run pytest`, `make gencode`, out-of-tree consumers regenerating with current settings) works identically. Generated output for the default mode should remain functionally identical; byte-identical is preferred where achievable.
- **Generated output is public API for out-of-tree consumers** (see CLAUDE.md). No renames, no annotation churn, no Python-visible behavior change.
- **No parser work.** No Rust parser generation, no parsing in the spike. Resist scope creep toward phase 2.
- **No `unsafe` reachable in the python-off configuration.** Enforced structurally (gating out `cross_cdylib.rs`), not by convention.
- Generator implementation stays Python.
- Rust-only applications pay no Python-associated costs.

## Verification expectations

- TDD throughout per CLAUDE.md (this is complex enough for the full design-stage process).
- Spike crate builds and passes under `cargo test` with the python feature off, with no pyo3 in its resolved dependency graph and unsafe forbidden.
- Full existing suite green in default mode: `uv run --group dev maturin develop && uv run pytest`; `uv run ruff check . && uv run pyright`; `cargo clippy -- -D warnings` in both feature modes; `make gencode` idempotent.
- CI config exercises both modes.
- Gaps report exists in this ADR dir (it may legitimately be short or empty, but its absence is a scope failure).
