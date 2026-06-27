# Test review — increments 1–3 (rust-fltkfmt)

Commits reviewed: e5bb7ec..1b48755 (4 commits)
Base (spec-freeze): 61fc5e8

---

## test-1 — Two pre-existing tests are broken by the generator change and left unrepaired

**File:line** `tests/test_rust_unparser_generator.py:1968`
(`test_count_newlines_in_trivia_multi_variant_emits_catchall`) and `:2035`
(`test_has_preservable_trivia_matches_configured_node_types`)

**What's wrong**

Commit `e5bb7ec` fixed a real clippy bug in `gsm2unparser_rs.py`: the generator was
emitting `match { Variant => …, _ => {} }` for multi-variant trivia child enums, which
clippy flags as `single_match`.  The fix was correct — replace with `if let` so the
generated code is clippy-clean at all variant counts.  However, the two tests that covered
the affected code paths were not updated in the same commit.  They still assert:

- `"cst::TriviaChild::Span(span) => {"` (match-arm syntax) and `"_ => {}"` for
  `_count_newlines_in_trivia` with multiple variants — both assertions now fail because
  the generator emits `if let cst::TriviaChild::Span(span) = &child.1 {` instead.
- `"cst::TriviaChild::Comment(_) => return true,"` for `_has_preservable_trivia` with a
  configured node name — fails because the generator now emits `if let
  cst::TriviaChild::Comment(_) = &child.1 {` / `return true;`.

The implementation log (increment 1 "Deviations / surprises") correctly describes the
clippy fix but does not mention the broken tests.  All four commits after the base were
pushed with `--no-verify`, bypassing the pre-commit hook that would have surfaced the
failure.

**Consequence**

`make check` fails on main.  The multi-variant paths in both helper generators
(`num_variants > 1` branch in `_gen_count_newlines_in_trivia_method`, filtered-node branch
in `_gen_has_preservable_trivia_method`) now have zero passing test coverage, because the
only tests that covered them are in a failing state.  Any regression in those branches goes
undetected.  The test name `emits_catchall` is now actively misleading — the whole point of
the change was to remove the catch-all.

**Fix**

Update both tests in the same commit that introduced or acknowledged the `if let` change.
For `test_count_newlines_in_trivia_multi_variant_emits_catchall`:

- Replace `assert "cst::TriviaChild::Span(span) => {" in body` with
  `assert 'if let cst::TriviaChild::Span(span) = &child.1 {' in body`.
- Drop `assert "_ => {}" in body` (no longer emitted for multi-variant).
- Rename the test to `test_count_newlines_in_trivia_multi_variant_uses_if_let` (the
  existing name describes the old behavior).

For `test_has_preservable_trivia_matches_configured_node_types`:

- Replace `assert "cst::TriviaChild::Comment(_) => return true," in body` with two
  separate assertions: `assert 'if let cst::TriviaChild::Comment(_) = &child.1 {' in
  body` and `assert 'return true;' in body`.
- Drop `assert "_ => {}" in body` (the `if let` form needs no catch-all).

The behavioral intent — "a configured trivia node type causes the helper to return true
when that variant is encountered" — is preserved; only the syntax assertions need
updating.

---

## test-2 — No test exercises the `pos < 0` guard in `fully_consumed`

**File:line** `crates/fltk-fmt-cli/src/lib.rs:54–58`

**What's wrong**

The implementation opens with `if pos < 0 { return false; }` to guard against negative
values (which `as usize` would silently wrap to a large number).  None of the five unit
tests calls `fully_consumed` with a negative argument.

**Consequence**

The guard's correctness is unverified.  If it were accidentally removed (or the early
return became unreachable due to a signature change), no test would catch the resulting
`usize` wraparound, which on a 64-bit platform would skip the entire string and return
`true` for any input.

**Fix**

Add `fn negative_pos_is_not_consumed()` that calls `assert!(!fully_consumed("foo", -1))`.

---

## test-3 — Behavior for `pos > src.chars().count()` is unspecified and untested

**File:line** `crates/fltk-fmt-cli/src/lib.rs:54–59`

**What's wrong**

When `pos` exceeds the character count, `src.chars().skip(pos as usize)` produces an empty
iterator; `Iterator::all` on an empty iterator returns `true`.  This means
`fully_consumed("foo", 1000)` returns `true`.  Whether that is the intended contract (treat
out-of-bounds as "past the end, therefore consumed") or a latent defect (a parser reporting
a position beyond the string is a bug that should surface as an error) is not documented.

**Consequence**

A parser bug that reports a position beyond the string end silently passes the `fully_consumed`
check and produces formatted output from a corrupted position.  This is undetectable by tests
and undocumented for callers.

**Fix**

Either (a) add a doc comment specifying the out-of-bounds behavior and a test asserting
`fully_consumed("foo", 1000)` is `true`, or (b) if the intent is to catch this case, change
the implementation to `pos >= 0 && pos as usize >= src.chars().count() || ...` and add a
test for the boundary.  Either way the contract needs to be explicit.

---

## Process note — deferral without tracking

The implementation log acknowledges the clippy fix that caused the test failures but does
not record the failures as a known deferral, does not reference a TODO, and does not explain
why the tests were not updated in-place.  Per CLAUDE.md, when implementation changes alter
generated code shape, the tests that verify that shape must be updated in the same commit.
Bypassing the pre-commit hook (`--no-verify`) to carry the failures across four commits is
not an acceptable substitute.

These are not "later-increment" items — they are existing tests for code already modified in
increment 1.  They should be fixed before increment 4 ships.
