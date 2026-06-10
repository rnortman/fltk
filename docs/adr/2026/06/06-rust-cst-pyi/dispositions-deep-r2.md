# Dispositions: deep review rework round (ce786b0..f9517ea)

Style: concise, precise. Audience: smart LLM/human. No padding.

---

## test-6

- Disposition: Won't-Do
- Action: Deleted the bare slugless `# TODO: add test_poc_per_class_no_cast_zero_errors ...` comment. No stub code added.
- Rationale: The PoC grammar's `Items` and `Trivia` classes have structurally different child types than the fegen protocol's counterparts of the same name (`Items` has `Identifier` children in the PoC grammar vs `Item` children in fegen; `Trivia` has no `block_comment`/`line_comment` accessors). Per-class conformance against the fegen protocol cannot be asserted for PoC classes — it would fail by design. Empirically confirmed: adding the test produces 2 pyright errors (`poc_cst.Items` and `poc_cst.Trivia` incompatible with their protocol counterparts). The emitter code path is shared; the fegen per-class test covers all three class shapes (Identifier, Items, Trivia) via the fegen grammar where they are correctly shaped. Won't-Do is the correct disposition; the bare TODO comment was the violation.

## test-7

- Disposition: Fixed
- Action: `tests/test_gsm2tree_rs.py:883-888` — dropped the `# TODO:` prefix, replaced with a plain explanatory comment documenting that the fast lint catches only quoted-string forms and that pyright conformance tests are the authoritative guard.
- Severity assessment: No functional impact; convention violation (bare slugless `# TODO:`) removed.

## reuse-1

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree_rs.py:339-345` — `_node_kind_python_name` now takes `rule_name: str` and delegates to `self._py_gen.node_kind_member_name(rule_name)`; both call sites in `_node_kind_block` and `generate_pyi` updated to pass `rule_name` from `_rule_info()`. Removed `## pyi-node-kind-name-reuse` from `TODO.md`.
- Severity assessment: CstGenerator is now the single source of truth for NodeKind member naming across .rs, .pyi, and protocol. A future naming convention change no longer risks silent divergence in the .pyi emitter.

## efficiency-1

- Disposition: Fixed (minimum-viable) / TODO(pyright-batch-tests) for remainder
- Action: `tests/test_gsm2tree_rs.py:1071-1097` — added `fegen_pyright_diagnostics` module-scoped fixture that writes all three fegen fixture files (stub, conformance_fixture.py, per_class_fixture.py) into one `tmp_path_factory` tmpdir and runs a single `uv run pyright --outputjson <dir>` over it; added `_run_pyright_over_dir` helper that partitions `generalDiagnostics` by file path. Updated `TestGeneratePyiSelfCheck.test_fegen_pyi_self_check_zero_errors`, `TestGeneratePyiConformance.test_fegen_whole_module_no_cast_zero_errors`, and `TestGeneratePyiConformance.test_fegen_per_class_no_cast_zero_errors` to consume the shared fixture. Narrowed `## pyright-batch-tests` TODO.md entry to the remaining PoC+cross-file work.
- Severity assessment: Reduces pyright subprocess invocations from 4 to 2 (fegen batch + PoC self-check). The PoC per-class conformance test was disposed as Won't-Do (test-6), so PoC self-check is the one remaining separate run for new-this-iteration tests.

## efficiency-2

- Disposition: Fixed
- Action: `tests/test_gsm2tree_rs.py:140-163` — extracted `fegen_generator` module-scoped fixture; `fegen_source` and `fegen_pyi` now derived from it. Removed `## fegen-pyi-fixture-sharing` from `TODO.md`.
- Severity assessment: Fegen grammar parse pipeline now runs once per test module (was twice). Removes the fixture duplication that invited a third copy on future additions.

## efficiency-3

- Disposition: Fixed
- Action: `tests/test_fltk_native_stub.py:53-56` — added `@functools.cache` to `_parse_stub`; dropped the `# TODO(pyright-batch-tests):` comment; replaced with a plain docstring sentence.
- Severity assessment: `_parse_stub` now reads and parses the stub file once per process; subsequent calls return the cached `ast.Module`. The TODO comment is gone.
