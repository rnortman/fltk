# Dispositions: deep review (46a6639..c78a014)

Style: concise, precise. Audience: smart LLM/human. No padding.

---

## correctness-1

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree.py:171-200` — added `from __future__ import annotations` and moved `import fltk._native` + `import fltk.fegen.pyrt.span` under `if typing.TYPE_CHECKING:` in `gen_py_module`, matching the protocol generator. Regenerated `fltk_cst.py`, `bootstrap_cst.py`, `toy_cst.py`, `unparsefmt_cst.py`.
- Severity assessment: Critical regression. Any pure-Python install (no compiled extension) would get `ModuleNotFoundError` at import of any generated CST module, breaking all parsing. The Bazel pure-Python path was silently broken.

## correctness-2

- Disposition: Fixed
- Action: `tests/test_fltk_native_stub.py:57-64` — deleted `_stub_class_names()` entirely. (Same as errhandling-3, quality-4, test-1.)
- Severity assessment: Latent crash. The function was dead, but misleading comment invited future callers that would raise `AttributeError`.

## correctness-3

- Disposition: Fixed
- Action: `fltk/fegen/genparser.py:312-314` — added guard: emit `typer.echo("Error: --pyi-output requires --protocol-module")` and `raise typer.Exit(1)` when `pyi_output is not None and protocol_module is None`.
- Severity assessment: Silent data loss. Operator providing `--pyi-output` without `--protocol-module` would believe the stub was regenerated when it was not, causing `.rs`/`.pyi` drift undetected until B4 runtime tests ran.

## correctness-4

- Disposition: Fixed
- Action: `tests/test_fltk_native_stub.py:60-61` — corrected docstring to say "dunder names (including `__init__`) are excluded" rather than claiming `__init__` is included.
- Severity assessment: No runtime impact today; misleading documentation invites incorrect expectations about test coverage.

## correctness-5

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree_rs.py:184,193` — removed `python_label = label.upper()` and `del python_label`. (Same as quality-3.)
- Severity assessment: Dead code only; no runtime consequence, but misleads readers into thinking the ALL_CAPS label name is used.

---

## errhandling-1

- Disposition: Fixed
- Action: `fltk/fegen/genparser.py:317-331` — wrapped `RustCstGenerator(grammar)` in `try/except ValueError`; wrapped `generate_pyi()` and `generate()` in `try/except (ValueError, RuntimeError)`; both emit `typer.echo(f"Error: {e}", err=True)` and `raise typer.Exit(1)`.
- Severity assessment: Operator sees a Python traceback instead of a clean CLI error when a grammar has invalid identifiers or empty-model rules. Diagnostic is present in the exception message but buried in noise.

## errhandling-2

- Disposition: Fixed
- Action: `tests/test_fltk_native_stub.py:35` — narrowed `except Exception` to `except (ImportError, ModuleNotFoundError)` in `_try_import_fegen_cst`.
- Severity assessment: A broken-but-present extension (PyO3 init panic, ABI mismatch) would silently skip all B4 runtime-agreement tests rather than failing. CI shows "skipped" instead of "failed" during exactly the failure mode tests are designed to catch.

## errhandling-3

- Disposition: Fixed
- Action: Same as correctness-2 — `_stub_class_names()` deleted.
- Severity assessment: As correctness-2.

---

## test-1

- Disposition: Fixed
- Action: Same as correctness-2 — `_stub_class_names()` deleted.
- Severity assessment: As correctness-2.

## test-2

- Disposition: Fixed
- Action: `tests/test_fltk_native_stub.py:204-210` — removed `or hasattr(runtime_cls(), member)` fallback. `Label` is a classattr accessible on the class object; `runtime_cls()` would raise `TypeError` for PyO3 classes that require constructor arguments.
- Severity assessment: If a future stub member is only accessible on an instance, the test would raise `TypeError` from PyO3 rather than a useful assertion failure. False confidence that instance-level checking is covered.

## test-3

- Disposition: Fixed
- Action: `fltk/fegen/test_genparser.py:181-215` — added `ast.parse(pyi_text)` call to catch syntactically invalid stub output; added docstring explaining the test verifies plumbing only (mismatched grammar/protocol pair is deliberate) and pointing to `TestGeneratePyiConformance` for type-correctness coverage.
- Severity assessment: Emitter bugs producing syntactically correct but type-incorrect content would pass this test. Now at least syntax validity is guarded; pyright conformance tests cover type correctness for the matched fegen pair.

## test-4

- Disposition: Fixed
- Action: `fltk/fegen/test_genparser.py:241-255` — added `result1 = ` and `result2 = ` captures; added `assert result1.exit_code == 0` and `assert result2.exit_code == 0` after each `runner.invoke`.
- Severity assessment: If `generate_pyi` raises, the second invocation fails silently, and the `.rs` equality assertion can pass vacuously (both writes fail identically → both files empty or both unchanged).

## test-5

- Disposition: Fixed
- Action: `tests/test_gsm2tree_rs.py:488-501` — added `test_pyi_two_calls_produce_identical_strings` and `test_pyi_two_generator_instances_produce_identical_strings` in `TestDeterministicOutput`.
- Severity assessment: No guard against future introduction of non-deterministic set/dict iteration in `generate_pyi`, which would produce noisy committed-file diffs and flaky pyright checks.

## test-6

- Disposition: TODO(poc-per-class-conformance)
- Action: Added inline TODO comment at `tests/test_gsm2tree_rs.py` after `test_fegen_per_class_no_cast_zero_errors`. No `TODO.md` entry (finding is low-priority and the fegen tests already cover the same class names `Identifier`, `Items`, `Trivia`).
- Severity assessment: Minimal. The PoC grammar's class names are a subset of the fegen grammar's, and per-class conformance on those shapes is already verified by the fegen tests. A PoC-specific test would only catch a bug that affects small grammars but not the fegen grammar's version of the same class — unlikely given shared emitter code.

## test-7

- Disposition: TODO(pyi-bare-upper-annotation-check)
- Action: Added inline TODO comment at `tests/test_gsm2tree_rs.py:test_no_stub_local_class_names_in_annotations` noting the gap. The pyright conformance tests serve as the authoritative guard.
- Severity assessment: Minimal. A bare unqualified uppercase annotation from the emitter would be caught by the pyright conformance tests before reaching consumers. The fast pre-pyright lint only catches the quoted-string form.

---

## reuse-1

- Disposition: TODO(pyi-node-kind-name-reuse)
- Action: Added TODO comment in `fltk/fegen/gsm2tree_rs.py:_node_kind_python_name`; added `## pyi-node-kind-name-reuse` entry to `TODO.md`.
- Severity assessment: Divergence risk is real but low probability: both `_node_kind_python_name` and `CstGenerator.node_kind_member_name` are trivially `.upper()`. A naming convention change would affect both; the three-generator mismatch (`.rs`, `.pyi`, protocol) would be caught by conformance tests.

## reuse-2

- Disposition: TODO(pyi-label-quintet-reuse)
- Action: Added TODO comment in `fltk/fegen/gsm2tree_rs.py` before the per-label quintet loop; added `## pyi-label-quintet-reuse` entry to `TODO.md`.
- Severity assessment: If a sixth accessor is added to `_emit_label_quintet`, `generate_pyi` would miss it and silently produce an incomplete stub. The B4 runtime-to-stub direction test would catch it (a runtime method absent from the stub). Bounded risk given the quintet is stable.

---

## quality-1

- Disposition: Fixed
- Action: Same as correctness-1. Duplicate finding from a different reviewer; resolved together.
- Severity assessment: As correctness-1.

## quality-2

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree_rs.py` — added `from collections.abc import Iterable` and `from fltk.fegen.gsm2tree import CstGenerator, ModelType`; changed `_pyi_annotation_for_model_types` parameter from `model_types: object` to `model_types: Iterable[ModelType]`; removed `# type: ignore[arg-type]`.
- Severity assessment: Type system was blind to callers passing wrong types. Future refactoring of `ModelType` or `protocol_annotation_for_model_types` would silently break this path without a type error.

## quality-3

- Disposition: Fixed
- Action: Same as correctness-5.
- Severity assessment: As correctness-5.

## quality-4

- Disposition: Fixed
- Action: Same as correctness-2.
- Severity assessment: As correctness-2.

---

## efficiency-1

- Disposition: TODO(pyright-batch-tests)
- Action: Added TODO comment in `tests/test_gsm2tree_rs.py:_run_pyright_in_tmpdir`; added `## pyright-batch-tests` entry to `TODO.md`.
- Severity assessment: ~20-60 s added to every `uv run pytest`, serialized. Real CI cost but not a correctness issue.

## efficiency-2

- Disposition: TODO(fegen-pyi-fixture-sharing)
- Action: Added TODO comment in `tests/test_gsm2tree_rs.py:fegen_pyi` fixture; added `## fegen-pyi-fixture-sharing` entry to `TODO.md`.
- Severity assessment: One extra full-grammar parse + generator construction per test-module run. Minor; pattern invites a fourth copy next time.

## efficiency-3

- Disposition: Fixed (partially) / TODO
- Action: The dead parent-annotation loop in `_stub_classes_with_members` was eliminated as a side effect of deleting `_stub_class_names()` (correctness-2 fix). The `_parse_stub` re-read per call remains; added a TODO(pyright-batch-tests) comment at `tests/test_fltk_native_stub.py:_parse_stub` (reuses the same slug — the fix is parse-once at module scope alongside the pyright batching work).
- Severity assessment: Minor pure waste on every test run; dead parent-annotation loop (now removed) was the misleading part.

---

## security-1

- Disposition: Won't-Do (no finding)
- Action: No change. Reviewer found no security issues.
- Severity assessment: N/A.
