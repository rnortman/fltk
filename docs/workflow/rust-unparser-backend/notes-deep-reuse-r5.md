## reuse-1

**File:line**: `fltk/unparse/gsm2unparser_rs.py:495-499` (new `_gen_alts_dispatch`) vs `fltk/unparse/gsm2unparser_rs.py:231-241` (pre-existing `_gen_rule_entry`)

**What's duplicated**: The clone-last alt-dispatch loop is emitted by both methods. The inner structure in each is:

```python
for alt_idx in range(n_alts):
    acc_arg = "acc" if alt_idx == n_alts - 1 else "acc.clone()"
    lines.append(f"        if let Some(r) = self.{prefix}__alt{alt_idx}(node, {pos_expr}, {acc_arg}) {{")
    lines.append("            return Some(r);")
    lines.append("        }")
lines.append("        None")
```

`_gen_alts_dispatch` hard-codes `alts_prefix` as the prefix and `pos` (the Rust variable from the generated method's signature) as the position expression. `_gen_rule_entry` hard-codes `unparse_{rule_name}` as the prefix and `0` (literal) as the position expression; when `pop_chain` is empty, the per-alternative body is identical byte-for-byte (`return Some(r);`). The `_gen_alts_dispatch` docstring already acknowledges it "parallels `_gen_rule_entry`'s alternative dispatch," but the parallel is not extracted into a shared helper.

**Existing function/utility**: `_gen_rule_entry`, `fltk/unparse/gsm2unparser_rs.py:187`. The new `_gen_alts_dispatch` could instead be a parameterized private helper that `_gen_rule_entry` also calls, accepting `prefix: str`, `pos_expr: str` (e.g. `"0"` vs `"pos"`), and an optional success-body override for the pop-chain case. Alternatively, `_gen_rule_entry` could delegate its dispatch loop to `_gen_alts_dispatch` with a renamed/extended signature that accepts a position-expression string and a success-body hook.

**Consequence**: The clone-last clone pattern (`"acc" if alt_idx == n_alts - 1 else "acc.clone()"`) and the `if let Some(r) = ...` dispatch loop structure exist in two separate methods. A future change to the dispatch pattern (e.g. short-circuiting on a None accumulator, adding profiling, or switching the clone strategy) must be applied in both `_gen_rule_entry` and `_gen_alts_dispatch` independently, with no compiler or test signal if one is missed.
