# Judge verdict — deep review

Phase: deep. Base f9ed936..HEAD 71f45fb (fixes on reviewed commit 5f7b5cb). Round 1.
Notes: 7 reviewer files (errhandling, correctness, security, test, reuse, quality, efficiency).
Findings: 9 distinct (errhandling-1, correctness-1, test-1..5, reuse-1, quality-1 ≡ reuse-1, quality-2). Security + efficiency: no findings.

## Added TODOs walk

None. No TODO-dispositioned findings in this batch (dispositions doc confirms no `scope-N` and no TODO/Won't-Do dispositions; all dispositions are Fixed).

## Other findings walk

### errhandling-1 — Fixed
Claim: `_item_spacing_lines` (`gsm2unparser_rs.py`) calls `_doc_to_rust_expr(spacing)` unguarded; a Group/Nest/Join/Comment spacing Doc raises a bare `ValueError("Unknown Doc type: …")`; consequence is a build-time generation error naming only the Doc type, not which rule/item/position triggered it — undiagnosable at the module boundary.
Evidence: diff wraps the call in `try/except ValueError` and re-raises with `f"Rule {rule_name!r} {position}-spacing for {item_id} uses unsupported Doc type: {exc}"` (item_id = label or term kind), `from exc` preserving the chained cause. This mirrors the established `_gen_rule_entry` JOIN_BEGIN wrap cited by the finding. Matches the reviewer's requested change essentially verbatim.
Assessment: fix addresses the consequence (context-bearing message, identifiable config entry) at the named site. Accept.

### correctness-1 — Fixed
Claim: `_gen_regex_term_body` emits a working body for non-INCLUDE (INLINE) regex (binds Span, reads `span.text()`, returns without advancing), while the Python backend's Regex branch (`gsm2unparser.py:1750`) calls `_extract_and_validate_nonsequence_child` unconditionally, which raises `RuntimeError` for any `disposition != INCLUDE` (`:267`). Consequence: under `python -O` (where `gsm2tree.py:630`'s INLINE-must-be-Identifier `assert` is stripped) Python raises but Rust silently emits a body — opposite outcomes for one grammar, violating the design's cross-backend generation-equivalence goal.
Ground-truth check: confirmed at `gsm2unparser.py:267` — `if item.disposition != gsm.Disposition.INCLUDE: raise RuntimeError(...)`, called unconditionally from the Regex branch (`:1756`). Python's own `if disposition == INCLUDE / else` advance branch is therefore dead — exactly the structure the Rust backend cloned without the preceding rejection.
Evidence: diff adds `if item.disposition != gsm.Disposition.INCLUDE: raise RuntimeError("… only INCLUDE regex terms can be unparsed.")` (explicit `raise`, survives `-O`) before any body emission, and collapses the now-dead INCLUDE-vs-else advance branch to an unconditional `pos + 1`. Docstring updated to state the parity rationale and cite `gsm2unparser.py:267` / `gsm2tree.py:630`. Exact message text differs from Python's, but the governing behavior (reject non-INCLUDE) now matches; the design (§2.2) never specified accepting non-INCLUDE.
Assessment: faithful parity fix; also removes genuinely dead code. Reviewer rated severity low/narrow (only diverges under `-O`), but the fix is correct and net-positive regardless. Accept.

### test-1 — Fixed
Claim: `_gen_term_body`'s final `raise ValueError` (unrecognized term kind) had no test, unlike the sibling `_rejects_non_*` guards; silent removal/rerouting would emit wrong Rust uncaught.
Evidence: added `test_term_body_rejects_unknown_term_kind` constructs an `Item` with a `gsm.Invocation` term and asserts `pytest.raises(ValueError, match="Unrecognized term type")`. Guard message confirmed at `gsm2unparser_rs.py:463`. Test passes.
Assessment: pins the guard. Accept.

### test-2 — Fixed
Claim: `assert "_ => return None," not in src` in `test_regex_single_variant_reads_span_text_and_advances` was file-global; the synthetic `_trivia` rule could confound it, silently testing the wrong rule.
Evidence: diff scopes the negative assertion to `_method_body(src, "unparse_r__alt0__item0")`, matching the other batch-5 negative assertions. Test passes.
Assessment: addresses the confounding. Accept.

### test-3 — Fixed (subsumed by correctness-1)
Claim: `test_regex_inline_body_reads_span_without_advance` was built from a grammar whose child enum had no `Span` variant, so it "tested" invalid Rust and gave false confidence; it also exercised the INLINE-emits-body path that correctness-1 removes.
Evidence: correctness-1 makes non-INCLUDE regex a generation error, so the test was rewritten as `test_regex_term_body_rejects_non_include_disposition` using a valid single-Span-variant grammar (`r := foo:/[0-9]+/;`) and asserting `pytest.raises(RuntimeError, match="only INCLUDE regex terms")`. Test passes.
Assessment: both the invalid-Rust and false-confidence concerns are eliminated because the path no longer exists; rewriting to assert rejection is the correct resolution. Accept.

### test-4 — Fixed
Claim: no sub-expression test asserts the `__alts` dispatch `None` all-alternatives-failed terminator; a dropped terminator would produce non-compiling Rust uncaught by generator tests.
Evidence: diff adds `assert "        None" in _method_body(src, "unparse_r__alt0__item0__alts")` to `test_subexpr_item_delegates_to_alts_dispatch`. Test passes.
Assessment: pins the terminator. Accept.

### test-5 — Fixed
Claim: spacing and sub-expression paths tested only in isolation; a guard gating spacing on term kind would drop spacing for sub-expression-walked items undetected.
Evidence: diff adds `test_subexpr_inner_item_gets_before_spacing` — grammar `r := (a:"x" | b:"y");` with a before-spacing anchor on inner label `a`, asserting `before_spec(Doc::Line)` appears in the inner nested-alt body and precedes the inner item call. Disposition's note that outer sub-expression-item spacing is unconfigurable (unlabeled/non-literal) is correct, so targeting the inner item is the reachable combination. Test passes.
Assessment: exercises spacing+subexpr in combination. Accept.

### reuse-1 / quality-1 — Fixed (single change)
Claim: the clone-last alt-dispatch loop is duplicated in `_gen_rule_entry` and `_gen_alts_dispatch`, already diverging on the `pop_chain` path; a future dispatch-strategy change risks being applied to only one.
Evidence: diff extracts `_gen_alt_dispatch_loop(prefix, n_alts, start_pos, pop_chain="")`; `_gen_rule_entry` calls it with `prefix=f"unparse_{rule_name}", start_pos="0", pop_chain=pop_chain`, `_gen_alts_dispatch` with `prefix=alts_prefix, start_pos="pos"`. By inspection the helper's emitted strings substitute back to the original lines exactly (rule-entry: `unparse_{rule}__alt{i}(node, 0, …)`; alts: `{alts_prefix}__alt{i}(node, pos, …)`), so output is byte-identical. Confirmed: all 73 generator tests (string-exact assertions) pass unchanged.
Assessment: single-sources the loop; output unchanged. Accept.

### quality-2 — Fixed
Claim: the `else: raise ValueError` in `_item_spacing_lines` is dead — `position: Literal["before","after"]` makes the if/elif exhaustive; the dead else mischaracterizes the param as open-ended with a runtime guard.
Evidence: diff drops the `else` branch and adds a comment documenting Pyright-enforced exhaustiveness. Disposition reports Pyright 0 errors (no possibly-unbound on `spacing`/`ctor`).
Assessment: removes the false safety net; correct. Accept.

## Disputed items

None.

## Note (no disposition required)

The correctness reviewer's "Minor note" (Rust `_gen_alternative_body` adds before/after spacing unconditionally vs Python gating on `Omit`/`RenderAs` disposition) was explicitly framed by the reviewer as "not a current-batch bug": it only diverges once a config uses omit/render, and `Omit`/`RenderAs` item-body handling is itself deferred, so there is no observable divergence today. It was not raised as a finding and needs no disposition; the gate restoration rides with the deferred Omit/RenderAs work.

## Approved

9 findings: 9 Fixed verified (errhandling-1, correctness-1, test-1..5, reuse-1, quality-1 [≡ reuse-1], quality-2). No TODOs, no Won't-Do, no scope-N. 73 generator tests pass.

---

## Verdict: APPROVED

All dispositions are Fixed and verified against the diff, the Python backend (parity ground truth at `gsm2unparser.py:267`/`:1750`), and a passing test run. No dispositions wrong.
