# Deep correctness review — r11 (committed .pyi stub + CST protocol module, OQ-3)

Commit reviewed: fabdc5a2ea6f4ca1ecc42386a4a5f40a8e776dd4 (base 0494f3127dd09141e7bc0f0b918862feaf449f46)

No findings.

## What was checked (mandate: does the .pyi actually describe the runtime surface; are annotations correct)

- **Stub-vs-generator drift.** Regenerated the fixture `.pyi` via `RustUnparserGenerator.generate_pyi`
  + `make fix` (ruff check --fix; ruff format). Result is byte-identical to the committed
  `fltk/_stubs/rust_parser_fixture/unparser.pyi`. The committed protocol module
  `tests/rust_parser_fixture_cst_protocol.py` likewise matches `genparser generate` output (only
  formatting differs pre-`make fix`). No staleness.
- **Method-set parity.** `generate_pyi` and `_gen_python_bindings` both iterate `self._grammar.rules`
  (trivia-processed), so each emits exactly `unparse_{rule}` + `unparse_{rule}_doc`. Built extension:
  62 `unparse_*` methods on `Unparser`; committed `.pyi`: 62. Set difference both directions is empty
  (incl. synthetic `unparse__trivia` / `_doc` typed against `_proto.Trivia`).
- **Annotation correctness against the live PyO3 surface** (introspected the compiled extension):
  - `Unparser()` no-arg `#[new]` ⇒ `__init__(self) -> None`. ✓
  - `unparse_{rule}($self, node, max_width=80, indent_width=4) -> PyResult<Option<String>>` ⇒
    `(node: _proto.{CN}, max_width: int = ..., indent_width: int = ...) -> str | None`. Runtime call
    returns `str`/`None`. ✓
  - `unparse_{rule}_doc($self, node) -> PyResult<Option<PyDoc>>`, `PyDoc` is `#[pyclass(name="Doc")]`
    ⇒ `(node: _proto.{CN}) -> Doc | None`. Runtime returns the `Doc` class; no width params. ✓
  - `Doc.render($self, max_width=80, indent_width=4) -> String` ⇒ `(max_width: int = ..., indent_width:
    int = ...) -> str`; `Doc.__repr__ -> str`. ✓ (`usize` → `int` is the correct pyo3 mapping.)
- **Protocol resolution.** Every `_proto.{ClassName}` referenced by the stub (Num … AnchoredWord,
  Trivia) exists as a `typing.Protocol` in the committed protocol module, and class/rule ordering
  matches. `register_classes` registers both `Unparser` and `Doc` into the `unparser` submodule
  (lib.rs), so `rust_parser_fixture.unparser.{Unparser,Doc}` resolve at runtime and in the stub.
- **Gate cleanliness + consumer typing.** Committed `.pyi` passes `ruff check`/`ruff format --check`
  in-project (the `typing.Optional` → `| None` switch removes the unfixable unused-`import typing`
  F401 trap). `tests/test_rust_unparser_pyi.py` (3) and the `generate_pyi` unit tests (7) pass:
  a correct consumer is pyright-clean and passing an `int` where `_proto.Num` is required is a
  `reportArgumentType` error, proving the node param is genuinely constrained (not `Any`).

Logic, control flow, and data flow of the only generator change in scope (`generate_pyi`) are clean
and consistent with the emitted PyO3 bindings.
