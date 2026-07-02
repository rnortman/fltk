# Exploration: `TODO(regex-portability-target-list-drift)`

## TODO.md entry (verbatim, current)

`TODO.md:50-52`:

```
## `regex-portability-target-list-drift`

`tests/test_regex_portability.py:test_committed_rust_target_grammar_regex_is_portable` hand-copies the list of Rust-parser-target grammars from the `make gencode` recipe (Makefile lines ~276, 279, 284-285). If a new grammar is added to `gen-rust-parser` in the Makefile without being added to `_RUST_PARSER_TARGET_GRAMMARS` in the test, the completeness check silently fails to cover it. Single-source this list — e.g. a small manifest or glob that both `make gencode` and the test read — to close the drift hole. Tie this to the `gencode-drift-gate` family when that item is burned down. Location: `tests/test_regex_portability.py` (`_RUST_PARSER_TARGET_GRAMMARS` list), `Makefile` (`gencode` recipe).
```

## All `TODO(regex-portability-target-list-drift)` occurrences in-repo

Exactly one `TODO(slug)` code comment exists, plus the `TODO.md` entry and mentions in ADR burndown prose (no other code comments):

- `tests/test_regex_portability.py:505-509` — the code comment (see below).
- `TODO.md:50-52` — the ledger entry (quoted above).
- Prose mentions only (not TODO(slug) comments): `docs/adr/2026/06/14-rust-backend-assessment/burndown/notes-session-autonomy-directives.md:69`, `docs/adr/2026/06/14-rust-backend-assessment/burndown/regex-portability-lint/dispositions-design2.md:80`, `judge-verdict-design2.md:94,132`, `design.md:618`, `implementation-log.md:15`, `notes-prepass-scope.md:28`.

No other file in the tree contains the string `regex-portability-target-list-drift`.

## The test-file comment and list (current, `tests/test_regex_portability.py`)

Lines 491-516:

```python
# ===========================================================================
# Whole-tree completeness check (design §7 -- under-admission guard)
# ===========================================================================
# Every regex in every Rust-parser-target grammar must be portable.
#
# Parser targets (the three grammars fed to gen-rust-parser in make gencode):
#   fegen.fltkg, rust_parser_fixture.fltkg, collision_fixture.fltkg
# (see Makefile lines 276, 279, 284-285).
#
# The other two grammars -- poc_grammar.fltkg, phase4_roundtrip.fltkg -- are
# gen-rust-cst-only (Makefile lines 269-272); the portability check never runs
# against them in production.  Their regexes happen to be portable but they are
# listed as CST-only in the comment below.
#
# TODO(regex-portability-target-list-drift): this list is hand-copied from
# Makefile's gencode recipe.  If a new grammar is added to gen-rust-parser in the
# Makefile without being added here, the whole-tree completeness test will silently
# fail to cover it.  See design §7 for discussion; tie this to the gencode-drift-gate
# family if/when that item is burned down.


_RUST_PARSER_TARGET_GRAMMARS = [
    _FEGEN_FLTKG,
    _RUST_PARSER_FIXTURE_FLTKG,
    _COLLISION_FIXTURE_FLTKG,
]
```

`_FEGEN_FLTKG`, `_RUST_PARSER_FIXTURE_FLTKG`, `_COLLISION_FIXTURE_FLTKG` are `Path` constants defined at `tests/test_regex_portability.py:37-40`:

```python
_ROOT = Path(__file__).parent.parent
_FEGEN_FLTKG = _ROOT / "fltk" / "fegen" / "fegen.fltkg"
_RUST_PARSER_FIXTURE_FLTKG = _ROOT / "fltk" / "fegen" / "test_data" / "rust_parser_fixture.fltkg"
_COLLISION_FIXTURE_FLTKG = _ROOT / "fltk" / "fegen" / "test_data" / "collision_fixture.fltkg"
```

`_RUST_PARSER_TARGET_GRAMMARS` feeds `_RUST_TARGET_CASES` (`tests/test_regex_portability.py:528-540`), which parametrizes `test_committed_rust_target_grammar_regex_is_portable` (`tests/test_regex_portability.py:543-556`) over every regex in each of the three grammars via `_load_grammar_regexes` → `parse_grammar_file` + `collect_regexes`.

## Actual `gen-rust-parser` call sites in the `gencode` recipe today

The `gencode` target spans `Makefile:253-329`. Within it, `gen-rust-parser` (directly or via the `build-fegen-rust-parser` / `gen-rust-parser` sub-targets) is invoked exactly three times:

1. `Makefile:289` — `$(MAKE) build-fegen-rust-parser`, which expands to the recipe at `Makefile:235-237`:
   ```
   build-fegen-rust-parser:
   	uv run python -m fltk.fegen.genparser gen-rust-parser \
   		fltk/fegen/fegen.fltkg crates/fegen-rust/src/parser.rs
   ```
   Grammar: `fltk/fegen/fegen.fltkg`.

2. `Makefile:299`:
   ```
   $(MAKE) gen-rust-parser GRAMMAR=fltk/fegen/test_data/rust_parser_fixture.fltkg RS_OUT=tests/rust_parser_fixture/src/parser.rs
   ```
   Grammar: `fltk/fegen/test_data/rust_parser_fixture.fltkg`.

3. `Makefile:319-320`:
   ```
   uv run python -m fltk.fegen.genparser gen-rust-parser --cst-mod-path super::collision_cst \
   	fltk/fegen/test_data/collision_fixture.fltkg tests/rust_parser_fixture/src/collision_parser.rs
   ```
   Grammar: `fltk/fegen/test_data/collision_fixture.fltkg`.

These three grammars (`fegen.fltkg`, `rust_parser_fixture.fltkg`, `collision_fixture.fltkg`) are exactly the three grammars in `_RUST_PARSER_TARGET_GRAMMARS` today. **The content of the two lists matches — there is no live drift as of `8fd5ecf`.**

## The cited line numbers do not point at `gen-rust-parser` calls, and never did

Both the `TODO.md` entry and the test-file comment cite "Makefile lines ~276, 279, 284-285" (TODO.md) / "276, 279, 284-285" (test comment) as the source of the three-grammar list. In the current Makefile:

- `Makefile:276` — `uv run python -m fltk.fegen.genparser gen-rust-lib src/lib.rs \` (part of the `gen-rust-lib` call, `Makefile:275-277`; this emits `src/lib.rs`, not a parser, and takes no grammar argument).
- `Makefile:279` — `uv run python -m fltk.fegen.genparser gen-rust-cst \` (part of the `gen-rust-cst` call for `poc_grammar.fltkg`, `Makefile:278-280` — a CST-only target, explicitly called out two lines later in the same comment block as *not* a parser target).
- `Makefile:284-285` — part of the `gen-rust-cst` call for `fegen.fltkg` → `crates/fegen-rust/src/cst.rs` (`Makefile:283-287` — CST + protocol-module + `.pyi` stub generation, not parser generation).

None of these three cited lines is a `gen-rust-parser` invocation. The actual `gen-rust-parser` call sites are `Makefile:289`, `299`, and `319-320` (enumerated above).

This mismatch is not recent drift from Makefile edits after the TODO was written: `git show dba6a4b:Makefile` (the commit that introduced both the TODO and the completeness test, `dba6a4b regex-portability-lint: fail codegen on non-portable regexes in grammars`) shows the same structural layout — `gen-rust-lib` immediately followed by `gen-rust-cst` for `poc_grammar.fltkg`, then `gen-rust-cst` for `fegen.fltkg`, then `build-fegen-rust-parser` — with the `gen-rust-parser` calls appearing after, not at, the cited lines. `git log -p --follow -- tests/test_regex_portability.py | grep` confirms the "(see Makefile lines 276, 279, 284-285)" comment text was introduced verbatim in `dba6a4b` and has not been edited since (`git log -S"regex-portability-target-list-drift"` returns only `dba6a4b`). So the line citation was already inaccurate at the moment of authorship, independent of the single-sourcing gap the TODO describes.

## `gencode-drift-gate`

`gencode-drift-gate` is **not** a `TODO.md` entry and has no `TODO(gencode-drift-gate)` code comment anywhere in the tree (`grep -rn "TODO(gencode-drift-gate)"` — no matches; confirmed no `## \`gencode-drift-gate\`` heading exists in `TODO.md`, only `regex-portability-target-list-drift` at `TODO.md:50`).

It exists as a proposed action item in the (non-TODO-system) ADR assessment doc `docs/adr/2026/06/14-rust-backend-assessment/recommended-actions.md:42-58`, phrased as: "Add the regenerate-and-diff gate. Append one step to `Makefile` `check-common`... run `gencode`... then `git diff --exit-code`..." with `Phase: A (step 2)`, `Depends on: none`.

Per `docs/adr/2026/06/14-rust-backend-assessment/burndown/handoff.md:56`, `gencode-drift-gate` is listed among items marked: "Others (`gencode-drift-gate`, `cargo-deny-in-ci`, `differential-property-harness`, `perf-harness`, `clockwork-committed-pin-proof`, `ship-opt-in-first-consumer`, `emission-ir-decision`) | OUT per user STATUS (rejected/deferred/ignored)." So as of that burndown record, `gencode-drift-gate` was explicitly taken out of scope (rejected/deferred/ignored), not merely "not yet burned down." It has not been re-opened as a `TODO.md` entry since.

## Other consumers of the same three grammars (not part of `make gencode`, not referenced by the TODO)

Bazel `BUILD.bazel` files (`BUILD.bazel:103,116,130` and `bazel-fltk/BUILD.bazel:103,116,132`) also declare `generate_rust_parser(...)` macro targets (from `rust.bzl:536`) against `fltk/fegen/fegen.fltkg` and `fltk/fegen/test_data/rust_parser_fixture.fltkg`. These are a separate, parallel build path (Bazel, not `make gencode`) and are not mentioned by the TODO or the test comment; whether they constitute a third place that could drift from the same grammar list is outside what the TODO describes (it scopes the drift risk to `Makefile`'s `gencode` recipe vs. the test's `_RUST_PARSER_TARGET_GRAMMARS`).

## Structural notes on what single-sourcing would touch

- The Makefile has no existing list/manifest construct enumerating "grammars fed to `gen-rust-parser`" — each of the three calls is a separate recipe line (two go through the parameterized `gen-rust-parser` sub-target at `Makefile:225-227`, one — `build-fegen-rust-parser` — hardcodes its grammar path directly at `Makefile:236-237`). There is no Make variable today that lists all three grammar paths together.
- The test does not currently read any Makefile-adjacent manifest; `_RUST_PARSER_TARGET_GRAMMARS` (`tests/test_regex_portability.py:512-516`) is built directly from three independently-declared `Path` constants (`tests/test_regex_portability.py:38-40`), which are themselves not derived from any shared source — they're separately hand-written path literals mirroring (in content, not by reference) the Makefile's `GRAMMAR=` arguments.
