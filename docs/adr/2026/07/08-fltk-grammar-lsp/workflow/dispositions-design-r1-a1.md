# Dispositions — design review r1 (dogfood LSP for fltk's own grammar DSLs)

Findings from `notes-design-design-reviewer-r1.md`, fact-checked against source at 9473bf9.
All five findings verified accurate; all five Fixed in `design.md`.

design-1:
- Disposition: Fixed
- Action: Rewrote stretch section step 1 ("Get pygls into the Bazel pip graph") to name the
  canonical regeneration command. Verified the reviewer's facts: `requirements_lock.txt:1-2`
  header records `uv export --format requirements-txt --no-editable --output-file
  requirements_lock.txt`, while the Bazel `lock` target (`BUILD.bazel:7-11`) runs
  rules_python's `uv pip compile` with a different output format. The design now declares
  `uv export ... --extra lsp ...` canonical (preserving committed format/provenance), keeps
  the `args = ["--extra", "lsp"]` addition to the Bazel `lock` target so a `bazel run
  //:requirements` rerun cannot silently drop pygls, and states explicitly that the `lock`
  target's output is not what gets committed.
- Severity assessment: High for the stretch goal — without the fix, either `@pypi//pygls`
  never materializes (the new `py_binary` fails to build) or the lock file's format and
  provenance churn as an undesigned side effect.

design-2:
- Disposition: Fixed
- Action: Changed all sketched def/ref kinds from `rule` to `type` in section 1
  (`fegen.fltklsp`: `def name: type;` and `ref rule:identifier: type;`;
  `unparsefmt.fltklsp` and the `fltklsp.fltklsp` extension: `def rule_name: type;`) and
  added a "Kind choice" bullet citing the legend-gating behavior (`lsp_config.py:691-694`,
  `classify.py:287-292`, `features.py` legend) and both in-tree precedents
  (`fltklsp.fltklsp:11`, `test_dogfood.py:27`). Aligned test plan items 2 (paint pinned as
  `type` + `declaration`) and 7 (`def rule_name: type;`). Verified the reviewer's claim:
  the def-site paint is emitted only when `def_stmt.kind[0] in TOKEN_LEGEND`, and `rule` is
  not in `SEMANTIC_TOKEN_TYPES`.
- Severity assessment: Medium-high — as drafted, test plan item 2 could not pass, forcing an
  undesigned implementer decision on the most user-visible surface (rule-name coloring in
  every downstream `.fltkg`).

design-3:
- Disposition: Fixed
- Action: Packaging section now says "six sidecar specs (four new in section 1 + two
  existing)" and clarifies that the wheel-verification list is the five data files that
  exist today, with the four new sidecars landing in the same globbed tree and guarded by
  test plan item 1. Count verified: 4 new (fegen.fltklsp, unparsefmt.fltklsp,
  unparsefmt.fltkfmt, fltklsp.fltkfmt) + 2 existing (fegen.fltkfmt, fltklsp.fltklsp).
- Severity assessment: Low — a consistency slip, not a coverage gap; registry and test plan
  already covered all six.

design-4:
- Disposition: Fixed
- Action: Test plan item 6 now spawns `[sys.executable, "-m", "fltk.lsp.grammar_cli",
  "fltkg"]`, matching the cited harness (verified: `test_server_crossfile.py:62-66` uses
  `sys.executable -m fltk.lsp.server_cli`, not a console script). Section 2 now specifies
  the `if __name__ == "__main__": app()` guard in `grammar_cli.py` (same as
  `server_cli.py:79-80`), required by both the `-m` invocation and the Bazel `py_binary`.
  Noted that the console-script name is covered by item 5's CLI tests via the Typer app
  object.
- Severity assessment: Medium — a console-script spawn fails with a confusing
  FileNotFoundError under stale editable installs and behaves differently in CI vs local,
  the exact papercut the existing `-m` pattern avoids.

design-5:
- Disposition: Fixed
- Action: Dropped the "mitigated by the lazy per-language client start" claim from the
  stretch section. The section now states lock contention is the expected case (VS Code
  session restore reopens editors at activation, starting multiple clients in the same
  tick), that Bazel queues on the lock so the symptom is slow/timed-out startups rather
  than corruption, and presents `--script_path` as the primary recommendation whenever more
  than one fltk language is in use. The matching edge-cases bullet was updated to agree.
- Severity assessment: Low-medium — docs-level only, but the README this section drives
  would have told users the common failure mode was unlikely when it is the default
  multi-file-workspace behavior.

Post-fix cleanup pass (cleanup-editor): aligned test plan item 2's paint wording with the
pinned kind choice and replaced the vague "regex-ish paint" with an explicit note that the
legend has no `regexp` type.
