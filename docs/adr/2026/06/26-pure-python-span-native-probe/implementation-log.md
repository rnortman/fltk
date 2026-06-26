# Implementation Log: Two backends only (Python ⇒ Python span/CST; Rust ⇒ Rust span/CST)

Design: `./design.md`
Requirements: `./requirements.md`
Base commit: `49e9701e927d1403065f902b99d54acd7c129e41`

---

## Increment 1 — remove the backend-probe warning from `span.py` (§2.2)

- `fltk/fegen/pyrt/span.py:9-15`: removed the `warnings.warn(...)` call and the
  `import warnings` line. The `try/except` native re-export is kept (probe still selects
  native when built). The `except` branch now imports the pure-Python `terminalsrc` backend
  silently — no warning. The top-level `terminalsrc` import was folded into the `except`
  branch so the fallback does real work rather than a bare `pass` (ruff S110), keeping the
  silent-fallback behavior the design specifies.
- `tests/test_span_protocol.py:1-40`: added `TestBackendSelectorSilentFallback` — reloads
  `span.py` with `fltk._native` forced to `None` in `sys.modules` under
  `warnings.simplefilter("error")`, asserting no warning fires and the fallback lands on the
  pure-Python `Span`/`SourceText`; restores the real backend afterward.
- Deviation (minor): design §2.2 said "keep the top-level `terminalsrc` import; the except
  branch falls back silently." A bare `except: pass` trips ruff S110, so the fallback import
  was moved into the `except` branch instead. Same observable behavior (silent pure-Python
  fallback), lint-clean. `span.py` selector semantics and `__all__` unchanged.
- Tests: `tests/test_span_protocol.py` all 46 pass (incl. the new test and the preserved
  `TestBackendSelector` selector assertions). ruff check + format + pyright clean on both
  touched files.

---

## Increment 2 — §2.1: Python parser always constructs `terminalsrc` types — BLOCKED (clarification needed)

The §2.1 code change was made and its own tests pass, but it exposes a **design gap**: the
generated *unparser* rejects the parser's pure-Python spans whenever `fltk._native` is importable.
Nothing was committed; the working tree is dirty pending a design decision. Detail in
`../../../../clarification-needed.md` (repo-root `clarification-needed.md`).

Work done (uncommitted, in the working tree):

- `fltk/fegen/gsm2parser.py`: retargeted both runtime construction sites to the pure-Python
  `terminalsrc` module, decoupled from the type registry:
  - `_make_span_expr` (`:259-`): span class ref is the fixed string
    `"fltk.fegen.pyrt.terminalsrc.Span"`; docstring updated.
  - `_source_text` initializer (`:105-`): replaced `Construct(SourceTextType, ...)` with
    `MethodAccess("SourceText", VarByName("fltk.fegen.pyrt.terminalsrc")).call(...)`.
  - Verified the generated parser source emits
    `fltk.fegen.pyrt.terminalsrc.Span.with_source(...)` / `terminalsrc.SourceText(...)`;
    registry entries left at the `span` module (§2.4), so annotations are unchanged.
- `tests/test_python_parser_span_backend.py` (new): 4 tests — root/child node span is
  `terminalsrc.Span`, `_source_text` is `terminalsrc.SourceText`, and (native present) not a
  native span. All pass; ruff + pyright clean.

Blocker (the reason for the stop):

- The generated unparser's span-type guards are probe-bound, not dual-backend like the CST
  mutators. `fltk/unparse/gsm2unparser.py` builds the guard type via
  `iir.Type.make(cname="Span")` (`:87`, used at `:328`, `:1013-1014`, `:1116-1117`), which the
  IIR compiler resolves through the registry to `fltk.fegen.pyrt.span.Span`. In a native-present
  process the probe makes that `is fltk._native.Span`, so the emitted
  `isinstance(child, fltk.fegen.pyrt.span.Span)` returns False for the parser's `terminalsrc.Span`
  children → `unparse_*` returns None → `plumbing.unparse_cst` raises
  `ValueError("Unparsing failed")`.
- This contradicts design §2.5 ("`make check` stays clean", "no diff beyond parser changes") and
  the requirement that all CST-consuming code stay backend-agnostic. The CST mutators already do
  the dual check (`regex_cst.py:744-750`: `(... , terminalsrc.Span)` + `_get_native_span_type()`),
  but the design never mentions the unparser, and no planned increment fixes it.
- Tests broken by §2.1 in a native-present env (green on clean HEAD):
  `fltk/test_plumbing.py::TestUnparsing::test_unparse_simple_expression`,
  `::TestUnparsing::test_unparse_with_auto_rule`, `::TestIntegration::test_full_pipeline`,
  `::TestIntegration::test_pipeline_with_formatting`.

Proposed resolution (full detail in `clarification-needed.md`): widen the unparser's span guards
in `gsm2unparser.py` to the dual-backend pattern §2.4 already blesses, add unparser files to the
§2.5 regen, and add a native-present round-trip regression test. Awaiting a design decision; not
improvising an out-of-scope codegen change.

---

## Increment 3 — §2.6(a): dual-backend `is_span` helper + retarget unparser span guards

The generated unparser now recognizes span children structurally via one shared helper instead
of the process-wide `span.py` probe — unblocking the §2.1 work without an intermediate
broken-unparse state in a native-present env.

- `fltk/unparse/pyrt.py:5,60-77`: added the dual-backend `is_span(obj)` helper —
  `isinstance(obj, Span)` (the module-top `terminalsrc.Span`) short-circuits, else lazy
  `sys.modules.get("fltk._native")` → `isinstance(obj, native.Span)`. Sits next to the existing
  dual-backend `extract_span_text` / `count_span_newlines`; added `import sys`; no top-level
  `fltk._native` import and no `span.py` import, so `pyrt` stays pure-Python importable and the
  probe never fires.
- `fltk/unparse/gsm2unparser.py:374-389`: added `_make_is_span_check(child_expr)`, building
  `fltk.unparse.pyrt.is_span(child)` the same way as the existing `fltk.unparse.pyrt.*` calls
  (`_gen_count_newlines_method` :936-945, the Regex `extract_span_text` site :1737-1746).
- `fltk/unparse/gsm2unparser.py` — retargeted the three probe-bound span guards to that helper:
  - `_extract_and_validate_nonsequence_child` (~:327-340): branch on `expected_type is
    self.span_type` — span case emits `not is_span(child)`; the `Identifier`/rule-node case keeps
    the concrete-class `iir.IsInstance` (unchanged).
  - `_count_newlines_in_trivia` (~:1018-1021): replaced `iir.IsInstance(child_value, Span)` with
    the helper call (the `if_` condition); the now-unused local `span_type` was removed.
  - `_gen_trivia_processing` (~:1121-1125): replaced the `is_span_check` `IsInstance` with the
    helper call (rhs of the `LogicalAnd` with `is_unlabeled`); `span_type` local kept — still used
    for the `whitespace_span` var annotation at :1131.
  - The other `IsInstance` sites (`:891` trivia-child types, `:1276` `Trivia`) are not span
    guards and are unchanged.
- `fltk/unparse/test_is_span_guard.py` (new): `is_span` unit coverage (True for `terminalsrc.Span`;
  True for `fltk._native.Span` when present; False for non-span; lazy native branch when native
  absent) + two generated-toy-unparser source checks (the helper call is emitted; no remaining
  `isinstance(...)` resolves through `fltk.fegen.pyrt.span.Span`).
- Verification (native-present env): `fltk/unparse/test_is_span_guard.py` +
  `fltk/test_plumbing.py::TestUnparsing` + `::TestIntegration` + `fltk/unparse/test_unparser.py`
  all pass (50 tests) — confirms the four §2.1-broken unparse tests are restored. ruff check +
  format + pyright clean on the three touched source files.
- Surprise/inherited state: the working tree still carries increment 2's uncommitted §2.1 changes
  (`fltk/fegen/gsm2parser.py`, `tests/test_python_parser_span_backend.py`); this commit
  deliberately stages only the §2.6(a) files and leaves §2.1 for its own later increment.

---

## Increment 4 — §2.1: Python parser always constructs `terminalsrc` types

Committed the §2.1 work that prior increments had left uncommitted in the working tree. The
generated Python parser now constructs pure-Python `terminalsrc` span/SourceText objects
unconditionally, decoupled from the type registry (registry entries stay at the `span` module per
§2.4, so the agnostic annotation surface is unchanged).

- `fltk/fegen/gsm2parser.py:105-137` (`_source_text` initializer): replaced
  `iir.Construct.make(self.SourceTextType, ...)` with a module-qualified call
  `iir.MethodAccess("SourceText", iir.VarByName(name="fltk.fegen.pyrt.terminalsrc", ...)).call(...)`,
  so the emitted class name no longer flows through the registry. Compiles to
  `fltk.fegen.pyrt.terminalsrc.SourceText(text=..., filename=...)`. Comment updated.
- `fltk/fegen/gsm2parser.py:273-291` (`_make_span_expr`): span class ref is now the fixed string
  `"fltk.fegen.pyrt.terminalsrc.Span"` instead of
  `lookup(self.TerminalSpanType).import_name()`; docstring updated to state construction is always
  `terminalsrc`.
- `tests/test_python_parser_span_backend.py` (new, 4 tests): root node span and span-typed child
  are `terminalsrc.Span`; `_source_text` is `terminalsrc.SourceText`; with native present the
  produced span is NOT `fltk._native.Span` (the core determinism regression).
- Verification (native-present env, `fltk._native` importable): the 4 new §2.1 tests pass, and the
  four §2.6(a)-restored unparse tests
  (`fltk/test_plumbing.py::TestUnparsing::{test_unparse_simple_expression,test_unparse_with_auto_rule}`,
  `::TestIntegration::{test_full_pipeline,test_pipeline_with_formatting}`) stay green — confirming
  §2.6(a) (already committed in increment 3) keeps the native-present unparse path working after
  §2.1 retargets construction. ruff check + format + pyright clean on both touched files.
- Context: this commit lands the increment-2 work that had been blocked pending the §2.6 design
  decision (now resolved and shipped as increment 3), so §2.1 no longer leaves an
  intermediate broken-unparse state.

---

## Increment 5 — §2.2: generated parsers stop importing `span.py` at runtime (lazy annotations)

The parser **generator** now emits lazy span annotations, so a generated Python parser no longer
needs a runtime `import fltk.fegen.pyrt.span` — it never touches the process-wide native-span
probe (and its warning) on import. (The span.py warning removal — the other half of §2.2 — was
already shipped in increment 1.)

- `fltk/fegen/genparser.py:97-126` (`generate_parser`): dropped
  `pyreg.Module(("fltk","fegen","pyrt","span"))` from the runtime `imports` list; after building
  `parser_mod`, inserted `from __future__ import annotations` at body[0]; appended an
  `if typing.TYPE_CHECKING:` block containing `import fltk.fegen.pyrt.span` (via
  `pygen.if_`/`pygen.expr`/`pygen.stmt`). The runtime `fltk.fegen.pyrt.terminalsrc` import stays
  (the §2.1 construction backend). Mirrors the established `gsm2tree.py:171-202` CST-generator
  pattern. `typing` is already in the parser's import list, so the TYPE_CHECKING guard needs no
  new top-level import.
- `fltk/fegen/test_genparser.py:174-235` (new `test_generated_parser_lazy_span_annotations`):
  runs the `generate` CLI on the simple grammar and AST-asserts on the emitted `*_parser.py`:
  (a) body[0] is `from __future__ import annotations`; (b) no module-top-level
  `import fltk.fegen.pyrt.span`; (c) `import fltk.fegen.pyrt.span` present under an
  `if typing.TYPE_CHECKING:` block; (d) runtime `import fltk.fegen.pyrt.terminalsrc` at top level.
- Verification: `fltk/fegen/test_genparser.py` all 25 pass (incl. the new test). ruff check +
  format + pyright clean on both touched files.
- Note: the committed parser files (`fltk/fegen/*_parser.py`, `fltk/unparse/*_parser.py`) now
  drift from the generator (they still carry the eager top-level `span` import); §2.5 regeneration
  reconciles them. Committed with `--no-verify` (intermediate increment); the §2.5 increment must
  pass the full `make check` drift gate.

---

## Increment 6 — §2.6(b): generated unparser annotations go lazy

The in-memory generated unparser's span-typed annotation is now a lazy string, so the unparser
no longer depends on some other module having imported `fltk.fegen.pyrt.span` as a side effect
(and never fires span.py's native-span probe when its annotation surface is constructed). No
committed artifact — every unparser is generated in-memory (§2.5).

- `fltk/unparse/gsm2unparser.py:1836-1879` (`generate_unparser` imports assembly): prepended
  `from __future__ import annotations` as `imports[0]` (ahead of the existing `import typing`),
  and appended an `if typing.TYPE_CHECKING:` block containing `import fltk.fegen.pyrt.span` after
  the `cst_import` append. Widened the `imports` local annotation from
  `list[ast.ImportFrom | ast.Import]` to `list[ast.stmt]` to admit the `ast.If` node. Both
  assembly sites (`plumbing.generate_unparser:420`, `genunparser.py:161` —
  `ast.Module(body=[*imports, unparser_ast])`) inherit both additions. The agnostic
  `fltk.fegen.pyrt.span.Span` annotation name (the `_count_newlines` `span:` param) is preserved
  (frozen surface, §2.4) but becomes a never-evaluated string.
- `fltk/unparse/test_is_span_guard.py:98-133` (new `TestLazySpanAnnotations`, 3 tests): reuses the
  existing `_generate_unparser_source` helper and AST-asserts on the emitted toy-unparser source:
  (a) `body[0]` is `from __future__ import annotations`; (b) no module-top-level
  `import fltk.fegen.pyrt.span`; (c) `import fltk.fegen.pyrt.span` present under
  `if typing.TYPE_CHECKING:`. Mirrors increment 5's parser-side `test_genparser.py` check.
- Verification (native-present env): `fltk/unparse/test_is_span_guard.py` (12 tests, incl. the new
  class) + `fltk/test_plumbing.py::TestUnparsing` + `::TestIntegration` +
  `fltk/unparse/test_unparser.py` all pass (53 total). ruff check + format + pyright clean on both
  touched files.
- Committed with `--no-verify` (intermediate increment); §2.5 regeneration is the increment that
  must pass the full `make check` drift gate. Plumbing removal (§2.3), regeneration (§2.5), and
  hybrid-test cleanup (§4.1) remain as separate later increments.

---

## Increment 7 — §2.3: remove the hybrid Python-parser/Rust-CST plumbing (commit PENDING)

Deleted the Python-parser/Rust-CST hybrid path from `fltk/plumbing.py` (the user's "rip that out"
directive). All changes in one file.

- `fltk/plumbing.py:90-104` (`generate_parser`): dropped the `rust_cst_module` keyword-only
  parameter and its `_load_rust_cst_classes` branch; `generate_parser` now always runs the Python
  CST `gen_py_module()` → `exec` path (`:114-118`). Removed the `RustBackendUnavailableError`
  mention from the docstring.
- `fltk/plumbing.py:125-131` (`generate_parser`): prepend `from __future__ import annotations`
  (built as `ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)`)
  ahead of the parser class in the exec'd `parser_module`, so the exec'd parser's `span.Span`
  annotations are never-evaluated lazy strings (§2.2/edge-case 4) now that §2.2/§2.5 stop the
  committed parsers from importing `span` at runtime as a side effect.
- `fltk/plumbing.py:36-64` (`parse_grammar` / `parse_grammar_file`): dropped the
  `rust_fegen_cst_module` keyword-only parameter and the entire Rust-backend branch; both functions
  now unconditionally use the committed Python `fltk_parser` + Python `fltk_cst` path.
- Deleted the now-dead support: `_load_rust_cst_classes`, `RustBackendUnavailableError`,
  `_fegen_rust_parser_cache`, `_fegen_grammar_cache`, `_load_fegen_grammar`, and the now-unused
  `import importlib` (`:11`). Verified no dangling references remain (grep clean).
- `parser_globals` still binds `Span`/`terminalsrc` as before (no native import added); updated the
  stale `# use \`public\` for both backends` comment (`:142`) to reflect the single Python backend.
- Verification (native-present env): smoke-tested the full pure-Python pipeline —
  `parse_grammar` → `generate_parser` → `parse_text` produces a `terminalsrc.Span` root span, and
  `generate_unparser` → `unparse_cst` → `render_doc` round-trips. ruff check + format + pyright
  clean on `fltk/plumbing.py`.
- Intermediate-commit consequence: `fltk/test_plumbing.py` and the other §4.1 hybrid tests import
  the deleted symbols (`RustBackendUnavailableError`, `_load_rust_cst_classes`) at module top and
  now fail at collection. Their removal/retargeting is §4.1, a separate later increment; committed
  with `--no-verify` per the incremental protocol (final increment §2.5 must pass `make check`).

---

## Increment 8 — §4.1 (part 1): remove hybrid-only tests, pure-deletion files

Removed the test code that existed solely to enforce the now-deleted (§2.3) Python-parser/Rust-CST
hybrid plumbing, in the two §4.1 files where the change is a pure deletion.

- `fltk/test_plumbing.py`: deleted `TestRustBackendUnavailableError`, `TestLoadRustCstClasses`,
  `TestGenerateParserRustBackend`, `TestParseGrammarRustBackend`, and `TestNoRuntimeCompilation`
  (the `:589` `_load_rust_cst_classes` source-inspection test). Dropped the now-unused imports they
  were the sole users of: `RustBackendUnavailableError`, `_load_rust_cst_classes`,
  `parse_grammar_file` (from the `fltk.plumbing` import block), and `importlib`, `inspect`, `types`,
  `unittest.mock`, `import fltk.plumbing as fltk_plumbing_mod`. The module was failing at collection
  on the deleted-symbol imports; it now collects and its 25 kept tests pass.
- `tests/test_phase4_fegen_rust_backend.py`: deleted `TestAC8RealCst2GsmRustBackend` (the
  `parse_grammar(..., rust_fegen_cst_module=...)` caller) and its AC8 section comment; dropped the
  now-unused imports `import fltk.fegen.fltk2gsm as fltk2gsm_mod` and `parse_grammar_file`; refreshed
  the module docstring to drop the AC8 coverage description. Kept `TestChildSpanAccessorContract`,
  `TestAC6FegenRustCstModule`, `TestAC9LabelBackendIndependence`, `TestRustParserSelfHosting`.
- Deletion of the contiguous class ranges was done with `sed` line-range deletes (safer than
  inlining ~165 lines of exact text); the import/docstring surgery was done with `Edit`.
- Minor scope note: §4.1 names only the test classes; removing the imports those classes were the
  sole users of (incl. `parse_grammar_file` in `test_plumbing.py`, not explicitly listed) and
  refreshing the stale AC8 docstring were required for a ruff-clean, non-stale result.
- Verification (native-present env, `fegen_rust_cst` built):
  `uv run pytest fltk/test_plumbing.py tests/test_phase4_fegen_rust_backend.py` → 57 passed, 0
  skipped. ruff check + format + pyright clean on both files.
- Intermediate-commit consequence: `tests/test_phase4_rust_fixture.py` and
  `tests/test_clean_protocol_consumer_api.py` still reference the deleted hybrid plumbing (their
  §4.1 treatment — delete+retarget — is a separate later increment), so the full suite is not yet
  green; committed with `--no-verify` per the incremental protocol.

---

## Increment 9 — §4.1 (part 2a): hybrid-removal in `tests/test_phase4_rust_fixture.py`

Removed this test file's dependency on the deleted (§2.3) Python-parser/Rust-CST hybrid generator.
The standalone `phase4_roundtrip_cst` extension ships **no parser** (verified: it exposes only a
`.cst` submodule, no `.parser`), so the Rust CST contracts are now exercised by constructing
`phase4_roundtrip_cst.cst` nodes directly instead of parsing through the hybrid.

- `tests/test_phase4_rust_fixture.py:30-33`: replaced the module-level
  `_rust_pr = generate_parser(_grammar_for_rust, rust_cst_module="phase4_roundtrip_cst.cst")` and
  the two-grammar setup with `_rust_cst = pytest.importorskip("phase4_roundtrip_cst.cst", ...)` —
  the genuine config-2 Rust CST module (the same object the hybrid's `_rust_pr.cst_module` was).
  Importing the submodule via `importorskip` keeps the skip-when-unbuilt behavior and gives pyright
  an `Any`-typed binding (the runtime-built extension has no stubs).
- `:54-55`: kept a single pure-Python parser `_python_pr = generate_parser(_grammar)` for the AC7
  python comparison and the parse roundtrip; dropped the now-unused `_grammar_for_rust` /
  `_grammar_for_python` duplication and the `sys` import.
- Retargeted every Rust-CST-contract test from `_rust_pr.cst_module.X` to `_rust_cst.X`
  (construction / span read-write, the 12 AC5 API-Contract items, Phase-1 identity/mutation,
  `extract_span` error paths, the cross-cdylib sourceless-span accessor). These never parsed —
  they only construct nodes — so they carry over unchanged in substance.
- `TestPhase1IdentityAndMutation::test_node_eq_distinct_allocation_deep_tree`: the original parsed
  the same input twice to get two distinct-allocation trees; rewrote it to build two
  structurally-equal trees by direct construction, preserving the pymethod → `Shared<T>::eq`
  delegation coverage (the non-ptr-eq path `test_node_eq_self_no_deadlock` doesn't reach).
- Deleted the hybrid-parser-driven tests (no Rust parser exists for this fixture grammar):
  `TestAC3Roundtrip` (whole class), `TestAC2ModuleRegistered::test_cst_module_in_sys_modules`
  (hybrid cst_module registration), and the `parse_text(_rust_pr, ...)` span tests in
  `TestAC7BothBackends` (`test_rust_backend_node_span_is_native_and_text_works`,
  `test_cross_cdylib_span_merge_after_accessor`, `test_cross_cdylib_child_span_merge`,
  `test_rust_backend_node_span_text_non_ascii`). The §4.1 retainable categories (construction,
  labels, list protocol, identity/mutation, extract_span error paths) don't include live-parse or
  cross-cdylib-merge — those exercised the deleted hybrid path itself.
- `TestAC7BothBackends`: re-parametrized the construct-only tests over CST **module objects**
  (`_python_pr.cst_module` / `_rust_cst`) instead of `ParserResult` objects; `test_full_parse_roundtrip`
  is now pure-Python-only (un-parametrized) since the fixture has no Rust parser. Renamed
  `TestAC2ModuleRegistered` → `TestAC2ModuleExposesClasses` (it now checks the extension exposes
  classes, not hybrid registration) and refreshed the module docstring.
- Verification (native-present env, `phase4_roundtrip_cst` built): all 49 tests pass; ruff check +
  format + pyright clean on the file.
- Committed with `--no-verify` (intermediate). The `tests/test_clean_protocol_consumer_api.py`
  retarget (§4.1) and the §2.5 regeneration (final, must pass `make check`) remain.

---

## Increment 10 — §4.1 (part 2b): retarget/remove hybrid call sites in `tests/test_clean_protocol_consumer_api.py`

Removed this file's dependency on the deleted (§2.3) Python-parser/Rust-CST hybrid generator — the
last §4.1 file. With this done, all hybrid-test cleanup is complete; only §2.5 regeneration remains.

- `tests/test_clean_protocol_consumer_api.py:160-170` (`_rust_cst_grammar`): RETARGETED to drive the
  genuine config-2 Rust parser directly — `fegen_rust_cst.parser.Parser(grammar_text,
  capture_trivia=False)` → `apply__parse_grammar(0)` → `result.result` (a
  `fegen_rust_cst.cst.Grammar`), the same API the kept `TestRustParserSelfHosting` uses
  (`tests/test_phase4_fegen_rust_backend.py:194-205`). Dropped the
  `parse_grammar_file(FEGEN_FLTKG_PATH)` / `generate_parser(rust_cst_module=...)` / `terminalsrc`
  hybrid plumbing; docstring updated. Every `TestCrossBackendDualShapeDispatch` dispatch assertion
  is unchanged.
- `:676` `test_span_kind_narrows_rust_backend_span_children`: docstring updated — with the genuine
  Rust parser, separator-child spans are now `fltk._native.Span` (not the hybrid's
  `terminalsrc.Span`); the test still holds because `.kind` is the shared `SpanKind.SPAN` for both
  backends (assertion body unchanged). Also refreshed the `rust_items` fixture docstring
  (`:579-581`) to name the genuine `fegen_rust_cst.parser` source.
- Removed `test_fltk2gsm_behavioral_equivalence` (the `parse_grammar_file(rust_fegen_cst_module=...)`
  site) and its `§4 item 3` section header; its property is preserved by the kept
  `TestRustParserSelfHosting` (drives `fegen_rust_cst.parser.Parser` over `fegen.fltkg`, asserts
  `gsm_rust == gsm_python`).
- Dropped the now-unused `from fltk.plumbing import generate_parser, parse_grammar_file` import and
  the `FEGEN_FLTKG_PATH` constant (both orphaned by the two changes; grep-confirmed no other users).
- Verification (native-present env, `fegen_rust_cst` built): all 53 tests pass; ruff check + format
  clean. Pyright on the file reports the pre-existing `fegen_rust_cst = None` Optional-access
  pattern (one new pair at `:165` for `fegen_rust_cst.parser`, same root cause as the 38 existing
  `fegen_rust_cst.cst` accesses); `tests/` is outside `make check`'s pyright scope
  (`include = ["fltk", "*.py"]`), so this does not gate.
- Committed with `--no-verify` (intermediate): committed parsers still drift from the generator
  (per increments 5/6), so the `make gencode` drift gate stays red until §2.5 regeneration (the
  final increment).

---

## Increment 11 — §2.5: regenerate committed parser artifacts — BLOCKED (clarification needed)

The §2.5 regeneration was performed (`make gencode` → `make fix`) and produced the exact 10
parser-file changes the design predicts (`from __future__ import annotations`, `span` import under
`TYPE_CHECKING`, construction sites `fltk.fegen.pyrt.span.*` → `fltk.fegen.pyrt.terminalsrc.*`).
**But the regenerated parsers fail `make check` at the `typecheck` (pyright) step**, exposing a
design gap §2.5/edge-case-6 did not anticipate. Nothing was committed; the regenerated parser files
were reverted to keep HEAD (`166737e`) clean. `make gencode` reproduces the failure deterministically.

### The failure (20 errors, 2 per file × 10 files)

Every regenerated parser's `consume_literal` and `consume_regex` helpers fail, e.g.
`fltk/fegen/fltk_parser.py:88` / `:99`:

```
error: Type "ApplyResult[int, Span]" is not assignable to return type "ApplyResult[int, Span] | None"
  Type parameter "ResultType@ApplyResult" is invariant,
    but "fltk.fegen.pyrt.terminalsrc.Span" is not the same as "fltk._native.Span"
```

These two helpers both **construct** the span and are **annotated** with the registry type:
- §2.1 makes the construction `fltk.fegen.pyrt.terminalsrc.Span.with_source(...)` →
  the returned value is `ApplyResult[int, terminalsrc.Span]`.
- §2.4 keeps the return annotation `ApplyResult[int, fltk.fegen.pyrt.span.Span] | None`. In a
  native-present env pyright resolves `fltk.fegen.pyrt.span.Span` (the `span.py` try/except
  selector, `span.py:8-14`) to **`fltk._native.Span`** — NOT the union the design assumed
  (design §1.4 claims pyright sees "the union of both backends"; for this annotation it does not).
- `fltk.fegen.pyrt.memo.ApplyResult`'s `ResultType` is **invariant**, so
  `ApplyResult[int, terminalsrc.Span]` ≠ `ApplyResult[int, fltk._native.Span]` → hard pyright error.

Confirmed pre-regen pyright is clean on the committed parsers (old `span.Span` construction matched
the `span.Span` annotation), so this is introduced solely by the §2.5 regen of the §2.1 change.

### Why this is a design gap, not an implementable detail

The design's central mechanism (§2: "separate the two jobs" — terminalsrc construction, agnostic
`span.Span` annotation) works for the CST node `span` **field** (an explicit `terminalsrc.Span |
fltk._native.Span` **union**, a covariant assignment target, generated by `gsm2tree.py` — unaffected)
but is **type-incompatible** for the parser's own `ApplyResult[int, Span]` **returns**, because
`ApplyResult` is invariant. The return type derives from `self.TerminalSpanType`
(`gsm2parser.py:153` → `ApplyResultType.instantiate(result_type=self.TerminalSpanType)`), the `Span`
registry type that §2.4 explicitly freezes at the `span` module. No fix preserves both §2.1
(terminalsrc construction) and §2.4 (frozen `span.Span` annotation):

- **(a) Make the parser's span annotations honest (`terminalsrc.Span`).** Point the parser's
  terminal-span annotation at `terminalsrc` (e.g. a parser-local `TerminalSpanType` rendering, or
  a targeted override for the `consume_*` returns). Honest for a pure-Python parser and matches the
  requirements ("pure-Python parser ⇒ pure-Python span"). **Contradicts design §2.4** ("every
  annotation derived from the registry is unchanged") and changes the parser's type-annotation
  surface, which CLAUDE.md flags as public-API-adjacent ("parsers ... and their type-annotation ...
  surfaces are public API"). Affects all parser-internal span annotations (consume_* returns,
  `span_var` locals at `gsm2parser.py:173,221`, Literal/Regex item return types at `:665-667`), not
  just the 2 reported sites — all consistently parser-internal, none CST/protocol/`.pyi`.
- **(b) Make `ApplyResult.ResultType` covariant** (`fltk/fegen/pyrt/memo.py`). Eliminates the
  invariance conflict globally so terminalsrc-constructed results satisfy a `span.Span`-typed
  (native) annotation. Out of scope (core runtime type), and a variance change to a shared generic
  has its own correctness surface.
- **(c) Cast** inside `consume_literal`/`consume_regex`. The design explicitly rejects casts
  (§5, and the clean-protocol-consumer philosophy).

This is a hole in the design's central thesis (it implicitly assumed the parser's span annotation
sites were covariant like the CST field, or that pyright would union the selector), forced by the
type system. Resolving it requires a design decision weighing §2.4's frozen-annotation directive
against pyright cleanliness — not an implementer improvisation on the surface the design froze and
CLAUDE.md guards.

### Recommendation

Option **(a)**, scoped to the parser's terminal-span annotation only: make a pure-Python parser's
span annotations honestly `terminalsrc.Span` (the parser is, by §2.1, unconditionally pure-Python,
so its terminal-consume helpers always return `terminalsrc.Span`). This is parser-**internal** (the
`fltk.fegen.pyrt.memo.ApplyResult[int, Span]` return of `consume_literal`/`consume_regex`, plus the
parser-local span annotations) — it renames no CST/protocol/`.pyi` symbol, leaves the CST node
`span` field union and all span-typed child annotations untouched, and forces no CST-consumer
churn. It is the minimal change that makes the parser self-consistent (terminalsrc construction +
terminalsrc annotation). It requires an explicit amendment to design §2.4/§2-item-2, which is why
it is escalated rather than applied. Awaiting that decision; not improvising a change to the frozen
annotation surface.

### State

- No code changed since `166737e` (increment 10): the §2.5 regen was reverted; this entry is the
  only change (log-only commit). All committed source is exactly the increment-10 tree.
- All design work **except §2.5 regeneration** is complete and committed (increments 1–10).
- `make check` is NOT yet clean: it cannot be until the committed parsers are regenerated, and the
  regen cannot land until the annotation-surface decision above is made.

---

## Increment 12 — DELTA D3.1: root-fix `SpanProtocol` to be the usable agnostic span type

First delta increment. The delta supersedes the original §2.1.1 cast with a variance-forced split
(D3): the CST/protocol/`.pyi`/unparser agnostic span slot becomes `SpanProtocol`. That only works
if a concrete span *value* is statically assignable to `SpanProtocol`, which it was **not** (the
shipped `SpanProtocol` declared `merge`/`intersect` with `other: SpanProtocol`, a wider param than
the concrete `Span` — contravariantly incompatible, so `terminalsrc.Span` was not a structural
subtype). This increment root-fixes the protocol so `terminalsrc.Span` is statically assignable,
unblocking every later delta increment. No registry/codegen change yet (D3.2+).

- `fltk/fegen/pyrt/span_protocol.py:1-13`: imports — added `TYPE_CHECKING`, `Literal` to the
  `typing` import; added `SpanKind` to the `terminalsrc` import; added a `TYPE_CHECKING`-only
  `from typing_extensions import Self`. `Self` is used solely in string annotations, and
  `runtime_checkable` checks member *presence* not signatures, so no runtime `typing_extensions`
  dependency is introduced (the project does not declare it as a runtime dep; 3.10 target → not
  `typing.Self`). Body still imports only `terminalsrc` (no `fltk._native`).
- `fltk/fegen/pyrt/span_protocol.py` (`kind` property, after `end`): added a read-only
  `kind` property `-> Literal[SpanKind.SPAN]` (D3.1 discriminant for Shape-2 `case
  proto_cst.Span.kind:` dispatch). Both backends already expose `kind`, so isinstance conformance
  is unbroken.
- `fltk/fegen/pyrt/span_protocol.py` (`merge`/`intersect`): retyped `other` and the return from
  `"SpanProtocol"` to `"Self"`. This is what makes a concrete span statically assignable to
  `SpanProtocol`, and is semantically more honest (each backend's `merge` accepts only its own span
  type at runtime).
- `fltk/fegen/pyrt/span_protocol.py` (above `line_col`): added `TODO(spanprotocol-native-linecol)`
  marking the residual static gap (native `Span.line_col` returns the native `LineColPos`, so
  `fltk._native.Span` is not *statically* a `SpanProtocol` — conforms only by runtime isinstance +
  `.pyi`). Per delta D5.2/D8 this is a contained, non-blocking gap. Paired `TODO.md` entry added.
- `fltk/fegen/pyrt/test_span_protocol_assignability.py` (new): module-level pyright-checked
  assignability assertions (lives under `fltk/`, so in `make check` pyright scope) — a
  `SpanProtocol` variable `= PySpan(0,1)`, a `SpanProtocol` dataclass field default `= UnknownSpan`,
  and a `-> SpanProtocol: return PySpan.with_source(...)`; plus runtime tests: both pyright slots
  construct, `isinstance(terminalsrc.Span, SpanProtocol)` True, (native present)
  `isinstance(fltk._native.Span, SpanProtocol)` True, and the new `kind` discriminant present /
  equal across backends. Native is deliberately NOT assigned into a static `SpanProtocol` slot
  (D5.2 gap).
- Verification (native-present env): `uv run pyright` clean on the 2 touched source files +
  `error_formatter.py` (the only `fltk/` `SpanProtocol` consumer) + `span.py`; ruff check + format
  clean; `test_span_protocol_assignability.py` (5) + `tests/test_span_protocol.py` (45) = 50 pass.
- Committed with `--no-verify` (intermediate increment; the final delta increment — regen — must
  pass the full `make check`). Registry repoint (D3.2), parser/CST/protocol/`.pyi`/unparser
  annotation moves (D3.3–D3.6), and the D6 regen + retargeted union-surface tests remain.

---

## Increment 13 — DELTA D3.3: parser keeps a concrete `terminalsrc.Span` annotation; cast eliminated; dead `span` import dropped

The generated Python parser now annotates its terminal spans with the concrete pure-Python
`terminalsrc.Span` ("Concept A"), matching its committed §2.1 `terminalsrc.Span.with_source(...)`
construction. This makes the invariant `ApplyResult[int, Span]` terminal-consume returns
exact-match (no `typing.cast`), resolving the increment-11 pyright blocker *for the parser's own
returns* (the parser→CST-setter boundary still needs D3.4's `SpanProtocol` move before a D6 regen
can pass). Scope was revised from the turn-2 draft (D3.2 SourceText half) after exploration showed
the SourceText repoint produces **no** observable emitted-parser diff — the `_source_text` field
carries no annotation (it is set via the constructor init-list as a plain assignment) and its
construction is a fixed module-qualified `terminalsrc.SourceText(...)` call (committed §2.1), so the
SourceText registry entry drives no emitted annotation. D3.3 is the observable, testable parser
half; the SourceText repoint is folded into a later increment with the rest of D3.2.

- `fltk/fegen/gsm2parser.py` (`ParserGenerator.__init__`, after the `get_parser_types()` unpack):
  introduced a parser-local concrete span type `iir.Type.make(cname="TerminalSpanConcrete")`,
  registered to `("fltk","fegen","pyrt","terminalsrc") / "Span"`, and reassigned
  `self.TerminalSpanType` to it. A distinct cname yields a distinct registry key, so it never
  collides with the shared `Span` entry (still `→ span` selector; that drives the cross-backend
  CST/protocol surface until D3.4/D3.5). Every parser span annotation flows from
  `self.TerminalSpanType` (the `consume_literal`/`consume_regex` `ApplyResult` result type, the
  `span_var` locals, the Literal/Regex item return types, and the `_make_span_expr` var `typ`), so
  the single reassignment flips all of them to `terminalsrc.Span` with no per-site edits.
- `fltk/fegen/gsm2parser.py` (`_make_span_expr` docstring): updated the stale "registry's `Span`
  entry stays pointed at the `span` module (§2.4)" note to state the parser-local concrete span
  type (D3.3).
- `fltk/fegen/genparser.py` (`generate_parser`): removed the now-dead `if typing.TYPE_CHECKING:
  import fltk.fegen.pyrt.span` block (added in increment 5) — the parser no longer names the `span`
  selector anywhere. `from __future__ import annotations` stays (harmless, avoids churn). Comment
  rewritten to reflect D3.3.
- `fltk/fegen/test_genparser.py`: reworked increment 5's `test_generated_parser_lazy_span_annotations`
  into `test_generated_parser_concrete_terminalsrc_span_annotations` — inverted the
  "span imported under TYPE_CHECKING" assertion to "span imported nowhere (and no `fltk._native`
  reference)", and added: `consume_literal`/`consume_regex` return
  `ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]` (not the `span` selector) and the source
  contains no `typing.cast(`.
- Verification (native-present env): regenerated a sample parser via the `generate` CLI — all span
  annotations are `fltk.fegen.pyrt.terminalsrc.Span`, no `span`/`fltk._native` reference, no
  TYPE_CHECKING block, no cast. ruff check + format + pyright clean on the 3 touched source files.
  Tests: `fltk/fegen/` + `fltk/unparse/` + `tests/test_python_parser_span_backend.py` = 476 passed
  (incl. the reworked test and the §2.1 determinism regressions; in-memory exec'd parsers still
  generate and run).
- Committed with `--no-verify` (intermediate increment; the final delta increment — D6 regen — must
  pass the full `make check`). Remaining delta work: D3.2 registry repoint (Span→SpanProtocol +
  SourceText→terminalsrc), D3.4 (CST/protocol span field+children → `SpanProtocol`), D3.5 (Rust
  `.pyi` → `SpanProtocol`), D3.6 (unparser annotation → `SpanProtocol`), and the D6 regen +
  retargeted union-surface tests.

---

## Increment 14 — DELTA D3.2: repoint the type registry

Repointed the shared type registry so the cross-backend span surface flows to the agnostic
`SpanProtocol` and `SourceText` flows to the honest concrete `terminalsrc` — one semantic change to
the registry, no codegen-structure change. After this the registry no longer names the `span`
selector for either entry.

- `fltk/iir/context.py:113-123` (`_register_builtin_types`, shared `Span` entry): repointed from
  `("fltk","fegen","pyrt","span") / "Span"` to `("fltk","fegen","pyrt","span_protocol") /
  "SpanProtocol"`. This is the single lever that flips every *registry-driven* span annotation —
  concrete CST span-typed children, protocol span-typed children, and the unparser's
  `_count_newlines` span param — to `SpanProtocol` automatically. Comment rewritten to describe the
  backend-neutral `SpanProtocol` role (replaces the stale backend-selector note).
- `fltk/iir/context.py:125-132` (`SourceText` entry): repointed from `span` to
  `("fltk","fegen","pyrt","terminalsrc") / "SourceText"` (honest; matches the committed §2.1
  `terminalsrc.SourceText(...)` construction). Comment updated.
- `fltk/fegen/gsm2parser.py:94-102` (`ParserGenerator.__init__`, the second `SourceText`
  re-registration for the same key): repointed from `span` to `terminalsrc` so it is **idempotent**
  with the context entry rather than a conflicting one. Leaving it at `span` while context moved to
  `terminalsrc` would raise `ValueError("Conflicting type registration")` (context.py:19-25) on
  every `ParserGenerator.__init__` and break all Python-parser generation — the hard crash D3.2
  warns about. Repointed (not deleted) to keep the field-type registration self-contained and avoid
  assuming the caller's context always pre-registers `SourceText`. Comment expanded to record the
  conflict-crash rationale.
- The parser's own terminal-span annotation is **unaffected**: it uses the increment-13 parser-local
  `TerminalSpanConcrete` (cname distinct from the shared `Span`), so `consume_literal`/`consume_regex`
  still return `ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]` and `get_parser_types()`'s shared
  `Span` is no longer used for any parser annotation.
- Verified by generating (native-present env): a representative CST's span-typed children
  (`children` element, `append`/`extend`/`child`/`append_<label>`/`children_<label>`/`child_<label>`/
  `maybe_<label>`/`insert`/`remove_at`/`replace_at`/`_check_child_type_for_mutators`) now render
  `fltk.fegen.pyrt.span_protocol.SpanProtocol`; the parser's `_source_text` annotates and constructs
  `terminalsrc.SourceText`; parser generation succeeds (no conflict crash) and a parsed root span is
  still a pure-Python `terminalsrc.Span`. The runtime mutator validation
  (`_allowed = (terminalsrc.Span,)` + `_get_native_span_type()`) is unchanged.
- Intentionally-still-intermediate state (NOT green; expected, committed `--no-verify`): the CST/
  protocol `span` **field** is still the hardcoded `terminalsrc.Span | fltk._native.Span` union and
  generated CST/protocol/unparser still import `span`/`fltk._native` (not yet `span_protocol`) — those
  are D3.4/D3.5/D3.6. So generated modules reference `span_protocol.SpanProtocol` without importing it
  (lazy `from __future__` strings → runtime-importable; pyright-dirty until the import moves land).
  Pre-existing union-surface tests (`tests/test_gsm2tree_rs.py`, `fltk/fegen/test_cst_protocol.py`
  §4-item-8) still pin the old surface and will fail until the D6 retarget.
- Tests: `tests/test_python_parser_span_backend.py` (4) + `fltk/fegen/pyrt/test_span_protocol_assignability.py`
  (4) pass — runtime span backend + `SpanProtocol` assignability preserved. ruff check + format +
  pyright clean on the 2 touched source files.
- Committed `--no-verify` (intermediate increment; the final delta increment — D6 regen — must pass
  the full `make check`). Remaining delta work: D3.4 (CST/protocol span field+children →
  `SpanProtocol` + imports), D3.5 (Rust `.pyi` → `SpanProtocol` + imports), D3.6 (unparser annotation
  import → `span_protocol`), and the D6 regen + retargeted union-surface tests.

---

## Increment 15 — DELTA D3.4: concrete CST + protocol span field/children → `SpanProtocol`

The generated concrete-CST and protocol modules now name the agnostic
`fltk.fegen.pyrt.span_protocol.SpanProtocol` for the `span` field and all span-typed children, and
import only `span_protocol` (under `TYPE_CHECKING`) — neither the `span` selector nor `fltk._native`
appears in the static annotation surface of either module. One semantic change, one generator file.

- `fltk/fegen/gsm2tree.py` (`gen_py_module`, concrete CST `span` field): replaced
  `span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = ...UnknownSpan` with
  `span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan`. The
  default stays the concrete `terminalsrc.UnknownSpan` (assignable to `SpanProtocol` after D3.1).
- `fltk/fegen/gsm2tree.py` (`gen_py_module`, concrete `TYPE_CHECKING` imports + the two preamble
  comments): dropped `import fltk.fegen.pyrt.span` and `import fltk._native`; added
  `import fltk.fegen.pyrt.span_protocol`. Comments rewritten to describe the agnostic protocol.
- `fltk/fegen/gsm2tree.py` (`_protocol_class_for_model`, protocol `span` field `:900`): replaced the
  same hardcoded union with `span: fltk.fegen.pyrt.span_protocol.SpanProtocol`.
- `fltk/fegen/gsm2tree.py` (`gen_protocol_module`, protocol `TYPE_CHECKING` imports + comment):
  dropped `import fltk.fegen.pyrt.span` / `import fltk._native`; added
  `import fltk.fegen.pyrt.span_protocol`.
- Span-typed **children** were NOT edited per-site — they flow from the registry `Span` entry
  (repointed to `span_protocol.SpanProtocol` in increment 14 / D3.2), so the `children` element,
  `append`/`extend`/`child`/`insert`/`remove_at`/`replace_at`/`_check_child_type_for_mutators`
  signatures and the `append_*`/`extend_*`/`children_*`/`child_*`/`maybe_*` quintet render
  `SpanProtocol` automatically (verified).
- Unchanged per D3.4: `_protocol_span_class` (still emits `kind:
  Literal[terminalsrc.SpanKind.SPAN]`, the `case proto_cst.Span.kind:` marker), and the runtime
  mutator validation (`_check_child_type_for_mutators`, `_get_native_span_type()`,
  `_MUTATOR_ALLOWED_CHILD_TYPES`) — the latter still references the *string* `"fltk._native"` via
  `sys.modules.get(...)` for lazy runtime isinstance, which D3.4 keeps as-is (runtime mechanism,
  independent of the static annotation). So the generated CST module still contains that one runtime
  string; the D6 "no native reference" source test must scope to imports/annotations, not string
  literals.
- Verification (native-present env): generated a sample CST + protocol from the bootstrap grammar —
  concrete `span` field, protocol `span` field, and every span-typed child render
  `fltk.fegen.pyrt.span_protocol.SpanProtocol`; both modules import `span_protocol` under
  `TYPE_CHECKING`; neither imports the `span` selector; the protocol module names `fltk._native`
  nowhere; the concrete module names it only in the runtime `_get_native_span_type()` helper. Tests:
  `test_gsm2tree.py` + `test_gsm2parser.py` + `tests/test_python_parser_span_backend.py` +
  `pyrt/test_span_protocol_assignability.py` = 11 pass. ruff check + format + pyright clean on
  `gsm2tree.py`.
- Intermediate state (NOT green, committed `--no-verify`): the committed `*_cst.py` / `*_cst_protocol.py`
  artifacts now drift from the generator (still the old union surface) until D6 regen; the
  union-surface tests `tests/test_gsm2tree_rs.py` (`test_imports_span_module`,
  `test_imports_fltk_native`, `test_span_annotation_exact_protocol_union`) and
  `fltk/fegen/test_cst_protocol.py:487-614` (§4-item-8 additive-widening suite) still pin the OLD
  surface and fail — their retarget/rework is D6. Remaining delta work: D3.5 (Rust `.pyi` →
  `SpanProtocol`), D3.6 (unparser annotation import → `span_protocol`), and the D6 regen +
  retargeted union-surface tests.

---

## Increment 16 — DELTA D3.5: Rust `.pyi` span field/children → `SpanProtocol`

The generated Rust `.pyi` stub now annotates the `span` field and all span-typed children with the
agnostic `fltk.fegen.pyrt.span_protocol.SpanProtocol` and imports only `span_protocol` — it names
neither `fltk._native`, the `fltk.fegen.pyrt.span` selector, nor the concrete `terminalsrc.Span`.
Rust node *classes* stay Rust types (no class renames); only the span annotation surface moves to
the agnostic contract, which is what keeps a Rust CST swap-compatible with the Python CST.

- `fltk/fegen/gsm2tree_rs.py` (`generate_pyi`, span field): replaced the hardcoded
  `span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span` with
  `span: fltk.fegen.pyrt.span_protocol.SpanProtocol`; comment updated.
- `fltk/fegen/gsm2tree_rs.py` (`generate_pyi`, imports): dropped `import fltk.fegen.pyrt.terminalsrc`,
  `import fltk.fegen.pyrt.span`, and `import fltk._native`; added `import fltk.fegen.pyrt.span_protocol`.
  Span-typed **children** were not edited per-site — they already render `SpanProtocol` from the
  registry `Span` entry (repointed in increment 14 / D3.2), so the span-field edit is the only
  `.pyi`-body change; the import set follows from it.
- Deviation from D3.5 text: the design named only `fltk._native` and the `span` selector for removal,
  expecting `terminalsrc` to stay. Empirically `terminalsrc` is referenced **only** in the old span
  field (the children already moved to `span_protocol` via the increment-14 registry repoint), so it
  becomes unused; ruff F401 flags unused imports in `.pyi` files (verified), and the D6 regen of the
  committed `fltk/_stubs/fegen_rust_cst/cst.pyi` would fail `make check` if the generator emitted it.
  So `terminalsrc` is dropped too. (`fltk.fegen.pyrt.span` was in fact already unused at HEAD — only
  its import line remained.)
- `tests/test_gsm2tree_rs.py` (`TestGeneratePyiHeader`): retargeted the three union-surface header
  tests — `test_imports_terminalsrc` → `test_no_import_terminalsrc` (assert no `terminalsrc`),
  `test_imports_span_module` → `test_no_import_span_selector` (assert no exact `import fltk.fegen.pyrt.span`
  line; line-exact to avoid the `span_protocol` prefix overlap), `test_imports_fltk_native` →
  `test_no_import_fltk_native` (assert no `fltk._native`); added `test_imports_span_protocol`.
- `tests/test_gsm2tree_rs.py` (`TestGeneratePyiClasses`): `test_span_annotation_exact_protocol_union`
  → `test_span_annotation_span_protocol` (assert `span: …span_protocol.SpanProtocol`). These five are
  the direct unit tests of `generate_pyi`'s span/import output (impl + its tests).
- Surprise (pre-existing, now fixed): the two pyright self-check tests
  (`TestGeneratePyiSelfCheck::{test_fegen_pyi_self_check_zero_errors,test_poc_pyi_self_check_zero_errors}`)
  were **already failing at HEAD** — increment 14's registry repoint made the `.pyi` children
  reference `fltk.fegen.pyrt.span_protocol` without the stub importing it (`reportAttributeAccessIssue`).
  D3.5 adds that import, so both self-checks now pass.
- Intermediate state (NOT green, committed `--no-verify`): the two conformance tests
  (`TestGeneratePyiConformance::{test_fegen_whole_module_no_cast_zero_errors,test_fegen_per_class_no_cast_zero_errors}`)
  now fail — the fresh `.pyi` has `span: SpanProtocol` while the committed protocol
  `fltk.fegen.fltk_cst_protocol` still carries the old union (`SpanProtocol` not assignable to
  `terminalsrc.Span | fltk._native.Span`). Their green requires the committed-protocol regen, which is
  D6. Also the committed `fltk/_stubs/fegen_rust_cst/cst.pyi` now drifts from the generator until the
  D6 regen.
- Verification (native-present env): generated POC `.pyi` imports only `typing` + `span_protocol` +
  `_proto`, span field is `SpanProtocol`, zero residual `terminalsrc`/`fltk._native`/`span`-selector
  refs. `uv run pytest tests/test_gsm2tree_rs.py` = 226 passed, 2 failed (the D6-coupled conformance
  pair above). ruff check + format + pyright clean on `gsm2tree_rs.py`; ruff clean on the test file.
- Committed `--no-verify` (intermediate increment; the final delta increment — D6 regen — must pass
  the full `make check`). Remaining delta work: D3.6 (unparser annotation import → `span_protocol`),
  and the D6 regen + retargeted union-surface tests (incl. `fltk/fegen/test_cst_protocol.py` §4-item-8
  rework and the two conformance tests above going green once the committed protocol is regenerated).

---

## Increment 17 — DELTA D3.6: unparser annotation import → `span_protocol`

The in-memory generated unparser's `TYPE_CHECKING`-only span import now names the agnostic
`span_protocol` contract module instead of the `span` selector, matching the `_count_newlines`
span annotation (already `SpanProtocol` via the increment-14 registry repoint). After this the
generated unparser names neither `fltk._native` nor the `fltk.fegen.pyrt.span` selector — runtime
or `TYPE_CHECKING`. No committed artifact (every unparser is generated in-memory, §2.5).

- `fltk/unparse/gsm2unparser.py` (`generate_unparser` imports assembly, the increment-6
  `TYPE_CHECKING` block): changed the guarded import from `fltk.fegen.pyrt.span` to
  `fltk.fegen.pyrt.span_protocol`. Updated the two surrounding comments (the `imports[0]`
  `from __future__` rationale and the `TYPE_CHECKING`-block note) to describe the agnostic
  `SpanProtocol` annotation surface (names neither native nor the selector). The
  `_count_newlines(self, span: …)` annotation itself is registry-driven (repointed to
  `SpanProtocol` in increment 14 / D3.2), so no annotation-site edit was needed — it was already
  rendering `fltk.fegen.pyrt.span_protocol.SpanProtocol` against an import that did not exist; this
  increment supplies that import.
- `fltk/unparse/test_is_span_guard.py` (`TestLazySpanAnnotations`): retargeted the increment-6
  assertions — `test_no_module_top_level_span_import` → `..._span_protocol_import`,
  `test_span_import_under_type_checking` → `test_span_protocol_import_under_type_checking` (asserts
  `fltk.fegen.pyrt.span_protocol` guarded under `if typing.TYPE_CHECKING:`); added
  `test_no_span_selector_import_anywhere` (line-exact `import fltk.fegen.pyrt.span` appears nowhere,
  guarding against the `span_protocol` prefix overlap). Class docstring updated.
- The §2.6(a) runtime `is_span` guard (increment 3) is unaffected — the change touches only the
  static annotation import surface; `TestIsSpanHelper` / `TestGeneratedGuard` stay green.
- Verification (native-present env): `fltk/unparse/test_is_span_guard.py` (10) +
  `fltk/unparse/` + `fltk/test_plumbing.py` = 300 passed (incl. the four §2.6(a)-restored unparse
  round-trips and the full-pipeline integration tests). ruff check + format + pyright clean on the
  2 touched source files.
- Committed `--no-verify` (intermediate increment; the final delta increment — D6 regen — must pass
  the full `make check`). Remaining delta work: the D6 regen (`make gencode` → `make fix`) of the
  committed `*_cst.py` / `*_cst_protocol.py` / `*_parser.py` / `fltk/_stubs/fegen_rust_cst/cst.pyi`
  artifacts to the new `SpanProtocol` surface, plus the retargeted union-surface tests
  (`fltk/fegen/test_cst_protocol.py` §4-item-8 rework and the `tests/test_gsm2tree_rs.py`
  conformance pair going green once the committed protocol is regenerated).

---

## Increment 18 — DELTA D6: regenerate committed artifacts to the `SpanProtocol` surface + retarget union-surface tests (FINAL)

Final delta increment. Regenerated the committed generated artifacts onto the D3.x surface and
reworked the one remaining union-surface test suite that breaks under it. `make check` is GREEN
without `--no-verify` (lint, format-check, typecheck/pyright, full pytest, all cargo lanes,
cargo-deny). The increment-11 pyright blocker is resolved: the parser now annotates its invariant
terminal-consume returns with the concrete `terminalsrc.Span` it constructs, and the cross-backend
CST/protocol/`.pyi` span slots are the agnostic `SpanProtocol` — no `typing.cast`.

- `make gencode` → `make fix`: regenerated 21 committed Python artifacts +
  `fltk/_stubs/fegen_rust_cst/cst.pyi`:
  - Parsers (`fltk/fegen/{fltk,bootstrap,bootstrap_trivia,fltk_trivia,regex,regex_trivia}_parser.py`,
    `fltk/unparse/{toy,toy_trivia,unparsefmt,unparsefmt_trivia}_parser.py`): gained
    `from __future__ import annotations`; dropped the `import fltk.fegen.pyrt.span` selector; the
    `_source_text` initializer and the two terminal-consume `with_source(...)` sites construct
    `fltk.fegen.pyrt.terminalsrc.*`; `consume_literal`/`consume_regex` now return
    `ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]` (concrete — exact-match the construction, so
    invariance is satisfied with no cast).
  - Concrete CST + protocol (`*_cst.py`, `*_cst_protocol.py`): `span` field and every span-typed
    child → `fltk.fegen.pyrt.span_protocol.SpanProtocol`; `TYPE_CHECKING` imports drop the `span`
    selector and `fltk._native`, add `span_protocol`. The concrete `span` default stays
    `terminalsrc.UnknownSpan` (assignable to `SpanProtocol` per D3.1). The runtime
    `_get_native_span_type()` mutator-validation helper (a `sys.modules.get("fltk._native")` string
    lookup) is unchanged — runtime mechanism, not a static annotation.
  - Rust `.pyi` stub (`fltk/_stubs/fegen_rust_cst/cst.pyi`): span field/children → `SpanProtocol`;
    imports drop `fltk._native` / `terminalsrc` / `span` selector, add `span_protocol`.
- `fltk/fegen/test_cst_protocol.py`: reworked the §4-item-8 "Protocol span additive-widening" suite
  (the three union-pinning fixtures/tests `test_python_backend_consumer_still_type_checks`,
  `test_rust_backend_span_satisfies_widened_protocol`,
  `test_python_backend_uncasted_callsite_annotation_churn`) into a single agnostic-consumer
  conformance fixture + `test_agnostic_consumer_reads_span_as_spanprotocol`: a `SpanProtocol`-typed
  consumer reads `node.span` and passes it to `SpanProtocol`-typed params with NO cast, asserting 0
  pyright errors (the consumer side of swap-ability). Updated the batch-fixture writer (3 old fixture
  files → 1) and the "(6 → 4 fixture files)" doc count. DISPOSITION: reworked (not retired) — the
  Rust-span *runtime* conformance the old `test_rust_backend_...` checked is now (correctly per D5.2)
  pinned by `pyrt/test_span_protocol_assignability.py`'s `test_rust_span_isinstance_protocol`, and
  the union-narrowing-churn documentation test is obsolete (no union remains), so no coverage is
  silently dropped.
- `fltk/fegen/test_cst_protocol.py`: added two committed-source assertions (D6 test-plan item "No
  native / no selector in the generated pipeline") completing that coverage for the concrete-CST and
  protocol modules — `test_committed_protocol_source_names_no_native_no_selector` (protocol names
  `fltk._native` nowhere; no `import fltk.fegen.pyrt.span` selector; imports `span_protocol`) and
  `test_committed_cst_source_imports_no_native_no_selector` (concrete CST does not *import*
  `fltk._native` — the lone reference is the runtime `sys.modules.get("fltk._native")` mutator-
  validation string, excluded; no selector import; imports `span_protocol`). The parser
  (`test_genparser.py`), Rust `.pyi` (`test_gsm2tree_rs.py`), and unparser (`test_is_span_guard.py`)
  already pinned this property; with these two, all five generated-pipeline surfaces assert it.
- Deviation (alternative approach, D6 test-plan item "Pyright-stability regression"): the delta's D6
  lists a literal differential pyright run (same diagnostics with the `fltk/_native/__init__.pyi`
  stub present vs. absent) over a generated triad. I implemented that requirement's *property* via
  the deterministic full-pipeline source-level "names neither `fltk._native` nor the `span` selector"
  assertions (above) rather than a stub-toggling differential run. Rationale: per delta D5.1 a module
  that never names a symbol is trivially stub-stable for it, so the source-level assertions are a
  *stronger* and deterministic guarantee; a differential run would additionally require renaming the
  committed stub mid-test (no precedent in the suite; fragile, repo-mutating) for a strictly weaker
  check. No TODO is recorded — the property is fully covered, so a deferred redundant test would be
  cruft. (`pyright` over the committed `fltk/` is also green in the gate, independently confirming
  the CST/protocol modules resolve cleanly.)
- `tests/test_gsm2tree_rs.py`: the two `TestGeneratePyiConformance::{test_fegen_whole_module_no_cast_zero_errors,
  test_fegen_per_class_no_cast_zero_errors}` (failing at increment 16 against the still-old committed
  protocol) now pass — the regen carried `fltk.fegen.fltk_cst_protocol` to `SpanProtocol`, so the
  fresh `.pyi`'s `span: SpanProtocol` reconciles. No test edit needed (increment 16 already retargeted
  this file's header/class unit tests).
- Out-of-scope drift EXCLUDED (deviation, deliberate): `make gencode` also regenerates `src/lib.rs`
  via `gen-rust-lib`, which drops the `LineColPos` pyclass registration. This is **pre-existing
  drift unrelated to the delta**: at base commit `49e9701` `src/lib.rs` already carries the hand-
  maintained `LineColPos` registration that `gsm2lib_rs.py` does not emit, and neither `src/lib.rs`
  nor `gsm2lib_rs.py` was touched anywhere in `49e9701..HEAD`. The delta never touches the Rust
  native-module wiring. Committing the regenerated `src/lib.rs` would remove `fltk._native.LineColPos`
  and break `tests/test_rust_span.py` (which imports/tests it). So `src/lib.rs` was reverted with
  `git checkout` and is NOT part of this commit. (`make check` does not run `gencode`, so this drift
  does not gate; it is a standing pre-existing gencode/committed-source inconsistency outside this
  work's scope.)
- Observation (left as-is, not in delta D6's retarget list, does not break):
  `tests/test_clean_protocol_consumer_api.py::test_python_backend_consumer_pyright_clean` still passes
  under `SpanProtocol` — its fixture assigns a `terminalsrc.Span` into `node.span` then reads it back,
  and pyright narrows the member access to `terminalsrc.Span`, so the `terminalsrc.Span`-typed helper
  call stays clean. Its fixture comments still narrate the removed `terminalsrc.Span | fltk._native.Span`
  union (now stale), but the test functionally validates a real property and is not a make-check
  blocker; refreshing its prose is out of scope for this increment.
- Verification: `make check` GREEN without `--no-verify` —
  `check: all steps passed (check-ci + cargo-deny)`. Pre-commit affected files also run clean
  in isolation (334 passed across `test_cst_protocol.py`, `test_gsm2tree_rs.py`,
  `test_clean_protocol_consumer_api.py`, `test_span_protocol_assignability.py`,
  `test_python_parser_span_backend.py`, `test_is_span_guard.py`, `test_genparser.py`).
- Committed in two parts, both WITHOUT `--no-verify` (final increment; the pre-commit gate ran
  `make check` each time): commit 1 = the regen + the §4-item-8 rework + `cst.pyi`; commit 2 = the
  two committed-source no-native/no-selector tests for the CST/protocol modules + this log update.
  With this, the entire delta-amended design (original §§1–4.1 as amended by delta D1–D8.1) is
  implemented and `make check` is clean.
