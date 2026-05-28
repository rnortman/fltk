# Deep Correctness Review — Phase 4 Runtime Integration

Reviewed: base `f8a2fe1` .. HEAD `cdffac4`. Mandate: does the code do what it appears to.
Concise. Precise. Audience: smart LLM/human.

Scope reviewed: `fltk/plumbing.py`, `fltk/fegen/fltk2gsm.py`, `fltk/fegen/genparser.py`,
`fltk/fegen/gsm2tree_rs.py`, generated `src/cst_fegen.rs`/`src/cst_generated.rs`,
`tests/rust_cst_fegen/src/cst.rs` accessor/append logic, and the new tests. Python suites
`test_plumbing.py`, `test_genparser.py`, `test_gsm2tree_rs.py` run green (87 tests). Tier-2
Rust-artifact tests not exercised here (extensions not built in this env; they `skip`).

## Findings

### correctness-1 (note, not a behavior bug)
`src/lib.rs:10,26-28` — `pub(crate) static UNKNOWN_SPAN` is now **write-only**. After the
generator change, no code in the crate reads `crate::UNKNOWN_SPAN`; every generated
`#[new]` in `src/cst_fegen.rs` / `src/cst_generated.rs` uses its own
`UNKNOWN_SPAN_CACHE` (runtime import of `fltk._native.UnknownSpan`) instead
(`gsm2tree_rs.py:238-242`). The static is still initialized at module init but never
consulted.
- Why: the diff removed `use crate::UNKNOWN_SPAN;` from generated output and replaced the
  `.get(py)` reads with a `GILOnceCell` import, but left the producer of the now-orphaned
  static in `lib.rs`.
- Consequence: no wrong runtime behavior — `m.add("UnknownSpan", ...)` (`lib.rs:25`) is the
  attribute the runtime import fetches, and that path is correct. The dead static is a
  latent `dead_code`/unused warning risk on the next `lib.rs` regen/cleanup, and a
  correctness trap only if a future edit assumes `crate::UNKNOWN_SPAN` is still the source of
  truth. Out of strict correctness lane (no produced-behavior defect); flagged so it is not
  mistaken for live coupling.
- Fix (optional, quality): drop the `UNKNOWN_SPAN` static + its init from `lib.rs`, or add a
  comment that it is retained only for external/back-compat reasons.

### correctness-2 (verified correct — interleaving invariant under the new filter)
`fltk2gsm.py:40-76` `visit_items`. New code prepends
`labeled_children = [(l,v) for l,v in items.children if l is not None]` then runs the
existing `children[::2]`/`children[1::2]` item/separator interleaving on the filtered list.
- Verified: the Python `fltk_parser` never appends trivia into an `Items` node — inter-item
  trivia only advances `pos` (`fltk_parser.py:301,308,313,318`), so the filter is a no-op on
  the Python path (no None-labeled children exist). The Rust fegen parser (produced by
  `generate_parser`, `capture_trivia=True`) interleaves None-labeled trivia between ITEM and
  separator entries; trivia is never labeled `ITEM`/`NO_WS`/`WS_ALLOWED`/`WS_REQUIRED`, so
  removing None entries preserves the strict ITEM, sep, ITEM, sep ordering the slicing
  assumes. Leading-separator detection on `labeled_children[0]` (`:44`) correctly inspects
  the first *labeled* child, skipping any leading trivia.
- No off-by-one / mispairing introduced. Equality of `gsm.Grammar` across backends is the
  guard (`test_phase4_fegen_rust_backend.py` AC8).

### correctness-3 (verified correct — hard-error ordering, no sys.modules pollution)
`plumbing.py:210-223`, `_load_rust_cst_classes:65-91`. On Rust backend, `_load_rust_cst_classes`
runs (and may raise `RustBackendUnavailableError`) **before** `setattr` loop and
`sys.modules[module_name] = cst_module` (`:221-223`) and before any parser `exec`. So a
missing/empty module leaves `sys.modules` clean and produces no parser. Confirmed by
`test_rust_backend_missing_module_hard_errors` / `_empty_module_` / `_no_python_exec_fallback`.
`ImportError` (incl. `ModuleNotFoundError`) is caught and re-raised chained; non-import
exceptions propagate as themselves — matches design intent (genuine extension bugs surface).

### correctness-4 (verified correct — no recursion, no signature mismatch)
`plumbing.py:39-51,129-148`. `parse_grammar(rust_fegen_cst_module=...)` calls
`_load_fegen_grammar()`, which calls `parse_grammar(grammar_text)` with no
`rust_fegen_cst_module` → takes the Python branch (`:113-128`), which never calls
`_load_fegen_grammar` → terminates. Module-scope `_fegen_grammar_cache` list memoizes (one
parse/process). `pr.parser_class(terminalsrc=terminals)` (`:134`) matches the generated
parser `__init__(self, terminalsrc=...)` (`fltk_parser.py:13`). The same `pr.cst_module` is
both the parser's node source and the `Cst2Gsm` injected namespace (`:147`), satisfying the
type-identity invariant for `isinstance`/label dispatch.

### correctness-5 (verified correct — Rust accessor count/break logic)
`tests/rust_cst_fegen/src/cst.rs` `child_item`/`maybe_item`/`children_item` (and siblings):
None-labeled tuples compare unequal to the label enum (`tup.get_item(0)?.eq(&label_obj)` →
false), so trivia is skipped. `child_item` errors unless exactly one match; `maybe_item`
breaks at count==2 and errors on `count > 1`; `children_item` collects all matches. No
off-by-one. `extend`/`append_*` build `(label, child)` tuples consistently; the generic
`extend` re-clones the label per element correctly (`cst.rs:809-817`).

## Summary
No produced-behavior correctness defect found in the changed Python or generated Rust logic.
The `visit_items` None-filter, the hard-error ordering, the anti-recursion design, and the
Rust accessor interleaving all hold. correctness-1 (dead `crate::UNKNOWN_SPAN` static in
`lib.rs`) is the only flag — a latent dead-code/coupling-confusion risk, not a runtime bug.
Note repeated per directive: this file is the deliverable; no behavior contents pasted.
