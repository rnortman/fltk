# Quality review — round 1

Reviewed: `9473bf9..0e6b0c5` (dogfood LSP for fltk's own grammar DSLs).

## quality-1: Regenerated `requirements_lock.txt` drifted — bare `.` self-requirement and dev-group leak into the Bazel pip hub

`requirements_lock.txt:3` (the bare `.` line), plus new entries `maturin==1.13.3` and
`tomli` (`# via maturin`).

The regeneration did not "preserve the existing format" as the design required: relative to the
old file, three things entered that are not pygls transitives — a bare `.` (the project itself,
emitted because `--no-emit-project` wasn't passed), and `maturin`+`tomli` (the `dev` group,
emitted because `--no-dev` wasn't passed; `dev = ["maturin>=1.7,<2"]` in `pyproject.toml:46`
predates this change, so this is uv-behavior drift, not a new dependency).

Consequence: this file is consumed verbatim by `pip.parse` (`MODULE.bazel:24`), and rules_python's
lockfile parser (`python/private/pypi/parse_requirements_txt.bzl`, reached from
`parse_requirements.bzl:96` in the bzlmod path) state-machines a bare `.` line into a requirement
*named* `.` — there is no local-path handling. That poisons the `@pypi` hub for every Bazel
consumer (the stated payoff of the stretch goal), and because test-plan item 9 is manual-only,
nothing in CI catches it. `maturin`/`tomli` additionally bloat the hub with the build backend,
which no `py_*` target needs.

Fix: regenerate with `uv export --format requirements-txt --no-editable --no-dev
--no-emit-project --extra lsp --output-file requirements_lock.txt`, treat *that* as the canonical
command (the file header will then record it), and mirror the intent in the `BUILD.bazel` `lock`
target's `args`. Verify with the documented `bazel run @fltk//:grammar_lsp -- fltkg` smoke (or at
least `bazel query @pypi//...`) before landing.

## quality-2: `Language` enum duplicates `BUILTIN_LANGUAGES` keys, held together by a sync test

`fltk/lsp/grammar_cli.py:596-609` (registry dict + hand-written `Language` enum);
`fltk/lsp/test_grammar_lsp.py::test_language_enum_matches_registry`.

The enum's three members restate the dict's three keys, and a dedicated test exists solely to
keep the two in sync — the classic tell of redundant state. Adding a fourth built-in language
means touching the dict, the enum, and remembering they're joined.

Consequence: a low-grade maintenance tax and a failure mode (forgotten enum member) that only a
meta-test catches, forever.

Fix: derive one from the other. Simplest: build the enum functionally from the registry —
`Language = enum.Enum("Language", {k: k for k in BUILTIN_LANGUAGES}, type=str)` (Typer accepts
functional enums for choice arguments) — and delete the sync test. Alternatively key the registry
by the enum.

## quality-3: `serve()` takes seven positional parameters; call sites pass bare `None`s by position

`fltk/lsp/server_cli.py:35-43`; call sites `server_cli.py:94` and `grammar_cli.py:648`
(`serve(grammar, lsp, fmt, None, width, indent, None)`).

A seven-arg positional signature where two args are `Path | None`, one is `str | None`, and
another is `str | None` is a transposition trap — `serve(grammar, lsp, fmt, None, width, indent,
None)` gives the reader no idea which `None` is `rule` and which is `resolver_spec`, and swapping
`lsp`/`fmt` would type-check.

Consequence: every future parameter (this API just grew a second caller and will likely grow
more, e.g. the resolver-extension TODO from the design's open question 1) extends the positional
minefield; call-site bugs become silent.

Fix: make everything after `grammar` keyword-only with the natural defaults
(`def serve(grammar: Path, *, lsp=None, fmt=None, rule=None, width=80, indent=2,
resolver_spec=None)`) and call with keywords. Callers then pass only what they mean.

## quality-4: Mid-file `noqa: E402` imports in `test_grammar_lsp.py` cargo-cult a guard that isn't there

`fltk/lsp/test_grammar_lsp.py:946-948`: `import pytest_lsp  # noqa: E402 -- optional 'test'
dependency; the module imports fine without a live run`.

The E402 pattern was copied from `test_server_crossfile.py`, where it is *earned*: those imports
must follow a module-level `pytest.skip(..., allow_module_level=True)` guard. Here there is no
guard — the imports are unconditional, so placing them mid-file changes nothing, and the
justification comment is false as written (if `pytest_lsp` is missing, this module fails at
collection regardless of where the import sits).

Consequence: a misleading comment plus a lint suppression that the next reader must decode, and a
pattern that invites more unguarded mid-file imports "because the other test file does it".

Fix: move the three imports to the top of the module and drop the `noqa`s — or, if
installed-distribution runs without the `test` extras are a real scenario, add the same
`pytest.importorskip`/module-level-skip guard the comment implies.

## quality-5: `_SAMPLE_FILES` re-states the registry as repo-relative strings, via a second path-resolution mechanism

`fltk/lsp/test_grammar_lsp.py:792-797` (`_REPO_ROOT` + `_SAMPLE_FILES`).

The nine sample files are exactly the nine files already named by `BUILTIN_LANGUAGES` — every
registry `grammar` is an fltkg sample, every `fmt` an fltkfmt sample, every `lsp` an fltklsp
sample. The test duplicates that set as hand-written repo-relative strings and reaches them
through a parallel `Path(__file__).parents[2]` mechanism, while three lines away the same test
file resolves the same files via `resolve_paths`/`importlib.resources`.

Consequence: two sources of truth for "the packaged spec files". A renamed or added sidecar
updates the registry (guarded by tests 1/5) but silently misses the round-trip test; the
`parents[2]` trick also only works in installed-distribution runs by the accident that all nine
files live inside the package.

Fix: derive the samples from `BUILTIN_LANGUAGES` itself — e.g.
`{"fltkg": [b.grammar per entry], "fltkfmt": [b.fmt ...], "fltklsp": [b.lsp ...]}` materialized
through the existing `resolve_paths` — and delete `_REPO_ROOT`/`_SAMPLE_FILES`.

## quality-6: `language-configuration-fltkfmt.json` and `language-configuration-fltklsp.json` are byte-identical

`editors/vscode/language-configuration-fltkfmt.json` and
`editors/vscode/language-configuration-fltklsp.json` (same git blob, `c558630`).

VS Code's `contributes.languages[].configuration` is just a path; two language entries may point
at the same file.

Consequence: a copy that must be edited twice — the first tweak to bracket/auto-close behavior
for the `fegen`-family languages that lands in only one file creates silent divergence between
two languages that are deliberately specified to share conventions.

Fix: keep one file (e.g. `language-configuration-braces.json`), point both `fltkfmt` and
`fltklsp` entries at it; keep `fltkg`'s separate (it genuinely differs: block comments,
square brackets).
