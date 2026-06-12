# Efficiency review — rust-cst-eq-depth (b02cb8f..44458c5)

Style note: concise, precise, complete, unambiguous; no padding. Audience: LLM/human reviewers.

Scope reviewed: generator changes (`fltk/fegen/gsm2tree_rs.py` `_eq_block`, `_emit_eq_arm`, `eq_shallow_enqueue`, iterative `impl PartialEq` driver), `crates/fltk-cst-core/src/shared.rs` (docs only), regenerated Rust/Python outputs, new depth tests in `tests/rust_parser_fixture/src/native_tests.rs`.

The core scheme is efficient as designed: lazy `Vec::new()` worklist (no allocation for shallow/all-ptr_eq comparisons), per-pair `ptr_eq` filtering *before* enqueue (shared subtrees never enqueued or re-locked), guards held one arm at a time, `compare(self, ...)` by value so Arc pairs drop promptly, span-only classes keep the O(1) one-line `eq`. Early-mismatch paths return before any descent at that level. No redundant traversals, no per-node heap allocation beyond the worklist, O(min(|A|,|B|)) peak memory replacing O(depth) stack. The deferred (worklist round-trip) handling of span-only leaf children costs ~2 Arc clone/drop + push/pop per leaf vs. inline comparison, but inlining would acquire child locks under the parent guards — a deliberate, documented lock-discipline constraint of the design (§2.2b); not flagged.

## efficiency-1: nondeterministic generated-Python output — spurious churn on every regen

- **Where**: `fltk/fegen/gsm2tree.py:25` (`types: set[ModelType]`) iterated at `gsm2tree.py:~407` (`for mt in model.types:` in the mutator type-check emission). Visible in this diff as pure-shuffle hunks: `fltk/fegen/bootstrap_cst.py` (e.g. `isinstance(child, Alternatives | Trivia | Identifier)` → `Identifier | Trivia | Alternatives`), `fltk/fegen/fltk_cst.py`, `fltk/unparse/toy_cst.py`, `fltk/unparse/unparsefmt_cst.py` — ~80 changed lines with zero semantic content.
- **Problem**: the runtime-check emission iterates a `set[str]`-keyed structure in hash order. With PYTHONHASHSEED randomization, every generator run reorders the `isinstance(child, A | B | ...)` unions and `_MUTATOR_ALLOWED_CHILD_TYPES` tuples. The dedup loop at `gsm2tree.py:~417` preserves *input* order ("deterministic output" comment), but the input order is itself nondeterministic. The annotation path is already sorted (`py_annotation_for_model_types`, `gsm2tree.py:88`); the check-emission path is not.
- **Consequence**: every `make gencode` dirties all four generated Python files with semantically empty diffs. Cost shows up per regen: inflated review diffs (this change carries ~80 unrelated churn lines), VCS noise that obscures real generated-output changes, and content-hash build-cache invalidation (Bazel and any downstream consumers caching on file content rebuild for no reason). Bites on every regeneration, forever, until fixed.
- **Fix**: sort before emitting — e.g. iterate `sorted(model.types, key=...)` (stable key handling the str-vs-Span-sentinel mix) in the `for mt in model.types` loop, matching the sorted-annotation precedent at `gsm2tree.py:88`. Then regenerate once to pin a canonical order. (Pre-existing defect surfaced by this regen, not introduced by it.)

No other findings.

Commit reviewed: 44458c5.
