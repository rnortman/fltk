# Request: named children mutators on both backends (insert / remove / replace / clear)

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

**Type:** New feature — additive public API on generated CST node classes, BOTH backends in lockstep.

**Origin:** Replaces TODO.md slug `rust-cst-children-list-view` (live-proxy idea rejected in triage, `docs/adr/2026/06/11-todo-burndown/triage.md` item 12).

**USER DIRECTION (verbatim, binding):** "OK, yes we want to do named mutators on both backends."

## Background

Backend divergence: Python-backend `node.children` is the node's actual dataclass list (in-place mutation edits the tree — an ACCIDENT of representation, not designed API; the pattern is now test-banned in generated parser code, `fltk/fegen/test_genparser.py:135-163`). Rust-backend `node.children` is a per-call snapshot (`_children_getter`, `gsm2tree_rs.py:875`); in-place mutation is a silent no-op. Full analysis in `exploration.md`, this dir.

The documented cross-backend mutation API today is append/extend only: `append`, `append_<label>`, `extend_<label>`, `extend_children` (exploration §4). Applications that need to rewrite trees (remove a child, replace one, insert at a position, clear) have no supported path on the Rust backend and only the accidental live-list path on Python.

Triage decision rationale (user-ratified): a live sequence-proxy was rejected — one extra pyclass per node type (PyO3 has no generic pyclasses, ~doubles generated class count), ~8-10 dunders each, AND a proxy is not a `list` (breaks `isinstance`, type parity with the Python backend's plain list, Protocol annotation `children: list[tuple[...]]`). Named, type-checked mutators are less code and keep `node.children` a plain list/snapshot on both backends.

## Fix shape

Add named mutator methods to generated node classes on BOTH backends with identical names and semantics. Candidate set (design finalizes names/signatures/error behavior): `insert(index, label, child)`, `remove_at(index)`, `replace_at(index, label, child)`, `clear()`. Index semantics (negative indices? out-of-range errors) must match between backends and be pinned by shared tests.

- Rust backend (`gsm2tree_rs.py` pymethods): write-lock + the same label/child type-checking conversion machinery `append` already uses (`_generic_append` path). Respect the hard invariant: NO Python work while holding a node lock (extract/convert outside or before the guard; see `_span_getter_setter` comments `gsm2tree_rs.py:836-851`). Design decides whether matching native (GIL-free) mutators are also emitted for symmetry with the native accessor API.
- Python backend (`gsm2tree.py` dataclass methods): same-named methods delegating to the underlying list.

## Constraints / non-goals

- Additive only: no change to `node.children` getter semantics on either backend (Python stays a live list for back-compat; Rust stays a snapshot). No proxy class.
- Fixed method names cannot collide with per-label generated methods (`child_<label>` etc. are prefixed, so bare `insert`/`clear` are safe) — design should verify against the reserved-name precedent (`_RESERVED_LABELS`, `gsm2tree_rs.py:24-26`) and extend it if a label could ever shadow a mutator.
- Per CLAUDE.md: this is new public API for out-of-tree consumers — naming is a deliberate, hard-to-reverse decision; design should state the naming rationale.
- Identity/registry interactions on Rust (removed children's handles, replaced children) must be considered in design — removal must not corrupt registry identity guarantees.
- Non-goal: making `node.children` mutation work on Rust; non-goal: deprecating Python's live-list behavior (separate question, out of scope).

## Verification expectations

- Cross-backend behavior tests: identical operation sequences produce identical trees (spans/labels/order) on both backends, including error cases (bad index, bad label type, bad child type).
- Rust: identity tests around remove/replace (registry behavior for evicted/replaced children).
- Existing suites pass; regenerate all outputs; `make fix`; `uv run pytest` + `cargo test` clean.
