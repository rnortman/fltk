# Deep security review — rust-unparser-backend batch 9

Commit reviewed: bb96d0e78ae563c4cbad898225c16be02b4baba5 (base 90ffae8c255e7bb01fcb6a180e4225ee10bcad44)

Scope: PyO3 Doc exposure (`PyDoc` + additive `unparse_*_doc`), `.pyi` stub emission
(`generate_pyi` + genparser CLI flags), regenerated fixture unparser/spacing output.

No findings.

Trust-boundary notes (reviewed, no issue):
- `unparse_*_doc` reuses the existing `node.shared().read()` guard pattern; the read
  guard is a local dropped on return. `resolve_spacing_specs` yields an owned (Rc-based)
  `Doc`, so `PyDoc` owns its tree with no borrow of the CST — no UAF / dangling ref.
- `PyDoc` is `#[pyclass(unsendable)]`, correctly matching the Rc-based core `Doc`
  (cross-thread use panics safely rather than risking UB).
- `PyDoc::render` takes untrusted `usize` width/indent from Python but calls the same
  `Renderer`/`RendererConfig` already reachable via the pre-existing `unparse_{rule}`
  string methods (same defaults/types) — no new attack surface; out-of-range Python ints
  raise a Python exception, not a panic.
- `__repr__` Debug-formats the resolved Doc derived from caller-supplied source spans;
  the caller already owns that data — no cross-boundary leak.
- `--protocol-module` / `--pyi-output` are build-time CLI args (developer-controlled),
  not runtime untrusted input; interpolation into the `.pyi` is not a runtime boundary.
