# Deep efficiency review — Phase 4 runtime integration

Commit reviewed: cdffac4 (base f8a2fe1). Concise. Precise. No content pasted from sources.

## efficiency-1 — `parse_grammar(rust_fegen_cst_module=...)` rebuilds the whole Rust fegen parser on every call

`fltk/plumbing.py:129-148`. The Rust branch calls `generate_parser(fegen_grammar, rust_cst_module=...)`
on every `parse_grammar` invocation. `generate_parser` (`plumbing.py:201-258`) does, each time:
`create_default_context`, `add_trivia_rule_to_grammar` + `classify_trivia_rules`, construct
`CstGenerator`, `importlib.import_module(rust_cst_module)` + `vars()` scan
(`_load_rust_cst_classes`), construct `ParserGenerator`, `compiler.compile_class`, `ast.fix_missing_locations`,
and a full `exec(compile(parser_module, ...))` of the generated parser source. The Python branch
by contrast reuses the committed, already-imported `fltk_parser.Parser` — near-zero setup.

The fegen grammar is fixed (`_load_fegen_grammar` is cached at module scope, `plumbing.py:36-51`),
so the entire derived artifact — trivia-classified grammar, generated parser class, and `cst_module` —
is identical across every Rust-backed `parse_grammar` call for the life of the process. Nothing is cached.

Consequence: every Rust-backend grammar parse pays full parser-codegen + `exec` + module-import cost
(milliseconds-to-tens-of-ms of `compile`/`exec`, dominating the actual parse for small grammars).
Bites whenever a caller parses more than one grammar with the Rust backend, or parses repeatedly
(e.g. a tool/loop, a test suite parsing many `.fltkg` files). The Python path has no such cost, so the
Rust backend is gratuitously slower at the one thing this phase adds.

Fix: cache the `generate_parser` result keyed by `(id(fegen_grammar), rust_fegen_cst_module)` at module
scope, parallel to `_fegen_grammar_cache`. Since `fegen_grammar` is a singleton and the module name is a
short string, a one-entry-per-module dict suffices. Reuse `pr.parser_class` and `pr.cst_module` across
calls; only `TerminalSource` + parse + `Cst2Gsm` are per-call. This makes the Rust path's per-call cost
match the Python path's.

## efficiency-2 — `Cst2Gsm.visit_items` materializes a full filtered copy of every node's children

`fltk/fegen/fltk2gsm.py:40`. `labeled_children = [(label, val) for label, val in items.children if label is not None]`
builds a new list for every `Items` node visited, on both backends. For the Python backend the comment
states no `None`-labeled children ever exist, so this is a pure full-copy no-op that filters nothing;
for the Rust backend it strips trivia. Either way it allocates a list proportional to child count for
every `Items` node in the tree, where the old code indexed `items.children` in place.

Consequence: per-node allocation across the whole CST during grammar conversion — O(total children)
extra allocation on a path that previously did none. Modest in absolute terms (grammar conversion is not
a tight inner loop), but it is new per-node work added to a tree walk, paid even by the unchanged Python
backend that gains nothing from the filter.

Fix (optional): skip the copy when nothing is filtered — e.g. only rebuild if any child has a `None`
label, or gate the filter on the Rust backend. Low priority; flagged because it taxes the default
Python path for a Rust-only concern. If kept for simplicity, no action needed — the cost is small and
the uniform code path has clarity value.

## Not findings (checked, OK)

- `_load_fegen_grammar` is correctly cached at module scope (`plumbing.py:36-51`); the fegen grammar is
  parsed at most once per process. Good.
- The `GILOnceCell` sentinel cache in `gsm2tree_rs.py` (generated `#[new]`) replaces a per-construction
  `crate::` static read with a one-time `fltk._native` import then a cached `clone_ref` — correct and
  cheaper than a Python import per node. No per-node import cost. Good.
- `parse_grammar_file` pre-checks `grammar_path.exists()` before `open()` (`plumbing.py:167`) — a TOCTOU
  existence check (catch #5). Pre-existing (not introduced by this diff); out of review scope. Noted only.
- `_load_rust_cst_classes` `vars(module)` scan is bounded by class count and runs once per
  `generate_parser` call — acceptable in isolation; its repetition is covered by efficiency-1.
