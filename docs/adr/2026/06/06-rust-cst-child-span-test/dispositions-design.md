# Dispositions: design review round 1 — rust-cst-child-span-test

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Notes file: `notes-design-design-reviewer.md`. All findings fact-checked against HEAD af6e6f3 source before disposition.

design-1:
- Disposition: Fixed
- Action: Verified against `TODO.md` at HEAD: `## rust-cst-child-span-test` heading is at line 35 (entry spans 35-37); `## rust-cst-child-node-identity` heading is at line 40 (entry 40-42). Corrected all three citations in design.md: Staleness corrections bullet (now `TODO.md:40-42`), Root cause / context (now `TODO.md:35-37`), and Cleanup (now "locate by slug heading (at line 35; entry spans lines 35-37)" plus an explicit do-not-touch note for the adjacent identity entry at line 40).
- Severity assessment: The stated line 39 pointed at the blank line before the *wrong* slug's heading; an implementer deleting by line number could remove part of the live `rust-cst-child-node-identity` entry. Slug text disambiguates, but the design's numbers actively misdirected.

design-2:
- Disposition: Fixed
- Action: Verified against `tests/test_fegen_rust_cst.py` at HEAD: lines 148-155 are the body of `test_children_label_returns_list` (its `==` asserts are at 157-158); the single-child roundtrip the new tests mirror is `test_append_and_child_roundtrip` at 132-139, with the clone-on-extraction `==` comment at 138. Corrected the citation in Proposed approach to name the test and cite `tests/test_fegen_rust_cst.py:132-139`.
- Severity assessment: Negligible correctness impact — the `==`-not-`is` precedent exists either way — but the citation sent readers to the middle of a different test in a doc whose authority is precise HEAD citations.

design-3:
- Disposition: Fixed
- Action: Verified: all six post-`importorskip` imports at `tests/test_phase4_fegen_rust_backend.py:34-39` carry `# noqa: E402`; the `importorskip` call at line 29 precedes them, so a bare new import fails ruff E402 and therefore `make check`. Proposed approach now spells the import as `from fltk._native import Span, SourceText  # noqa: E402` and states why the suppression is mandatory, citing the neighboring imports.
- Severity assessment: An implementer following the design verbatim would pass pytest but fail the `make check` precommit gate — caught late, after the design's stated verification steps all pass.
