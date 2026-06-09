# Design review findings: rust-cst-child-span-test

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Verification scope: every substantive claim in `design.md` checked against HEAD af6e6f3 source. The design's load-bearing claims are all correct: child accessors return `fltk._native.Span` rebuilt via `to_pyobject` (`src/cst_fegen.rs:4307-4323`, `4564-4582`, `4943`, `5322` — all exact); `extract_from_pyobject` rejects non-Span children with `TypeError` "unsupported child type" (`4325-4338`; `RawStringChild`/`LiteralChild` are single-variant `Span` enums at `4674-4676`/`5053-5055`); `.start`/`.end` getters exist (`crates/fltk-cst-core/src/span.rs:354-365`, exact) and `tests/test_rust_span.py:61-68` asserts readability (the staleness exploration's §4 "assert text(), not start/end" is indeed superseded, as the design says); sourceless `text() is None` / `has_source() False` semantics confirmed (`span.rs:218-248,298-300`); source survives the native roundtrip via `source_full_text_str()` + `SourceText(full_text)` + `with_source` (`cst_fegen.rs:4314-4317`); `with_source(start, end, source)` signature confirmed (`span.rs:204-207`); `"hello world!"[3:9] == "lo wor"` is correct; `fltk2gsm.py` refs (24-41, 43-45, 164-166, 168-170, 31, 37-41) all exact; test-file refs (importorskip line 29, tsrc import line 38, TODO comment 111-113, AC8 equality tests 67-87, module docstring all-skip warning) all exact; `CLASS_LABEL_INFO` at `tests/test_fegen_rust_cst.py:43-61` exact, confirming the three (class, append, child) triples and zero-arg construction; `make build-fegen-rust-cst` target exists (`Makefile:64`). Supersession of request.md's "CRITICAL correction" is grounded: following request.md literally is impossible at HEAD (appending `terminalsrc.Span` raises `TypeError`; accessors no longer return it). Requirements coverage is complete (focused test in the named file, localized-failure rationale, TODO slug + comment retirement, build/run verification). No internal contradictions; scope is tight (test-only, three small parametrized tests; the rejection pin is the one authored addition and is explicitly called out as such).

Findings (all minor):

## design-1 — Stale TODO.md line numbers in Cleanup and §"Staleness corrections"

- Quote (design.md:37, :92): "`TODO(rust-cst-child-span-test)` slug (live at `TODO.md:39` ...)"; "Remove the `## rust-cst-child-span-test` entry from `TODO.md` (heading at line 39 plus its paragraph)". Also design.md:13: "`TODO(rust-cst-child-node-identity)` (`TODO.md:44-46`)".
- What's wrong: at HEAD af6e6f3 the `## rust-cst-child-span-test` heading is at `TODO.md:35` (paragraph at :37) and `## rust-cst-child-node-identity` is at `TODO.md:40` (paragraph at :42). Line 39 is the blank line immediately before the **wrong** slug's heading, and 44-46 sits inside the identity entry's paragraph region but not at its heading.
- Why: verified by grep — `TODO.md:35` and `TODO.md:40` are the actual headings. The design claims to be rewritten "against HEAD af6e6f3" (design.md:5), so these are not pre-4c8f0ad leftovers; they were wrong at authoring time.
- Consequence: an implementer who follows the cleanup instruction by line number rather than by slug would start deleting at the blank line before `## rust-cst-child-node-identity` — i.e. risk removing (part of) the wrong TODO entry, which is a live, separate work item. Slug text disambiguates, but the design's stated line numbers actively point at the adjacent entry.
- Fix: cite the headings by slug only, or correct to `TODO.md:35-38` (span-test entry) and `TODO.md:40` (identity entry).

## design-2 — Misplaced citation for the existing `==`-based roundtrip precedent

- Quote (design.md:66): "the existing roundtrip tests already use `==` for this reason (`tests/test_fegen_rust_cst.py:148-155`)".
- What's wrong: lines 148-155 are the body of `test_children_label_returns_list` up to its length assertion; its `==` assertions are at 157-158. The single append/child roundtrip test the design's new tests mirror (`test_append_and_child_roundtrip`, with the clone-on-extraction `==` comment) is at lines 132-139.
- Why: verified by reading `tests/test_fegen_rust_cst.py` at HEAD. The substantive claim (existing tests use `==`, not `is`) is true; only the line range is off.
- Consequence: negligible for correctness — the precedent exists either way — but the citation sends a reader to the middle of a different test, and the design's stated authority is "follows current code (HEAD af6e6f3)". Low-cost correction: cite `tests/test_fegen_rust_cst.py:132-139` (or 126-158 for the class).

## design-3 — New import needs `# noqa: E402` or `make check` fails

- Quote (design.md:41): "Add `from fltk._native import Span, SourceText` to the post-skip import block".
- What's wrong: the design doesn't say the import must carry `# noqa: E402`. Every existing post-`importorskip` import in `tests/test_phase4_fegen_rust_backend.py:34-39` carries `# noqa: E402` because module-level code (the `importorskip` call at line 29) precedes the imports.
- Why: `tests/test_phase4_fegen_rust_backend.py:34-39` (verified — all six imports have the suppression). Ruff E402 fires on any module-level import after non-import statements; `make check` is the precommit gate (CLAUDE.md).
- Consequence: an implementer adding the import exactly as written produces a file that fails `uv run ruff check .` / `make check`. The design's own Test plan lists pytest verification only and would not catch this until the gate. Trivial fix: state the `# noqa: E402` explicitly (matching neighbors).
