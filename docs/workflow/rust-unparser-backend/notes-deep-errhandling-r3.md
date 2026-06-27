Commit reviewed: e6a682cb883db43d6df2cc7215cb982121934254

---

errhandling-1
File: fltk/unparse/gsm2unparser_rs.py, _gen_rule_entry (diff lines ~194–216)

The broken error path: two `for op in anchor.operations` loops — one over RULE_START
operations, one over RULE_END operations — each consist of an `if/elif/elif` chain with
no `else` branch. For RULE_START, only GROUP_BEGIN, NEST_BEGIN, and JOIN_BEGIN are
handled; for RULE_END, only NEST_END, GROUP_END, and JOIN_END.

Why: any other OperationType value (SPACING misrouted to a rule-start anchor; a
GROUP_END/NEST_END/JOIN_END in the rule-start position; a GROUP_BEGIN in the rule-end
position; any future OperationType added to the enum) falls through both chains without
error, log, or any code emission. The operation is silently dropped.

Through the normal `.fltkfmt` parser path these anchor keys only ever receive the
matching BEGIN/END types, so the silent drop is unreachable there. It is reachable
through direct `FormatterConfig` construction in tests or calling code — including the
`get_anchor_config` merge path, which can produce unexpected operation orderings when
both global and rule-specific configs exist for the same key.

Consequence: a misconfigured or programmatically constructed FormatterConfig that places
a SPACING op (or any unexpected type) in a RULE_START anchor generates Rust code that
silently omits the intended push operation. The generated output is wrong and there is
no diagnostic at generation time or run time to identify the cause. On-call would see
incorrect formatting in the Rust unparser with no traceable error path.

What must change: add an `else: raise ValueError(f"Unexpected operation type
{op.operation_type!r} in RULE_START anchor for rule {rule_name!r}")` after the
RULE_START elif chain, and a corresponding `else: raise ValueError(...)` for the
RULE_END chain. These are invariant violations — if they fire, the config is malformed
and the generator must not proceed silently.

---

errhandling-2
File: fltk/unparse/gsm2unparser_rs.py, _gen_rule_entry (diff line ~198)

The broken error path:

    lines.append(f"        let acc = acc.push_nest({op.indent or 1});")

Why: `op.indent or 1` evaluates the operand with Python's truthiness rule. `None or 1`
gives 1 (intended default). But `0 or 1` also gives 1, so a `FormatOperation` with
`indent=0` silently emits `push_nest(1)`. `FormatOperation(indent=0)` is a valid
construction — `FormatOperation.indent` is typed `int | None` and the grammar allows
`nest(0)` (even if semantically odd). The substitution is wrong-value-with-no-diagnostic.

Consequence: generated Rust code uses the wrong indent level. No exception, no log. The
mismatch between the configured indent and the emitted Rust is invisible until the
generated output is inspected, and even then the cause is non-obvious.

What must change: replace `op.indent or 1` with `op.indent if op.indent is not None
else 1`. If `op.indent is None` is actually an invariant violation for a NEST_BEGIN
operation (it should always be set), raise instead of defaulting.

---

errhandling-3
File: fltk/unparse/gsm2unparser_rs.py, _gen_rule_entry (diff line ~203)

The broken error path:

    separator_expr = self._doc_to_rust_expr(op.separator)

`_doc_to_rust_expr` raises `ValueError("Unknown Doc type: <doc>")` when the separator
Doc is a Group, Nest, Join, or Comment. This ValueError propagates to the caller of
`generate()` with no additional context.

Why: the error message names the Doc object but not the rule whose JOIN_BEGIN separator
triggered it. In a grammar with many rules, the stack trace identifies the Python call
site but not the grammar-level origin (rule name, anchor position, config source).

Consequence: a single unsupported separator type in any rule's config produces
`ValueError: Unknown Doc type: ...` with no indication of which rule failed. The
diagnosis requires iterating over rules or binary-searching the config, which is
avoidable.

What must change: wrap the call and re-raise with rule context:

    try:
        separator_expr = self._doc_to_rust_expr(op.separator)
    except ValueError as exc:
        msg = f"Rule {rule_name!r} JOIN_BEGIN separator uses unsupported Doc type: {exc}"
        raise ValueError(msg) from exc
