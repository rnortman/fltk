# Quality Review — cross-backend-label-equality

Commit reviewed: c57f888. Base: 854e1ad.

---

## quality-1

**File:line:** `fltk/fegen/gsm2tree.py:195`

**Issue:** `kind` dataclass field emits `NodeKind.{class_name.upper()}` directly instead of routing through `node_kind_member_name(rule_name)`. The method `node_kind_member_name` (line 95–97) is the defined abstraction for this mapping; line 195 duplicates the `.upper()` inline. The Protocol generator (line 446) correctly uses `node_kind_member_name(rule_name)`. The concrete-class generator bypasses it, creating two parallel paths for the same mapping.

**Consequence:** If `node_kind_member_name` is ever changed (e.g. to apply a different transform for rules with names that don't round-trip through class-name upper), the concrete-class path silently diverges from the Protocol path and from the Rust generator. The divergence would cause a `Literal` type mismatch between concrete class and Protocol — a pyright error at downstream call sites, not a test failure.

**Fix:** In `py_class_for_model`, the `class_name` parameter is already derived from `rule_name` via `class_name_for_rule_node`. Either pass `rule_name` through to `py_class_for_model` so `node_kind_member_name` can be called, or assert that `class_name.upper() == node_kind_member_name(rule_name)` immediately after computing `class_name` in `gen_py_module` (line 145). The simpler fix is to pass the rule name alongside the class name, matching the existing pattern in `_protocol_class_for_model`.

---

## quality-2

**File:line:** `fltk/fegen/gsm2tree_rs.py:160` (generated into every NodeKind enum, e.g. `src/cst_fegen.rs:16`)

**Issue:** `#[allow(non_camel_case_types)]` is unconditionally emitted on the `NodeKind` enum. `NodeKind` uses CamelCase Rust variant names (`Grammar`, `Rule`, `Items`, …); none are non-camel-case. The lint suppression is needed for `Items_Label`, `Grammar_Label`, etc., but copying the same preamble to `NodeKind` suppresses a warning that would never fire.

**Consequence:** Rust compiler warnings about non-camel-case identifiers on `NodeKind` variants (should they accidentally appear in future) are silently swallowed. The suppression also signals to readers that the enum has non-standard names when it does not, adding confusion. As more grammars accumulate, all will carry this unnecessary suppression.

**Fix:** In `_node_kind_block` (`gsm2tree_rs.py:160`), remove the `lines.append("#[allow(non_camel_case_types)]")` line. The annotation is correct on label enum blocks (where it is genuinely needed) and should not be copied to `NodeKind`.

---

## quality-3

**File:line:** `fltk/fegen/gsm2tree.py:423` and `fltk/fegen/fltk_cst_protocol.py:7`

**Issue:** `_protocol_class_for_model` gained a `rule_name: str = ""` default parameter, creating a silent fallback that emits `kind: object` when called with only two positional args. There is no in-tree caller that uses this fallback — the sole caller at line 417 always passes `rule` as the third argument. The default exists to preserve the old signature, but the old signature no longer exists in any caller. This is dead-fallback code: the `else: klass.body.append(pygen.stmt("kind: object"))` branch at line 448–449 is unreachable from current callers.

**Consequence:** A future call to `_protocol_class_for_model(class_name, model)` (e.g. in a test or subclass) silently emits `kind: object` instead of the correct `Literal[NodeKind.X]`, producing a Protocol member that pyright cannot narrow on. The breakage is silent: no error at call time, no generator error — only a downstream narrowing failure.

**Fix:** Make `rule_name` a required positional parameter (remove the default). All current callers already pass it. If there is a future need for a "no concrete module" path, add an explicit `Optional` with a documented semantic, not an empty-string sentinel.

---

## quality-4

**File:line:** `fltk/fegen/fltk_cst_protocol.py:7` (generated); `fltk/fegen/gsm2tree.py:407–412`

**Issue:** The Protocol module now unconditionally imports `NodeKind` from the concrete Python CST module (`from fltk.fegen.fltk_cst import NodeKind`) at module level. Before this change, the Protocol module had no runtime imports from the concrete module. This creates a new hard coupling: loading the Protocol module requires the concrete Python CST module to be importable, even for consumers who use the Protocol purely for type-checking with a Rust backend.

**Consequence:** Out-of-tree consumers using the Protocol module purely for type annotations (e.g. `from mygrammar_cst_protocol import Foo`) now pull in the entire concrete Python CST module at import time. In environments where the generated Python CST is intentionally absent (pure-Rust deployments), this breaks module loading. The coupling also propagates to every generated grammar: any out-of-tree grammar's Protocol module will import from the corresponding concrete module unconditionally. This is a permanent structural coupling added to every generated Protocol module.

**Fix:** Move the `from {concrete_module} import NodeKind` import under `if typing.TYPE_CHECKING:` in the Protocol module. With `from __future__ import annotations` already present, all `Literal[NodeKind.X]` annotations are evaluated lazily (as strings), so runtime resolution of `NodeKind` is not needed. In `gsm2tree.py:gen_protocol_module`, change the import emission to include a `TYPE_CHECKING` guard: emit `if TYPE_CHECKING:\n    from {concrete_module} import NodeKind` instead of a bare import statement.
