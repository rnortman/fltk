# Efficiency review — rust-cst-pyi

Reviewed: 46a6639..c78a014 (HEAD c78a014).
Style: concise, precise, complete, unambiguous. No padding.

## efficiency-1 — four cold pyright subprocesses, no batching

`tests/test_gsm2tree_rs.py:961-1139` (`pyright_available` fixture, `_run_pyright_in_tmpdir`,
`TestGeneratePyiSelfCheck` ×2, `TestGeneratePyiConformance` ×2).

Each of the 4 new tests spawns its own `uv run pyright --outputjson` in a fresh per-test
`tmp_path` with its own `pyrightconfig.json`. Each run pays full cold cost: `uv` resolution +
node/pyright startup + re-analysis of the entire `fltk` import closure (`fltk_cst_protocol`
et al.) — no analysis cache is shared across tmpdirs. The three fegen-stub tests even check
the *same* generated stub text three times in three separate dirs.

**Consequence:** roughly 4× multi-second cold pyright runs (typically 20–60 s total) added to
every `uv run pytest`, serialized; scales linearly as more grammars/fixtures get this
treatment.

Fix: stage all stubs + fixture files into one module-scoped tmpdir and invoke pyright once
over the directory, partitioning `generalDiagnostics` by file path per assertion (one test or
parametrized asserts over a session-scoped result). Minimum viable: merge the fegen self-check
+ whole-module + per-class fixtures into a single tmpdir/run (they already share `fegen_pyi`).

## efficiency-2 — fegen.fltkg parse pipeline duplicated by `fegen_pyi` fixture

`tests/test_gsm2tree_rs.py:748-765` (`fegen_pyi`) repeats verbatim the
read → `fltk_parser.Parser` parse → `Cst2Gsm` → `RustCstGenerator` pipeline already run by the
module-scoped `fegen_source` fixture (`:140-153`) (and a third copy inside a test at
`:497-507`, pre-existing). `RustCstGenerator.__init__` additionally rebuilds a full
`CstGenerator` (rule models for all 14 rules) each time. The self-hosted parse of the full
grammar file runs under pytest's debug-logging config, so it is the slow step.

**Consequence:** one extra full-grammar parse + generator construction per test-module run,
pure duplicate work; pattern invites a fourth copy next time a fegen fixture is needed.

Fix: one module-scoped `fegen_generator: RustCstGenerator` fixture; derive `fegen_source`
(`gen.generate()`) and `fegen_pyi` (`gen.generate_pyi(...)`) from it. Same for
`poc_source`/`poc_pyi` (cheap, but free to share).

## efficiency-3 — stub re-read/re-parsed per helper call; dead parent-annotation pass

`tests/test_fltk_native_stub.py:53-112`.

- `_parse_stub()` re-reads and re-parses `fltk/_native/fegen_cst.pyi` on every helper call:
  `_stub_top_level_names()` (2 tests) + `_stub_classes_with_members()` (2 tests) = 4
  read+parse cycles of the ~400-line stub per run.
- `_stub_classes_with_members()` (`:74-77`) runs a full `ast.walk` + `iter_child_nodes`
  parent-annotation pass over every node whose result it never uses — `node.parent` is read
  only by `_stub_class_names()` (`:57-64`), which is never called (and which parses its own
  fresh tree, where the parents wouldn't exist anyway). The pass is 100% dead work executed
  twice per run.

**Consequence:** minor but pure waste on every test run; the dead pass also misleads readers
into preserving it.

Fix: parse once at module scope (or `functools.cache` on `_parse_stub`), drop the
parent-annotation loop, delete the unused `_stub_class_names`.

## Not flagged

- `generate_pyi` calling `_rule_info()` afresh (4th O(rules) recompute per generator instance,
  alongside `generate`/`_node_kind_block`/`_register_classes_fn`): one-shot offline codegen,
  pre-existing pattern, negligible.
- `import fltk._native` now emitted unconditionally into generated Python CST modules
  (`gsm2tree.py:181-184`): no measurable import-time cost when the extension exists (the
  `fltk.fegen.pyrt.span` selector already loads it); the hard-ImportError in pure-Python
  fallback environments is a compatibility/correctness question, not efficiency — flagged to
  the correctness lane.
- `python_label = label.upper()` / `del python_label` in `generate_pyi`
  (`gsm2tree_rs.py:184,193`): dead assignment, trivial cost — quality lane.
