# Judge verdict — prepass

Phase: prepass. Base b668897..HEAD b107645. Round 2 — APPROVED or ESCALATE only.
Notes: notes-prepass-slop.md (no findings), notes-prepass-scope.md (4 findings). Dispositions: dispositions-prepass.md (updated through rework commits c8c425b, b107645).
Prior round-1 verdict: REWORK on scope-1 and scope-3; scope-2 and scope-4 accepted at round 1 and unchanged since — not re-walked.

Style note: concise, precise, complete, unambiguous. No padding.

## Added TODOs walk

No TODO-dispositioned findings. Rework diff d568cc4..b107645 adds no TODO comments (grep verified). Nothing to score.

## Other findings walk

### scope-1 — Fixed (multibyte error entry) — re-verified after rework

Round-1 defect: `("grammar", '"café" :=', FAIL)` errored at position 0, before any multibyte content; the consequence (line/col + caret indexing over a multibyte prefix) was untested.
Rework: entry replaced with `("grammar", 'x := "café" ** ;', FAIL)` at `tests/test_rust_parser_parity_fegen.py:72`.
Verification: ran the Python parser on this input. Result is None (FAIL branch executes), error position is **12** — after the multibyte 'é' at codepoint position 9 — and the rendered header is `Syntax error at line 1 col 13:` with the caret under position 12 on the same line as the multibyte run. Line/col and caret computation must index past the multibyte character; a codepoint/byte confusion in the Rust formatter (byte position 13 for 'é' is 2 bytes) would now produce a col or caret mismatch and fail `_assert_messages_equiv`'s header byte-equality. Design §2.5 requirement met. Test passes under both trivia settings (suite: 113 passed).
Assessment: rework addresses the consequence at the named line. Accept.

### scope-3 — Fixed (comparator self-tests) — re-verified after rework

Round-1 defect: 6 of 10 §4.4 dimensions not pinned (child-count, deep-child, species-reverse, header, group-order, token-set — earlier checks fired first or only a helper was tested).
Rework: `_assert_messages_equiv` extracted in `tests/parser_parity.py:71-88`; `assert_error_equiv` now delegates its entire message-comparison path to it (`parser_parity.py:115`), so negative tests on the helper cover the production path. Self-tests reworked in `tests/test_rust_parser_parity_fegen.py`. Per-dimension verification against the comparator's check order (kind :13, span :15-18, children-len :22, label :28, species :32, recursion :36):

- **kind, span, label** — unchanged from round 1, pinned then; still pass. Pinned.
- **child-count** (`test_assert_cst_equal_fails_child_count_mismatch`): hand-built `Grammar` nodes both with `Span(0,10)`, identical kind and labels, 1 vs 2 children — span check cannot fire first; the length check (or `zip(strict=True)`) is the discriminator. A comparator missing the length check no longer passes. Pinned.
- **deep-child** (`test_assert_cst_equal_fails_deep_child_mismatch`): hand-built Grammar→Rule→Identifier with all enclosing spans `Span(0,25)`; only the leaf Identifier span differs (end 5 vs 6). Kind/span/len/label/species all match at depths 0-1; only recursion to depth 2 detects the mismatch. A non-recursing comparator raises nothing → test fails. Recursion pinned.
- **species node-vs-span** — unchanged from round 1, pinned then. Pinned.
- **species span-vs-node** (`test_assert_cst_equal_fails_species_span_vs_node`): Python `Rule` with a bare `Span(0,1)` at NAME where the Rust Rule has an Identifier node; kind, span (copied from `rust_node.span`), child-count (2), and labels all match — the species check at `parser_parity.py:32` is the discriminator. Reverse direction now covered. Pinned.
- **header** (`test_assert_error_equiv_fails_header_mismatch`): hand-built parsed messages through `_assert_messages_equiv`, rules identical, headers differing in col text — fires at the header assert (`parser_parity.py:79`), not the position check (which lives separately in `assert_error_equiv`). Pinned.
- **group order** (`test_assert_messages_equiv_fails_group_order`): identical headers, same key set in reversed insertion order — header assert passes, fires at `list(keys())` equality (`parser_parity.py:81`). Pinned.
- **token set** (`test_assert_messages_equiv_fails_token_set`): identical headers and key order, differing per-rule sets — fires at the token-set assert (`parser_parity.py:86`). Pinned.

The two round-1 helper-only tests (`test_parse_error_message_group_order`, `test_parse_error_message_token_set_mismatch`) were replaced, not merely supplemented — no vacuous residue. All 10 §4.4 dimensions plus position now have genuine negative coverage on the production comparison path. Suite: 113 passed.
Assessment: rework complete. Accept.

## Approved

4 findings: 4 Fixed verified (scope-2, scope-4 at round 1; scope-1, scope-3 at round 2), 0 Won't-Do, 0 TODOs. Slop pass: no findings.

---

## Verdict: APPROVED

All dispositions acceptable after rework. HEAD b107645.
