Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Reviewed commits: f8fdb53..627c2bd (increments 1-10 + 2 gate fixes). Base: f8fdb53. HEAD: 627c2bd.

## Verdict: Job is finished. No escalation.

All design §2 sub-sections are implemented. All §4 acceptance criteria are met (see per-item detail below). One deliberate deviation from design § option choice (documented). One minor test-coverage gap that does not affect functional correctness. No unjustified punts.

---

## §2 sub-section completion

- **§2.1** (`fltk-cst-core` split crate): Complete. `crates/fltk-cst-core/` created; `Span`/`SourceText` moved; downstream fixture crates depend on it with `default-features = false`.
- **§2.2** (native `span` field): Complete. `span: Span` in every generated node struct; `Span::unknown()` sentinel; explicit Python getter/setter; no `UNKNOWN_SPAN_CACHE`. **Deviation:** design chose "Option B: no Python `.start`/`.end` getter"; implementation added them in increment 7 for drop-in parity with `terminalsrc.Span`. Explicit, documented in impl log (increment 7); test enforcement of Option B removed. Rationale (downstream consumer parity) is sound. Deviation does not violate the core requirement.
- **§2.3** (native children container): Complete. Per-node `<Name>Child` enums, `Vec<(Option<Label>, Child)>` storage, `append`/`extend`/`extend_children`, per-label accessors, on-demand `children` getter. `gsm2parser.py` emits `extend_children` calls instead of getter-mutation.
- **§2.4** (native equality, hash, repr): Complete. `_eq_method` uses native `PartialEq`; hash unchanged; repr uses native fields.
- **§2.5** (parse path native spans): Complete. `backend-with-source-signature` prerequisite landed (increment 5: Python `SourceText` wrapper, portable `Span.with_source`). `gsm2parser.py` emits `_source_text` field construction and `Span.with_source` calls. All four `*.rs` files regenerated.
- **§2.6** (`fltk2gsm` migration): Complete with deliberate fallback. `_span_text(span)` calls `span.text()` first; falls back to `self.terminals[span.start:span.end]` for bootstrap-phase sourceless Python-backend spans. Design said `text_or_raise()` or `.text()` — `.text()` variant used. Fallback is an explicit compatibility shim for the bootstrap transition (documented in code comment). Once `fltk_parser.py` regeneration is fully bootstrapped, only the `text()` path executes.
- **§2.7** (protocol annotation widening): Complete. `gsm2tree.py:560` emits `terminalsrc.Span | fltk._native.Span`; all four protocol files regenerated; `TYPE_CHECKING` guard added.
- **§2.8** (generator changes): Complete. All four generated `*.rs` files produced by the updated generator; no hand-edits.

---

## §4 acceptance criteria

1. **Pure-Rust node state test (no GIL):** `tests/rust_cst_fixture/src/native_tests.rs` — 7 `#[cfg(test)]` tests; no `Python::with_gil`, no pyo3 runtime anywhere in the file. Constructs `Entry`+`Identifier` subtrees, walks to leaf `Span`, reads `start()`/`end()`, compares equal/unequal subtrees. **Met.**

2. **No-PyObject audit:** `tests/test_gsm2tree_rs.py::TestNoPyObjectAudit` — grep gates assert no generated node struct has `span: PyObject`, no `Py<PyList>` children field, no `UNKNOWN_SPAN_CACHE`. **Met.**

3. **Span setter type check:** `tests/test_rust_cst_poc.py::test_span_setter_rejects_non_span` — `node.span = object()` raises `TypeError`; `test_span_getter_returns_native_span` asserts returned span is `fltk._native.Span`. **Met.**

4. **Native equality (Python):** `tests/test_rust_cst_poc.py::TestNativeEquality` — equal/differing span and children tested. **Met.**

5. **Cross-crate construction (Rust):** `tests/rust_cst_fixture/src/native_tests.rs` — `Span::new_sourceless`, `Span::unknown`, `Identifier::new_native`, `push_child_native`, `span_native()`, `children_native()` all exercised via public API with no `pub(crate)` access. **Met.**

6. **Parse path (Python, Rust backend):** Covered via integration: `test_fltk2gsm_behavioral_equivalence` (`test_clean_protocol_consumer_api.py:334`) parses `fegen.fltkg` with the Rust backend via `parse_grammar_file(..., rust_fegen_cst_module="fegen_rust_cst")`; `fltk2gsm.Cst2Gsm` then calls `span.text()` on child spans, succeeding only if they are source-bearing. **Minor gap:** no explicit `isinstance(node.span, fltk._native.Span)` assertion after a live parse. Functionally equivalent because §4 item 2 audit structurally guarantees every stored span is native `Span`, and the `test_fltk2gsm_behavioral_equivalence` would fail if `span.text()` didn't work. Not a blocking gap.

7. **fltk2gsm under both backends:** `test_fltk2gsm_behavioral_equivalence` + `tests/test_phase4_fegen_rust_backend.py::TestFltk2gsmRustBackend` — both backends produce equal `gsm.Grammar` output on the same input. **Met.**

8. **Protocol additive-widening (pyright):** `tests/test_cst_protocol.py::test_python_backend_consumer_still_type_checks` + `tests/test_cst_protocol.py::test_rust_backend_span_satisfies_widened_protocol` + `tests/test_clean_protocol_consumer_api.py::test_python_backend_consumer_pyright_clean`. **Met.**

9. **Cross-backend behavioral equivalence:** `tests/test_phase4_rust_fixture.py::TestAC7BothBackends` — construction, span read/write, label equality/hash, isinstance dispatch, `children` list protocol, full parse roundtrip run against both Python and Rust backends. `.kind` cross-backend covered in `test_clean_protocol_consumer_api.py` §4 item 6/7 tests. `repr` excluded per design. **Met.**

---

## Deferred TODOs

- `TODO(rust-cst-child-node-identity)`: native `Box<ChildNode>` ownership means the same child read twice via getter may not be the same Python object. Design explicitly classifies this as non-blocking (§2.3, §3, §5). Rationale sound. **Correctly deferred.**

---

## No findings.
