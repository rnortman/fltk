## slop-1

**File:line:** `fltk/unparse/gsm2unparser_rs.py:365`

**Quote:**
```python
lines.append("        // Term handling (extract/validate child + dispatch) is emitted later.")
```

**What's wrong:** This embeds a narrative LLM writing-process comment into the *generated Rust output*. The phrase "is emitted later" refers to the incremental development plan, not anything about the code's runtime behavior. A reader of the generated `.rs` file gets a comment that describes when the author planned to write more code — meaningless once the "later increment" ships, and actively misleading if the comment survives.

**Consequence:** Generated code ships with a comment that reads like an author's note to themselves, not documentation. Any downstream consumer who reads the generated file sees scaffolding prose instead of intent. Worse, if the comment is not deleted when the next increment fills in the real body, it becomes a lie.

**Suggested fix:** Remove the comment or replace it with a forward-looking `// TODO(...)` that references the tracking slug. Better still: just leave the body as the bare pass-through line — the function name (`__item{N}`) already communicates what the method is for; the reader can see it's a stub by looking at the body.

---

## slop-2

**File:line:** `fltk/unparse/gsm2unparser_rs.py:354–367` (`_gen_item_method` docstring)

**Quote:**
```
The real body — child extraction/validation and term dispatch
(``_extract_and_validate_nonsequence_child`` / ``gen_term_unparser``), plus
quantified-loop and suppressed-item handling — is emitted by a later increment.
Until then the method passes its accumulator and position through unchanged.
```

**What's wrong:** The docstring describes the development schedule ("is emitted by a later increment", "Until then") rather than what the function does. Docstrings belong to the code and live forever; development-phase narration belongs in the commit message, PR description, or implementation log.

**Consequence:** After the next increment replaces the pass-through body, this docstring becomes a false claim ("the method passes … through unchanged"). Any reviewer or future maintainer who reads it gets wrong information without touching the code being described.

**Suggested fix:** Trim to describe the function's *invariant contract*: what the signature means, what the emitted method is responsible for. Drop all references to "later increment" and "until then."

---

## slop-3

**File:line:** `fltk/unparse/gsm2unparser_rs.py:255–266` (RULE_START loop) and `269–277` (RULE_END loop)

**Quote (RULE_START):**
```python
for op in start_anchor.operations:
    if op.operation_type == OperationType.GROUP_BEGIN:
        ...
    elif op.operation_type == OperationType.NEST_BEGIN:
        ...
    elif op.operation_type == OperationType.JOIN_BEGIN:
        ...
    # no else
```

**What's wrong:** Unrecognized operation types are silently dropped. If a `.fltkfmt` config puts a `GROUP_END` or `NEST_END` in a RULE_START anchor (misconfiguration), or if a new `OperationType` is added later, both loops consume the operation and emit nothing. There is no `else: raise` and no warning.

**Consequence:** A misconfigured or future-extended anchor silently produces a Rust unparser that ignores part of its formatting config. The discrepancy between the Python and Rust backends' behavior would be invisible at generation time and only manifest at runtime in incorrect formatting output. The JOIN_BEGIN branch already shows the pattern for what "unexpected input" should look like (`raise RuntimeError`); the same treatment should apply to the unrecognized-type case.

**Suggested fix:** Add `else: raise RuntimeError(f"Unhandled operation type in RULE_START anchor: {op.operation_type}")` (and equivalent for RULE_END) after the final `elif` in each loop.
