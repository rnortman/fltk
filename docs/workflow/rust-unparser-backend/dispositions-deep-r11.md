# Dispositions — deep review r11

Commit reviewed: fabdc5a2ea6f4ca1ecc42386a4a5f40a8e776dd4
Base: 0494f3127dd09141e7bc0f0b918862feaf449f46

Reviewers with no findings: correctness, security.

---

errhandling-1:
- Disposition: Fixed
- Action: `Makefile` `gencode` protocol-module step. Replaced the `;`-chained block
  with `set -e; tmpdir=$(mktemp -d); trap 'rm -rf "$tmpdir"' EXIT; <generate>; <cp>`.
  `set -e` aborts the line on any failure; the EXIT trap cleans the temp dir on both
  success and failure. A generator or `cp` failure now propagates a non-zero exit to
  Make instead of being masked by a trailing `rm` that always exits 0. Verified the
  three shell paths (success → 0; generator-fail → non-zero, no stale copy; cp-fail →
  non-zero) in isolation.
- Severity assessment: Real. `make gencode` could exit 0 with a stale/absent committed
  protocol module after a generator crash, leaving the `.pyi`'s `node` types checked
  against an old protocol with no Make-level signal in CI.

quality-3:
- Disposition: Fixed
- Action: Same change as errhandling-1 (`Makefile` `gencode` step). This is the same
  defect reported by two reviewers; one fix covers both. The chosen `set -e` + EXIT
  trap form also addresses the reviewer's deeper note that the naive `&&`-then-`;`
  form still ends with `rm`'s (always-0) exit code.
- Severity assessment: Same as errhandling-1.

test-1:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_pyi.py`. Added `_CONSUMER_BAD_NARROWING` (assigns
  `unparse_num`'s `str | None` return to a bare `str`) written to
  `consumer_bad_narrowing.py` in the existing batched fixture, plus
  `test_consumer_return_keeps_optional` asserting a `reportAssignmentType`/`reportArgumentType`
  error. This errors only if the stub keeps `| None`, so it guards against a silent
  drop of `| None` that the OK consumer (assigns into a `str | None` target) cannot
  detect. Verified: pyright runs and the test passes.
- Severity assessment: Genuine coverage gap. A manual or generator regression dropping
  `| None` from the return type would mislead downstream callers relying on `None`
  ("could not unparse") with no test catching it.

test-2:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_pyi.py`. Added `_CONSUMER_BAD_RENDER` (assigns
  `Doc.render()`'s `str` return to a bare `int`, under an `is not None` guard) written
  to `consumer_bad_render.py`, plus `test_consumer_render_returns_str` asserting a
  `reportAssignmentType` error. This errors only if `render()` is a concrete `str`, so
  it proves the return is not `Any`. Verified: pyright runs and the test passes. Both
  new files are written into the same module-scoped fixture, preserving the single
  batched pyright run (no per-test spawning).
- Severity assessment: Genuine coverage gap, parallel to test-1, for `Doc.render()`.

reuse-1:
- Disposition: Fixed
- Action: `tests/pyright_test_utils.py` gained a shared `pyright_runnable()` probe
  (and `import shutil`); `tests/test_rust_unparser_pyi.py` removed its private
  `_pyright_available()` and now defines `pyright_available` as a one-line fixture
  delegating to `pyright_runnable()`. The duplicated probe logic now lives in the
  shared module the file already imports from, instead of adding a fourth copy.
  (The three pre-existing inline copies in `test_gsm2tree_rs.py`,
  `test_clean_protocol_consumer_api.py`, and `fltk/fegen/test_cst_protocol.py` are
  outside this design's diff and left untouched; the shared home now exists for a
  later cross-file consolidation.)
- Severity assessment: Maintainability. Without this the probe would have a fourth
  divergent copy; a future change to the availability check would need patching in
  more places.

quality-1:
- Disposition: Fixed
- Action: Same change as reuse-1. quality-1 (inline the redundant `_pyright_available`
  wrapper to match the three existing files) and reuse-1 (consolidate into the shared
  util) point at the same redundant helper from opposite directions. Resolved by
  consolidation rather than inlining: the redundant single-call-site private helper is
  gone, and the remaining one-line fixture is a necessary pytest-DI adapter over the
  shared `pyright_runnable()` (it carries real abstraction value — a plain function
  cannot be a fixture dependency), which is what quality-1's underlying objection was
  about. Consolidation also satisfies reuse-1, so the two findings do not conflict in
  outcome.
- Severity assessment: Quality/consistency; same redundancy as reuse-1.

reuse-2:
- Disposition: Fixed
- Action: `tests/pyright_test_utils.py` — `write_pyright_config` gained a keyword-only
  `extra_paths: list[str] | None = None` that is emitted as `extraPaths` when given
  (backward compatible; existing callers unaffected). `tests/test_rust_unparser_pyi.py`
  replaced its inline `json.dumps({...})` pyrightconfig write with
  `write_pyright_config(tmpdir, extra_paths=[repo_root, fltk/_stubs])`. Verified the
  other two callers (`test_clean_protocol_consumer_api.py`, `test_cst_protocol.py`)
  still pass.
- Severity assessment: Maintainability. The inline copy duplicated the three base
  config keys the helper owns; the venv/python-version convention would otherwise
  drift across copies.

quality-2:
- Disposition: Fixed
- Action: Same change as reuse-2 (same defect, two reviewers).
- Severity assessment: Same as reuse-2.

efficiency-1:
- Disposition: Fixed (round 2 — was TODO(unparser-gencode-protocol-only); the judge ruled
  the work mechanical, fully-specified, and doable-now, so a parked TODO was not acceptable.)
- Action: Implemented the `--protocol-only` flag on the `generate` subcommand and rewired the
  `gencode` recipe to use it, dropping the temp-dir dance.
  - `fltk/fegen/genparser.py` (`generate`): added `--protocol-only` option. When set, the
    command builds the trivia-enhanced grammar + `CstGenerator` once, writes only
    `<base>_cst_protocol.py`, and returns early — the shared CST module write and both parser
    generations are now gated behind `if not protocol_only:`. Added a mutual-exclusion guard
    (`--protocol-only` with `--trivia-only`/`--no-trivia-only` exits 1, since no parsers are
    produced). The verbose CST-path summary no longer reads the now-conditional `shared_cst`
    local (recomputed inline) to keep pyright's possibly-unbound check happy.
  - `Makefile` (`gencode`, the fixture protocol step): replaced the
    `mktemp -d` + `set -e`/EXIT-trap + full-suite `generate` + `cp` block with a single
    `generate --protocol-only ... --output-dir tests` invocation that writes
    `tests/rust_parser_fixture_cst_protocol.py` directly. The errhandling-1 masking concern is
    moot — there is no longer a trailing `rm`/`cp`; the lone `generate`'s exit status is the
    line's status.
  - `TODO.md`: removed the `unparser-gencode-protocol-only` entry (work done).
  - `fltk/fegen/test_genparser.py`: added `test_generate_protocol_only_emits_only_protocol`
    (writes only the protocol module; no CST, no parsers), `test_generate_protocol_only_matches_full_run`
    (byte-identical protocol output vs a full `generate`), and
    `test_generate_protocol_only_rejects_trivia_flags` (mutual-exclusion error, nothing written).
  - Verified: 46/46 genparser tests pass; running the new `gencode` protocol step + `ruff` leaves
    `tests/rust_parser_fixture_cst_protocol.py` byte-identical (clean `git diff`); repo-wide ruff
    check, ruff format --check, and pyright are clean.
- Severity assessment: Negligible runtime/correctness impact (dev-workflow-only redundant codegen
  over one small fixture grammar); fixed as a cleanliness item per the judge's do-now ruling.
