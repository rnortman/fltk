Concise. Precise. Complete. Audience: smart LLM/human. No padding.

Commit reviewed: 767315f (base: 6fd32e7)
Committed work assessed: §2.1 (fltk-cst-core split), §2.2 (native span field), §2.3 (native children Vec + child enum), §2.4 (native equality/repr), §2.5 partial (gsm2parser extend_children fix), §2.5 prerequisite (backend-with-source-signature).
Known-not-started and out of scope: §2.5 source-bearing spans on parse path, §2.6, §2.7, §2.8.

---

## test-1 — Pure-Rust GIL-free acceptance test (design §4 item 1) entirely absent

File/area: `tests/rust_cst_fixture/src/lib.rs`, `crates/fltk-cst-core/src/span.rs` — no `#[cfg(test)]` block in either or any Rust source file in the repo.

What's wrong: Design §4 item 1 is the primary acceptance test for the native-state requirement: "construct a node subtree with native spans and `Box`-owned child nodes, walk it, read `span.start()/end()`, compare two equal subtrees and two differing subtrees — *without* `Python::with_gil` / interpreter init." Requirements §"Native node state" second bullet makes this an acceptance criterion. The fixture crate (`tests/rust_cst_fixture/`) is explicitly called out in the design as the home for this test. Zero `#[cfg(test)]` or `#[test]` items exist anywhere in the production or fixture Rust sources.

Consequence: The core deliverable — that native node state (§2.3 `Box<ChildNode>` + §2.2 `Span` field) enables GIL-free traversal — is entirely unverified at the Rust level. All Python-level tests exercise these types through pyo3 (which holds the GIL), so a regression that re-introduces a GIL dependency inside the native traversal logic would not be caught. The acceptance criterion is unmet by test.

Fix: Add a `#[cfg(test)]` module to `tests/rust_cst_fixture/src/cst.rs` (or a separate `tests/rust_cst_fixture/tests/pure_rust.rs`) that: (a) constructs `Span::new_sourceless` and `Span::new_with_source` via the `fltk-cst-core` public API, (b) constructs an `Identifier` with `span` and a child `IdentifierChild::Span(span)`, (c) reads `node.span.start()` and `node.span.end()`, (d) asserts two identical subtrees compare equal via `PartialEq`, (e) asserts a modified subtree compares unequal. No `Python::with_gil` call anywhere in the test. Run with `cargo test` in the fixture crate.

---

## test-2 — `extend_children` emission not tested at generator level

File/area: `tests/test_gsm2tree_rs.py` — no test for `fn extend_children` in generated source.

What's wrong: `gsm2tree_rs.py` gained `_generic_extend_children` (increment 3/4), which emits `fn extend_children(&mut self, other: PyRef<'_, ClassName>)` for every node class. This method is now the only safe mutation path for inline-to-parent children in the Rust backend (design §2.3 parser-generator note; §2.5 partial). `TestNodeStructure` and `TestNoPyObjectAudit` check span fields, child enums, and Vec storage, but no test asserts that `fn extend_children` is present in the generated source, nor that `extend_children` is registered in the `register_classes` block (it does not need to be, but the emission of the method itself is unverified at the generator level).

Consequence: A regression in `_generic_extend_children` (e.g. the method silently dropped from emission, or emitted with wrong signature) would not be caught by the generator-source tests. The Python-level tests in `test_rust_cst_poc.py::TestChildrenListSemantics::test_cross_node_children_extend_via_method` exercise `extend_name` (label-specific), not `extend_children`. The compiled-artifact tests (phase4 / AC8) catch it end-to-end but only when the fixture is built — slow and indirect.

Fix: Add to `TestNodeStructure` in `tests/test_gsm2tree_rs.py`:
```python
def test_extend_children_emitted(self, poc_source: str) -> None:
    """§2.3/§2.5: extend_children method is emitted for each node class."""
    assert "fn extend_children(" in poc_source
    # Verify the specific signature form for at least one class.
    assert "fn extend_children(&mut self, other: PyRef<'_, Identifier>) -> PyResult<()>" in poc_source
```

---

## test-3 — `gsm2parser.py` extend_children call-site change not directly tested

File/area: `fltk/fegen/test_genparser.py` — no test that the generated parser emits `extend_children` calls rather than `.children.extend(...)`.

What's wrong: The most failure-prone part of this increment is `gsm2parser.py:495-502,712-715` — the two inline-to-parent child-extension sites that were changed from getter-mutation to `extend_children` method calls. If this emission is wrong (reverted, or emitted conditionally for only one of the two sites), the Rust backend silently loses children on inline parse paths. There is no generator-level test asserting that the generated parser source contains `extend_children` calls at these sites.

Consequence: A regression at either gsm2parser emit site (the loop path at line 497 or the alternatives path at line 712) would produce a Rust-backend parser that silently returns nodes with empty/incomplete children. The AC8 tests (`test_phase4_fegen_rust_backend.py`) would likely catch this — but only when `fegen_rust_cst` is built (optional artifact), and only for the fegen grammar. A grammar with `+` quantifiers on inline terms (the loop path) and a grammar with alternatives + inline terms (the alternatives path) need separate coverage to identify which site regressed.

Fix: Add to `fltk/fegen/test_genparser.py` a test that calls `gsm2parser.ParserGenerator` on a grammar with (a) a repeating inline term (`term+`) and (b) an alternatives rule with an inline sub-rule, then asserts the generated parser source contains `extend_children(other=` (not `children.extend(`). This is a source-text grep test, matching the style of the existing genparser tests.

---

## test-4 — `test_span.py::test_with_source_text` not updated for new `SourceText` form

File/area: `tests/test_span.py:61-63`.

What's wrong:
```python
def test_with_source_text():
    s = Span.with_source(6, 11, "hello world")
    assert s.text() == "world"
```
This tests only the legacy `str` form of `with_source`. The new `SourceText` wrapper form (`Span.with_source(6, 11, SourceText("hello world"))`) — which is the portable form mandated by the design and tested in `test_span_protocol.py::TestSourceTextAndPortableWithSource::test_portable_with_source_python_backend` — is absent from `test_span.py`, the dedicated test file for the Python-backend `terminalsrc.Span`. The coverage for the new form lives only in the cross-backend protocol test.

Consequence: `test_span.py` is the canonical unit test for `terminalsrc.Span`. A reviewer checking `terminalsrc.py`'s `with_source` would look there and find only the old API tested. The `SourceText` branch in `with_source` (the `isinstance(source, SourceText)` path at `terminalsrc.py:134-135`) has no test in its home file. Minor: the coverage gap is filled elsewhere, so the behavior is verified — but the test locality is wrong for a dedicated unit-test file.

Fix: Add to `tests/test_span.py`:
```python
def test_with_source_text_object():
    from fltk.fegen.pyrt.terminalsrc import SourceText
    st = SourceText("hello world")
    s = Span.with_source(6, 11, st)
    assert s.text() == "world"
```
