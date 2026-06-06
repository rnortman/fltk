# Test Review — Cross-Backend Label Equality

Commit reviewed: c57f888. Base: 854e1ad.

---

## test-1

**File:line:** `tests/test_cross_backend_label_equality.py:223-228`

**What's wrong — missing coverage:** `TestNodeKindCrossBackend.test_no_raise_on_unrelated` only tests `kind == other` (one direction) and omits the symmetric `other == kind` check. The corresponding `TestLabelCrossBackend.test_ac7_no_raise_on_unrelated_objects` (line 126) explicitly tests both directions for labels. The NodeKind test suppresses `b_key` via `ARG002` and never uses a cross-backend label as the unrelated operand (unlike the label test at line 131 which appends a cross-family label). It also omits the `!=` direction.

**Consequence:** A bug in the reflected `__eq__` path on `NodeKind` (the case where `other.__eq__(kind)` is called) or in `__ne__` would not be caught by any test. The symmetric path is the one the design calls out in §3.2 as critical for correctness when both sides might return `NotImplemented`.

**Fix:** Mirror the AC7 label test structure: loop over `[None, 1, "NodeKind.ITEMS", object(), _label(b_key, "Items", "NO_WS")]`, check both `kind == other` and `other == kind`, and assert both `== False` and `!= True`.

---

## test-2

**File:line:** `tests/test_cross_backend_label_equality.py:126-142`

**What's wrong — missing coverage:** `test_ac7_no_raise_on_unrelated_objects` adds only a same-backend cross-class label (`_label(a_key, "Disposition", "INCLUDE")`) as the cross-family case. It never tests a *cross-backend* cross-class case — e.g. `a_key.Items.Label.NO_WS == b_key.Disposition.Label.INCLUDE`. The cross-backend path (`_fltk_canonical_name` comparison) is exercised only for equal-name members; for unequal cross-class cross-backend cases the test uses same-backend operands only. The failure mode (strings match accidentally, or NotImplemented cascade) is backend-combination dependent.

**Consequence:** A bug where the canonical-name path returns wrong results for cross-backend cross-class operands (different class prefixes) would not be caught. E.g. if a Rust-side `_fltk_canonical_name` for `Disposition.Label.INCLUDE` were malformed, the test wouldn't detect it in the unequal direction.

**Fix:** In the parametrized `test_ac7_no_raise_on_unrelated_objects`, add `_label(b_key, "Disposition", "INCLUDE")` (note `b_key`, not `a_key`) so the cross-backend cross-class path is exercised.

---

## test-3

**File:line:** `tests/test_cross_backend_label_equality.py:95-101`

**What's wrong — missing coverage:** `test_ac4_hash_consistent_cross_backend` tests hash agreement only for `Items.Label` members (`NO_WS`, `WS_ALLOWED`, `WS_REQUIRED`, `ITEM`). It tests no `NodeKind` members (those are tested in `TestNodeKindCrossBackend.test_hash_consistent`), but more critically it does not test any label class other than `Items` — e.g. `Disposition.Label`, `Quantifier.Label`, `Rule.Label`. The Rust `__hash__` construction (`PyString::new(py, self.__repr__())`) is per-enum-type; a bug in `__repr__` on a non-`Items` label enum would produce wrong hash output undetected.

**Consequence:** Hash bugs on label enums other than `Items` (e.g. `Disposition_Label.__hash__` returning wrong value) would not be caught here. The `test_ac5_set_collapse` and `test_ac6_membership_in_tuple` tests also use only `Items` labels, so there is no indirect coverage either.

**Fix:** Add at least one member from a second label class (e.g. `Disposition.Label.INCLUDE`) to the hash check members list, or parametrize over label class names.

---

## test-4

**File:line:** `tests/test_cross_backend_label_equality.py:211-221` (`test_canonical_strings_disjoint_from_label`)

**What's wrong — quality:** The test accesses `kind._fltk_canonical_name` and `label._fltk_canonical_name` as public attributes with `type: ignore[union-attr]`. This is fine for the structure check, but the test only checks one pair (`ITEMS` NodeKind vs `Items.NO_WS` Label). It does not check that a `NodeKind` member from the *same* rule name (`ITEMS` vs `Items.Label.ITEM`) is disjoint — the design's family disjointness guarantee (`"NodeKind.ITEMS"` vs `"Items.Label.ITEM"`) is the precise case the design warns about. The current test compares `ITEMS` NodeKind against `NO_WS` Label — a case where the strings would obviously differ anyway regardless of the format.

**Consequence:** If a generator bug emitted `NodeKind.ITEMS` with canonical name `"Items.Label.ITEMS"` (accidentally using the Label format), the disjointness test would still pass because `"Items.Label.ITEMS" != "Items.Label.NO_WS"`. The most dangerous collision — same node name used in both families — is not tested.

**Fix:** Add an assertion that `_nodekind(a_key, "ITEMS") != _label(b_key, "Items", "ITEMS")` (if `ITEMS` is a label member) or more generally verify `kind_cn != label_cn` where the label member name and NodeKind member name are the same word.

---

## test-5

**File:line:** `tests/test_cross_backend_label_equality.py` — omission

**What's wrong — missing coverage:** No test verifies that node objects themselves do **not** expose `_fltk_canonical_name`. The design (§2.1, §3.3) states nodes must not carry the marker so `node == label` routes to `NotImplemented`/`False`, not through the canonical-name path. Without a test, a generator change that accidentally emits `_fltk_canonical_name` on node structs would silently break the marker-scope guarantee and cause `node == label` to return `True` if they happen to share a canonical string.

**Consequence:** The node-doesn't-carry-marker invariant is load-bearing (design §2.1 "implementers MUST NOT add the marker via a shared base/mixin") and is currently unverified.

**Fix:** Add a test asserting `not hasattr(py_cst.Items(...), "_fltk_canonical_name")` (and the Rust equivalent via `fegen_rust_cst.Items`) and that `py_cst.Items() != py_cst.Items.Label.ITEM` (a cross-type comparison between a node object and a label).

---

## test-6

**File:line:** `tests/test_gsm2tree_rs.py:640-648` (`TestKindGetter.test_kind_getter_is_getter_attr`)

**What's wrong — weak assertion:** The test counts total `#[getter]` occurrences and asserts `>= 3`, but the comment inside the test conflates `kind` getters with `_fltk_canonical_name` getters (which also use `#[getter]`). The assertion does not verify that the `kind` getter and the `#[getter]` attribute appear adjacent (i.e. that the getter attribute is actually on the kind function). A refactor that moves `#[getter]` onto other functions without attaching it to `kind` would still pass.

**Consequence:** The test is structurally vacuous for its stated purpose of "kind getter is annotated with `#[getter]`" — it only counts occurrences globally. A regression where `kind` getter loses its `#[getter]` attribute (breaking Python-side `node.kind` access) would not be caught here if other `#[getter]` annotations still exist.

**Fix:** Replace or supplement the count test with a text proximity check: verify that `"#[getter]"` appears as the immediately preceding non-blank line before `"fn kind(&self) -> NodeKind {"` in the generated source, similar to how the existing `test_register_classes_label_before_struct` uses index ordering.

---

## test-7

**File:line:** `fltk/test_plumbing.py:566-585` (`TestCst2GsmNoSelfCst.test_produces_correct_grammar`)

**What's wrong — quality:** The test only checks `len(grammar_default.rules) == len(grammar_baseline.rules)` and rule names. It does not compare the full `gsm.Grammar` structures (alternatives, items, separators, dispositions, quantifiers). The `gsm.Grammar` dataclass presumably supports `==`; the stronger integration tests in `TestAC8RealCst2GsmRustBackend` use `assert python_result == rust_result` (full equality). This test uses partial checks, making it a weaker regression guard than needed for the in-file verification of AC10 correctness.

**Consequence:** A regression where `self.cst` removal breaks disposition or quantifier mapping in `Cst2Gsm` (e.g. `visit_disposition` returning wrong values due to wrong constant substitution) would not be caught by this test — rule names would still match.

**Fix:** Replace the name-by-name loop with `assert grammar_default == grammar_baseline` (full structural equality), matching the pattern used in `TestAC8RealCst2GsmRustBackend`.
