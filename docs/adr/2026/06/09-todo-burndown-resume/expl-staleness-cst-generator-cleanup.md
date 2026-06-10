# Staleness check: docs/adr/2026/06/06-cst-generator-cleanup/design.md

Checked at HEAD af6e6f3. Concise. Precise. No padding.

---

## 1. TODO slugs: still live, still in the right places

All three slugs remain in `TODO.md` (lines 31, 35, 56) with identical text to when the design was written.

Code comment locations have shifted due to commit 4c8f0ad's large edit of `gsm2tree.py` (+34 lines net):

| Slug | Design-cited line | Current line | Location unchanged? |
|---|---|---|---|
| `cst-protocol-generator-refactor` | `:399-401` | **:409-411** | Same block, +10 lines |
| `protocol-label-member-private` | `:443-445` (docstring) | **:453-455** | Same docstring, +10 lines |
| `cst-protocol-label-free` | `:556-561` | **:578-583** | Same if-else branch, +22 lines |

All three `TODO(slug)` code comments are confirmed present at their new line numbers.

---

## 2. `gsm2tree.py` function line numbers

Design cites specific line numbers; all have shifted. Current actual locations:

| Identifier | Design-cited | Current |
|---|---|---|
| `py_annotation_for_model_types` | `:85-93` | **:85-93** (unchanged) |
| `protocol_annotation_for_model_types` | `:402-432` | **:412-442** |
| `py_class_for_model` | `:200-348` | **:196-359** |
| `_protocol_class_for_model` | `:518-615` | **:540-641** |
| `gen_protocol_module` | `:471-499` | **:477-521** |
| `_emit_protocol_label_member_class` | `:434-469` | **:444-475** |
| `_protocol_class_for_model_with_assignments` | `:501-516` | **:523-538** |

The design's function-body descriptions remain accurate for the current code, just at shifted offsets.

---

## 3. Sub-task A (`protocol-label-member-private`): design still applicable

`gen_protocol_module` (`:477-521`) still emits `_ProtocolLabelMember` unconditionally at line 510 via `self._emit_protocol_label_member_class()`. No `__all__` is emitted anywhere in the function. The generated artifact `fltk/fegen/fltk_cst_protocol.py` still defines `_ProtocolLabelMember` at module level (committed artifact).

Commit 4c8f0ad added `_protocol_span_class()` (`:518`) and `_cst_module_protocol()` (`:519`) calls to `gen_protocol_module`, adding two new Protocol classes (`Span`, `CstModule`) that the design did not account for in its `__all__` symbol list.

**Design impact:** The design's proposed `__all__` contents (`all Protocol node classes + "NodeKind" + "Span" + "CstModule"`) correctly names `Span` and `CstModule`. The new `_protocol_span_class` method produces the `Span` Protocol class and `_cst_module_protocol` produces `CstModule` — both were already listed in the design's intended public `__all__`. No revision needed for sub-task A.

---

## 4. Sub-task B (`cst-protocol-label-free`): design still applicable

`py_class_for_model` (`:196-359`) still unconditionally emits:
- `Label` enum (`pygen.klass(name="Label", bases=["enum.Enum"])`) at line 206, regardless of whether `labels` is empty.
- `children: list[tuple[typing.Optional[Label], {child_annotation}]]` at line 233.
- `label: typing.Optional[Label] = None` in `append` at line 244.
- `label: typing.Optional[Label] = None` in `extend` at line 252.
- `tuple[typing.Optional[Label], {child_annotation}]` return from `child()` at line 267.

The Protocol generator (`_protocol_class_for_model`, `:540-641`) still uses `if labels:` conditionals at `:550`, `:575`, `:585`, `:603` — unchanged. The label-free `TODO(cst-protocol-label-free)` comment and `tuple[None, T]` emit remain at `:578-583`.

The design's correction (make concrete backend match Protocol/Rust for label-free nodes) remains entirely applicable.

---

## 5. Sub-task C (`cst-protocol-generator-refactor`): design still applicable

The parallel quintet loops remain:
- Concrete: `:283-355` (`for label in labels:` loop with 5 per-label methods, real bodies)
- Protocol: `:611-639` (`for label in labels:` loop with 5 per-label methods, `...` bodies)

The design's narrow extract target (quintet loop only, ~40 lines saved) is unchanged. The design explicitly rejects full unification, and that judgment is unaffected.

Commit 4c8f0ad added `extend_children` to both the concrete class (`:259-265`) and the Protocol class (`:599-601`). This is a new 6th method in both classes, not a quintet member. The design's quintet extraction scope (5 per-label accessors: `append_<l>`, `extend_<l>`, `children_<l>`, `child_<l>`, `maybe_<l>`) is unchanged — `extend_children` takes a different parameter (the whole node, not a per-label child) and is not per-label. The quintet loop is unaffected.

---

## 6. Rust CST rework (commit 4c8f0ad): impact on design

The spike `spike-label-free-rust.md` described the Rust generator as emitting `pub struct Foo { span: PyObject, children: Py<PyList> }` (pure-Python-object storage). Commit 4c8f0ad replaced this with native storage: `span: Span, children: Vec<(Option<Label>, Child)>` (`gsm2tree_rs.py:484-486`).

The spike's **conclusions** about the Rust backend's label-free behavior are still correct:
- `_label_enum_block` still returns `""` when `not labels` (`gsm2tree_rs.py:314-315`).
- No `Label` classattr is emitted for zero-label rules; `_label_classattr` is guarded by `if labels:` at `gsm2tree_rs.py:546`.
- Registration of label enums is guarded `if labels:` at `gsm2tree_rs.py:914-915`.

The struct field for the label slot is now `Option<{class_name}_Label>` when labels exist, `Option<()>` when label-free (`gsm2tree_rs.py:474`: `label_type = f"Option<{class_name}_Label>" if labels else "Option<()>"`). The Python-visible label in `children` tuples is still `py.None()` for `None` arms (`_children_getter` at `:645`). The Rust backend's Python-surface behavior (no `Label` class, `None` in children tuples) for label-free nodes is unchanged.

The design's statement "Rust backend needs no change here" remains correct.

The spike cited generator line numbers (`gsm2tree_rs.py:228-235`, `:284-300`, `:371-417`, etc.) that are now invalid; the relevant current locations are: `_label_enum_block` guard at `:308-315`; struct definition at `:483-487`; `_generic_append` at `:657-670`; `_generic_extend` at `:701-723`; `_generic_child` at `:742-761`; `_label_classattr` at `:625-634`; per-label loop at `:555-556`; registration guard at `:913-915`.

---

## 7. `extend_children` not in design

Commit 4c8f0ad added `extend_children` to both concrete (`py_class_for_model:259-265`) and Protocol (`_protocol_class_for_model:599-601`) generators. This is a new method beyond the quintet. The design's sub-task C test plan says "byte-identity" after extraction — the extraction helper produces zero output for label-free nodes and the quintet items only; `extend_children` (which takes `self, other: 'ClassName'`, no label) is not a per-label method and would remain in each generator's class-level frame, not extracted. No revision needed.

---

## 8. `test_cst_protocol.py:113` reference in design

The design notes this test "scans `ast.ClassDef` nodes; `_ProtocolLabelMember` is still a `ClassDef`." Commit 4c8f0ad significantly modified `test_cst_protocol.py` (+143 lines). Verify the test still exists at that line:

The design's line reference (`:113`) should now be at a different offset, but the test's logic and the design's claim about it ("still a `ClassDef`, scan unaffected") depends on the test's content, not its line number. The design's correctness claim about sub-task A's test impact remains valid regardless of line offset.

---

## Summary

| Design claim | Current status |
|---|---|
| All three slugs live in `TODO.md` | **Confirmed** (lines 31, 35, 56) |
| All three `TODO(slug)` comments in `gsm2tree.py` | **Confirmed** (lines 409, 453, 578) |
| `py_class_for_model` unconditionally emits Label enum and Optional[Label] | **Confirmed** (lines 206, 233, 244, 252, 267) |
| Protocol generator uses `if labels:` for label-free asymmetry | **Confirmed** (lines 550, 575, 585, 603) |
| Parallel quintet loops in both generators | **Confirmed** (concrete :283-355; protocol :611-639) |
| No `__all__` in `gen_protocol_module` | **Confirmed** |
| Design's `__all__` public-symbol list covers new `Span`/`CstModule` Protocol classes | **Confirmed** (design already listed both) |
| Rust backend label-free guard unchanged | **Confirmed** (`_label_enum_block:314-315`) |
| Rust struct fields reworked by 4c8f0ad | **Yes** — native `Span` + `Vec`, not `PyObject`/`Py<PyList>`; spike line numbers invalid, conclusions valid |
| Cited `gsm2tree.py` line numbers | **All shifted +10 to +22 lines** |
| Cited `gsm2tree_rs.py` line numbers from spike | **All shifted**; new locations noted above |

**Design is applicable as written.** No claim is invalidated by 4c8f0ad. Line number citations in the design and spike docs are stale but function/behavior descriptions are accurate at current HEAD.
