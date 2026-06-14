# Dispositions: user notes (round 1)

## requirements-user-1: "submodule" meant *Bazel submodule*, not git submodule

User correction (verbatim in notes-requirements-user.md): the requirements
interpreted "submodule" as "git submodule," but the user said "bazel submodule,"
which is correct — FLTK becomes available within Bazel build files as
`@fltk//...`, which is a Bazel submodule. Asked whether exploration and/or
requirements need correction.

- **Disposition:** Fixed
- **Action:**
  - `requirements.md`, Open questions → TODO(dep-mechanism): rewrote the
    "Premise correction" block (now "Premise clarification"). It no longer says
    the request's "submodule" framing is wrong; it explains "submodule" = Bazel
    submodule (`@fltk//...`), resolved by `bazel_dep` + `git_override` pinned to
    a commit (cites `MODULE.bazel:34`, `:89–98`), and reframes the decision as
    keep-the-Bazel-module-source-dep vs. wheel/pip. Removed the "not
    submodule-vs-pip" assertion that contradicted the user.
  - `requirements.md`, same section, option (A): relabeled "Stay with
    `git_override` (source dep)" → "Keep the Bazel-module source dep
    (`@fltk//...` via `git_override`)" to match the corrected terminology.
  - `requirements.md`, User-visible surface → Clockwork `MODULE.bazel` bullet:
    "the existing `git_override` tuple at line 34" → "the existing `bazel_dep` +
    `git_override` tuple at line 34, resolving `@fltk`."
  - `exploration-clockwork.md` §1: the line "Bazel module via `git_override`
    (not a git submodule, ...)" now states FLTK is consumed as a *Bazel
    submodule* available as `@fltk//...`, and clarifies the not-a-git-submodule
    point as a parenthetical rather than the headline.
  - `exploration-fltk.md`: no edit — it contains no git-submodule
    characterization (verified by full read).
- **Severity assessment:** Terminology-only. The actual mechanism described
  (`bazel_dep` + `git_override` pinned by commit, exposed as `@fltk//...`) was
  already correct in both docs and is confirmed against
  `~/tps/clockwork/MODULE.bazel` lines 16/34/89–98. The fix corrects a framing
  that wrongly contradicted the user's chosen term ("submodule"); it does not
  change any acceptance criterion, scope boundary, or the dep-mechanism options
  themselves. Left undone, it would have made the recommendation open by
  "correcting" the user with a premise the user did not hold.
