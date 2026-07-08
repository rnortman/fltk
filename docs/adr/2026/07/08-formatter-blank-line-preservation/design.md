# Design: formatter blank-line preservation — two-part root cause

Status: revised after design review r1. Both defects and the combined fix were verified by
execution on this checkout (see §2, "End-to-end verification").
Exploration: `docs/adr/2026/07/08-formatter-blank-line-preservation/exploration.md`.
Failing test: `fltk/lsp/test_gear_demo.py::test_formatting_preserves_blank_lines_between_items`.

## 1. Root cause — two independent defects, both required for the fix

### 1a. `.fltkfmt` statement-order clobbering (shared config layer)

`fmt_cst_to_config` (`fltk/unparse/fmt_config.py:818-936`) processes `.fltkfmt` statements in
source order, and the two trivia-related handlers disagree about ownership of
`FormatterConfig.trivia_config`:

- `_process_preserve_blanks_statement` (`fmt_config.py:511-527`) **mutates** the existing
  `TriviaConfig` in place (creating a default one if absent) and sets `preserve_blanks`.
- `_process_trivia_preserve_statement` (`fmt_config.py:496-508`) **replaces** the whole object:

  ```python
  config.trivia_config = TriviaConfig(preserve_node_names=node_names)
  ```

  `TriviaConfig.preserve_blanks` defaults to `0` (`fmt_config.py:59`), so the replacement
  silently discards any previously parsed `preserve_blanks` value.

`examples/gear/gear.fltkfmt:8-9` lists `preserve_blanks: 1;` **before**
`trivia_preserve: LineComment;` — the only committed `.fltkfmt` with that order — so the final
config is `TriviaConfig(preserve_node_names={'LineComment'}, preserve_blanks=0)`.

Both unparser generators read `trivia_config.preserve_blanks` as a **generation-time constant**
(`fltk/unparse/gsm2unparser.py:1166-1171` and `:1351-1359`; Rust mirror
`fltk/unparse/gsm2unparser_rs.py:1553-1562`). With the value `0`, the
`newline_count >= 2 → HardLine(blank_lines=N)` branch is never emitted into the generated
unparser at all.

Minimal reproduction (no editor, no gear pipeline), verified by execution:

```python
from fltk import plumbing

plumbing.parse_format_config("preserve_blanks: 1;\ntrivia_preserve: LineComment;\n").trivia_config
# TriviaConfig(preserve_node_names={'LineComment'}, preserve_blanks=0)   <-- clobbered

plumbing.parse_format_config("trivia_preserve: LineComment;\npreserve_blanks: 1;\n").trivia_config
# TriviaConfig(preserve_node_names={'LineComment'}, preserve_blanks=1)   <-- correct
```

### 1b. Generated newline counting is blind to node-wrapped whitespace (both generators)

Fixing 1a alone leaves the pinned test red — verified by execution: with `preserve_blanks = 1`
reaching generation time, the generated gear unparser *does* contain the blank-line branch
(`elif self._count_newlines_in_trivia(trivia_node) >= 2: ...`), but at runtime
`_count_newlines_in_trivia` returns `0` for gear's trivia, so every inter-item gap still falls
to the default-spacing arm and the blank lines still collapse.

The generated `_count_newlines_in_trivia` (from `_gen_count_newlines_in_trivia_method`,
`gsm2unparser.py:970-1063`; Rust mirror `gsm2unparser_rs.py:1501-1551`) counts newlines only in
**direct `Span` children** of the `Trivia` node:

```python
if fltk.unparse.pyrt.is_span(trivia.children[idx][1]):
    count = count + self._count_newlines(trivia.children[idx][1])
```

Gear defines its own trivia rule with a *named* whitespace rule
(`examples/gear/gear.fltkg:45-46`: `_trivia := ( ws | line_comment )+ ;` /
`ws := chars:/\s+/ ;`), so an inter-item blank line is a `Ws` **node** child of `Trivia`
(verified on the parsed sample: `Trivia.children == [(Label.WS, Ws(... Span(102,104) "\n\n"))]`),
not a direct span — `is_span` is false, the count is `0`. Grammars whose trivia captures
whitespace as unlabeled direct `Span` children (e.g. `fltk/fegen/fegen.fltkg:19`, and the
synthesized default trivia rule from `gsm.add_trivia_rule_to_grammar`, `fltk/fegen/gsm.py:477-504`)
are unaffected, which is why every existing `preserve_blanks` test passes.

### Why the existing tests missed both defects

Every existing `preserve_blanks` test either uses the non-clobbering statement order or bypasses
config parsing by constructing/overwriting `TriviaConfig` directly in Python
(`fltk/unparse/test_unparser.py:994-1128`, `tests/test_rust_unparser_generator.py:1819`,
`:1963`) — so 1a was invisible. And every one of them runs on fegen or on toy grammars with
direct-`Span` trivia children — so 1b was invisible too. `test_formatting_is_idempotent` cannot
catch either, because collapsing blanks is idempotent.

## 2. Fix — two components

### Component A: config layer (`fltk/unparse/fmt_config.py`)

Change `_process_trivia_preserve_statement` to mutate `trivia_config` in place, symmetric with
`_process_preserve_blanks_statement`:

```python
def _process_trivia_preserve_statement(...):
    ...
    if config.trivia_config is None:
        config.trivia_config = TriviaConfig()
    config.trivia_config.preserve_node_names = node_names
```

Semantics the config language now guarantees:

- **Each directive owns its own field.** `trivia_preserve:` sets `preserve_node_names`;
  `preserve_blanks:` sets `preserve_blanks`. Statement order between the two is irrelevant.
- **Repeated occurrences of the same directive: last one wins** (unchanged from today's
  behavior for `trivia_preserve`, and already true for `preserve_blanks`).

### Component B: whitespace-aware trivia newline counting (both generators)

Extend the generated `_count_newlines_in_trivia` so a trivia child contributes newlines when it
is **either** a direct `Span` (unchanged) **or** a node whose full source text is non-empty and
entirely whitespace. Nodes containing any non-whitespace (comments) contribute nothing — this is
what keeps gear's `line_comment` terminator (`nl:"\n"`, `gear.fltkg:47`) from being miscounted
as blank-line evidence.

The whitespace-only test is a **runtime** check on the child node's span text, not a
generation-time classification of "whitespace rules" (deciding from the grammar whether a rule's
regexes can only match whitespace would require regex analysis and would misclassify; the
runtime check is exact, cheap, and identical in both backends). A node whose span text is empty
or contains non-whitespace counts `0` — i.e. degrades to today's behavior, never over-counts.

- **Python** (`gsm2unparser.py:970-1063`): add a pyrt runtime helper (following the existing
  delegation pattern of `count_span_newlines`/`is_span`, `fltk/unparse/pyrt.py:72-99`), e.g.
  `count_whitespace_newlines(child, terminals)`: span → `count_span_newlines` (unchanged
  semantics); node → extract the node's `span` text via `extract_span_text` (handles both span
  backends), return its newline count iff the text is non-empty and all-whitespace, else `0`.
  The generated loop body becomes a single unconditional
  `count += pyrt.count_whitespace_newlines(child, self.terminals)` — less iir codegen than the
  current `is_span` conditional.
- **Rust** (`gsm2unparser_rs.py:1501-1551`): the generator knows the `TriviaChild` variants at
  generation time; emit an arm per node-typed variant alongside the existing `Span` arm. Nodes
  expose `span()` (`fltk/fegen/gsm2tree_rs.py:1182`) and `Span::text_str()` (already used by the
  existing counter): count `t.matches('\n').count()` iff
  `!t.is_empty() && t.chars().all(char::is_whitespace)`. Carry the usual parity comments citing
  the Python lines, as the rest of `gsm2unparser_rs.py` does.

### End-to-end verification (prototype, run on this checkout)

The full fixed pipeline was exercised before sign-off: component A simulated by setting
`preserve_blanks = 1` on the parsed gear config, component B by patching the generated
unparser's `_count_newlines_in_trivia` with exactly the whitespace-only-node semantics above.
Result over `examples/gear/sample/main.gear`: all four inter-item blank lines preserved
(`\n\nshape Wheel {`, `\n\nconst SPOKES`, `\n\nfn rim_area`, `\n\nfn total_area`), leading
`// gear` comment preserved, output idempotent under re-formatting, and the formatted output
reparses. Component A alone was also run and confirmed insufficient (all blanks still
collapsed), pinning that both components are required.

No resolver change is needed: `resolve_specs._mutate_after_sep`
(`fltk/unparse/resolve_specs.py:350-380`) already merges the `HardLine(blank_lines=1)`
SeparatorSpec correctly against gear's `after ";" { hard; }` AfterSpec (larger blank count wins),
as the verified prototype output demonstrates.

### What is deliberately NOT changed

- **`examples/gear/gear.fltkfmt` keeps its current statement order.** Reordering it would mask
  defect 1a and leave every out-of-tree `.fltkfmt` with this order broken. As committed, it is
  the regression artifact that exercises the fixed path.
- **The `preserve_blanks > 0` branch-emission ladders in both generators** (Python
  `gsm2unparser.py:1171`/`:1359`, Rust `gsm2unparser_rs.py:1254`/`:1348`) are untouched; the
  generators change only inside `_gen_count_newlines_in_trivia_method` and its Rust mirror.
- **The trivia-rule branch** (`rule.is_trivia_rule`, `gsm2unparser.py:1102`) is untouched: the
  gear blank-loss path runs through the general (non-trivia-rule) branch, and preserved-trivia
  rendering (comments) is a separate path the prototype confirmed keeps working.
- **`fltk/lsp/server.py` is untouched.** `_ensure_format_pipeline` builds the pipeline from
  `parse_format_config_file` + `generate_unparser`, so it inherits both components.

### Known adjacent gaps, out of scope

- **Rule-level `preserve_blanks` is parsed but never consumed.** `RuleConfig.preserve_blanks`
  (`fmt_config.py:928-933`) and `FormatterConfig.get_preserve_blanks(rule_name)`
  (`fmt_config.py:309-329`) exist, but neither generator calls the rule-aware method — both read
  the global field, a divergence the Rust backend documents deliberately
  (`gsm2unparser_rs.py:1250`, `:1342`, `:1558`). Pre-existing feature gap, not a cause of this
  bug (gear's config has no rule-level `preserve_blanks`). Defer with
  `TODO(rule-preserve-blanks)` in `TODO.md` plus comments at `gsm2unparser.py:1166`/`:1351` and
  `gsm2unparser_rs.py:1553`.
- **A blank line whose second newline is a comment terminator is not detected** on the
  no-preservable-trivia path (e.g. `x // c\n\ny` with comments unpreserved: the comment node
  owns the first `\n`, the whitespace holds only one). This matches the existing
  direct-span-only semantics ("count newlines in whitespace") and is unreachable for gear, whose
  config preserves `LineComment` (comment-bearing trivia takes the preserved path instead). Not
  worth a TODO: no known grammar/config hits it, and "done" would need a semantics decision
  about whether comment terminators are whitespace.

## 3. Cross-backend (Python/Rust) equivalence

Component A lives in `fltk/unparse/fmt_config.py`, the single config layer shared by both
backends (there is no Rust-side config parser), so it fixes both backends identically by
construction. Component B is **not** shared — it is a mirrored change in both generators, so
equivalence there is maintained the way the rest of the trivia codegen maintains it: line-cited
parity comments (`gsm2unparser_rs.py:1240-1403` style) plus mirrored tests. §5 pins each side:
Python behaviorally (rendering tests over a custom-trivia grammar), Rust at the
generated-source level (consistent with the existing `tests/test_rust_unparser_generator.py`
approach, e.g. `:1990-2019`), and a Rust test through the parsed-config path pins that
component A reaches the Rust generator.

## 4. Impact on generated public API / out-of-tree consumers

- **No generated symbol, signature, or type-annotation changes.** `_count_newlines_in_trivia`
  is a private helper inside the generated unparser; component B changes only its body (and, in
  Rust, its match arms). Component A changes which spacing branches get emitted, per the config
  the consumer wrote.
- **Consumer class (a) — statement-order clobbering:** any consumer whose `.fltkfmt` lists
  `preserve_blanks:` before `trivia_preserve:` currently gets `preserve_blanks` silently
  ignored; after regeneration their formatter honors it.
- **Consumer class (b) — custom trivia rules:** any consumer whose grammar wraps whitespace in
  named trivia rules (gear-style `ws := chars:/\s+/`) and sets `preserve_blanks > 0` currently
  has blank lines silently collapse *regardless of statement order*; after regeneration their
  formatter preserves them.
- Both are the documented semantics of the directive (`TriviaConfig.preserve_blanks` docstring,
  `fmt_config.py:55-58`) finally being delivered — bug fixes, not compatibility breaks. A
  consumer could only be "relying" on the old behavior by writing a directive that asks for the
  opposite; formatted-output changes for them are the fix working. No migration action beyond
  the normal regen → `make fix` → commit flow.

## 5. Test plan (TDD order)

New tests are written first and must fail before the fix, except where noted.

### Engine level — config parsing (`fltk/unparse/test_fmt_config.py`) — pins component A

1. `preserve_blanks: 1;` **then** `trivia_preserve: LineComment;` →
   `trivia_config == TriviaConfig(preserve_node_names={"LineComment"}, preserve_blanks=1)`.
   **Fails today.** The 1a root-cause pin.
2. Reverse order → same resulting `TriviaConfig`. Passes today; pins order-independence as an
   invariant rather than an accident.
3. Repeated `trivia_preserve:` statements → last one's node set wins **and** a preceding
   `preserve_blanks` still survives. Pins the "last-wins per field, fields independent"
   semantics of §2.

### Engine level — end-to-end rendering (`fltk/unparse/test_unparser.py`)

4. A `preserve_blanks` rendering test on a direct-span-trivia grammar whose `FormatterConfig`
   comes **entirely from parsed config text** in the clobbering order, asserting blank lines
   survive. **Fails today** (via 1a alone). Closes the parse-path hole; existing
   `test_preserve_blanks_*` tests keep their direct-override style.
5. Rendering tests on a small **custom-trivia grammar**
   (`_trivia := ( ws | line_comment )+ ; ws := chars:/\s+/ ; line_comment := ... . nl:"\n" ;`),
   config from parsed text — pins component B behaviorally:
   a. Blank line between items survives with `preserve_blanks: 1`. **Fails today** even with
      the non-clobbering statement order (1b alone).
   b. A gap containing an unpreserved comment and no blank line in the source renders with no
      blank line — the comment's terminator newline must not be counted as blank-line evidence.
      Guards the whitespace-only rule of §2 Component B.
6. Unit tests for the new pyrt helper (`fltk/unparse/pyrt.py`): span child, whitespace-only
   node child, comment node child, empty-span node child.

### Rust backend (`tests/test_rust_unparser_generator.py`)

7. Parsed-config path: mirror of the existing `*_preserve_blanks_emits_blank_line_branch` tests
   (`:1812`, `:1955`) but with the config built via `plumbing.parse_format_config` on
   clobbering-order text. **Fails today.** Pins that component A reaches the Rust generator.
8. Generated-source pins for component B, extending the existing
   `test_count_newlines_in_trivia_*` tests (`:1990-2019`): a grammar whose `TriviaChild` enum
   has a node-typed whitespace variant must emit the whitespace-only counting arm
   (`chars().all(char::is_whitespace)` over `span().text_str()`), and the Span arm must be
   unchanged. **Fails today.**

### Gear-demo level (`fltk/lsp/test_gear_demo.py`)

9. `test_formatting_preserves_blank_lines_between_items` — already committed and failing;
   becomes the passing integration regression test. No change to it. (The prototype in §2
   already demonstrated it goes green with both components applied.)
10. `test_formatting_is_idempotent` and `test_formatting_preserves_leading_comment` must still
    pass. Idempotency now runs over output that *contains* blank lines; it holds because
    `preserve_blanks: N` normalizes any run of blanks to exactly N
    (`test_preserve_blanks_one_normalizes_to_single_blank` pins the normalization), so
    re-formatting normalized output is a fixed point — confirmed by the prototype run.

### Full-suite regression

`uv run pytest` — in particular `tests/test_fltkfmt_parity.py` (Python-vs-Rust formatter byte
parity over `fegen.fltkfmt`, non-clobbering order, direct-span trivia — must remain green) and
the existing `test_preserve_blanks_*` suites (direct-span counting semantics unchanged).

## 6. Open questions

None. Two judgment calls are resolved in the body: the unconsumed rule-level `preserve_blanks`
is deferred as `TODO(rule-preserve-blanks)` (§2, pre-existing gap orthogonal to this bug), and
the whitespace-only check runs at runtime rather than via generation-time regex classification
(§2 Component B, exactness + backend symmetry).
