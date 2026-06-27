# Dispositions — prepass round 5

slop-1:
- Disposition: Fixed
- Action: `fltk/unparse/gsm2unparser_rs.py:318` — `_item_spacing_lines` `position`
  param retyped `Literal["before", "after"]`; bare `else` replaced with explicit
  `elif position == "after"` plus an `else: raise ValueError(...)` (msg assigned to a
  var per the file's EM102 convention) at `:344-345`.
- Severity assessment: Low in practice — the method is private and only ever called
  with the string literals `"before"`/`"after"`. The bare-else catch-all was a real
  but latent sloppiness tell; making it explicit costs nothing and surfaces a future
  typo as an error rather than silently emitting after-spacing.

slop-2:
- Disposition: Fixed
- Action: `crates/fltk-unparser-core/src/doc.rs:224,233` — rewrote the `before_spec`
  and `after_spec` rustdoc to lead with the contract and link `[Doc::BeforeSpec]` /
  `[Doc::AfterSpec]` and `resolve_spacing_specs`; dropped the "port of the Python
  unparser's `_create_*_spec`" provenance and the "`Rc` wrapping mirrors group/nest"
  implementation note. These are `pub fn` on a crate consumed out-of-tree, so the docs
  now describe what a caller needs rather than the porting context.
- Severity assessment: Cosmetic — no behavior change. The provenance/impl-detail noise
  in public API docs was a genuine LLM tell; the contract was already present, so the
  trim is a small clarity improvement. `cargo doc` clean (the one remaining warning,
  the pre-existing `concat` ambiguous-link on the untouched `nil()` doc at :158, is out
  of scope).
