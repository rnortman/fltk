# Correctness Review — Phase 3 Rust CST Generator

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Base 6f82c48 .. HEAD af7dc6e. Verified: built (`maturin develop`), full suite passes (635), Phase 3 files pass (182), generated PoC output byte-equivalent to hand-written Phase 2 modulo cosmetic comment chars + enum/struct interleave order + added Trivia class.

---

## correctness-1

**File**: `fltk/fegen/gsm2tree_rs.py:44-59` (`generate`), `:401-415` (`_register_classes_fn`)

**What's wrong**: A grammar rule whose model has empty `types` (e.g. all items SUPPRESS, no whitespace separators) is silently emitted as a node struct. The Python generator (`gsm2tree.py:117-122`) raises `RuntimeError("Model class ... would have no members ...")` for the identical model. The Rust generator never performs this check.

**Why**: The design (design.md:338-340) asserts "The Rust generator inherits this check via `CstGenerator`. If a grammar produces such a rule, the Python analysis layer raises before the Rust emitter runs." This is false. The `RuntimeError` is raised in `CstGenerator.py_class_for_model` — part of the *emit* pipeline (`gen_py_module` → `py_class_for_model`). `RustCstGenerator.__init__` only invokes `CstGenerator.__init__`, which runs `model_for_rule` (the *analysis* pipeline). `model_for_rule` / `model_for_items` / `model_for_item` never inspect `model.types` for emptiness — they only build the `ItemsModel`. So no exception is raised during analysis; `RustCstGenerator.generate()` proceeds to emit a struct from the empty model.

Confirmed empirically: rule `empty := %"x"` (single suppressed literal) →
- `pg.rule_models['empty'].types == set()`
- Python `gen_py_module()` raises `RuntimeError: Model class \`Empty\` would have no members ...`
- Rust `generate()` emits `pub struct Empty {` (no label enum), no error.

**Consequence**: For any grammar containing a rule that includes no terms (every item SUPPRESS and no whitespace separator producing `_trivia`), the two generators diverge: Python rejects the grammar; Rust accepts it and emits a degenerate node class with `span` + empty `children` and only the three generic methods (`append`/`extend`/`child`), no per-label methods, no `Label`. This violates the design's stated invariant that the empty-model case is rejected uniformly by the shared analysis layer. The emitted struct compiles (the struct body never references `model.types`), so the divergence is silent — a grammar author gets a usable-but-meaningless node class from the Rust path and a hard error from the Python path. Not triggered by the PoC grammar or `fegen.fltkg` (every rule there has ≥1 included term), so no current test exercises it.

**Suggested fix**: In `generate()` (and `_register_classes_fn`, or factor a shared rule iterator), before emitting a rule's blocks, raise the same error the Python generator does when `not model.types`:
```python
for rule in self.grammar.rules:
    model = self._py_gen.rule_models[rule.name]
    if not model.types:
        class_name = self._py_gen.class_name_for_rule_node(rule.name)
        raise RuntimeError(
            f"Model class `{class_name}` would have no members; "
            "ensure there is at least one term included in the model."
        )
    ...
```
This restores parity with `gsm2tree.py` and matches the design's intended contract.

---

## Non-issues verified (no finding)

- **Generated PoC ≡ Phase 2**: `diff` of `6f82c48:src/cst_poc.rs` vs `af7dc6e:src/cst_generated.rs` shows only (a) comment box-drawing chars vs hyphens, (b) label-enum/struct interleave order (Phase 2 emitted all enums then all structs; generator emits enum,struct per rule — compiles identically), (c) appended `Trivia` class + `register_classes`. No behavioral method-body differences. `test_rust_cst_poc.py` (27 ACs) unchanged and passes against generated output.
- **Label/generic method name collision**: a label named `child` yields `child_child`/`append_child`, distinct from generic `child`/`append`. No shadowing.
- **register_classes ordering**: label enum `add_class` always precedes its node struct (PyO3 requires referenced types registered first); empty-label rules correctly emit only the struct line. Verified in both `cst_generated.rs` and `cst_fegen.rs`.
- **Determinism**: emit loop iterates `self.grammar.rules` (ordered Sequence) and `sorted(model.labels.keys())`. No unsorted set iteration in the emit path. `test_deterministic_output` passes.
- **Zero-label test impl-block extraction** (`test_gsm2tree_rs.py:407-410`): `source.index("\n}", impl_start)` reliably finds the impl-closing brace — method-body closing braces are 4-space indented (`    }`), only the impl/register_classes braces sit at column 0, and the impl brace is the first such after `impl Token {`. Logic sound.
- **`__eq__` NotImplemented path / `__hash__` raising / `maybe`/`child` early-break count semantics**: emitted verbatim from Phase 2 template; validated by the passing 27-AC suite.
- **fegen submodule `Label` classattr** (design.md:354 assumption): `test_label_access` passes for all 14 submodule-registered classes — `type_object` is module-agnostic as assumed.
