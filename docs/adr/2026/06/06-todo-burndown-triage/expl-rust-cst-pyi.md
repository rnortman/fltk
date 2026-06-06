# TODO(rust-cst-pyi) — Adversarial Verification

Date: 2026-06-06. Concise. No prescriptions.

---

## 1. Claim: `gen_rust_cst` exists in `genparser.py` as cited

**Confirmed.** `fltk/fegen/genparser.py:264-287`:

```python
@app.command(name="gen-rust-cst")
def gen_rust_cst(
    grammar_file: Annotated[Path, typer.Argument(...)],
    output_file: Annotated[Path, typer.Argument(...)],
) -> None:
    # TODO(rust-cst-pyi): also emit a .pyi stub for the generated Rust extension here,
    # derived from the same GSM, so pyright can verify the PyO3 surface satisfies CstModule.
    grammar = _parse_grammar_raw(grammar_file)
    src = gsm2tree_rs.RustCstGenerator(grammar).generate()
    output_file.write_text(src)
```

The `TODO(rust-cst-pyi)` comment is at line 279. The command name on the CLI is `gen-rust-cst` (hyphenated), matching the TODO claim exactly. The TODO.md entry at line 43-45 cites `genparser.py` (`gen_rust_cst` command) and matches verbatim.

---

## 2. Claim: "boundary cast at the injection site (`plumbing.py`)"

**Partially correct, but the cast location is not a `CstModule` boundary cast — it is a `cst.Grammar` cast on `result.result`.**

`fltk/plumbing.py` contains `Cst2Gsm` at two call sites:

- Python path, line 146-149:
  ```python
  cst2gsm = fltk2gsm.Cst2Gsm(terminals.terminals)
  return cst2gsm.visit_grammar(cast("cst.Grammar", result.result))
  ```
- Rust path, line 174-177:
  ```python
  cst2gsm = fltk2gsm.Cst2Gsm(terminals.terminals)
  return cst2gsm.visit_grammar(cast("cst.Grammar", result.result))
  ```

The cast in both paths is `cast("cst.Grammar", result.result)` where `result.result` is statically `Any` (from `ParseResult`). This cast satisfies `visit_grammar`'s annotation `grammar: cst.Grammar` (where `cst` is `fltk_cst_protocol`). There is **no** explicit `cast(CstModule, ...)` anywhere in `plumbing.py`; the term "boundary cast" in the TODO/ADR refers to the fact that the Rust module is loaded dynamically via `importlib.import_module` (`plumbing.py:99`) and its classes are accessed as `Any`, then attributed via `setattr` (`plumbing.py:251`). The Rust CST module itself is typed `types.ModuleType`, not `CstModule`.

The "boundary cast" in `fltk2gsm.py` `_DEFAULT_CST` described in `test_cst_protocol.py:371` — confirmed there is **no** `_DEFAULT_CST` symbol in `fltk2gsm.py` (grep returned no output). `Cst2Gsm.__init__` at line 11 takes only `terminals`; it has no `cst=` parameter:

```python
class Cst2Gsm:
    def __init__(self, terminals):
        self.terminals = terminals
```

The ADR requirements at line 56 (`requirements.md`) describe an injection `Cst2Gsm(..., cst=pr.cst_module)` as a confirmed fact, but the actual `fltk2gsm.py:10-12` has no such parameter. The ADR text overstates the current implementation — the DI parameter (`cst=`) was apparently designed but not implemented; `Cst2Gsm` has no `cst` parameter in the shipped code. The `visit_*` methods use `cst.Items.Label.NO_WS` etc. directly from the `fltk_cst_protocol` import at line 6, not from an injected module.

---

## 3. ADR `05-cst-type-annotations-regression` B3a/B4 framing

ADR found at `docs/adr/2026/06/05-cst-type-annotations-regression/`. The README (`README.md`) is the accepted decision; `requirements.md` contains the formal B-numbered requirements.

**B3a** (`requirements.md:54-58`): Confirms Rust CST extension exists and is "injected into `Cst2Gsm` on the opt-in path (`plumbing.parse_grammar(..., rust_fegen_cst_module=...)` → `Cst2Gsm(..., cst=pr.cst_module)`)". The injection site description (`Cst2Gsm(..., cst=pr.cst_module)`) is **not reflected in the actual code** — `fltk2gsm.Cst2Gsm.__init__` accepts no `cst=` parameter. The actual Rust path in `plumbing.py:174` simply constructs `Cst2Gsm(terminals.terminals)` and calls `visit_grammar` with a cast, exactly as the Python path does. B3a's other claim — "no stub/protocol generator for the Rust CST surface" — is confirmed: no `.pyi` files in the project tree (only in `.venv`), and `gsm2tree_rs.py:35-` `RustCstGenerator` emits only `.rs` source.

**B4** (`requirements.md:60-67`): Scopes Rust-backend verification as deferred unless Rust stub generation is in scope this cycle. Decision: it was deferred. The shared `CstModule` Protocol (`fltk/fegen/fltk_cst_protocol.py:750`) covers B1/B6 for the Python path; B4 for the Rust path is explicitly deferred per B3a, recorded as `TODO(rust-cst-pyi)`.

The `test_cst_protocol.py` T2a test (`test_member_access_fixture_zero_errors`, line 325) verifies the Python backend against `CstModule` via pyright in a subprocess fixture. There is no equivalent T4-or-later test for the Rust backend's `.so` surface.

---

## 4. `CstModule` Protocol — actual shape

`fltk/fegen/fltk_cst_protocol.py:750-795`:

```python
class CstModule(typing.Protocol):
    @property
    def Grammar(self) -> type[Grammar]: ...
    @property
    def Rule(self) -> type[Rule]: ...
    # ... one @property per grammar rule (13 total for fegen grammar) ...
    @property
    def Span(self) -> type[Span]: ...
```

`CstModule` is generated by `gsm2tree.CstGenerator.gen_cst_module_protocol` (`gsm2tree.py:633-645`) and committed as `fltk_cst_protocol.py`. It is not re-generated at runtime; it is a static committed artifact for the fegen grammar specifically.

---

## 5. No `.pyi` generation today

`gsm2tree_rs.RustCstGenerator` (`gsm2tree_rs.py:35`) generates only `.rs` source via `generate()`. No `.pyi` emission path exists anywhere in the generator stack. The `gen_rust_cst` command at `genparser.py:264` calls `RustCstGenerator(grammar).generate()` and writes the `.rs` string; no stub file is produced.

---

## 6. Feasibility and scope

The work described by the TODO is:

1. **`.pyi` emission**: Add a `gen_py_stub()` or equivalent method to `RustCstGenerator` (or a new class) that traverses the same GSM and emits `.pyi` text mirroring the PyO3 `#[pyclass]` surface. This is parallel to `gen_py_module()` in `CstGenerator` (`gsm2tree.py`). Input: GSM (already available in `gen_rust_cst`). Output: `.pyi` string. The GSM already carries all node names, label names, accessor method names, and span field presence — all the information needed.

2. **B4 Rust-backend verification**: A pytest test that (a) compiles and imports a generated Rust CST extension (requires `maturin develop` or equivalent — a build step, not just Python), then (b) runs pyright over a fixture that assigns the imported module to `CstModule` without a `cast`. This is larger than item 1 alone; the compile step requires the Rust toolchain and a grammar with a compiled extension available under test.

The `.pyi` emitter (item 1 in isolation) is a moderate-size addition: ~100–200 lines of Python generating `class Foo:\n    span: ...\n    ...` for each node. The B4 harness (item 2) requires deciding whether tests compile Rust on-the-fly or rely on the pre-built `fltk._native` extension, which is grammar-specific. No cross-grammar B4 test can reuse `fltk._native` directly since it is the fegen-specific Rust extension, not a consumer's extension.

The TODO as scoped is accurate: the `.pyi`'s function is verifying the cast in `plumbing.py` (the `cast("cst.Grammar", result.result)` on the Rust path) does not mask a real surface gap. Given `Cst2Gsm` has no `cst=` injection parameter in the actual code, the surface gap risk is narrower than the ADR text implies — the Rust nodes are passed directly to `visit_grammar` under a protocol cast, not through an injected module attribute.

---

## Open factual questions

- `fltk2gsm.py` has no `cst=` parameter on `Cst2Gsm.__init__` and no `_DEFAULT_CST` binding, contradicting ADR B3a's parenthetical `Cst2Gsm(..., cst=pr.cst_module)`. Whether this DI wiring was planned but never implemented, or was implemented and then removed, is not determinable from the current code or commit messages alone.
- `test_cst_protocol.py:371` references "the cast in fltk2gsm.py `_DEFAULT_CST`" — this symbol does not exist in `fltk2gsm.py`. The test comment may be stale or refer to a planned symbol.
