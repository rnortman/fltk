# Judge verdict — design review

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Phase: design. Doc: `docs/adr/2026/06/10-rust-parser-python-bindings/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 2 findings.

## Findings walk

### design-1 — Fixed
Claim: §2.4 comparator discriminated span-vs-node children via `hasattr(child, "kind")`; spans expose `kind` on both backends, so the comparator would recurse into every span child and raise `AttributeError` (or silently skip span comparison if defensively written), breaking the entire parity corpus.
Fact-check (independent): `terminalsrc.py:55` — `kind: Literal[SpanKind.SPAN]` field on the Span dataclass; `crates/fltk-cst-core/src/span.rs:564` — `#[getter] fn kind` on the Span pyclass. `children`: present on nodes (`fltk/fegen/fltk_cst.py:82` dataclass field; `tests/rust_cst_fegen/src/cst.rs:492` getter), absent from spans on both backends (no `children` in span.rs or terminalsrc.py). Reviewer's premise and the responder's chosen fix are both source-accurate.
Doc inspection: §2.4 now discriminates by `hasattr(child, "children")` and carries an explicit "**Not** `hasattr(child, "kind")`" warning with both citations; §4 item 4 requires negative self-tests for span-vs-node misdiscrimination "in both directions — pins the `hasattr(child, "children")` discrimination of §2.4", exactly the reviewer's suggested self-test addition.
Assessment: fix addresses claim and consequence in full, including the self-test gap. Accept.

### design-2 — Fixed
Claim: controlling design §4 names trailing-character behavior (`fltk/fegen/test_trailing_character_bug.py`) as required parity-corpus input; no corpus entry covered it, so an end-of-input final-position divergence — the exact historical Python bug — would pass the suite.
Doc inspection: §2.5 fegen list now has an explicit trailing-character bullet ("at least one SUCCESS entry whose input ends in a non-whitespace terminal with no trailing whitespace/newline — `result.pos == len(input)` on both backends"), citing controlling design §4 and `test_trailing_character_bug.py`. The fixture corpus table gains a `test_trailing_character_bug.py (controlling design §4)` row: the same-input with/without-trailing-whitespace pair (`"x+"`-style) with explicit SUCCESS/PARTIAL expectations, plus a non-whitespace-terminal SUCCESS entry. Matches the reviewer's suggested fix including the table citation.
Assessment: requirement-traceability gap closed at both grammars. Accept.

## Disputed items

None.

## Approved

2 findings: 2 Fixed verified, 0 Won't-Do, 0 TODOs.

---

## Verdict: APPROVED

Both dispositions verified against the updated design and independently fact-checked against source. Round 1.
