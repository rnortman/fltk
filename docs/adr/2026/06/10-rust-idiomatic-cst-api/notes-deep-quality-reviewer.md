## quality-1

**File:line**: `fltk/fegen/gsm2tree_rs.py:1069–1094`

`_native_per_label_methods` takes `class_name` but not `rule_name`, even though every caller is `_node_block` which has `rule_name` as a direct parameter. To obtain `rule_name`, the method reconstructs a full `class_name → rule_name` reverse map from `self._py_gen.rule_models` on every invocation (line 1086), then looks up `class_name` with `.get()` (line 1087). Because every `class_name` passed by `_node_block` was itself derived from `class_name_for_rule_node(rule_name)`, the `.get()` always hits — the `else` fallback at line 1094 (`ref_type, single_node_cls, total_variants = f"&{enum_name}", None, 2`) is dead code. The fallback silently assumes a union-typed label with two variants, which would generate incorrect accessor signatures for any label that is actually span-only or single-node-typed.

**Consequence**: (a) O(|grammar|) dict construction per node block call, wasted on every code generation run; (b) the dead fallback branch creates a false impression that `rule_name` may legitimately be absent, which will mislead the next person who reasons about whether the map lookup can miss; (c) if the fallback were ever reachable (e.g. if a future refactor calls this method from outside `_node_block`), it would silently emit wrong accessor types for non-union labels — mistyped generated code that compiles but returns `&FooChild` where `&Shared<T>` or `&Span` is expected.

**Fix**: add `rule_name: str` as a parameter to `_native_per_label_methods`; update the single call site in `_node_block` (line 728) to pass `rule_name`; remove lines 1086–1094 (the map construction, the `.get()`, and the dead fallback), replacing with `ref_type, single_node_cls, total_variants = self._label_type_info(rule_name, label)` directly in the loop.

---

## quality-2

**File:line**: `fltk/fegen/gsm2tree_rs.py:1199–1215, 1264–1282` (generated union-label `child_<lbl>` and `maybe_<lbl>` bodies)

The union-typed-label branch of `_native_per_label_methods` (the `else` branch at lines 1143, 1198, 1263, 1327 — reached when `label_types` has more than one type) is never exercised by any in-tree grammar. All labels in the PoC grammar, fegen grammar, and fixture grammar are either span-only or single-node-typed; `_label_type_info` never returns `len(label_types) > 1` for any real grammar. The union-label native accessor and mutator code paths in the generator are untested at the generator unit-test level (`test_gsm2tree_rs.py` has no test grammar that produces a union label), and the compiled Rust test suite (`native_tests.rs`, `spike_tests.rs`) naturally cannot test it either. The only validation these paths receive is clippy/rustc on the generated output — but since no grammar exercises the union path, even that is vacuous.

**Consequence**: the union-label paths use a different algorithmic structure than the single-typed paths (`two-next()` iterator trick + second `.filter().count()` re-scan on the error path vs. `collect()` + index). Any bug in the union-label emission goes undetected until a downstream grammar with a truly union-typed label exercises it. As Phase 4 generates parsers that may encounter union labels from complex grammars, this becomes a latent failure point. The pattern also propagates: whoever adds the first union-label grammar will find that the generator-level tests provide zero coverage signal.

**Fix**: add a test grammar with a union-typed label (e.g. a rule `node := lhs:( identifier | literal ) rhs:identifier`) to `test_gsm2tree_rs.py`, verify the generated Rust accessor signatures are correct, and add a compiled Rust test in `native_tests.rs` or `spike_tests.rs` for the union-label read and write paths. This is the test gap that hides generator bugs in the union branch.
