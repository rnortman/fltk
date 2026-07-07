# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks). Re-open only with profiling evidence.

## `fmt-cli-per-consumer-version`

`fltk-fmt-cli`'s `FmtArgs` carries `#[command(version)]`, which clap expands to `CARGO_PKG_VERSION` where `FmtArgs` is defined — the scaffolding crate — so every consumer binary reports `fltk-fmt-cli`'s version, not its own. This is an observable defect today: `fltkfmt` is `0.1.0` (`crates/fltkfmt/Cargo.toml`; deliberately outside the root workspace with its own `[workspace]`), while `fltk-fmt-cli` is `0.2.0` (`crates/fltk-fmt-cli/Cargo.toml`), so `fltkfmt --version` prints `0.2.0` for a `0.1.0` binary. Fix by threading `version` (and possibly `name`) through `run_main` / `fltk_formatter_main!` the same way `about` is threaded (commit for `fmt-cli-per-consumer-about`), so `<consumer> --version` prints the consumer's own version. Do NOT add a second bare `&'static str` positional argument next to `about` on `run_main`: two adjacent indistinguishable string params can be swapped silently (a version string rendered as the `--help` description). Introduce an identity struct instead (e.g. `FormatterInfo::new(about).version(..)`, keeping `about` required) so this fix — and any later per-consumer knob — is a non-breaking addition rather than another signature break. Location: `crates/fltk-fmt-cli/src/lib.rs` (`#[command(version)]` on `FmtArgs`, and `run_main`).

## `lsp-cst-text-helpers`

`fltk/lsp/lsp_config.py`'s `_span_text` / `_identifier_text` and the inline literal-extraction
sequence in `_parse_anchor` duplicate helpers that already exist for `.fltkfmt`:
`fltk/unparse/fmt_config.py` (`_span_text`, `_extract_identifier_text`, `_extract_literal_text`)
and the more careful `fltk/unparse/pyrt.py:extract_span_text` (which guards against a
source-bearing span whose `text()` returns `None` — a guard the `fmt_config` and `lsp_config`
copies both lack). There is also a fourth single-backend copy at `fltk/fegen/fltk2gsm.py`
(`Cst2Gsm._span_text`). Consolidate into one canonical, `SpanProtocol`-typed helper (dropping
the `hasattr` probe and `type: ignore`s now that `SpanProtocol` includes `text()`), keeping the
pyrt source-bearing guard, and migrate all copies to it. Deferred because it touches out-of-round
modules (`fmt_config`, `unparse.pyrt`). Location: `fltk/lsp/lsp_config.py` (`_span_text`,
`_identifier_text`, `_parse_anchor`).

## `lsp-test-parse-helper`

`fltk/lsp/test_lsp_config.py` (`_load`) and `fltk/lsp/test_lsp_validation.py` (`_parse`) each
hand-roll the same `TerminalSource` → `Parser` → `apply__parse_lsp_spec` → full-consumption
check, diverging only on failure reporting (`_load` renders a caret diagnostic; `_parse`
bare-asserts). The design's `plumbing.parse_lsp_config` wrapper (not yet built) is the intended
home for this sequence; fold both helpers onto it once it lands, rather than building a throwaway
interim shared helper. Location: `fltk/lsp/test_lsp_config.py`, `fltk/lsp/test_lsp_validation.py`.

## `formatter-group-idempotency`

The formatter is not idempotent on grouped alternations at narrow widths: `fltk/fegen/test_data/rust_parser_fixture.fltkg` formatted at width 40 / indent 4 changes between pass 1 and pass 2 (a grouped alternation `( inner:rec_via_sub . "+" | inner:atom ) .` re-breaks into a multi-line `(` … `)` block on the second pass), converging only at pass 2. Single-pass cross-backend parity holds, so this is a shared formatter-layout bug present in both the Python and Rust backends, not a backend divergence. Fixing it is a formatter behavior change to both backends and was out of scope for the pure test addition that discovered it (`fltkfmt` integration tests). The idempotency integration test (`crates/fltkfmt/tests/cli.rs`, `format_format_is_format`) carves this one case out explicitly, pinning current behavior (`out2 != out1`, `out3 == out2`); when the formatter is fixed that carve-out's `assert_ne!` trips, forcing its removal alongside this entry. Location: `crates/fltkfmt/tests/cli.rs` (the `TODO(formatter-group-idempotency)` carve-out in `format_format_is_format`); the layout logic lives in the shared unparser/renderer (`fltk/unparse/` and the generated Rust unparser).

## `lsp-classify-hotpath`

`fltk/lsp/classify.py`'s `classify` / `default_tokens` are the per-document hot path the M2
server will sit on. The once-per-grammar table build is now hoisted: `AnalysisEngine` builds a
`_GrammarTables` once in `__init__` and threads it into `classify` via the optional `tables`
parameter, so `highlight` no longer re-walks the grammar and recompiles every terminal regex per
call. Two internal inefficiencies remain, both confined to `classify.py` and neither forcing a
change to the engine seam's signature: (1) `_winner_segments` rescans all intervals per boundary
pair (O(n^2)); a sweep line maintaining the active set reaches the intended O(n log n); (2)
`classify` walks the analysis tree twice (`_explicit_intervals` then `_default_intervals`) — fold
default emission into the explicit walk. Both are the design-stage sweep-line/walk-fusion rewrite
of the interval-resolution core, best batched (shared walk/segment logic). Address before the M2
server ships (it drives `classify` per keystroke), or when profiling on a real grammar shows
`classify` latency dominates. Location: `fltk/lsp/classify.py` (`_winner_segments`, the second
`_default_intervals` loop in `classify`).

## `lsp-rule-surface-index`

`fltk/lsp/lsp_config.py`'s `_index_rule` (`RuleIndex`: labels / literals / invoked rules) and
`fltk/lsp/classify.py`'s `_build_terminal_table` (`_TerminalTable`: literals / regexes,
label-keyed) are two parallel per-rule walks over `rule.alternatives` × `gsm.for_each_item`, each
collecting an overlapping slice of a rule's item surface (literals appear in both). The definition
of "what a rule's items expose to anchors/classification" thus lives in two mirrored walkers in
two modules; the planned INLINE-support change (splicing invoked rules' terminals into the parent
surface) must then be implemented twice, and any drift shows up as validation accepting an anchor
the classifier can't match. Unify into one per-rule surface index (labels, literals, regexes,
invoked rules; label-keyed views derived from it) consumed by validation, resolution, and the
classifier tables. Deferred rather than done in respond-mode because it restructures private
surfaces across two modules; best landed with INLINE support, which is what forces both walks to
change. Location: `fltk/lsp/lsp_config.py` (`_index_rule`), `fltk/lsp/classify.py`
(`_build_terminal_table`).
