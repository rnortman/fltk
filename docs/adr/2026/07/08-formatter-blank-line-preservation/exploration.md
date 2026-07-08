# Exploration: gear-demo blank-line-preservation formatter failure

Context gathered for the designer who will root-cause and fix. This file cites code only; it
draws no conclusions about what the fix should be.

## Reproduction

```
uv run --extra lsp pytest fltk/lsp/test_gear_demo.py -k "preserves or idempotent" -q
```

`test_formatting_preserves_blank_lines_between_items` (`fltk/lsp/test_gear_demo.py:112-127`) fails:
the blank lines that separate `use`/`shape`/`const`/`fn` items in `examples/gear/sample/main.gear`
are gone from the formatted output. `test_formatting_preserves_leading_comment` (`:130-134`) and
`test_formatting_is_idempotent` (`:73-91`) pass. `_gear_formatter()` (`:94-109`) builds the exact
pipeline `fltk/lsp/server.py:766-769` builds: `plumbing.generate_parser` →
`plumbing.parse_format_config_file` → `plumbing.generate_unparser` → `plumbing.parse_text` →
`plumbing.unparse_cst` → `plumbing.render_doc`.

## The two directives and their file order

`examples/gear/gear.fltkfmt:1-9`:

```
ws_allowed: nbsp;
ws_required: nbsp;
preserve_blanks: 1;
trivia_preserve: LineComment;
```

`preserve_blanks: 1;` appears **before** `trivia_preserve: LineComment;`.

Compare the two other committed `.fltkfmt` files that combine both directives, both in the
opposite order (`trivia_preserve` first, `preserve_blanks` second):

- `fltk/fegen/fegen.fltkfmt:1-2`: `trivia_preserve: LineComment, BlockComment;` then `preserve_blanks: 1;`
- `fltk/lsp/test_data/greet.fltkfmt:1-2`: `trivia_preserve: BlockComment, LineComment;` then `preserve_blanks: 1;`

`examples/gear/gear.fltkfmt` is the only committed `.fltkfmt` with `preserve_blanks` listed first.

## Config parsing: `fltk/unparse/fmt_config.py`

`fmt_cst_to_config` (`fltk/unparse/fmt_config.py:818-936`) walks `formatter.children_statement()`
in source order and dispatches each statement type to a `_process_*` handler, `continue`-ing after
the first match per statement (`:830-869`).

- `_process_preserve_blanks_statement` (`:511-527`):
  ```python
  if config.trivia_config is None:
      config.trivia_config = TriviaConfig()
  config.trivia_config.preserve_blanks = count
  ```
  Mutates the existing `TriviaConfig` in place (or creates one with defaults first).

- `_process_trivia_preserve_statement` (`:496-508`):
  ```python
  config.trivia_config = TriviaConfig(preserve_node_names=node_names)
  ```
  Unconditionally **replaces** `config.trivia_config` with a freshly constructed `TriviaConfig`,
  passing only `preserve_node_names`. `TriviaConfig` (`:42-59`) declares
  `preserve_blanks: int = 0` as a dataclass field default, so the new object's `preserve_blanks`
  is `0` regardless of what the old object held.

For `gear.fltkfmt`'s order: `preserve_blanks: 1;` sets `trivia_config.preserve_blanks = 1` on a
fresh `TriviaConfig()`; the very next statement, `trivia_preserve: LineComment;`, replaces that
object wholesale with `TriviaConfig(preserve_node_names={"LineComment"})`, whose `preserve_blanks`
is back to `0`. The final `FormatterConfig.trivia_config.preserve_blanks` is `0`.

Confirmed by direct construction:
```python
plumbing.parse_format_config_file(Path("examples/gear/gear.fltkfmt")).trivia_config
# TriviaConfig(preserve_node_names={'LineComment'}, preserve_blanks=0)
```
For `fegen.fltkfmt`'s order (`trivia_preserve` first, `preserve_blanks` second) the final
`preserve_blanks` is `1`, because `_process_preserve_blanks_statement` mutates in place rather
than replacing.

## Where `preserve_blanks` is consumed at codegen time: `fltk/unparse/gsm2unparser.py`

`_gen_trivia_processing` (`gsm2unparser.py:1083-1439`) is the single place that emits spacing
between grammar items for `WS_REQUIRED`/`WS_ALLOWED` separators (`:1097-1098` guards this; `NO_WS`
returns immediately). It branches on whether the containing rule is itself the trivia rule
(`rule.is_trivia_rule`, `:1102`, using the generic `Regex(r"[\s]+")` span-child representation from
`add_trivia_rule_to_grammar`, `fltk/fegen/gsm.py:477-504`) vs. an ordinary rule whose sequence has
a `Trivia`-typed CST child interleaved (`:1264` onward, general case).

In both branches, `preserve_blanks` is read as a **generation-time constant**:
```python
preserve_blanks = 0
if self.formatter_config.trivia_config:
    preserve_blanks = self.formatter_config.trivia_config.preserve_blanks
```
(`:1166-1169` trivia-rule branch; `:1351-1354` general branch — reads the bare
`trivia_config.preserve_blanks` field directly, not the rule-aware
`FormatterConfig.get_preserve_blanks(rule_name)` method defined at `fmt_config.py:309-329`, which
also exists but is never called by either unparser generator per the `gsm2unparser_rs.py:1249-1250`
/ `:1341-1342` docstrings quoted below).

`if preserve_blanks > 0:` (`:1171` and `:1359`) is the *only* place the generator emits code that
checks `newline_count >= 2` and calls `_add_separator_spec(..., spacing=HardLine(blank_lines=preserve_blanks), ...)`
(`:1180-1187`, `:1368-1375`). When `preserve_blanks == 0` at generation time, neither branch's
`if` is emitted at all — the generated method for that rule has no blank-line-detection code path,
only the "preserve line structure" (single `HARDLINE`) and "default spacing" arms
(`:1216-1241`, `:1403-1410`).

`_gen_count_newlines_in_trivia_method` (`:970-1063`) generates `_count_newlines_in_trivia`
(used by the general, non-trivia-rule branch) unconditionally regardless of `preserve_blanks`.

### Confirmed via generated source for the gear grammar

`plumbing.generate_unparser_source(grammar, cst_module_name, config)` was dumped to
`/tmp/.../scratchpad/gear_unparser.py` (225KB). `grep -n "blank_lines\|preserve_blanks"` over that
file matches **only** the `_count_newlines_in_trivia` method definition (`gsm2unparser.py:32` in
the dump) — zero call sites and zero `HardLine(blank_lines=...)`/`HARDLINE_BLANK` emissions
anywhere in the generated unparser for this grammar+config pair, consistent with
`trivia_config.preserve_blanks == 0` at generation time.

## Where the blank-line trivia actually lives in the CST

Dumped the parsed CST for `examples/gear/sample/main.gear` (`file` rule). The blank line between
`use ...;` and `shape Wheel {` is captured as `text[102:104] == "\n\n"`, held in a `Ws` span inside
a `Trivia` node that is the **last child of the `UseStmt` node itself** — not a sibling of `ITEM`
in `File.children`. This is because `use_stmt := ... . ";" , ;` (`examples/gear/gear.fltkg:8`) ends
with a trailing `,` (`Separator.WS_ALLOWED`), so `Items.sep_after` for `use_stmt`'s last item (`;`)
is processed inside `unparse_use_stmt__alt0` itself (`gen_alternative_unparser`,
`gsm2unparser.py:1669-1673`, loop bound `item_idx < len(items.items) and item_idx < len(items.sep_after)`),
consuming the trailing whitespace (including the blank line) as part of `use_stmt`'s own
`unparse_use_stmt` call before that accumulator is merged into `file`'s via
`accumulator.add_accumulator(child_result.accumulator)` (`unparse_file__alt0__item0__inner`, dumped
source `:105-116`).

By contrast, `_gen_quantified_item_body` (`gsm2unparser.py:537-627`, generated as
`unparse_file__alt0__item1` for `item*`, dumped source `:118-140`) loops over repeated `item`
occurrences with **no** call to `_gen_trivia_processing` between iterations — each iteration only
extracts the next `ITEM`-labeled child and advances `pos` by exactly one CST-child slot. This
matches the fact above: inter-item trivia is captured inside the *preceding* item's own trailing
separator, not as a `file`-level sibling, so the quantified loop never needs to consume it itself
for this grammar. (Whether this generalizes to grammars where a quantified item's own inner rule
has no trailing separator was not checked further — out of scope for this fact-gathering pass.)

## Confirmed end-to-end effect on the Doc tree

Isolated call to `unparser.unparse_use_stmt(use_stmt_node)` (bypassing render) on the gear pipeline:

Raw (pre-`resolve_spacing_specs`) doc, tail:
```
..., Text(';'), AfterSpec(HardLine), SeparatorSpec(spacing=Nbsp, preserved_trivia=None, required=False)
```
Resolved doc, tail:
```
..., Text(';'), HardLine
```
i.e. plain `HardLine` (single newline, no blank), not `HardLine(blank_lines=1)`. This is consistent
with the generated-source finding above: the trailing separator after `;` in `use_stmt` falls
straight to the "no newlines detected" / default-spacing arm (`SeparatorSpec(spacing=NBSP, ...)`,
since `ws_allowed: nbsp;` is gear's global default, `gear.fltkfmt:1`) because the
`if preserve_blanks > 0:` branch was never generated for this rule.

## `resolve_spacing_specs`: how `AfterSpec + SeparatorSpec` merge when both carry `HardLine`

`fltk/unparse/resolve_specs.py`, `_mutate_after_sep` (`:350-380`): when `sep_spec.spacing` is a
`HardLine` with `blank_lines > 0` and `after_spec.spacing` is a `HardLine` with fewer (or is not a
`HardLine`), the separator's larger-blank-lines `HardLine` wins (`:368-374`). This merge logic
*would* propagate a `HardLine(blank_lines=1)` SeparatorSpec correctly against the
`after ";" { hard; }` global `AfterSpec(HARDLINE)` (`gear.fltkfmt:15`) — it was not exercised here
only because the SeparatorSpec never carried `blank_lines>0` in the first place, per above.

## Rust backend: `fltk/unparse/gsm2unparser_rs.py`

Shares `fltk/unparse/fmt_config.py` — no separate Rust-side config module, so the `TriviaConfig`
replacement in `_process_trivia_preserve_statement` affects both backends identically; a
Rust-generated unparser for `gear.fltkfmt` would read the same `trivia_config.preserve_blanks == 0`.

Structural mirror of the Python trivia/blank-line logic, with explicit divergence notes:

- `_get_preserve_blanks` (`:1553-1562`): docstring states it "Reads the *global*
  `trivia_config.preserve_blanks` exactly as the Python backend does (`gsm2unparser.py:1168`/`:1341`),
  not the rule-aware `get_preserve_blanks`" — i.e. the same generation-time-constant, non-rule-aware
  read as the Python backend, deliberately mirrored.
- Blank-line branch generation: `:1254` (trivia-rule branch, mirrors `gsm2unparser.py:1171`) and
  `:1348`/`:1396-1403` (general branch, mirrors `gsm2unparser.py:1359`/`:1368-1375`).
- `:1240` and `:1323`/`:1391-1395` docstrings explicitly describe the `preserve_blanks == 0` vs `> 0`
  arms and note the trivia-rule branch preserves single-newline line structure even at
  `preserve_blanks == 0` while the non-trivia branch's `== 0` arm does not — parity comments citing
  exact Python line numbers throughout, confirming the two generators are meant to behave
  identically for this feature.

## Existing tests: what is and isn't covered

`fltk/unparse/test_unparser.py:979-1150+` (`test_preserve_blanks_default_collapses_blanks`,
`test_preserve_blanks_one_normalizes_to_single_blank`, `test_preserve_blanks_no_source_blanks_no_output_blanks`,
`test_preserve_blanks_two_normalizes_to_two_blanks`) all either:
- parse a format-config string with `trivia_preserve:` listed **before** any `preserve_blanks`
  usage and no `preserve_blanks:` statement at all (`:994-999`, the "default" test), or
- load `fegen.fltkfmt` (`trivia_preserve` first, `preserve_blanks` second — the non-clobbering
  order) and then **override** `fmt_config.trivia_config.preserve_blanks = 1` directly in Python
  (`:1043`, `:1087`, and the `preserve_blanks: 2` test at `:1128`), bypassing
  `fmt_cst_to_config`'s statement-order handling entirely for the actual value used.

`tests/test_rust_unparser_generator.py:1812-1849` (`test_trivia_rule_preserve_blanks_emits_blank_line_branch`)
and `:1955-2000` (`test_non_trivia_rule_preserve_blanks_emits_blank_line_branch`) both construct
`FormatterConfig(trivia_config=TriviaConfig(preserve_blanks=2))` directly as a Python object
(`:1819`, `:1963`), not via `parse_format_config`/`fmt_cst_to_config`.

No existing test parses a `.fltkfmt` text/file where a `preserve_blanks:` statement precedes a
`trivia_preserve:` statement and then asserts on the resulting `trivia_config.preserve_blanks`
value or on rendered blank-line output. `examples/gear/gear.fltkfmt` is the first committed
artifact with that statement order, and `test_formatting_preserves_blank_lines_between_items`
(added in the "gear demo" work) is the first test exercising it through the full
`parse_format_config_file` → render pipeline.

## Other requested surfaces, briefly

- `fltk/plumbing.py`: `generate_parser` (`:91-167`), `parse_text` (`:170-215`),
  `parse_format_config`/`parse_format_config_file` (`:218-269`), `_assemble_unparser_module`
  (`:314-340`, single source of truth for the unparser-assembly steps — trivia-rule injection via
  `gsm.add_trivia_rule_to_grammar`/`gsm.classify_trivia_rules` then `gsm2unparser.generate_unparser`),
  `generate_unparser`/`generate_unparser_source` (`:343-399`), `unparse_cst` (`:402-433`, calls
  `resolve_spacing_specs` on the raw doc before returning), `render_doc` (`:436-447`).
- `fltk/lsp/server.py`: `_ensure_format_pipeline` (`:751-775`) builds parser+unparser once per
  session via exactly `plumbing.generate_parser` / `plumbing.generate_unparser` with
  `self._formatter_config`; `_format_blocking` (`:777-821`) runs parse → unparse_cst → render_doc →
  reparse-verify, discarding edits (returning `None`) on any exception or reparse failure at
  `:790-813` — a blank-line loss would not surface as a pipeline error, only as silently-wrong
  output, since the reparsed-and-collapsed text still parses successfully.
- `fltk/unparse/combinators.py`: `HardLine.blank_lines` field (`:63-72`) is the sole carrier of
  blank-line count; `HARDLINE`/`HARDLINE_BLANK` singletons (`:135-136`) and `hardline(blank_lines)`
  helper (`:153-159`).
- `fltk/unparse/renderer.py`: `HardLine` rendering (`:117-120`) emits `1 + blank_lines` consecutive
  `break_line()` calls — the only place blank-line count becomes actual blank output lines.
- `fltk/fegen/gsm.py`: `add_trivia_rule_to_grammar` (`:477-504`) synthesizes the default `_trivia`
  rule (`Regex(r"[\s]+")`, single required item, `Separator.NO_WS` after) when the grammar doesn't
  define its own (gear's grammar does define its own, `examples/gear/gear.fltkg:45-47`:
  `_trivia := ( ws | line_comment )+ ;`). `classify_trivia_rules` (`:348-379`) marks
  trivia-reachable rules via `_mark_trivia_reachable`/`_mark_trivia_reachable_in_items`
  (`:382-403`) and validates separation/non-nilness (`validate_trivia_separation`,
  `validate_trivia_rule_not_nil`, `validate_no_repeated_nil_items`).
