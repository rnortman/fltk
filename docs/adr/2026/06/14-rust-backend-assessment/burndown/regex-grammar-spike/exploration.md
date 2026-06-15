# Regex Grammar Spike — Exploration

Codebase survey for the designer laying out the spike for proving `regex.fltkg`
works by generating a parser + CST from it and testing it against real-world and
adversarial regexes.

---

## 1. Makefile codegen targets

File: `Makefile`

### Python codegen (`generate` subcommand)

The canonical Python codegen target is `gencode` (line 247–297).  Each grammar
gets one invocation of:

```
uv run python -m fltk.fegen.genparser generate \
    <grammar.fltkg> <base_name> <cst_module_name> \
    --output-dir <dir>
```

That single call produces four files (line 248–252 comment, lines 250–253):

| file | content |
|---|---|
| `{base_name}_cst.py` | Python CST dataclass module |
| `{base_name}_cst_protocol.py` | Protocol module (type stubs for downstream) |
| `{base_name}_parser.py` | Non-trivia parser |
| `{base_name}_trivia_parser.py` | Trivia-preserving parser |

Concrete examples from `gencode`:

```makefile
uv run python -m fltk.fegen.genparser generate \
    fltk/fegen/fegen.fltkg fltk fltk.fegen.fltk_cst \
    --output-dir fltk/fegen
```

Output: `fltk/fegen/fltk_cst.py`, `fltk/fegen/fltk_cst_protocol.py`,
`fltk/fegen/fltk_parser.py`, `fltk/fegen/fltk_trivia_parser.py`.

### Rust codegen (`gen-rust-cst` / `gen-rust-parser` subcommands)

Makefile lines 220–221 (parametric target):

```makefile
gen-rust-cst:
	uv run python -m fltk.fegen.genparser gen-rust-cst $(GRAMMAR) $(RS_OUT) $(EXTRA_ARGS)

gen-rust-parser:
	uv run python -m fltk.fegen.genparser gen-rust-parser $(GRAMMAR) $(RS_OUT)
```

Usage:

```
make gen-rust-cst GRAMMAR=path/to/grammar.fltkg RS_OUT=path/to/cst.rs
make gen-rust-parser GRAMMAR=path/to/grammar.fltkg RS_OUT=path/to/parser.rs
```

`EXTRA_ARGS` on `gen-rust-cst` accepts `--protocol-module` and `--pyi-output`
(genparser.py lines 270–295).

### `make` orchestration for the spike

The `gencode` target (line 247) applies the pattern of running Python codegen
per grammar, then normalizing with `ruff check --fix` + `ruff format`.  A new
spike grammar target should follow the same shape.  The `build-test-fixtures`
target (line 94) lists all native extension builds that `make test` depends on.

---

## 2. Generator entry points

File: `fltk/fegen/genparser.py`

Top-level CLI: `fltk.fegen.genparser` (`app = typer.Typer(...)`, line 23).

### `generate` command (Python CST + parsers)

`genparser.py:120–252`, function `generate(grammar_file, base_name, cst_module_name,
output_dir, ...)`.

Pipeline (lines 173–244):
1. `parse_grammar_file(grammar_file)` → `gsm.Grammar`
2. `gsm.add_trivia_rule_to_grammar(grammar, context)`
3. `gsm2tree.CstGenerator(grammar, py_module, context).gen_py_module()` → writes
   `{base_name}_cst.py`
4. `cstgen.gen_protocol_module()` → writes `{base_name}_cst_protocol.py`
5. `gsm2parser.ParserGenerator(...).parser_class` compiled → writes
   `{base_name}_parser.py` and `{base_name}_trivia_parser.py`

### `gen-rust-cst` command

`genparser.py:265–362`, function `gen_rust_cst(grammar_file, output_file, ...)`.

Pipeline (lines 334–362):
1. `_parse_grammar_raw(grammar_file)` → raw `gsm.Grammar` (no trivia processing)
2. `gsm2tree_rs.RustCstGenerator(grammar, source_name=...)` — applies trivia
   internally
3. `gen.generate()` → writes `.rs` file; optionally `gen.generate_pyi(...)` →
   writes `.pyi` stub

### `gen-rust-parser` command

`genparser.py:368–397`, function `gen_rust_parser(grammar_file, output_file, ...)`.

Pipeline:
1. `_parse_grammar_raw(grammar_file)` → raw `gsm.Grammar`
2. `gsm2parser_rs.RustParserGenerator(grammar, cst_mod_path=..., source_name=...)`.
3. `gen.generate()` → writes `.rs` file

**Key difference from Python path**: both Rust generators take the raw grammar
(no trivia pre-processing); trivia is added internally by `RustCstGenerator`.
`_parse_grammar_raw` (line 255–262) is distinct from `parse_grammar_file` exactly
for this reason.

---

## 3. Generated artifact layout

### Python artifacts (in-tree examples)

`fltk/fegen/`:
- `fltk_cst.py` — generated from `fegen.fltkg`
- `fltk_cst_protocol.py`
- `fltk_parser.py`
- `fltk_trivia_parser.py`
- `bootstrap_cst.py`, `bootstrap_cst_protocol.py`, `bootstrap_parser.py`,
  `bootstrap_trivia_parser.py` — from `bootstrap.fltkg`

`fltk/unparse/`:
- `toy_cst.py`, `toy_cst_protocol.py`, `toy_parser.py`, `toy_trivia_parser.py`
- `unparsefmt_cst.py`, `unparsefmt_cst_protocol.py`, `unparsefmt_parser.py`,
  `unparsefmt_trivia_parser.py`

### Rust artifacts (in-tree examples)

`crates/fegen-rust/src/`:
- `cst.rs` — generated from `fegen.fltkg`
- `parser.rs` — generated from `fegen.fltkg`

`tests/rust_cst_fixture/src/`:
- `cst.rs` — generated from `fltk/fegen/test_data/phase4_roundtrip.fltkg`

`tests/rust_poc_cst/src/`:
- `cst.rs` — generated from `fltk/fegen/test_data/poc_grammar.fltkg`

`tests/rust_parser_fixture/src/`:
- `cst.rs`, `parser.rs` — generated from `fltk/fegen/test_data/rust_parser_fixture.fltkg`
- `collision_cst.rs`, `collision_parser.rs` — from `collision_fixture.fltkg`

Each Rust artifact set lives in a standalone Cargo crate with its own
`Cargo.toml`; the crate is compiled by `maturin develop` from that crate's
directory (Makefile lines 199, 206, 211, 215).

---

## 4. Test layout

### Fixture grammar files

`fltk/fegen/test_data/`:
- `poc_grammar.fltkg` — 2 rules (`identifier`, `items`), minimal fixture
- `phase4_roundtrip.fltkg` — 6 rules, config grammar (key=value format)
- `rust_parser_fixture.fltkg` — 22+ rules exercising all generator features:
  literals, regexes, quantifiers (+/?/*), WS_REQUIRED, sub-expressions, union
  labels, suppress/include, direct + indirect left recursion, multibyte
- `collision_fixture.fltkg` — collision-detection fixture for multi-grammar cdylib

### Test files using generated parsers

`tests/test_phase4_rust_fixture.py` — imports `phase4_roundtrip_cst`
(pre-built Rust extension); uses `fltk.plumbing.parse_grammar_file`,
`generate_parser`, `parse_text`.  Pattern:

```python
_grammar = parse_grammar_file(_GRAMMAR_PATH)
_pr = generate_parser(_grammar, rust_cst_module="phase4_roundtrip_cst.cst")
result = parse_text(_pr, "foo = 42;", "config")
assert result.success, result.error_message
```

`tests/test_rust_parser_bindings.py` and `test_rust_parser_fixture_bindings.py`
— invoke `apply__parse_<rule>` directly on the Rust parser via Python bindings
(lower-level than `parse_text`).

`fltk/fegen/test_gsm2parser.py` — builds GSM in Python, calls
`create_parser_generator` helper, uses `gsm.Grammar` directly with no `.fltkg`
file.

`fltk/fegen/test_gsm2parser_rs.py` — unit-tests `RustParserGenerator` by
constructing `gsm.Grammar` directly (no `.fltkg` file, no extension module
build); calls `gen.generate()` and asserts on the emitted source string.

### How tests invoke a generated parser on strings

Via `fltk.plumbing`:

```python
from fltk.plumbing import parse_grammar_file, generate_parser, parse_text

grammar = parse_grammar_file(Path("my.fltkg"))
pr = generate_parser(grammar)           # Python backend
result = parse_text(pr, input_text, start_rule_name)
assert result.success
assert result.cst is not None
```

`parse_text` (plumbing.py:300–331): creates `TerminalSource(text)`, instantiates
`pr.parser_class(terminals)`, calls `parser.apply__parse_{rule_name}(0)`, checks
`result.pos == len(terminals.terminals)`.

**Without the extension build step**, the test can use the Python-only backend
(`rust_cst_module=None`, the default) and requires only `maturin develop` for
`fltk._native` (already covered by `make build-native`).

---

## 5. Regex term syntax in `.fltkg` files

Grammar for regex terms is defined in `fltk/fegen/fegen.fltkg` line 13:

```
term :=
  identifier | literal | "/" . regex:raw_string . "/" | "(" , alternatives , ")" ;
```

```
raw_string := value:/([^\/\n\\]|\\.)+/ ;
```

A regex term in a `.fltkg` source file is the body between the outer `/…/`
delimiters.  The `raw_string` rule permits any character except `/`, newline, and
bare `\` — those must be escaped.  The text matched by `raw_string.child_value()`
is the raw regex body (the delimiter slashes are consumed and suppressed by the
`"/"` literals in `term`).

**Self-escaping constraint** (also documented in `regex.fltkg` lines 31–36):
inside a `.fltkg` regex terminal, a literal `/` must be written `\/` and a literal
`\` must be written `\\`, because the `.fltkg` tokenizer scans `raw_string` with
`([^\/\n\\]|\\.)+`.

---

## 6. Programmatic enumeration of regexes in a grammar

### GSM field

`gsm.py:152–153`:

```python
@dataclasses.dataclass(frozen=True, eq=True, slots=True)
class Regex:
    value: str   # ← the verbatim regex body text (outer /.../ stripped)
```

`fltk2gsm.py:168–170` — `Cst2Gsm.visit_regex` populates it:

```python
def visit_regex(self, regex: cst.RawString) -> gsm.Regex:
    span = regex.child_value()
    return gsm.Regex(self._span_text(span))
```

`self._span_text(span)` returns the raw source text of the `raw_string` node's
`value` child span — exactly the regex body without the outer `/…/` delimiters.

### How to enumerate

After `parse_grammar_file(path)` (or `parse_grammar(text)`) returns a
`gsm.Grammar`, walk every `Rule → Items → Item` and recurse into
`Sequence[Items]` sub-expressions.  Any `item.term` that `isinstance(term,
gsm.Regex)` holds `term.value`, the verbatim regex body.

`gsm.py:291–302` provides `_for_each_item(items, visitor)` which already does
the depth-first walk including sub-expressions.  A collector is:

```python
from fltk.fegen import gsm

def collect_regexes(grammar: gsm.Grammar) -> list[str]:
    found: list[str] = []
    def _visit(_idx: int, item: gsm.Item) -> None:
        if isinstance(item.term, gsm.Regex):
            found.append(item.term.value)
    for rule in grammar.rules:
        for alt in rule.alternatives:
            gsm._for_each_item(alt, _visit)
    return found
```

(`_for_each_item` is private-named but lives in `gsm.py`; or inline the walk.)

Rust codegen uses the same field: `gsm2parser_rs.py:757–760` accesses
`term.value` directly:

```python
elif isinstance(term, gsm.Regex):
    idx = self._regex_idx(term.value)
```

---

## 7. The three corpora

### `fltk/fegen/fegen.fltkg`

6 regex terms (extracted by `grep -oP "(?<=/)([^/\n]|\\.)+(?=/)"
fltk/fegen/fegen.fltkg`):

| pattern |
|---|
| `[_a-z][_a-z0-9]*` |
| `([^\/\n\\]\|\\.)+` |
| `("([^"\n\\]\|\\.)+"\|'([^'\n\\]\|\\.)+')` |
| `[^\n]*` |
| `(?:[^*]\|\*+[^\/\*])*` |
| `\*+\/` |

### `docs/adr/2026/06/14-rust-backend-assessment/burndown/regex-portability-lint/regex.fltkg`

The draft allowlist grammar itself.  Its own regex terminals (which must
self-describe the portable subset) include:

| rule | regex body |
|---|---|
| `number` | `[0-9]+` |
| `class_char` | `[^\\\]\[\-\n]` |
| `flag_chars` | `[imsU]+` |
| `class_shorthand` | `[dDwWsS]` |
| `assertion` | `[bB]` |
| `anchor_escape` | `[Az]` |
| `control_escape` | `[nrtfv0a]` |
| `hex_escape.digits` | `[0-9A-Fa-f][0-9A-Fa-f]` |
| `unicode_escape` (8-hex) | `[0-9A-Fa-f]{8}` (written as 8 adjacent `[…]`) |
| `unicode_escape` (4-hex) | `[0-9A-Fa-f]{4}` (written as 4 adjacent `[…]`) |
| `meta_escape` | `[.*+?()\[\]{}|^$\/\\\-]` |
| `literal_char` | `[^.*+?()\[|^$\\{\n]` |

### `~/tps/clockwork/clockwork/dsl/clockwork.fltkg`

Path: `/home/rnortman/tps/clockwork/clockwork/dsl/clockwork.fltkg` (single
`.fltkg` in the repo).

10 regex terms:

| pattern (verbatim body) | rule |
|---|---|
| ` *` | `doc` (leading space-strip) |
| `[^\n]*` | `doc_line` |
| `[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}` | `uuid_spec` |
| `[_a-zA-Z][_a-zA-Z0-9]*` | `identifier` |
| `[0-9]('?[0-9])*` | `nonnegative_integer` |
| `[eE]` | `number` (exponent) |
| `("([^"\n\\]\|\\.)+"\|'([^'\n\\]\|\\.)+')` | `string_literal` |
| ` *` | `clk_generate` (whitespace in parser directive) |

(The `doc` leading-separator pattern and the `clk_generate` whitespace pattern
each appear twice; there are 10 total occurrences, ~6 distinct patterns.)

**Notable portability questions for the clockwork corpus**:
- `\b` (word boundary) appears in the UUID pattern
  (`[0-9a-fA-F]{8}\b-…`). `\b` is admitted by `regex.fltkg`'s `assertion` rule
  (`/[bB]/`) at top level but **only outside a character class**.  In the UUID
  pattern `\b` appears at top level (not inside `[…]`), so it is in the
  `escape_body → assertion` path and is admitted.
- ` *` (space + star) — `" "` is `literal_char` (space is not in the excluded
  set `[^.*+?()\[|^$\\{\n]`), so a bare space followed by `*` is `repetition →
  atom(literal_char) . quantifier(zero_or_more)`.  Portable.
- `'?` — apostrophe in `[0-9]('?[0-9])*` is inside a non-capturing group.
  Apostrophe is a `literal_char` (not in excluded set).  Portable.

---

## 8. How `gsm2parser_rs.py` collects regexes (implementation detail)

`RustParserGenerator.__init__` (gsm2parser_rs.py:74–134) stores:
- `self._regex_patterns: list[str]` — ordered, deduplicated
- `self._regex_index: dict[str, int]` — pattern → index

`_regex_idx(pattern)` (lines 136–141): appends to both structures on first
encounter; returns the index.

`_gen_consume_term` (line 757–760): calls `self._regex_idx(term.value)` for
every `gsm.Regex` term encountered during code generation.  The same walk
therefore both collects regexes and generates the `consume_regex(pos, idx)` call.

The emitted Rust contains a `REGEX_PATTERNS: [&str; N]` constant (line 304) and
a `REGEX_CELLS: [OnceLock<Regex>; N]` (line 307); `regex_at(idx)` initializes
lazily (lines 296–311 region).

---

## 9. Open factual questions

- **`regex.fltkg` self-compilation**: the grammar's own internal regexes (e.g.
  `[imsU]+`, `[dDwWsS]`, `[nrtfv0a]`, `[0-9]+`) must themselves pass the
  `regex.fltkg` portability check.  A quick scan suggests they do, but this
  should be verified programmatically as part of the spike.
- **Empty-pattern handling**: `regex.fltkg` line 53 comment states "an empty
  pattern is handled by the caller (`check_regex_portable` treats `""` as
  portable)".  No such `check_regex_portable` function exists in the committed
  code — it is anticipated spike output, not a pre-existing function.  The spike
  must implement it.
- **`doc` leading space pattern `" *"` in clockwork.fltkg**: this is a leading
  separator context (the `doc` rule uses `. / */ .` with NO_WS separators around
  a regex).  The regex body is literally ` *` (one space followed by asterisk).
  The `*` is `zero_or_more` quantifier on a `literal_char` (space).  Admitted.
  Needs a test case.
- **Rust fixture path for the spike**: no `tests/rust_*_fixture` crate exists
  for `regex.fltkg` yet.  If the spike needs a compiled Rust extension, it would
  follow the `tests/rust_parser_fixture/` pattern.  If Python-only testing
  suffices for proving the grammar, no new Cargo crate is needed.
