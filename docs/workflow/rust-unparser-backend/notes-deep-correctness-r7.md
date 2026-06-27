# Deep correctness review — batch 7 (trivia/separator processing + PyO3 wrapper)

Commit reviewed: 1fcae0bbe0063b83b1883eb439ababc9da6916d4 (base 72ea1e4252ddea2918b725418716b55e531254b8)

Scope: `fltk/unparse/gsm2unparser_rs.py` (trivia processing + PyO3 bindings),
`crates/fltk-unparser-core/src/{accumulator,doc,lib}.rs`, plus the new tests.

## correctness-1 — non-trivia-rule branch forces a HardLine on a bare newline when `preserve_blanks == 0`, diverging from the Python backend

File: `fltk/unparse/gsm2unparser_rs.py:304-318` (`_gen_non_trivia_rule_processing`, the
`else:` / `preserve_blanks == 0` arm of the no-preservable-content path).

What's wrong: The Rust generator emits, for a non-trivia rule with `preserve_blanks == 0`
when the trivia has no preservable content,

```rust
let newline_count = self._count_newlines_in_trivia(&trivia_node);
if newline_count >= 1 {
    acc = acc.add_trivia(separator_spec(Some(Doc::HardLine { blank_lines: 0 }), None, <req>));
} else {
    acc = acc.add_trivia(separator_spec(<default spacing>, None, <req>));
}
```

The Python non-trivia branch does NOT do this. In `gsm2unparser.py:1392-1399` the
`preserve_blanks == 0` case is unconditional — it emits only the default separator spec and
performs no newline check (the comment is explicit: "preserve_blanks == 0: don't preserve any
whitespace structure, use configured spacing"). `newline_count` is computed at
`gsm2unparser.py:1346` but is referenced only inside the `preserve_blanks > 0` arm.

Why: The two Python branches deliberately differ in their `preserve_blanks == 0` handling:
- trivia-rule branch (`:1216-1242`): newline → `HardLine`, else default (preserve line
  structure for comments living inside `_trivia`).
- non-trivia branch (`:1392-1399`): always default (collapse the inter-token gap).

The Rust port made the non-trivia branch mirror the trivia-rule branch (the docstring at
`gsm2unparser_rs.py:218-220` says "exactly as the trivia-rule branch does … or a
single-newline / default one (preserve_blanks == 0)"), which is the wrong model: the Python
non-trivia branch has no single-newline arm. The trivia-rule branch in this same diff
(`_gen_trivia_rule_processing`, lines 168-182) correctly keeps the newline check, so the
asymmetry that Python encodes was collapsed only on the non-trivia side.

`preserve_blanks` defaults to 0 (`fmt_config.py:59`) and `preserve_node_names` defaults to an
empty set (`fmt_config.py:53`), so with the default `FormatterConfig` every inter-token gap of
an ordinary (non-trivia) rule takes exactly this no-preservable / `preserve_blanks == 0` path.
This is the common case, not an edge case.

Consequence: With the default formatter config, when a Rust-backed unparser reformats source
where two tokens of a non-trivia rule were separated by whitespace containing a newline (but no
preserved comment), the Rust backend emits a forced `HardLine` (keeping the line break), while
the Python backend emits the configured default separator (typically collapsing to a space /
softline / nothing). The two backends produce different formatted text for the same CST under
the same config — a direct violation of the stated cross-backend behavioral-equivalence goal,
affecting downstream consumers in the default configuration. The new test
`test_non_trivia_rule_emits_trivia_preservation_branch` (test file lines 1794-1800) asserts the
diverging behavior (`if newline_count >= 1 {` + `separator_spec(Some(Doc::HardLine ...`), so the
bug is locked in rather than caught.

Suggested fix: In the `preserve_blanks == 0` arm of `_gen_non_trivia_rule_processing`, emit only
the default separator spec (no `newline_count` read, no `>= 1` HardLine branch), matching
`gsm2unparser.py:1392-1399`. Keep the `preserve_blanks > 0` arm as-is. Update the test to assert
the collapsed (default-only) output for the non-trivia `preserve_blanks == 0` path.

## Items checked and found correct

- Trivia-rule branch (`_gen_trivia_rule_processing`): bounds/else structure, the
  `WS_REQUIRED` `return None` arms (not-whitespace and OOB) vs `WS_ALLOWED` no-else, the
  `preserve_blanks > 0` (>=2 / >=1 / default) vs `preserve_blanks == 0` (>=1 / default)
  ladder, and the `(None, Span(span))` unlabeled-whitespace match all faithfully port
  `gsm2unparser.py:1103-1263`. Bracket nesting balances.
- Non-trivia branch `pos += 1` placement (only in the `Trivia` arm, not the not-trivia /
  OOB arms), the `!acc.last_was_trivia()` guard, the match on `.1` (value only, no label
  check — correct parity), and the `num_variants > 1` gating of the `_ =>` catch-all all
  match the Python branch.
- `_has_preservable_trivia` / `_count_newlines_in_trivia` emission: `sorted()` over
  `preserve_node_names` affects only OR-pattern arm order (no behavior change); first-match
  semantics, the drop-unknown-name filtering, and the `num_variants > 1` catch-all gating are
  consistent with the Python isinstance loop.
- PyO3 wrapper (`_gen_python_bindings`): `#[pyclass(name = "Unparser")]` preserves the public
  symbol; `RendererConfig { indent_width, max_width }` matches the two public fields in
  `render.rs`; `resolve_spacing_specs` and `Renderer::new(cfg).render(&resolved)` type-check
  (Doc-by-value, `&Doc`); `node.shared().read()` matches the generated `pub fn shared(&self) ->
  &Shared<…>` handle (`gsm2tree_rs.py:1230`) and the established `&guard` deref-coercion pattern;
  `r.accumulator.doc()` matches the public `UnparseResult.accumulator` field. Signature/param
  order (`max_width`, `indent_width`) is consistent between the `#[pyo3(signature=…)]` and the fn
  params.
- Rust core additions: `DocAccumulator::last_was_trivia()` returns the field; `separator_spec`
  wraps both optional fields via `.map(Rc::new)`, matching `Doc::SeparatorSpec { spacing:
  Option<Rc<Doc>>, preserved_trivia: Option<Rc<Doc>>, required: bool }`.
