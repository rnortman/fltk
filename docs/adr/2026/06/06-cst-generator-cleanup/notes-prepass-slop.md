## slop-1

**File:** `fltk/fegen/gsm2tree.py` — `concrete_body_for` closure (~line 282)

**Quote:**
```python
            # maybe
            return [
```

**What's wrong:** The comment `# maybe` is the method-name sentinel for the final branch of `concrete_body_for`. It looks like a leftover thinking-aloud fragment rather than a real comment — there is no condition guarding it, and the comment communicates nothing the reader cannot see from context. Compare the four guarded branches above it (each with an explicit `if method == "...":`); the final case falls through with just `# maybe` as its only label. A reader momentarily wonders whether this is a valid catch-all or an incomplete branch.

**Consequence:** Reads like LLM self-narration ("# maybe" = "this is the maybe case"), which signals unreviewed output. Would draw an immediate question in code review.

**Fix:** Either add an explicit guard (`if method == "maybe":`) with a fallthrough `raise ValueError(f"Unknown method: {method!r}")` after it, or at minimum change the comment to `# method == "maybe"` and add the unreachable raise. The raise is the right fix: if a new method name is passed that isn't one of the five known values, the current code silently returns the `maybe` body, producing a subtly broken generated class with no diagnostic.

---

## slop-2

**File:** `fltk/fegen/gsm2tree.py` — `gen_protocol_module`, ~line 358

**Quote:**
```python
        # Insert after imports (5 stmts: from __future__, enum, typing, terminalsrc, TYPE_CHECKING if-block)
        # so __all__ appears near the top of the module, not at the end.
        num_import_stmts = 5
```

**What's wrong:** The magic number `5` is explained only in an adjacent comment that lists the specific stmts assumed to be present. The count will silently go wrong if the import block changes (e.g., a new import is added to the module preamble). The comment documents the fragility rather than fixing it; a named constant without the structural coupling adds nothing.

**Consequence:** The comment is load-bearing documentation for a fragile assumption, which is a slop tell — the right answer is to derive the position structurally (e.g., find the last import/`TYPE_CHECKING` stmt and insert after it) rather than hardcode 5. As written it is a maintenance trap that won't break loudly — `__all__` will silently end up in the wrong position.

**Fix:** Replace the hardcoded index with a positional search: find the index of the last `ast.ImportFrom` / `ast.If` (the `TYPE_CHECKING` block) in `module.body` and insert at `last_import_idx + 1`.

---

No other slop findings.
