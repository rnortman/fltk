# Judge verdict — requirements (user-correction pass)

Phase: requirements. Doc: `docs/adr/2026/06/13-rust-bazel-packaging/requirements.md`.
User notes (authoritative): `notes-requirements-user.md`. Round 1.
1 user finding; disposition Fixed.

## Other findings walk

### requirements-user-1 — Fixed

User correction (verbatim): the requirements read "submodule" as *git submodule*,
but the user said **Bazel submodule** — FLTK becomes available in Clockwork's
build files as `@fltk//...`. Consequence (implied): the doc was "correcting" the
user with a premise the user never held (git-submodule-vs-pip), and would have
recommended on a wrong framing. Real consequence — accept.

Source ground truth — `~/tps/clockwork/MODULE.bazel`:
- Line 34: `("fltk", "https://github.com/rnortman/fltk.git", "0afecaf5...", NO_PATCH)` — the FLTK dep tuple, verbatim.
- Line 89: `[bazel_dep(name = name) for ...]` and lines 91–98: `[git_override(module_name = name, commit = commit, ...) for ... if remote.endswith(".git")]`.
So FLTK is declared `bazel_dep` + resolved by `git_override` pinned to a commit, exposed as `@fltk//...`. No `.gitmodules`. The mechanism the docs describe was already correct; only the *framing word* ("submodule") was mis-attributed. The user's term is right.

Edits verified against the disposition's claims:
- `requirements.md` open-questions / TODO(dep-mechanism), "Premise clarification" (lines 183–193): now states `"submodule" means **Bazel submodule** — i.e. FLTK is a Bazel module made available ... as @fltk//...`; explicitly `not a git submodule`; reframes the decision as `keep the Bazel-module source dep ... vs. wheel/pip`. The prior assertion that the user's submodule framing was wrong is gone. Matches the correction.
- `requirements.md` option (A), line 195: `Keep the Bazel-module source dep (@fltk//... via git_override)` — relabeled as claimed.
- `requirements.md` User-visible surface, line 108: `the existing bazel_dep + git_override tuple at line 34, resolving @fltk` — matches source (tuple at 34, bazel_dep at 89, git_override at 91).
- `exploration-clockwork.md` §1, lines 5–8: headline is now `Bazel module via git_override ... a Bazel submodule, available ... as @fltk//...`; the not-a-git-submodule point is demoted to a parenthetical. Matches claim.
- `exploration-fltk.md`: no edit. Full read confirms it contains no "submodule" characterization at all (FLTK-side factual survey only). Correctly left untouched.

Assessment: every edit is source-accurate and directly resolves the user's
correction. The fix adopts the user's term ("submodule" = Bazel submodule),
removes the contradicting "not submodule-vs-pip" assertion, and changes no
acceptance criterion, scope boundary, or dep-mechanism option. Severity
self-assessment (terminology-only) is correct. Accept.

## Approved

1 finding: 1 Fixed verified.

---

## Verdict: APPROVED

The single user correction is dispositioned Fixed and the fix is verified
source-accurate across `requirements.md` and `exploration-clockwork.md`;
`exploration-fltk.md` correctly required no edit. No acceptance criterion or
scope boundary changed.
