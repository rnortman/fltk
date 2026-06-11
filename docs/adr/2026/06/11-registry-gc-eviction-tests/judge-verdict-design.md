# Judge verdict — design review

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Phase: design. Doc: `docs/adr/2026/06/11-registry-gc-eviction-tests/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 3 findings, all dispositioned Fixed.

## Findings walk

### design-1 — Fixed
Claim: §6 asserted "`make check` clean" while §1 itself cites the pre-existing `cargo-test` libpython link failure; consequence is the implementer misattributing or silently skipping the gate.
Design §6 now: states the caveat, names `Makefile:46-47` / workspace `cargo test -q`, gives both remedies (create the symlink, or run the other gate steps individually), and instructs "Do not attribute the link failure to this change."
Verified against `Makefile:9-10`: the `check` target's step list is `lint format-check typecheck test cargo-check cargo-clippy cargo-test cargo-test-no-python cargo-clippy-no-python check-no-pyo3`; the nine steps enumerated in §6 are exactly that list minus `cargo-test`. "Only `cargo-test` links libpython" holds: `cargo-check` is `cargo check -q` (no link step); clippy lanes likewise; the no-python lanes use `--no-default-features` / `-p` isolation.
Assessment: fix addresses the consequence with both of the reviewer's suggested remedies. Accept.

### design-2 — Fixed
Claim: §3 tests construct `Entry()`/`Identifier()` but the design never said how the file obtains the classes; consequence is a copy-the-preamble implementer importing `fltk.plumbing` and adding registry-occupying module state to the one GC-sensitive file.
Design §2.3 now: classes and `_registry_*` wrappers are taken as attributes of the importorskip'd `phase4_roundtrip_cst` module object (cites `register_classes`, `tests/rust_cst_fixture/src/cst.rs:4844-4861`), and explicitly forbids copying the sibling's `fltk.plumbing`/`generate_parser` plumbing (`test_phase4_rust_fixture.py:36-55`).
Verified `test_phase4_rust_fixture.py:36-55`: module-level `fltk.plumbing` import, `parse_grammar_file`, and two `generate_parser` calls are exactly there; the cited line range is accurate (reviewer's 48-57 and responder's 36-55 both cover the plumbing block).
Assessment: one-sentence fix the reviewer asked for, plus the explicit prohibition. Accept.

### design-3 — Fixed
Claim: §2.2 doc-comment contract ("< 4096") and §2.3 allocator (`itertools.count(1)`, unbounded) stated different contracts for the same addresses; consequence is the safety argument silently drifting false.
Design now: §2.2 doc contract reads "small synthetic integer addresses (counter from 1, far below any heap Arc address; weak eviction cleans them up regardless)"; §2.3 reads "a few dozen addresses — small integers far below any mappable heap address." No "< 4096" remains anywhere in the doc; the two sections state one contract and nothing unenforced is documented as a bound.
Assessment: matches the reviewer's first suggested phrasing. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED

All dispositions acceptable; every fix verified in the revised design and source-checked.
