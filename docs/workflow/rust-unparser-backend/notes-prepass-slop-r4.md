slop-1: `fltk/unparse/gsm2unparser_rs.py` — `_gen_suppressed_item_body`, last `raise RuntimeError`

```
"cannot be recreated from CST. Consider adding a lable or removing the suppression."
```

"lable" is a typo. The implementation log says it is "preserved for parity" with the upstream Python backend typo. But we own the Python backend too — this is a workaround for an existing-code bug with no TODO to fix the upstream. Two files now ship the misspelling in user-facing error messages.

Consequence: Ships a typo in a production error message. A reviewer will flag it; the "parity" justification requires knowing both files, and reviewers checking only this diff will just see bad English.

Fix: Fix the typo here and fix it in the Python backend in the same commit.

---

slop-2: `fltk/unparse/gsm2unparser_rs.py` — `_gen_identifier_term_body` (line ~326) and `_gen_validate_span_child` (line ~413)

```python
child_classes, has_span = self._cst._child_variants_for_rule(rule_name)
```

`_child_variants_for_rule` is a private method on `RustCstGenerator` called from a different class. The implementation log explicitly notes the gap ("there is no public wrapper for it") and says a public wrapper could be added — but there is no `TODO` comment at either call site in the code. The two call sites have identical boilerplate (`len(child_classes) + (1 if has_span else 0)`) that would also be centralized by a public wrapper.

Consequence: Cross-class private-method access with no in-code marker is a maintenance trap. The next person adding an identifier or regex increment will silently repeat the pattern rather than being prompted to add the wrapper. Reads as an oversight, not a deliberate deferral.

Fix: Either add a `# TODO(rust-child-variants-public)` at each call site (and a matching `TODO.md` entry), or add the public wrapper now — it is clearly the right design and the two call sites show the pattern is already duplicated.

---

slop-3: `fltk/unparse/gsm2unparser_rs.py` — docstrings throughout new methods

Multiple docstrings narrate the implementation process rather than the function's contract:

- `_gen_item_method`: "Multiple-quantifier loops and the remaining single terms (regex, nested alternatives) are not yet emitted here -- **their bodies stay a pass-through scaffold for a later increment**."
- `_gen_alternative`: "regex/nested-alternative term handling, quantified loops … **land in later increments**."
- `_gen_identifier_term_body`: "**Where the Python backend** extracts the rule node directly from the child tuple, the Rust child value is the `{CN}Child` enum…" (three more paragraphs of cross-file rationale)
- `_gen_validate_span_child`: "Where the Python backend uses a dynamic `is_span` probe…" (same pattern)
- Every new private helper includes `gsm2unparser.py:NNNN` line-number cross-references.

"Later increment", "this increment", "a port of `:485`" are LLM implementation-log phrases. They describe what was done during development, not what the function does or what invariants it maintains. The Python line numbers are stale the moment the Python file is reorganized.

Consequence: Code reads as an LLM narrating its own work session. PR reviewers will notice "later increment" language; it also signals that the docstrings will become misleading noise after subsequent increments remove the "deferred" stubs.

Fix: Strip implementation-history phrases. State what each method does and what its invariants are ("emits the Rust body lines for an item with `SUPPRESS` disposition; optional items return a pass-through, required literals re-emit their text, required non-literal terms raise at generation time"). Move cross-backend rationale and line-number cross-references to the commit message or ADR.
