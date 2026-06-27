# Dispositions — prepass round 11

Scope notes (`notes-prepass-scope-r11.md`): no findings.

Slop notes (`notes-prepass-slop-r11.md`): slop-1, slop-2.

slop-1:
- Disposition: Fixed
- Action: Rewrote the `.pyi` `import typing` comment at `fltk/unparse/gsm2unparser_rs.py:122-127` to lead with the invariant ("Emit return types as the PEP 604 `X | None` union, never `typing.Optional[...]`: ruff ... does NOT auto-fix the now-unused `import typing` (F401) in a stub file ...") instead of opening with "No `import typing`".
- Severity assessment: Comment-quality only; no behavioral effect. The original framing narrated the removed line rather than stating a regression guard, mildly hurting maintainability.

slop-2:
- Disposition: Fixed
- Action: Reworded the `test_generate_pyi_header` docstring at `tests/test_rust_unparser_generator.py:2260-2264` to fold the absence of `import typing` into the summary sentence, so the negative assertion under test (`assert "import typing" not in pyi`) is stated up front rather than buried as justification.
- Severity assessment: Docstring-quality only; the test logic and assertions are unchanged. Previously a reader scanning docstrings could miss that the test guards against `import typing` reappearing.
