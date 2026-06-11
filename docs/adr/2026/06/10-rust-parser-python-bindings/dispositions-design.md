# Dispositions: Phase 3 design review, round 1

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Notes reviewed: `notes-design-design-reviewer.md`. Both findings fact-checked against source before disposition.

---

design-1:
- Disposition: Fixed
- Action: §2.4 `assert_cst_equal` species discrimination changed from `hasattr(child, "kind")` to `hasattr(child, "children")`, with an explicit warning that `kind` exists on spans on both backends (verified: `terminalsrc.py:55` `kind: Literal[SpanKind.SPAN]` field; `crates/fltk-cst-core/src/span.rs:564` `#[getter] fn kind` returning the same `SpanKind.SPAN` object; `children` confirmed absent from spans on both backends — no `children` in span.rs, none on the `Span` dataclass — and present on nodes: fltk_cst.py:82, cst.rs:492). §4 item 4 now requires self-tests for span-vs-node misdiscrimination in both directions.
- Severity assessment: As written, the comparator would recurse into every span child and raise `AttributeError`, breaking essentially the entire parity corpus on a comparator bug rather than testing parity — or worse, a defensive implementation could silently skip span comparison. High-severity, correctly caught.

design-2:
- Disposition: Fixed
- Action: §2.5 fegen corpus gains an explicit trailing-character bullet (SUCCESS entry ending in a non-whitespace terminal, citing controlling design §4 and `test_trailing_character_bug.py`); the fixture corpus table gains a `test_trailing_character_bug.py` row (with/without-trailing-whitespace pair mapped onto the fixture grammar plus a non-whitespace-terminal SUCCESS entry).
- Severity assessment: Controlling design §4 explicitly lists trailing-character behavior as a parity-corpus input; without these entries a Rust end-of-input final-position divergence (the exact historical Python bug, `fltk/fegen/test_trailing_character_bug.py`) would pass the suite. Cheap to close; requirement-traceability gap, correctly caught.

---

No Won't-Do or TODO items. Design updated in place: `design.md` §2.4, §2.5, §4.
