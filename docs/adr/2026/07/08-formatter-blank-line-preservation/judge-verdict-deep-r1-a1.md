# Judge verdict — deep review

Phase: deep. Base ef8f727..HEAD cadb4b2 (dispositions committed as cadb4b2 on top of 5864ae1). Round 1.
Notes: 7 reviewer files (security, reuse, efficiency: no findings); 7 findings total across correctness, error-handling, test, quality.
Design (frozen): docs/adr/2026/07/08-formatter-blank-line-preservation/design.md

## Added TODOs walk

### quality-3 — TODO(trivia-count-helper) at `fltk/unparse/gsm2unparser_rs.py` (arm loop in `_gen_count_newlines_in_trivia_method`)

TODO mechanics are correct: slug, `TODO.md` entry with concrete location and done-condition, `TODO(trivia-count-helper)` comment at the emission loop.

Q1 (worth doing): yes — the generated `_count_newlines_in_trivia` (confirmed at `crates/fegen-rust/src/unparser.rs:41-56`) carries a byte-identical 7-line read-lock/whitespace-check/count body per node-typed variant; N=2 in fegen, N copies in every downstream grammar with richer trivia. The design itself flags a possible future semantics tweak (comment-terminator handling, §2 "Known adjacent gaps") that would then need N-fold verification per grammar.

Q2 (design/owner input required): **no**. The fix is fully specified with no open semantic question: emit one private helper per impl (`fn _whitespace_node_newlines(t: Option<&str>) -> usize`), each arm delegates — the exact delegation shape the Python side already has (`pyrt.count_whitespace_newlines`), which the design cites as the model. Semantics are unchanged. The responder's own TODO.md entry contains the complete fix design. The stated deferral reason is workload — "changes generated Rust source (requires regen → make fix) and cascades into the exact-arm-body assertions... aggregate work beyond a respond-mode patch" — which is the "non-trivial" dodge, not "design work required." Regen → `make fix` → commit is the documented standard flow (CLAUDE.md), and updating the three generated-source pins in `tests/test_rust_unparser_generator.py` is mechanical.

The responder's design-conformance argument ("the design prescribes an arm per node-typed variant") does not hold: the helper approach keeps an arm per variant (delegating), keeps the match exhaustive, and keeps the whitespace expression in the emitted source — every property design §2/§5 actually pins.

Furthermore: this duplication was created by this iteration (the node arms are new); per rubric it cannot be silently deferred when it fails Q2.

Assessment: Q2 fails → do-now. **Disposition wrong.**

## Other findings walk

### correctness-1 — Fixed

Claim: Python `str.isspace()` vs Rust `char::is_whitespace` disagree on U+001C–U+001F, producing a byte-level cross-backend formatting divergence for trivia matched via explicit character classes.

Verification: I confirmed by exhaustive scan over all 0x110000 codepoints that the divergence between `str.isspace()` and the Unicode `White_Space` property (Rust's classifier) is exactly `{0x1c, 0x1d, 0x1e, 0x1f}` — no other codepoint differs in either direction. The fix (`pyrt.py:83-93`, `_C0_SEPARATORS` + `_is_unicode_whitespace_only`, gating the node path at `pyrt.py:111`) is therefore exact and complete; Rust side correctly untouched (it is the target semantics), no regen needed. Span path remains ungated on both sides (parity preserved — Rust `Span` arm also counts unconditionally). Pinned by `test_pyrt.py::test_c0_separator_node_child_counts_zero` (`"\n\x1c\n"` → 0); suite passes at HEAD.

Assessment: fix verified exact and complete. Accept.

### errhandling-1 — Won't-Do

Claim: new Rust node arms silently count 0 when `text_str()` is `None` for a source-bearing-but-invalid span, while the mirrored Python path raises `ValueError` — silent blank-line drops with no diagnostic in the Rust backend.

Verification of the rationale's three legs:
1. Pre-existing convention — **confirmed**: the Rust `Span` arm is `.map(...).unwrap_or(0)` (`unparser.rs:40`) while Python's span path (`count_span_newlines` → `extract_span_text`, `pyrt.py:47-49`) raises for source-bearing-invalid. The asymmetry class predates this diff; the new node arms extend it rather than introduce it.
2. Relaxing Python to silent-0 — **confirmed harmful**: `extract_span_text`'s raise is a documented deliberate fail-loud guard (`pyrt.py:44-49`), and relaxing only the node path would make Python's own span/node paths mutually inconsistent.
3. "Rust cannot distinguish sourceless from invalid" — **factually wrong**: `Span::has_source()` exists (`crates/fltk-cst-core/src/span.rs:474`, also pyo3-exposed at `:709`). A Rust arm *could* panic on `has_source() && text_str().is_none()`. The responder's infeasibility claim does not survive source inspection.

Despite the error in leg 3, the Won't-Do outcome is correct on the merits: the condition requires an invalid span on a node inside a successfully-parsed CST — an invariant the parser never violates (reviewer and responder agree on unreachability), which per calibration makes this a nit ("path genuinely impossible"). And a node-arm-only panic would create a new inconsistency *inside the same generated function* (node arms loud, sibling `Span` arm silent), so a coherent fix necessarily expands into re-conventioning the pre-existing `Span` arm on both backends — beyond this finding and this diff. Legs 1 and 2 independently carry the active-harm argument.

Assessment: accept Won't-Do; the factual error in leg 3 is noted for the record but does not change the outcome.

### test-1 — Fixed

Claim: the comment-terminator guard test passed both against the correct code and against the exact bug it claims to pin (single stray newline never crosses the `>= 2` threshold).

Diff at `test_unparser.py:1255`: input changed to `"foo; // c1\n// c2\nbar;\n"` (the reviewer's own verified discriminating input); docstring now states why two comments are needed. I independently re-verified discrimination by injecting a guard-dropped `count_whitespace_newlines` (counts node newlines unconditionally) and running the test: **fails under the broken helper, passes at HEAD**.

Assessment: fix verified red/green in both directions. Accept.

### quality-1 — Fixed

Claim: ADR-only vocabulary ("defect 1a/1b", "component A/B") and changelog phrasing ("Fails before the fix", "unchanged semantics") in test docstrings and `pyrt.py`.

Verification: diff shows all flagged docstrings reworded to self-standing descriptions (`test_unparser.py:1169/1203/1234`, `test_rust_unparser_generator.py:2038/2056`, `test_gear_demo.py:105`); `pyrt.py` history note gone. Grep across `fltk/` and `tests/` for all flagged phrases returns zero matches outside the ADR directory.

Assessment: complete. Accept.

### quality-2 — Fixed

Claim: `has_span` inferred by `num_variants > len(node_child_classes)` subtraction, re-encoding another module's invariant.

Diff: `has_span_child(rule_name)` added at `gsm2tree_rs.py:848-856` as a one-line wrapper over `_child_variants_for_rule`'s second element, parallel to `child_class_names_for_rule`; call site at `gsm2unparser_rs.py:1519` now uses it. Value identical by construction; fix commit touches no `crates/` files, consistent with the byte-unchanged claim. Generator tests pass.

Assessment: exactly the reviewer's suggested fix. Accept.

### quality-4 — Fixed

Claim: gear blank-line test copy-pastes the six-line format-pipeline setup from the idempotency test.

Diff: module-level `_gear_formatter()` extracted (`test_gear_demo.py:47-66`); both tests consume it. The dropped explicit final reparse assert is coverage-neutral: `render(once)` internally asserts `parsed.success` on the formatted output, which is the same guard, and the replacement comment says so. Full `test_gear_demo.py` suite passes (15 passed).

Assessment: complete, no coverage lost. Accept.

## Disputed items

- **quality-3 / TODO(trivia-count-helper)**: fails rubric Q2 — the fix requires no design decision and this iteration created the duplication. Need: do it now. Concrete fix, within the approved design's scope and structure (semantics unchanged, arm-per-variant and exhaustiveness preserved, source-level pinning preserved):
  1. In `_gen_count_newlines_in_trivia_method` (`gsm2unparser_rs.py`), emit one private helper per unparser impl — `fn _whitespace_node_newlines(t: Option<&str>) -> usize` containing the existing `if let Some(t) = ... { if !t.is_empty() && t.chars().all(char::is_whitespace) { t.matches('\n').count() } ... }` body — and reduce each node arm to `count += Self::_whitespace_node_newlines(node.read().span().text_str());`. Keep the parity comment citing `pyrt.count_whitespace_newlines`.
  2. Regenerate `crates/fegen-rust/src/unparser.rs`, run `make fix`, `cargo check`.
  3. Update the exact-source assertions in `tests/test_rust_unparser_generator.py` (the three `count_newlines_in_trivia` tests) to pin the helper body once plus the delegating arms — the whitespace-only expression stays pinned, just in one place.
  4. Remove the `TODO(trivia-count-helper)` comment and `TODO.md` entry.

  Alternatively, if the responder believes this genuinely needs a decision (e.g. that the design's §5 generated-source pins must stay arm-local), escalate with that specific reason — but "requires regen and test updates" alone does not qualify.

## Approved

6 of 7 findings: 5 Fixed verified (correctness-1, test-1, quality-1, quality-2, quality-4), 1 Won't-Do sound (errhandling-1, with a noted factual correction that does not change the outcome).

---

## Verdict: REWORK

One disposition wrong (quality-3: deferred-by-workload TODO for a problem this iteration created, fix requires no design input). Round 1.
