# Judge verdict — final pre-pass QA

Phase: final pre-pass QA. Base 6f975eb..HEAD f89c809. Round 1.
Notes: notes-final-slop.md (2 findings), notes-final-scope.md (no findings).
Dispositions: dispositions-final-prepass.md — slop-1 Fixed, slop-2 Fixed.

## Added TODOs walk

No TODO-dispositioned findings this round. The two findings in scope are both
Fixed; the scope reviewer reported no findings (so no `scope-N` deferral to
adjudicate). Section omitted — nothing to walk. (Feature-wide TODOs added across
the larger base..HEAD range were dispositioned and judged in the earlier deep /
prepass rounds; not in scope for this final pre-pass adjudication.)

## Other findings walk

### slop-1 — Fixed
Claim: `validate()` has six rejection branches; five have unit tests but the
`check && output.is_some()` branch (lib.rs:104-106, with its own explanatory
comment) is never exercised. Consequence: visible test-count-vs-branch gap, and
no regression guard if `run_inner` dispatch order changes so `--output` is
silently ignored under `--check`.
Disposition action: added `check_with_output_is_rejected` at lib.rs:726-731.
Evidence: the new test parses `["fltkfmt", "--check", "-o", "out.fltkg",
"in.fltkg"]` and asserts `run_args_only(&args) == 2`. With `in_place=false`,
`validate()` skips the first two branches and hits the `check && output.is_some()`
branch at line 104 first — so the test does take the targeted branch and asserts
its exit code. Structurally identical to the five sibling rejection tests
(`in_place_with_output_is_rejected`, etc.) and to the reviewer's own suggested
fix (verbatim). Closes the count gap the finding named.
Note: like all five sibling rejection tests, this one uses non-existent file
paths, so it would also reach exit 2 via the read-error fallback if the branch
were deleted — i.e. it is a parity/count guard, not an isolation guard. That is
the established pattern these tests follow and is not what the finding flagged
(the finding asked for parity with the siblings, which is delivered). Holding the
responder to a stronger standard than the five pre-existing tests would be
inventing a finding the reviewer did not make.
Assessment: fix addresses the comment and consequence; matches the suggested fix
and sibling pattern. Accept. (Severity: nit/low — test completeness on
already-correct behavior.)

### slop-2 — Fixed
Claim: the `identity` stub docstring "returns the source unchanged" restates the
function name and one-line body, adding no information; stands out against the
substantive `upper`/`fail` docstrings beside it.
Disposition action: replaced with a why-focused docstring.
Evidence (diff at lib.rs:585): `/// Stub format_fn: returns the source
unchanged.` → `/// No-op transform: used to verify `--check` exits 0 when input
is already formatted.` Matches the reviewer's suggested why-focused rewrite. The
stub is in fact only consumed by `check_exits_0_when_already_formatted`
(lib.rs:663), so the new docstring is accurate.
Assessment: addresses the finding. Accept. (Severity: trivial/nit — cosmetic,
no behavioral impact.)

## Disputed items

None.

## Approved

2 findings: 2 Fixed verified. notes-final-scope.md: no findings.

---

## Verdict: APPROVED

Both slop findings Fixed and verified against the diff. slop-1 adds the missing
sixth-branch rejection test matching the established sibling pattern; slop-2
replaces a hollow docstring with an accurate why-focused one. No scope findings.
Commit f89c80930a8799aaf476077b572fea449e3024d2.
