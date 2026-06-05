## Increment 1 — Protocol generation: `gen_protocol_module` on `CstGenerator` (commit 3ffe12d)

- `fltk/fegen/gsm2tree.py:285-430`: added `protocol_node_name`, `protocol_annotation_for_model_types`, `gen_protocol_module`, `_protocol_class_for_model`, `_cst_module_protocol` to `CstGenerator`.
- `fltk/fegen/genparser.py:181-193`: wired `gen_protocol_module` into `generate` command; emits `{base_name}_cst_protocol.py` alongside `{base_name}_cst.py`; writes `# ruff: noqa: N802` header (CstModule @property methods have PascalCase names intentionally) before `ast.unparse` output.
- `fltk/fegen/fltk_cst_protocol.py`: generated from fegen grammar + `make fix`; 14 Protocol node classes (`GrammarNode`…`BlockCommentNode`) + `CstModule`; ruff and pyright clean.
- `fltk/fegen/fltk_cst.py`: regenerated as side effect + `make fix` (style normalization only; no type changes).
- Deviation: design specified `ClassVar[Label]` for nested `Label` members; shipped `ClassVar[object]` instead. Pyright flags `ClassVar[Label]` as `reportUndefinedVariable` (self-referential nested class annotation); `ClassVar[object]` satisfies the design goal (attribute-presence check via `m.Items.Label.NO_WS` resolves) without pyright errors. The design explicitly states "attribute-presence only" as the guarantee for label checking (design.md:41), so the weaker type is consistent with stated intent.

## Increment 3 — Pyright test harness + test suite + visit_grammar cast fixes (commit b2c6e20)

- `fltk/fegen/test_cst_protocol.py`: 8 tests; `run_pyright` helper (subprocess + JSON, `pytest.skip` when unavailable).
  - T1: `test_protocol_module_has_one_class_per_rule`, `test_protocol_node_has_required_members`, `test_cst_module_protocol_has_property_per_rule` — assert per-node Protocol members from fegen grammar.
  - T2a: `test_member_access_fixture_zero_errors`, `test_wrong_member_access_is_flagged` — member resolution and negative (wrong method flagged).
  - T2b: `test_boundary_probe_documents_label_mismatch` — bare assignment produces errors, confirms cast necessity.
  - T4: `test_protocol_is_not_dataclass_specific` — plain-class stand-in cast accepted.
  - T5: `test_fltk2gsm_does_not_import_protocol_at_runtime` — protocol absent from sys.modules at runtime.
- `fltk/fegen/genparser.py:9-10,62`: added TYPE_CHECKING import of cstp; cast result.result to cstp.GrammarNode at visit_grammar call site.
- `fltk/unparse/genunparser.py:9-10,50`: same cast pattern.
- `fltk/test_plumbing.py:11-12,581`: same cast pattern.
- `fltk/fegen/gsm2tree.py`: ruff format (whitespace only, no logic change).
- T3 and T6 are gate-level; `uv run pyright` (0 errors) and `make check` (782 tests pass) verified at commit.

## Increment 2 — fltk2gsm.py: restore visit_* annotations + DI boundary casts (commit ae53867)

- `fltk/fegen/fltk2gsm.py:1-22`: added `from __future__ import annotations`, replaced `ModuleType` import with `typing.cast`, added `TYPE_CHECKING`-only import of `fltk_cst_protocol as cstp`.
- `fltk/fegen/fltk2gsm.py:15-18`: added `_DEFAULT_CST: cstp.CstModule = cast("cstp.CstModule", _default_cst)` module-level sentinel (B008: no function call in default argument position); `__init__` now `cst: cstp.CstModule = _DEFAULT_CST`.
- `fltk/fegen/fltk2gsm.py`: restored all 11 `visit_*` primary-parameter annotations (`cstp.GrammarNode`, `cstp.RuleNode`, `cstp.IdentifierNode`, `cstp.AlternativesNode`, `cstp.ItemsNode`, `cstp.ItemNode`, `cstp.TermNode`, `cstp.DispositionNode`, `cstp.QuantifierNode`, `cstp.LiteralNode`, `cstp.RawStringNode`).
- `fltk/plumbing.py:31-34`: added `TYPE_CHECKING`-only import of `cstp`; added `cast` to `typing` import.
- `fltk/plumbing.py:147-150`: cast `result.result` (concrete `fltk_cst.Grammar`) to `cstp.GrammarNode` at the Python-default-path call site — same nominal nested-Label mismatch as the `__init__` default binding.
- `fltk/plumbing.py:179-183`: cast `pr.cst_module` to `cstp.CstModule` and `result.result` to `cstp.GrammarNode` at the Rust-injection call site — the documented `di-boundary-escape` Rust boundary cast.
- pyright clean (0 errors) on both files; all 774 tests pass; ruff clean.
- Deviation: design specified one boundary cast at `__init__`'s default binding; also required casts at the two `visit_grammar(result.result)` call sites in `plumbing.py` (Python and Rust paths) because `result.result` is typed concretely by the parser and does not satisfy `GrammarNode` structurally (same nested-Label limitation). Three casts total, all documented at their sites.
