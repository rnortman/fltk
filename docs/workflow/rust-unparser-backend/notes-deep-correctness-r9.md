# Deep correctness review — batch 9 (PyO3 Doc exposure, .pyi stub, .fltkfmt fixture)

Commit reviewed: bb96d0e78ae563c4cbad898225c16be02b4baba5 (base 90ffae8c)

No findings.

## Scope checked
- `fltk/unparse/gsm2unparser_rs.py`: new `generate_pyi()`; PyDoc pyclass + per-rule
  additive `unparse_{rule}_doc` emission in `_gen_python_bindings`.
- `fltk/fegen/genparser.py`: `--protocol-module` / `--pyi-output` wiring + ordering.
- `fltk/fegen/test_data/rust_parser_fixture.fltkfmt` (new) and the regenerated
  `tests/rust_parser_fixture/src/unparser.rs`.
- Tests in `test_genparser.py` and `tests/test_rust_unparser_generator.py`.

## Verifications performed (all clean)
- No generation drift: re-ran `gen-rust-unparser --format-config ...rust_parser_fixture.fltkfmt`;
  committed `unparser.rs` is byte-identical to fresh generator output.
- Rust emission compiles: `cargo clippy --manifest-path tests/rust_parser_fixture/Cargo.toml
  --features python -- -D warnings` passes (PyDoc, `unsendable`, doc methods, registrar).
- New generator + CLI tests pass (18 tests).
- Resolve/render boundary: `Renderer::render` panics on `AfterSpec/BeforeSpec/SeparatorSpec/Join`
  (render.rs:188). The `_doc` method stores `resolve_spacing_specs(r.accumulator.doc())` (the
  *resolved* doc), so `PyDoc::render` never reaches that panic. Storing the unresolved doc would
  have been a bug; it does not.
- Pipeline parity of the additive path: `unparse_x_doc(node).render(w,i)` runs unparse→resolve
  (in `_doc`) then render (in `PyDoc::render`) with the same `RendererConfig` as the string
  method `unparse_x(node,w,i)`, so the two produce identical strings. Both call the same
  `self.inner.unparse_x`; the doc handle is rendered by borrow (`&self.resolved`), so multi-width
  rendering does not mutate/consume it.
- `resolve_spacing_specs(doc: Doc)` takes Doc by value (resolve.rs:39); both string and doc
  methods pass `r.accumulator.doc()` by value — consistent, no `&` mismatch.

## .pyi vs actual generated Python surface (matches)
- `generate_pyi` and `_gen_python_bindings` both iterate the same trivia-processed
  `self._grammar.rules` and use `self._class_name(rule.name)`, so method set and class names
  agree, including the synthetic `_trivia` rule (`unparse__trivia` / `unparse__trivia_doc`,
  `_proto.Trivia`).
- Stub `Unparser.__init__(self)->None`, `unparse_{rule}(self, node:_proto.CN, max_width:int=...,
  indent_width:int=...)->Optional[str]`, `unparse_{rule}_doc(self, node:_proto.CN)->Optional[Doc]`,
  `Doc.render(self, max_width:int=..., indent_width:int=...)->str`, `Doc.__repr__(self)->str`
  each map 1:1 to the emitted PyO3 `#[pyclass(name="Unparser")]` / `#[pyclass(name="Doc")]`
  surface (incl. defaulted-vs-positional arg shapes).
- `node` is typed `_proto.{ClassName}` exactly as the CST `.pyi` does, so a Rust-CST node
  (passed at runtime as `PyRef<cst::Py{ClassName}>`) type-checks against the structural protocol
  without a cast. The exposed `Doc` class and `unparse_*_doc` methods are an intended, user-blessed
  additive divergence from the Python backend (design OQ2), not an accidental parity break; the
  stub describes the Rust surface, which it does faithfully.

## Non-issues considered and dismissed
- Grammar rule literally named `doc`: stub-local document `class Doc` and rule class `_proto.Doc`
  are distinct namespaces; at runtime the CST `Doc` and unparser `Doc` live in separate
  submodules. No collision.
- Empty-model rule: `generate_pyi` mirrors `generate()`'s direct rule iteration (both reference
  `cst::Py{CN}` / `_proto.{CN}`); behavior is identical to the pre-existing `.rs` path, not a new
  divergence.
- Deep-tree recursion in derived `Debug` used by `PyDoc.__repr__`: documented deferred hardening
  (design §3 / OQ1), off the happy path.
