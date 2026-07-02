# slop-reviewer notes

## slop-1
- File: fltk/fegen/pyrt/test_span_protocol_assignability.py:14-18
- Quote: "Native ``fltk._native.Span`` IS now statically assigned into a ``SpanProtocol`` slot here ... so this native pin is the headline assertion of that change: the \"near-drop-in Rust backend\" promise made static and enforced by ``make check`` on every future edit."
- What's wrong: Changelog/narrative comment — describes the diff's own history ("IS now", "the headline assertion of that change") rather than documenting a current invariant. Reads as the author talking about the PR to itself instead of explaining the code to a future reader who never saw the "before" state.
- Consequence: Once merged, "now" and "that change" become meaningless/stale to anyone reading the file later with no diff context — a classic tell that the docstring was drafted from the diff, not from the code's steady-state meaning.
- Suggested fix: Rewrite as a present-tense statement of fact, e.g. "Native `fltk._native.Span` is statically assignable to a `SpanProtocol` slot here ... which enforces the near-drop-in Rust-backend promise via `make check`."

## slop-2
- File: fltk/fegen/pyrt/span_protocol.py:7-10
- Quote: "``LineColPos`` is re-exported for backward compatibility ... It is no longer named by any annotation in this module (the protocols use ``LineColPosProtocol``)"
- What's wrong: "no longer" narrates a before/after transition rather than stating the current fact plainly (the import exists solely for re-export; it isn't used as an annotation).
- Consequence: Minor, but same pattern as slop-1 — comment is written relative to the diff instead of the code's own timeline.
- Suggested fix: "It is not named by any annotation in this module (the protocols use ``LineColPosProtocol``); the import exists solely to preserve the public re-export."

No blocking issues found otherwise: the new `LineColPosProtocol`, its assignability pins, and the AST-based stub-stability guard test are consistent with the file's pre-existing dense-docstring convention, syntactically valid, and the TODO.md / inline TODO removal is a clean, complete match (no orphaned TODO(spanprotocol-native-linecol) references left behind).
