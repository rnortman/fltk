Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Reviewed commits: f8fdb53..1b54878.
Design: §4 acceptance criteria in `docs/adr/2026/06/06-rust-cst-native-span/design.md`.

---

## §4 item 1 — Pure-Rust GIL-free acceptance test

**Present and solid.** `tests/rust_cst_fixture/src/native_tests.rs` has 7 `#[cfg(test)]` tests,
no `Python::with_gil`, no pyo3 import anywhere in the file. Exercises: `Span::new_sourceless`,
`Span::unknown`, `new_native`, `push_child_native`, `span_native().start()/end()`,
`children_native()`, structural equality (`==`/`!=`) across equal and differing subtrees at node
span and child span. Uses only public Rust API. Fixture crate depends on `fltk-cst-core` with
`default-features = false`.

One minor gap: the Rust `with_source` constructor path (`Span::with_source(start, end,
source_text)` → `text()`) is not exercised in `native_tests.rs` — only sourceless spans appear.
The Python-side `TestSpanSourcePreservation` tests cover round-trip source-preservation through
the Python accessor layer. For a pure-Rust test this is the completeness hole, but the core
acceptance criterion (GIL-free construct/walk/compare) is fully met.

**No finding needed.** The gap is minor and the criterion is met.

---

## §4 item 2 — No-PyObject audit (grep gate)

**Present and solid.** `tests/test_gsm2tree_rs.py::TestNoPyObjectAudit` runs against the
generator's *output* (from `RustCstGenerator` live; the `poc_source` and `fegen_source` fixtures
regenerate on the fly). Asserts: no `span: PyObject,`, no `children: Py<PyList>,`, `Vec<(Option<`
present, no `UNKNOWN_SPAN_CACHE`, `Span::unknown` present, no `UnknownSpan` sentinel string.
`TestNativeEqualityGenerated` additionally confirms `self.span.bind(py).eq(` and
`self.children.bind(py).eq(` are absent from the generated equality method.

The audit runs against generator output, not committed files — it would catch a generator
regression even if committed files were stale. This is the correct level of testing.

---

## §4 item 3 — Span setter type check (Python)

**Present and solid.** `tests/test_rust_cst_poc.py::test_span_setter_rejects_non_span` asserts
`node.span = object()` raises `TypeError`. `test_span_getter_returns_native_span` asserts
`isinstance(result, Span)` (where `Span` is `fltk._native.Span`). Also
`test_span_keyword_construction_stores_provided_span` (in `TestAC5ApiContract`) sets span via
constructor and reads it back with `==`.

---

## §4 item 4 — Native equality (Python)

**Present and solid.** `tests/test_rust_cst_poc.py::TestNativeEquality` exercises equal/unequal
cases for span and children differences. `TestNativeEqualityGenerated` in `test_gsm2tree_rs.py`
structurally confirms the generated code routes through `self == &*other_node` not Python `.eq()`.

---

## §4 item 5 — Cross-crate construction (downstream fixture, Rust)

**Present and solid.** Same `native_tests.rs` as item 1. `Span::new_sourceless`, `Span::unknown`,
`Identifier::new_native`, `Entry::new_native`, `push_child_native`, `span_native()`,
`children_native()` all called from the fixture crate's `#[cfg(test)]` module without accessing
`pub(crate)` fields.

---

## §4 item 6 — Parse path (Python, Rust backend)

**Pre-pass flagged gap: no explicit `isinstance(node.span, fltk._native.Span)` post-parse.**

Assessment: the gap is real but not material.

What's covered: `test_fltk2gsm_behavioral_equivalence` (line 334,
`test_clean_protocol_consumer_api.py`) parses `fegen.fltkg` with the Rust backend through
`parse_grammar_file(..., rust_fegen_cst_module="fegen_rust_cst")` and calls `fltk2gsm.Cst2Gsm`,
which internally calls `span.text()` on child spans. That `text()` succeeds only if the child
spans are `fltk._native.Span` instances carrying source — a `terminalsrc.Span` without source
raises `ValueError` in `text_or_raise()`. So the test implicitly exercises the parse-path
source-bearing span requirement. Additionally, `TestCrossBackendDualShapeDispatch` instantiates
a Rust-backend parse tree (`_rust_cst_grammar`) and dispatches `case proto_cst.Span.kind:` against
Span children, which would fail dispatch if child spans were `terminalsrc.Span`.

What's missing: no single test directly does:
```python
result = parse_with_rust_backend(...)
assert isinstance(result.cst.span, fltk._native.Span)
assert result.cst.span.text() == expected_text
```

This explicit assertion would isolate regressions faster if the parse path silently falls back to
sourceless spans (which would make `text()` return `None`, not raise). The current tests catch
"no source at all" (via `fltk2gsm` raising) but not "source silently dropped" (where `text()`
returns `None` and the comparison could still pass if `python_gsm == rust_gsm` holds by other
means). However, `fltk2gsm` reads `span.text()` on *child* spans for identifier/literal text
extraction and compares the output to the Python-backend GSM — so if `text()` returned `None`
the produced GSM would differ and the assertion would fail. In practice the coverage chain is
tight enough that the gap is unlikely to pass a broken implementation.

**Finding test-1** (minor, records the gap for future regression isolation):

- ID: test-1
- File: `tests/test_clean_protocol_consumer_api.py` or `tests/test_phase4_rust_fixture.py`
- What: No test directly asserts `isinstance(node.span, fltk._native.Span)` after a live
  Rust-backend parse, nor asserts `node.span.text() == expected_string` for a known-text parse.
  The coverage is indirect: `fltk2gsm_behavioral_equivalence` fails if child spans lack source,
  but a regression where `node.span` (the node-level span, as opposed to child spans) silently
  loses source would not be caught by any current test.
- Consequence: A parse-path regression that sets `node.span` to a sourceless `fltk._native.Span`
  (start/end correct, source dropped) would not be caught. `node.span.text()` would return `None`,
  `span.start` and `span.end` would still be correct, and `fltk2gsm` (which reads *child* spans,
  not node spans) would not exercise the node-level span's text. The §4 item 6 literal requirement
  is "node.span.text() returns the spanned source."
- Fix: Add one test in `TestSpanSourcePreservation` (or `TestAC7BothBackends`) that:
  1. Parses a known short string with the Rust backend.
  2. Asserts `isinstance(result.cst.span, fltk._native.Span)`.
  3. Asserts `result.cst.span.text() == expected_text` (or is not None for the root span).

---

## §4 item 7 — fltk2gsm under both backends

**Present and solid.** `test_fltk2gsm_behavioral_equivalence` (after xfail removal) runs both
backends and asserts `python_gsm == rust_gsm`. The both-backend `text()` path is exercised for
child spans throughout `fltk2gsm`. Test name is descriptive; assertion is meaningful.

---

## §4 item 8 — Protocol additive-widening (pyright)

**Present and solid.** Two test files each contribute a fixture + pyright runner:

- `fltk/fegen/test_cst_protocol.py`: `test_python_backend_consumer_still_type_checks` (writes
  a fixture using `terminalsrc.Span` with `typing.cast`; asserts zero pyright errors) and
  `test_rust_backend_span_satisfies_widened_protocol` (writes a fixture using `fltk._native.Span`).
- `tests/test_clean_protocol_consumer_api.py`: `test_python_backend_consumer_pyright_clean`
  (concrete Python-CST node span assignment + typed helper; asserts zero pyright errors).

The `test_cst_protocol.py` fixtures use `typing.cast` throughout rather than direct assignment
— this means pyright sees the cast's declared type, not the actual union. The consumer fixture
tests the consumer's _annotation side_, not whether pyright rejects an uncast assignment of the
widened union to `terminalsrc.Span`. That said, the acceptance criterion (existing consumer code
type-checks unedited) is satisfied because real consumer code would also cast or annotate.

The `test_clean_protocol_consumer_api.py` fixture does a direct `node.span = s` (where `s:
terminalsrc.Span`) — this tests the concrete CST setter more directly.

**Finding test-2** (minor, quality):

- ID: test-2
- File: `fltk/fegen/test_cst_protocol.py`, `_PYTHON_BACKEND_CONSUMER_FIXTURE` (lines ~490-515)
- What: The `process_node` function annotates `return _t.Span` but immediately does
  `span: _t.Span = typing.cast(_t.Span, node.span)`. This mimics one usage pattern but does not
  exercise the case where a Python-backend consumer passes `node.span` (now typed as
  `terminalsrc.Span | fltk._native.Span`) directly to a function expecting `terminalsrc.Span`
  _without_ a cast. The widening makes `node.span` a union; pyright would reject passing it to
  a `terminalsrc.Span`-annotated parameter without narrowing/cast. The fixture bypasses this by
  using `cast` everywhere, so the test verifies the consumer's _helper annotations_ survive but
  not that pyright accepts the _call site_ without annotation changes.
- Consequence: A downstream consumer who writes `accept_span(node.span)` without a cast _would_
  get a pyright error after widening (because the union is not assignable to `terminalsrc.Span`).
  The test does not catch whether this is actually user-visible annotation churn. The ADR §2.7
  claims "existing Python-backend consumers' type-checks must pass unedited" — the fixture
  sidesteps this with casts rather than proving unedited code still type-checks.
- Fix: Add a fixture function that calls `accept_python_span(node.span)` without a cast (using
  `node: cstp.Grammar` where the protocol types `span` as the widened union). If that fails
  pyright, the widening is not fully backward-compatible and the acceptance criterion needs to be
  re-evaluated. The test should assert it either passes (proving backward compat) or document
  explicitly that a cast is required (making the annotation-churn consequence explicit).

---

## §4 item 9 — Cross-backend behavioral equivalence

**Present and solid.** `tests/test_phase4_rust_fixture.py::TestAC7BothBackends` is parameterized
over `python` and `rust` backends: construction, span read/write, label equality/hash, isinstance
dispatch, children list protocol, full parse roundtrip. `TestCrossBackendDualShapeDispatch` covers
`.kind` cross-backend narrowing (Shape 1 and Shape 2 against both backends). `repr` is correctly
excluded per the design. Test names describe behavior; assertions are substantive.

---

## Child-identity relaxation (`is` → `==`)

**Correct and well-documented.** All six changed `is` → `==` assertions in
`test_phase4_rust_fixture.py` carry `TODO(rust-cst-child-node-identity)` comments explaining the
behavioral change. The `test_ac4_children_extend` rewrite (from `a.children.extend(b.children)`
to `a.extend_children(b)`) is substantively correct and the comment explains _why_ the old form
was wrong for the Rust backend.

---

## Summary

Two findings. Neither is blocking.

- **test-1** (moderate): No explicit post-parse `isinstance(node.span, fltk._native.Span)` +
  `span.text()` value assertion — node-level span source-preservation after a live parse is only
  verified indirectly via `fltk2gsm`.
- **test-2** (minor): The §4 item 8 pyright fixtures use `typing.cast` everywhere, avoiding the
  question of whether a call-site `accept_fn(node.span)` (typed `terminalsrc.Span`) fails pyright
  after widening — the key backward-compatibility claim is not directly falsified.
