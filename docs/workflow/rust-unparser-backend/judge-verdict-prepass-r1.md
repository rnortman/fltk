# Judge verdict — prepass

Phase: prepass (code). Base 8a29f25..HEAD 285064a. Round 1.
Notes: 2 reviewer files (slop, scope); 2 findings + 1 non-blocking scope note.

## Added TODOs walk

No added TODOs in the base..HEAD Rust diff (grep for TODO/FIXME/XXX/HACK over added
`crates/**/*.rs` is empty). The design's deferred `TODO(unparser-deep-tree)` belongs to a
later increment (resolve/render hardening) and is not present in this diff. Nothing to score.

## Other findings walk

### slop-1 — Fixed
Claim: four helper-constructor docstrings in `doc.rs` restate the identifier/parameter name
verbatim (LLM-stub tell); consequence is rendered docs that say nothing beyond the signature
and erode confidence in the load-bearing commentary.
Diff: `text` (doc.rs:132) → "Literal content rendered verbatim: never broken across lines or
re-indented."; `nil` (doc.rs:157) → "The identity element for [`concat`]: contributes no
output and is dropped during concatenation."; `nest` (doc.rs:172) → "Increase indentation by
`indent` spaces while the enclosing group breaks; a no-op when that group fits on one line."
`line` left unchanged, which the reviewer explicitly accepted.
Assessment: each new docstring states semantics the symbol cannot — verbatim/no-reindent,
concat identity + drop, break-conditional indentation. Cosmetic finding, fix addresses the
stated consequence. Accept.

### slop-2 — Fixed (via documentation, behavior unchanged)
Claim: `resolve_spacing` (resolve.rs:615) asserts `sep_spacing.is_some()` but never consults
`required`, an asymmetry with the 2-element patterns (`mutate_after_sep`/`mutate_sep_before`)
which guard `sep_spacing.is_some() || required`; consequence is that a reviewer cannot tell
whether the assert is a correct invariant or a latent crash for
`SeparatorSpec { required: true, spacing: None, preserved_trivia: None }` flanked by both
specs. Reviewer offered two acceptable fixes: add the `required` guard OR document why.
Responder chose to document and explicitly declined the behavioral change.
Verification of the load-bearing claim — Python `_resolve_spacing` (resolve_specs.py:545-560):
after the preserved-trivia branch, `if sep_spec.spacing is None: raise RuntimeError(...)` —
raised **regardless of `required`** (`required` is never read in this function). The
2-element patterns (resolve_specs.py:364, :397) guard `sep_spec.spacing is not None or
sep_spec.required`. So the exact 2-vs-3-element asymmetry the reviewer flagged exists
identically in the Python backend. The added comment (resolve.rs:624-630) states precisely
this and cites resolve_specs.py:555.
Assessment: responder's disposition is correct on the merits. resolve.rs is a literal port
(design §2.1, §3) and the contract is cross-backend rendered-string parity (design §2.4);
adding a `required` guard on the Rust side only would diverge from Python and break that
mandate. Any genuine reachability of this combination is a shared, pre-existing Python issue
whose fix must be a deliberate both-backends change, not an incidental Rust-only superset —
out of scope for a faithful port. The comment resolves exactly the reviewer's stated
consequence (invariant-vs-latent-crash doubt). Accept.

### scope reviewer — no findings
"No findings." Non-blocking log note: increment-2 log claims "16 `#[test]`s" in
accumulator.rs; actual is 15 test functions (a `#[test]`+`#[should_panic]` pair was
double-counted). Reviewer confirms all 15 described scenarios are present and no test is
missing. No disposition required; nothing to dispute.

## Approved

2 findings: 2 Fixed verified (slop-1 doc rewrites; slop-2 parity-documented assert). Scope:
no findings, log-count note is cosmetic with no missing test.

---

## Verdict: APPROVED

Both dispositions acceptable. slop-1 fix carries real information; slop-2's parity claim
checks out against resolve_specs.py:545-560 (Python raises regardless of `required`; the
2-vs-3-element asymmetry is faithfully reproduced) and the decision not to add a Rust-only
`required` guard is the correct call for a parity-mandated port. No added TODOs.
HEAD 285064a9a37c76f56f6fa1b44d4c553c34f49bcc.
