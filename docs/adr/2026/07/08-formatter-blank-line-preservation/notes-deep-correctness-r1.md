# Correctness review — formatter blank-line preservation (r1)

Reviewed: `ef8f727..5864ae1`

Verified clean (traced against surrounding source, not just the diff):

- Component A (`fmt_config.py:505-513`): in-place mutation is symmetric with
  `_process_preserve_blanks_statement`; no other site replaces `config.trivia_config`
  (checked all assignment sites), so field ownership / order independence holds.
- `pyrt.count_whitespace_newlines`: span path unchanged (`count_span_newlines`); node path
  handles both backends (`.span` is a dataclass field on Python nodes, a pyo3 `#[getter]` on
  Rust handles, `gsm2tree_rs.py:1341-1346`); `UnknownSpan` (`Span(-1,-1)`, sourceless) falls
  through `extract_span_text` to `terminals[-1:-1] == ""` → `isspace()` false → 0, so
  sentinel spans never over-count. `""` correctly contributes 0, matching Rust's
  `!t.is_empty()` guard.
- Python generator loop (`gsm2unparser.py:1023-1062`): bounds `idx < len(children)`,
  increment, and accumulation all correct; passes `children[idx][1]` (the value, not the
  tuple) to the helper; `self.terminals` and `_get_pyrt_module` both exist and are used the
  same way as the neighboring `_count_newlines` method.
- Rust generator (`gsm2unparser_rs.py:1516-1560`): `has_span = num_variants >
  len(node_child_classes)` is exactly the `has_span` boolean from
  `_child_variants_for_rule` (`gsm2tree_rs.py:826-846`), and the per-class arms iterate the
  same list the child-enum emission iterates, so the match is exhaustive with no duplicates
  by construction. Brace balance verified in both `has_span` branches. `cargo check` on the
  regenerated `crates/fegen-rust/src/unparser.rs` passes; the Span-only fixture unparsers
  (`tests/rust_parser_fixture/src/unparser*.rs`) are byte-identical under the new emission,
  confirmed by inspection.
- fegen regen semantics: `BlockComment`/`LineComment` span text can never be all-whitespace
  (starts with `//`/`/*`), so the regenerated fegen counter is behaviorally identical to the
  old Span-only version — consistent with `test_fltkfmt_parity.py` staying green (ran it:
  16 passed).
- Ran the new/changed suites: `test_fmt_config.py`, `test_pyrt.py`, `test_unparser.py`,
  `test_rust_unparser_generator.py`, `test_gear_demo.py` — all pass.

## correctness-1

- **File:line:** `fltk/unparse/pyrt.py:96` vs `fltk/unparse/gsm2unparser_rs.py:1545` (and
  the regenerated `crates/fegen-rust/src/unparser.rs:40,48`).
- **What:** The two backends' whitespace-only gates use different whitespace classifiers.
  Python uses `str.isspace()`; Rust uses `char::is_whitespace` (Unicode `White_Space`
  property). These disagree on U+001C–U+001F (FS/GS/RS/US): `"\n\x1c\n".isspace()` is
  `True` in Python, but `'\u{1c}'.is_whitespace()` is `false` in Rust.
- **Why:** `str.isspace()` is true for bidirectional classes WS/B/S plus category Zs, a
  strict superset of `White_Space` on those four control characters. The design
  (§2 Component B) specifies the Rust check as "matching the Python helper", but the
  classifiers are not identical.
- **Consequence:** A grammar whose trivia rule matches U+001C–U+001F via an explicit
  character class (e.g. `/[ \t\n\x1c]+/`, which both regex engines honor identically, so
  the parsers do NOT diverge) produces a trivia node like `"\n\x1c\n"` that counts 2
  newlines (blank-line evidence → `HardLine(blank_lines=N)`) under the Python formatter but
  0 under the Rust formatter — a byte-level cross-backend formatting divergence, violating
  the Python/Rust behavioral-equivalence requirement (CLAUDE.md; design §3). Unreachable
  for `\s`-based trivia rules (the common case, incl. gear) because the regex layers
  diverge identically upstream; only explicit character classes expose it.
- **Suggested fix:** Pick one classifier and mirror it exactly. Cheapest: in
  `count_whitespace_newlines`, replace `text.isspace()` with
  `text and all(c.isspace() and c not in "\x1c\x1d\x1e\x1f" for c in text)` — or, cleaner,
  define the gate as Unicode `White_Space` on both sides (Python:
  `all(unicodedata... )` helper or an explicit frozenset of `White_Space` chars) and add a
  parity comment citing the counterpart line, as the rest of `gsm2unparser_rs.py` does.
  Alternatively, document the divergence as accepted for exotic control characters.

No other findings.
