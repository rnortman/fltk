# Formatter Surface Exploration

Scope: the `.fltkfmt` file format, the Python formatter CLI, format-spec config concepts, and other CLI conventions. Does not cover Rust crates or parser/unparser codegen internals.

---

## 1. The `fegen.fltkfmt` File

**Location**: `fltk/fegen/fegen.fltkfmt`

This is the format spec for FLTK's own `.fltkg` grammar files. Content (61 lines):

```
trivia_preserve: LineComment, BlockComment;
preserve_blanks: 1;

ws_allowed: nil;
ws_required: bsp;

before ";" { nbsp; }
after ";" { hard; }
before "," { nbsp; }
after "," { bsp; }
before ":" { nbsp; }
after ":" { bsp; }
before "." { nbsp; }
after "." { bsp; }

rule rule {
    group to ";";
    nest from after ":=" to ";";
    group from name to ":=";
    after name { nbsp; }
    after ":=" { bsp; }
}

rule alternatives {
    group;
    before "|" { bsp; }
    after "|" { nbsp; }
}

rule items {
    group;
    after item { nbsp; }
}

rule item {
    after ":" { nil; }
}

rule term {
    group;
    after "/" { nil; }
    before "/" { nil; }
    after "(" { bsp; }
    before ")" { bsp; }
    nest from after "(" to before ")";
}

rule block_comment {
    ws_allowed: nbsp;
}

rule _trivia {
    ws_required: nbsp;
}
```

A second fixture format spec exists at `fltk/fegen/test_data/rust_parser_fixture.fltkfmt` (46 lines), used by the Rust unparser fixture tests. It exercises `ws_allowed`, `ws_required`, `before`/`after` with literals and labels, rule-level `group`/`nest`/`join`, and item-level range forms (`group from after X to before Y`).

A toy format spec at `fltk/unparse/toy.fltkfmt` is not canonical — it uses syntax (`between`, `indent(2)`, `before: nbsp`) that does not match the actual grammar.

---

## 2. The `.fltkfmt` Grammar

**Location**: `fltk/unparse/unparsefmt.fltkg`

This is the authoritative grammar for `.fltkfmt` files. Key rules:

```
formatter := , statement* ;

statement :=
  default | group | nest | join | after | before
  | rule_config | trivia_preserve | preserve_blanks | omit | render ;

default :=
  ( ws_allowed:"ws_allowed" | ws_required:"ws_required" ) , ":" , spacing , ";" , ;

rule_config :=
  "rule" , rule_name:identifier , "{" , ( rule_statement , )* , "}" , ;

rule_statement :=
  default | group | nest | join | after | before | preserve_blanks | omit | render ;

group := "group" , ";" , | "group" : from_spec? , to_spec? , ";" , ;
nest  := "nest" , ";" , | "nest" : ( indent:integer )? , from_spec? , to_spec? , ";" , ;
join  := "join" : from_spec? , to_spec? , doc_literal , ";" , ;

from_spec := "from" : ( after:"after" : )? . from_anchor:anchor ;
to_spec   := "to"   : ( before:"before" : )? . to_anchor:anchor ;

anchor := label:identifier | literal ;

after  := "after"  : anchor , "{" , position_spec_statement* , "}" , ";"? , ;
before := "before" : anchor , "{" , position_spec_statement* , "}" , ";"? , ;

omit   := "omit"   : anchor , ";" , ;
render := "render" : anchor , "as" : spacing , ";" , ;

position_spec_statement := spacing , ";" , | preserve_blanks ;

spacing := nil:"nil" | nbsp:"nbsp" | bsp:"bsp" | soft:"soft" | hard:"hard"
         | blank:"blank" . ( , "(" , num_blanks:integer? , ")" )? ;

trivia_preserve   := "trivia_preserve" , ":" , trivia_node_list , ";" , ;
trivia_node_list  := identifier , ( "," , identifier )* ;
preserve_blanks   := "preserve_blanks" , ":" , count:integer , ";" , ;

identifier := name:/[a-zA-Z_][a-zA-Z0-9_]*/ ;
literal    := value:/("([^"\n\\]|\\.)+"|'([^'\n\\]|\\.)+')/ ;
integer    := value:/[0-9]+/ ;

_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
```

Trivia: only `line_comment` (no block comment). Comments delimited by `//` to end of line.

Generated parsers from this grammar: `fltk/unparse/unparsefmt_parser.py` and `fltk/unparse/unparsefmt_trivia_parser.py`. Generated CST: `fltk/unparse/unparsefmt_cst.py`.

---

## 3. Format-Spec Config Concepts

Documented in `docs/format-specs.md`. Python implementation in `fltk/unparse/fmt_config.py`.

### Spacing values (`fltk/unparse/fmt_config.py:384-406`, `_spacing_cst_to_doc`)

| DSL keyword | Python Doc constant | Behavior |
|---|---|---|
| `nil` | `NIL` | No space |
| `nbsp` | `NBSP` | Non-breaking space, always a space |
| `bsp` | `LINE` | Breaking space: space if fits, newline if not |
| `soft` | `SOFTLINE` | Nothing if fits, newline if not |
| `hard` | `HARDLINE` | Always newline |
| `blank` | `HARDLINE_BLANK` | Newline + 1 blank line |
| `blank(N)` | `HardLine(blank_lines=N)` | Newline + N blank lines |

### Top-level config structure (`fltk/unparse/fmt_config.py:156-166`)

`FormatterConfig` dataclass:
- `global_ws_allowed: Doc` — default for `,`-separated items (default `NIL`)
- `global_ws_required: Doc` — default for `:`-separated items (default `LINE`)
- `anchor_configs: dict[str, AnchorConfig]` — global before/after anchors
- `rule_configs: dict[str, RuleConfig]` — per-rule overrides
- `trivia_config: TriviaConfig | None`

`TriviaConfig` (`fltk/unparse/fmt_config.py:43-59`):
- `preserve_node_names: set[str] | None` — CST class names to preserve (e.g. `{"LineComment", "BlockComment"}`); empty set = discard all; `None` = preserve all
- `preserve_blanks: int` — 0 = collapse blanks (default), N>0 = normalize to N blank lines

`RuleConfig` (`fltk/unparse/fmt_config.py:139-153`):
- `ws_allowed_spacing: Doc | None`
- `ws_required_spacing: Doc | None`
- `anchor_configs: dict[str, AnchorConfig]`
- `preserve_blanks: int | None` — overrides global when not None

`AnchorConfig` (`fltk/unparse/fmt_config.py:123-137`):
- `selector_type: ItemSelector` — LABEL, LITERAL, RULE_START, RULE_END
- `selector_value: str`
- `disposition: None | Normal | Omit | RenderAs`
- `operations: list[FormatOperation]`

`FormatOperation` (`fltk/unparse/fmt_config.py:111-120`):
- `operation_type: OperationType` — SPACING, GROUP_BEGIN, GROUP_END, NEST_BEGIN, NEST_END, JOIN_BEGIN, JOIN_END
- `spacing: Doc | None`
- `indent: int | None` — used with NEST_BEGIN
- `separator: Doc | None` — used with JOIN_BEGIN

Anchor key format (`fltk/unparse/fmt_config.py:560`): `"{position}:{selector_type.value}:{selector_value}"` e.g. `"after:literal:;"`, `"before:label:name"`, `"before:rule_start:"`, `"after:rule_end:"`.

### Renderer config (`fltk/unparse/renderer.py:22-27`)

`RendererConfig` dataclass:
- `indent_width: int = 4`
- `max_width: int = 80`

---

## 4. Python Formatter CLI

### Entry point

No `[project.scripts]` / `[project.entry-points]` in `pyproject.toml`. The formatter is a plain module, invoked as:

```
uv run python -m fltk.unparse_cli GRAMMAR FORMAT_SPEC INPUT_FILE [options]
```

Module path: `fltk/unparse_cli.py`. The `app` object is a `typer.Typer` (`name="unparse"`). Called via `if __name__ == "__main__": app()` at line 139.

The `genparser` tool (a different CLI) is at `fltk/fegen/genparser.py`, invoked as:

```
uv run python -m fltk.fegen.genparser <subcommand> ...
```

It is also a `typer.Typer` (`name="genparser"`, `add_completion=False`).

### `unparse_cli` positional arguments and flags (`fltk/unparse_cli.py:30-54`)

```
main(
    grammar: Path,             # positional: path to .fltkg
    format_spec: Path,         # positional: path to .fltkfmt
    input_file: Path | None,   # positional: input file, or omit/"-" for stdin
    --output / -o: Path,       # output file (default: stdout)
    --width / -w: int = 80,    # max line width
    --indent / -i: int = 2,    # indent spacing
    --rule / -r: str,          # start rule name
    --generate-unparser: Path, # write generated unparser .py to file
    --cst-module: str,         # CST module import path (required with --generate-unparser)
    --parser-module: str,      # parser module import path (optional, with --generate-unparser)
)
```

Input: stdin when `input_file` is None or `"-"`. Output: stdout when `--output` is absent.

### `genparser` subcommands relevant to formatting

**`gen-rust-unparser`** (`fltk/fegen/genparser.py:470-580`):
```
gen_rust_unparser(
    grammar_file: Path,           # positional: .fltkg
    output_file: Path,            # positional: .rs output
    --cst-mod-path: str = "super::cst",
    --format-config: Path | None, # path to .fltkfmt; baked into generated Rust at gen time
    --protocol-module: str | None,
    --pyi-output: Path | None,
)
```

When `--format-config` is absent, `FormatterConfig()` (all defaults) is used. The format config is parsed with `parse_format_config_file` from `fltk.plumbing` (`fltk/fegen/genparser.py:551`).

---

## 5. Format Config Parsing Pipeline

Entry point for parsing `.fltkfmt` at runtime: `fltk.plumbing.parse_format_config_file(path)` → `parse_format_config(text)` (`fltk/plumbing.py:203-254`).

Pipeline:
1. `terminalsrc.TerminalSource(config_text)` — tokenize source
2. `unparsefmt_parser.Parser(terminals).apply__parse_formatter(0)` — parse to CST using generated parser
3. `fmt_cst_to_config(result.result, terminals)` (`fltk/unparse/fmt_config.py:818`) — walk CST, build `FormatterConfig`

`fmt_cst_to_config` (`fltk/unparse/fmt_config.py:818-936`) iterates `formatter.children_statement()` and dispatches to per-statement processors: `_process_default_statement`, `_process_group_statement`, `_process_nest_statement`, `_process_join_statement`, `_process_after_statement`, `_process_before_statement`, `_process_trivia_preserve_statement`, `_process_preserve_blanks_statement`, `_process_omit_statement`, `_process_render_statement`. Rule blocks recurse using `rule_config_cst.children_rule_statement()`.

---

## 6. Other CLI Conventions

Both CLIs use `typer` (`typer.Typer`) with `add_completion=False`. Error messages go to stderr via `typer.echo(..., err=True)` and exit via `raise typer.Exit(1)`. No color/rich formatting (unparse_cli sets `pretty_exceptions_enable=False`).

Makefile targets using the formatters/generators always go through `uv run python -m <module>`. No installed console-script shims exist.

The `genparser` CLI uses subcommands (`@app.command(name=...)`) to distinguish `generate`, `gen-rust-cst`, `gen-rust-parser`, `gen-rust-unparser`, `gen-rust-lib`. The unparse CLI is a single command.

Flag conventions observed:
- Long flags with dashes: `--output-dir`, `--format-config`, `--cst-mod-path`, `--protocol-module`, `--pyi-output`
- Short aliases for common render knobs: `-o`/`--output`, `-w`/`--width`, `-i`/`--indent`, `-r`/`--rule`, `-v`/`--verbose`
- Boolean flags as `--flag` / `--no-flag` pairs where Typer requires disambiguation
- Positional arguments are ordered: input sources first, then output targets
