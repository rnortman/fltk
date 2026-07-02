# Exploration: `TODO(unparser-join-sep-resolve)`

Base commit: `8fd5ecf`.

## Locations

Exactly one code-comment instance, plus the required `TODO.md` entry and three
historical review-doc mentions (not code TODOs):

- `crates/fltk-unparser-core/src/resolve.rs:124-128` — the comment, immediately
  above the `Some(separator.clone())` call site at `resolve.rs:131`, inside
  `expand_joins` (`resolve.rs:96-155`).
- `TODO.md:97-99` — the `## unparser-join-sep-resolve` entry, text matches the
  team-lead's quoted description verbatim.
- `docs/workflow/rust-unparser-backend/dispositions-deep-r1.md:142-143`,
  `docs/workflow/rust-unparser-backend/judge-verdict-deep-r1.md:10-11,97`,
  `docs/workflow/rust-unparser-backend/implementation-log.md:174` — prior
  review-chain artifacts recording the same TODO's creation; not additional
  TODO sites.

## Does the cited code match the description?

Yes. `expand_joins` (`resolve.rs:96-155`) matches on `Doc::Join { docs, separator }`
(`resolve.rs:98`) and iterates `docs` (`resolve.rs:105`). For each element after
the first non-after/before element (tracked via `need_sep`, `resolve.rs:104,137-139`),
when `need_sep && !is_after_before` (`resolve.rs:123`) it pushes a new
`Doc::SeparatorSpec` node whose `preserved_trivia` is `Some(separator.clone())`
(`resolve.rs:129-133`). `separator` is `&Rc<Doc>` (destructured at `resolve.rs:98`
from the `Doc::Join` variant), so `.clone()` is an `Rc` refcount bump — every
emitted `SeparatorSpec` across all gaps points at the identical underlying `Doc`
node (same `Rc::as_ptr`), not a deep copy.

For a plain M-element join with no per-item `after`/`before` annotations, the
first element sets `need_sep = true` without pushing a separator; each of the
remaining M-1 elements triggers exactly one `Some(separator.clone())` push.
So "M-1 `SeparatorSpec`s, each holding a clone of the same `separator` `Rc`" is
accurate for the common case described (`resolve.rs:104-140`).

## Does resolution re-run the full 4-pass pipeline on that subtree once per spec?

Yes, for the typical unannotated-item case. The `SeparatorSpec`'s
`preserved_trivia` is consumed via `resolve_rc(trivia)` in the pattern mutators:

- `mutate_standalone_sep` (`resolve.rs:479-499`, the path hit when a bare
  `SeparatorSpec` sits between two plain docs with no `AfterSpec`/`BeforeSpec`
  neighbor) — `resolve.rs:489-491`.
- `mutate_after_sep` (`resolve.rs:381-405`) and `mutate_sep_before`
  (`resolve.rs:408-432`) — hit only when an `AfterSpec`/`BeforeSpec` immediately
  flanks the separator (per-item spacing annotations); both call `resolve_rc(trivia)`
  at `resolve.rs:395` and `resolve.rs:422` respectively.
- `resolve_spacing` (`resolve.rs:624-645`, reached from `mutate_after_sep_before`
  at `resolve.rs:360-378`) also calls `resolve_rc(trivia)` at `resolve.rs:631`.

`resolve_rc` (`resolve.rs:55-71`) is the full 4-pass pipeline named in the module
doc comment (`resolve.rs:1-17`): `expand_joins` → `extract_all_boundary_specs` →
`resolve_patterns` → `collapse_hardline_sequences`. So each `SeparatorSpec` whose
`preserved_trivia` gets consulted re-invokes all 4 passes on that trivia subtree,
independent of the other M-2 identical invocations.

One qualifier the TODO text doesn't spell out: `mutate_consecutive_specs`
(`resolve.rs:517-619`) can absorb an adjacent `SeparatorSpec`-with-trivia without
calling `resolve_rc` on the one it discards — e.g. "only next has trivia — skip
curr, process next" (`resolve.rs:583-586`) drops `curr` without resolving it,
deferring resolution to the surviving spec. This only reduces the call count
below M-1 when specs end up adjacent (e.g. runs of empty/omitted items); it does
not contradict the M-1 claim for the general non-degenerate case the TODO
describes.

## Is "results are byte-identical every time" true?

`resolve_rc` and everything it calls (`expand_joins`, `extract_all_boundary_specs`,
`extract_boundary_specs`, `resolve_patterns`, `resolve_concat_patterns`, the
`mutate_*` functions, `collapse_hardline_sequences`, `merge_spacing`,
`pick_spacing_with_blank_lines`) are pure structural recursions over the `Doc`
argument passed in — no global/thread-local state, no RNG, no I/O, no
position/index/context parameter threaded in from the caller. Confirmed by
reading the full file (`resolve.rs:1-695`): every helper signature takes only
`&Rc<Doc>` / `&[Rc<Doc>]` / `&VecDeque<Rc<Doc>>` and returns a value derived
solely from that input. Since every gap's `preserved_trivia` is a clone of the
literal same `Rc` (same pointer, same pointee), re-running `resolve_rc` on it
M-1 times is guaranteed by referential transparency to produce M-1 structurally
equal (though separately heap-allocated, since `resolve_rc` builds new `Rc`
nodes rather than returning the input `Rc` unchanged) results. The "byte-identical"
claim holds.

## Is the "deferred: separators are simple docs" claim true?

Yes, confirmed at two independent layers, both predating this TODO:

- Python backend: `gsm2unparser.py:396-426` (`_doc_to_combinator_expr`) has an
  exhaustive `if/elif` over `NIL/NBSP/LINE/SOFTLINE/HARDLINE` sentinels,
  `HardLine`, `Text`, and `Concat` only; anything else (`Group`, `Nest`, `Join`,
  `Comment`) falls through to `raise ValueError(f"Unknown Doc type: {doc}")` at
  `gsm2unparser.py:425-426`. This function is the one used to compile a `Join`'s
  separator to generated code, at both of its call sites
  (`gsm2unparser.py:240`, `gsm2unparser.py:1512`, `gsm2unparser.py:1556`).
- Rust backend: `gsm2unparser_rs.py:1693-1729` (`_doc_to_rust_expr`) is an
  explicit port of the same restriction — its docstring states it "raise[s]
  `ValueError("Unknown Doc type: …")` on anything else -- including `Group`,
  [Nest, Join]" (`gsm2unparser_rs.py:1696`), and `gsm2unparser_rs.py:580,603`
  documents the same parity requirement for spacing generally.

The `Doc` class hierarchy (`fltk/unparse/combinators.py:10-134`) does define
`Group`/`Nest` (subclasses of `ContentWrapper`, `combinators.py:76-101`) and
`Join` (subclass of `DocListWrapper`, `combinators.py:108-116`), so these types
exist in the model but are unreachable as a `Join` separator because the
grammar-to-doc compiler for any spacing/separator position always routes
through `_doc_to_combinator_expr`/`_doc_to_rust_expr`, which reject them. The
`.fltkfmt` grammar itself (`fltk/unparse/unparsefmt.fltkg:70-77`) syntactically
allows a `join_literal`'s `separator` to be any `doc_literal`, including a
nested `join_literal` or `compound_literal` (group/nest) — the restriction is
enforced only at code-generation time, not at parse time, but it is enforced
unconditionally (there is no configuration or grammar construct that reaches
generated Rust/Python code with a compound separator).

Given that restriction, a separator `Doc` reaching `expand_joins` at runtime is
always built from `Nil`/`Nbsp`/`Line`/`SoftLine`/`HardLine`/`Text`/`Concat`
only — i.e., a flat or shallow tree with no `Group`/`Nest`/`Join` nesting. Each
redundant `resolve_rc` call's cost is bounded by the leaf count of that shallow
subtree (a small constant in practice, typically 1-3 nodes such as `Text(",")`
or `Concat([Text(","), Line])`), not by the join's element count `M`. So the
per-gap redundant cost is small and constant; the *aggregate* waste across the
whole join is `O(M · c)` for small constant `c` — linear in join length, same
asymptotic order as the unavoidable per-gap work the pipeline already does, not
a separate quadratic blowup. This matches the TODO's own framing ("cost scales
with join length... each redundant run is small") rather than contradicting it.

## Summary of fact-check

- Code matches the TODO's description exactly, including the precise
  M-1-clones-of-one-`Rc` mechanism and the `Some(separator.clone())` site.
- The determinism/byte-identical claim is true by construction (pure functions,
  same `Rc` pointer in every gap).
- The "simple docs only" deferral claim is true and independently verifiable at
  two call sites (Python and Rust backends), both predating this TODO, with no
  bypass path found.
- Only one `TODO(unparser-join-sep-resolve)` code comment exists in the tree;
  `TODO.md` has the matching single entry; slug join is consistent.
