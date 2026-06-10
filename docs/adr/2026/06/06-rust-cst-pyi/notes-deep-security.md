# Security review — rust-cst-pyi (46a6639..c78a014)

No findings.

Vectors examined and ruled out:
- Grammar-derived identifiers into generated `.pyi`: `RustCstGenerator.__init__` validates all rule names and item labels against `_IDENTIFIER_RE` before emission (`fltk/fegen/gsm2tree_rs.py:52-67`); `generate_pyi` runs on the same instance, so the existing build-time code-injection guard covers the new emitter.
- `--protocol-module` interpolated unvalidated into stub text (`import {protocol_module} as _proto`): value is the operator's own CLI argument, and `.pyi` files are never executed (CPython ignores them; pyright only parses) — no execution or privilege consequence.
- `--pyi-output` / default stub path writes (`genparser.py`): operator-specified paths in a local dev CLI; no untrusted input reaches the path.
- `fltk/_native/` stub directory shadowing the compiled extension: availability footgun only, not attacker-controllable; guarded by header comment and runtime tests.
- Tests instantiate runtime PyO3 classes and `ast.parse` the committed stub — no untrusted data flow.
