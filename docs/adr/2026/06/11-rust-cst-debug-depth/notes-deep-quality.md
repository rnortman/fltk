Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 2f9b05e (base: 8c10cea)

---

## quality-1

**File:line** `tests/test_gsm2tree_rs.py:447-453`

**Issue** `test_node_struct_pyclass_gated` has a stale assertion that passes for the wrong reason. The docstring says "data struct derives Clone and Debug (Phase 2)" and the assertion is `assert "#[derive(Clone, Debug)]" in poc_source`. After this change, node data structs emit `#[derive(Clone)]` plus a manual `impl fmt::Debug`; the string `#[derive(Clone, Debug)]` now appears only on child enums. The assertion still passes — but it now witnesses child-enum behavior, not node-struct behavior. The intent (verify node structs derive Debug) is silently gone.

**Consequence** The generator can now regress node-struct Debug (e.g., accidentally drop the manual `impl fmt::Debug` emission or reintroduce `derive(Debug)` on structs) without any generator test catching it. Only the downstream Rust compile gate would surface it, much later. The test's false confidence propagates: future maintainers reading it will believe node-struct Debug is tested.

**Fix** Update the test to match the new reality:
- Change the comment from "Data struct derives Clone and Debug (Phase 2)" to reflect that node structs now have a manual Debug impl.
- Replace `assert "#[derive(Clone, Debug)]" in poc_source` (which now matches child enums only) with:
  - `assert "#[derive(Clone)]" in poc_source` (node struct derives only Clone now — this matches both node structs and child enums, but is directionally correct)
  - `assert "impl fmt::Debug for Identifier" in poc_source` (positive test that manual Debug is present)
  - `assert "#[derive(Clone, Debug)]\npub struct" not in poc_source` (node structs must not derive Debug)
- Optionally add a test asserting `"use std::fmt;" in poc_source` since the preamble test at lines 173-191 does not currently check for it.

---

## quality-2

**File:line** `TODO.md` (absent entry); `docs/adr/2026/06/11-rust-cst-debug-depth/design.md:17`

**Issue** Deep `PartialEq` recursion through the same `Shared<T>` ownership chain is a live DoS vector — `assert_eq!` on two attacker-depth-controlled trees, or any equality check in parser fixtures or downstream consumer tests, stack-overflows and aborts the process (same mechanism as the fixed Debug/Drop paths). The design correctly identifies it as "out of scope (pre-existing, distinct, not user-authorized here)" but files no TODO entry. CLAUDE.md requires every known concrete thing that needs to happen to have a `TODO.md` entry with a slug and a code comment at the relevant location. There is no entry and no `TODO(rust-cst-eq-depth)` comment anywhere.

**Consequence** The PartialEq exposure will be forgotten. Future reviewers will see the iterative Debug/Drop treatment and assume all three recursive paths have been addressed. The next person to write a deep-tree equality test (or have a parser consumer do so) will encounter an unexplained SIGSEGV with no tracking context explaining why the fix was deferred. The fix is the same pattern: emit iterative `impl PartialEq` on node structs (or a depth-capped shallow equality that refuses to compare subtrees, depending on semantics wanted).

**Fix** Add a `TODO.md` entry:

```markdown
## `rust-cst-eq-depth`

`PartialEq` on generated node structs recurses through `Shared<T>` children with no
depth bound; tree depth is attacker-controlled, so `assert_eq!` or any equality check
on a deep parser-produced tree aborts the process (stack exhaustion, uncatchable).
Same root cause as the fixed Debug/Drop paths. Fix: emit iterative `impl PartialEq` on
node structs (worklist or depth-capped shallow form, per the same generator pattern used
for `impl Drop`). Location: `fltk/fegen/gsm2tree_rs.py` (`_node_block`, `_drop_block`
pattern), `crates/fltk-cst-core/src/shared.rs` (`PartialEq` impl).
```

Add `// TODO(rust-cst-eq-depth)` to the `impl<T: PartialEq> PartialEq for Shared<T>` block in `crates/fltk-cst-core/src/shared.rs` (line 93) and to the derived `PartialEq` comment in `fltk/fegen/gsm2tree_rs.py` `_node_block`.

---

## quality-3

**File:line** `fltk/fegen/gsm2tree_rs.py:1678-1689` (`_drop_block`)

**Issue** The `drain_into` match-arm body is copy-pasted N times in the generator (one per class in `child_union`), with only the variant name changing. In the generated output this produces N identical 5-line bodies distinguished only by type. For the parser fixture that is 10 arms; for `cst_fegen.rs` it is larger. The body:

```python
lines.append(f"            DropWorklistItem::{cls}(shared) => {{")
lines.append("                if shared.strong_count() == 1 {")
lines.append("                    // Sole owner: steal the children so the node drops childless")
lines.append("                    // (its Drop early-returns) instead of recursing through drop glue.")
lines.append("                    let children = std::mem::take(&mut shared.write().children);")
lines.append("                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));")
lines.append("                }")
lines.append("            }")
```

is repeated verbatim for every `cls`.

**Consequence** If the drain body needs to change (e.g., add observability, change the steal condition, or refactor the children-Vec access), the generator must update a block of `lines.append(...)` calls that reads as a flat list with no per-arm abstraction. The repetition in the generator masks the uniformity of the arm bodies. Each copy is also a potential site for the bodies to diverge (a mis-edit to one arm but not others would produce subtly non-uniform drain logic).

**Fix** Extract an `_emit_drain_arm(lines, cls)` helper method in `_drop_block` and call it in the loop:

```python
def _emit_drain_arm(self, lines: list[str], cls: str) -> None:
    lines.append(f"            DropWorklistItem::{cls}(shared) => {{")
    lines.append("                if shared.strong_count() == 1 {")
    lines.append("                    // Sole owner: steal the children so the node drops childless")
    lines.append("                    // (its Drop early-returns) instead of recursing through drop glue.")
    lines.append("                    let children = std::mem::take(&mut shared.write().children);")
    lines.append("                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));")
    lines.append("                }")
    lines.append("            }")

# in _drop_block:
for cls in child_union:
    self._emit_drain_arm(lines, cls)
```

This is a pure generator refactor (generated output is identical); it makes the uniformity explicit and reduces the change surface for future edits to the drain logic.
