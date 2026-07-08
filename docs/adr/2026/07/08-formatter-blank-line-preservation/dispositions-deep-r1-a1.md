# Deep-review r1 dispositions — formatter blank-line preservation

Base `ef8f727`. Fixes committed on top of `5864ae1`.

## correctness-1 — Python `str.isspace()` vs Rust `char::is_whitespace` divergence

- Disposition: Fixed
- Action: `fltk/unparse/pyrt.py:80-98` — added `_is_unicode_whitespace_only` (and
  `_C0_SEPARATORS = "\x1c\x1d\x1e\x1f"`); `count_whitespace_newlines` now gates the node path on
  it instead of `text.isspace()`. This excludes the four C0 information separators U+001C-U+001F
  that Python's `str.isspace()` accepts but Rust's `char::is_whitespace` (Unicode `White_Space`)
  rejects, so a trivia node classifies as whitespace-only identically in both backends. Rust side
  unchanged (it is already the target semantics), so no regen. Pinned by
  `fltk/unparse/test_pyrt.py:47` (`test_c0_separator_node_child_counts_zero`, `"\n\x1c\n"` -> 0).
- Severity assessment: A grammar whose trivia matches U+001C-U+001F via an explicit character
  class would have produced a byte-level Python/Rust formatting divergence (blank line preserved
  under Python, collapsed under Rust). Unreachable for `\s`-based trivia (incl. gear), but a real
  cross-backend-equivalence violation for exotic char classes; the fix is exact and cheap.

## errhandling-1 — Rust node arm returns 0 for `text_str()==None` while Python raises

- Disposition: Won't-Do
- Action: no change.
- Severity assessment: Reachable only when a node inside a successfully-parsed CST carries an
  invalid source-bearing span — an invariant violation the parser never emits (it sets valid
  spans on every node). Defensive-only; no valid input reaches it.
- Rationale (Won't-Do): The reviewer's two reconciliations both cause active harm, and the state
  flagged is a pre-existing convention, not a new one.
  (1) The identical Python-raises / Rust-returns-0 split already exists on the pre-existing `Span`
  arm: Python's span path routes through `extract_span_text`, which raises on a source-bearing
  invalid span (`pyrt.py:47-49`), while the Rust `Span` arm is `...map(...).unwrap_or(0)`
  (`gsm2unparser_rs.py:1535`). The new node arms merely extend the same convention; they do not
  introduce a divergence class.
  (2) Reviewer option (b) — relax the Python node path to return 0 — would delete a *deliberate*
  fail-loud guard. `extract_span_text`'s raise is documented as intentional (`pyrt.py:43-49`: "A
  source-bearing span whose `text()` returns None indicates invalid byte offsets, not a missing
  source"); swallowing it would trade Python's loud, correlatable diagnostic for silent wrong
  output — the exact silent-blank-drop symptom this change exists to fix — and make the Python
  span path (still raising) and node path (newly silent) mutually inconsistent.
  (3) Reviewer option (a) — make the Rust node arm panic on `None` — is unsafe: `Span::text_str`
  (`crates/fltk-cst-core/src/span.rs:430-439`) returns `None` for *both* a legitimately sourceless
  span and an invalid one, and the design deliberately maps sourceless/empty spans to 0 ("degrades
  to today's behavior, never over-counts", design §2 Component B). Panicking on `None` would crash
  formatting on legitimately sourceless node spans that today correctly count 0. Distinguishing the
  two would require a `has_source`-style capability the Rust `text_str()` path does not expose.
  Fully specifying option (b) also requires stating the choice in the design's "identical in both
  backends" claim, which is frozen and cannot be edited here.

## test-1 — comment-terminator guard test does not discriminate the whitespace-only rule

- Disposition: Fixed
- Action: `fltk/unparse/test_unparser.py:1232-1259`
  (`test_preserve_blanks_custom_trivia_comment_terminator_not_counted`) — changed the input from
  `"foo; // c\nbar;\n"` (one comment, one terminator newline) to `"foo; // c1\n// c2\nbar;\n"`
  (two consecutive comments, two terminator newlines) and reworded the docstring to state why.
  Dropping the whitespace-only guard would now mis-count the two terminators to 2, crossing the
  `>= 2` blank-line threshold and emitting a spurious blank; the corrected input therefore fails
  against the bug and passes against the fix.
- Severity assessment: The old input passed both against the correct code and against the exact
  bug component B fixes (a single stray newline never reaches the `>= 2` threshold), so a future
  regression dropping the guard would slip through green CI. Test integrity, no production impact.

## quality-1 — design-doc terminology / changelog phrasing in test docstrings

- Disposition: Fixed
- Action: reworded docstrings to plain, self-standing descriptions and dropped the ADR-only
  "defect 1a/1b", "component A/B", and "Fails before the fix" vocabulary at:
  `fltk/unparse/test_unparser.py:1169`, `:1202`, `:1233`;
  `tests/test_rust_unparser_generator.py:2036`, `:2056`;
  `fltk/lsp/test_gear_demo.py:94`; and the "unchanged semantics" history note at
  `fltk/unparse/pyrt.py:83`. Grep for the flagged phrases across `fltk/` and `tests/` is now clean.
- Severity assessment: The labels are intelligible only via the ADR; this repo just scrubbed the
  same class of comment (`fe10193`, `f38cdb3`). Maintainability, no runtime impact.

## quality-2 — Rust generator reverse-engineers `has_span` by arithmetic

- Disposition: Fixed
- Action: added `has_span_child(rule_name) -> bool` public wrapper on the CST generator
  (`fltk/fegen/gsm2tree_rs.py:848-856`, over `_child_variants_for_rule`'s second element, parallel
  to `child_class_names_for_rule`) and replaced `num_variants > len(node_child_classes)` at
  `fltk/unparse/gsm2unparser_rs.py:1519` with `self._cst.has_span_child(...)`. Value is identical
  by construction, so generated `unparser.rs` is byte-unchanged (no regen).
- Severity assessment: The subtraction re-encoded another module's variant-counting invariant at
  the consumer; if the child enum grew another variant kind it could silently miscompute `has_span`
  and drop/add a `Span` arm. Latent maintainability hazard, no current defect.

## quality-3 — generated Rust duplicates the node-arm body per variant

- Disposition: TODO(trivia-count-helper)
- Action: added `TODO.md` entry `trivia-count-helper` and a `TODO(trivia-count-helper)` comment at
  `fltk/unparse/gsm2unparser_rs.py` (immediately above the `for cls in node_child_classes` arm
  loop). Deferred rather than done: the design (§2 Component B) prescribes "an arm per node-typed
  variant", and extracting a single emitted helper changes committed generated Rust source
  (requires regen -> `make fix`) and cascades into the exact-arm-body assertions in
  `tests/test_rust_unparser_generator.py` — aggregate work beyond a respond-mode patch.
- Severity assessment: Bounded duplication (N node variants, N=2 in fegen); bloats generated diffs
  downstream but the generator remains a single source of truth. Minor maintainability.

## quality-4 — gear test copy-pastes the format-pipeline setup

- Disposition: Fixed
- Action: extracted module-level `_gear_formatter() -> Callable[[str], str]`
  (`fltk/lsp/test_gear_demo.py:46-66`) that builds the parse->unparse->render pipeline once and
  returns the render callable; `test_formatting_is_idempotent` and
  `test_formatting_preserves_blank_lines_between_items` now both use it. Dropped the redundant
  final reparse assert in the idempotency test (the second `render(once)` already reparses and
  asserts on the output) with a comment noting so.
- Severity assessment: Second copy of the six-line setup in a suite the design expects to grow;
  drift risk plus a full parser+unparser rebuild per copy. Maintainability, no runtime impact.
