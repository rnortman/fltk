# Judge verdict — slop/scope prepass 2 (increments 4-6)

Phase: prepass (slop + scope). Base 762bbced..HEAD 0718645. Round 1.
Reviewed commit (responder applied fixes in 0718645 over reviewers' c52d998).
Notes: notes-prepass2-slop.md (5 findings), notes-prepass2-scope.md (1 finding). 6 findings total, all dispositioned Fixed.

## Added TODOs walk

None. No finding was dispositioned TODO this round.

## Other findings walk

### slop-1 — Fixed
Claim: docstring `/// Is this path the stdin sentinel (`-`)?` on `is_stdin` restates the identifier verbatim; consequence is review-slowing noise / LLM tell.
Diff at `crates/fltk-fmt-cli/src/lib.rs:80`: the `///` line is deleted; `fn is_stdin` now stands with its self-evident one-line body. No non-obvious invariant exists to document (`path.as_os_str() == "-"`).
Assessment: fix removes exactly the flagged line and adds nothing spurious. Accept.

### slop-2 — Fixed
Claim: `validate` rustdoc cites "the design's 'CLI behavior summary'" — an external-artifact reference dead to out-of-tree readers.
Diff at `crates/fltk-fmt-cli/src/lib.rs:84-88`: citation clause removed; rustdoc now reads "…to print to stderr (exit code 2): `--in-place` with `--output`, …". The enumerated list of rejected combinations — the informative part — is preserved verbatim.
Assessment: citation dropped, substance kept. Matches the reviewer's prescribed fix. Accept.

### slop-3 — Fixed
Claim: `write_atomic` rustdoc ends with `See design §3 "...write atomicity"` — opaque cross-reference.
Diff at `crates/fltk-fmt-cli/src/lib.rs:117-118`: the `See design §3 …` sentence is removed; the preceding self-contained rationale ("A crash mid-write leaves the original intact (a truncate-then-write would corrupt it).") remains.
Assessment: clean removal; explanation stands alone. Accept.

### slop-4 — Fixed
Claim: `#[macro_export] fltk_formatter_main!` rustdoc (public API) opens with "This is the 'easy reuse' surface from the design:" — process narrative in out-of-tree-visible docs.
Diff at `crates/fltk-fmt-cli/src/lib.rs:177-181`: opener replaced with a direct description — "A consumer crate writes a single invocation naming its grammar's concrete `Parser`/`Unparser` types and the start-rule … method names, and gets a complete formatter binary." The "from the design" framing is gone; the example block follows.
Assessment: process self-talk replaced with caller-facing description, consistent with the reviewer's suggested rewrite. Accept.

### slop-5 — Fixed
Claim: `fltkfmt` binary module doc records "first consumer" / "Almost all of the work lives in …" — a development-moment diary entry that goes wrong once a second consumer exists.
Diff at `crates/fltkfmt/src/main.rs:8-10`: the "first consumer" framing is removed; now leads with the durable fact — "The entire binary is a single `fltk_formatter_main!` invocation (from the reusable `fltk-fmt-cli` scaffolding crate) …" and "Producing a formatter for any other FLTK grammar is the same one invocation with different names."
Assessment: time-bound framing replaced with a durable property. Accept.

### scope-1 — Fixed
Claim: implementation-log increment-4 entry says "15 new `run_inner` integration tests"; actual added count is 13 (base 12 → HEAD 25). Reviewer explicitly states this is a log count error, not a coverage gap — all design §4 `fltk-fmt-cli` behaviors present and tested.
Diff at `docs/workflow/2026-06-27-rust-fltkfmt/implementation-log.md:86`: "15 new" → "13 new". Verified independently: `git show 762bbced:…lib.rs | grep -c '#[test]'` = 12; HEAD = 25; delta = 13. The "25 tests pass" total was already correct.
Assessment: negligible-severity log correction, applied accurately and confirmed by source. Accept.

## Disputed items

None.

## Approved

6 findings: 6 Fixed verified (5 slop doc/comment removals, 1 log count correction). No TODOs, no Won't-Dos. All cosmetic / documentation / log severity; each fix removes exactly the flagged text and preserves the informative substance.

---

## Verdict: APPROVED

All six dispositions acceptable. Every Fixed claim verified against the diff at the named line; scope-1's count corroborated by direct grep. Nothing disputed.
