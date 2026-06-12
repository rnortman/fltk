# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `empty-cn-underscore-rule`

Underscore-only rule names (`_`, `__`, etc.) pass `_IDENTIFIER_RE` but `snake_to_upper_camel` collapses them to CN `""`, producing `pub struct  {` (Rust syntax error) with no generation-time diagnostic. Fix: reject rule names whose derived CN is empty — either tighten `_IDENTIFIER_RE` to require at least one `[a-z0-9]` character, or add an explicit post-CN check. Location: `fltk/fegen/gsm2tree_rs.py` (`_IDENTIFIER_RE` definition and per-rule validation in `RustCstGenerator.__init__`).

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks). Re-open only with profiling evidence.


