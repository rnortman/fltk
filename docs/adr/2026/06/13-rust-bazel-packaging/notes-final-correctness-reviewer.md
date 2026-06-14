# Correctness review — final

Commits reviewed: fltk fafa6d7..9657025, Clockwork ece332a..6717614.
Focus: generated public-API pyo3 qualification in gsm2tree_rs.py / gsm2parser_rs.py.

## correctness-1

File: fltk/fegen/gsm2tree_rs.py:501 (preamble emits `use pyo3::PyTypeInfo;`);
gap is in `_RESERVED_CLASS_NAMES` (~43-75) and `_RESERVED_CLASS_NAMES_SEEDED` (~86-106).

What's wrong: The de-globbing robustness upgrade is supposed to make the full set
of unqualified preamble imports enumerable and reserved-or-qualified. It misses one
unqualified type-namespace import: the trait `pyo3::PyTypeInfo`, imported unqualified
at line 501 and used (`{Label}::type_object(...)`). A grammar rule named `type_info`
derives CN=`TypeInfo` and handle `Py{CN}` = `PyTypeInfo` (py_handle_name, line 740),
emitting `pub struct PyTypeInfo` — which collides with the imported trait `PyTypeInfo`
in the Rust type namespace.

Why it is not caught: `PyTypeInfo` is a `Py`-prefixed name, so it cannot live in
`_RESERVED_CLASS_NAMES` (the machine check at lines 120-132 forbids `Py{Upper}` entries
there, because that set is matched against CN, and CN for this rule is `TypeInfo`, not
`PyTypeInfo`). To be rejected it must be in `_RESERVED_CLASS_NAMES_SEEDED` so it is
seeded into the cross-rule `claims` dict (lines 216-219) and reported when the rule's
handle `PyTypeInfo` is added at line 228. It is absent from the seeded set, so `claims`
contains only one claimant for `PyTypeInfo` (the rule itself) and no collision is
reported. The per-rule reserved check (lines 170-178) compares CN=`TypeInfo` against
both sets and finds nothing. Generation succeeds silently.

Contrast establishing the gap is real: the three exception imports are handled
correctly via the same handle⟺CN identity — rule `index_error` → CN `IndexError`
(reserved in the plain set) blocks handle `PyIndexError`. `type_info`/`TypeInfo` has no
corresponding reserved CN, and the matching seeded entry is missing.

Consequence: a downstream out-of-tree consumer whose grammar has a rule named
`type_info` gets generated `cst.rs` that fails to compile with rustc E0255 ("the name
`PyTypeInfo` is defined multiple times"). This is exactly the silent-miscompile-at-the-
consumer failure mode the reserved-set backstop is meant to make impossible, and it is
generated PUBLIC API per CLAUDE.md. No test exercises `type_info`
(test_gsm2tree_rs.py:1620-1649 covers index_error/type_error/value_error/bound/py/
python/into_py_object but not type_info).

Suggested fix: add `"PyTypeInfo": "pyo3::PyTypeInfo (unqualified trait import in generated
cst.rs preamble)"` to `_RESERVED_CLASS_NAMES_SEEDED`, and add a `type_info` case to the
reserved-rejection parametrization. (Alternatively qualify the two `::type_object` call
sites as `<{Label} as pyo3::PyTypeInfo>::type_object` and drop the `use pyo3::PyTypeInfo;`
import, recovering `type_info` as a legal rule name — consistent with the any/err/result
qualification choice.)

## Other checks (no findings)

- gsm2parser_rs.py change (register_classes param `&Bound<'_, pyo3::types::PyModule>`,
  retained `pyo3::prelude::*` glob inside `mod python_bindings`): correct. The parser
  generator emits only fixed names (PyParser, PyApplyResult), never rule-derived `PyX`,
  so the glob cannot collide. Asymmetry is documented at the emission site.
- Remaining unqualified type-namespace preamble imports all covered: PyIndexError/
  PyTypeError/PyValueError (plain set), Python/Py/Bound/IntoPyObject (plain set),
  Py{Any,List,Module,String,Type}Methods (seeded set, seeding loop verified). Macros
  pyclass/pymethods/pyfunction/wrap_pyfunction are macro-namespace, cannot collide.
- handle⟺CN identity reasoning verified: handle is always `Py`+CN, so reserving a CN
  blocks its handle, and a Py-prefixed import only collides via the seeded path.
- Cross-rule claims construction (lines 216-243) and machine-checked invariant
  (lines 120-132) are internally consistent.
- Clockwork roundtrip test logic (clockwork_rust_roundtrip_test.py) sound; the
  `result.pos == len(src)` and no-trailing-newline reasoning is correct. Span.__module__
  negative assertion is correct. POC scaffolding scope.
