# Design review findings: error-msg-escape

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Verification performed against base 7ddec4a: `crates/fltk-parser-core/src/errors.rs`, `crates/fltk-parser-core/src/terminalsrc.rs`, `crates/fltk-parser-core/src/lib.rs:24`, `fltk/fegen/pyrt/errors.py`, `fltk/fegen/pyrt/terminalsrc.py`, `tests/parser_parity.py`, `tests/test_rust_parser_parity_fixture.py`, `fltk/fegen/test_data/rust_parser_fixture.fltkg`, `tests/rust_parser_fixture/src/parser.rs:95-97` (and `REGEX_PATTERNS` line 21: trivia = `[\s]+`), `fltk/fegen/gsm2parser_rs.py:378`, `TODO.md:54`. Confirmed accurate: all cited file:line anchors; the `("stmt", "x\r=\r@", FAIL)` trace (trivia `[\s]+` consumes `\r` in both engines; `longest_parse_len == 4`; sentinel line_span `[0,4)` = `x\r=\r`; pad 10); the `("num", "\x1b[31mabc", FAIL)` trace; col domain `[-1, line_len]` so the prefix slice is always in range; `col == -1` corner; comparator unaffected if both sides escape identically; no parser regeneration needed (both backends format via the runtime, generated Rust delegates at parser.rs:95-97); `tests/test_pyrt_errors.py` does not exist (correctly labeled "new"); existing Rust goldens are ASCII-clean and named correctly.

## design-1: "Expected: block ... already escapes via py_repr_str/Python repr" is false for C1 on the Rust side

Section: "Edge cases / failure modes", bullet: "**`Expected:` block:** token rendering already escapes via `py_repr_str`/Python `repr`; untouched."

What's wrong: `py_repr_str` (errors.rs:191-216) escapes only codepoints < 0x20 and 0x7f (errors.rs:208); U+0080–U+009F (C1) pass through **raw** — explicitly documented as a divergence at errors.rs:188-190 ("Non-ASCII chars are emitted raw"). Python `repr` escapes C1 (`repr('\x9b')` → `'\\x9b'`, verified). So for C1: (a) the Rust Expected block emits raw C1, and (b) the two backends diverge.

Why it matters: the design's own widening rationale names U+009B (8-bit CSI) as "the exact vector this fix exists to block," then asserts the Expected block is already safe — internally inconsistent. The "no U+0080–U+009F anywhere in a formatted message" assertion (test plan item 1, bullet 4) is only exercised on a message whose grammar tokens are ASCII, so the gap is untestable as planned and invisible.

Consequence: a grammar whose token text contains a C1 codepoint still injects a raw single-character CSI into Rust-formatted error messages, and trips the parity comparator's token-set check (parser_parity.py:114) cross-backend. Risk is bounded — grammar tokens are author-controlled, not untrusted parse input, and the divergence is preexisting and documented — but the design's stated rationale for leaving the block untouched is factually wrong.

Suggested fix: reword the bullet to the verifiable claim — "py_repr_str escapes C0/DEL; raw C1 in grammar tokens is a preexisting, documented divergence (errors.rs:188-190), out of scope because tokens are grammar-author-controlled, not untrusted input." Optionally note it as follow-up if the C1 security argument is taken seriously.

## design-2: DEL/C1 widening exceeds the approved escape set and is self-adjudicated

Section: "Decisions (deliberate widening beyond the TODO's literal "C0" wording)" + "Open questions: None. The DEL/C1 widening ... not user-judgment items."

What's wrong: the request pins the fix shape to "Identical escaping of C0 controls (except `\t`; `\n` unreachable)" (request.md:25) and frames the output change as "a deliberate, **user-approved** change" (request.md:32), where the approval is triage item 4 — which covered C0 escaping. The design widens the escape set to DEL + C1 and then declares the widening "not user-judgment items," closing the question it just opened.

Why it matters: per CLAUDE.md, observable changes to generated output for out-of-tree consumers must be deliberate, called-out decisions; the design does call it out plainly (good), but the requirements bound the set, and a deviation from a user-approved spec is exactly a user-judgment item. The security rationale (U+009B single-char CSI, raw DEL) is sound and verified; the objection is to the adjudication, not the engineering.

Consequence: if the user intended the approved C0-only set, the implementation deviates from spec with no checkpoint; conversely if the widening is accepted, the requirements doc is now stale relative to the design and the parity tests will pin the wider set. Either way the discrepancy should be resolved by the user, not by the design declaring it closed.

Suggested fix: keep the widening and its rationale, but list it under Open questions as a one-line user confirmation ("escape set widened from C0 to C0+DEL+C1 — confirm"), or get the requirements doc amended.
