# Dispositions — deep review round 3 (rust-unparser-backend)

Commit reviewed: e6a682cb883db43d6df2cc7215cb982121934254
Base: d622ff7905362ebc71b3f232cae8b801db9bdd0f

Reviewers with no findings: security (no findings), efficiency (no findings).

---

correctness-1:
- Disposition: Fixed
- Action: `fltk/unparse/gsm2unparser_rs.py:_doc_to_rust_expr` (now ~341, ~344) — changed
  the emitted `Doc::text("...")` / `Doc::concat(vec![...])` to the crate-qualified free
  functions `fltk_unparser_core::text("...")` / `fltk_unparser_core::concat(vec![...])`.
  `text`/`concat` are free module functions in `fltk-unparser-core` (doc.rs:134, :200;
  `pub use` in lib.rs:22-24), not associated functions on `Doc` (the only `impl Doc` is
  `Drop`), so `Doc::text`/`Doc::concat` do not resolve (E0599). Crate-qualified emission
  mirrors the Python backend's module-qualified `combinators.text(...)`/`concat(...)`
  (`gsm2unparser.py:419,423`) and matches the design header `use` set (design §2.2), which
  intentionally does not import `text`/`concat`; this avoids unused-import warnings in
  generated files that never emit a separator. Updated the three string-asserting tests
  (`test_doc_to_rust_expr_text_is_escaped`, `_concat_recurses`, `_nested_concat`).
- Severity assessment: High. Any FormatterConfig routing a Text/Concat separator (e.g.
  `join ... by ","`) through `_doc_to_rust_expr` emitted uncompilable Rust and broke
  cross-backend parity (Python compiled, Rust did not). Latent until the design's
  join-from-to fixture (§2.6) lands, but a genuine bug.

---

errhandling-3:
- Disposition: Fixed
- Action: `fltk/unparse/gsm2unparser_rs.py:_gen_rule_entry` (~203) — wrapped the JOIN_BEGIN
  `self._doc_to_rust_expr(op.separator)` call in `try/except ValueError`, re-raising as
  `f"Rule {rule_name!r} JOIN_BEGIN separator uses unsupported Doc type: {exc}"` with
  `from exc`. Added `test_join_begin_unsupported_separator_reports_rule_context`. This is a
  purely additive diagnostic improvement: both backends still reject the same configs with
  a ValueError (no behavioral/parity change), so the Python backend's bare-ValueError at
  `gsm2unparser.py:240` is not a parity constraint here — only the message text differs.
- Severity assessment: Low. A misconfigured separator already errored at generation time;
  the change only adds the offending rule name to the message, easing diagnosis.

---

test-1:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_generator.py` — added
  `test_rule_level_join_anchor_emits_push_pop` (JOIN_BEGIN with a Text separator →
  `acc.push_join(fltk_unparser_core::text(","))`, paired JOIN_END → `.pop_join()`) and
  `test_join_begin_without_separator_raises` (separator=None → RuntimeError during
  `generate()`). The previously-untested rule-level JOIN_BEGIN/JOIN_END path and its
  explicit None-separator guard are now covered.
- Severity assessment: Medium. The only explicit error raise in the increment, plus the
  whole join-anchor branch, were invisible to tests; a regression would have gone
  undetected until the join fixture compiled.

---

test-2:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_generator.py` — added
  `test_empty_alternative_body_is_passthrough`, calling `_gen_alternative_body` directly
  with `gsm.Items(items=[], sep_after=[])` and asserting the body is the pass-through
  return with no `let mut pos`/`let mut acc` threading preamble. Added `from fltk.fegen
  import gsm`.
- Severity assessment: Low-Medium. The degenerate empty-alternative branch diverges most
  from the normal path and was uncovered; the targeted test guards it without needing a
  grammar that survives full trivia/CST processing with an empty alternative.

---

test-3:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_generator.py` — added
  `test_nest_begin_without_indent_defaults_to_one`: a `FormatOperation(NEST_BEGIN)` with no
  explicit indent now asserts `push_nest(1)`, covering the `op.indent or 1` fallback.
- Severity assessment: Low. The fallback is unreachable through `.fltkfmt` (indent is
  always supplied) but reachable via direct FormatOperation construction; now covered.

---

reuse-1:
- Disposition: Fixed
- Action: `fltk/unparse/gsm2unparser_rs.py:141` (`_class_name`) — replaced
  `self._cst._py_gen.class_name_for_rule_node(rule_name)` with the public wrapper
  `self._cst.class_name_for_rule(rule_name)` (gsm2tree_rs.py:779). The wrapper exists
  precisely to insulate callers from the `_py_gen` indirection; design §2.2 itself names
  `class_name_for_rule` as the helper to reuse. Output is byte-identical (the wrapper
  delegates to the same `class_name_for_rule_node`).
- Severity assessment: Low. Maintainability: avoids hardcoding the private delegation path
  in a new third callsite.

---

quality-1:
- Disposition: Fixed
- Action: Same change as reuse-1 (`_class_name` now uses `self._cst.class_name_for_rule`).
  The reviewer additionally asked to fix the pre-existing `RustParserGenerator._class_name`
  (gsm2parser_rs.py:231) and its direct use at :171. That is left out of scope: those
  lines belong to the parser backend, which this design does not modify (CLAUDE.md "Touch
  only code the design describes"); fixing them is an unrelated cleanup of pre-existing
  code and not part of the rust-unparser-backend diff. The new code — the actual subject
  of this finding — is fixed.
- Severity assessment: Low. New-code intent is now correct and self-documenting; the
  pre-existing parser-backend copy is benign (works, just bypasses the wrapper) and
  predates this work.

---

errhandling-1:
- Disposition: Won't-Do
- Action: no change.
- Severity assessment: Low. Reachable only via hand-constructed FormatterConfig (the
  `.fltkfmt` parser only ever routes matching BEGIN/END types to these anchors); a
  misconfig silently drops the op rather than raising.
- Rationale (Won't-Do): The Python backend has the byte-identical `if/elif/elif` chains
  with no `else` for both RULE_START and RULE_END (`gsm2unparser.py:224-243`) and silently
  drops unexpected operation types in exactly the same way. The design mandates the Rust
  backend mirror the Python backend, and §2.2 explicitly forbids Rust-only divergence
  ("would have to be a deliberate both-backends change, not an incidental Rust-only
  superset"). Adding a `raise` to the Rust generator alone would make the two backends
  behave differently on the same FormatterConfig — precisely the cross-backend divergence
  CLAUDE.md ("cross-backend behavioral equivalence") and the design forbid. A defensive
  raise has merit but must be a deliberate both-backends change, which is out of scope for
  this design.

---

errhandling-2:
- Disposition: Won't-Do
- Action: no change.
- Severity assessment: Low. `FormatOperation(NEST_BEGIN, indent=0)` emits `push_nest(1)`
  via `0 or 1`. A user writing `nest(0)` in `.fltkfmt` would hit this, but `nest(0)` is
  semantically degenerate.
- Rationale (Won't-Do): The Python backend uses the identical `op.indent or 1`
  (`gsm2unparser.py:233`), so it produces `push_nest(1)` for `indent=0` too. Changing the
  Rust backend to `op.indent if op.indent is not None else 1` would make `nest(0)` emit
  `push_nest(0)` in Rust but `push_nest(1)` in Python from the same `.fltkfmt` input — a
  cross-backend divergence the design and CLAUDE.md forbid. If `indent=0` should be
  honored, that is a both-backends change (out of scope here), not a Rust-only fix.
