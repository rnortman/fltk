# Judge verdict — design review

Phase: design. Doc: `./design.md`. Base `49e9701`. Round 1.
Notes: 1 reviewer file; 2 findings (design-1, design-2). Both dispositioned Fixed.

(Design phase — no Added-TODOs walk.)

## Other findings walk

### design-1 — Fixed
Claim: §2.2 treated both construction sites symmetrically as "change the module string,"
but the `_source_text` site is `iir.Construct.make(self.SourceTextType, text=..., filename=...)`,
not a `VarByName`; a `Construct`'s emitted class name resolves through the type registry, which
§2.5 freezes to the `span` module — so there is no string to swap. Consequence: an implementer
following §2.2+§2.5 literally has no described way to retarget the SourceText construction; the
tempting shortcut (re-register the entry) violates the §2.5 frozen-registry invariant and, if
generalized to `Span`, churns the public CST child span annotations CLAUDE.md forbids.

Source check (ground truth):
- `_source_text` is `iir.Construct.make(self.SourceTextType, text=..., filename=...)` —
  `gsm2parser.py:113-123`. Confirmed.
- `Construct` resolves its class name through the registry — `compiler.py:312-315`
  (`iir_type_to_py_constructor(expr.typ.root_type())`) → `reg.py` `import_name(concrete=True)`
  builds `<module>.<name>` from the registered module. With the entry frozen to
  `("fltk","fegen","pyrt","span")` (`gsm2parser.py:78-84`), the emitted name is always
  `fltk.fegen.pyrt.span.SourceText`. Confirmed — the contradiction is real.
- `_make_span_expr` by contrast builds a `VarByName` from a dotted string (`gsm2parser.py:270-281`),
  so the first bullet's string-swap claim is genuinely correct only for the Span site.

Fix check: §2.2 (lines 134-161) now states the `_source_text` site needs a **structural** change
and prescribes replacing the `Construct` with
`iir.MethodAccess("SourceText", iir.VarByName(name=<module>)).call(text=..., filename=...)`,
leaving the registry untouched; §2.5 (lines 215-219) adds that the registry is retargeted only via
emitting IIR nodes, never by editing the registry. Verified the prescribed node compiles correctly:
`MethodAccess.call(**kwargs)` exists (`model.py:391`); the `MethodCall` branch emits
`<bound_to>.<member>(<args>)` (`compiler.py:305-309`) with keyword args via `_format_args`
(`compiler.py:285-289`) → `<module>.SourceText(text=..., filename=...)`, bypassing the registry.
This is the same proven pattern `_make_span_expr` already uses (`gsm2parser.py:277`).
Assessment: finding is real and well-scoped; the rewrite addresses the consequence with a
source-correct, registry-independent mechanism. Accept Fixed.

### design-2 — Fixed
Claim: §2.4 said "add `fltk._native` to `parser_globals`," but the emitted name `fltk._native.Span`
resolves as `getattr(fltk, "_native")` off the already-bound `parser_globals["fltk"]` package
object — a dict *key* `"fltk._native"` is never consulted, and the `_native` attribute exists only
after an explicit import. Consequence: `AttributeError: module 'fltk' has no attribute '_native'`
in any process where `_native` was not already imported by another path. Reviewer self-flags low
severity (Rust CST load may import `_native` incidentally).

Source check (ground truth):
- `parser_globals["fltk"] = fltk` — `plumbing.py:270`. Confirmed.
- `fltk._native` is a compiled submodule: dir contains only `__init__.pyi`, no `__init__.py`, so
  `getattr(fltk, "_native")` requires an explicit import to have run. Confirmed. Adding a dict key
  does not create the package attribute. The consequence holds.

Fix check: §2.4 (lines 186-208) now specifies **execute `import fltk._native` on the native path**
(after which `parser_globals["fltk"]` suffices) and explicitly explains why inserting a
`"fltk._native"` key does not work; edge case 6 (lines 262-268) is updated to match. The note that
the design must not rely on the incidental Rust-CST-load import ordering is the correct defensive
call.
Assessment: real finding (low severity, as the reviewer concedes); the rewrite is source-correct
and removes the incidental-ordering dependency. Accept Fixed.

## Approved

2 findings: 2 Fixed verified (both fixes present in the design and technically correct against
`gsm2parser.py`, `compiler.py`, `model.py`, `reg.py`, `plumbing.py`, and the `fltk/_native` layout).

---

## Verdict: APPROVED

Both dispositions sound. Each finding states a real consequence justified by source; each Fixed
rewrite is present in `design.md` and verified technically correct (design-1: registry-independent
`MethodAccess(...).call(...)` mirroring the proven `_make_span_expr` pattern; design-2: explicit
`import fltk._native` rather than a dict key). Nothing disputed.
