slop-1
File: crates/fltkfmt/tests/cli.rs:270
Quote: "Assertions bind only to the stable contract the original design specified — exit code 2, empty stdout, and a stderr carrying the filename..."
What's wrong: comment cites "the original design" as the authority for the test's scope instead of just stating the invariant.
Consequence: references an ephemeral workflow/design document from in-repo code comments; reads as leftover from an internal planning process rather than a standalone code comment, and the referent won't exist/won't be resolvable to future readers.
Suggested fix: drop "the original design specified" and just state the contract directly, e.g. "Assertions bind only to the stable contract: exit code 2, empty stdout, ...".
