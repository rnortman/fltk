# Dispositions — prepass round 1

slop-1:
- Disposition: Fixed
- Action: Rewrote the low-value doc comments on the helper constructors in
  `crates/fltk-unparser-core/src/doc.rs`: `text` (line 132), `nil` (line 157),
  and `nest` (line 172) now describe semantics the identifier/signature does not
  already state. `line` was acceptable per the reviewer and left unchanged.
- Severity assessment: Cosmetic. The docstrings were accurate but restated the
  symbol name; the new wording carries information (verbatim/no-reindent for
  `text`, identity-for-concat for `nil`, break-conditional indentation for `nest`).

slop-2:
- Disposition: Fixed
- Action: Added an explanatory comment to `resolve_spacing` at
  `crates/fltk-unparser-core/src/resolve.rs:621-627` documenting that the
  `assert!(sep_spacing.is_some())` is a faithful port of the Python
  `_resolve_spacing` (`resolve_specs.py:545-560`), which fails the same way and
  also ignores `required`. Did NOT change the guard to consult `required`.
- Severity assessment: The reviewer's "latent crash / asymmetry" concern is real
  as a clarity matter, but the suggested behavioral fix (guard on `required`)
  would be actively wrong: the Python backend's `_resolve_spacing` raises
  `RuntimeError` when the separator has neither trivia nor spacing, regardless of
  `required`, and the 2-element-vs-3-element asymmetry exists identically in
  Python. resolve.rs is a literal port (design §2.1, §3) and cross-backend
  rendered-string parity is the explicit design mandate; adding a `required`
  guard only on the Rust side would diverge from Python and break parity. The
  combination is reachable in both backends or neither — it cannot be a
  Rust-only crash. The comment resolves the reviewer's doubt without introducing
  a divergence.
