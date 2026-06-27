## slop-1

**File:** `fltk/unparse/gsm2unparser_rs.py` ~line 239

**Quote:**
```python
        # No `import typing`: return types use the PEP 604 `X | None` union (the project's
        # canonical normalized form -- the committed CST `.pyi` carries `| None` post-`ruff
        # --fix`).  Emitting `typing.Optional[...]` would have ruff rewrite it to `| None` and
        # then leave `import typing` unused (F401, which ruff does not auto-fix in a stub), so
        # the committed stub would not pass `make check`.  Emitting the union directly keeps the
        # raw generator output gate-clean for every downstream consumer.
```

**What's wrong:** Opens with `# No 'import typing':` — narrates the removed line rather than stating a maintainable invariant. The framing ("we removed this") reads as an explanation of what changed, not a guard against regression.

**Consequence:** A reviewer who hasn't seen the diff gets a process narrative instead of a rule. The actionable invariant ("emitting `X | None` directly keeps stubs gate-clean because ruff won't auto-fix F401 in stubs") is buried. The comment reads like an LLM justifying a decision after the fact.

**Suggested fix:** Lead with the invariant rather than the absence: `# Emit PEP 604 'X | None', not typing.Optional: ruff rewrites Optional -> | None in fixable code but does NOT auto-fix unused imports (F401) in stub files, so a committed stub with Optional gains a permanent gate failure.`

---

## slop-2

**File:** `tests/test_rust_unparser_generator.py`, `test_generate_pyi_header` docstring

**Quote:**
```python
    """The stub imports __future__ annotations and the protocol module aliased _proto.

    No ``import typing``: return types use the PEP 604 ``X | None`` union directly, so the
    raw stub is gate-clean (a ``typing.Optional`` form would have ruff strip the usage but
    leave ``import typing`` as an un-auto-fixed F401 in the committed stub).
    """
```

**What's wrong:** The first sentence describes only what IS in the stub, but the central assertion now tested is the **absence** of `import typing` (`assert "import typing" not in pyi`). The summary line never mentions the negative assertion; the second paragraph buries it as justification rather than stating the behavior under test.

**Consequence:** A reader scanning test names and docstrings misses that this test guards against `import typing` reappearing. The docstring reads like an explanation of the code change rather than a specification of what the test enforces.

**Suggested fix:** Fold the absence into the first sentence: `The stub header has 'from __future__ import annotations' and 'import {proto} as _proto' but no 'import typing': return types use PEP 604 X | None directly, keeping committed stubs gate-clean (ruff cannot auto-fix F401 in stub files).`
