# Dispositions — deep review round 1

Commit base 9473bf9 / reviewed 0e6b0c5. No `scope-N` findings, so no escalation.

## errhandling-1

- Disposition: Fixed
- Action: `editors/vscode/extension.js:55-63` — `client.start()` now has a `.catch` that removes
  the client from the `clients` map and shows a `window.showErrorMessage`; added `window` to the
  `require("vscode")` destructure. A failed/transient launch is now surfaced and retryable on the
  next document-open instead of caching a permanently-dead client.
- Severity assessment: A one-time launch failure (missing uv, bad `server.command`, pygls-less env,
  contention) otherwise silently killed a language's tooling for the whole session with no
  editing-surface signal.

## errhandling-2

- Disposition: Won't-Do
- Action: no change.
- Severity assessment: A raw `KeyError` traceback instead of a clean message, but only reachable if
  the `Language` enum and `BUILTIN_LANGUAGES` drift — a developer invariant, not a runtime input.
- Rationale (Won't-Do): The reviewer explicitly rated this "no change required." Typer restricts
  `language` to enum values and the values are literally the dict keys; the drift is CI-guarded by
  `test_language_enum_matches_registry`, so it cannot ship broken. Adding a runtime guard would be
  dead code for an invariant already enforced at test time.

## correctness (no findings)

- Disposition: Won't-Do (nothing to act on)
- Action: no change.
- Severity assessment: n/a — reviewer reported no findings.

## security (no findings)

- Disposition: Won't-Do (nothing to act on)
- Action: no change.
- Severity assessment: n/a — reviewer reported no findings.

## reuse (no findings)

- Disposition: Won't-Do (nothing to act on)
- Action: no change.
- Severity assessment: n/a — reviewer reported no findings.

## test-1

- Disposition: Fixed
- Action: `fltk/lsp/test_grammar_lsp.py:76` (`test_highlight_fltkg`) — added
  `assert tt(result.tokens, text, "[a-z]+") == "macro"`, pinning the `raw_string.value` → `macro`
  regex-body paint that the design calls out as a non-obvious choice.
- Severity assessment: Deleting/mistyping the `raw_string` scope in `fegen.fltklsp`, or a regression
  to the default paint, would previously ship silently.

## test-2

- Disposition: Fixed
- Action: `fltk/lsp/test_grammar_lsp.py:64-90` — extended the sample text to
  `'foo := name:bar , "lit" | baz ;\nbar := /[a-z]+/ ;\nbaz := "x" ;\n'` and added assertions that
  `|` → `operator`, `,` → `punctuation`, `;` → `punctuation` (in addition to the existing `:=`),
  exercising both hand-authored literal groups.
- Severity assessment: A literal left out of / moved between the operator/punctuation groups, or a
  transcription typo, would previously go undetected.

## quality-1

- Disposition: Fixed
- Action: regenerated `requirements_lock.txt` with `uv export --format requirements-txt
  --no-editable --no-dev --no-emit-project --extra lsp`. The bare `.` self-requirement (poisoned the
  `@pypi` hub as a package literally named `.`) and the dev-group leak (`maturin`, `tomli`) are gone;
  `pygls` and its transitives remain. Verified: the only `==` deltas vs. the reviewed file are the
  removals of `maturin` and `tomli`; no bare `.`/`maturin`/`tomli` lines remain; header records the
  new command. `BUILD.bazel` `lock` already carries `args = ["--extra", "lsp"]`, and its underlying
  `uv pip compile` does not emit the project or dev group, so no change was needed there.
- Severity assessment: The bare `.` line breaks `pip.parse` for every Bazel consumer — the stated
  payoff of the stretch goal — and nothing in CI (item 9 is manual) would have caught it.

## quality-2

- Disposition: Won't-Do
- Action: no change (kept the static `Language` enum + `test_language_enum_matches_registry`; added
  a docstring at `fltk/lsp/grammar_cli.py:52` explaining why it is static).
- Severity assessment: A small bounded duplication (three ids) guarded by a meta-test; a forgotten
  enum member is caught at CI time.
- Rationale (Won't-Do): The recommended fix — `Language = enum.Enum("Language", {...}, type=str)`
  derived from the registry — was implemented and rejected by pyright:
  `grammar_cli.py:...: error: Variable not allowed in type expression (reportInvalidTypeForm)`,
  because a dynamically-created enum is a variable and cannot be used as the type annotation of the
  Typer `language` argument. CLAUDE.md mandates pyright-clean code, and the annotation is required
  for the typed Typer choice argument. The static enum is the necessary cost of static typing here;
  the sync test is the intentional, cheap guard for a three-element bounded set.

## quality-3

- Disposition: Fixed
- Action: `fltk/lsp/server_cli.py:35-43` — everything after `grammar` is now keyword-only with
  natural defaults (`def serve(grammar, *, lsp=None, fmt=None, rule=None, width=80, indent=2,
  resolver_spec=None)`). Both call sites pass keywords: `server_cli.py:94`
  (`serve(grammar, lsp=lsp, fmt=fmt, rule=rule, width=width, indent=indent, resolver_spec=resolver)`)
  and `grammar_cli.py:97` (`serve(grammar, lsp=lsp, fmt=fmt, width=width, indent=indent)`).
- Severity assessment: The prior seven-positional signature with several `Path | None`/`str | None`
  args was a transposition trap where a swapped `lsp`/`fmt` would still type-check.

## quality-4

- Disposition: Fixed
- Action: `fltk/lsp/test_grammar_lsp.py` — moved `import pytest_lsp`, `from lsprotocol import types
  as t`, and `from pytest_lsp import ClientServerConfig, LanguageClient` to the top import block and
  dropped the three `# noqa: E402` suppressions and the false "imports fine without a live run"
  justification (the imports are unconditional, so their position never mattered).
- Severity assessment: A misleading comment and a lint suppression guarding nothing, inviting
  copycat unguarded mid-file imports.

## quality-5

- Disposition: Fixed
- Action: `fltk/lsp/test_grammar_lsp.py` — deleted `_REPO_ROOT` and the hand-written `_SAMPLE_FILES`
  string table; `test_formatting_roundtrip_on_real_files` now derives its samples from
  `BUILTIN_LANGUAGES` via `resolve_paths`/`importlib.resources` (the per-language file kind is picked
  by `_SAMPLE_ATTR`), removing the second `Path(__file__).parents[2]` path mechanism and the second
  source of truth for the packaged spec files.
- Severity assessment: A renamed/added sidecar updated the registry but silently missed the
  round-trip test; the `parents[2]` trick only worked by the accident that all files live in-package.

## quality-6

- Disposition: Fixed
- Action: `editors/vscode/` — the byte-identical `language-configuration-fltkfmt.json` and
  `language-configuration-fltklsp.json` are collapsed into one `language-configuration-braces.json`
  (git-mv of the fltkfmt file, git-rm of the fltklsp file); `package.json` points both the `fltkfmt`
  and `fltklsp` language entries at it. `fltkg` keeps its own file (block comments, square brackets).
- Severity assessment: Two copies that must be edited in lockstep; the first divergent tweak would
  silently split two languages specified to share conventions.

## efficiency-1 (no findings)

- Disposition: Won't-Do (nothing to act on)
- Action: no change.
- Severity assessment: n/a — reviewer reported no product-code findings.

## efficiency-2

- Disposition: Fixed
- Action: `fltk/lsp/test_grammar_lsp.py:142-165` — the round-trip test now generates the parser and
  unparser once per language (they depend only on grammar+cfg) via a closure `_format`, instead of
  regenerating them inside the old module-level `_format` on every call (~18 regenerations → 3).
  Folded into the quality-5 rewrite of the same test.
- Severity assessment: Test-suite wall time only; no production impact.
