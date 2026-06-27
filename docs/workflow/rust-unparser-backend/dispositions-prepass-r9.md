# Dispositions — prepass r9

Commit: bb96d0e78ae563c4cbad898225c16be02b4baba5

## slop-1
- Disposition: Fixed
- Action: Rewrote the `generate_pyi` docstring in `fltk/unparse/gsm2unparser_rs.py` (~lines 95-118) to drop every "design §2.3", "design OQ-2/OQ-3", and `user answer "Yes, emit .pyi"` phrase; the method contract (what `protocol_module` is, what the returned `.pyi` describes, that it is pure-Python/extension-independent) is retained.
- Severity assessment: Cosmetic but real — design-doc cross-references and conversation transcripts in a docstring are noise for out-of-repo readers and read like an implementation diary. No behavioral impact.

## slop-2
- Disposition: Fixed
- Action: In `fltk/unparse/gsm2unparser_rs.py` `_gen_python_bindings` docstring/comments (lines ~1696-1810): removed `user answer "Please expose the intermediate Doc"`, "design OQ-2", "design §2.1/§2.2/§2.3/§2.4" references; kept the behavioral description (full-pipeline string method, additive `_doc` method, `unsendable` rationale that core `Doc` uses `Rc`).
- Severity assessment: Same class as slop-1 — process-history prose where a contract belongs. Cosmetic.

## slop-3
- Disposition: Fixed
- Action: Dropped "(design OQ-3)" from the `gen_rust_unparser` command docstring in `fltk/fegen/genparser.py:481`; the sentence about the optional `.pyi` stub reads correctly without it. This docstring is the Typer `--help` text, so the parenthetical was user-visible.
- Severity assessment: Minor user-facing polish — a meaningless parenthetical would otherwise appear in CLI `--help`.

## slop-4
- Disposition: Fixed
- Action: In `tests/test_rust_unparser_generator.py`, replaced design-doc references in the four flagged test-body comments (lines ~2147, ~2152, ~2180, ~2206) with the inline testable reason (e.g. "single-threaded" without "by design §2.1"; tightened the fully-qualified-path comment; "An inspection affordance for callers" without "(OQ-2)"; "purely additive" without "design §2.4").
- Severity assessment: Cosmetic test-comment noise; lowered signal-to-noise for future failure diagnosis. No effect on what the assertions check.

## Note on consistency sweep
The same `design §N` / `OQ-N` / `user answer X` pattern appeared in many sibling
docstrings/comments across the three named files beyond the four cited spots (the
slop pass saw a representative diff sample). To avoid leaving identical breadcrumbs
that a later pass would re-flag, all such references in these three files were
stripped in the same commit, preserving the technical rationale in each case.
Real source-location references (e.g. `gsm2unparser.py:267`, `gsm2tree.py:630`) and
the `deep-r1` divergence notes were left intact, as they point to durable code, not
the transient design document.
