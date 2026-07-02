# slop-reviewer notes

Commit reviewed: a330940ed619771bcb4724be3e53d4f68fd8fcfe..f4de25b006830a7711b0656f0bccdecddadadb9d

## slop-1
- File: tests/test_rust_span.py:1093
- Quote: `"""Regression tests for forged-ABI on the Span path (forged-abi-extract-span-uniformity design).`
- What's wrong: Parenthetical names an ephemeral design/TODO slug rather than describing what the tests verify. The referenced TODO entry is deleted by this same diff (TODO.md), so the docstring points at something that no longer exists in-repo.
- Consequence: Reads as a workflow artifact leaking into shipped code; a reviewer has no document to resolve "(...design)" against once the TODO is gone.
- Suggested fix: Drop the parenthetical; the "Mirrors TestForgedSourceTextRejected" sentence already gives the reader what they need.

## slop-2
- File: tests/test_rust_span.py:1114
- Quote: `The exploration §4 scenario end-to-end: FakeSpan copies both ABI attributes (so`
- What's wrong: References an "exploration" phase document by section number ("§4") — an ephemeral EDTC-process artifact, not something checked into the repo.
- Consequence: Meaningless to anyone who didn't see the exploration doc; the comment should stand on the code's own behavior instead of pointing offstage.
- Suggested fix: Rephrase to describe the scenario directly (which the rest of the docstring already does) and drop the "§4" pointer.

Otherwise: the extensive SAFETY/rationale comments in crates/fltk-cst-core/src/cross_cdylib.rs and span.rs are verbose but match the pre-existing documentation style already used for extract_source_text/get_source_text_type in this file, so not flagged as new tells. No empty catches, swallowed results, or silent fallbacks visible in the diff. No commented-out code.
