# Deep security review — pure-python-span-native-probe

Commit reviewed: ab38ec777920f4761f124e56b3cedc995acee46a (base 49e9701e927d1403065f902b99d54acd7c129e41)
Scope: changed code under fltk/, src/, tests/. (No src/ or crates/ Rust changes in this range.)

No findings.

Rationale (no untrusted trust boundary crossed, no new attack surface):
- The change is type-annotation / backend-isolation plumbing: span registry repointed to
  `SpanProtocol`, generated annotations switched off `fltk._native`, lazy `__future__` imports,
  and an `is_span` dual-backend runtime guard. None of this introduces injection, auth, path,
  SSRF, deserialization, crypto, or secret-handling surface.
- `fltk/plumbing.py` REMOVES the hybrid path, including `_load_rust_cst_classes` which called
  `importlib.import_module(module_name)` — a documented arbitrary-code-execution sink if fed an
  untrusted module name. Removing it shrinks attack surface; net security improvement.
- The remaining `exec(compile(...))` calls in `generate_parser` (plumbing.py) are pre-existing and
  execute generator-produced AST derived from grammar text, not raw untrusted strings; the diff
  changes only the surrounding control flow (drops the rust-cst branch, prepends a `__future__`
  import node), not the trust model of the exec. Not introduced/altered by this change in a
  security-relevant way.
- `fltk/unparse/pyrt.py::is_span` resolves the native type via `sys.modules.get("fltk._native")` +
  `getattr`; no import-by-name of attacker data, no eval, no reflection on untrusted input.
- `fltk/fegen/pyrt/span.py` only drops a `warnings.warn` call; no behavior reachable by an attacker.
</content>
</invoke>
