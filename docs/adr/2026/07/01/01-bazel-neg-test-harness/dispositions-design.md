# Dispositions — design review round 1 (`bazel-neg-test-harness`)

Notes: `notes-design-design-reviewer.md`. Design: `design.md`.
All three findings fact-checked against the working tree at c03a801 and
`git show 8fd5ecf:` before disposition.

design-1:
- Disposition: Fixed
- Action: Header line in `design.md` changed from `Base commit: 8fd5ecf.` to
  `Base commit: c03a801`, with a parenthetical noting that exploration.md's
  line citations are at 8fd5ecf and differ (TODO.md entry 109-111 there vs.
  59-61 here).
- Severity assessment: Verified real — at HEAD (c03a801) the TODO.md entry is
  at 59-61 and `_require_protocol_module` is called at rust.bzl:603, matching
  the design's citations; at 8fd5ecf the same lines are 109-111 and 604
  (confirmed via `git show`). An implementer cross-checking citations against
  the stated base would find every one off and either distrust the design or
  edit wrong lines. One-line fix eliminates the mismatch.

design-2:
- Disposition: Fixed
- Action: In §1 the snippet's version literal `"1.7.1"` replaced with the
  placeholder `"<latest BCR release>"`, and the parenthetical reworded to say
  the value is substituted at implementation time because the latest release
  is not verifiable from this repo.
- Severity assessment: Low but real — the copyable snippet and the
  instruction next to it disagreed about which wins, and the literal was an
  unverifiable external-registry claim (exploration.md:30 confirms no
  in-tree skylib to check against). Copying verbatim would silently pin a
  possibly-stale version. Placeholder removes the contradiction.

design-3:
- Disposition: Fixed
- Action: §2's struct-instantiation paragraph reworded: the legality claim is
  now explicitly flagged as an external-Bazel-semantics claim with no in-repo
  precedent, with an instruction to verify it first (build the
  `neg_protocol_without_module` target's analysis before writing the rest of
  the suite) and a concrete fallback path (the
  `generate_rust_srcs_for_testing` alias plus adjusting the §3 BUILD snippet).
- Severity assessment: Limited, as the reviewer says — repo-wide search
  confirms no existing struct-exported rule usage to cite, but the design
  already pre-declared the fallback, so a failure costs mid-implementation
  churn (rework of the §3 snippet and the one-exported-name rationale), not
  correctness. Ordering the verification first converts that churn into an
  early, cheap check.
