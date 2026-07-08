# Deep-review r1 dispositions — formatter blank-line preservation (rework a2)

Rework round: only the judge-disputed finding (quality-3) is re-dispositioned here.
The six findings the judge accepted (correctness-1, errhandling-1, test-1, quality-1,
quality-2, quality-4) stand as in `dispositions-deep-r1-a1.md` and are not reopened.

Fix committed as `5385e61` (full `make check` precommit gate passed).

## quality-3 — generated Rust duplicates the node-arm body per variant

- Disposition: Fixed
- Action: extracted the whitespace-only newline count into a single emitted helper per Rust
  unparser impl. `fltk/unparse/gsm2unparser_rs.py`:
  - New `_gen_whitespace_node_newlines_method` emits
    `fn _whitespace_node_newlines(t: Option<&str>) -> usize` (the `if let Some(t) = t { if
    !t.is_empty() && t.chars().all(char::is_whitespace) { return t.matches('\n').count(); } } 0`
    body, `#[allow(dead_code)]`), and `_gen_trivia_helper_methods` appends it whenever the trivia
    rule has node-typed variants (returns `None` / omits it for Span-only trivia, so no dead
    helper).
  - The node-arm loop in `_gen_count_newlines_in_trivia_method` now emits
    `count += Self::_whitespace_node_newlines(node.read().span().text_str());` per variant instead
    of the repeated read-lock/whitespace-check/count body; the `TODO(trivia-count-helper)` comment
    is gone and the method docstring updated.
  Regenerated `crates/fegen-rust/src/unparser.rs` (regen → `make fix`; the two `BlockComment` /
  `LineComment` arms now delegate and the helper is emitted once) and `cargo check --features
  python` passes. Test pins in `tests/test_rust_unparser_generator.py` updated: the two
  node-variant tests (`:2007`, `:2035`) now assert delegation + a single helper body via a
  separate `_method_body(src, "_whitespace_node_newlines")` check, the multi-variant test asserts
  exactly two delegating arms, and the Span-only test (`:1990`) asserts the helper is absent.
  `TODO.md` entry `trivia-count-helper` removed.
- Severity assessment: Bounded generated-source duplication (N node variants; N=2 in fegen, N per
  downstream grammar with richer trivia). The whitespace-only counting rule now lives in one place,
  so a future tweak (e.g. the comment-terminator semantics the design flags as an open question) is
  verified once per grammar rather than N times. Semantics unchanged; the match stays exhaustive
  with one arm per variant and no wildcard, and the whitespace-only expression stays pinned in the
  generated source. Maintainability, no runtime behavior change.
