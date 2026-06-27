# Dispositions — deep review (rust-fltkfmt increments 1-3), round 1

Base `61fc5e8`, reviewed HEAD `1b48755`. Fixes committed on top.

Note on the shared test failure: `correctness-1`, `test-1`, and `quality-1` are the same
defect (the two stale generator tests). All three are dispositioned Fixed by the single
test update; the suite is green (152 passed in `tests/test_rust_unparser_generator.py`).

---

errhandling-1:
- Disposition: TODO(unparser-none-path-diagnostics)
- Action: TODO comment added at `fltk/unparse/gsm2unparser_rs.py` (the
  `if self._has_preservable_trivia(...)` / `if let Some(trivia_result)` block, ~line 1346)
  plus a `TODO.md` entry. No generated output changed.
- Severity assessment: Real observability gap — a sourceless/mislabeled trivia span makes
  `unparse__trivia` return `None`, which the missing `else` arm silently discards, dropping a
  comment from formatted output with no signal. But this is a pre-existing pattern in the Rust
  unparser generator (landed in 6f975eb, before this feature), it is not in the fltkfmt design
  scope, and in the actual `fltkfmt` pipeline (`Parser::new(src, filename, true)`) every span
  carries source, so the `None` branch is an invariant-violation path, not an expected one.
- Rationale (deferral): The fix is a deliberate cross-backend policy choice
  (log-and-continue vs `debug_assert!` vs halt) that must be applied to **both** the Rust
  generator and the Python unparser to preserve the project's hard cross-backend behavioral
  parity requirement (CLAUDE.md). Emitting a Rust-only `eprintln` now would diverge the
  backends. Deferred with tracking rather than implemented in respond mode.

errhandling-2:
- Disposition: TODO(unparser-none-path-diagnostics)
- Action: TODO comment added at `fltk/unparse/gsm2unparser_rs.py` (`_gen_regex_term_body`, the
  `let text = span.text()?;` site, ~line 1077) plus the same `TODO.md` entry. No generated
  output changed.
- Severity assessment: Same root theme as errhandling-1 — a `None` from `span.text()` for a
  labeled span (Identifier/RawString/Literal/comment content; all parse as INCLUDE regex spans
  routed through this one generator site) propagates via `?` to the public `unparse_*` entry
  with no record of which label failed. The generator already documents this as a deliberate
  failure mode (docstring ~line 1032). It is an invariant-violation path in the fltkfmt
  pipeline, where spans always carry source.
- Rationale (deferral): Same as errhandling-1 — adding a diagnostic is a cross-backend policy
  decision out of the current feature's scope; tracked under one slug
  (`unparser-none-path-diagnostics`) covering both sites.

correctness-1:
- Disposition: Fixed
- Action: Updated the two stale tests in `tests/test_rust_unparser_generator.py`.
  `test_count_newlines_in_trivia_multi_variant_emits_catchall` renamed to
  `..._uses_if_let`; now asserts `if let cst::TriviaChild::Span(span) = &child.1 {` is present
  and `_ => {}` is absent. `test_has_preservable_trivia_matches_configured_node_types` now
  asserts `if let cst::TriviaChild::Comment(_) = &child.1 {` and `return true;` are present and
  `_ => {}` is absent. Docstrings updated to describe the `if let` intent. No generator change
  (the emitted Rust was already correct and clippy-clean; only the test text was stale).
- Severity assessment: High for the review gate — `make check`/`pytest` was red, and the
  multi-variant trivia-helper branches had zero passing coverage, so a real regression there
  would have been indistinguishable from the known-red state. No runtime defect.

security (notes-deep-security.md):
- Disposition: Won't-Do (no findings)
- Action: no change. The reviewer reported "No findings." Forward-looking items
  (`--in-place` atomic write, symlink/permission handling, terminal-escape sanitization,
  recursion depth) concern `run_main`/I/O that lands in a later increment and is not in this
  diff.
- Severity assessment: N/A — nothing to address now; noted for the implementer of the I/O
  increment.

test-1:
- Disposition: Fixed
- Action: Same change as correctness-1 (the two stale tests). The "Process note" in
  notes-deep-test.md (deferral via `--no-verify` without tracking) is resolved by this
  round: the tests are now green and will be enforced by the final increment's `make check`.
- Severity assessment: Same as correctness-1.

test-2:
- Disposition: Fixed
- Action: Added `tests::negative_pos_is_not_consumed` in `crates/fltk-fmt-cli/src/lib.rs`,
  asserting `!fully_consumed("foo", -1)` and `!fully_consumed("", -1)`.
- Severity assessment: Low — the `pos < 0` guard was correct but unverified; without a test,
  silent removal would wrap `pos as usize` and report any input "consumed". Now covered.

test-3:
- Disposition: Fixed
- Action: Chose option (a) — documented the contract. Extended the `fully_consumed` doc
  comment to specify the boundary behavior (negative ⇒ false; at/beyond char count ⇒ true,
  vacuously, because the parser bounds `pos` by input length) and added
  `tests::pos_past_end_is_consumed` asserting `fully_consumed("foo", 3)` and
  `fully_consumed("foo", 1000)` are both `true`.
- Severity assessment: Low — `pos` originates from the parser bounded by input length, so an
  out-of-range positive `pos` does not arise; documenting + pinning the contract removes the
  ambiguity the reviewer flagged.

reuse (notes-deep-reuse.md):
- Disposition: Won't-Do (no findings)
- Action: no change. Reviewer reported "No findings."
- Severity assessment: N/A.

quality-1:
- Disposition: Fixed
- Action: Same change as correctness-1 (the two stale tests).
- Severity assessment: Same as correctness-1.

quality-2:
- Disposition: Fixed
- Action: Removed the grammar-specific `about = "Format FLTK grammar files."` from
  `FmtArgs`'s `#[command]` in `crates/fltk-fmt-cli/src/lib.rs` (now `#[command(version)]`;
  clap falls back to the struct doc comment, which is generic). Added a
  `TODO(fmt-cli-per-consumer-about)` comment above `FmtArgs` and a `TODO.md` entry so the
  later `run_main`/`fltk_formatter_main!` increment threads a per-consumer `about` via
  `FmtArgs::command().about(..)` rather than sealing one wording in for every consumer.
- Severity assessment: Medium for the public-API surface — `fltk-fmt-cli` is consumed by
  out-of-tree formatters for arbitrary grammars, so the baked `.fltkg` wording would mislead
  every other consumer's `--help`. The misleading string is now gone; the per-consumer hook is
  tracked rather than implemented because the mechanism belongs to the later macro/`run_main`
  increment.

efficiency-1:
- Disposition: Won't-Do
- Action: no change.
- Severity assessment: The non-comment separator case scans a trivia node's children twice
  (`_has_preservable_trivia` then `_count_newlines_in_trivia`). The reviewer measured the cost
  as a negligible bounded constant per separator (`children()` is an O(1) slice borrow, trivia
  between two tokens is small) and explicitly concluded "leaving it as-is is reasonable,"
  filing it for an informed call, not as a blocker.
- Rationale (Won't-Do): This is pre-existing generator logic (this diff only changed the
  clippy `match`→`if let` shape, not the two-pass structure). The only in-scope change here
  would touch the Rust generator alone, which would diverge the merged single-pass from the
  Python backend and break the project's hard cross-backend structural/behavioral parity
  requirement (CLAUDE.md) for no measurable benefit; applying it to both backends is outside
  this feature's scope and unjustified by the negligible cost. Doing the optimization as part
  of this work would therefore actively harm parity, so it is declined.
