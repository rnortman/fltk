# FLTK AST Guide

The generated AST layer turns a CST into typed trees: one Rust type or Python dataclass per
grammar rule, converters in both directions, and a `.fltkast` sidecar that shapes the result
without touching the grammar.

This guide covers what gets generated, how to generate it, the complete `.fltkast` reference,
and the semantics you can rely on (spans, equality, errors, round trips).

Prerequisites: [grammar-syntax.md](grammar-syntax.md) for `.fltkg` files,
[usage.md](usage.md) for parser generation, [cst-structure.md](cst-structure.md) for the CST
the AST is converted from.

## Which layer do you want?

FLTK offers three views of the same parse, and they are not competitors:

| Layer | What it is | Reach for it when |
|---|---|---|
| **CST** | Every child in source order, trivia included, spans everywhere | Formatters, linters, language servers, refactoring — anything that must reproduce the input |
| **serde frontend** (Rust) | A `serde::Deserializer` over the CST: text goes straight into *your* `#[derive(Deserialize)]` types ([guide](rust-serde-guide.md)) | The entity/config layer of a DSL, where you would rather own the structs |
| **generated AST** | Typed trees FLTK generates from grammar + sidecar, with converters both ways | Expression sub-languages (folds, precedence towers), the write direction, and cross-backend schema parity |

The AST layer's three durable advantages:

1. **Expression sub-languages.** A precedence tower with `fold_left:` becomes a nested chain
   type; hand-writing the equivalent recursive types (and their teardown) is where "just write
   the structs" stops being pleasant.
2. **The write direction.** `to_cst` plus the generated unparser gives you "build a value
   programmatically, emit canonical source".
3. **One schema, two backends.** One sidecar generates parallel Rust and Python trees whose
   accepted lexemes, refusals and error templates match, rather than a struct set per language.

The three layers compose: an AST-typed field inside a hand-written serde struct is spelled like
any other field, and a CST node can be held verbatim beside either.

## Quick start

### Rust

Given `calc.fltkg`:

```
expr   := term:number , ( , op:add_op , term:number)* ;
add_op := plus:"+" | minus:"-" ;
number := val:/[0-9]+/ ;
```

and `calc.fltkast`:

```
rule number { type: i64; transparent; }
rule add_op { transparent; }
rule expr   { fold_left: op; }
```

Generate the CST, the parser and the AST module:

```bash
bazel run --run_under="cd $PWD &&" @fltk//:genparser -- gen-rust-cst    calc.fltkg src/cst.rs
bazel run --run_under="cd $PWD &&" @fltk//:genparser -- gen-rust-parser calc.fltkg src/parser.rs
bazel run --run_under="cd $PWD &&" @fltk//:genparser -- gen-rust-ast    calc.fltkg src/ast.rs \
    --ast-config calc.fltkast --parser-mod-path super::parser --goal expr
```

`--run_under="cd $PWD &&"` makes the relative paths after `--` resolve in the directory you
invoked Bazel from rather than in the runfiles tree; see [usage.md](usage.md#quick-start-source-generation).

Then:

```rust
// pub enum Expr { Operand(i64), Binary(ExprBinary) }
// pub struct ExprBinary { pub op: AddOpValue, pub lhs: Box<Expr>, pub rhs: Box<Expr>, pub span: Span }

let value = ast::parse_str("1 + 2 - 3", Some("calc.txt"))?;
match value {
    ast::Expr::Binary(link) => println!("{:?} at {:?}", link.op, link.span),
    ast::Expr::Operand(n) => println!("{n}"),
}
```

`Cargo.toml` needs one entry beyond the CST/parser crates: `fltk-ast-core`. The two shape comments
name types in shorthand; the emitted file spells std items and runtime types by absolute path, for
the reason under [Runtime dependencies](#runtime-dependencies).

### Python

```bash
bazel run --run_under="cd $PWD &&" @fltk//:genparser -- generate calc.fltkg calc calc.calc_cst -o calc/
bazel run --run_under="cd $PWD &&" @fltk//:genparser -- gen-ast  calc.fltkg calc calc.calc_cst \
    --ast-config calc.fltkast --parser-module calc.calc_parser --goal expr -o calc/
```

`generate` always writes `calc/calc_cst_protocol.py` beside the CST module. Both layers need it:
`calc_cst.py` imports its `NodeKind` from it, and the AST module's `from_cst` converters are typed
and keyed against it, which is what lets one AST layer convert a CST from either the Python or the
Rust backend.

Converting at the parse boundary is one of three ways to keep your own code backend-portable; the
other two annotate CST-reading code against the protocol module or against one concrete backend.
See §10.6 of `fltk-grammar-reference.md` for what each style costs.

```python
from calc.calc_ast import parse, ExprBinary

value = parse("1 + 2 - 3", filename="calc.txt")
if isinstance(value, ExprBinary):
    print(value.op, value.span)
```

The Python runtime is `fltk.fegen.pyrt.astrt`, which ships with FLTK; there is nothing to add.

## Generating

### `gen-ast` (Python backend)

```bash
bazel run --run_under="cd $PWD &&" @fltk//:genparser -- gen-ast GRAMMAR_FILE BASE_NAME CST_MODULE [options]
```

Writes `{BASE_NAME}_ast.py`.

| Argument / option | Required | Meaning |
|---|---|---|
| `GRAMMAR_FILE` | yes | The `.fltkg` grammar |
| `BASE_NAME` | yes | Output basename (`calc` writes `calc_ast.py`) |
| `CST_MODULE` | yes | Import path of the generated CST module (`calc.calc_cst`) |
| `--protocol-module PATH` | no | Import path of the generated CST protocol module the `from_cst` converters are typed against; defaults to `CST_MODULE` + `_protocol` |
| `--ast-config PATH` | no | The `.fltkast` sidecar. Omitted, the AST is derived from the grammar alone |
| `--parser-module PATH` | no | Import path of the generated parser; adds `parse(source, filename=None)` |
| `--unparser-module PATH` | no | Import path of the generated unparser; adds `unparse(value, renderer_config=None)` |
| `--goal RULE` | no | Rule the conveniences target; defaults to the grammar's first rule *carrying an AST type* |
| `--output-dir`, `-o` | no | Output directory |

### `gen-rust-ast` (Rust backend)

```bash
bazel run --run_under="cd $PWD &&" @fltk//:genparser -- gen-rust-ast GRAMMAR_FILE OUTPUT_FILE [options]
```

| Argument / option | Required | Meaning |
|---|---|---|
| `GRAMMAR_FILE` | yes | The `.fltkg` grammar |
| `OUTPUT_FILE` | yes | Path to write (conventionally `src/ast.rs`) |
| `--ast-config PATH` | no | The `.fltkast` sidecar |
| `--cst-mod-path PATH` | no | Rust path to the generated CST module; defaults to `super::cst` |
| `--parser-mod-path PATH` | no | Rust path to the generated parser; adds `parse_str(src, filename)` |
| `--unparser-mod-path PATH` | no | Rust path to the generated unparser; adds `unparse_str(value, max_width, indent_width)` |
| `--goal RULE` | no | Rule the entry points target; defaults to the grammar's first rule *carrying an AST type* |

Both commands validate the sidecar against the grammar and build the whole model **before**
opening the output file, so a rejected sidecar leaves no artifact behind. Only the backend
being generated is required to be complete: a `custom(...)` list may omit the other backend's
entries.

The Rust module's header comment names the `fltk-ast-core` cargo features it needs — `indexmap`
for `key:` collections, `uuid` / `decimal` for those two builtins. Enable them on the runtime
crate.

### Bazel (Rust)

`generate_rust_parser` grows the AST module as an opt-in:

```python
load("@fltk//:rust.bzl", "generate_rust_parser")

generate_rust_parser(
    name="calc_rs",
    src="calc.fltkg",
    ast_config="calc.fltkast",
    ast=True,
    goal="expr",
)
```

| Attribute | Meaning |
|---|---|
| `ast_config` | Label of the `.fltkast` sidecar, passed as `--ast-config` |
| `ast` | Emit `<name>/ast.rs` beside `cst.rs` / `parser.rs` |
| `goal` | `--goal` for the generated entry points; empty leaves the generator's default |

Both `python_extension` modes accept these. In `python_extension = True`, `fltk_pyo3_cdylib`
takes the same `ast` flag: it declares `ast.rs` as an output of the assembly step, adds
`pub mod ast;` to the generated crate root, and links `fltk-ast-core`. The basename `ast.rs` is
load-bearing — the generated modules name each other as siblings of `cst_mod_path`.

## What gets generated

Every rule classifies into one of four **node forms**. The sidecar can shape a rule but never
invents a form the grammar does not have (except `sum;` / `product;`, which choose between the
two multi-alternative forms).

| Form | The grammar shape | What is generated |
|---|---|---|
| **enum-shaped** | Two or more alternatives, each exactly one required labeled literal (`red:"red" \| blue:"blue"`) | A value enum `<Rule>Value` plus a node holding it in `value` |
| **terminal-only** | Every child a terminal, at least one of them a regex | A node holding the matched text in `text` (or a coerced `value`) |
| **sum** | Two or more alternatives told apart by their labeled children | Rust: an enum over the alternatives. Python: a union alias |
| **product** | Everything else | A struct / dataclass with one member per label |

A rule whose terminals are all *literals* is a product, not terminal-only: its span is a grammar
constant modulo whitespace, so a `text` member on it would hold formatting rather than data.

Every Rust shape this guide prints — the ones below and the two in the quick start above — names
types in shorthand: `String`, `Vec<T>`, `Box<T>`, `Span`. The emitted file spells std items and
runtime types by absolute path instead (`::std::string::String`, `::fltk_cst_core::Span`), for the
collision reason under [Runtime dependencies](#runtime-dependencies); the type is the same either
way, and your own annotations can use whichever spelling is in scope.

### Product rules

One member per INCLUDE label, in grammar order, plus `span`:

```rust
pub struct ServerDef {
    pub name: String,
    pub settings: IndexMap<String, Setting>,
    pub span: Span,
}
```

```python
@dataclasses.dataclass
class ServerDef:
    name: str
    settings: dict[str, Setting]
    span: SpanProtocol = dataclasses.field(default=terminalsrc.UnknownSpan, compare=False)
```

Suppressed items (`%`) contribute nothing, and neither do unlabeled literals and regexes — they
are suppressed by default. An unlabeled *rule reference* is a different case: it carries the
rule name as an implicit label (see [cst-structure.md](cst-structure.md)), so `setting*` is the
field `setting` and a sidecar selects it as `field setting { … }`. An inlined reference (`!`)
contributes no node and so no field. A label is what makes a child data.

### Field types

A field's type is its **element type** inside a **container** chosen by the label's whole-rule
arity:

| Label arity | Container | Rust | Python |
|---|---|---|---|
| Exactly once | single | `T` | `T` |
| At most once | optional | `Option<T>` | `T \| None` |
| Repeatable | collection | `Vec<T>` | `list[T]` |
| Repeatable, element declares `key:` | map | `IndexMap<K, T>` | `dict[K, T]` |
| Repeatable, element declares `key: … multi;` | map | `IndexMap<K, Vec<T>>` | `dict[K, list[T]]` |

Element types:

| The label carries | Rust | Python |
|---|---|---|
| A regex terminal | `String` | `str` |
| A literal terminal, required | `Span` | `SpanProtocol` |
| A literal terminal, optional | `bool` (presence) | `bool` |
| A rule reference | that rule's type | that rule's type |
| A `transparent;` rule reference | the erased payload | the erased payload |
| More than one kind under one label | a generated field enum `<Rule><Label>` | a union alias |

A required labeled literal is a **position**, not text: the CST records which alternative
matched, never which spelling. See [Labeling literals](#labeling-literals) below.

### Union labels

When one label carries more than one kind (`val := item:num | item:name | item:/[!@#$]+/`), the
field's type is a generated enum over the possibilities:

```rust
pub enum ValItem { Num(Num), Name(Name), Text(String) }
```

Python spells the same thing as a union alias.

### Sum rules

Rust generates an enum; Python a union alias over the variants' payloads.

- **Variant name** = the UpperCamel of the alternative's single label, or `Alt<N>` (1-based)
  when the alternative carries more than one label. Rename with `variant <Computed>: <New>;`.
- **Payload.** An alternative that is *exactly one* required, labeled, included reference to
  another rule carries that rule's type directly (`Atom::Num(Num)`), provided no sibling variant
  carries the same type. Every other alternative gets a generated payload struct named
  `<Rule><Variant>` holding that alternative's fields.

```rust
pub enum Expr {
    Alt1(Box<ExprAlt1>),   // lhs:expr . "+" . rhs:atom
    Atom(Atom),            // atom:atom
}
```

Recursive types are boxed where the cycle requires it; you do not choose or see this beyond the
`Box` in the signature.

### Enum-shaped rules and value enums

```
metric_type := counter:"counter" | gauge:"gauge" | histogram:"histogram" ;
```

generates a value enum `MetricTypeValue` with one member per **label** (not per alternative:
two spellings under one label are one value) and a node whose `value` holds it. With
`transparent;` the value enum *is* what use sites carry. With `bool: <label>;` the rule's value
is a plain `bool` and no enum is generated.

### Terminal-only rules

```rust
pub struct Num { pub text: String, pub span: Span }
```

`text_from: <label>;` redirects `text` to one child's span instead of the node's own (the
quote-stripping idiom: `quoted := %"'" . value:/[a-z]+/ . %"'"` with `text_from: value;`).
A `type:` coercion replaces `text: String` with `value: <coerced type>`.

### Folds

`fold_left: op;` / `fold_right: op;` on a rule shaped `operand , (op , operand)*` turns the flat
run into a nested chain:

```rust
pub struct ExprBinary { pub op: AddOpValue, pub lhs: Box<Expr>, pub rhs: Box<Expr>, pub span: Span }
pub enum Expr { Operand(i64), Binary(ExprBinary) }
```

A link's `span` covers everything below it. The Rust chain types carry a worklist-based `Drop`
and a worklist-based equality walk, so a chain as deep as its source neither overflows the stack
on teardown nor on comparison. Python compares chains by ordinary dataclass recursion, which is
as deep as any Python structure walk.

### Module surface

| Item | Rust | Python |
|---|---|---|
| Per-rule conversion in | `T::from_cst(&Shared<cst::T>) -> Result<T, AstError>` | `T.from_cst(node)` and `t_from_cst(node)` |
| Per-rule conversion out | `T::to_cst(&self) -> Result<Shared<cst::T>, AstError>` | `T.to_cst()` and `t_to_cst(value)` |
| Text → AST | `parse_str(src, filename) -> Result<Goal, ParseToAstError>` | `parse(source, filename=None) -> Goal` |
| AST → text | `unparse_str(value, max_width, indent_width) -> Result<String, AstError>` | `unparse(value, renderer_config=None) -> str` |

The entry points are emitted only when the corresponding module path is passed on the command
line. `parse_str` / `parse` parse without trivia capture — a converter ignores unlabeled
children, so there is nothing to capture it for — check that the whole input was consumed, and
reject a depth-exceeded parse even when the parser returned a tree.

## The `.fltkast` sidecar

A sidecar is a file of `option` statements and `rule` blocks. `//` starts a line comment.
Naming a rule the grammar does not have, or a trivia rule, is an error. So is a duplicate
`rule` block, a duplicate statement inside a block, or a statement that does not apply to the
rule's node form. Every offense in the file is collected and reported together, each with a
`file:line:col` caret.

```
option cst = true;

rule identifier { transparent; }
rule number     { type: i64; transparent; }
rule setting    { key: name; }
rule server_def { field setting { name: settings; } }
```

### Options

| Statement | Effect |
|---|---|
| `option cst = true;` | Every generated node gains a `cst` back-pointer to the node it was converted from. It is optional, defaulted, and excluded from equality and `repr` — hand-built values have none, the AST fields stay authoritative, and the reverse direction ignores it |

`cst` is the only option.

### Statement reference

| Statement | Applies to | Effect |
|---|---|---|
| `type: <builtin>;` | terminal-only | Coerce the rule's text to a scalar |
| `type: custom(...);` | terminal-only | Coerce through your own parse/render functions |
| `bool: <label>;` | enum-shaped, exactly two labels | The rule's value is a `bool`; `<label>` is the true one |
| `transparent;` | terminal-only, enum-shaped, single-field product | The rule gets no type; use sites carry its payload |
| `text_from: <label>;` | terminal-only | `text` comes from `<label>`'s span, not the node's |
| `key: <label> [multi];` | product | Collections of this rule become maps keyed by `<label>` |
| `fold_left: <op>;` / `fold_right: <op>;` | single-alternative `operand , (op , operand)*` | Fold the flat run into a nested chain |
| `flatten;` | product, never used as a collection | The rule gets no type; its fields are hoisted into each referencing node |
| `custom(rust: "...", python: "...");` | any | FLTK generates nothing for the rule; your type supplies `from_cst`/`to_cst` |
| `name: <Ident>;` | any | Rename the rule's generated type |
| `variant <Computed>: <Ident>;` | sum, enum-shaped, fold | Rename one variant |
| `field <label> { name: <ident>; }` | product, sum payloads | Rename one field |
| `sum;` / `product;` | ≥2 alternatives, not enum-shaped | Force the multi-alternative classification |

Every statement but `variant` and `field` may appear at most once per block.

Pairs that cannot share a block:

| Conflict | Why |
|---|---|
| `type:` + `bool:` | A boolean rule's value is not a coerced text |
| `type:` + `fold_left:`/`fold_right:` | A fold rule is not terminal-only |
| `type:` + `flatten;` | A flattened rule has fields, not a scalar value |
| `transparent;` + `flatten;` | Two different erasures of the same rule |
| `transparent;` + `key:` | An erased rule's use sites carry a payload with no key field to index by |
| `flatten;` + `key:` | `flatten;` refuses collection use sites, which is the only place `key:` acts |
| `sum;` + `product;` | They name opposite classifications |
| `custom(...)` + anything | A custom rule gets no generated type to shape |

Erasure cycles are refused across rules: a `transparent;` rule reachable from itself through
other `transparent;` rules, and likewise for `flatten;`. At least one rule in the cycle must
keep a type of its own.

### `type:`

Builtins: `i8` `i16` `i32` `i64` `u8` `u16` `u32` `u64` `f32` `f64` `uuid` `decimal`.

The coercion replaces the node's `text: String` with `value: <type>`, parsed by a strict gate
shared by both backends: the same lexemes are accepted, the same range refusals are raised, and
serialization renders the same bytes. `uuid` and `decimal` map to `fltk_ast_core::Uuid` /
`Decimal` (re-exported so generated code and the runtime cannot be on two versions) and to
`uuid.UUID` / `decimal.Decimal`, each behind its own cargo feature on the Rust side.

`type: custom(...)` takes six entries, three per backend, and only the backends being generated
must be complete:

```
rule amount {
  type: custom(rust_type:    "crate::money::Cents",
               rust_parse:   "crate::money::parse_cents",
               rust_unparse: "crate::money::render_cents",
               py_type:      "myapp.money.Cents",
               py_parse:     "myapp.money.parse_cents",
               py_unparse:   "myapp.money.render_cents");
}
```

Python entries are dotted paths and need at least a module and an attribute, because the
generated module imports everything before the last component.

### `bool:`

```
boolean := true:"true" | false:"false" ;
```
```
rule boolean { bool: true; transparent; }
```

The rule's value becomes a plain `bool` rather than a value enum, so a use site is a `bool`
field. The check counts *labels*, not alternatives — `yes:"yes" | yes:"y" | no:"no"` is a
two-valued rule.

### `transparent;`

An erased rule gets no generated type at all; every reference to it carries the rule's single
payload instead. This is the workhorse statement: it is what turns `identifier` into a `String`
field, `number` into an `i64` field, and a `metric_type` reference into a `MetricTypeValue`.

Erasure is transitive — a transparent rule whose one field is itself transparent erases all the
way down — and a cycle of transparent rules is a generation error: at least one rule in the
cycle must keep a type of its own.

### `text_from:`

Redirects a terminal-only rule's `text` to one child's span. The label must occur exactly once.
The node's own `span` is unchanged, so a quoted string's span still covers the quotes while its
`text` does not.

### `key:` and `key: … multi;`

`key: <label>;` on a product rule says "collections of this rule are maps, keyed by `<label>`".
It acts at the *use site*: `setting*` inside `server_def` becomes
`IndexMap<String, Setting>` / `dict[str, Setting]` rather than a `Vec` / `list`.

```
setting := name:identifier , "=" , value:value , ";" , ;
```
```
rule setting { key: name; }
```

Rules:

- The keying label must occur **exactly once** on the element rule. An optional or repeatable
  key is a generation error, with or without `multi`.
- The key must resolve to text or to one of the eight integer builtins. A key that still has a
  node type is refused — mark the referenced rule `transparent;` (as `identifier` is above) so
  the key resolves to a string. So are a `type: custom(...)` type, a float, and a literal's
  position (a literal's text is a grammar constant, so every element would share one key).
  Integer keying means declaring `type: <int>;` on the transparent key rule.
- **The key stays a field.** `Setting` still has its `name` member; the map key is a lookup
  convenience, and both conversion directions read the key off the element.
- Without `multi`, a repeated key is an error naming both locations ("previously defined here").
- With `multi`, elements sharing a key accumulate: the map's values become `Vec<T>` / `list[T]`,
  a key takes its place in the map where its first element appeared, and a repeated key is no
  longer an error.

`key:` conflicts with `transparent;` (an erased rule's use sites carry a payload with no key
field to index by) and with `flatten;` (which refuses collection use sites, leaving a `key:`
that keys nothing).

**The `multi` unparse consequence.** Grouping loses global interleaving: `a=1; b=2; a=3;`
converts to `{a: [1, 3], b: [2]}`, which can only unparse as `a=1; a=3; b=2;`. A
parse → `to_cst` → unparse round trip therefore **canonicalizes to grouped order**. This is a
language-level change to adopt along with `multi`, not a surprise. The AST-value round-trip law
still holds, because equality on a keyed map is by key, not by position. Consumers who need
interleaving preserved skip `key:` and keep the `Vec` / `list`.

Also deliberate: a hand-built map entry whose value list is *empty* cannot be rendered — the key
lives on the element, so a key with no element has nothing to carry it. `to_cst` refuses it with
an `AstError` naming the rule and the key rather than silently dropping the key. Values coming
from `from_cst` never contain an empty entry.

### `fold_left:` / `fold_right:`

Requires a single-alternative rule carrying exactly two labels: a repeatable operator and a
one-or-more operand. The direction picks the nesting. See [Folds](#folds) above for the
generated shape. `transparent;` cannot apply to a fold rule — an operand/link pair has no single
payload to erase to.

### `flatten;`

A flattened wrapper gets no type; the rule referencing it holds the wrapper's fields directly:

```
task_def := "task" : name:identifier , schedule? , "{" , setting* , "}" , ;
schedule := "every" : interval:number . unit:time_unit ;
```
```
rule schedule { flatten; }
```

`TaskDef` gains `interval` and `unit` directly. Where the wrapper's own use site is optional, the
hoisted fields are degraded to optional types, and a partially filled wrapper is refused rather
than written out as a CST missing a required child. Hoisting is transitive: a field can live
several wrappers down, and the whole path is walked to read it.

`flatten;` is refused on a rule used as a *collection* anywhere — repeated hoisted fields have
nowhere to go — and a cycle of flattened rules is refused for the same reason `transparent;`
cycles are.

### `custom(rust: ..., python: ...);`

The whole-rule escape hatch: FLTK generates no type and no converter for the rule, and each
backend names its own user type, which supplies the `from_cst`/`to_cst` convention. Because
there is no generated type to shape, `custom(...)` conflicts with every other statement in the
block.

### Renaming

| Statement | Renames |
|---|---|
| `name: <Ident>;` | The rule's generated type |
| `variant <Computed>: <Ident>;` | One variant, selected by its computed name (`Alt2`, `Inner`, …) |
| `field <label> { name: <ident>; }` | One field, selected by its grammar label |

A rename is rejected where it would apply to nothing: `variant` on a product or a `bool:` rule,
`field` on a terminal-only or enum-shaped rule. A statement that validates but does nothing is
exactly what this layer exists to prevent.

Names are checked against both backends at once, so a name that works on one and not the other
is refused at generation time: no leading `__` (Python private-name mangling), no Python
keyword, no Rust keyword that cannot be written as a raw identifier. A field may not be named
`span`, `text`, `value`, `cst`, `from_cst` or `to_cst` — generated nodes carry those members.

Renaming grammar labels is how you deal with a label like `type:`, which is a fine grammar label
and a poor Python field name.

### `sum;` / `product;`

A multi-alternative rule classifies as a sum when every pair of alternatives is told apart by its
labeled children and no pair is a strict extension of another; otherwise it is a product. The
override chooses explicitly:

```
val := item:num | item:name | item:/[!@#$]+/ ;
```
```
rule val { product; }
```

Left alone this is three alternatives all labeled `item`, which as a sum would mint three
variants called `Item`. One product with a union-typed field is what the union label means. The
override applies only to multi-alternative, non-enum-shaped rules.

## Spans and equality

Every generated type carries a `span` locating it in the source, and **spans never take part in
equality**. Two values converted from identical text at different offsets — or in different
files — compare equal.

This is what makes the round-trip law usable: a value built by hand carries unknown spans, and a
value parsed from that value's rendering carries real ones, and the two are still equal. It also
means equality is a statement about *content*, which is what a test wants to assert.

- Rust: `PartialEq` is generated per type and compares members but not `span`. Types that nest
  without a bound (folds, recursive sums) compare through a worklist rather than by recursion.
- Python: node classes are `dataclasses` with `span` declared `compare=False`. Value enums
  compare across backends by a canonical member name, so a pure-Python member and its PyO3
  counterpart are equal.

A sum, a fold and a field enum expose `span()` returning the span of whichever payload they
hold — when every payload carries one. An erased payload (a bare `i64`, a `String`) does not, so
those enums have no `span()`.

## Errors

Both backends raise one error type from conversion, with the same message templates:

| | Rust | Python |
|---|---|---|
| Conversion failure | `fltk_ast_core::AstError` | `astrt.AstError` |
| `parse_str` / `parse` failure | `ParseToAstError::{Parse, Ast}` | `AstError`, or the parser's own error |

`AstError` carries three things:

| Member | What it holds |
|---|---|
| `message` | What went wrong, naming the rule and label involved |
| `span` | Where it went wrong |
| `related` | Secondary locations, each with its own explanation |

`Display` / `str()` renders **the message and the primary position only** — `"… at line L,
column C"` when the span resolves one, the bare message when it does not (hand-built values carry
unknown spans). Secondary locations are carried, not rendered: a diagnostic renderer walks
`related` itself.

```rust
match Config::from_cst(&node) {
    Err(err) => {
        eprintln!("{err}");
        for (note, span) in &err.related {
            eprintln!("  {note}: {span:?}");
        }
    }
    Ok(config) => { /* … */ }
}
```

```python
try:
    config = Config.from_cst(node)
except astrt.AstError as err:
    print(err)
    for note, span in err.related:
        print(f"  {note}: {span}")
```

The duplicate-key refusal is the worked example: its message names the rule and the key, its
`span` is the offending element, and `related` carries `("previously defined here", …)` pointing
at the first one.

Most conversion errors are reachable only from a hand-built or mutated CST — a parser-produced
tree satisfies the arities the grammar declares by construction. The exceptions are the ones the
grammar cannot enforce: `type:` coercion failures (a number the width cannot hold) and duplicate
`key:` values.

## Text → AST → text

With both a parser module and an unparser module named at generation time, the loop closes:

```python
value = parse(source, filename="app.conf")
value.settings["port"].value = 9090
print(unparse(value))
```

The law the layer guarantees: **`from_cst(parse(unparse(value))) == value`**. Rendering a value
and re-reading it gives back an equal value. The reverse — that unparsing a parsed document
reproduces the original bytes — is *not* guaranteed and is not meant to be: the AST holds
content, the formatter decides layout, and the CST is the layer that preserves input fidelity.

Three canonicalizations are worth knowing about, because they are the places rendering
deliberately differs from the input:

1. **Whitespace and layout** come from the generated formatter (the grammar's `.fltkfmt`, or the
   default separator spacing), not from the source.
2. **Equivalent literal spellings** canonicalize to the first spelling in grammar order (see
   below).
3. **`multi` maps** render in grouped order.

`unparse_str` / `unparse` go through `to_cst` first, so every refusal `to_cst` can raise — an
unplaceable value, a text that would not re-parse, an empty `multi` group — surfaces here as an
`AstError` before any rendering happens.

## Labeling literals

**A label is a statement about semantic content.** Labeling a literal encodes a distinction the
*parser* is responsible for; application code recovers that distinction from the label, never by
inspecting the literal's text. The CST records which position matched, never which spelling, and
the AST field for a required labeled literal is a bare position for exactly that reason.

Three consequences:

- **A literal with no discriminatory effect should be unlabeled.** Alternative spellings of such
  a literal (`("import" | "use")`) are equivalent by definition, and the unparser canonicalizes
  to the first spelling in grammar order. This is intended: it is also the keyword-evolution
  mechanism — put the new keyword first, accept both, and the formatter ports existing files.
- **Multiple spellings under one label declare the spellings equivalent.**
  `shade:"gray" | shade:"grey"` is one variant `Shade`; both spellings dispatch to it, and
  rendering emits `gray`. This is the supported way to accept a spelling variant.
- **Distinct semantic values take distinct labels.** `yes:"yes" | no:"no"` — which is the
  enum-shaped idiom, and gets a value enum.

One shape is refused outright, at unparser generation time: a label that is **always present**,
carried **only** by literals, and covering **two or more distinct spellings**
(`flag:"yes" | flag:"no"` in a position where `flag` always occurs). No formatter can reproduce
what the author wrote there, so the generator says so and names both fixes: if the spellings mean
the same thing, remove the label; if they are distinct values, give each its own. Because
`unparse_str` / `unparse` need the generated unparser, they inherit the refusal; `to_cst` still
generates for such grammars.

A label that is sometimes absent is left alone — there, presence is the datum and several
spellings are legitimate.

## Float widths in Python

`type: f32;` means the field **is** a 32-bit float, on both backends. Rust has a type for that;
Python does not, so the Python backend emulates one:

- Parsing rounds the value through 32 bits.
- Rendering emits the shortest decimal string that round-trips through the *declared* width, in
  CPython `repr` conventions. A parsed `3.14` renders as `3.14`, not `3.140000104904175`.
- Construction normalizes: a generated class with `f32` fields rounds them through 32 bits in
  `__post_init__`, so `Ratio(value=3.14)` holds exactly what Rust's `Ratio { value: 3.14f32 }`
  holds.

The payoff is that cross-backend equality and byte-identical rendering hold for `f32` fields.
The cost is two escape paths that `__post_init__` cannot see: mutating a field in place, and an
`f32` reached only through a union payload where no owning dataclass exists. A value that got
there compares unequal to its parsed self until it has been through one unparse/parse cycle;
rendering normalizes it either way.

A magnitude the width cannot hold at all is still refused — an infinity has no grammar spelling.
`f64`, the integer widths, `uuid` and `decimal` are untouched by any of this: `f64` is what
CPython floats already are.

If your language wants decimal semantics rather than binary floating point, declare
`type: decimal;` instead — it maps to `decimal.Decimal` and `rust_decimal::Decimal`.

## Runtime dependencies

| Backend | Dependency | Notes |
|---|---|---|
| Rust | `fltk-ast-core` | pyo3-free. Features: `indexmap` (default-on, needed by `key:`), `uuid`, `decimal` (off by default) |
| Rust | `fltk-cst-core` | For `Span`, which every node carries |
| Python | `fltk.fegen.pyrt.astrt` | Ships with FLTK |

Generated Rust names the runtime by absolute path (`::fltk_ast_core::AstError`), so a rule called
`error` or `span` cannot collide with anything your preamble imported. Std items in type position
are spelled absolute for the same reason (`::std::string::String`, `::std::vec::Vec`): the generated
module declares one item per rule at module scope, and Rust resolves those before the prelude, so a
rule named `option` or `string` would otherwise make the file it appears in uncompilable.

The generated AST module is **public API for out-of-tree consumers**: type names, field names,
variant names, accepted lexemes and error templates are all downstream-visible. Renaming a rule,
a label, or a sidecar-driven name is a breaking change for the code written against it.
