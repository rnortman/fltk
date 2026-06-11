# Dispositions: design review round 1 — registry GC/eviction/ABA tests

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Notes reviewed: `notes-design-design-reviewer.md`. All three findings fact-checked against `Makefile`, `tests/test_phase4_rust_fixture.py`, and the design text; all confirmed accurate.

design-1:
- Disposition: Fixed
- Action: §6 rewritten. Verified: `make check` (`Makefile:9-10`) includes `cargo-test` = workspace `cargo test -q` (`Makefile:46-47`); `fltk-cst-core` default features include `python`, which links libpython, and exploration §2 documents the missing-symlink link failure on this machine. §6 now states the caveat, the two remedies (create the symlink, or run the other nine gate steps individually — only `cargo-test` links libpython; `cargo-check`/`clippy` do not), and instructs the implementer not to attribute the failure to this change.
- Severity assessment: Without the fix the stated gate is unsatisfiable on this machine; an implementer would either misdiagnose a pre-existing environment failure as their bug or silently skip verification.

design-2:
- Disposition: Fixed
- Action: §2.3 first paragraph now states classes and `_registry_*` wrappers are taken as attributes of the importorskip'd `phase4_roundtrip_cst` module object (citing `register_classes`, `tests/rust_cst_fixture/src/cst.rs:4844-4861`), and explicitly forbids copying the sibling file's `fltk.plumbing`/`generate_parser` module-level plumbing (`test_phase4_rust_fixture.py:36-55`).
- Severity assessment: Verified the sibling file's preamble does include module-level `parse_grammar_file`/`generate_parser` state (lines 36-55); copying it would add registry-occupying import state to the one GC-sensitive file built to avoid it. Real risk for a copy-the-preamble implementer; the fix removes the ambiguity.

design-3:
- Disposition: Fixed
- Action: §2.2 doc-comment contract rephrased to "small synthetic integer addresses (counter from 1, far below any heap Arc address; weak eviction cleans them up regardless)" — no "< 4096" bound. §2.3 allocator rationale aligned to the same contract ("a few dozen addresses — small integers far below any mappable heap address"), replacing the page-zero phrasing. The two sections now state one contract; nothing unenforced is documented as a bound.
- Severity assessment: Minor doc-drift risk only (safety unaffected in practice — heap addresses are far above either bound), but the safety argument as written would stop matching the code; rephrasing eliminates the drift for free.

All edits are localized fix-ups; cleanup-editor not re-invoked.
