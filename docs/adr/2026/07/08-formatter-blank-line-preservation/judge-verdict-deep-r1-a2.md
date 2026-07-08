# Judge verdict — deep review (rework a2)

Phase: deep. Base ef8f727..HEAD 5385e61 (rework commit 5385e61 on top of cadb4b2). Round 2 — APPROVED or ESCALATE only.
Scope: one reworked disposition (quality-3). The six findings accepted in round 1 (correctness-1, errhandling-1, test-1, quality-1, quality-2, quality-4) are not reopened.

## Added TODOs walk

None. The round-1 `TODO(trivia-count-helper)` was converted to Fixed; grep confirms zero references to the slug outside the ADR directory, and the `TODO.md` entry is removed in 5385e61. No new TODOs added this round.

## Other findings walk

### quality-3 — Fixed (was TODO, rejected round 1)

Claim: every node-typed `TriviaChild` arm of the generated `_count_newlines_in_trivia` carried a byte-identical 7-line read-lock/whitespace-check/count body; N copies per grammar bloat committed generated source and force N-fold verification of any future whitespace-rule tweak.

Round-1 prescription (verdict a1, Disputed items) had four parts. Verification of each against commit 5385e61:

1. **Emit one helper per impl; arms delegate.** `_gen_whitespace_node_newlines_method` added to `gsm2unparser_rs.py`, emitting `fn _whitespace_node_newlines(t: Option<&str>) -> usize` with the exact former inline body (`!t.is_empty() && t.chars().all(char::is_whitespace)` → `t.matches('\n').count()`, else 0 — semantics byte-equivalent). Each node arm in `_gen_count_newlines_in_trivia_method` now emits `count += Self::_whitespace_node_newlines(node.read().span().text_str());`. The match remains exhaustive with one arm per variant and no wildcard; the parity comment citing `pyrt.count_whitespace_newlines` is retained. Bonus beyond the prescription: the helper is omitted for Span-only trivia (`returns None` when no node-typed variants), avoiding dead emitted code, with `#[allow(dead_code)]` on the emitted helper justified by a self-standing comment (preserve_blanks == 0 unparsers).
2. **Regen, make fix, cargo check.** Committed `crates/fegen-rust/src/unparser.rs` at HEAD: exactly 1 helper definition, exactly 2 delegating arms (`BlockComment`, `LineComment`), 0 remnants of the old inline body (`let guard = node.read();` count is 0). I independently ran `cargo check --features python` in `crates/fegen-rust`: clean. Dispositions report full `make check` passed.
3. **Update generated-source pins.** All three `test_count_newlines_in_trivia_*` tests updated and passing at HEAD (3 passed): the node-variant test pins delegation in the method body plus the whitespace expression once via `_method_body(src, "_whitespace_node_newlines")`; the all-node-variants test asserts exactly two delegating arms (`count == 2`); the Span-only test asserts the helper is absent. The whitespace-only expression stays pinned in generated source, now in one place — exactly the shape the prescription asked for.
4. **Remove TODO comment and TODO.md entry.** Both gone in the diff; repo-wide grep for `trivia-count-helper` outside the ADR dir returns nothing. The replacement comment at the arm loop describes current structure, not history.

Design conformance: within the frozen design's bounds — §2 Component B's runtime whitespace test, arm-per-variant exhaustive match, and §5 item 8's generated-source pinning are all preserved; only where the shared expression lives changed.

Assessment: fix addresses the finding completely, verified by independent compilation and test run. Accept.

## Disputed items

None.

## Approved

7 of 7 findings: 6 carried from round 1 (5 Fixed verified, 1 Won't-Do sound), 1 Fixed verified this round (quality-3).

---

## Verdict: APPROVED

The single reworked disposition (quality-3) implements the round-1 prescription in full; independent verification (test run, cargo check, generated-source inspection, slug grep) confirms it.
