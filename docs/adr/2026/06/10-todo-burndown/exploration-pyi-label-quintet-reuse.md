# Exploration: pyi-label-quintet-reuse

Concise. Precise. No fluff.

---

## How many copies of the quintet exist?

Three distinct implementations emit the per-label accessor quintet. No fourth copy was found.

### Copy 1 — `_emit_label_quintet` in `CstGenerator`

`fltk/fegen/gsm2tree.py:574-621`

A shared helper that takes two callbacks and returns `list[ast.FunctionDef]`. It owns the method-name templates and signature shapes.

```python
def _emit_label_quintet(
    self,
    *,
    labels: list[str],
    annotation_for: Callable[[str], str],
    body_for: Callable[[Literal["append", "extend", "children", "child", "maybe"], str], list[ast.stmt]],
) -> list[ast.FunctionDef]:
```

Called twice: once by `py_class_for_model` (concrete dataclass, `gsm2tree.py:354-360`) and once by `_protocol_class_for_model` (Protocol class, `gsm2tree.py:694-700`). Both pass a different `body_for` callback; `annotation_for` also differs (py vs protocol annotation). The function-name templates (`append_{label}`, etc.) and parameter shapes are encoded exactly once here.

Per-method signatures emitted:
- `append_{label}(self, child: {lann}) -> None`
- `extend_{label}(self, children: typing.Iterable[{lann}]) -> None`
- `children_{label}(self) -> typing.Iterator[{lann}]`
- `child_{label}(self) -> {lann}`
- `maybe_{label}(self) -> typing.Optional[{lann}]`

### Copy 2 — `generate_pyi` in `RustCstGenerator`

`fltk/fegen/gsm2tree_rs.py:186-195`

String-building loop, called once per label:

```python
for label in labels:
    lann = self._pyi_annotation_for_model_types(model.labels[label], class_name=f"{class_name}.{label}")
    lines.append(f"    def append_{label}(self, child: {lann}) -> None: ...")
    lines.append(f"    def extend_{label}(self, children: typing.Iterable[{lann}]) -> None: ...")
    lines.append(f"    def children_{label}(self) -> typing.Iterator[{lann}]: ...")  # stub/runtime diverge
    lines.append(f"    def child_{label}(self) -> {lann}: ...")
    lines.append(f"    def maybe_{label}(self) -> typing.Optional[{lann}]: ...")
```

The method names, parameter names (`child`, `children`), and return-type forms are re-specified independently as f-string literals. The TODO comment at `gsm2tree_rs.py:183` explicitly flags this: `# TODO(pyi-label-quintet-reuse)`.

### Copy 3 — `_per_label_methods` in `RustCstGenerator`

`fltk/fegen/gsm2tree_rs.py:882-987`

Rust string emission. The five method names are re-coded here as Rust `fn` signatures embedded in string lists. This is the Rust *implementation* copy, not a Python signature copy; it is not AST-based and has no shared ancestry with copies 1 or 2. Method names: `append_{label}`, `extend_{label}`, `children_{label}`, `child_{label}`, `maybe_{label}` — identical spelling.

---

## Method-by-method comparison: Copy 2 vs Copy 1

| Method | Copy 1 (`_emit_label_quintet`) | Copy 2 (`generate_pyi`) |
|---|---|---|
| `append_{label}` | `self, child: {lann}` → `None` | `self, child: {lann}` → `None: ...` |
| `extend_{label}` | `self, children: typing.Iterable[{lann}]` → `None` | `self, children: typing.Iterable[{lann}]` → `None: ...` |
| `children_{label}` | `self` → `typing.Iterator[{lann}]` | `self` → `typing.Iterator[{lann}]: ...` |
| `child_{label}` | `self` → `{lann}` | `self` → `{lann}: ...` |
| `maybe_{label}` | `self` → `typing.Optional[{lann}]` | `self` → `typing.Optional[{lann}]: ...` |

The names, parameter names, and return-type forms match exactly. The only structural difference is the annotation source: Copy 1 uses `annotation_for(label)` (which calls `protocol_annotation_for_model_types` or `py_annotation_for_model_types` depending on the caller), while Copy 2 calls `_pyi_annotation_for_model_types` (which calls `protocol_annotation_for_model_types` and then re-qualifies quoted names with `_proto.`). Both ultimately use the same underlying annotation logic from `CstGenerator.protocol_annotation_for_model_types`.

---

## Where the actual annotation logic lives

`CstGenerator.protocol_annotation_for_model_types` at `gsm2tree.py:414-435` is shared by all three Python-facing copies:
- Copy 1 calls it via `annotation_for` callbacks
- Copy 2 calls it via `_pyi_annotation_for_model_types` → `self._py_gen.protocol_annotation_for_model_types`

`_pyi_annotation_for_model_types` at `gsm2tree_rs.py:207-223` is the thin wrapper that converts `'"ClassName"'` → `'_proto.ClassName'` on top of the shared logic.

---

## Is there a natural single source of truth?

The method-name and parameter-shape logic is encoded in `_emit_label_quintet` (Copy 1) as positional knowledge: the five f-strings at `gsm2tree.py:601-619`. Copy 2 (`generate_pyi`) re-encodes the same five f-strings as Python string lines at `gsm2tree_rs.py:188-195`.

A potential single source would be a data table — a list of `(method_template, param_template, return_template)` tuples — consumed by both. The obstacle is the AST vs string boundary: `_emit_label_quintet` calls `pygen.function(...)` to construct `ast.FunctionDef` nodes; `generate_pyi` appends raw strings to `lines`. A shared data table would require `generate_pyi` to be rewritten to construct AST nodes and unparse them, or `_emit_label_quintet` to be split into a name/signature table plus separate AST construction. Neither is structurally complex, but both require crossing the string/AST boundary.

The annotation computation is already shared (via `_pyi_annotation_for_model_types`). What is not shared is the method-name prefixes and the parameter-name keywords (`child` vs `children`).

---

## Is drift loud or silent?

**Partially loud, partially silent.**

### What the conformance tests catch

`tests/test_gsm2tree_rs.py:1166-1202` (`TestGeneratePyiConformance`) runs pyright over a fixture that assigns the emitted `.pyi` module to `cstp.CstModule` (no cast). This checks structural compatibility with the protocol. The protocol's per-label quintet is generated by Copy 1 (`_emit_label_quintet` via `_protocol_class_for_model`). If Copy 2's method names drift from Copy 1's, pyright will report a conformance error — **loud**.

`tests/test_fltk_native_stub.py:184-196` (`TestStubToRuntime.test_stub_members_exist_at_runtime`) checks that every method declared in the committed `.pyi` exists on the runtime Rust module. If Copy 2 adds a method that Copy 3 (Rust) does not implement, this fails at runtime — **loud when the extension is built**.

`tests/test_gsm2tree_rs.py:896-920` (`TestGeneratePyiPerLabelAccessors`) checks presence of all five accessor prefixes in the generated `.pyi` by name-string assertion. These are string tests, not pyright tests, and only cover the PoC grammar's specific label names (`name`, `no_ws`, `ws_allowed`, `ws_required`, `item`).

### What is NOT caught

If a method is **added to Copy 1** (e.g., a sixth `count_{label}` accessor) and the same method is added to Copy 3 (Rust implementation) but Copy 2 (`generate_pyi`) is not updated:
- The committed `.pyi` stub will omit the method
- `test_stub_members_exist_at_runtime` will not flag it (direction: stub → runtime, not runtime → stub for per-class members)
- `test_runtime_classes_in_stub` at `test_fltk_native_stub.py:136-149` checks class-level attributes (module-level `type` objects), not instance methods
- The conformance check will fail if pyright enforces the protocol's new method on the stub — but only if the protocol was already regenerated and committed

**The gap**: if a new method exists in the protocol and the Rust implementation but not in the `.pyi`, `TestStubToRuntime.test_stub_members_exist_at_runtime` does not check in the runtime→stub direction for instance methods (only module-level class names and non-class module attrs are covered). The per-class method coverage in `test_fltk_native_stub.py` goes stub→runtime only. Drift where the runtime has a method the stub omits is **silent** unless pyright conformance catches the missing protocol method.

**Concrete silent scenario**: add `count_{label}` to protocol (Copy 1) and Rust (Copy 3), forget to add it to `generate_pyi` (Copy 2). The conformance test (`_m: cstp.CstModule = fegen_cst`) would fail because `fegen_cst.<Class>` wouldn't have `count_{label}` in its stub (pyright checks the stub, not the runtime for type-checking). This would be caught. But if the protocol is also not regenerated, all three sides drift silently until something regenerates the protocol.

---

## Open factual questions

- Does any test regenerate the protocol on-the-fly and check it against the `.pyi`? (Not found; tests use committed `.pyi` and committed protocol module.)
- Is there a `make regen` or equivalent that regenerates both the protocol and the `.pyi` atomically? (Not examined; `Makefile` not read.)
