quality-1. `fltk/fegen/gsm2tree_rs.py:201,213,234` — `_generic_append`, `_generic_extend`, `_generic_child` accept `class_name: str` and suppress the unused-arg lint with `# noqa: ARG002` rather than removing the parameter.

Consequence: every call site in `_node_block` passes `class_name` that is silently dropped. If a future maintainer wants to use `class_name` inside one of these methods (e.g. to emit a struct-type constructor), the signature already "supports" it but the existing suppression masks the intent mismatch. New per-label methods that are added later may follow this same parameter-but-suppress pattern, spreading the inconsistency.

Fix: remove `class_name` from the three signatures and update the three call sites in `_node_block` (`lines.extend(self._generic_append())` etc.).

---

quality-2. `tests/test_gsm2tree_rs.py:298-308` — `FEGEN_RULE_NAMES` is defined but never referenced anywhere in the file.

Consequence: dead constant in a new file. Future readers will wonder whether it has semantic significance or was accidentally omitted from an assertion. It also signals that a planned "rule-name ↔ class-name correspondence" test was omitted; when the generator's `class_name_for_rule_node` logic is changed, there is no test that catches a broken mapping.

Fix: either delete `FEGEN_RULE_NAMES`, or add a test that verifies each rule name maps to the expected class name (pairing it with `FEGEN_CLASS_NAMES`).

---

quality-3. `fltk/fegen/gsm2tree_rs.py:56-61` — `generate()` iterates `self.grammar.rules` twice: once to emit per-rule blocks, and once inside `_register_classes_fn()` which also iterates `self.grammar.rules` and re-derives `class_name` and `labels`. The derivation logic (`rule_models[rule.name]`, `class_name_for_rule_node`, `sorted(model.labels.keys())`) is duplicated between `generate()` (via `_label_enum_block` / `_node_block`) and `_register_classes_fn()`.

Consequence: if the derivation logic or ordering ever diverges between the two loops (e.g., a conditional skip is added to one but not the other), the emitted type definitions and the `register_classes` call list go out of sync silently — no compiler error, just missing registrations at runtime. The duplication will propagate if a third loop (e.g., emitting doc comments or a trait impl) is added.

Fix: introduce a small `_rule_info` helper (or a per-rule dataclass/namedtuple) that derives `(class_name, labels, enum_name)` once per rule, and have both `generate()` and `_register_classes_fn()` consume it.
