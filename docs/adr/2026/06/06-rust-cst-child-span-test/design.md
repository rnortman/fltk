# Design: rust-cst-child-span-test

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human. (Note retained per authoring protocol; applies to this doc.)

Scope: test-only. No source changes. See `request.md` for the original spec and `exploration.md` for the original contract exploration — **both predate commit 4c8f0ad and are superseded on the accessor contract**; see "Staleness corrections" below and `docs/adr/2026/06/09-todo-burndown-resume/expl-staleness-rust-cst-child-span-test.md` for the forensics. This design follows current code (HEAD af6e6f3).

## Staleness corrections (supersedes request.md constraints)

Commit 4c8f0ad ("Rust CST holds native Span and children — no Python objects") rewrote the child model:

- Children are stored as **native `fltk-cst-core::Span`** inside a per-class child enum (`src/cst_fegen.rs:4295-4297`, `IdentifierChild::Span(Span)`; same shape for `RawStringChild`, `LiteralChild`).
- `append_<label>` extracts via `extract_from_pyobject` (`src/cst_fegen.rs:4325-4338`), which accepts only the locally-registered `Span` or `fltk._native.Span` (cross-cdylib path through `extract_span`, `src/cst_fegen.rs:16-42`). A `terminalsrc.Span` is **rejected with `TypeError`** ("unsupported child type").
- `child_<label>` reconstructs a **fresh `fltk._native.Span` Python object** per call via `to_pyobject` (`src/cst_fegen.rs:4307-4323`): sourceless → `Span(start, end)`; source-bearing → `Span.with_source(start, end, SourceText(full_text))`. No identity guarantee — `TODO(rust-cst-child-node-identity)` (`TODO.md:40-42`) documents the clone-on-extraction behavior; tests must use value/attribute assertions, never `is`.

request.md's "CRITICAL correction" (assert `.start`/`.end` on a returned `terminalsrc.Span`, never on a Rust span) is therefore **doubly invalidated**:

1. The accessor no longer returns `terminalsrc.Span` — it returns `fltk._native.Span`, and appending a `terminalsrc.Span` is rejected.
2. `fltk._native.Span` **now exposes `.start`/`.end` as read-only getters** for drop-in parity with `terminalsrc.Span` (`crates/fltk-cst-core/src/span.rs:354-365`; `tests/test_rust_span.py:61-68` asserts readability). The old "intentionally absent" doc comment is gone (`src/span.rs` is now a two-line re-export of `fltk_cst_core::{SourceText, Span}`).

Note: the staleness exploration's §4 ("assert `.text()`, not `.start`/`.end`") is itself slightly off — it carried forward the pre-getter belief. Current code supports both reads, and `fltk2gsm._span_text` uses both (see below), so the test asserts both.

## Root cause / context

`fltk2gsm.Cst2Gsm` reads span text through `_span_text(span)` (`fltk/fegen/fltk2gsm.py:24-41`) on the object returned by a child accessor, in three visitors:

- `visit_identifier` (`fltk2gsm.py:43-45`): `span = identifier.child_name()`
- `visit_literal` (`fltk2gsm.py:164-166`): `span = literal.child_value()`
- `visit_regex` (`fltk2gsm.py:168-170`): `span = regex.child_value()`

`_span_text` requires, of the accessor result:

- `.text()` — primary path (`fltk2gsm.py:31`); succeeds for source-bearing spans.
- `has_source()` and `.start`/`.end` — fallback path for sourceless spans (`fltk2gsm.py:37-41`, terminals slice).

With the Rust fegen backend the accessor result is an `fltk._native.Span` (reconstructed from native storage, `src/cst_fegen.rs:4564-4582` for `Identifier.child_name`; `:4943` `RawString.child_value`; `:5322` `Literal.child_value`).

Gap: no focused test asserts this contract. Coverage is only the indirect AC8 equality tests (`tests/test_phase4_fegen_rust_backend.py:67-87`). A regression in accessor return type (e.g. an object lacking `.text()`) would surface as an `AttributeError` inside `_span_text`, buried in a visitor stack, not as a localized failure naming the accessor. Likewise a source-preservation regression in `to_pyobject` (dropping the source on reconstruction) would surface as a confusing `ValueError`/wrong-text failure deep in parsing. This design adds the localized regression test and retires the `TODO(rust-cst-child-span-test)` slug (live at `TODO.md:35-37` and `tests/test_phase4_fegen_rust_backend.py:111-113`).

## Proposed approach

One file touched: `tests/test_phase4_fegen_rust_backend.py` (already gated by `pytest.importorskip("fegen_rust_cst")` at line 29). Add `from fltk._native import Span, SourceText  # noqa: E402` to the post-skip import block — the suppression is mandatory: the `importorskip` call at line 29 precedes the imports, so ruff E402 fires without it (all existing post-skip imports at lines 34-39 carry it; `make check` is the gate). `terminalsrc as tsrc` is already imported (line 38).

Add one test class, `TestChildSpanAccessorContract`, replacing the TODO comment at lines 111-113. Parametrize over the three `(class, append_method, child_method)` triples that match the three `fltk2gsm` visitors (method names confirmed in `CLASS_LABEL_INFO`, `tests/test_fegen_rust_cst.py:43-61`):

- `fegen_rust_cst.Identifier` — `append_name` / `child_name` (→ `visit_identifier`)
- `fegen_rust_cst.Literal` — `append_value` / `child_value` (→ `visit_literal`)
- `fegen_rust_cst.RawString` — `append_value` / `child_value` (→ `visit_regex`; `visit_regex(self, regex: cst.RawString)` at `fltk2gsm.py:168`)

Three tests, each parametrized over the triples:

1. **Sourceless roundtrip — fallback-path contract.**
   `span = Span(3, 9)` (distinct nonzero, non-equal values so swapped/zeroed fields fail); `node = Class()`; `append_<label>(span)`; `result = child_<label>()`. Assert:
   - `isinstance(result, Span)` — pins the return type as `fltk._native.Span`.
   - `result.start == 3` and `result.end == 9` — pins the getters `_span_text`'s fallback slice depends on.
   - `result.text() is None` and `result.has_source() is False` — pins sourceless semantics (`crates/fltk-cst-core/src/span.rs:218-248,298-300`).

2. **Source-bearing roundtrip — primary-path contract + source preservation.**
   `src = SourceText("hello world!")`; `span = Span.with_source(3, 9, src)`; append; read back. Assert:
   - `isinstance(result, Span)`; `result.start == 3`; `result.end == 9`.
   - `result.has_source() is True` and `result.text() == "lo wor"` — pins that source survives the native-storage roundtrip (`to_pyobject` rebuilds via `SourceText(full_text)`, `src/cst_fegen.rs:4314-4317`). ASCII source text keeps codepoint-vs-byte questions out of scope (codepoint semantics are pinned in `tests/test_rust_span.py:125+`).
   - Do **not** assert anything about the identity of the result's source object — `to_pyobject` constructs a fresh `SourceText` from the full text string; only content is preserved.

3. **Rejection — append contract.**
   `pytest.raises(TypeError)` around `append_<label>(tsrc.Span(3, 9))` — pins that `extract_from_pyobject` rejects non-`Span` children (`src/cst_fegen.rs:4325-4338`). This is a deliberate contract pin: if a future change re-admits arbitrary Python children, this test fails loudly and must be updated deliberately rather than the contract drifting silently.

Do **not** assert `result is span` anywhere — identity is explicitly not guaranteed (clone-on-extraction; `TODO.md:40-42`); the existing roundtrip test these mirror already uses `==` for this reason (`test_append_and_child_roundtrip`, `tests/test_fegen_rust_cst.py:132-139`).

## Edge cases / failure modes

- **`fegen_rust_cst` not built.** Module-level `importorskip` (line 29) skips the whole file. An all-skipped CI lane is already flagged as a failure signal by the module docstring; no new handling.
- **Accessor on empty node.** `child_<label>()` with nothing appended raises `ValueError` ("Expected one ... child", `src/cst_fegen.rs:4576-4580`); not this test's contract — every case appends first, matching existing roundtrip tests.
- **Cross-cdylib span.** The test appends `fltk._native.Span` into a `fegen_rust_cst` (standalone cdylib) node — this exercises the slow cross-cdylib path in `extract_span` (`src/cst_fegen.rs:21-37`), which is exactly the path real out-of-tree consumers hit. A regression in cross-cdylib extraction fails here cleanly.
- **Two backends, one generated surface.** The file uses the standalone `fegen_rust_cst` extension rather than embedded `fltk._native.fegen_cst`; consistent with the rest of the file and the TODO's stated location.
- **Regressions this catches:** accessor returning an object lacking `.text()`/`.start`/`.end` → assertion or `isinstance` failure naming the accessor; `to_pyobject` dropping source → test 2's `text()`/`has_source()` assertions fail; `extract_from_pyobject` silently accepting wrong types → test 3 fails.
- **What it deliberately does not catch:** end-to-end parse correctness (AC8's job); child Python-object identity (out of scope, tracked by `rust-cst-child-node-identity`).

## Test plan

After this change, `tests/test_phase4_fegen_rust_backend.py` contains, in addition to AC6/AC8/AC9:

- `TestChildSpanAccessorContract::test_sourceless_span_start_end` — 3 params.
- `TestChildSpanAccessorContract::test_source_bearing_span_text` — 3 params.
- `TestChildSpanAccessorContract::test_append_rejects_terminalsrc_span` — 3 params.

Verification:
- Build: `uv run --group dev maturin develop` then `make build-fegen-rust-cst`.
- `uv run pytest tests/test_phase4_fegen_rust_backend.py` passes; skips cleanly without the extension.
- Sanity (manual, not committed): temporarily make `to_pyobject` drop the source branch and confirm test 2 fails at its own assertion, not deep in a visitor.

Cleanup:
- Remove the `TODO(rust-cst-child-span-test)` comment block (`tests/test_phase4_fegen_rust_backend.py:111-113`) — the new class takes its place.
- Remove the `## rust-cst-child-span-test` entry from `TODO.md` — locate by slug heading (at line 35; entry spans lines 35-37). Do not touch the adjacent `## rust-cst-child-node-identity` entry (line 40).

## Open questions

None. request.md's stale constraints are superseded by current code (documented above); following the code as it stands requires no user judgment. The rejection pin (test 3) is the only authored choice beyond the staleness exploration's recommendation, and it pins behavior the code already enforces.
