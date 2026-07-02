slop-1:
- Disposition: Fixed
- Action: Reworded the comment at `crates/fltkfmt/tests/cli.rs:270` to state the invariant directly ("Assertions bind only to the stable contract — exit code 2, empty stdout, ...") instead of citing "the original design specified" as the authority.
- Severity assessment: Cosmetic. A code comment referenced an ephemeral planning document that won't resolve for future readers; no behavioral impact, but it reads as leftover planning cruft.

scope (notes-prepass-scope.md):
- Disposition: no findings reported; nothing to act on.
