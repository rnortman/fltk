# Judge verdict — prepass

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Phase: prepass (slop + scope). Base 108ee61..HEAD 65279b7. Round 1.
Notes: 2 reviewer files; 2 findings (scope: no findings, one informational note).

## Other findings walk

### slop-1 — Fixed
Claim: `test_escape_mixed_xhh_and_uxxxx` input/expected mismatch — visible literal appears to lack `\x80`, so either the test always fails or the diff is unverifiable. Consequence: cross-backend pin test unreviewable from the diff.
Ground truth: byte-level inspection of the pre-fix line shows the input *did* contain raw UTF-8 bytes `0xC2 0x80` (U+0080) — the test was functionally correct, but the C1 char was invisible in the diff, which is exactly the reviewer's stated unverifiability consequence.
Diff at commit 40fbd00, `tests/test_pyrt_errors.py:121`: raw bytes replaced with explicit `\x80` escape; input is now `"\x80‎\tabc"` — fully ASCII-source (the LRM is already the `‎` escape sequence, satisfying the reviewer's "ASCII-safe literals only" suggestion). Expected string unchanged; no behavioral change.
Assessment: fix addresses the consequence at the named line; responder's severity read (readability-only, test was correct) is accurate. Accept.

### slop-2 — Won't-Do
Claim: `pub mod escape;` in `crates/fltk-cst-core/src/lib.rs` exposes more API surface than callers need; suggested `pub(crate) mod escape;`. Consequence stated as "minor API surface leak… Not blocking." Severity: nit by the reviewer's own framing.
Rationale: design-mandated; narrowing would break the re-export path.
Ground truth, two independent grounds:
1. Design §Part (a) (design.md:55) explicitly specifies: "`pub mod escape;` in `fltk-cst-core/src/lib.rs`" with `fltk_cst_core::escape::escape_control_chars` as the canonical public path. Prepass cannot relitigate an explicit design decision.
2. The finding's suggested fix is incorrect Rust: with `pub(crate) mod escape;`, the path `fltk_cst_core::escape::escape_control_chars` is unreachable from *outside* `fltk-cst-core`, so `fltk-parser-core`'s `pub use fltk_cst_core::escape::escape_control_chars;` (errors.rs:89, verified at HEAD) would fail to compile. The reviewer's own note claims the opposite ("pub use of a pub fn from a pub(crate) module works fine from an external crate") — false; `pub(crate)` visibility gates the path for external crates. Making it work would require a root re-export inside `fltk-cst-core`, i.e. a design change the finding does not argue for.
Assessment: Won't-Do sound — design-mandated surface, nit-severity finding, and the proposed alternative is broken as written. Accept.

## Scope note (no disposition required)

Scope reviewer found no findings. Informational note: design test plan #1 said escape tests "move" from `errors.rs` to `escape.rs`; the diff duplicates them (copies remain at `errors.rs:315+`). Reviewer explicitly marked this not a violation (net more coverage; the retained copies also exercise the re-export path). No disposition was owed; none given. No action.

## Approved

2 findings: 1 Fixed verified, 1 Won't-Do sound.

---

## Verdict: APPROVED

Both dispositions acceptable. Round 1.
