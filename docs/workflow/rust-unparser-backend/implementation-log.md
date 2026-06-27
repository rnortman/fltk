# Implementation Log: Rust Unparser Backend

Design: `design.md` (effective design = design + user answers to open questions inline).
Requirements: `requirements.md`.

---

## Increment 1 — `fltk-unparser-core` crate + `Doc` type

Created the pyo3-free runtime crate and its foundational `Doc` combinator type
(design §2.1, `doc.rs` bullet).

- `Cargo.toml:2`: added `"crates/fltk-unparser-core"` to the root workspace `members`.
- `crates/fltk-unparser-core/Cargo.toml`: new crate, `rlib`, no pyo3 and no
  `fltk-cst-core` dependency (both structural absences, documented in-file per
  design §2.1).
- `crates/fltk-unparser-core/src/doc.rs`: `Doc` enum — all 14 variants from
  `combinators.py` collapsed into one enum (`Text`, `Comment`, `Line`, `Nbsp`,
  `SoftLine`, `HardLine{blank_lines}`, `Group`, `Nest{indent,content}`, `Concat`,
  `Join{docs,separator}`, `Nil`, `AfterSpec`, `BeforeSpec`, `SeparatorSpec`),
  `Rc`-wrapped children. Helper constructors port the `combinators.py` module
  functions: `text`, `comment`, `line`, `nbsp`, `softline`, `nil`, `hardline`,
  `group`, `nest`, `indent`, `join`, and `concat` (Nil/Concat flattening per
  `combinators.py:172`). Iterative `Drop` via a worklist (`take_children` helper +
  thread-local `Nil` sentinel) for stack safety per design §3 / open question 1.
- `crates/fltk-unparser-core/src/lib.rs`: re-exports `Doc` and the constructors
  (surface grows in later increments).
- 13 `#[test]`s in `doc.rs`: construction of every constructor, `concat`
  flattening/Nil-dropping/single-collapse, and three 200k-deep drop tests (group,
  concat, join) proving the iterative `Drop` does not stack-overflow.
- `cargo test -p fltk-unparser-core --no-default-features` and
  `cargo clippy ... --all-targets` both green.

Deviations:
- Design §2.1 lists named constructors `text, concat, hardline, group, nest, join`;
  shipped the rest of the trivial `combinators.py` helpers too (`comment`, `line`,
  `nbsp`, `softline`, `nil`, `indent`) to complete the faithful port — same
  semantic unit, used by later modules/generated code.
- `concat` matches nested `Concat` via `&mut` + `Vec::append` (not by-value move):
  `Doc` implements `Drop`, so moving fields out of an owned value is E0509-forbidden.
  Behavior is identical to the Python flatten.
- Derived `Debug`/`PartialEq` recurse (only `Drop` is iterative); deep-tree
  hardening of those is deferred per design §3 / answered open question 1
  (resolve/render recursion left as-is for this milestone).

---

## Increment 2 — `DocAccumulator` (accumulator.rs)

Ported `accumulator.py`'s `DocAccumulator` to the runtime crate (design §2.1,
`accumulator.rs` bullet).

- `crates/fltk-unparser-core/src/accumulator.rs`: `DocAccumulator` as the immutable
  persistent structure — private `DocNode { doc, tail }` `Rc`-linked chain plus
  `last_was_trivia`, optional `parent` (`Rc<DocAccumulator>`), optional `nesting_doc`
  placeholder. Methods port one-for-one: `new`/`Default`, `add_non_trivia`,
  `add_trivia`, `add_accumulator` (NIL-merge keeps self's trivia state),
  `push_group`/`pop_group`, `push_nest`/`pop_nest`, `push_join`/`pop_join`, and
  `doc()` (head chain reversed, flattened via `concat`). `Clone` is derived and cheap
  (Rc bumps). Pop-mismatch / merge-non-flattened invariants → `assert!`/`panic!` with
  diagnostics matching the Python `RuntimeError` messages.
- `crates/fltk-unparser-core/src/lib.rs`: `mod accumulator;` + `pub use
  accumulator::DocAccumulator;`; updated crate-doc progress note.
- 16 `#[test]`s in `accumulator.rs`: empty→Nil, add ordering, trivia flag,
  add_accumulator content+trivia-state merge (incl. NIL case), open-nesting merge
  panic, push/pop group/nest/join (incl. single-element and empty join), trivia
  propagation through pop, both pop-mismatch panics, and a 200k-deep node-chain drop.
- `cargo test -p fltk-unparser-core --no-default-features` (28 passed) and
  `cargo clippy ... --all-targets` both green.

Deviations:
- `DocNode` gets an iterative `Drop` (drains the `tail` chain through a loop), beyond
  the design's literal accumulator scope. Rationale: a flat sibling list at one
  nesting level is attacker-controlled depth, and a recursive `Rc<DocNode>` drop is
  the exact happy-path stack-overflow hazard design §3 hardened for `Doc`; the
  iterative drop keeps the same bar. Covered by `deep_node_chain_drops_*`. The
  `parent`-chain (nesting depth) drop is left recursive, same deferral class as the
  recursive `resolve`/`render` (answered open question 1).
- `pop_join`'s content→docs extraction splices via `&mut` + `std::mem::{take,replace}`
  rather than moving fields out of the owned `Doc` (E0509: `Doc` implements `Drop`),
  identical idiom to increment 1's `concat`. Behavior matches the Python list build.

---

## Increment 3 — `resolve.rs` (`resolve_spacing_specs`)

Ported `fltk/unparse/resolve_specs.py`'s spacing-resolution stage to the runtime
crate (design §2.1, `resolve.rs` bullet): the pass that rewrites `AfterSpec`/
`BeforeSpec`/`SeparatorSpec`/`Join` control nodes into concrete spacing.

- `crates/fltk-unparser-core/src/resolve.rs`: `resolve_spacing_specs(doc: &Doc) -> Doc`
  (public) plus the full private pass set, one-for-one with the Python module —
  `expand_joins`, `extract_all_boundary_specs` + `extract_boundary_specs`,
  `resolve_patterns` + `resolve_concat_patterns` (the sliding working set, now a
  `VecDeque<Rc<Doc>>`), the six precedence-ordered pattern mutators
  (`mutate_after_sep_before`, `mutate_after_sep`, `mutate_sep_before`,
  `mutate_text_newline`, `mutate_standalone_sep`, `mutate_standalone_after_before`),
  `mutate_consecutive_specs`, `collapse_hardline_sequences` + `collapse_hardline_list`,
  `resolve_spacing`, and `merge_spacing`.
- `crates/fltk-unparser-core/src/lib.rs`: `mod resolve;` + `pub use
  resolve::resolve_spacing_specs;`; crate-doc progress note updated.
- 17 `#[test]`s in `resolve.rs`, seeded from `test_resolve_specs.py`: problematic
  spec sequence, consecutive-sep collapse, after/before/sep merge (incl. HardLine
  blank-line preservation), `extract_boundary_specs` extraction, Group/Nest boundary
  bubbling, deeply-nested after-spec + separator combination, preserved-trivia
  precedence, Join expansion (incl. empty join → Nil), HardLine + soft-break collapse,
  and standalone-spec disposal.
- `cargo test -p fltk-unparser-core --no-default-features` (45 passed) and
  `cargo clippy -p fltk-unparser-core --no-default-features --all-targets` green.

Deviations / notes:
- The internal passes thread `Rc<Doc>` (not `&Doc`/owned `Doc`) so unchanged
  subtrees are reused by refcount bump, mirroring the Python frozen-dataclass sharing
  where a "pass-through" leaf is the same object. `resolve_rc` is the `Rc`-threaded
  core and the recursion target for preserved-trivia resolution. (The public signature
  was originally `resolve_spacing_specs(&Doc) -> Doc` per design §2.1; changed to take
  `Doc` by value in the deep-r1 review round — see that section below.)
- Added a private `concat_rc` (the `Rc` analog of `doc::concat`) rather than cloning
  `Vec<Rc<Doc>>` into `Vec<Doc>` to reuse the existing `concat`; same flatten/Nil-drop/
  single-collapse semantics, but preserves sharing.
- Factored the shared HardLine-blank-line preservation logic of `_mutate_after_sep`
  and `_mutate_sep_before` into one `pick_spacing_with_blank_lines` helper (the two
  Python branches are mirror images); behavior is identical to each.
- `_resolve_concat_patterns`'s Python type-guard (raise if a non-`Doc` is in the
  sequence) is dropped: the Rust `&[Rc<Doc>]` type makes it unrepresentable.
- The `_resolve_spacing` "neither trivia nor spacing" `RuntimeError` becomes an
  `assert!` (generator-bug path), matching the accumulator increment's idiom.
- `cargo fmt` also normalized the `Doc::Join` variant in `doc.rs` (increment 1
  committed `--no-verify`, so it was never fmt-checked) and `Cargo.lock` gained the
  `fltk-unparser-core` entry; both are incidental, required-by-`make check` cleanups
  pulled in here.

---

## Review round — deep r1

Fixes applied in response to the deep r1 review notes (batch 1: `doc.rs`/`accumulator.rs`/
`resolve.rs`). All 64 crate tests pass; clippy + fmt clean.

Deviations from design introduced by these fixes:

- **`resolve_spacing_specs` now takes `Doc` by value** (was `&Doc` per design §2.1).
  The `&Doc` form deep-cloned the whole tree on entry (`Rc::new(doc.clone())`) only to
  hand it to the `Rc`-threaded core — defeating the design's own "share unchanged
  subtrees" rationale on the per-unparse hot path. Callers hold an owned `Doc` from
  `accumulator.doc()`, so passing by value is a free move; the design's example call
  sites (§2.3/§2.4 `resolve_spacing_specs(&r.accumulator.doc())`) simply drop the `&`.
  (quality-1 / efficiency-4)

- **`extract_boundary_specs` no longer mirrors Python's `pop(0)`/`insert(0, …)`
  literally.** Design §2.1 frames `resolve.rs` as a literal port; this fix replaces the
  two O(n²) front-shifting loops with pop-from-end + one `reverse()` (trailing) and a
  single `drain(..k)` (leading). Output is byte-identical; only the per-Concat-level
  cost changes from super-linear to linear. (quality-2 / efficiency-3)

Non-deviation fixes (faithful improvements, no design impact):

- `Doc::drop` swaps single-child slots with a freshly allocated `Rc::new(Doc::Nil)`
  instead of a `thread_local!` sentinel: `Drop` can run during TLS teardown, where
  touching a `thread_local!` panics and aborts mid-unwind. Matches the no-TLS-in-drop
  CST precedent. (correctness-1)
- `DocAccumulator::doc()` walks the chain by borrow (only `node.doc` is cloned), dropping
  the per-node refcount churn on a hot path. (efficiency-1)
- Test additions: `mutate_text_newline`, the four `extract_boundary_specs` edge cases,
  the `resolve_spacing` "neither trivia nor spacing" panic, `pop_nest` wrong-nesting
  panic, the separator-HardLine-blank-lines branch, the eight multi-level/consecutive-
  spec extraction cases ported from `test_resolve_specs.py`, and deep-drop tests for
  `Nest`/`AfterSpec`/`BeforeSpec`. (test-1..6, test-8)
- `resolve.rs` test module imports `line`/`softline`/`hardline`/`nil` from `doc` instead
  of redefining them. (reuse-2)

Deferred (TODO added):

- `TODO(unparser-join-sep-resolve)` (`resolve.rs` `expand_joins`, + `TODO.md`): a `Join`
  separator is resolved once per gap; resolve it once and reuse. Bounded today because
  separators are restricted to simple docs. (efficiency-2)

Won't-Do (see `dispositions-deep-r1.md` for rationale): test-7 (white-box
`add_trivia_sets_flag` test kept), reuse-1 (`concat`/`concat_rc` split kept).

---

## Increment 4 — `render.rs` (Wadler-Lindig `Renderer`)

Ported `fltk/unparse/renderer.py` to the runtime crate (design §2.1, `render.rs`
bullet): the final pipeline stage that turns a resolved `Doc` into a string.

- `crates/fltk-unparser-core/src/render.rs`: `RendererConfig { indent_width,
  max_width }` (pub fields, `Default` = 4/80, `renderer.py:21`); private `Mode`
  enum (`Flat`/`Break`); `Renderer { config }` with `new(config)` + `Default`;
  `Renderer::render(&self, doc: &Doc) -> String` (`renderer.py:47`) and the
  private `fits` helper (`renderer.py:147`). Queue-based traversal mirrors the
  Python `pop(0)`/`insert(0, …)` via `VecDeque` `pop_front`/`push_front`; the
  Python `break_line`/`append_content` closures become methods on a small
  `Output` struct (Rust can't re-call mutable closures freely). Root wrapped in
  `Group(doc)` for the top-level fit check exactly as Python does.
- `crates/fltk-unparser-core/src/lib.rs`: `mod render;` + `pub use
  render::{Renderer, RendererConfig};`; crate-doc progress note updated.
- 39 `#[test]`s in `render.rs`, ported black-box from `test_renderer.py`: simple
  text/empty/hardline(+blanks), group fit/break, nested groups, nest indentation,
  group-with-nest, soft/nbsp, complex nested, parent-breaks-before-child,
  broken-child-forces-parent-break, group(nest(group)) indent behavior, midline
  width, unbreakable content (text/group/nested), negative & zero remaining width,
  hardline at exhausted width, nil/empty-text at zero width, exact-width boundary,
  text/comment newline width calc, comment re-indentation & empty-line handling,
  mixed text/comment, multiline-comment group break, relative-indent preservation,
  nest-boundary breaks, default-config, and the unresolved-spec panic.
- `cargo test -p fltk-unparser-core --no-default-features` (103 passed) and
  `cargo clippy ... --all-targets` + `cargo fmt --check` all green.

Deviations / notes:
- `fits`/`render` track remaining width and column as `isize` (not `usize`): the
  Python `remaining_width = max_width - current_column` can go *negative*, and
  `_fits` short-circuits to `False` on a negative width — a behavior distinct from
  a remaining width of exactly zero. `usize`/`saturating_sub` would collapse that
  distinction (it matters for groups containing only soft breaks reached past the
  width limit), so the signed type preserves exact parity.
- Text/Comment share one render arm and one `fits` arm: the two Python branches
  are byte-identical (both newline-aware, re-indent each embedded line).
- Width/column use `str::chars().count()` (code points), matching Python `len`.
- Unrenderable variants (`Join`/`AfterSpec`/`BeforeSpec`/`SeparatorSpec`) `panic!`
  in `render` (mirroring the Python `ValueError`) and are skipped in `fits`
  (mirroring `_fits`'s missing `else`); both via explicit arms (no wildcard) so a
  future `Doc` variant forces a compile error.
- Python white-box tests (`test_fits_function_behavior`, `Mode`-direct) not
  ported: `Mode`/`fits` are private; their behavior is covered through `render`
  edge cases (zero/negative width). `RendererConfig`/`Renderer` derive `Copy`.

---

## Increment 5 — `result.rs` (`UnparseResult`)

Ported `fltk/unparse/pyrt.py`'s `UnparseResult` to the runtime crate (design §2.1,
`result.rs` bullet), completing the core crate's public surface.

- `crates/fltk-unparser-core/src/result.rs:18-46`: `UnparseResult { accumulator:
  DocAccumulator, new_pos: usize }` (port of `pyrt.py:16`) with public fields, a
  `new(accumulator, new_pos)` constructor, and a `doc()` convenience returning
  `accumulator.doc()` (port of the Python `doc` property). Module doc notes that
  `pyrt.py`'s `extract_span_text`/`count_span_newlines`/`is_span` helpers have no
  Rust analog (the CST child enum is the discriminant; spans carry their own
  source — design §1/§2.1), so only `UnparseResult` ports here.
- `crates/fltk-unparser-core/src/lib.rs:19,30`: `mod result;` + `pub use
  result::UnparseResult;`.
- 3 `#[test]`s in `result.rs`: field storage, `doc()` convenience, empty-accumulator
  `doc()` → Nil.
- `cargo test -p fltk-unparser-core --no-default-features` (106 passed) and
  `cargo clippy ... --all-targets` + `cargo fmt --check` all green.

This completes design §2.1 (the `fltk-unparser-core` crate): `doc.rs`,
`accumulator.rs`, `resolve.rs`, `render.rs`, `result.rs`, and the `lib.rs`
re-exports are all in place.

Notes:
- `new_pos` is `usize` (Python `int`), matching the positional child index used by
  generated code (design §2.2 threads `pos: usize`).
- `new()` constructor added beyond the design's bare struct spec — trivial, mirrors
  the other core types' `new` constructors and gives generated code one call site.

---

## Increment 6 — `RustUnparserGenerator` scaffold (commit PENDING)

Began design §2.2: stood up the generator file's skeleton — `generate()` now emits a
complete (rule-less) Rust unparser file consisting of the file header + the `Unparser`
struct. One semantic unit: the generator class + memoized `generate` producing a valid
header and struct. Rule-walking bodies (rule entry, alternatives/items, term handling,
trivia, anchors, sub-expressions, suppressed items), the PyO3 wrapper (§2.3), `.pyi`,
CLI/Makefile/LibSpec wiring (§2.5), and the fixture (§2.6) are later increments.

- `fltk/unparse/gsm2unparser_rs.py` (new): `RustUnparserGenerator(grammar,
  formatter_config=None, cst_mod_path="super::cst", source_name=None)` — constructor
  builds an internal `RustCstGenerator(grammar)` (reused for trivia classification +
  static naming helpers in later increments), stores `self._grammar = self._cst.grammar`,
  `self._formatter_config = formatter_config or FormatterConfig()`, `self._cst_mod_path`,
  `self._source_name`, and a `self._generated` memo. `generate() -> str` is idempotent
  (memoized, per `gsm2parser_rs.py:225`).
- `_gen_header()` (`gsm2unparser_rs.py`): emits the file-level doc comment (with the
  escaped `source_name` when present, via the reused `gsm2parser_rs._rust_str_lit`),
  `#![allow(non_snake_case)]`, the design-§2.2 `use fltk_unparser_core::{DocAccumulator,
  Doc, UnparseResult, RendererConfig, Renderer, resolve_spacing_specs};` line, and the
  cst import (direct `use {path};` when it ends in `cst`, else `use {path} as cst;` —
  mirroring `gsm2parser_rs._gen_header`).
- `_gen_struct()` (`gsm2unparser_rs.py`): emits `#[derive(Default)] pub struct Unparser;`
  + `impl Unparser { pub fn new() -> Self { Unparser } }` (unit struct, no `terminals`
  arg — design §2.2).
- `tests/test_rust_unparser_generator.py` (new): 4 smoke tests — header+struct presence,
  escaped `source_name` in header, cst-mod-path direct-vs-aliased import, and `generate()`
  idempotency. All pass; ruff + pyright + ruff-format clean.

Notes:
- `#[derive(Default)]` added on the unit struct so the no-arg `new()` satisfies
  clippy::new_without_default (the parser's `new` takes args, so it does not). Trivial,
  beyond the design's bare struct spec.
- The header `use fltk_unparser_core::{...}` is emitted verbatim per design §2.2 even
  though the rule-less scaffold uses none of those names yet; later rule/PyO3 increments
  consume them. The scaffold file is not compiled this increment (no fixture crate yet —
  §2.6), so the interim unused-import status is moot; compilation is verified once the
  fixture lands.

---

## Review round — deep r2 (commit PENDING)

Dispositions in `dispositions-deep-r2.md`. Fixes applied this round:

- **quality-1 / reuse-1 (shared Rust-codegen helpers).** Design §2.2 said the unparser
  generator "reuses the parser backend's `_rust_str_lit`". To make that cross-module
  reuse a clean, intentional dependency (rather than importing a private symbol) the
  helper was renamed `gsm2parser_rs._rust_str_lit` → `rust_str_lit` (public). The
  parallel CST-import decision (`use {path};` vs `use {path} as cst;`), previously
  copy-pasted into both `_gen_header` methods, was extracted to a shared module-level
  `gsm2parser_rs.cst_module_import(cst_mod_path)` used by both generators. No separate
  shared utility module was created (ADR `2026/06/11-rust-naming-shared` §"Not changed"
  forbids that; `gsm2parser_rs` remains the home). Generator output is byte-identical
  (verified: regenerated `rust_parser_fixture` parser.rs differs only in temp-rustfmt
  config, content unchanged). Callers updated: `gsm2parser_rs.py`, `gsm2unparser_rs.py`,
  `test_gsm2parser_rs.py`, and a prose ref in `gsm2tree_rs.py:152`.
- **quality-2.** `render.rs` `Output::append_content` replaced the two `!text.is_empty()`
  guards with a single early `return` on empty text.
- **test-1/test-2.** `render.rs` tests: added `#[should_panic]` cases for `Doc::Join` and
  `Doc::BeforeSpec` (the spec/join render arm was only exercised via `AfterSpec`), and a
  sibling-group width test (`sibling_groups_break_when_combined_too_wide`).
- **test-3/test-4/test-5.** `tests/test_rust_unparser_generator.py`: assert
  `#![allow(non_snake_case)]` and each imported `fltk_unparser_core` symbol are emitted;
  new `test_generate_source_name_is_escaped` exercises backslash escaping in the header.

---

## Increment 7 — `_doc_to_rust_expr` helper

Continued design §2.2 with the single self-contained `Doc`-to-Rust-expression
helper: `RustUnparserGenerator._doc_to_rust_expr(doc)`. It mirrors
`gsm2unparser.py`'s `_doc_to_combinator_expr` (`:396`) **exactly** — covers `Nil`,
`Nbsp`, `Line`, `SoftLine`, `HardLine`, `Text`, and `Concat`, raising the same
`ValueError("Unknown Doc type: …")` on anything else (`Group`, `Nest`, `Join`,
`Comment`) — but emits Rust `Doc` constructor expressions. This is the
spacing/anchor-emission primitive consumed by later rule-walking increments; it has
no dependency on the rule walk itself, so it ships and tests standalone.

- `fltk/unparse/gsm2unparser_rs.py:23`: import the `combinators` `Doc` variant types
  (`Concat`, `Doc`, `HardLine`, `Line`, `Nbsp`, `Nil`, `SoftLine`, `Text`).
- `fltk/unparse/gsm2unparser_rs.py` `_doc_to_rust_expr`: `Nil`→`Doc::Nil`,
  `Nbsp`→`Doc::Nbsp`, `Line`→`Doc::Line`, `SoftLine`→`Doc::SoftLine`,
  `HardLine`→`Doc::HardLine {{ blank_lines: N }}`, `Text`→`Doc::text("…")`
  (content via `rust_str_lit`, wrapped in literal quotes), `Concat`→
  `Doc::concat(vec![…])` (recursive); else `raise ValueError`. The group/nest/join
  rejection is the load-bearing parity point (design §2.2): the Python backend
  already errors on such separators, so the Rust backend must too.
- `tests/test_rust_unparser_generator.py`: 7 new unit tests — primitives, HardLine
  blank-line counts, Text escaping (backslash + embedded quote), flat + raw-nested
  Concat recursion, and a parametrized Group/Nest/Join/Comment rejection.
- `uv run pytest tests/test_rust_unparser_generator.py` (14 passed); ruff check +
  pyright + ruff format --check all clean.

Notes:
- `rust_str_lit` returns the literal *content* without outer quotes (its docstring,
  `gsm2parser_rs.py:60`), so `_doc_to_rust_expr` wraps it in `"…"` itself — the
  initial draft (relying on it to quote) failed and was corrected.
- The Python reference dispatches the four primitives through a singleton-keyed dict
  (`NIL`/`NBSP`/`LINE`/`SOFTLINE`); the Rust-emitting port uses `isinstance` arms in
  the same precedence order (output is identical — those singletons are the only
  instances of their types). `HardLine` keeps a single `blank_lines`-carrying arm
  rather than the Python's `HARDLINE`/`HARDLINE_BLANK`/`hardline(n)` three-way split,
  because the Rust `Doc::HardLine { blank_lines }` variant is uniform.

---

## Increment 8 — rule-entry + alternative-dispatch backbone

Continued design §2.2 with the rule-walk control-flow backbone: per-rule entry
method + alternative dispatch + per-alternative method scaffold. Item/term/trivia/
item-anchor handling inside the alternatives is deferred to a later increment.

- `fltk/unparse/gsm2unparser_rs.py:24`: import `ItemSelector`, `OperationType`
  from `fltk.unparse.fmt_config` (rule-level anchor queries).
- `fltk/unparse/gsm2unparser_rs.py` `generate()`: appended section 3 — calls the
  new `_gen_rule_methods()`.
- `_class_name(rule_name)`: CamelCase CST struct name via
  `self._cst._py_gen.class_name_for_rule_node` (mirrors `gsm2parser_rs._class_name`).
- `_gen_rule_methods()`: emits an `impl Unparser { … }` block (a *second* impl
  block, separate from the `new()` impl in `_gen_struct`); iterates
  `self._grammar.rules` (trivia-processed), so the synthetic `_trivia` rule yields
  `unparse__trivia` exactly as the Python backend / parser backend do.
- `_gen_rule(rule)`: entry method + one `__alt{N}` scaffold per alternative.
- `_gen_rule_entry(rule, class_name)`: ports `_generate_rule_unparser`
  (`gsm2unparser.py:190`) + the `is_rule_unparser` branch of
  `gen_alternatives_unparser` (`:721`). Emits `pub fn unparse_{rule}(&self, node:
  &cst::{CN}) -> Option<UnparseResult>`: `let acc = DocAccumulator::new();`,
  RULE_START anchor pushes (`push_group`/`push_nest(indent)`/`push_join(<sep>)`,
  rebinding `acc` in config order; JOIN_BEGIN missing-separator → same
  `RuntimeError` as Python `:238`; separator via the existing `_doc_to_rust_expr`),
  then dispatches alternatives from `pos = 0` (clone `acc` for every attempt but the
  last, which moves it), and on the first success applies the RULE_END pop chain
  (`.pop_nest()/.pop_group()/.pop_join()` in config order) rebuilding
  `UnparseResult::new(acc, r.new_pos)` — or `return Some(r)` when there are no
  RULE_END anchors. Falls through to `None`.
- `_gen_alternative_scaffold(rule_name, class_name, alt_idx)`: emits
  `fn unparse_{rule}__alt{N}(&self, node: &cst::{CN}, pos: usize, acc:
  DocAccumulator) -> Option<UnparseResult>` with a placeholder body returning
  `Some(UnparseResult::new(acc, pos))` (the degenerate empty-alternative case);
  the real item walk supersedes it next increment.
- `tests/test_rust_unparser_generator.py`: 6 new generator string-content tests —
  entry signature + `impl Unparser` + `None` fallthrough, alt scaffold signature +
  placeholder body, single-alt move dispatch (no pop chain), multi-alt clone-then-
  move dispatch, trivia rule → `unparse__trivia`, and rule-level group/nest
  RULE_START/RULE_END anchors emitting `push_group`/`push_nest(2)` and the
  `r.accumulator.pop_nest().pop_group()` chain. 20 tests pass; ruff check + ruff
  format --check + pyright clean.

Notes:
- The `__alt{N}` scaffold leaves `node` unused (placeholder body uses only `acc`/
  `pos`); the next increment's item walk consumes it. Like increment 6's unused
  header imports, this is moot until the fixture crate (§2.6) first compiles the
  emitted file — which lands only after the alt bodies are real. No source compiles
  the generated unparser yet.
- Rule methods live in a second `impl Unparser { … }` block rather than reopening
  `_gen_struct`'s impl: minimal disturbance to the existing struct/`new()` emission
  and its tests; multiple inherent impls are valid Rust. Inter-method/inter-impl
  blank-line spacing is left for `cargo fmt` via `make fix` when the fixture lands
  (same deferral as increment 6; the generated unparser is not compiled this
  increment).

---

## Increment 9 — alternative item-walk control-flow backbone

Continued design §2.2 with the alternative item-walk backbone: each `__alt{N}`
body now threads the accumulator/position through one `__alt{N}__item{M}` method
per item, replacing increment 8's single-method `__alt{N}` scaffold. Ports the
required/optional control flow of `gen_alternative_unparser`
(`gsm2unparser.py:1561`, `:1597` ff.) without yet emitting any per-item term
handling — the `__item{M}` methods are pass-through scaffolds this increment.

- `fltk/unparse/gsm2unparser_rs.py` `_gen_rule`: now iterates
  `enumerate(rule.alternatives)` and calls `_gen_alternative(rule_name,
  class_name, alt_idx, alt)` (was `_gen_alternative_scaffold` over a range).
- `_gen_alternative` (replaces `_gen_alternative_scaffold`): emits the `__alt{N}`
  body method plus one `__alt{N}__item{M}` method per item, joined `\n\n`.
- `_gen_alternative_body`: emits `pub`-less `fn unparse_{rule}__alt{N}(&self, node,
  pos, acc) -> Option<UnparseResult>`. Non-empty alternatives open with `let mut
  pos = pos; let mut acc = acc;` then, per item: a required item (non-optional
  quantifier) uses `let r = self.{item_fn}(node, pos, acc)?;` (moves `acc`,
  `?`-fails the alternative when the item is `None`); an optional item uses `if let
  Some(r) = self.{item_fn}(node, pos, acc.clone()) { … }` (clones `acc` so an absent
  optional leaves the prior accumulator intact). Both success paths do `pos =
  r.new_pos; acc = r.accumulator;` (the default `Normal` disposition merge), and the
  body returns `Some(UnparseResult::new(acc, pos))`.
- `_gen_item_method`: emits the `__item{M}` method with the design-§2.2 threaded
  signature and a pass-through body (`Some(UnparseResult::new(acc, pos))`).
- `_gen_rule_methods` docstring updated to describe the item-walk + scaffold items.
- `tests/test_rust_unparser_generator.py`: renamed `test_alternative_scaffold_
  signature` → `test_alternative_and_item_method_signatures` (now asserts both the
  `__alt0` and `__alt0__item0` signatures + scaffold body); added
  `test_required_item_threads_accumulator_with_question_mark` (the `let mut`
  threading + `?` dispatch), `test_optional_item_keeps_prior_accumulator` (`opt :=
  "a"? . "b";` → `if let Some` + `acc.clone()` for the optional, `?` for the
  required). 22 tests pass; ruff check + ruff format --check + pyright clean.

Deviations from the draft scope:
- The draft targeted identifier (rule-reference) term handling as the first
  term-kind vertical slice. That would have made `generate()` *raise* on every
  grammar whose items are not rule references — including the synthetic `_trivia`
  rule (regex / sub-expression items) added whenever a grammar has a WS separator,
  and the existing literal-only test grammars (`greeting := "hello"`,
  `choice := "a" | "b"`). The alt-walk control-flow backbone (placeholder item
  methods) is the genuinely separable, independently-coherent prerequisite: it
  compiles, threads correctly, and never raises, and each term kind then fills in
  `_gen_item_method` without re-touching the walk. Identifier/literal/regex/sub-
  expression handling, quantified loops, suppressed items, trivia/separator
  processing, before/after-item spacing, item-level anchors, and the
  `Omit`/`RenderAs` dispositions are the next increments.

Notes:
- `_gen_alternative_body` keeps a defensive empty-alternative arm (emits a bare
  `Some(UnparseResult::new(acc, pos))`, no `let mut`) mirroring increment 8's
  "degenerate empty-alternative" intent. The FLTK grammar parser rejects empty
  alternatives (`:= | "x"` is a syntax error), so this arm is unreachable through
  the public parse path and is therefore not unit-tested.
- Generated unparser still not compiled (no fixture crate yet, §2.6); per the
  increment-6/8 deferral, inter-method blank-line spacing and clippy/rustfmt
  conformance are handled by `make fix` when the fixture lands. Verified the
  emitted Rust by inspection (required+optional threading, trivia rule generates
  cleanly with scaffold items).

---

## Increment 10 — suppressed-item handling in the item walk

Continued design §2.2 with the first real `__item{M}` term-body emission: the
`SUPPRESS` branch of `gen_item_unparser` (`gsm2unparser.py:460`), i.e. a port of
`_gen_suppressed_quantified_item_body` (`:485`). Suppressed items are absent from the
CST, so they neither read `node` nor advance `pos`; the generator reconstructs the
grammar minimum.

- `fltk/unparse/gsm2unparser_rs.py` `_gen_alternative`: now passes the `gsm.Item` to
  `_gen_item_method` (was index-only) so the item method can route on
  disposition/quantifier.
- `_gen_item_method(..., item)`: new `item` parameter; delegates the body to
  `_gen_item_body`.
- `_gen_item_body(item)`: routing mirror of `gen_item_unparser` (`:460`) — `SUPPRESS`
  first (suppressed items can't be position-extracted), else the deferred pass-through
  scaffold (INCLUDE/INLINE term handling + multiple-quantifier loops are later
  increments).
- `_gen_suppressed_item_body(item)`: port of `:485`. Optional (`min == 0`) → emit
  nothing (`Some(UnparseResult::new(acc, pos))`); required literal →
  `let acc = acc.add_non_trivia(fltk_unparser_core::text("<escaped>")); Some(...)`
  (text escaped via the shared `rust_str_lit`, no pos advance); required
  regex/identifier/sub-expression → `raise RuntimeError` at generation time with the
  same messages as `:514`/`:520`/`:526` (incl. the upstream "lable" typo, preserved
  for parity). This makes the canonical bare-literal grammars (`greeting := "hello"`,
  `choice := "a" | "b"`) emit correct output, since bare literals default to SUPPRESS
  (`bootstrap2gsm.py:70-74`), and satisfies the design §4 "generation raises on
  required-suppressed-regex" test.
- `_gen_rule_methods` / `_gen_alternative` docstrings updated to reflect that SUPPRESS
  items are now emitted (no longer "every `__item{M}` is a pass-through scaffold").
- `tests/test_rust_unparser_generator.py`: updated the stale "pass-through scaffold"
  claim in `test_alternative_and_item_method_signatures`; added 9 tests — unit tests on
  `_gen_suppressed_item_body` (required literal emission, literal escaping, optional →
  nothing, required-regex raise, required-identifier raise) and end-to-end `generate()`
  tests (suppressed literal re-emits text + no `pos + 1`, bare suppressed regex raises,
  explicit `%ident` suppressed identifier raises, INCLUDE labeled literal stays a
  scaffold with no `add_non_trivia`). 36 tests pass; ruff check + ruff format --check +
  pyright clean.

Deviation from the increment-10 draft scope:
- The draft targeted the INCLUDE/INLINE literal branch of `gen_term_unparser`
  (`:1719`). On reading `bootstrap2gsm.py:70-74` it became clear that a bare literal
  (no label, no explicit disposition) defaults to `SUPPRESS`, so the canonical test
  grammars route through `_gen_suppressed_quantified_item_body`, not `gen_term_unparser`
  — the INCLUDE path is only reached by labeled/`$` literals. The suppressed branch is
  therefore both the genuinely self-contained first slice (needs no child enum / label
  enum / span extraction) and the one that makes the simplest grammars produce correct
  output. INCLUDE/INLINE literal handling (with child extraction + validation) is the
  next increment.

Notes:
- Suppressed-item methods leave `node` unused (suppressed items are absent from the
  CST). Like increments 6/8/9, the generated unparser is not compiled this increment
  (no fixture crate yet, §2.6), so the unused-param status is moot until the fixture
  lands; it is the same deferred-conformance bucket as the prior increments. (Unlike
  the scaffold's transient unused `node`, suppressed-item methods will keep `node`
  unused in the final design — the fixture-landing increment will resolve warning
  conformance holistically.)

---

## Increment 11 — INCLUDE/INLINE literal term handling

Continued design §2.2 with the first real single-term `__item{M}` body: the
`Literal` branch of `gen_term_unparser` (`gsm2unparser.py:1719`), reached by
labeled / `$` literals (bare literals default to SUPPRESS, handled in increment
10). One term kind; a literal item now extracts/validates its `Span` child and
re-emits the literal text.

- `fltk/unparse/gsm2unparser_rs.py:22`: import `naming` (for the label-enum
  variant name).
- `_gen_item_method` / `_gen_item_body`: `_gen_item_body` now takes
  `(rule_name, class_name, item)` and adds the `item.quantifier.is_multiple()`
  branch (deferred quantified loop → pass-through scaffold) before the single-term
  path, mirroring `gen_item_unparser`'s routing order (`:460`).
- `_gen_term_body(rule_name, class_name, item)`: port of `gen_term_unparser`
  (`:1669`) dispatch — `Literal` → `_gen_literal_term_body`; identifier/regex/
  nested-alternative terms stay the pass-through scaffold (deferred).
- `_gen_literal_term_body(rule_name, class_name, item)`: port of the `Literal` arm
  (`:1719`). Emits `let acc = acc.add_non_trivia(fltk_unparser_core::text("…"))`
  (text via `rust_str_lit`); INCLUDE runs the span-child validation and advances
  `pos + 1` (`:1740`), other dispositions (INLINE) emit the text with `pos`
  unchanged.
- `_gen_validate_span_child(rule_name, class_name, item)`: port of the `Span` case
  of `_extract_and_validate_nonsequence_child` (`:254`). Emits
  `let children = node.children();` + bounds check (`pos >= children.len()` →
  `return None`), an optional label check (`child_tuple.0 != Some(cst::{CN}Label::
  {Variant})` → `return None`), and — only when the child enum has >1 variant — a
  `match &child_tuple.1 { cst::{CN}Child::Span(_) => {} _ => return None, }`. The
  dynamic `is_span` probe collapses to a static `match` arm (design §1/§2.2).
- `tests/test_rust_unparser_generator.py`: replaced the now-stale
  `test_generate_include_literal_stays_scaffold` (a labeled INCLUDE literal is no
  longer a scaffold); added 5 tests — labeled single-variant (extraction + label
  check + `pos + 1`, no variant match), labeled multi-variant (Span `match` +
  `_ => return None` catch-all), unlabeled `$"x"` single-variant (bounds-only), text
  escaping, and multiple-quantifier literal stays a scaffold. 40 tests pass; ruff
  check + ruff format --check + pyright clean.

Deviations / notes:
- Single-variant guard: the variant `match` (and its catch-all) is emitted only when
  the child enum has >1 variant — mirroring the CST generator's `num_variants > 1`
  guard in `_child_enum_block` (`gsm2tree_rs.py`). For a `Span`-only enum the type is
  statically guaranteed, so an unconditional `match` would be either a vacuous
  single-arm match or, with a catch-all, an `unreachable_patterns` error. Likewise
  the `child_tuple` binding is emitted only when needed (labeled or multi-variant) to
  avoid an unused-variable warning in the unlabeled single-variant case.
- Variant count comes from `self._cst._child_variants_for_rule(rule_name)` (a
  single-underscore method on the owned `RustCstGenerator`); there is no public
  wrapper for it (unlike `class_name_for_rule` / `rule_has_labels`). The identifier/
  regex increments will need the same child-variant info, so a public wrapper on
  `RustCstGenerator` paralleling `rule_has_labels` could be added then if preferred.
- The label-enum variant name uses `naming.snake_to_upper_camel(item.label)` — the
  same public helper `gsm2tree_rs._rust_variant_name` wraps — so it is byte-identical
  to the emitted label enum variants.
- Generated unparser still not compiled (no fixture crate yet, §2.6); per the
  increment-6/8/9/10 deferral, clippy/rustfmt/warning conformance (and the INLINE
  literal's unused-`node` case) are handled by `make fix` when the fixture lands.
  Emitted Rust verified by inspection (single- and multi-variant literal item
  methods).

---

## Increment 12 — identifier (rule-reference) term handling

Continued design §2.2 with the next single term kind in the item walk: the identifier
(rule-reference) branch of `gen_term_unparser` (`gsm2unparser.py:1680`), mirroring
increment 11's literal handling. A bare identifier reference defaults to an INCLUDE
labeled item (`bootstrap2gsm.py:66-74`); the item now extracts/validates its rule-ref
child-enum variant, read-locks the `Shared` child, recursively unparses the referenced
rule, merges, and advances `pos + 1`.

- `fltk/unparse/gsm2unparser_rs.py` `_gen_term_body`: routes `gsm.Identifier` terms to
  the new `_gen_identifier_term_body` (before the `Literal` arm, matching
  `gen_term_unparser`'s dispatch order); regex / nested-alternative terms stay the
  pass-through scaffold (deferred).
- `_gen_identifier_term_body(rule_name, class_name, item)`: port of the `Identifier`
  arm (`:1680`). Emits the shared bounds/label prelude (always `need_tuple=True` — the
  inner `Shared` is read from `child_tuple.1`), then `let shared = match &child_tuple.1
  { cst::{CN}Child::{RefClass}(shared) => shared, _ => return None };` (the catch-all
  emitted only when the child enum has >1 variant, mirroring the span path / CST
  generator's `num_variants > 1` guard), `let guard = shared.read();`,
  `let child_result = self.unparse_{ref_rule}(&guard)?;`,
  `let acc = acc.add_accumulator(&child_result.accumulator);`, and
  `Some(UnparseResult::new(acc, pos + 1))`. `{RefClass}` is the referenced rule's CST
  struct name (`self._class_name(item.term.value)`); the child-enum variant for a
  rule-ref is named by that class.
- `_gen_child_prelude(class_name, item, *, need_tuple)` (new): extracted the shared
  bounds/label prelude of the child extraction (`children` bind + `pos >= len` bounds
  check + optional `child_tuple` bind + optional label check) so the span and identifier
  paths reuse it. `_gen_validate_span_child` now calls it (then appends the `Span` match)
  — its emitted output is byte-identical to increment 11.
- Updated the deferred-term docstrings in `_gen_rule_methods`, `_gen_alternative`,
  `_gen_item_method`, `_gen_item_body`, and `_gen_term_body` to move identifier from the
  deferred list into the implemented set.
- `tests/test_rust_unparser_generator.py`: 3 new tests — single-variant identifier
  (prelude + bind + no catch-all + read/recurse/merge/advance), multi-variant identifier
  (`bar:other` in `r := foo:"x" . bar:other` → `_ => return None` catch-all, the
  union-label mismatch path), and a `_gen_identifier_term_body` unit test confirming the
  no-catch-all single-variant shape. 43 tests pass; ruff check + ruff format --check +
  pyright clean.

Deviations / notes:
- Design §2.2 pseudocode merges with `acc.add_accumulator(child_result.accumulator)`; the
  core's actual signature is `add_accumulator(&self, other: &DocAccumulator)`
  (`accumulator.rs:99`), so the emitted call passes `&child_result.accumulator`. Behavior
  matches the Python `add_accumulator` call.
- The `_gen_child_prelude` extraction is a reuse refactor of increment 11's
  `_gen_validate_span_child` (the span output is unchanged); it makes the span/identifier
  child-validation share their common bounds/label prelude rather than duplicating it.
- Two-step match→`shared`, then `let guard = shared.read();`, exactly as design §2.2
  words it (rather than reading inside the match arm), keeping the single-variant
  exhaustive-match case clean.
- Generated unparser still not compiled (no fixture crate yet, §2.6); per the
  increment-6..11 deferral, clippy/rustfmt/warning conformance (and the INLINE literal's
  unused-`node` case) are handled by `make fix` when the fixture lands. Emitted Rust
  verified by inspection (single- and multi-variant identifier item methods, incl. the
  read-lock + recursive `unparse_{ref}` call + accumulator merge).

---

## Increment 13 — regex term handling

Continued design §2.2 with the next single term kind in the item walk: the regex
branch of `gen_term_unparser` (`gsm2unparser.py:1750`), mirroring increments 11
(literal) and 12 (identifier). A regex term binds its captured `Span` child, reads
the text via `span.text()`, and re-emits it as `Doc::text` — the captured source,
not a fixed string. This is the term kind the synthetic `_trivia` rule's `content`
item uses, so implementing it makes that rule emit a real body too (see test note
below).

- `fltk/unparse/gsm2unparser_rs.py` `_gen_term_body`: routes `gsm.Regex` terms to the
  new `_gen_regex_term_body` (after the `Literal` arm, matching `gen_term_unparser`'s
  dispatch order); nested-alternative terms stay the pass-through scaffold (deferred).
- `_gen_regex_term_body(rule_name, class_name, item)`: port of the `Regex` arm
  (`:1750`). Emits the shared bounds/label prelude via `_gen_child_prelude`
  (`need_tuple=True` — the captured `Span` is read from `child_tuple.1`), then
  `let span = match &child_tuple.1 { cst::{CN}Child::Span(span) => span, [_ => return
  None,] };` (catch-all only when the child enum has >1 variant, mirroring the
  span/identifier paths' `num_variants > 1` guard), `let text = span.text()?;`
  (the `?` is the design-§3 sourceless-span → `return None` path — no `terminals`
  fallback in the Rust CST), and `let acc = acc.add_non_trivia(fltk_unparser_core::
  text(text));`. Position advances `pos + 1` only for INCLUDE (matching `:1781`); other
  dispositions read the text without consuming a CST position. A non-`Regex` routing
  guard raises (explicit `RuntimeError`, not assert) so a misroute names its rule
  rather than silently emitting `span.text()` for a literal/identifier.
- Updated the deferred-term docstrings in `_gen_rule_methods`, `_gen_alternative`,
  `_gen_item_method`, `_gen_item_body`, and `_gen_term_body` to move regex from the
  deferred list into the implemented set.
- `tests/test_rust_unparser_generator.py`: replaced the now-stale
  `test_single_regex_term_stays_scaffold` with a regex section — single-variant
  (`r := foo:/[0-9]+/;`: prelude + bind + no catch-all + read/advance), multi-variant
  (`r := foo:other . bar:/[0-9]+/;`: `_ => return None` catch-all), unlabeled
  (`r := $/[0-9]+/;`: bounds + bind, no label check), a `_gen_regex_term_body` unit
  test (no-catch-all single-variant shape), an INLINE-disposition unit test (reads
  span, no `pos + 1`), and a non-Regex routing-guard raise. 54 tests pass; ruff check
  + ruff format --check + pyright clean.

Deviations / notes:
- **Trivia-rule output changed → 3 pre-existing tests rescoped.** The synthetic
  `_trivia` rule's `content` term is a regex, so implementing regex made
  `unparse__trivia` emit a real regex body (`node.children()`, `child_tuple.0 !=
  Some(...)`, `span.text()`, `pos + 1`) instead of the prior pass-through scaffold.
  Three pre-existing tests (`test_generate_suppressed_literal_reemits_text`,
  `test_include_unlabeled_literal_single_variant_emits_bounds_only`,
  `test_multiple_quantifier_literal_stays_scaffold`) used file-global `not in src`
  negatives that had silently relied on regex-being-a-scaffold to keep the trivia rule
  empty; they now caught the trivia body. Fixed by adding a `_method_body(src, fn_name)`
  test helper that extracts a single method's source and scoping each over-broad
  negative to the rule under test. This preserves each test's intent (correctly scoped)
  rather than relying on an unrelated rule staying unimplemented.
- Generated unparser still not compiled (no fixture crate yet, §2.6); per the
  increment-6..12 deferral, clippy/rustfmt/warning conformance (and the INLINE term's
  unused-`node` cases) are handled by `make fix` when the fixture lands. Emitted Rust
  verified by inspection (single-/multi-variant regex item methods + the trivia rule's
  regex body).

---

## Increment 14 — nested-alternatives / sub-expression term handling

Completed design §2.2's last remaining single-term kind in `_gen_term_body`: the
nested-alternatives / sub-expression term (design §2.2 "Nested alternatives /
sub-expression", `gsm2unparser.py:1791`), parallel to increments 11 (literal), 12
(identifier), 13 (regex). A sub-expression term is a `Sequence[Items]` whose children
are inlined into the *enclosing* rule's CST node (label/child enums flatten into the
parent — confirmed via `RustCstGenerator` for `r := (a:"x" | b:"y")`: `RLabel = {A,B}`).
So the item delegates to a generated `__alts` dispatch that walks the same
`cst::{ParentClass}` node from the passed `pos`, mirroring the parser backend's
`_gen_subexpr_term` and the Python unparser's nested
`gen_alternatives_unparser(..., is_rule_unparser=False)`.

Enabling refactor (method-name prefix threading): the per-alternative/-item generators
hard-coded `unparse_{rule}__alt{N}__item{M}` from `(rule_name, alt_idx, item_idx)`.
Nested sub-expressions need names like `..._item{M}__alts__alt{K}__item{L}`, so the
naming is now prefix-driven and the alternative/item generators return flat
`list[str]` method-block lists (so a sub-expression item can append its nested method
tree as siblings). Output for non-sub-expression grammars is byte-identical (the
existing 50 tests pass unchanged).

- `fltk/unparse/gsm2unparser_rs.py:22`: `from collections.abc import Sequence` (for the
  nested-alternatives type hint).
- `_gen_rule`: builds `prefix = f"unparse_{rule.name}"` and `extend`s with the (now
  list-returning) `_gen_alternative(prefix, rule_name, class_name, alt_idx, alt)`.
- `_gen_alternative(prefix, rule_name, class_name, alt_idx, alt) -> list[str]`: returns
  the `{prefix}__alt{N}` body block + each item method's blocks (flat list).
- `_gen_alternative_body`: first param `rule_name` → `prefix`; method/item-fn names now
  `{prefix}__alt{N}` / `{prefix}__alt{N}__item{M}`.
- `_gen_item_method(prefix, rule_name, class_name, alt_idx, item_idx, item) -> list[str]`:
  computes `item_prefix = f"{prefix}__alt{alt_idx}__item{item_idx}"`, emits the item
  method, and — when `_item_routes_to_subexpr(item)` — appends `_gen_subexpr_methods`'
  nested `__alts` tree.
- `_item_routes_to_subexpr(item)` (new): the single routing predicate
  (`disposition != SUPPRESS and not quantifier.is_multiple() and isinstance(term, list|tuple)`),
  keeping body-routing (`_gen_term_body`) and sibling-emission (`_gen_item_method`) from
  drifting.
- `_gen_item_body` / `_gen_term_body`: thread `item_prefix`; `_gen_term_body` now routes
  `list|tuple` terms to `_gen_subexpr_term_body` and raises `ValueError` on any other
  (unknown) term kind, mirroring the Python `gen_term_unparser` `else` (`:1820`) — the
  prior subexpr pass-through scaffold is gone.
- `_gen_subexpr_term_body(item_prefix)` (new): body is just
  `self.{item_prefix}__alts(node, pos, acc)` (label/disposition intentionally ignored —
  the Python `list` branch ignores both; inner items carry their own labels).
- `_gen_subexpr_methods(item_prefix, rule_name, class_name, alternatives)` (new): emits
  the `{item_prefix}__alts` dispatch + recurses via `_gen_alternative` over the nested
  alternatives (so deeper sub-expressions recurse).
- `_gen_alts_dispatch(alts_prefix, class_name, n_alts)` (new): the nested dispatch —
  tries each `{alts_prefix}__alt{K}` from the *passed* `pos`, no rule-level anchors,
  clone-then-move `acc`.
- `tests/test_rust_unparser_generator.py`: updated `_gen_alternative_body` direct-call to
  pass a `prefix` (`"unparse_r"`); added 6 sub-expression tests — single-alt delegation +
  `__alts` dispatch shape, multi-alt clone-then-move + inner labeled-literal handling
  (labels resolve against the enclosing `RLabel`), doubly-nested recursion, the
  `_gen_subexpr_term_body` unit body, a parametrized `_item_routes_to_subexpr` table, and
  a "plain rule emits no `__alts`" negative. 64 tests pass; ruff check + ruff format
  --check + pyright clean.

Notes / deviations:
- **Labeled sub-expression terms are unsupported by the CST layer** — `gsm2tree.py:639`
  asserts a labeled item's term is not a `Sequence`. This is a pre-existing limitation
  (the Python backend hits the same assertion at CST generation), not introduced here;
  the tests use unlabeled sub-expressions (`r := ("x" . "y")`, `r := (a:"x" | b:"y")`),
  the supported form. The Rust unparser, like the Python one, never reaches its
  sub-expression code for a labeled sub-expression because CST/model construction fails
  first.
- Sub-expression term kind uses `isinstance(term, list | tuple)` (the parser backend's
  `_gen_consume_term` convention + GSM `Term = ... | Sequence[Items]`), broader than the
  Python unparser's `isinstance(term, list)`; the design directs "same as the parser
  backend's sub-expression handling" (design §2.2), and `tuple` is type-valid per the GSM.
- `_gen_term_body` now *raises* on an unrecognized term kind (e.g. `Invocation`) instead
  of the prior silent pass-through scaffold — faithful to the Python `gen_term_unparser`
  `else` and avoids silently mis-generating an unsupported term.
- Trivia/separator processing, before/after-item spacing, item-level anchors, quantified
  loops, and the `Omit`/`RenderAs` dispositions remain deferred (nested alternatives get
  the same deferred treatment as top-level, since they reuse `_gen_alternative_body`).
- Generated unparser still not compiled (no fixture crate yet, §2.6); per the
  increment-6..13 deferral, clippy/rustfmt/warning conformance is handled by `make fix`
  when the fixture lands. Emitted Rust verified by inspection (single-/multi-alt and
  doubly-nested sub-expression method trees).

---

## Increment 15 — before/after-item spacing

Continued design §2.2 with per-item spacing: the `__alt{N}` body now wraps each item
with its configured before/after spacing, porting the Python
`gen_alternative_unparser`'s `_gen_before_item_spacing` / `_gen_after_item_spacing`
emission (`gsm2unparser.py:1605`/`:1637`/`:1654`). Before- and after-spacing are the
symmetric halves of one feature (same `get_*_spacing` → wrap-in-spec → `add_non_trivia`
machinery), one increment — the precedent being increment 8's rule-level START+END
anchors landing together.

- `crates/fltk-unparser-core/src/doc.rs`: added `before_spec(spacing: Doc) -> Doc` and
  `after_spec(spacing: Doc) -> Doc` constructors (port of the Python unparser's
  `_create_before_spec`/`_create_after_spec`) wrapping the spacing in the existing
  `Doc::BeforeSpec`/`Doc::AfterSpec` variants (`Rc`-wrapping mirrors `group`/`nest`).
  No new variant — only constructors. +1 `#[test]` (`before_after_spec_wrap_spacing`);
  110 crate tests pass, clippy + fmt clean.
- `crates/fltk-unparser-core/src/lib.rs:22-25`: re-export `after_spec`, `before_spec`.
- `fltk/unparse/gsm2unparser_rs.py` `_gen_alternative_body`: gained a `rule_name`
  parameter (to query the `FormatterConfig`); before each item emits the before-spacing
  line unconditionally (8-space indent, ahead of the call — matching the Python
  `accumulator_var` threading where the `BeforeSpec` persists even when an optional item
  is absent), and after the success merge emits the after-spacing line — at the 8-space
  indent for a required item, and at the 12-space indent *inside* the `if let Some` block
  for an optional item (so after-spacing is added only on the matched path, per Python
  `:1654`).
- `_item_spacing_lines(rule_name, item, position, indent)` (new): queries
  `get_before_spacing`/`get_after_spacing`, wraps the result via `_doc_to_rust_expr` +
  the `fltk_unparser_core::before_spec`/`after_spec` constructor, and returns the single
  `acc = acc.add_non_trivia(<spec>);` line (or `[]` when no spacing is configured — the
  default-config case, so all prior tests/grammars emit unchanged output).
- `_gen_alternative` updated to pass `rule_name` to `_gen_alternative_body`.
- `tests/test_rust_unparser_generator.py`: updated the `_gen_alternative_body`
  direct-call (new `rule_name` arg) and added 7 tests — before/after spacing emission +
  placement on a required item, optional-item before(outer)/after(inner-block)
  placement, literal-selector before-spacing, default-config emits no spec (negative),
  and two `_item_spacing_lines` unit tests (empty without config, wrapped-line with).
  71 generator tests pass; ruff check + ruff format + pyright clean.

Notes / deviations:
- Spacing is emitted in the alternative body (around the item call), not inside the
  `__item{M}` method — matching the Python backend, where spacing lives in
  `gen_alternative_unparser` and the term work lives in the item/term methods. This
  placement is load-bearing for optional items: the before-spec must persist in `acc`
  even when the optional item's method returns `None` (the current optional pattern
  passes `acc.clone()`, so a before-spec added *inside* the item method would be lost on
  a no-match — diverging from Python's leak behavior).
- Spacing is queried/emitted for *every* item including gsm-`SUPPRESS` ones, matching
  Python (the alt-level spacing in `gen_alternative_unparser` is gated on the *formatter*
  disposition Omit/RenderAs — deferred — not on the grammar SUPPRESS/INCLUDE disposition).
- `_doc_to_rust_expr` is reused unchanged; before/after spacing is always a primitive
  (`_spacing_cst_to_doc` only yields Nil/Nbsp/Line/SoftLine/HardLine), but routing
  through it preserves the Python backend's Group/Nest/Join rejection (its
  `_create_*_spec` runs the spacing through `_doc_to_combinator_expr`).
- `Omit`/`RenderAs` dispositions are still deferred, so before-spacing's Python guard
  (`not isinstance(item_disposition, Omit | RenderAs)`) is currently vacuously true (the
  Rust backend treats all items as `Normal`); the gate lands with the disposition
  increment. Item-level anchor push/pop, quantified loops (`__inner`), trivia/separator
  processing, PyO3 wrapper (§2.3) + intermediate-Doc exposure + `.pyi` (OQ-2/OQ-3),
  CLI/Makefile/LibSpec wiring (§2.5), fixture (§2.6), and parity tests (§4) remain
  deferred.
- Generated unparser still not compiled (no fixture crate yet, §2.6); per the
  increment-6..14 deferral, clippy/rustfmt/warning conformance is handled by `make fix`
  when the fixture lands. The new core constructors *are* compiled and tested.

---

## Increment 16 — item-level anchor push/pop operations

Continued design §2.2 with the one remaining `_gen_alternative_body` per-item
emission: item-level anchor operations (design §2.2 "Item-level anchor operations",
porting `gsm2unparser.py` `_gen_anchor_operations_before_item` `:1472` /
`_gen_anchor_operations_after_item` `:1517`, invoked from `gen_alternative_unparser`
`:1602`/`:1656`). For label-/literal-selected anchors, the alternative body now
brackets each item with accumulator push/pop state transitions:
GROUP_BEGIN/NEST_BEGIN/JOIN_BEGIN → `acc = acc.push_group()` /
`acc.push_nest(indent)` / `acc.push_join(<sep>)` ahead of the item, and
GROUP_END/NEST_END/JOIN_END → `acc = acc.pop_group()` / `acc.pop_nest()` /
`acc.pop_join()` after it. This is the path that implements item-level
`group from label:X to label:Y`, `nest from … to …`, `join from … to …` (vs
increment 8's rule-level RULE_START/RULE_END anchors). One semantic unit (before +
after anchors are symmetric halves); core `push_*`/`pop_*` already exist (increment
2), so generator + tests only — no core crate changes.

- `fltk/unparse/gsm2unparser_rs.py:26`: import `AnchorConfig` (for the
  `_item_anchor_config` return annotation).
- `_gen_alternative_body`: before each item now emits `_item_anchor_lines(rule_name,
  item, "before", "        ")` *ahead of* the before-spacing line (anchors precede
  spacing, matching the Python `:1602`→`:1605` order), and *after* the item block
  (outside the optional `if let Some`) emits `_item_anchor_lines(..., "after",
  "        ")` — unconditional at the 8-space indent, matching the Python after-anchor's
  `method.block` scope (`:1656`; applied even when an optional item is absent, unlike
  after-*spacing* which is inside the matched block).
- `_item_anchor_config(rule_name, item, position)` (new): the anchor-config lookup,
  preserving the before/after selector asymmetry — `before` falls back from a missing
  LABEL anchor to a LITERAL anchor (`:1483`), `after` consults LABEL-only for a
  labeled item and LITERAL only for an unlabeled literal (`:1525` `elif`).
- `_item_anchor_lines(rule_name, item, position, indent)` (new): emits the
  `acc = acc.push_*()` / `acc = acc.pop_*()` reassignments (no `let` rebind — mutates
  the body's `let mut acc`, unlike the rule-level shadow-rebind / pop-chain in
  `_gen_rule_entry`). SPACING ops are skipped (handled by `_item_spacing_lines`).
  JOIN_BEGIN routes its separator through the existing `_doc_to_rust_expr` (inheriting
  the Group/Nest/Join rejection) and raises on a missing separator (same message as
  the rule-level path); an unsupported separator re-raises with rule/position/item
  context.
- `tests/test_rust_unparser_generator.py`: added an item-level-anchor section (13
  tests) — group push/pop placement (push before item, pop after merge), nest with
  indent + indent-default-to-1, join push/pop + missing-separator raise +
  unsupported-separator context, literal-selected anchor, before-anchor-precedes-
  before-spacing ordering, optional-item after-anchor-is-unconditional (outer indent,
  not inner-block), default-config emits no `acc = acc.push_*`, `_item_anchor_lines`
  SPACING-skip + empty-without-config units, and the before/after selector-asymmetry
  unit. 86 generator tests pass; ruff check + ruff format --check + pyright clean.

Notes / deviations:
- The op→Rust mapping is *not* shared with `_gen_rule_entry`'s rule-level anchors: the
  rule-level START uses `let acc = acc.push_*()` (shadow rebind) and END appends a
  `.pop_*()` chain to `r.accumulator`, whereas item-level both-directions reassign the
  `let mut acc` and handle the full op set in each direction — structurally distinct
  emission shapes, so a shared helper would be awkward. The shared piece (JOIN_BEGIN
  separator + missing/unsupported error handling) follows the same pattern as
  `_gen_rule_entry` / `_item_spacing_lines` but is inlined.
- Anchors are emitted for *every* item including gsm-`SUPPRESS` ones, matching Python
  (the Python before/after-anchor calls at `:1602`/`:1656` are unconditional, not gated
  on disposition — same as the before/after-spacing emission in increment 15).
- Generated unparser still not compiled (no fixture crate yet, §2.6); per the
  increment-6..15 deferral, clippy/rustfmt/warning conformance is handled by `make fix`
  when the fixture lands. Emitted Rust verified by inspection (push/pop placement around
  required + optional items, the before-anchor/before-spacing order, and the
  unconditional optional after-anchor). Remaining design work: quantified loops
  (`__inner`), trivia/separator processing, `Omit`/`RenderAs` dispositions, PyO3
  wrapper + intermediate-Doc exposure + `.pyi` (§2.3/OQ-2/OQ-3), CLI/Makefile/LibSpec
  wiring (§2.5), fixture (§2.6), parity tests (§4).

---

## Increment 17 — quantified-item loop (`__inner`)

Continued design §2.2 with the one remaining single-term routing case in the item
walk: the multiple-quantifier (`+`/`*`) loop. `_gen_item_body` previously routed
`item.quantifier.is_multiple()` to a pass-through scaffold (increment 11); the item
body now loops over a per-occurrence `__inner` method, porting
`_gen_quantified_item_body` (`gsm2unparser.py:533`). The loop and its `__inner` body
are interdependent halves of one change.

- `fltk/unparse/gsm2unparser_rs.py` `_gen_item_body`: the `is_multiple()` branch now
  calls `_gen_quantified_loop_body` (was a pass-through return).
- `_gen_quantified_loop_body(item_prefix, item)` (new): port of
  `_gen_quantified_item_body` (`:533`). Emits `let mut current_pos = pos; let mut acc =
  acc;` then `while current_pos < node.children().len() { let Some(r) =
  self.{item_prefix}__inner(node, current_pos, acc.clone()) else { break; }; acc =
  r.accumulator; current_pos = r.new_pos; … }` and `Some(UnparseResult::new(acc,
  current_pos))`. `acc.clone()` per attempt (like the optional-item pattern) keeps the
  accumulator at its last-successful value when an occurrence fails, mirroring the
  Python `accumulator` staying unchanged on a `None` inner result. For `+`
  (`quantifier.min() == gsm.Arity.ONE`) it adds `let mut match_count = 0usize;`,
  `match_count += 1;`, and `if match_count == 0 { return None; }` (the Python
  minimum-occurrence check, `:611`); `*` (min ZERO) omits all three.
- `_gen_inner_methods(item_prefix, rule_name, class_name, item)` (new): emits the
  `{item_prefix}__inner` per-occurrence method — signature is the standard threaded
  `(&self, node, pos, acc) -> Option<UnparseResult>`, body is `_gen_term_body` over the
  same `item` (the inner handles one occurrence; the quantifier is irrelevant to it,
  matching the Python `gen_term_unparser((*path, "inner"), item, …)` at `:546`). When
  the term is a sub-expression it appends the nested `__alts` tree via
  `_gen_subexpr_methods(inner_prefix, …)`, exactly as `_gen_item_method` does for a
  non-quantified sub-expression — so a quantified sub-expression's `__alts` tree hangs
  off `__inner`, not the item method.
- `_item_routes_to_quantified_loop(item)` (new): single routing predicate
  (`disposition != SUPPRESS and quantifier.is_multiple()`), mirroring
  `_item_routes_to_subexpr`. `SUPPRESS` is excluded because the Python
  `gen_item_unparser` checks `SUPPRESS` before the multiple-quantifier branch (`:462`),
  so a suppressed quantified item is reconstructed as the grammar minimum by
  `_gen_suppressed_item_body`, never as a loop.
- `_gen_item_method`: now emits the `__inner` sibling(s) for a quantified-loop item
  (the new branch precedes the sub-expression branch — a quantified sub-expression's
  nested methods hang off `__inner`).
- Docstrings updated (`_gen_rule_methods`, `_gen_item_method`, `_gen_item_body`,
  `_item_routes_to_subexpr`) to move quantified loops from the deferred/pass-through
  set into the implemented set.
- `tests/test_rust_unparser_generator.py`: removed the now-obsolete
  `test_multiple_quantifier_literal_stays_scaffold` (a quantified literal is no longer a
  scaffold) and added a quantified-loop section (10 tests): `+` loop + min check, `*`
  loop omits the counter/check, `__inner` carries the single-occurrence literal body,
  quantified identifier inner recurses, quantified sub-expression inner delegates to a
  nested `__alts` tree, a `_gen_quantified_loop_body` `+`-vs-`*` unit, and a parametrized
  `_item_routes_to_quantified_loop` table. 96 generator tests pass; ruff check + ruff
  format --check + pyright clean.

Notes / deviations:
- Loop failure uses a let-else `else { break; }` (cleaner than the optional item's
  `if let Some`), but the same `acc.clone()`-per-attempt accumulator discipline.
- Generated unparser still not compiled (no fixture crate yet, §2.6); per the
  increment-6..16 deferral, clippy/rustfmt/warning conformance is handled by `make fix`
  when the fixture lands. Emitted Rust verified by generation+inspection for `+`, `*`,
  quantified identifier, and quantified sub-expression grammars. Remaining design work:
  trivia/separator processing, `Omit`/`RenderAs` dispositions, PyO3 wrapper +
  intermediate-Doc exposure + `.pyi` (§2.3/OQ-2/OQ-3), CLI/Makefile/LibSpec wiring
  (§2.5), fixture (§2.6), parity tests (§4).

---

## Increment 18 — item-level formatter dispositions (`Omit` / `RenderAs`)

Wired the last per-item generation-time `FormatterConfig` query into the item walk:
`get_item_disposition` (design §2.2 "Anchors / spacing / dispositions"). The
alternative body previously treated every item as `Normal`; it now honors `Omit` and
`RenderAs`, porting the Python `gen_alternative_unparser` disposition branch
(`gsm2unparser.py:1600` ff., `:1604` before-spacing gate, `:1628`/`:1633`/`:1644`
success-path branches). Generator + tests only; no core crate changes (the `Doc`
machinery already exists).

- `fltk/unparse/gsm2unparser_rs.py:29`: import `Normal`, `Omit`, `RenderAs` from
  `fltk.unparse.fmt_config`.
- `_gen_alternative_body` per-item loop: queries `get_item_disposition(rule_name, item)`
  once per item; `is_normal = isinstance(disposition, Normal)`. Before-spacing is now
  emitted only for `Normal` items (the Python `not isinstance(item_disposition, Omit |
  RenderAs)` gate, `:1604`); item-level anchors stay unconditional. Required items: a
  `Normal` item moves `acc` into the call and reassigns it from the result (unchanged);
  an `Omit`/`RenderAs` item passes `acc.clone()` so the prior `acc` survives the call
  (its produced `Doc` is discarded). `pos = r.new_pos;` runs for every disposition on
  the success path.
- `_item_disposition_success_lines(rule_name, item, item_disposition, indent)` (new):
  the success-path accumulator handling — `Normal` → `acc = r.accumulator;` + after-item
  spacing; `RenderAs` → `acc = acc.add_non_trivia(<spacing>);` (item output discarded,
  spacing via the existing `_doc_to_rust_expr`, re-raising with rule/item context on a
  rejected Group/Nest/Join/Comment Doc — same pattern as `_item_spacing_lines` /
  JOIN_BEGIN); `Omit` → `[]`. Used by both the required and optional paths (optional
  passes the 12-space inner indent).
- `_gen_alternative_body` docstring updated to describe the disposition handling and the
  move-vs-clone rule.
- `tests/test_rust_unparser_generator.py`: import `NORMAL`/`OMIT`/`RenderAs`; added an
  item-disposition section (8 tests) — Omit/RenderAs on required + optional items
  (clone-in + pos advance + discard/substitute, no `acc = r.accumulator;`), Omit skips
  before-spacing (SPACING op + Omit on one anchor), RenderAs unsupported-spacing context
  raise, Omit applied to a default-suppressed bare literal (the canonical `omit` use:
  only the Normal sibling merges), and a `_item_disposition_success_lines` unit. 104
  generator tests pass; ruff check + ruff format --check + pyright clean.

Notes / deviations:
- Disposition is queried and applied uniformly for *every* item, including gsm-`SUPPRESS`
  ones, matching Python (`get_item_disposition` is called at `:1600` for all items). A
  suppressed item's method reconstructs the grammar minimum into its accumulator; the
  disposition then merges it (`Normal`), discards it (`Omit`), or substitutes
  (`RenderAs`) — so `omit "literal"` drops a default-suppressed token from the output,
  exercised by `test_omit_applies_to_suppressed_literal`.
- The `RenderAs` `_doc_to_rust_expr` call is wrapped with rule/item error context
  (the Python backend does not wrap its `_doc_to_combinator_expr` call). This follows
  the established Rust-backend convention (`_item_spacing_lines`, rule/item JOIN_BEGIN);
  the `.fltkfmt` path only ever produces primitive render-as spacing
  (`_spacing_cst_to_doc`), so the wrap fires only on a hand-built `FormatterConfig`.
- Default config is byte-identical: with no dispositions configured `get_item_disposition`
  returns `Normal` for every item, so before-spacing, the moved-`acc` call, and
  `acc = r.accumulator;` + after-spacing all emit exactly as before (the 96 pre-existing
  generator tests pass unchanged).
- Generated unparser still not compiled (no fixture crate yet, §2.6); per the
  increment-6..17 deferral, clippy/rustfmt/warning conformance is handled by `make fix`
  when the fixture lands. One new warning bucket: an alternative whose every item is
  `Omit` (and that has no acc-mutating anchors) would leave `let mut acc` never
  reassigned (`unused_mut`) — a degenerate config, resolved holistically in the
  fixture-landing increment with the other deferred warnings. Remaining design work:
  trivia/separator processing (§2.2), PyO3 wrapper + intermediate-Doc exposure + `.pyi`
  (§2.3/OQ-2/OQ-3), CLI/Makefile/LibSpec wiring (§2.5), fixture (§2.6), parity tests
  (§4).

---

## Increment 19 — trivia-rule branch of `_gen_trivia_processing`

Continued design §2.2 "Trivia processing" (`gsm2unparser.py:_gen_trivia_processing`,
`:1084`). That method has **two** branches; this increment ports the **trivia-rule**
branch (`:1103`-`:1263`): a trivia rule consumes the whitespace its own WS separators
matched (captured as unlabeled `Span` children), counts newlines, and emits the
appropriate `SeparatorSpec`. The **non-trivia-rule** branch (`:1265`-`:1427`:
`Trivia`-child lookup, `unparse__trivia` call, `SeparatorSpec` preservation) plus the
`_has_preservable_trivia` / `_count_newlines_in_trivia` utilities are deferred to the
next increment — they depend on this branch's `unparse__trivia` being correct first.
The two branches are independent emissions in one Python method, so they split cleanly.

- `crates/fltk-unparser-core/src/doc.rs`: added `separator_spec(spacing: Option<Doc>,
  preserved_trivia: Option<Doc>, required: bool) -> Doc` constructor (port of the Python
  unparser's `_create_separator_spec`, `:446`; both optional fields `Rc`-wrapped, mirroring
  `before_spec`/`after_spec`). +1 `#[test]` (`separator_spec_wraps_optional_fields`).
  111 crate tests pass; clippy + `cargo fmt --check` clean.
- `crates/fltk-unparser-core/src/lib.rs:24`: re-export `separator_spec`.
- `fltk/unparse/gsm2unparser_rs.py` `_gen_alternative_body`: now threads the alternative's
  `initial_sep` (before the first item, Python `:1588`) and each item's `sep_after[item_idx]`
  (after the after-anchor lines, Python `:1658`, guarded by `item_idx < len(alt.sep_after)`)
  through the new `_gen_trivia_processing`.
- `_gen_trivia_processing(rule_name, class_name, separator, indent)` (new): dispatch port of
  `_gen_trivia_processing` (`:1084`) — `NO_WS` → `[]` (Python early return `:1098`); a WS
  separator on a trivia rule (`self._grammar.identifiers.get(rule_name).is_trivia_rule`) →
  the trivia-rule branch; a WS separator on a non-trivia rule → `[]` (deferred branch).
- `_gen_trivia_rule_processing(rule_name, class_name, separator, indent)` (new): the
  trivia-rule branch. Emits the bounds check; `if let (None, cst::{CN}Child::Span(span))`
  (the unlabeled-whitespace-Span guard, Python `:1140` `is_unlabeled and is_span`); `pos += 1`;
  `let newline_count = span.text().map(|t| t.matches('\n').count()).unwrap_or(0);` (the
  design-§2.2 inline form of `_count_newlines`, no `terminals` fallback). `preserve_blanks > 0`
  emits the `>= 2` (blank-line `HardLine{preserve_blanks}`) / `>= 1` (plain `HardLine`) /
  default three-way; `preserve_blanks == 0` emits `>= 1` / default. The not-whitespace and
  out-of-bounds arms `return None` for WS_REQUIRED, emit default spacing (not-whitespace) or
  nothing (out-of-bounds) for WS_ALLOWED — matching the Python `if_in_bounds` having an
  `orelse` only for WS_REQUIRED.
- `_add_separator_spec_lines(...)` / `_add_default_separator_spec_lines(...)` (new): ports of
  `_add_separator_spec` (`:1429`) and `_add_default_separator_spec` (`:1447`). Spacing routes
  through the existing `_doc_to_rust_expr` (inheriting Group/Nest/Join/Comment rejection,
  re-raised with rule/context) and wraps in `fltk_unparser_core::separator_spec(...)` +
  `acc.add_trivia(...)`. The default-separator spacing comes from `get_spacing_for_separator`.
- `tests/test_rust_unparser_generator.py`: 7 new tests — WS_REQUIRED consume-whitespace shape
  (bounds, Span match, pos++, newline count, HardLine + default Line, two `return None`),
  WS_ALLOWED never-returns-None + `Doc::Nil` default + no OOB else, `preserve_blanks=2`
  blank-line branch, non-trivia rule emits no trivia processing (deferred-branch negative),
  NO_WS emits nothing (default `_trivia`), a `_gen_trivia_processing` unit (NO_WS/non-trivia
  no-op + trivia-rule fires), and an `_add_separator_spec_lines` unsupported-spacing rejection.
  117 generator tests pass; ruff check + ruff format --check + pyright clean.

Notes / deviations:
- `preserve_blanks` reads the *global* `trivia_config.preserve_blanks` exactly as the Python
  branch does (`:1168`), **not** the rule-aware `get_preserve_blanks` (which exists but the
  Python `_gen_trivia_processing` does not call); replicated for byte-parity.
- The combined `is_unlabeled and is_span` Python guard becomes one `if let (None,
  cst::{CN}Child::Span(span))` pattern (label `None` makes it refutable, so the `else` arm is
  always reachable and no `num_child_variants > 1` guard is needed here, unlike the term-body
  span/identifier matches).
- The initial-sep call site is wired symmetrically but only the sep_after path is exercised by
  tests (a trivia rule with a WS *initial* separator is not constructible via `parse_grammar`);
  both route through the same `_gen_trivia_processing`. The empty-alternative short-circuit
  (unreachable — the parser rejects empty alternatives) skips initial-sep, a benign dead-path
  divergence.
- Generated unparser still not compiled (no fixture crate yet, §2.6); per the increment-6..18
  deferral, clippy/rustfmt/warning conformance is handled by `make fix` when the fixture lands.
  The new core `separator_spec` constructor *is* compiled and tested. Remaining design work:
  the non-trivia-rule trivia branch + its utilities (§2.2), PyO3 wrapper + intermediate-Doc
  exposure + `.pyi` (§2.3/OQ-2/OQ-3), CLI/Makefile/LibSpec wiring (§2.5), fixture (§2.6),
  parity tests (§4).

---

## Increment 20 — non-trivia-rule branch of `_gen_trivia_processing` + trivia utilities

Completed design §2.2's "Trivia processing" by porting the **non-trivia-rule** branch of
`_gen_trivia_processing` (`gsm2unparser.py:1265`-`:1427`) plus the two utilities only that
branch calls (`_has_preservable_trivia` `:846`, `_count_newlines_in_trivia` `:971`). This
is the last remaining §2.2 piece; increment 19 explicitly deferred it to "the next
increment" (it depends on the trivia-rule branch's `unparse__trivia` being correct first).
The two branches of the single Python method split cleanly into one semantic unit each.

- `crates/fltk-unparser-core/src/accumulator.rs`: added `pub fn last_was_trivia(&self) ->
  bool` (the field was private; the generated non-trivia branch reads it cross-crate, port
  of the `accumulator.last_was_trivia` read at `gsm2unparser.py:1266`). +1 `#[test]`
  (`last_was_trivia_accessor_reflects_state`); 112 crate tests pass, clippy + `cargo fmt
  --check` clean.
- `fltk/unparse/gsm2unparser_rs.py` `_gen_trivia_processing`: the non-trivia-rule arm now
  calls the new `_gen_non_trivia_rule_processing` (was a deferred `return []`).
- `_gen_non_trivia_rule_processing(rule_name, class_name, separator, indent)` (new): port
  of `:1265`-`:1427`. Emits `if !acc.last_was_trivia() { if pos < node.children().len() {
  match &node.children()[pos].1 { cst::{CN}Child::Trivia(trivia_shared) => { … } _ => {
  <default sep> } } } else { <default sep> } }`. The Trivia arm read-locks the
  `Shared<Trivia>`; `if self._has_preservable_trivia(&trivia_node)` → `if let Some(
  trivia_result) = self.unparse__trivia(&trivia_node)` → `SeparatorSpec(None,
  Some(trivia_result.accumulator.doc()), required)` (preserved trivia precedence), else the
  newline-driven blank/single/default spacing (same `preserve_blanks` three-/two-way as the
  trivia-rule branch, reusing `_add_separator_spec_lines` / `_add_default_separator_spec_lines`);
  `pos += 1` always (`:1402`). The not-a-Trivia `_ =>` catch-all is emitted only when
  `num_child_variants > 1` (a Trivia-only child enum's single arm is exhaustive). Unlike the
  trivia-rule branch it never `return None`s — not-a-Trivia / OOB always emit default spacing.
- `_gen_trivia_helper_methods` / `_gen_has_preservable_trivia_method` /
  `_gen_count_newlines_in_trivia_method` (new): emitted once at the head of the `impl
  Unparser` block (wired into `_gen_rule_methods`). `_has_preservable_trivia` triages the
  `trivia_config`: `preserve_node_names is None` → `true`; empty / no config / no configured
  name is an actual trivia child → `false`; else loops the children and `return true`s on a
  matching `cst::TriviaChild::{Name}` (names filtered against the real trivia child classes).
  `_count_newlines_in_trivia` sums `span.text().map(|t| t.matches('\n').count())
  .unwrap_or(0)` over `cst::TriviaChild::Span` children (design §2.2's inline `_count_newlines`
  substitute). The param is `_trivia_node` when unused (constant-body cases).
- Docstrings updated (`_gen_rule_methods`, `_gen_alternative_body`, `_gen_trivia_processing`)
  to move the non-trivia branch from deferred into implemented.
- `tests/test_rust_unparser_generator.py`: rescoped 2 stale tests (the deferred-branch
  `test_non_trivia_rule_emits_no_trivia_processing` is replaced by the positive
  `test_non_trivia_rule_emits_trivia_preservation_branch`; the unit dispatch test now uses a
  grammar with a real non-trivia WS gap and asserts the branch fires). Added a non-trivia
  section (9 tests): preservation-branch shape, WS_ALLOWED required=false + Nil default,
  `preserve_blanks>0` blank-line branch, single-variant catch-all omission,
  `_count_newlines_in_trivia` shape, and four `_has_preservable_trivia` cases (default→false,
  None→true, unknown-name→dropped→false, configured-comment-rule→match arm). 125 generator
  tests pass; ruff check + ruff format --check + pyright clean.

Notes / deviations:
- **`last_was_trivia()` accessor added to the core crate** beyond design §2.1's literal
  accumulator surface: the field is private and the generated non-trivia branch (a separate
  crate) must read it. Small, faithful supporting change to this branch's semantic unit; the
  Python reads the attribute directly (`:1266`).
- **`_has_preservable_trivia` filters configured names against actual trivia child classes.**
  The Python builds an `isinstance(child, cst.{Name})` per configured name; a name that is a
  real class but never a trivia child simply never matches at runtime, and a name that is not
  a class at all errors at runtime. The Rust backend cannot emit a match arm for a nonexistent
  `TriviaChild` variant (compile error), so a non-present name is dropped — reproducing the
  Python "never matches → false" outcome rather than diverging. A name naming a real,
  non-trivia class is the only divergence (Python: never-match; Rust: dropped), both
  off-happy-path misconfigurations.
- **Trivia helper methods are emitted unconditionally** (matching the Python backend's
  unconditional emission and the already-unconditional `unparse__trivia`). When the
  non-trivia branch is present (any non-trivia rule with a WS gap — true for the §2.6 fixture)
  the helpers are live; for a trivia-less grammar they (like `unparse__trivia`) would be dead
  private methods — the same deferred warning-conformance bucket the prior increments note,
  resolved holistically when the fixture lands and the generated unparser first compiles.
- The non-trivia branch reads `acc.last_was_trivia()` then reassigns the alternative body's
  `let mut acc`; the `match`/`if let` borrow of `node` coexists with the `pos`/`acc` local
  mutations (independent bindings).
- Generated unparser still not compiled (no fixture crate yet, §2.6); per the increment-6..19
  deferral, clippy/rustfmt/warning conformance is handled by `make fix` when the fixture
  lands. The new core `last_was_trivia` accessor *is* compiled and tested. This completes
  design §2.2 (the `RustUnparserGenerator` walk + trivia). Remaining design work: PyO3 wrapper
  + intermediate-Doc exposure + `.pyi` (§2.3/OQ-2/OQ-3), CLI/Makefile/LibSpec wiring (§2.5),
  fixture (§2.6), parity tests (§4).

---

## Increment 21 — PyO3 wrapper layer (string-returning per-rule methods)

Ported design §2.3's PyO3 wrapper: a `#[cfg(feature = "python")] mod python_bindings
{ ... }` block emitting `PyUnparser` (the Python-visible `Unparser`) with a no-arg
constructor, one full-pipeline string-returning method per rule, and the
`register_classes` registrar + re-export. Parallels
`gsm2parser_rs.RustParserGenerator._gen_python_bindings`. Generator + tests only; no core
crate changes (the pipeline functions already existed from §2.1).

- `fltk/unparse/gsm2unparser_rs.py` `generate()`: appended section 4 — calls the new
  `_gen_python_bindings()`.
- `_gen_python_bindings()` (new, end of class): emits the gated `mod python_bindings`
  with `use pyo3::prelude::*;`, `use super::cst;`, `use super::Unparser;`, and
  `use super::{Renderer, RendererConfig, resolve_spacing_specs};`; the
  `#[pyclass(name = "Unparser")] pub struct PyUnparser { inner: Unparser }`; the `#[new]
  fn new()` building `PyUnparser { inner: Unparser::new() }`; one
  `#[pyo3(signature = (node, max_width = 80, indent_width = 4))] fn unparse_{rule}(&self,
  node: PyRef<'_, cst::Py{CN}>, max_width: usize, indent_width: usize) ->
  PyResult<Option<String>>` per `self._grammar.rules` (read-lock `node.shared()`,
  `let Some(r) = self.inner.unparse_{rule}(&guard) else { return Ok(None); }`,
  `resolve_spacing_specs(r.accumulator.doc())`, `RendererConfig { indent_width,
  max_width }`, `Ok(Some(Renderer::new(cfg).render(&resolved)))`); and
  `pub fn register_classes(...)` (`module.add_class::<PyUnparser>()?;`) + the gated
  `pub use python_bindings::register_classes;`.
- `tests/test_rust_unparser_generator.py`: 7 new tests — module/pyclass/`#[new]`/super
  import shape, per-rule full-pipeline body, signature defaults, `resolve` by-value (the
  design's `&r.accumulator.doc()` is asserted absent), one-method-per-rule + correct Py
  handle types over a multi-rule grammar, `unparse__trivia` over `cst::PyTrivia`, and
  `register_classes` + re-export. 132 generator tests pass; ruff check + ruff format
  --check + pyright clean.

Notes / deviations:
- **`resolve_spacing_specs` is called by value** (`resolve_spacing_specs(r.accumulator.
  doc())`), not by reference as design §2.3's example writes (`&r.accumulator.doc()`):
  the core signature was changed to `Doc`-by-value in the deep-r1 review (logged there);
  the wrapper follows the actual signature. A test asserts the `&`-form is absent.
- **`unparse__trivia` is exposed as a pyo3 method too.** The wrapper iterates
  `self._grammar.rules` (trivia-processed), so the synthetic `_trivia` rule yields an
  `unparse__trivia` Python method over `cst::PyTrivia` — matching both the parser backend
  (which exposes `apply__trivia`) and the Python unparser's per-rule public surface.
- **Pipeline types referenced via `super::`.** `Renderer`/`RendererConfig`/
  `resolve_spacing_specs` are imported once in the design-§2.2 root header; the wrapper
  reaches them through `super::` so that root import stays the single source of truth
  (rather than re-importing from `fltk_unparser_core` inside the module). Consequence:
  when the `python` feature is OFF, those three *root* imports are unused (the wrapper is
  their only consumer) → an unused-import warning. This is the same deferred
  warning-conformance bucket every prior increment notes (the generated unparser is not
  compiled until the §2.6 fixture lands, where `make fix` / holistic warning resolution
  applies); the design's root-header form is preserved unchanged.
- Generated unparser still not compiled (no fixture crate yet, §2.6); emitted Rust
  verified by inspection (the full `python_bindings` block for a literal grammar — pyclass,
  `new`, `unparse_greeting`, `unparse__trivia`, `register_classes`, re-export).
- This completes design §2.3.

## Deep review round 7 — respond fixes

Applied against HEAD 1fcae0b (review of trivia/separator processing + PyO3 wrapper).

- **Cross-backend parity fix (correctness-1).** `_gen_non_trivia_rule_processing`'s
  `preserve_blanks == 0` no-preservable arm now emits the configured default separator
  *unconditionally* (no newline check), matching the Python non-trivia branch
  (`gsm2unparser.py:1392-1399`). Previously the Rust port mistakenly mirrored the
  trivia-rule branch's single-newline `HardLine`, diverging in the default-config common
  case. The trivia-rule branch still keeps its `preserve_blanks == 0` line-structure
  `HardLine` (`preserve_line_at_zero=True`).
- **Shared ladder helper (reuse-1 / correctness-1).** Extracted
  `_gen_newline_separator_ladder` (the `newline_count` -> `SeparatorSpec` branching) and
  `_get_preserve_blanks`, used by both trivia branches; the trivia-rule vs non-trivia
  `preserve_blanks == 0` difference is the `preserve_line_at_zero` flag. The non-trivia
  branch now binds `newline_count` only when the ladder reads it (preserve_blanks > 0), so
  the corrected `== 0` path has no unused binding.

Deviations from design introduced this round:
- **Borrowing newline accessor (efficiency-1).** Design §2.2 specified
  `span.text().map(...)` for newline counting; the trivia-rule branch and
  `_count_newlines_in_trivia` now emit `span.text_str().map(...)`, backed by a new
  allocation-free `Span::text_str(&self) -> Option<&str>` in `fltk-cst-core`
  (`crates/fltk-cst-core/src/span.rs`; `text()` now delegates to it). Removes a per-gap
  `String` allocation on the inter-token hot path. The regex term body keeps `.text()`
  (it retains an owned `String`).
- **Dead-code guards.** The trivia helper methods `_has_preservable_trivia` /
  `_count_newlines_in_trivia` are emitted with `#[allow(dead_code)]`: a grammar with no
  non-trivia WS gap (or, for the counter, `preserve_blanks == 0`) leaves them uncalled,
  and the generated unparser is public API for downstream grammars that may not exercise
  them. Without this the parity fix would leave `_count_newlines_in_trivia` uncalled (hence
  a clippy `dead_code` error) for the default-config fixture once §2.6 lands.
- **Encapsulation (quality-1).** Added public `RustCstGenerator.child_class_names_for_rule`
  (parallel to `num_child_variants`); the unparser generator no longer reaches into the
  private `_child_variants_for_rule`.
- Test hardening: `#[pymethods]`/`impl PyUnparser`/indented inner-`use` assertions,
  branch-fingerprinted dispatch unit test, a multi-variant `_count_newlines_in_trivia`
  catch-all test, a per-rule `ws_required_spacing` override test, and the locked-in
  non-trivia tests updated to the corrected (default-only) `preserve_blanks == 0` output.
  134 generator tests + 57 `fltk-cst-core` (--no-default-features) tests pass; ruff,
  pyright, and `clippy -p fltk-cst-core --no-default-features -D warnings` clean.

---

## Increment 22 — `gen-rust-unparser` CLI subcommand

Added the `gen-rust-unparser` CLI subcommand (design §2.5, first bullet),
mirroring the existing `gen-rust-parser`. CLI-only; no core crate, no Makefile,
no LibSpec wiring (those are later §2.5 increments).

- `fltk/fegen/genparser.py:19-20`: added top-level imports
  `from fltk.plumbing import parse_format_config_file` and
  `from fltk.unparse import gsm2unparser_rs` (both verified circular-import-free;
  `fltk.plumbing` does not import `genparser`).
- `fltk/fegen/genparser.py` `gen_rust_unparser` (`@app.command(name="gen-rust-unparser")`):
  `GRAMMAR OUTPUT [--cst-mod-path super::cst] [--format-config FILE.fltkfmt]`.
  Validates `--cst-mod-path` against the existing module-level `_CST_MOD_PATH_RE`
  (exit 1 on mismatch, before any file write); parses the grammar via
  `_parse_grammar_raw` (which already exits 1 on missing/unparseable grammar);
  when `--format-config` is given, parses it via
  `fltk.plumbing.parse_format_config_file` (`ValueError`/`FileNotFoundError` →
  exit 1); builds `RustUnparserGenerator(grammar, formatter_config=…,
  cst_mod_path=…, source_name=str(grammar_file))` and `generate()`s inside a
  `try` so a `ValueError`/`RuntimeError` (e.g. required-suppressed regex,
  group/nest/join separator) exits 1 *before* writing — no partial file. Writes
  `output_file` only after successful generation.
- `fltk/fegen/test_genparser.py`: new `gen-rust-unparser` CLI section, 7 tests
  (mirroring the `gen-rust-parser` section) — happy path (emits `unparse_word`,
  the `fltk_unparser_core` import, `use super::cst;`), missing grammar file,
  generation error leaves no partial file (required-suppressed regex
  `parent := %/[a-z]+/ , "x" ;`), invalid `--cst-mod-path`, custom
  `--cst-mod-path` propagates to the `use my::cst;` line, `--format-config`
  applied (parses + reaches generator), and missing `--format-config` file →
  exit 1 with no output.
- `uv run pytest fltk/fegen/test_genparser.py tests/test_rust_unparser_generator.py`
  (166 passed); ruff check + ruff format --check + pyright clean on both changed
  files.

Notes:
- `parse_format_config_file` raises `FileNotFoundError` for a missing config and
  `ValueError` on a parse failure; both are caught → exit 1 (CLI-friendly),
  slightly broadening the design's literal "`ValueError`/`RuntimeError`" to also
  cover the missing-file case for the format-config option.
- Remaining design work: Makefile + LibSpec wiring (§2.5), intermediate-Doc
  exposure + `.pyi` (OQ-2/OQ-3), fixture (§2.6), parity tests (§4).

---

## Increment 23 — LibSpec unparser wiring (§2.5 `gsm2lib_rs.py` + `--unparser` flag)

Continued design §2.5 with the `LibSpec` wiring (third bullet): a downstream consumer's
generated `lib.rs` can now include the unparser submodule. Generator + CLI + tests; no
core crate, no Makefile (later §2.5 increment), no fixture.

- `fltk/fegen/gsm2lib_rs.py` `LibSpec.standard`: added the keyword-only
  `with_unparser: bool = False` param (design §2.5 signature). When `True` it appends
  `Submodule("unparser", "unparser")` after the (optional) parser submodule — so the
  emitted order is cst, parser, unparser. `register_fn` stays the default
  `register_classes` (existing two-submodule convention). cst is still always present;
  `with_parser` and `with_unparser` are orthogonal (e.g. `with_parser=False,
  with_unparser=True` → cst + unparser). Docstring updated.
- `fltk/fegen/genparser.py` `gen_rust_lib`: added the `--unparser` flag
  (`unparser: bool = False`), passed as `with_unparser=unparser` to
  `LibSpec.standard(...)`. Like `--no-parser`, it has no effect on the `--no-cst`
  runtime-only path (that branch builds an empty-submodule `LibSpec` directly), matching
  the existing convention that submodule flags are silently inert under `--no-cst`.
  Command docstring + examples updated.
- `fltk/fegen/test_gsm2lib_rs.py`: added a `with_unparser` section (5 tests) — default
  omits the unparser submodule, `with_unparser=True` emits `mod unparser;` + its
  `register_submodule` call, all-three-submodules present, `with_parser=False,
  with_unparser=True` (cst + unparser, no parser), and the cst→parser→unparser
  registration order.
- `fltk/fegen/test_genparser.py`: added 3 `gen-rust-lib` CLI tests — `--unparser`
  adds the unparser submodule alongside cst + parser, default omits it, and
  `--no-parser --unparser` emits cst + unparser only.
- `uv run pytest fltk/fegen/test_gsm2lib_rs.py fltk/fegen/test_genparser.py` (77 passed);
  ruff check + ruff format --check + pyright clean on all four changed files.

Notes:
- `--unparser` is an additive flag defaulting off (vs `--no-parser`'s default-on
  invert) because the unparser is the new, opt-in submodule; existing `gen-rust-lib`
  invocations emit byte-identical output (the default-config negative tests confirm).
- Remaining design work: Makefile wiring (§2.5), OQ-2 intermediate-Doc exposure,
  OQ-3 `.pyi`, fixture (§2.6), parity tests (§4).

---

## Increment 24 — fixture compiles the generated unparser + Makefile target

Stood up the generated unparser inside the existing `tests/rust_parser_fixture/`
crate so it *first compiles and links* — the milestone every prior generation
increment deferred ("Generated unparser still not compiled (no fixture crate yet,
§2.6)"). This is also where the holistic generated-code warning conformance the
prior increments promised "when the fixture lands" is resolved. Default
`FormatterConfig` (no `.fltkfmt` yet).

Fixture wiring (design §2.6):
- `tests/rust_parser_fixture/Cargo.toml:21`: added
  `fltk-unparser-core = { path = "../../crates/fltk-unparser-core" }` (a plain,
  non-optional, pyo3-free dep — the PyO3 wrapper lives in the *generated* code and
  uses the fixture's own `pyo3`, so no feature coordination; the fixture's
  default-features graph stays pyo3-free, so `check-no-pyo3` still passes).
- `tests/rust_parser_fixture/src/unparser.rs` (new, generated, ~2204 lines):
  produced by the new Makefile target from `rust_parser_fixture.fltkg`.
- `tests/rust_parser_fixture/src/lib.rs:3,18`: `pub mod unparser;` + the
  `register_submodule(m, "unparser", unparser::register_classes)` call under the
  existing `#[cfg(feature = "python")] #[pymodule]`.

Makefile (design §2.5 second bullet):
- `Makefile`: `gen-rust-unparser` target mirroring `gen-rust-parser`
  (`GRAMMAR`/`RS_OUT`), and a `gencode` line regenerating the fixture's
  `unparser.rs` (so the committed file is regenerable — gencode-drift discipline,
  design §3). The fixture is already in every `cargo clippy`/`cargo test`/
  `check-no-pyo3`/`cargo-deny` lane via its manifest path, so `pub mod unparser;`
  brings the generated unparser under all of them automatically — no new lane lines.

Generator warning-conformance fixes (`fltk/unparse/gsm2unparser_rs.py`) — the first
compile under `-D warnings` surfaced exactly three structural lint classes; each
fixed at the generator so *every* downstream grammar's output is clean, not just
this fixture:
- **python-off unused imports.** `_gen_header` now splits the unparser-core import:
  `DocAccumulator`/`Doc`/`UnparseResult` stay unconditional, and the pipeline types
  `Renderer`/`RendererConfig`/`resolve_spacing_specs` (consumed only by
  `python_bindings` via `super::`) move to a `#[cfg(feature = "python")]`-gated
  `use`. Without this a python-off build flags those three as unused.
- **unused `node` param.** New `_node_param(body_lines)` static helper (`\bnode\b`
  word-boundary scan); `_gen_item_method`, `_gen_inner_methods`, and
  `_gen_alternative_body` name the param `_node` when the emitted body never reads
  the node — i.e. `SUPPRESS` items, `INLINE` literals, and the degenerate
  empty-alternative body. (clippy `unused_variables`.)
- **single-variant infallible match.** `_gen_identifier_term_body` and
  `_gen_regex_term_body` now emit an irrefutable `let cst::{Enum}::{V}(x) =
  &child_tuple.1;` for a single-variant child enum (the multi-variant
  `match … { _ => return None }` form is unchanged). (clippy
  `infallible_destructuring_match`.)
  These are warning-conformance/idiomatic-codegen changes only; emitted *behavior*
  is identical (an irrefutable `let` destructures the same single variant; `_node`
  is the same unused binding).

Tests (`tests/test_rust_unparser_generator.py`): updated the 8 string-assertion
tests the new shapes touched (single-variant identifier/regex → irrefutable `let`,
suppressed-literal item method → `_node`), and strengthened
`test_generate_emits_header_and_struct` to lock in the python-gated pipeline
import. 134 generator tests + the genparser CLI tests pass.

Verified: `cargo clippy -D warnings` clean on the fixture for both feature sets and
on the workspace (incl. `fltk-unparser-core`); fixture native (`--no-default-features`)
`cargo test` green; `maturin develop --features extension-module` builds the
extension with the `unparser` submodule registered; an end-to-end smoke
(Rust-parse → Rust-unparse via Python: `num`/`name`/`nest`/`expr`/`paren_expr`)
round-trips correctly; and full `make check` passes.

Deviations / notes:
- **Default-config fixture; `.fltkfmt` split out.** Design §2.6 calls for a
  `.fltkfmt` exercising spacing/before-after anchors/rule- and item-level
  group/nest/join. With the default config those generation paths emit nothing, so
  the item-level anchor/spacing *generated* Rust is not compile-exercised here. The
  `.fltkfmt` fixture config (and its compile + parity coverage) is a separate later
  increment; this one is the first-compile milestone for the core walk, all term
  kinds, quantifiers, sub-expressions, trivia processing, and the PyO3 string
  wrapper.
- **`gen-rust-unparser` Makefile target mirrors `gen-rust-parser` exactly** (no
  `--format-config` passthrough). The `.fltkfmt` increment will pass the config
  (the `collision_parser` gencode line is the precedent for calling the CLI
  directly when a target's positional form is insufficient).
- The generator warning fixes are beyond design §2.2's literal emission shapes but
  are precisely the "holistic warning conformance … resolved when the fixture
  lands" that increments 6–21 each deferred; no `#![allow(...)]` blanket
  suppressions were used.

---

## Increment 25 — intermediate-Doc exposure to Python (OQ-2)

Exposed the unparser's intermediate `Doc` to the Python surface (design OQ-2, user
answer "Please expose the intermediate Doc"; design §2.4 settles it as purely
additive). One semantic change: a `PyDoc` handle plus the per-rule methods that
produce it — interdependent parts of one feature. The string-returning
`unparse_{rule}` methods (§2.3, increment 21) are untouched. Generator + regenerated
fixture + tests only; no core crate change (`fltk-unparser-core` is pyo3-free by
design §2.1, so all pyo3 lives in the *generated* `python_bindings`).

- `fltk/unparse/gsm2unparser_rs.py` `_gen_python_bindings`: emits, inside the gated
  `mod python_bindings`, a `#[pyclass(name = "Doc", unsendable)] pub struct PyDoc {
  resolved: fltk_unparser_core::Doc }` with `#[pymethods]` `render(&self,
  max_width=80, indent_width=4) -> String` (builds `RendererConfig` and runs
  `Renderer::new(cfg).render(&self.resolved)`, reusing the `super::`-imported pipeline
  types) and `__repr__(&self) -> String` (`format!("Doc({:?})", self.resolved)`).
- `_gen_python_bindings` per-rule loop: after each string `unparse_{rule}` method,
  also emits `fn unparse_{rule}_doc(&self, node: PyRef<'_, cst::Py{CN}>) ->
  PyResult<Option<PyDoc>>` — read-lock the handle, `self.inner.unparse_{rule}`, then
  `resolve_spacing_specs(r.accumulator.doc())`, wrap in `PyDoc { resolved }`. Returns
  the *resolved* Doc (design §4 "expose the resolved Doc"); stops before rendering so
  a caller can render at multiple widths without re-walking the CST.
- `_gen_python_bindings` `register_classes`: now also `module.add_class::<PyDoc>()?;`.
- `_gen_python_bindings` docstring: added the OQ-2 paragraph describing the additive
  surface.
- `tests/rust_parser_fixture/src/unparser.rs`: regenerated (+302 lines, all confined
  to `python_bindings`: the `PyDoc` block + one `unparse_*_doc` per rule + the new
  registration). Committed as raw generator output (see formatting note below).
- `tests/test_rust_unparser_generator.py`: added a `_pymethod_body` helper (extracts
  an 8-space-indented `#[pymethods]` method; `_method_body` only handles 4-space rule
  methods) and 6 tests — PyDoc pyclass+`unsendable`+field, the `render`+`__repr__`
  methods, the per-rule doc method resolving-without-rendering, one-doc-method-per-rule
  with correct Py handle types, the trivia-rule doc method, and PyDoc registration.

Verification:
- 153 Python tests pass (`tests/test_rust_unparser_generator.py` 145 +
  `test_rust_parser_fixture_bindings.py`); ruff check + ruff format --check + pyright
  clean on the changed Python.
- `cargo clippy -D warnings` clean on the fixture for both feature sets
  (`--features python` and default/python-off); native `cargo test` on the fixture
  green (59 passed).
- Runtime smoke (built via `make build-rust-parser-fixture`): Rust-parse `"123"` →
  `unp.unparse_num_doc(node)` returns a `Doc`; `repr(doc)` == `Doc(Text("123"))`;
  `doc.render()`, `doc.render(max_width=5)`, `doc.render(5, 2)` all work and
  `doc.render() == unp.unparse_num(node)` (string-method parity).

Deviations / notes:
- **`unsendable` on `PyDoc`** — beyond the design's bare "expose the Doc" wording, but
  forced: the core `Doc` uses `Rc` (design §2.1), so a `PyDoc` field is `!Send` and a
  plain `#[pyclass]` fails to compile. `unsendable` is pyo3's sanctioned mechanism (the
  handle may only be touched on its creating thread — fine for a formatting Doc).
  Making `Doc` `Send` would mean switching the core to `Arc`, a much larger out-of-scope
  core change.
- **`__repr__` added** beyond a bare render surface, serving OQ-2's explicit "or to
  inspect formatting" motivation (via the derived `Doc` `Debug`). Recursive like
  `Debug`/resolve/render — same deferred deep-tree class as answered OQ-1.
- **`PyDoc` field uses the fully-qualified `fltk_unparser_core::Doc` path**, not an
  import: the header's `Doc` import is gated on `_uses_doc_type`, so a `use super::Doc;`
  or a second `use fltk_unparser_core::Doc;` in `python_bindings` would either be
  unresolved or a duplicate-import error depending on the grammar. The qualified path
  sidesteps both.
- **Generated Rust is committed as raw generator output** — confirmed `make fix` is
  ruff-only (Python) and `make check` has no `cargo fmt --check` gate, so the
  unparser-core/generated `.rs` formatting is the generator's own emission, not
  `cargo fmt`'s. (An initial `cargo fmt` reflowed the whole file; reverted.) This
  corrects the standing "clippy/rustfmt conformance handled by `make fix`" phrasing in
  earlier increment notes: warning conformance is handled by generator emission +
  clippy (resolved in increment 24); rustfmt is not part of the gate for this file.

---

## Increment 26 — `.pyi` type stub for the unparser's Python surface (OQ-3)

Design OQ-3 (user answer: "Yes, emit .pyi"). Added `.pyi` emission for the generated
unparser's Python surface, wired into the `gen-rust-unparser` CLI, mirroring the CST
backend's `generate_pyi` + `--protocol-module`/`--pyi-output` precedent
(`gsm2tree_rs.py:321`, `genparser.py` `gen-rust-cst`). Generator + CLI + tests only; no
core crate change and no fixture regeneration (`generate()` output is byte-unchanged — a
`.pyi` is a separate artifact).

- `fltk/unparse/gsm2unparser_rs.py` `generate_pyi(protocol_module)` (new, after
  `generate()`): emits a pure-Python `.pyi` — `from __future__ import annotations`,
  `import typing`, `import {protocol_module} as _proto`; a `class Doc:` with
  `render(self, max_width=..., indent_width=...) -> str` and `__repr__(self) -> str`; and a
  `class Unparser:` with `__init__(self) -> None` plus, per rule (iterating the
  trivia-processed `self._grammar.rules`, so `_trivia` yields `unparse__trivia`), the
  string method `unparse_{rule}(self, node: _proto.{CN}, max_width=..., indent_width=...)
  -> typing.Optional[str]` and the additive OQ-2 Doc method `unparse_{rule}_doc(self,
  node: _proto.{CN}) -> typing.Optional[Doc]`. Pure (no `self._generated`/`_uses_doc_type`
  side effects); callable independent of `generate()`.
- `fltk/fegen/genparser.py` `gen_rust_unparser`: added `--protocol-module` and
  `--pyi-output` options (mirroring `gen-rust-cst`). `--pyi-output` without
  `--protocol-module` → exit 1 (before any write). The `.pyi` text is generated together
  with the `.rs` inside the one `try` (so a generation error leaves no partial artifacts),
  the `.rs` is written first, then the `.pyi` to `--pyi-output` or
  `output_file.with_suffix(".pyi")`. Command docstring + examples updated.
- `tests/test_rust_unparser_generator.py`: 7 generator tests — header imports, `Doc`
  class shape, `Unparser` class + `__init__`, per-rule string + doc method signatures
  (node typed `_proto.{CN}`), multi-rule per-rule class names, trivia rule over
  `_proto.Trivia`, and `ast.parse` validity of the emitted stub.
- `fltk/fegen/test_genparser.py`: 5 CLI tests — no `.pyi` by default (backward compatible),
  `--protocol-module` writes a `.pyi` next to the `.rs` (content + `ast.parse`),
  `--pyi-output` override, `--pyi-output` without `--protocol-module` rejected (nothing
  written), and `.rs` byte-unchanged with vs without `--protocol-module`.
- `uv run pytest tests/test_rust_unparser_generator.py fltk/fegen/test_genparser.py`
  (192 passed); ruff check + ruff format --check + pyright clean on all four changed files.

Notes / deviations:
- **`node` typed via the CST protocol module (`_proto.{CN}`), requiring `--protocol-module`.**
  Design OQ-3 only says "emit .pyi"; it does not specify how to type the `node` parameters.
  Resolved by following the CST `.pyi` precedent exactly: the unparser's `unparse_*` methods
  accept the Rust CST handles, whose config-agnostic type identity is the CST protocol
  module's `{CN}` (a `typing.Protocol`), so a downstream caller's Rust-CST node structurally
  conforms without a cast. OQ-3's phrase "the unparser has no such protocol" refers to the
  absence of an `UnparserModule` conformance protocol (the CST's `CstModule`), not to the
  node types — the unparser stub references `_proto` only to type `node`, and emits no
  module-level conformance assertions. Without `--protocol-module`, no `.pyi` is emitted
  (backward compatible, matching `gen-rust-cst`).
- **`.pyi` uses `typing.Optional[...]`** (not `X | None`), matching the committed CST `.pyi`
  (`gsm2tree_rs.generate_pyi`) which passes `make check`; keeps the two stub generators
  stylistically aligned.
- **Fixture `.pyi` (commit + pyright coverage) deferred.** This increment validates the
  stub via generator-level content assertions + `ast.parse`; committing a generated `.pyi`
  into `tests/rust_parser_fixture/` and running pyright against it folds naturally into the
  remaining `.fltkfmt` fixture (§2.6) / parity (§4) work. Remaining design work: `.fltkfmt`
  fixture config + Makefile `--format-config` passthrough + item-level anchor compile
  coverage (§2.6/§2.5), cross-backend parity tests + `tests/unparser_parity.py` (§4), and
  the native `native_tests.rs` unparser test (§4).

---

## Increment 27 — `.fltkfmt` fixture format config + regenerate fixture unparser (§2.6)

Added a non-default `.fltkfmt` format config for the fixture grammar and regenerated
`unparser.rs` against it, so the spacing/anchor generated-Rust paths the default config
never reaches — before/after anchors, rule-level group/nest/join (RULE_START/RULE_END
push/pop), and item-level group/nest/join ranges (per-item push/pop) — are first
compile-exercised and linked. This is design §2.6's `.fltkfmt` (plus the §2.5 Makefile
`--format-config` passthrough for the fixture's gencode line, done via a direct CLI call
per the increment-24 `collision_parser` precedent).

- `fltk/fegen/test_data/rust_parser_fixture.fltkfmt` (new): `ws_allowed: bsp;` /
  `ws_required: nbsp;` defaults; top-level `before "+" { nbsp; }` / `after "+" { nbsp; }`;
  `rule expr { group; nest from lhs to rhs; after lhs { nbsp; } }` (rule-level group +
  label-anchored item-level nest range + label after-spacing); `rule stmt { group from
  lhs to rhs; before "=" { nbsp; } after "=" { nbsp; } }` (label-anchored item-level
  group range, WS_REQUIRED default, literal anchors); `rule items { join bsp; after item
  { bsp; } }` (rule-level join with a primitive `bsp`→`Doc::Line` separator + label
  after-spacing over a quantified item); `rule paren_expr { nest; group from after "("
  to before ")"; after "(" { soft; } before ")" { soft; } }` (rule-level nest +
  literal-anchored item-level group range with from-after/to-before modifiers + literal
  anchors). All separators stay primitive (group/nest/join Doc separators are rejected
  by both backends).
- `Makefile:285-287`: the fixture's `gencode` `unparser.rs` line is now a direct
  `python -m fltk.fegen.genparser gen-rust-unparser --format-config … <grammar> <out>`
  call (was `$(MAKE) gen-rust-unparser GRAMMAR=… RS_OUT=…`), so the committed fixture
  unparser is regenerated with the format config. The `gen-rust-unparser` Makefile
  *target* is unchanged (still mirrors `gen-rust-parser`, no `--format-config`), matching
  increment 24's plan that the positional target stays simple and the fixture line calls
  the CLI directly (the `collision_parser` precedent).
- `tests/rust_parser_fixture/src/unparser.rs`: regenerated (~2204 → 2496 lines). New
  emissions confirmed present: 3 `push_group()` (1 rule-level `expr`, 2 item-level
  `stmt`/`paren_expr`), 2 `push_nest` (item-level `expr nest from lhs to rhs` +
  rule-level `paren_expr nest`), 1 `push_join(Doc::Line)` (rule-level `items`), 7
  matching `pop_*`, and 12 `before_spec`/`after_spec` calls — placement verified by
  inspection (e.g. `unparse_paren_expr` entry `push_nest(1)` + success `pop_nest()`;
  item-level `push_group()` after the `(` item and `pop_group()` before the `)` item;
  `after_spec(Doc::SoftLine)` after `(`, `before_spec(Doc::SoftLine)` before `)`).

Verification:
- `cargo clippy -D warnings` clean on the fixture for both feature sets
  (`--features python` and default/python-off) and `check-no-pyo3` still holds (the
  unparser-core dep is pyo3-free; the default graph has no pyo3).
- Native `cargo test` on the fixture: 59 passed (the format-config `unparser.rs` links
  and runs).
- `uv run pytest tests/test_rust_unparser_generator.py fltk/fegen/test_genparser.py`:
  192 passed (no Python source changed; generator/CLI behavior unaffected).

Notes:
- This increment is the first compile-exercise of the item-level/rule-level anchor and
  before/after-spacing generated Rust (default config emits none of it); end-to-end
  cross-backend *behavioral* parity over this config is asserted by the §4 parity tests
  (a later increment), not here.
- Committed `unparser.rs` is raw generator output (no `cargo fmt`), per increment 25's
  finding that `make check` has no `cargo fmt --check` gate for these files.
- Remaining design work: cross-backend parity tests + `tests/unparser_parity.py` (§4),
  the native `native_tests.rs` unparser test (§4), and the committed fixture `.pyi` +
  pyright coverage (OQ-3 follow-up).

---

## Increment 28 — cross-backend unparser parity tests (§4, `.fltkfmt` config)

Ported design §4's "Cross-backend parity" deliverable: a parity helper module plus the
fixture parity test, asserting the Python and Rust unparser backends render byte-equal
output for the same CST. One semantic unit (cross-backend unparse parity); the helper +
the test that consumes it implement the same change. Touches design §4 only.

Scope note — **`.fltkfmt` config only this increment.** The Rust unparser bakes its
`FormatterConfig` at *generation* time (design §2.2/§2.3: `Unparser::new()` takes no
config), and the committed fixture `unparser.rs` is baked with the `.fltkfmt`
(increment 27). So cross-backend parity over `.fltkfmt` is directly testable; parity
over the **default** `FormatterConfig` (design §4's "both") requires a *second* Rust
unparser module baked with the default config in the fixture — a separable fixture
change deferred to the next increment.

- `tests/unparser_parity.py` (new): the parity helper, analogous to
  `tests/parser_parity.py` (not a test module itself). `unparse_python` runs the Python
  pipeline (instantiate `unparser_class(text)` → `unparse_{rule}(cst)` → None-check →
  `resolve_spacing_specs(result.accumulator.doc)` → `render_doc` at a `RendererConfig`);
  `unparse_rust` calls the Rust `unparse_{rule}(node, max_width=, indent_width=)`
  full-pipeline method; `assert_unparse_parity` runs both at the same config and asserts
  they agree on success (None ⇔ Ok(None)) and on the rendered bytes.
- `tests/test_rust_unparser_parity_fixture.py` (new): `pytest.importorskip
  ("rust_parser_fixture")`; module-level caches for the grammar, the Python parser
  result (`capture_trivia=True`), and the Python unparser result (generated from the
  fixture `.fltkfmt`, matching the baked Rust config). A 37-entry `(rule, text)` corpus
  of fully-parsing inputs exercising the `.fltkfmt` paths (before/after `+`/`=`/`(`/`)`
  anchors, rule-level group/nest/join, item-level group/nest ranges, WS_REQUIRED/
  WS_ALLOWED spacing + trivia collapse) plus default-spacing rules, union labels,
  multibyte text, suppressed/`$`-included terms, sub-expressions, and bounded-depth
  recursion (design §4: recursion without the deep-tree limit). Parametrized over the
  corpus × two `RendererConfig`s — wide (80/4, everything flat) and narrow (8/2, groups
  break) — so the Wadler-Lindig flat-vs-break decisions are exercised cross-backend.
- `uv run pytest tests/test_rust_unparser_parity_fixture.py` (74 passed); ruff check +
  ruff format --check + pyright clean on both new files.

Notes:
- The helper inlines the 3-line Python pipeline (reusing `resolve_spacing_specs` +
  `render_doc`) rather than calling `plumbing.unparse_cst`, so an unparse failure maps
  to `None` (symmetric with the Rust `Optional[str]`) instead of `unparse_cst`'s
  `ValueError`, while a genuinely missing method still surfaces as `AttributeError`.
- The two Rust/Python `RendererConfig` field orders differ (`RendererConfig {
  indent_width, max_width }` in Rust; `RendererConfig(indent_width=4, max_width=80)` in
  Python) but the defaults match (4/80); the helper passes both as keywords so the
  matching is explicit.
- Remaining design work: default-`FormatterConfig` cross-backend parity (second baked
  Rust unparser module in the fixture + extend this corpus, §4/§2.6), the native
  `native_tests.rs` unparser test (§4), and the committed fixture `.pyi` + pyright
  coverage (OQ-3 follow-up).

---

## Increment 29 — native (GIL-free) unparser fixture test (§4)

Ported design §4's "Native fixture test" deliverable: native Rust `#[test]`s in the
`rust_parser_fixture` crate that build a CST via the native Rust parser API (spans
carry their own source), run the **core** pyo3-free `Unparser` + `resolve_spacing_specs`
+ `Renderer` with no `python` feature and no GIL, and assert the rendered string —
proving the `fltk-unparser-core` runtime and the generated pure-Rust `Unparser` link
and run with no Python runtime. Test-only; no core crate, generator, CLI, Makefile, or
`lib.rs` change (`native_tests.rs` is already `mod native_tests;` and in the fixture's
cargo lanes). Touches design §4 only.

- `tests/rust_parser_fixture/src/native_tests.rs`: appended a native-unparser section to
  the existing `#[cfg(test)] mod tests` — module `use`s (`crate::unparser::Unparser`,
  `fltk_unparser_core::{resolve_spacing_specs, Renderer, RendererConfig}`), a
  `render_native!($src, $parse, $unparse, $max_width, $indent_width)` macro (parse via the
  native `apply__parse_{rule}` → read-lock the `Shared` node → `Unparser::new().unparse_{rule}
  (&*guard)` → `resolve_spacing_specs(unparsed.doc())` → `Renderer::new(RendererConfig{..})
  .render(&resolved)`; asserts the parser consumed all codepoints via `chars().count() as
  i64`), and 9 `#[test]`s asserting the rendered bytes.
- Expected strings are the parity-validated Python-backend reference for the fixture
  `.fltkfmt` config the committed `unparser.rs` is baked with (increment 27): every
  (rule, text, config) asserted is a corpus entry in
  `tests/test_rust_unparser_parity_fixture.py` (which proves Python==Rust at these exact
  configs), so the constants are authoritative, not "assert whatever it emits". Derived
  via the Python pipeline at authoring time (`tests/unparser_parity.unparse_python`).
- Coverage: plain tokens (`num`/`name`/`atom`), WS_REQUIRED + item-level group + `=`
  anchors (`stmt` `"x = y"`), rule-level join + after-item spacing (`items` `"1a2b"` →
  `"1 a 2 b"`), rule group + `nest from lhs to rhs` flat-vs-break at both corpus configs
  (`expr` `"1+2+3"` → `"        1+2+3"` wide / `"    1+2+3"` narrow — exercises the
  Wadler-Lindig break decision + nest indentation in the pure-Rust renderer), rule-level
  nest + item-level `group from after "(" to before ")"` (`paren_expr` `"(42)"` →
  `"    (42)"` / `"  (42)"`), multibyte codepoint-indexed spans (`arrow` `"→x"`),
  bounded-depth recursion (`nest` `"(((42)))"`), the union-label span/regex arm
  (`val` `"!@#"`), and an empty zero-or-more match (`zero_items` `""` → `""`).
- `cargo test --no-default-features` on the fixture: 68 passed (59 prior + 9 new);
  the 9 `native_unparse_*` tests pass GIL-free. `cargo clippy --no-default-features`
  and `cargo clippy --features python`, both `-D warnings --all-targets`, clean.

Notes:
- The "native Rust API" used to build the CST is the native Rust **parser** (`Parser::new`
  over a source string), matching the parity test's Rust side; this gives spans real
  source so the regex/literal term bodies' `span.text()` succeed (a hand-built CST with
  `Span::unknown()` would hit the design-§3 sourceless-span `return None` path). The
  existing deep-tree tests in this module already use the same `Parser` API.
- `&*guard` (not `&guard`) passes the `RwLockReadGuard`'s target `&cst::{CN}` explicitly
  to the `unparse_{rule}(&self, node: &cst::{CN})` method.
- No `make check` gate concern beyond cargo: this increment touches only fixture test
  code, already in the fixture clippy/test lanes; no Python source changed.

Remaining design work: default-`FormatterConfig` cross-backend parity (second baked Rust
unparser module in the fixture + extend the corpus, §4/§2.6), and the committed fixture
`.pyi` + pyright coverage (OQ-3 follow-up).

---

## Increment 30 — default-`FormatterConfig` cross-backend unparser parity (§4)

Completed design §4's "run with both the default `FormatterConfig` and the fixture
`.fltkfmt`": added a default-config-baked Rust unparser module to the fixture and
extended the parity test to assert Python==Rust over the default `FormatterConfig`
— the "second baked Rust unparser module … + extend the corpus" called out as the
next step in increments 28/29. One semantic unit: the Rust unparser bakes its config
at generation time, so default-config parity *requires* a second baked module; that
module has no independent value (default-config compile was already proven in
increment 24), so the module + its parity coverage are inseparable and ship together
(precedent: increment 28's helper + test). Spans §2.6 (fixture module) + §2.5
(Makefile gencode line) + §4 (parity test) but is one feature — the §4 default-config
parity assertion, with the fixture module purely its mechanism.

- `tests/rust_parser_fixture/src/unparser_default.rs` (new, generated, ~2471 lines):
  generated from `rust_parser_fixture.fltkg` with **no** `--format-config` (default
  `FormatterConfig`), default `--cst-mod-path super::cst`. Raw generator output (no
  `cargo fmt`, per increment 25/27's finding that `make check` has no rustfmt gate for
  these files).
- `tests/rust_parser_fixture/src/lib.rs:4,19`: `pub mod unparser_default;` + a
  `register_submodule(m, "unparser_default", unparser_default::register_classes)` call
  under the existing `#[cfg(feature = "python")] #[pymodule]`. A *distinct* submodule
  (`unparser_default`) holds the default-config `Unparser`/`Doc` pyclasses — the
  separate parent submodule sidesteps the `#[pyclass(name = "Unparser")]` (and `Doc`)
  name reuse with the `.fltkfmt`-baked `unparser` submodule (they are different Rust
  types in different Python module namespaces, so no registration collision).
- `Makefile:287-288`: a `gencode` line regenerating `unparser_default.rs` via
  `$(MAKE) gen-rust-unparser GRAMMAR=… RS_OUT=…` with **no** `EXTRA_ARGS` (default
  config), mirroring the existing fixture unparser line minus `--format-config`.
- `tests/test_rust_unparser_parity_fixture.py`: module docstring rewritten to describe
  both configs; added `_py_unparser_result_default_cached()` (Python unparser via
  `generate_unparser(grammar, cst_module_name)` — no `formatter_config`, so it defaults
  to `FormatterConfig()`, matching the Rust `unparser_default.rs`); added
  `test_unparse_parity_default` parametrized over the **same** shared `_CORPUS` × the
  same two `_CONFIGS` (wide 80/4, narrow 8/2), comparing the Python default-config
  unparser vs `rust_parser_fixture.unparser_default.Unparser()`, reusing
  `assert_unparse_parity` from `tests/unparser_parity.py` unchanged.

Verification:
- `cargo clippy -D warnings --all-targets` clean on the fixture for both feature sets
  (`--features python` and `--no-default-features`); `make check-no-pyo3` still holds
  (the new module's pyo3 is in the `python`-gated generated code; the unparser-core dep
  is pyo3-free, so the default graph stays pyo3-free).
- Native `cargo test --no-default-features` on the fixture: 68 passed (unchanged — the
  new module adds no native tests, only links).
- `uv run pytest tests/test_rust_unparser_parity_fixture.py`: 148 passed (74 `.fltkfmt`
  + 74 default). ruff check + ruff format --check + pyright clean on the changed Python.
- Gencode-drift: regenerating `unparser_default.rs` via the Makefile's CLI produces a
  byte-stable file.

Notes:
- The shared corpus is reused verbatim for both configs (design §4: "a shared corpus of
  `(rule, text)` … run with both"); the inputs parse identically, only the baked
  formatting differs, so the same `(rule, text)` pairs exercise both backends' default-
  config flat-vs-break decisions.
- Remaining design work: the committed fixture `.pyi` + pyright coverage (OQ-3
  follow-up) — the generator + CLI already emit the `.pyi` (increment 26) and a
  generator test `ast.parse`s it; committing a fixture `.pyi` and pyright-checking it
  against a CST protocol module (the `gsm2tree_rs` `cst.pyi` precedent) is the last
  piece.

---

## Increment 31 — committed fixture `.pyi` + pyright coverage (OQ-3 follow-up)

The last remaining design item (per increment 30's closing note): commit the fixture
unparser's `.pyi` and bring it under pyright coverage, mirroring the CST backend's
committed `fltk/_stubs/fegen_rust_cst/cst.pyi` + `fltk.fegen.fltk_cst_protocol`
precedent. The generator/CLI already emit the `.pyi` (increment 26); this commits a
concrete one, supplies the CST protocol module it types `node` against, wires
regeneration into `gencode`, and adds consumer-facing pyright tests.

- `tests/rust_parser_fixture_cst_protocol.py` (new, committed): the fixture grammar's
  Python CST **protocol** module — the typing source the unparser `.pyi` annotates each
  `node` against (`_proto`). It is self-contained (stdlib + `fltk.fegen.pyrt` only; does
  not embed `cst_module_name`). `generate` also emits `cst.py` + two parsers, but the
  Rust backend supplies cst/parser, so only the protocol is committed.
- `fltk/_stubs/rust_parser_fixture/unparser.pyi` (new, committed): the unparser `.pyi`
  for the `.fltkfmt`-baked `unparser` submodule, typed against
  `tests.rust_parser_fixture_cst_protocol`. Under `fltk/_stubs` (pyright `extraPaths`)
  and `fltk/` (pyright `include`), so `make typecheck` checks it.
- `fltk/_stubs/rust_parser_fixture/__init__.pyi` (new): stub-package marker (mirrors
  `fltk/_stubs/fegen_rust_cst/__init__.pyi`).
- `Makefile` `gencode`: (a) a protocol-module step that runs `generate` into a temp dir
  and copies only `rust_parser_fixture_cst_protocol.py` to `tests/` (keeps gencode
  output to exactly the committed file, no untracked leftovers); (b) the fixture
  `unparser.rs` line's `EXTRA_ARGS` extended with
  `--protocol-module tests.rust_parser_fixture_cst_protocol --pyi-output
  fltk/_stubs/rust_parser_fixture/unparser.pyi`. The gencode tail's `ruff` normalization
  makes both committed files gate-clean; both verified byte-stable on regeneration.
- `tests/test_rust_unparser_pyi.py` (new): consumer-facing pyright coverage via
  `pyright_test_utils` — a correct consumer of `rust_parser_fixture.unparser` is
  pyright-clean (`unparse_num -> str | None`, `unparse_num_doc -> Doc | None`,
  `Doc.render`), and a misuse (`int` where `_proto.Num` is required) is a
  `reportArgumentType` error (proves the stub constrains, not `Any`). Plus an
  artifact-existence guard. Runs off the committed `.pyi` alone (no built extension).

Deviation from design / increment 26:
- **`generate_pyi` now emits PEP 604 `X | None` and drops `import typing`**
  (`fltk/unparse/gsm2unparser_rs.py` `generate_pyi`). Increment 26 chose
  `typing.Optional[...]` "to match the CST `.pyi`", but that reasoning was off: the
  committed CST `.pyi` carries `| None` (post-`ruff --fix`) and keeps `import typing` for
  *other* names (`Literal`/`Iterable`). The unparser `.pyi` uses `typing` *only* for
  `Optional`, so `ruff` rewrites `Optional` → `| None` and then leaves `import typing`
  unused — an F401 that `ruff` does **not** auto-fix in a stub, making the committed stub
  fail `make check`. Emitting the union directly keeps the raw generator output
  gate-clean for *every* downstream consumer's committed stub, not just the fixture.
  Updated the 4 affected `generate_pyi` tests in `tests/test_rust_unparser_generator.py`.

Notes:
- Protocol module home is `tests/` (fixture artifacts live there); the unparser `.pyi`
  under `fltk/_stubs` references it as `_proto`. pyright *checks* the committed `.pyi`
  (under `fltk/`) and *resolves* the protocol module + consumer test under `tests/`
  (not in the `include` set).
- One `.pyi` for the `unparser` submodule only (not also `unparser_default`): the two
  submodules have an identical Python surface (only baked formatting differs, which
  lives in `.rs`, not the stub), so a single committed stub dogfoods OQ-3.
- No `.rs` drift: only `generate_pyi` changed; `generate()` output for both fixture
  unparser modules is byte-identical (verified).

`make check` passes (full gate: lint, format-check, typecheck, test, all cargo lanes,
check-no-pyo3, cargo-deny).

**Design complete.** All sections are accounted for: §2.1 core crate (incs 1–5),
§2.2 generator walk + trivia (incs 6–20), §2.3 PyO3 wrapper (inc 21), §2.4 API
contract (incs 21/25), §2.5 CLI/Makefile/LibSpec (incs 22–24, 27, 31), §2.6 fixture +
`.fltkfmt` (incs 24, 27, 31), §3 edge cases (throughout), §4 tests (incs 28–30 + this
increment's pyright tests), and the answered open questions OQ-1 (recursive
resolve/render kept; iterative `Doc::drop`, inc 1), OQ-2 (intermediate `Doc` exposed,
inc 25), OQ-3 (`.pyi` emitted inc 26; committed fixture stub + pyright coverage, this
increment).
