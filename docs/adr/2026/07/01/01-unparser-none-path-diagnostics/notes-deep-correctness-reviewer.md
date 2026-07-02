# Deep correctness review — unparser-none-path-diagnostics

Commit reviewed: 462cf1c920351b1f83dc20f178001076cc196a9a (base 1d277ce8).

## What was verified (no findings)

- **Site coverage, Rust.** The single emission site (`_gen_non_trivia_rule_processing`)
  produces every `if let Some(trivia_result) = self.unparse__trivia(...)` in the
  committed generated unparsers; in `crates/fegen-rust/src/unparser.rs` there are 17
  such sites and 17 matching `panic!("...refusing to silently drop comments...")`
  else-arms. No orphaned silent path remains.
- **Site 2 remnants.** Zero `span.text()?;` occurrences remain in
  `fltk/unparse/gsm2unparser_rs.py` output paths or in any of the three committed
  generated unparsers (`crates/fegen-rust/src/unparser.rs`,
  `tests/rust_parser_fixture/src/unparser.rs`, `.../unparser_default.rs`) at HEAD.
  (An early grep during this review transiently showed pre-change file contents;
  re-verified against a clean tree at 462cf1c — clean.)
- **`pos` semantics at both panic/raise sites.** Rust: the panic fires before the
  `pos += 1` advance, so the reported position is the Trivia child's index. Python:
  the `current_pos_var` advance is appended to `if_trivia.block` after the whole
  preservable/else tree, so the raise reports the Trivia child index. Confirmed at
  runtime: `test_preserved_trivia_unparse_none_raises` sees `child position 1` for
  children `[a, trivia, b]`.
- **Format-string safety.** `rust_str_lit` returns escaped content without outer
  quotes; rule names and labels are grammar identifiers (no `{`, `}`, `"`), so the
  baked-in panic format strings cannot gain stray format placeholders. The rule-name
  interpolation (`unparse_{rule_lit}`) matches actual generated method names,
  including the `_trivia` → `unparse__trivia` double-underscore case (verified in
  fixture output).
- **Debug-form assertion.** `Span`'s manual `Debug` impl
  (`crates/fltk-cst-core/src/span.rs:295-306`) prints
  `Span { start: .., end: .., has_source: <bool> }`, so the site-2 test's
  `"has_source: false" in msg` assertion is sound, not incidental.
- **Python IIR construction.** `orelse=True` + `if_trivia_success.orelse.expr_stmt(...)`
  follows the established `_make_is_span_check` / `extract_span_text` module-var
  pattern, and the generated module already imports `fltk.unparse.pyrt`
  (`gsm2unparser.py:1848`). Exercised end-to-end by the new runtime test.
- **Python single site.** `unparse__trivia`'s result is consumed at exactly one
  generated site in `gsm2unparser.py` (the `if_trivia_success` at :1321), so the one
  `orelse` covers all WS gaps in all rules.
- **Tests executed during review** (all pass):
  - `uv run pytest fltk/unparse/test_pyrt.py fltk/unparse/test_unparser.py::test_preserved_trivia_unparse_none_raises tests/test_rust_unparser_generator.py` — 155 passed.
  - `uv run pytest tests/test_rust_unparser_none_path_diagnostics.py` — 1 passed.
  - `cargo test --manifest-path crates/fegen-rust/Cargo.toml test_preservable_trivia_unparse_none_panics` — 1 passed (should-panic).
- **Backtracking/loop interaction** (panic instead of `None` inside alternatives and
  quantified `__inner` bodies) matches the design's accepted semantics; the newline
  count `unwrap_or(0)` paths are design-declared out of scope and untouched.

## Findings

### correctness-1

- **File:line:** `fltk/unparse/gsm2unparser_rs.py:1312-1315` (docstring of
  `_gen_non_trivia_rule_processing`)
- **What's wrong:** The docstring bullet still reads: "On failure (`unparse__trivia`
  returns `None`) no separator spec is emitted — a faithful port of Python's
  `if_trivia_success` having no `orelse` (`gsm2unparser.py:1321`); `pos` advances past
  the `Trivia` child either way." All three claims are now false: the emitted code
  `panic!`s in the failure arm (lines 1381-1386 of the same file), the Python
  `if_trivia_success` at `gsm2unparser.py:1321` now *has* an `orelse` (this diff added
  `orelse=True`), and `pos` does not advance on failure (the panic aborts before
  `pos += 1`).
- **Why:** The diff updated the inline comment inside the method body
  (`gsm2unparser_rs.py:1364-1367`) but left the method docstring's preservable-trivia
  bullet untouched. Design change 2 explicitly required: "update the docstring bullet
  that documents the missing-`else` as 'a faithful port of Python's
  `if_trivia_success` having no `orelse`'." The `_gen_regex_term_body` docstring got
  its corresponding update; this one did not.
- **Consequence:** No wrong runtime behavior — the generated code is correct. The
  defect is a code/documentation contradiction inside the changed function: the
  docstring asserts the silent-continue semantics this commit exists to remove, and
  cites a Python line whose behavior this same commit changed. A maintainer reading
  the docstring (the authoritative description of what this method emits) would
  conclude the `None` case is still silently tolerated and that `pos` advancement is
  unconditional, and could reintroduce or "fix" behavior against the wrong contract.
- **Suggested fix:** Rewrite the bullet to match the emitted code, e.g.: "On failure
  (`unparse__trivia` returns `None`) the emitted `else` arm `panic!`s (refusing to
  silently drop comments), mirroring the Python backend's
  `raise_preserved_trivia_failure` in `if_trivia_success.orelse`
  (`gsm2unparser.py:1336-1350`); `pos` advances past the `Trivia` child only on
  success."
