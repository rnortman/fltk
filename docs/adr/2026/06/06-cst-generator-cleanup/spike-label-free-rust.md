# Spike: how the Rust CST backend handles a zero-label node

Empirical + code-read spike. No git-tracked file was modified; all generation
and compilation happened in a scratch dir (`/tmp/labelfree.MCvaDI/`).

## Question

For a rule with ZERO labels (only `$`-disposition literals/regexes, e.g.
`foo := $"x" , $"y";`), the Python *concrete* backend emits a dead, memberless
`Label(enum.Enum)` and `children: list[tuple[Optional[Label], T]]`; the Protocol
uses `tuple[None, T]` and no `Label`. How does the **Rust** backend
(`fltk/fegen/gsm2tree_rs.py`, `RustCstGenerator`) handle the same node?

## Summary of findings

- The Rust backend **does not** emit a zero-variant enum for label-free nodes.
  Emission of the per-rule `<Class>_Label` enum is **guarded** on the rule
  having ≥1 label; for zero labels it emits nothing.
- The generated Rust **compiles cleanly** (`cargo check` exits 0, no warnings).
- The Rust backend **sidesteps the empty-enum problem entirely** by storing
  labels as opaque `Option<PyObject>` in the generic methods, never referencing
  the (non-existent) enum type for a zero-label rule. The label enum is only
  ever named by the *per-label* methods, which themselves are only emitted when
  labels exist.
- Runtime label surface for a zero-label node: the label slot in each children
  tuple is Python `None` — matching the **Protocol's** `tuple[None, T]`, not the
  Python concrete's `Optional[Label]`.

## 1. Code-read: `fltk/fegen/gsm2tree_rs.py`

### The label enum is guarded on ≥1 label (NOT unconditional)

`_label_enum_block` returns the empty string when the rule has no labels — the
guard is explicit and even documents the rustc constraint:

- `gsm2tree_rs.py:228-235`

```python
def _label_enum_block(self, class_name: str, labels: list[str]) -> str:
    """...
    For rules with no labels, emits nothing (Rust enums cannot have zero variants).
    ...
    """
    if not labels:
        return ""
```

So a zero-label rule produces **no** `<Class>_Label` enum at all. There is no
zero-variant enum emitted.

### Where the label is stored / how the children tuple is built

The node struct holds only `span: PyObject` and `children: Py<PyList>`; the label
is never a struct field and is never typed as the enum.

- struct: `gsm2tree_rs.py:284-300` (emits `pub struct <Class> { span: PyObject, children: Py<PyList> }`)

The generic `append` / `extend` carry the label as an **opaque
`Option<PyObject>`**, defaulting to `py.None()`; they never name the enum type:

- `_generic_append` — `gsm2tree_rs.py:371-381`
  (`label: Option<PyObject>`, `let label_val = label.unwrap_or_else(|| py.None());`)
- `_generic_extend` — `gsm2tree_rs.py:383-402` (same opaque pattern)
- `_generic_child` — `gsm2tree_rs.py:404-417` (no label reference at all)

### The enum type is referenced only by per-label methods / the Label classattr

The only places the `<Class>_Label` enum name appears are:

- `Label` classattr — `_label_classattr`, `gsm2tree_rs.py:360-369`, emitted only
  under the `if labels:` guard at `gsm2tree_rs.py:309-310`.
- per-label methods (`append_<l>`, `extend_<l>`, `children_<l>`, `child_<l>`,
  `maybe_<l>`) — `_per_label_methods`, `gsm2tree_rs.py:419-542`, called in a
  `for label in labels:` loop at `gsm2tree_rs.py:316-317`. Zero labels → zero
  per-label methods → the enum name is never emitted.
- registration — `_register_classes_fn`, `gsm2tree_rs.py:585-598`, registers the
  enum class only under `if labels:` (`gsm2tree_rs.py:591-593`).

Conclusion: for a zero-label rule the enum type is **never named anywhere**, so
its absence cannot cause a missing-symbol error.

## 2. Generated Rust for the zero-label `Foo` node

Scratch grammar (`/tmp/labelfree.MCvaDI/labelfree.fltkg`):

```
foo := $"x" , $"y" ;
```

Generated with the pure-Python path:

```
uv run python -m fltk.fegen.genparser gen-rust-cst labelfree.fltkg cst.rs   # exit 0
```

(The grammar also auto-acquires a `trivia` rule with a `content` label, which
provides a *labeled* comparison node in the same file — see §4.)

### Label enum for `Foo`

**None.** A grep of the generated file for `Foo_Label` / `append_*` / `child_*` /
`maybe_*` / a `Label` classattr on `Foo` returns nothing. The only occurrence of
`Foo` outside the struct/`kind`/`__eq__`/`__repr__`/`NodeKind` is the `__repr__`
format string. By contrast, the labeled `Trivia` rule *does* get a
`Trivia_Label` enum, a `Label` classattr, and `append_content` / `children_content`
/ `child_content` / `maybe_content` methods (cst.rs:162-..., 240, 279-...).

### Struct + generic methods for `Foo` (verbatim, cst.rs:62-128)

```rust
#[pyclass]
pub struct Foo {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Foo {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<PyObject>) -> PyResult<Self> {
        let span_obj = match span {
            Some(s) => s,
            None => UNKNOWN_SPAN_CACHE
                .get_or_try_init(py, || -> PyResult<PyObject> {
                    Ok(py.import("fltk._native")?.getattr("UnknownSpan")?.unbind())
                })?
                .clone_ref(py),
        };
        Ok(Foo {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[getter]
    fn kind(&self) -> NodeKind {
        NodeKind::Foo
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&self, py: Python<'_>, child: PyObject, label: Option<PyObject>) -> PyResult<()> {
        let label_val = label.unwrap_or_else(|| py.None());
        let tup = PyTuple::new(py, [label_val, child])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &self,
        py: Python<'_>,
        children: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        let label_val = label.unwrap_or_else(|| py.None());
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label_val.clone_ref(py).into_bound(py), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let list = self.children.bind(py);
        let n = list.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        Ok(list.get_item(0)?.unbind())
    }
    // ... __eq__, __hash__, __repr__ (no label reference)
}
```

No `Label` classattr, no per-label methods. Note there is also **no** `NodeKind`
problem: `NodeKind` is a separate, fully-populated enum (one variant per rule,
cst.rs:17-30) and is unrelated to the per-rule label enum.

**Confirmed: no zero-variant Rust enum is emitted.**

## 3. Compile check

A throwaway cdylib crate was assembled in the scratch dir mirroring
`tests/rust_cst_fixture/Cargo.toml` (pyo3 0.23, abi3-py310), with the generated
`cst.rs` and a one-line `lib.rs` calling `cst::register_classes`.

```
cargo check --manifest-path /tmp/labelfree.MCvaDI/crate/Cargo.toml
...
    Checking phase4-roundtrip-cst v0.1.0 (/tmp/labelfree.MCvaDI/crate)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 4.76s
CARGO_EXIT=0
```

**It compiles — exit 0, zero warnings.** This is the expected result given §1:
because the empty enum is never emitted and never referenced for a zero-label
rule, there is nothing uninhabited to construct or match on. The hypothetical
"uninhabited type" hazard does not arise because the type does not exist.

## 4. Cross-backend consistency / runtime label surface

- The Rust node stores labels as opaque Python objects in the children tuples.
  For a zero-label rule the parser/builder only ever calls the **generic**
  `append`/`extend` with no `label` argument, so `label_val` becomes `py.None()`
  (`gsm2tree_rs.py:376`, `:390`). The label slot in every children tuple is
  therefore Python **`None`**.
- This matches the **Protocol** surface (`tuple[None, T]`, no `Label` class). It
  does **not** reproduce the Python *concrete* backend's dead `Optional[Label]`
  surface — there is no Rust `Foo.Label` attribute at all (no `Label` classattr
  is emitted for `Foo`), so a downstream consumer cannot reference a vestigial
  `Foo.Label` on the Rust class the way they could on the Python concrete class.
- Because labels are opaque `PyObject`s and the enum is only used as a *producer*
  of label values inside per-label methods (which don't exist here), the Rust
  backend **does not have the empty-enum problem at all** — it sidesteps it
  structurally, not by special-casing rustc.

## 5. Definitive answers

(a) **Zero-variant enum for label-free nodes?** No. `_label_enum_block` returns
    `""` when `not labels` (`gsm2tree_rs.py:234-235`); no enum, no `Label`
    classattr, no per-label methods, no registration entry are emitted.

(b) **Does it compile?** Yes. `cargo check` on a fixture-equivalent crate
    containing the generated `cst.rs` exits 0 with no warnings.

(c) **Runtime / PyO3 label surface match?** Matches the **Protocol's** `None`.
    The label slot in the children tuples is Python `None`, and no `Label` class
    is exposed on the node — i.e. it is *closer to the Protocol than to the
    Python concrete backend*. It does **not** reproduce the concrete backend's
    dead `Optional[Label]` / vestigial memberless `Label` enum.

## Implication for the divergence being triaged

The dead-memberless-`Label` artifact is a **Python-concrete-backend-only**
phenomenon. The Rust backend already does the "right" thing (no vestigial label
machinery for label-free rules) and agrees with the Protocol. So any cleanup of
the Python concrete backend's dead `Label` should be measured against the Rust
backend + Protocol behavior as the reference, not the other way around — the
Rust generator needs no change here.

### Key file references

- Generator: `/home/rnortman/src/fltk/fltk/fegen/gsm2tree_rs.py`
  - guard: lines 234-235; struct: 284-300; generic append/extend/child: 371-417;
    Label classattr guard: 309-310 (`_label_classattr` 360-369);
    per-label loop/methods: 316-317 / 419-542; registration guard: 590-594.
- CLI: `/home/rnortman/src/fltk/fltk/fegen/genparser.py` `gen-rust-cst` 264-287.
- Scratch artifacts (not git-tracked): `/tmp/labelfree.MCvaDI/labelfree.fltkg`,
  `/tmp/labelfree.MCvaDI/cst.rs`, `/tmp/labelfree.MCvaDI/crate/`.
