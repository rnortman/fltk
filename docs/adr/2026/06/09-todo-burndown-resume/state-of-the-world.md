# TODO Burndown — State of the World (2026-06-09)

Style: concise, precise, no padding. Audience: user deciding how to resume the burndown.

## TL;DR

- **0 of 8 accepted items implemented.** All 8 designs exist (committed in 6fd32e7) but none went through design review or a user design gate — they are drafts.
- **1 item is done by accident**: `backend-with-source-signature` was fully subsumed by the excise-python rework (commit 4c8f0ad — its message says so explicitly). Slug removed from TODO.md and code. **Drop it from the queue.**
- **4 items are ready as-is** (only line-number staleness, no substantive change needed): `pin-ci-actions`, `extract-rule-name-to-class-name`, `test-class-is-type-body`, `cst-generator-cleanup`.
- **1 item needs a minor design touch-up**: `fegen-cst-rs-single-source` (the rework added a Makefile `gencode` step + a `TODO(slug)` comment the design claims don't exist; both must be cleaned up too).
- **1 item needs a moderate design update**: `rust-cst-pyi` (span annotation is now a union type; new `extend_children` method must be in the .pyi).
- **1 item needs a redesign**: `rust-cst-child-span-test` (its central factual premise — accessors return `terminalsrc.Span` with `.start`/`.end` — is no longer true; the proposed test would fail for the wrong reason).
- **2 new TODOs appeared during the rework, untriaged**: `span-source-as-py-crosscdylib` (real efficiency bug: two O(source-length) ops per span accessor call cross-cdylib) and `rust-cst-child-node-identity`. Not in the accepted batch; user call whether to add them.

Staleness evidence per item: `expl-staleness-<slug>.md` in this directory.

## What happened since the handoff

Handoff (`../06-todo-burndown-triage/handoff.md`) recorded 8 accepted items with designs. Then a side quest: commit 4c8f0ad ("Rust CST holds native Span and children — no Python objects"), with full workflow record at `../06-rust-cst-native-span/` and forensics at `../06-rust-cst-nominal-backend-forensics/` (untracked). Two follow-up Makefile commits (d40d8bc, af6e6f3). Current HEAD: af6e6f3.

The rework changed the Rust CST from Python-object storage (`span: PyObject`, `children: Py<PyList>`) to native storage (`span: Span`, `children: Vec<(Option<Label>, Child)>`), made span accessors return `fltk._native.Span`, added `extend_children` to both backends and the protocol, made the protocol `span` annotation a union, added `make gencode`, and folded in the entire `backend-with-source-signature` design.

**Workflow position**: all 8 items stopped after design *draft*. No `notes-design-*`, dispositions, or judge verdicts exist in any of the 8 dirs. Next step for every surviving item is design review (or design revision first, where flagged below).

## Per-item status

### 1. pin-ci-actions — READY
Design fully applicable. All cited `ci.yml` lines, action refs, TODO comments confirmed at HEAD; no `dependabot.yml`. Only defect: design cites `TODO.md:15`/`15-17`; actual entry is at lines 11–13. Orthogonal to the rework.

### 2. fegen-cst-rs-single-source — MINOR DESIGN UPDATE
Core claim still true: `src/cst_fegen.rs` and `tests/rust_cst_fegen/src/cst.rs` are byte-identical independent copies (both 6857 lines, same md5); the `include!` fix and all design decisions remain valid. Two substantive deltas from 4c8f0ad:
- `Makefile:108` now has a `TODO(fegen-cst-rs-single-source)` comment — design claims no code comment exists ("removal is a no-op"); wrong now.
- `make gencode` (Makefile:104-109) regenerates *both* copies; the second regen step must be removed/replaced when the duplicate is eliminated.
Plus pervasive line-number drift (documented in the staleness file). Fix shape unchanged; design needs these two facts incorporated.

### 3. extract-rule-name-to-class-name — READY
All four duplicated copies exist with unchanged bodies; `fltk/fegen/naming.py` still absent; behavioral analysis (`.lower()` divergence) still accurate. Only staleness: `gsm2unparser.py` cites shifted ~54-61 lines (638-639 → 634-635; 1888 → 1827). The rework did not touch the relevant code.

### 4. test-class-is-type-body — READY
The deletion target (`TestAllClassesImportable`, the `isinstance(cls, type)` assert, AC-7 banner) is intact at shifted lines (now 68–81 in `tests/test_fegen_rust_cst.py`). `CLASS_LABEL_INFO` is now a 4-tuple (rework added a `child_factory` column) — affects only the design's "don't touch this" guard wording, not the change. Applicable as written; implementer must use current line numbers.

### 5. rust-cst-child-span-test — REDESIGN
**Substantially stale.** The design's premise — Rust accessors return the appended `terminalsrc.Span` unchanged, test should assert `.start`/`.end` and `isinstance(result, tsrc.Span)` — is false post-rework:
- Children are stored as native `fltk-cst-core::Span`; `extract_from_pyobject` **rejects** `terminalsrc.Span` (only accepts native/`fltk._native.Span`).
- Accessors return `fltk._native.Span`, which deliberately has no `.start`/`.end` Python attributes — the designed assertion would `AttributeError`.
- `fltk2gsm.py` visitors now go through `_span_text(span)` → `span.text()`; cited lines all moved.
The *gap* is still real (no focused accessor-contract test; slug live at TODO.md:39 and `tests/test_phase4_fegen_rust_backend.py:111-113`), and target location/pairs are still right. Correct contract now: append a native span, assert `child_name().text()` and `isinstance(..., fltk._native.Span)`. Side-finding: existing `TestAppendChildRoundtrip` (`tests/test_fegen_rust_cst.py:142-155`) uses `terminalsrc.Span(0,1)` and may now be broken against a rebuilt extension — worth checking during this item.

### 6. cst-generator-cleanup (label-free + generator-refactor + label-member-private) — READY
Every design claim re-verified at HEAD: all three slugs live, unconditional Label-enum emission in `py_class_for_model` confirmed, Protocol `if labels:` asymmetry confirmed, quintet loops confirmed, no `__all__` confirmed. The rework's new `Span`/`CstModule` protocol classes were *already* in the design's `__all__` list; new `extend_children` is not a per-label method and is outside the quintet extraction scope. Rust backend "no change needed" claim still correct. Line numbers shifted +10 to +22; spike line refs invalid but conclusions valid.

### 7. rust-cst-pyi — MODERATE DESIGN UPDATE
Structure (emit `.pyi` from `_rule_info`, NodeKind handling, `children` as list, partial-write guard) still valid; slug live (TODO.md:27, `genparser.py:279`). Three substantive deltas:
- Design says type `span` as `terminalsrc.Span`; committed protocol now annotates `span: terminalsrc.Span | fltk._native.Span`. Stub must match the union.
- Design's "Rust span is opaque, has no `.start`/`.end`, don't invent them" rationale is dead — getter now returns `fltk._native.Span` with `.start`/`.end`.
- `extend_children` now exists on every node (generator + committed protocol); the `.pyi` structure in §2.1 omits it — conformance would fail.
OQ-1 (Part 1 vs Part 2 split) still open.

### 8. backend-with-source-signature — DONE (subsumed)
Commit 4c8f0ad implemented every design edit exactly (frozen `SourceText` dataclass, `with_source(str | SourceText)` with eager TypeError, selector export) **plus** the out-of-scope parse-path wiring. Commit message: "backend-with-source-signature prerequisite folded in." Slug gone from TODO.md and code; both open design questions resolved matching design defaults. Nothing remains. The ADR dir (`../06-backend-with-source-signature/`) should get a closure note rather than be implemented.

## New, untriaged TODOs from the rework

- **`span-source-as-py-crosscdylib`** (TODO.md:52-54): successor *problem* (not a rename) created by the rework. Generated code's cross-cdylib span getters do `source_full_text_str()` (full source string clone) + Python-constructor call — two O(source-length) operations *per accessor call* — because the locally-registered `SourceText` type ≠ `fltk._native.SourceText`. Fix sketch in TODO: `extract_source_text` preamble helper using `downcast_unchecked` on the shared-rlib invariant, making it O(1). Real efficiency bug in the hot accessor path.
- **`rust-cst-child-node-identity`** (TODO.md:44-46): native child storage returns a fresh `Py<ConcreteNode>` wrapper per accessor call; five tests relaxed `is` → `==`. Behavioral note / possible future work.

Neither has a request, exploration (beyond the rework's docs), or design. Not part of the accepted batch.

## Proposed resume plan (user arbitrates)

1. **Close** `backend-with-source-signature` (write closure note in its ADR dir; no implementation).
2. **Revise designs**: `rust-cst-child-span-test` (redesign), `rust-cst-pyi` (moderate), `fegen-cst-rs-single-source` (minor) — fresh designer per item with the staleness file as added input; then design review chain.
3. **Design review chain** for the 4 ready items (designs were never reviewed) → user design gates as they arrive.
4. **Implementation queue** (serialized, per burndown policy: squash to main incl. ADR docs, no ship-gate, no pushes) — suggested order, cheapest first: pin-ci-actions → test-class-is-type-body → extract-rule-name-to-class-name → rust-cst-child-span-test → fegen-cst-rs-single-source → rust-cst-pyi → cst-generator-cleanup.
5. **User call**: triage `span-source-as-py-crosscdylib` and `rust-cst-child-node-identity` into this batch, or leave for a future burndown.
