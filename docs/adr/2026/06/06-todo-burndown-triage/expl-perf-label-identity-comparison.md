# TODO Triage: `perf-label-identity-comparison`

Concise. Precise. No fluff. Audience: smart LLM/human.

## Claim verbatim (TODO.md:27-29)

> The generated `tup.get_item(0)?.eq(&label_obj)?` pattern in label-accessor methods performs
> an O(children) linear scan with equality comparison per access. Identity comparison (`is`) or
> pre-grouped storage would be O(1). Defer until profiling confirms a bottleneck.
> Location: `fltk/fegen/gsm2tree_rs.py` (template in `_per_label_methods`).

## Code surface

**Generator template** — `fltk/fegen/gsm2tree_rs.py:453-476` (`_per_label_methods`):

```python
# TODO(perf-label-identity-comparison): the generated `tup.get_item(0)?.eq(&label_obj)?`
# below performs an O(children) linear scan with equality comparison per access.
lines.extend([
    f"    fn children_{label}(&self, py: Python<'_>) -> PyResult<Py<PyList>> {{",
    f"        let label_obj = {enum_name}::{rust_variant}.into_pyobject(py)?;",
    "        let result = PyList::empty(py);",
    "        for (idx, item) in self.children.bind(py).iter().enumerate() {",
    "            ...",
    "            if tup.get_item(0)?.eq(&label_obj)? {",
    ...
```

Same pattern appears in `child_{label}` (lines 478-508) and `maybe_{label}` (lines 510-540).

**Generated Rust example** — `src/cst_fegen.rs:234-242`:
```rust
fn children_rule(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
    let label_obj = Grammar_Label::Rule.into_pyobject(py)?;
    let result = PyList::empty(py);
    for (idx, item) in self.children.bind(py).iter().enumerate() {
        ...
        if tup.get_item(0)?.eq(&label_obj)? {
            result.append(tup.get_item(1)?)?;
        }
    }
```

Also confirmed in `src/cst_fegen.rs:250,259,277,286` (other label accessors same rule); same pattern repeats for every label across all rules.

## Is the O(children) scan real?

**Yes.** `self.children.bind(py).iter()` iterates all children. No early termination once label-matched items are found (except in `child_`/`maybe_` which break only on count > 1 after already scanning everything). Each iteration does a tuple unpack and one `.eq()` call.

## What does `.eq()` cost?

`Bound<PyAny>::eq()` calls `rich_compare(CompareOp::Eq)` — PyO3 `any.rs:1114-1120` — which dispatches to Python `__eq__`. The label enum's `__eq__` is overridden via `#[pymethods]` (`_emit_rust_cross_backend_eq_hash`, `gsm2tree_rs.py:161-173`). The custom `__eq__` does:
1. `other.extract::<EnumType>()` — Rust-side type extraction (fast if types match).
2. If successful: `self == &other_label` — Rust `PartialEq` on enum variants (O(1)).
3. If not: `other.getattr("_fltk_canonical_name")` + string compare.

So per-iteration cost is a Python dispatch + fast Rust comparison when label types match. Not a string allocation per step, but not a raw pointer compare either.

## Would identity comparison (`is`) be correct?

**Only under a restricted API contract that does not currently hold.**

PyO3's `PyAnyMethods::is()` (`pyo3-0.23.5/src/types/any.rs:933-935`) does `self.as_ptr() == other.as_ptr()`. This exists and is usable.

**The problem**: `Grammar_Label::Rule.into_pyobject(py)?` is implemented via `Bound::new(py, self)` — confirmed at `pyo3-macros-backend-0.23.5/src/pyclass.rs:2173`. This is a fresh heap allocation every call. The label stored in the children tuple (from `append_rule`) and the label constructed at the top of `children_rule` are **different Python objects** even though they are semantically equal. Identity comparison would return `false` for every child, producing empty results.

Making identity comparison work would require caching one `GILOnceCell<PyObject>` per label variant per class, so the same Python object is reused. This is feasible (analogous to `UNKNOWN_SPAN_CACHE` at `gsm2tree_rs.py:131` / `src/cst_fegen.rs:9`), but has a further correctness constraint:

**Cross-backend concern**: the generic `append` method (`gsm2tree_rs.py:371-380`) accepts `label: Option<PyObject>` and stores it verbatim. A downstream consumer (or the Python parser running against the Rust backend) could call `node.append(child, label=SomeNode.Label.FOO)` with a Python-backend label object. The Python-backend label is a different Python object than the Rust-cached singleton. Identity comparison would silently fail to match those children — a correctness regression against the existing `eq()`-based behavior.

**In normal generated-parser usage**: generated parsers use only typed `append_{label}` methods (confirmed: `fltk/fegen/fltk_parser.py:128,148,161,217,254,342,361,380,416,450,469,488`; `gsm2parser.py:451` template). `extend` for inline rules uses `result.children.extend(item.result.children)` which copies existing tuples, preserving whatever label objects were originally stored. So in practice the cross-backend case does not arise from generated parsers — but it IS a supported public API path.

## Would identity comparison be correct in the Python backend?

Yes, because Python `enum.auto()` members are singletons: `Foo.A is Foo.A` is always `True` (verified: `enum.Enum.__eq__ is object.__eq__` is `True`). The Python backend's `label == Class.Label.FOO` (`gsm2tree.py:303-304`) is in effect an identity comparison. This asymmetry between backends is a hidden correctness difference the TODO does not call out.

## Pre-grouped storage

Would make label accessors O(1) but requires a `dict[label_variant, list[child]]` alongside `children: list[tuple[...]]`. Breaks the `children` attribute's public API shape (`list[tuple[Optional[Label], T]]` as declared in protocols and used by downstream consumers). Not a drop-in change.

## Blockers and open questions

- No profiling data exists yet; the TODO's "defer until profiling" rationale is intact.
- The TODO's "identity comparison" alternative is **incorrect as stated** without also (a) caching per-variant Python objects in `GILOnceCell` and (b) accepting the cross-backend correctness restriction on generic `append`. The TODO does not capture this.
- The Python-backend `==` effectively being identity while the Rust-backend uses a full `rich_compare` dispatch is a hidden behavioral difference (performance, not correctness, since both return the same answer in correct usage).
- `GILOnceCell`-based identity comparison IS implementable; cost would be one Python heap allocation per variant per process (amortized) and one pointer comparison per loop iteration instead of a Python dispatch. Whether that matters depends on CST node child counts in real grammars.

## Verdict

TODO is **correctly deferred**. The O(children) scan claim is accurate. The "identity comparison" framing is imprecise: it requires per-variant object caching and carries a cross-backend API correctness risk not mentioned in the TODO. The pre-grouped storage alternative is incompatible with the public `children` API. No action needed until profiling data.
