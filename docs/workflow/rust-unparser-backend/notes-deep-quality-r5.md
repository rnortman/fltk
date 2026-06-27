# Quality review — batch 5 (f9ed936..5f7b5cb)

## quality-1

**File:line:** `fltk/unparse/gsm2unparser_rs.py:233–242` (`_gen_rule_entry`) and `:495–500` (`_gen_alts_dispatch`)

**Issue — copy-paste with slight variation:** Both methods independently implement the "try each `{prefix}__alt{N}` from position `X`, clone `acc` for all but the last attempt, return the first success" dispatch loop.  The two copies differ only in: (a) start position (`0` literal vs. passed `pos`), (b) how the callee name is spelled (`self.unparse_{rule_name}__alt{alt_idx}` vs. `self.{alts_prefix}__alt{alt_idx}`), and (c) the `pop_chain` application in the rule-entry path.

**Consequence:** Any future change to the dispatch strategy — error telemetry, a different acc-clone heuristic, diagnostics on total-failure — must be applied in both places independently.  The `pop_chain` path is already a concrete divergence between the two copies (rule entry has it; alts dispatch doesn't), so the shared logic is already drifting.  When item-level anchors land and touch the dispatch site, the probability of updating only one copy and silently breaking sub-expression dispatch is real.

**Fix:** Extract a private helper that emits just the loop lines:

```python
def _gen_alt_dispatch_loop(
    self, prefix: str, n_alts: int, start_pos: str, pop_chain: str = ""
) -> list[str]:
    lines: list[str] = []
    for alt_idx in range(n_alts):
        acc_arg = "acc" if alt_idx == n_alts - 1 else "acc.clone()"
        lines.append(
            f"        if let Some(r) = self.{prefix}__alt{alt_idx}"
            f"(node, {start_pos}, {acc_arg}) {{"
        )
        if pop_chain:
            lines.append(f"            let acc = r.accumulator{pop_chain};")
            lines.append("            return Some(UnparseResult::new(acc, r.new_pos));")
        else:
            lines.append("            return Some(r);")
        lines.append("        }")
    lines.append("        None")
    return lines
```

`_gen_rule_entry` calls it with `prefix=f"unparse_{rule_name}"`, `start_pos="0"`, `pop_chain=pop_chain`.  `_gen_alts_dispatch` calls it with `prefix=alts_prefix`, `start_pos="pos"`.  The method body construction around the loop stays in each caller.

---

## quality-2

**File:line:** `fltk/unparse/gsm2unparser_rs.py:344–346` (`_item_spacing_lines`)

**Issue — dead branch after `Literal` exhaustion:** The `else: raise ValueError(...)` branch is unreachable.  `position: Literal["before", "after"]` means Pyright flags any call site whose argument isn't one of those two strings, and the two branches above cover the entire type.  No runtime path reaches `else`.

**Consequence:** To a reader unfamiliar with `Literal`, the `else` branch signals that the method accepts an open-ended string with a runtime fallthrough guard — the opposite of what the type says.  If a third position value is added to the `Literal` in the future and the author forgets a matching `elif`, the `else` gives false confidence that the runtime guard catches it; but Pyright's flow analysis would already flag unbound `spacing`/`ctor` variables before `else` is reached, making the branch doubly redundant.  The pattern also propagates: callers generating the position string at a level where Pyright can't track the `Literal` may silence a real exhaustiveness error by relying on the `else` as a safety net.

**Fix:** Drop the `else` branch entirely.  The `if / elif` pair is exhaustive given the `Literal` type; Pyright enforces it at all call sites.  If explicit unreachability documentation is desired, use `typing_extensions.assert_never(position)` in a bare `else` (available for Python 3.10 via `typing_extensions`; stdlib `typing.assert_never` is 3.11+).
