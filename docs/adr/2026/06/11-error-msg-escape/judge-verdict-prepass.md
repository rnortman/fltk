# Judge verdict — pre-pass

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Phase: pre-pass (code). Base ef8288c..HEAD 8da7924. Round 1.
Notes: `notes-prepass-slop.md` (3 findings). **Input discrepancy:** `notes-prepass-scope.md` was named as an input but does not exist in the worktree or anywhere in git history (`git log --all` finds nothing). Dispositions doc covers only the 3 slop findings. Adjudication below covers what exists; the orchestrator should confirm the scope reviewer produced no findings rather than a lost file.

## Added TODOs walk

None. No TODO dispositions in this round.

## Other findings walk

### slop-1 — Fixed
Claim: 4-line derivation comment block (sentinel-quirk math, manual pad calculation) in Rust test `format_error_message_with_controls_in_line`, `crates/fltk-parser-core/src/errors.rs` — workbench notes committed as test commentary.
Evidence: HEAD diff shows the test carries only `// Failing line contains \x1b[31m and \r; error at col 0.` The quoted derivation block (`line_ends sentinel excludes last char...`, `pad=0`, `escaped_suffix = ...`) is absent from HEAD.
Assessment: removed as claimed; remaining comment states what the test verifies, not how it was derived. Accept.

### slop-2 — Fixed
Claim: sentinel-quirk explanation comment on the `("stmt", "x\r=\r@", FAIL)` corpus entry in `tests/test_rust_parser_parity_fixture.py` — hedging implementation detail inline with a data entry.
Evidence: HEAD diff at `tests/test_rust_parser_parity_fixture.py:113-118` retains only the functional trace (`name matches "x", WS_REQUIRED separators consume each \r ... rhs:atom fails at pos 4`). The quoted note (`triggers the sentinel last-line quirk ... caret points one column past the rendered line`) is gone. The sentinel quirk remains documented where it belongs: `design.md` edge cases ("Sentinel last-line quirk") — matching the reviewer's suggested fix.
Assessment: removed as claimed; retained comment is actionable corpus context. Accept.

### slop-3 — Fixed
Claim: C1 test inputs in `tests/test_pyrt_errors.py` rendered as empty/invisible literals — unverifiable by inspection, fragile to editor normalization; consequence is either vacuous tests or silent future breakage.
Evidence: HEAD `tests/test_pyrt_errors.py:25-27` (`test_escape_control_chars_c1`) uses explicit escapes: `escape_control_chars("") == "\\x9b"`, `""`, `""`. Rust mirror test `escape_control_chars_table` uses `\u{009b}` etc. — same convention.
Assessment: exactly the reviewer's prescribed fix; source is now unambiguous and editor-safe. The disposition's severity note (tests passed pre-fix; literals were present but invisible) is consistent with the fix being representational, not behavioral. Accept.

## Disputed items

None among adjudicated findings. Outstanding for the orchestrator (not a responder fault): confirm `notes-prepass-scope.md` was intentionally absent (zero scope findings) and not dropped.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED

All dispositions in `dispositions-prepass.md` verified against HEAD 8da7924. Caveat above: scope notes file missing from inputs; verdict covers slop notes only.
