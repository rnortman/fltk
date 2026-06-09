## slop-1

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree.py:317` — replaced implicit `# maybe` fall-through with explicit `if method == "maybe":` guard; added `raise ValueError(f"Unknown method: {method!r}")` as unreachable catch-all after the branch.
- Severity assessment: Silent misbehavior if a new method name is added to the quintet — the old code would return the `maybe` body for any unrecognized method name with no diagnostic.

---

## slop-2

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree.py:503-510` — replaced hardcoded `num_import_stmts = 5` with a structural search using `max(i for i, stmt in enumerate(module.body) if isinstance(stmt, ast.ImportFrom | ast.Import) or ...)` to find the last import/`TYPE_CHECKING` block and insert `__all__` at `last_import_idx + 1`.
- Severity assessment: The hardcoded count would silently misplace `__all__` if any import were ever added to the protocol module preamble, producing malformed or mis-ordered generated output with no diagnostic.
