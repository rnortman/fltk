# Dispositions — deep review batch 5 (rust-unparser-backend)

Commit reviewed: 5f7b5cb. Fixes committed on top.

## Scope-aggregate triage

No `scope-N` findings in this batch; no escalation. All findings are within respond-mode
scope (a single behavior-parity fix, an error-context wrap, a dead-branch removal, a helper
extraction, and test additions/rewrites).

---

errhandling-1:
- Disposition: Fixed
- Action: `_item_spacing_lines` (`fltk/unparse/gsm2unparser_rs.py`) now wraps the
  `_doc_to_rust_expr(spacing)` call in `try/except ValueError` and re-raises with rule + item
  (label or term kind) + position context, mirroring the existing `_gen_rule_entry` JOIN_BEGIN
  wrap. The bare `_doc_to_rust_expr` "Unknown Doc type: …" is preserved as the chained cause.
- Severity assessment: A `FormatterConfig` with a Group/Nest/Join/Comment item-spacing Doc would
  raise an undiagnosable bare ValueError at generation time, giving no hint which rule/item
  triggered it. Build-time only; no runtime exposure.

correctness-1:
- Disposition: Fixed
- Action: `_gen_regex_term_body` now raises `RuntimeError` ("only INCLUDE regex terms can be
  unparsed") for any non-INCLUDE disposition, before emitting any body, matching the Python
  backend's unconditional `_extract_and_validate_nonsequence_child` rejection
  (`gsm2unparser.py:267`). The now-dead INCLUDE-vs-else advance branch was collapsed to an
  unconditional `pos + 1`. Docstring updated. The unit test that pinned the old (divergent)
  INLINE-emits-a-body behavior was rewritten to assert the rejection (see test-3).
- Severity assessment: Under `python -O` (where `gsm2tree.py:630`'s INLINE-must-be-Identifier
  assert is stripped) an INLINE regex term made Python's generator raise but Rust's silently
  emit a body — opposite outcomes for one grammar, violating the design's cross-backend
  generation-equivalence goal. Off `-O` both already rejected; impact was limited to optimized
  runs, but the `else` branch was dead in every other configuration. The design's regex bullet
  (§2.2) never specified accepting non-INCLUDE; the parity principle it states repeatedly governs.

test-1:
- Disposition: Fixed
- Action: Added `test_term_body_rejects_unknown_term_kind` (`tests/test_rust_unparser_generator.py`)
  constructing an `Item` with a `gsm.Invocation` term and asserting `_gen_term_body` raises
  `ValueError` matching "Unrecognized term type".
- Severity assessment: The `_gen_term_body` final guard (added this batch) had no test; silent
  removal or rerouting would emit wrong Rust for a future misrouted term kind with no failing test.

test-2:
- Disposition: Fixed
- Action: In `test_regex_single_variant_reads_span_text_and_advances`, scoped the
  `"_ => return None," not in …` negative assertion to `_method_body(src, "unparse_r__alt0__item0")`
  instead of the whole file, matching the other batch-5 negative assertions.
- Severity assessment: The file-global assertion could be confounded by the synthetic `_trivia`
  rule, silently testing the wrong rule and masking a real catch-all regression.

test-3:
- Disposition: Fixed (subsumed by the correctness-1 fix)
- Action: The flagged test (`test_regex_inline_body_reads_span_without_advance`) was built from a
  grammar whose child enum had no `Span` variant, so it "tested" invalid Rust. The correctness-1
  fix makes non-INCLUDE regex a generation error, so the test was rewritten as
  `test_regex_term_body_rejects_non_include_disposition` — it now uses a valid single-Span-variant
  grammar and asserts the `RuntimeError`, eliminating both the invalid-Rust and false-confidence
  concerns at once.
- Severity assessment: The old test gave false confidence about generated-code correctness and
  exercised a path (INLINE regex emitting a body) that the correctness-1 fix removed entirely.

test-4:
- Disposition: Fixed
- Action: Added an assertion in `test_subexpr_item_delegates_to_alts_dispatch` that the `__alts`
  dispatch body contains the `None` all-alternatives-failed terminator
  (`_method_body(src, "unparse_r__alt0__item0__alts")`).
- Severity assessment: A dropped terminator would emit Rust that fails to compile on the
  exhausted-alternatives path, but no generator test (which does not compile output) caught it.

test-5:
- Disposition: Fixed
- Action: Added `test_subexpr_inner_item_gets_before_spacing` — a grammar `r := (a:"x" | b:"y");`
  with a `before:label:a` SPACING anchor, asserting `before_spec` is emitted in the inner nested
  alternative body (`unparse_r__alt0__item0__alts__alt0`) ahead of the inner item call. Spacing on
  the *outer* sub-expression item is not configurable (it is unlabeled and non-literal, so no
  selector matches — `fmt_config._get_spacing`), so the test exercises the sub-expression + spacing
  combination at the inner item, where it is reachable.
- Severity assessment: A regression gating spacing on term kind would drop spacing for
  sub-expression-walked items while the isolated spacing/sub-expression tests still passed.

reuse-1:
- Disposition: Fixed
- Action: Extracted `_gen_alt_dispatch_loop(prefix, n_alts, start_pos, pop_chain="")`
  (`fltk/unparse/gsm2unparser_rs.py`); both `_gen_rule_entry` (`start_pos="0"`, optional
  `pop_chain`) and `_gen_alts_dispatch` (`start_pos="pos"`) now call it. Generator output is
  byte-identical (all 75 generator tests pass unchanged).
- Severity assessment: The clone-last dispatch loop existed in two copies already diverging on the
  `pop_chain` path; a future dispatch-strategy change risked being applied to only one.

quality-1:
- Disposition: Fixed (same change as reuse-1)
- Action: Same `_gen_alt_dispatch_loop` extraction; the two copies of the dispatch loop are now
  single-sourced.
- Severity assessment: Same as reuse-1 — copy-paste-with-variation that would drift further when
  item-level anchors touch the dispatch site.

quality-2:
- Disposition: Fixed
- Action: Dropped the unreachable `else: raise ValueError(...)` branch in `_item_spacing_lines`;
  the `if position == "before" / elif "after"` pair is exhaustive given `position:
  Literal["before", "after"]`. Pyright confirms no possibly-unbound on `spacing`/`ctor`
  (0 errors). A comment documents the exhaustiveness.
- Severity assessment: The dead `else` mischaracterized the `Literal` parameter as an open-ended
  string with a runtime fallthrough guard — misleading to readers and a false safety net.

security (no findings): no action.
efficiency (no findings): no action.
