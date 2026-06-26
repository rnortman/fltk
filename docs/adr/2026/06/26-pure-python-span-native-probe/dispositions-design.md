# Dispositions — design review (round 1)

Design: `./design.md`
Reviewer notes: `./notes-design-design-reviewer.md`
Base commit: `49e9701e927d1403065f902b99d54acd7c129e41`

## design-1

- Disposition: Fixed
- Action: Rewrote §2.2's `_source_text` bullet and added a clarifying sentence to §2.5's first
  bullet. The design now states that the `_source_text` site needs a **structural** change, not a
  string swap: it is currently `iir.Construct.make(self.SourceTextType, text=..., filename=...)`
  (`gsm2parser.py:113-123`), and the compiler resolves a `Construct`'s emitted class name through
  the registry (`compiler.py:312-315` → `iir_type_to_py_constructor` → `import_name(concrete=True)`,
  `reg.py:26-29`), which §2.5 freezes to the `span` module. The fix replaces the `Construct` node
  with a registry-independent, module-qualified call expression mirroring `_make_span_expr`:
  `iir.MethodAccess("SourceText", iir.VarByName(name=<construction module>)).call(text=..., filename=...)`,
  which the compiler's `MethodCall` branch (`compiler.py:305-309`, `_format_args` at `:285-289`,
  verified to handle keyword args via `MethodAccess.call(**kwargs)`, `model.py:391`) emits as
  `<module>.SourceText(...)` without touching the registry. §2.5 now explains that the registry is
  retargeted only via the emitting IIR nodes, never by editing the registry.
- Severity assessment: Without this, an implementer following §2.2+§2.5 literally has no described
  way to retarget the SourceText construction; the tempting shortcut (re-registering `SourceTextType`)
  violates the §2.5 frozen-registry invariant and, if generalized to `Span`, churns the public CST
  child span annotations CLAUDE.md forbids. The implementer would either stall on the contradiction
  or break the public annotation surface.

## design-2

- Disposition: Fixed
- Action: Rewrote §2.4's first bullet and edge case 6's tail. The design now specifies **execute
  `import fltk._native` on the native path** (after which the existing `parser_globals["fltk"] = fltk`
  at `plumbing.py:270` suffices), and explicitly states that inserting a `"fltk._native"` dict key
  does NOT work because `fltk._native.Span` resolves as `getattr(fltk, "_native")`, never as a
  lookup of a global literally named `"fltk._native"` — and `_native` is a compiled submodule
  (`fltk/_native/__init__.pyi:1-7`) whose attribute exists only after an explicit import. The note
  that the Rust CST load may import `_native` incidentally is retained, but the design no longer
  relies on that ordering.
- Severity assessment: If the implementer literally "adds it to parser_globals" rather than running
  `import fltk._native`, the native/hybrid-path parser raises
  `AttributeError: module 'fltk' has no attribute '_native'` at the first construction site in any
  process where `_native` was not already imported by another path. Low severity (the Rust CST load
  often imports `_native` as a side effect) but the design should not depend on incidental ordering.
