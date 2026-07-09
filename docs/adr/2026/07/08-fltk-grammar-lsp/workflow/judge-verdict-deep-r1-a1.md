# Judge verdict — deep review

Phase: deep. Base 9473bf9..HEAD b269006 (findings reviewed at 0e6b0c5; fixes in b269006). Round 1.
Notes: 7 reviewer files (correctness, security, reuse: no findings); 10 actionable findings + 3 no-finding lanes.

## Added TODOs walk

No finding was dispositioned TODO, and `git diff 9473bf9..b269006` (excluding `docs/`) adds no
`TODO(` comments. Nothing to score.

## Other findings walk

### errhandling-1 — Fixed
Claim: `extension.js` cached the client before `client.start()` and never handled the rejected
start promise; consequence — a transient launch failure silently kills a language's tooling for
the whole session with no retry and no user-visible signal.
Diff at `editors/vscode/extension.js:55-63`: `client.start().catch(...)` now deletes the client
from `clients` (re-enabling retry on next document-open) and calls `window.showErrorMessage` with
the error; `window` added to the vscode destructure. Both halves of the reviewer's "what must
change" (surface + un-cache) are present. `deactivate()` iterates only live map entries, so the
deleted dead client is correctly not stopped.
Assessment: fix addresses the consequence at the named line. Accept.

### errhandling-2 — Won't-Do
Claim: unguarded `BUILTIN_LANGUAGES[language.value]` could KeyError on enum/registry drift —
but the reviewer itself rated this "no change required": Typer restricts input to enum values,
and `test_language_enum_matches_registry` (passing, verified by test run) CI-guards the drift.
Assessment: responder and reviewer agree; a runtime guard would be dead code for a CI-enforced
invariant. Accept.

### test-1 — Fixed
Claim: the design-flagged non-obvious `raw_string.value` → `macro` paint was never asserted.
Diff at `fltk/lsp/test_grammar_lsp.py`: `assert tt(result.tokens, text, "[a-z]+") == "macro"`
added to `test_highlight_fltkg` — exactly the reviewer's proposed assertion. Test passes.
Assessment: pin in place. Accept.

### test-2 — Fixed
Claim: of the 14 hand-authored operator/punctuation literals in `fegen.fltklsp`, only `:=` was
asserted.
Diff: sample text extended to `'foo := name:bar , "lit" | baz ;\n...'`; new assertions `|` →
`operator`, `,` → `punctuation`, `;` → `punctuation`. That is one additional operator plus two
punctuation literals — meets the reviewer's fix ("at least one punctuation literal and one more
operator"). Tests pass.
Assessment: both literal groups now exercised. Accept.

### quality-1 — Fixed
Claim: regenerated `requirements_lock.txt` contained a bare `.` self-requirement (which
rules_python's parser turns into a package named `.`, poisoning the `@pypi` hub — the stated
payoff of the Bazel stretch goal) plus dev-group leakage (`maturin`, `tomli`).
Diff: bare `.` line removed; `maturin==1.13.3` and `tomli` blocks removed; header now records
`uv export ... --no-editable --no-dev --no-emit-project --extra lsp ...`. Verified in the current
file: no `^\.$`/`maturin`/`tomli` lines remain; `pygls`, `lsprotocol`, `cattrs`, `attrs` all
still pinned (4 `==` matches). Responder's claim that `BUILD.bazel` needed no change checks out:
`BUILD.bazel:7-12` `lock` target already carries `args = ["--extra", "lsp"]`, and per the design
(design.md, stretch item 1) the `lock` rule is `uv pip compile`-based, which does not emit the
project or dev group — the committed file's canonical command is the `uv export` one now recorded
in the header.
Assessment: fix complete; the one reviewer suggestion not taken (mirroring extra flags into the
`lock` args) is genuinely inapplicable to `uv pip compile`. Accept.

### quality-2 — Won't-Do
Claim: static `Language` enum duplicates `BUILTIN_LANGUAGES` keys, held in sync only by a
meta-test; recommended deriving the enum functionally from the registry.
Rationale: the recommended functional enum was tried and rejected by pyright —
`reportInvalidTypeForm` ("Variable not allowed in type expression") — because a dynamically
created enum is a variable and cannot annotate the Typer `language` argument. That is real,
documented pyright behavior, and the project mandates pyright-clean code (CLAUDE.md lint gate).
The reviewer's alternative (key the registry by the enum) merely moves the join: a `Language`
member without a registry entry would still need a coverage guard, string-keyed consumers
(`_engine("fltkg")`, test parametrization over `list(BUILTIN_LANGUAGES)`) would need
`Language(...)` conversions, and the duplicated surface is three ids. Responder also added a
docstring at `grammar_cli.py:52-58` explaining why the enum is static and naming the guard test.
Assessment: recommended fix infeasible under the project's type gate; residual duplication is
bounded (3 ids), CI-guarded, and now documented. A long-term owner would not spend more here.
Accept.

### quality-3 — Fixed
Claim: seven positional parameters on `serve()`, callers passing bare positional `None`s — a
transposition trap (`lsp`/`fmt` swap type-checks).
Diff at `fltk/lsp/server_cli.py:34-43`: everything after `grammar` is keyword-only with natural
defaults (`lsp=None, fmt=None, rule=None, width=80, indent=2, resolver_spec=None`). Both call
sites pass keywords: `server_cli.py:95` and `grammar_cli.py:102` (`serve(grammar, lsp=lsp,
fmt=fmt, width=width, indent=indent)` — omitting the defaults it doesn't set, as intended).
Assessment: matches the reviewer's proposed signature exactly. Accept.

### quality-4 — Fixed
Claim: mid-file `noqa: E402` imports cargo-culted a skip-guard pattern that isn't present, with a
false justification comment.
Diff: `pytest_lsp`, `lsprotocol.types`, `ClientServerConfig`/`LanguageClient` moved to the top
import block; all three `noqa` suppressions and the misleading comment deleted.
Assessment: took the reviewer's primary option (imports at top); no guard needed since the
imports were unconditional anyway. Accept.

### quality-5 — Fixed
Claim: `_SAMPLE_FILES` re-stated the registry as repo-relative strings via a parallel
`Path(__file__).parents[2]` mechanism — a second source of truth.
Diff: `_REPO_ROOT` and `_SAMPLE_FILES` deleted; `test_formatting_roundtrip_on_real_files` now
iterates `BUILTIN_LANGUAGES.values()` and resolves each entry's file of the language's kind
(`_SAMPLE_ATTR`) via `resolve_paths`/`importlib.resources`. Coverage is preserved: for each
language the derived set is exactly the old three files (every entry's grammar / fmt / lsp), and
a future added/renamed sidecar is picked up automatically. Test passes for all three languages.
Assessment: single source of truth restored. Accept.

### quality-6 — Fixed
Claim: byte-identical `language-configuration-fltkfmt.json` / `-fltklsp.json`.
Diff: fltkfmt file git-mv'd to `language-configuration-braces.json` (100% similarity), fltklsp
copy deleted; `package.json:46,57` point both language entries at the shared file; `fltkg` keeps
its own (block comments, square brackets — genuinely different).
Assessment: matches the reviewer's fix, including keeping `fltkg` separate. Accept.

### efficiency-2 — Fixed
Claim (test-lane, optional): `_format` regenerated parser+unparser per call — ~18 codegen runs
where 3 suffice.
Diff: parser/unparser generated once per language inside the round-trip test; `_format` is now a
closure doing only parse/unparse/render. Folded into the quality-5 rewrite.
Assessment: exactly the reviewer's direction. Accept.

### correctness / security / reuse / efficiency-1 — no findings
Reviewers reported no findings; the security reviewer's note documents what was checked (machine-
scoped server command, no resolver_spec from the new entry point, stdio-only, pinned hashed deps).
"Won't-Do (nothing to act on)" is the correct null disposition. Accept.

## Verification

`uv run pytest fltk/lsp/test_grammar_lsp.py`: 15 passed at HEAD, including the new paint
assertions, the registry-derived round-trip, the enum-sync guard, and the e2e pytest-lsp session.

## Disputed items

None.

## Approved

13 dispositions: 8 Fixed verified, 2 Won't-Do sound (errhandling-2, quality-2), 3 no-finding
lanes correctly null. No TODOs added.

---

## Verdict: APPROVED

Every Fixed disposition is verified against the diff at the named lines and the touched tests
pass; both substantive Won't-Dos rest on verified facts (reviewer's own "no change required";
a real pyright `reportInvalidTypeForm` constraint) rather than convenience.
