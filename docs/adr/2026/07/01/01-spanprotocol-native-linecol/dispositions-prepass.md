# Dispositions — prepass, round 1

slop-1:
- Disposition: Fixed
- Action: Rewrote the docstring paragraph at test_span_protocol_assignability.py:14-17 in present tense — dropped "IS now" / "the headline assertion of that change" / the "(spanprotocol-native-linecol)" diff-tag; states the current invariant ("is statically assigned ... enforces the promise via make check").
- Severity assessment: Cosmetic/maintainability — the diff-relative wording ("now", "that change") goes stale for a future reader with no before-state context, but does not affect behavior or types.

slop-2:
- Disposition: Fixed
- Action: Rewrote the re-export comment at span_protocol.py:7-8 — "has been an importable public name" -> "is an importable public name"; "It is no longer named by any annotation" -> "It is not named by any annotation". Present-tense statement of the current fact.
- Severity assessment: Cosmetic/maintainability — same before/after-narration tell as slop-1, no behavioral impact.

Notes: both are comment/docstring-only edits; no runtime, type, or public-API surface changed. Affected test module still passes (6/6).
