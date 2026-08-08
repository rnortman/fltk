# FLTK Rust serde Guide

The serde frontend is a `serde::Deserializer` over a generated CST: source text in your own
syntax goes straight into **your** `#[derive(Deserialize)]` types, and serde's unknown-field,
missing-field and wrong-type errors come back positioned by CST span.

```rust
let config: AppConfig = de::from_str(&text, Some("app.conf"))?;
```

`AppConfig` is yours. FLTK generates no types for it — the frontend generates a description of
your grammar's tree and the entry points that run the shared runtime over it. This is the
serde_json / toml architecture with your own syntax at the front.

Prerequisites: [grammar-syntax.md](grammar-syntax.md) for `.fltkg` files,
[usage.md](usage.md) for CST and parser generation, [ast-guide.md](ast-guide.md) for the
`.fltkast` sidecar, which the frontend shares and does not extend.

## Which layer do you want?

| Layer | What it is | Reach for it when |
|---|---|---|
| **CST** | Every child in source order, trivia included, spans everywhere | Formatters, linters, language servers — anything that must reproduce the input |
| **serde frontend** (Rust) | Text → your `#[derive(Deserialize)]` types, errors positioned by span | The entity/config layer of a DSL, where you would rather own the structs |
| **generated AST** | Typed trees FLTK generates from grammar + sidecar, converters both ways | Expression sub-languages (folds), the write direction, cross-backend schema parity |

They compose. A field of a hand-written serde struct can be a generated AST type (see
[AST-typed fields](#ast-typed-fields)) or a CST node held verbatim (see [`Raw`](#raw)).

The division of labor the frontend assumes:

- **grammar (`.fltkg`) = syntax.** Enumerate keys in the grammar only where syntax genuinely
  varies per key. Where entries are uniform, write one generic rule —
  `key:name , "=" , value:value , ";"` — and let the target struct name the keys.
- **sidecar (`.fltkast`) = shape.** `key:` / `multi`, `transparent;`, `flatten;`, renames. One
  sidecar serves the AST emitters and this one; there is no serde-specific directive.
- **target types = schema.** Which keys exist, which are required, and what each one's value
  must be, are decided by your structs.

## Quick start

`app.fltkg` — one generic entry rule, no key enumerated in the grammar:

```
config  := , setting* ;
setting := key:name , "=" , (value:boolean | value:word) , ";" , ;
name    := text:/[a-z_][a-z0-9_]*/ ;
word    := text:/[a-zA-Z0-9_.]+/ ;
boolean := true:"true" | false:"false" ;
```

(`boolean` comes first in the alternation because `word` would otherwise match `true` as well;
alternatives are tried in order.)

`app.fltkast` — the shape: entries are keyed by their `key` label, and the mechanical leaves are
erased:

```
rule name    { transparent; }
rule word    { transparent; }
rule boolean { bool: true; transparent; }
rule setting { key: key; }
rule config  { field setting { name: settings; } }
```

Generate the CST, the parser and the serde module:

```bash
uv run python -m fltk.fegen.genparser gen-rust-cst    app.fltkg src/cst.rs
uv run python -m fltk.fegen.genparser gen-rust-parser app.fltkg src/parser.rs
uv run python -m fltk.fegen.genparser gen-rust-serde  app.fltkg src/de.rs \
    --ast-config app.fltkast --parser-mod-path super::parser --goal config
```

Your types, and one call:

```rust
use serde::Deserialize;

#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Document {
    settings: Settings,
}

#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Settings {
    host: Value<String>,
    port: Value<u16>,
    verbose: Value<bool>,
}

/// A keyed entry's value is the element minus the field that keys it — here, `value`.
#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Value<T> {
    value: T,
}

let text = "host = localhost;\nport = 8080;\nverbose = true;\n";
let document: Document = de::from_str(text, Some("app.conf"))?;
assert_eq!(document.settings.port.value, 8080u16);
```

Three things happened that are the point of the layer:

- `port` became a `u16` because the *target* said so. The grammar has no integer rule and the
  sidecar has no `type:` — the `u16` gate ran over the value's source text.
- `verbose` became a `bool` because the sidecar's `bool: true;` says that rule's value is a
  boolean. The literal texts `true` / `false` are never special-cased on their spelling alone.
- A typo is a real diagnostic instead of a parse failure:

```text
unknown field `prot`, expected one of `host`, `port`, `verbose` at line 2, column 1
```

The message is serde's; the position is FLTK's.

`Cargo.toml` gains exactly two entries beyond the CST/parser crates: `serde` (with its `derive`
feature, for your own targets) and `fltk-serde-core`.

## Generating

### `gen-rust-serde`

```bash
uv run python -m fltk.fegen.genparser gen-rust-serde GRAMMAR_FILE OUTPUT_FILE --ast-config PATH [options]
```

| Argument / option | Required | Meaning |
|---|---|---|
| `GRAMMAR_FILE` | yes | The `.fltkg` grammar |
| `OUTPUT_FILE` | yes | Path to write (conventionally `src/de.rs`) |
| `--ast-config PATH` | **yes** | The `.fltkast` sidecar. Required: `key:`, `transparent;`, `flatten;` and the renames are what tell the frontend what the tree means |
| `--cst-mod-path PATH` | no | Rust path to the generated CST module; defaults to `super::cst` |
| `--parser-mod-path PATH` | no | Rust path to the generated parser; adds `from_str(src, filename)` |
| `--goal RULE` | no | Rule `from_str` targets; defaults to the grammar's **first** rule |
| `--ast-mod-path PATH` | no | Rust path to the generated AST module; adds a `Deserialize` impl per generated AST type |

Generation validates the sidecar and builds the whole model **before** opening the output file,
so a rejected sidecar or a name collision leaves no artifact behind.

**Name the output `de.rs`, not `serde.rs`.** A crate-root `mod serde` makes every
`use serde::…` in the crate ambiguous under Rust 2018+.

Unlike `gen-rust-ast`, `--goal` has no refinement: every rule gets a deserializer, so the
default is the grammar's first rule whatever its shape. Naming a trivia rule is an error.

### What lands in `de.rs`

| Item | When | What it is |
|---|---|---|
| `pub fn from_str<T: DeserializeOwned>(src: &str, filename: Option<&str>) -> Result<T, ParseToTargetError>` | `--parser-mod-path` | Parse the goal rule, then deserialize. Rejects a partial parse and a depth-exceeded parse, exactly as `ast.rs::parse_str` does |
| `pub fn from_<rule>_cst<T: DeserializeOwned>(node: &Shared<cst::R>) -> Result<T, DeserializeError>` | always, per rule | Deserialize from a node you already have. This is what makes [`Raw`](#raw) useful, and lets a caller who already parsed start anywhere |
| `impl<'de> Deserialize<'de> for ast::T` | `--ast-mod-path` | See [AST-typed fields](#ast-typed-fields) |
| per-rule `static` shape descriptions and `NodeShape` impls | always | The description the runtime's one Deserializer reads. Not public API |

Without `--ast-mod-path` the frontend generates **zero public types** — the pure
bring-your-own-structs mode.

### Makefile

```bash
make gen-rust-serde GRAMMAR=app.fltkg RS_OUT=src/de.rs \
     EXTRA_ARGS="--ast-config app.fltkast --parser-mod-path super::parser \
                 --ast-mod-path super::ast --goal config"
```

Generated code is not expected to be rustfmt-clean straight out of the generator: the intended
flow is generate → `make fix` → commit.

### Bazel

`generate_rust_parser` grows the serde module as an opt-in:

```python
load("@fltk//:rust.bzl", "generate_rust_parser")

generate_rust_parser(
    name="app_rs",
    src="app.fltkg",
    ast_config="app.fltkast",
    ast=True,
    serde=True,
    goal="config",
    python_extension=True,
)
```

| Attribute | Meaning |
|---|---|
| `ast_config` | Label of the `.fltkast` sidecar, passed as `--ast-config`. **Required** by `serde = True` |
| `serde` | Emit `<name>/de.rs` beside `cst.rs` / `parser.rs` |
| `ast` | Emit `<name>/ast.rs`; with `serde = True` the serde module also gets the `Deserialize` impls |
| `goal` | `--goal` for the generated entry points; empty leaves each generator's default |

`serde = True` without `ast_config`, and `ast_config` with neither `ast` nor `serde`, are
refused — at loading time by the macro and again at analysis time by the rule.

In `python_extension = True`, `fltk_pyo3_cdylib` takes the same flags: it declares `de.rs` as an
output of the crate assembly, adds `pub mod de;` to the generated crate root, and links
`fltk-serde-core` and `serde`. The basename `de.rs` is load-bearing — the generated modules name
each other as siblings of `cst_mod_path`.

`de.rs` holds no pyclasses and is not registered with the `#[pymodule]`; it is Rust-only surface
of the same crate.

## The data model

One rule is one shape. What the frontend serves for it, per node form:

| Node form | Served as |
|---|---|
| **product** | A map: one entry per field, in model field order, keyed by the field's name (after sidecar renames) |
| **terminal-only** | A string — the node's source text, with `text_from:` honored |
| **enum-shaped** | A unit-variant enum, or the variant's name as a string. With `bool: <label>;`, a boolean |
| **sum** | An externally tagged enum: `{VariantName: <the alternative's payload>}` |
| **fold** | The nested chain, externally tagged: `{Operand: …}` / `{Binary: {op, lhs, rhs}}` |
| `transparent;` rule | Erased — the payload's own shape is served in its place, all the way down |
| `flatten;` wrapper | Erased — the hoisted fields appear directly on the referencing node |

Field arities come from the label's whole-rule arity, the same table the AST layer uses:

| Label arity | Served as |
|---|---|
| Exactly once | the child's value |
| At most once | the entry is present iff the child is. Absent + non-`Option` target = serde's missing-field error |
| Repeatable | a sequence, **always present** — empty when there are no children, so a `Vec` field needs no `#[serde(default)]` |
| Repeatable, element declares `key:` | a map *or* a sequence, whichever the target asks for. See [Keyed regions](#keyed-regions) |
| An optional labeled literal | a boolean: was it written? |

A union label — one label carrying more than one rule — is served as whatever the child at that
position actually is. The quick start uses one: `(value:boolean | value:word)` serves a boolean
where the source wrote `true` and a string where it wrote anything else, and a `Value<bool>` /
`Value<String>` target reads each. There is no tag to match on, so an externally tagged enum
target does *not* work over a union label; a self-describing target does, and an
[AST-typed field](#ast-typed-fields) is the escape hatch.

### Products are structs

```
metric_def := "metric" : name:name , ":" , type:metric_type , ("interval" : interval:num)? , ";" ;
```

```rust
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Metric {
    name: String,
    metric_kind: Kind,     // `field type { name: metric_kind; }` in the sidecar
    interval: Option<u32>, // the grammar's `?`
}
```

A grammar label that is a poor Rust field name is renamed in the sidecar, exactly as for the AST
layer — `field <label> { name: <ident>; }` — and the serde field name is the renamed one.

Doc-comment content is a field like any other: if a label captures it, a target with
`deny_unknown_fields` must declare it (or drop `deny_unknown_fields`).

### Sums are externally tagged enums

```
stanza := server_def | metric_def ;
```

```rust
#[derive(Deserialize)]
enum Entry {
    ServerDef(Server),
    MetricDef(Metric),
}
```

The variant name is the model's variant name — the UpperCamel of the alternative's single label,
or `Alt<N>` when it carries more than one, renameable with the sidecar's `variant`. The content
is the alternative's payload: the referenced rule's shape where the alternative is one labeled
reference, and a map of the alternative's own fields otherwise.

A sum alternative or a fold link declared as a **unit** variant is refused rather than accepted
with everything it carries discarded:

```text
variant "Operand" carries content, found a map, expected a unit variant at line 1, column 1
```

### Folds are nested chains

A `fold_left:` / `fold_right:` rule serves the chain the AST layer builds:

```rust
#[derive(Deserialize)]
enum Expr {
    Operand(Term),
    Binary { op: Op, lhs: Box<Expr>, rhs: Box<Expr> },
}
```

Definable, but the blessed route for an expression sub-language is an
[AST-typed field](#ast-typed-fields): FLTK already generates that chain type, with its
non-recursive teardown and equality.

### Enum-shaped rules

```
metric_type := counter:"counter" | gauge:"gauge" | histogram:"histogram" ;
```

```rust
#[derive(Deserialize)]
enum Kind { Counter, Gauge, Histogram }
```

A `String` target gets the **variant name**, not the literal the source spelled, so sidecar
`variant` renames and `rename_all` on the target agree with the enum form. With `bool: <label>;`
the rule is a boolean instead.

## Scalars read source text

`deserialize_u16` — and every other numeric width — runs the corresponding `fltk-ast-core`
scalar gate over the node's own span text, on **any** node, not only a terminal-only one. The
CST span *is* the lexeme.

Consequences:

- The accepted lexemes, range refusals and message templates are exactly those of a `type:`
  coercion in the AST layer. One gate, one wording, both layers.
- The sidecar's `type:` is **not needed** on this path and is ignored by the frontend — the
  target struct is the type schema. (Its one exception is a `type:` resolving a *key* field; see
  [Key identity](#key-identity).)
- A node whose span legitimately contains interior separators fails the gate, and the message
  names the text it refused. That is a grammar-design property, and the most common way to meet
  it is aiming a scalar at the wrong node:

```text
rule "setting": "port = 8080;\n" is not a valid u16 at line 2, column 1
```

  — a `u16` aimed at a whole keyed *element* rather than at its value.

- `String` / `&str` likewise serve span text, with `text_from:` honored, which is how the
  quote-stripping idiom (`quoted := %"'" . value:/[a-z]+/ . %"'"` with `text_from: value;`)
  shapes both layers at once. `char` requires a one-character text.
- `bool` is served by a presence flag and by a `bool:`-shaped rule only. A terminal whose text
  happens to be `true` is a string:

```text
expected a boolean, found a string at line 1, column 8
```

- Self-parsing target types (`uuid::Uuid`, chrono types, …) deserialize from the string we serve
  and apply their own parse rules — the same trust model as serde_json / toml. The grammar's
  terminal regex remains the first gate on what text can appear at all.

## Keyed regions

`key: <label>;` on an element rule says "collections of this rule are keyed by `<label>`". The
statement, its rules and its conflicts are documented in
[the sidecar reference](ast-guide.md#key-and-key--multi); this section is what the serde path
does with it.

### Map or sequence — the target chooses

The same region serves both, and the declared type picks:

```rust
// map form: one entry per key, the key field omitted from the value
struct Server { name: String, settings: BTreeMap<String, SettingValue> }
#[derive(Deserialize)] struct SettingValue { value: Val }

// sequence form: the plain elements in source order, key included as an ordinary field
struct Rows   { name: String, settings: Vec<Row> }
#[derive(Deserialize)] struct Row { key: String, value: Val }
```

The map form is also what a struct target reads, which is the point of the whole layer: a
`#[serde(deny_unknown_fields)]` struct over a keyed region turns an unknown key into
`unknown field …, expected one of …` at the offending key's own position.

**The key is omitted from the value's fields.** It is the map key; carrying it in the value
struct as well would fight `deny_unknown_fields`. So the value of an entry is the element rule's
shape *minus* the key field — which is why the quick start's target has a `Value<T>` level. If
you would rather see the key beside the rest, ask for the sequence form.

The sequence form is also the interleaving-preserving escape: it has no identity and no
duplicate check, and elements arrive in source order.

### Key identity

Key identity is **declaration-driven**, not target-driven: it comes from the key's resolved type
in the sidecar, and is therefore the same for every target reading that source.

- A **text** key (the default) groups and refuses duplicates by the key child's source text, and
  is served as a string.
- An **integer** key — declared with `type: <int>;` on the (transparent) key rule, exactly as the
  AST layer requires for integer-keyed maps — normalizes each key text through that gate, so `7`
  and `007` are one key, and is served at the declared width. serde's own integer forwarding
  fits it to the target's key type, so a `struct Id(u16)` newtype key works too.

To key a region by integers, declare it. A target whose key type disagrees with the declaration
gets serde's own invalid-type error at the key child rather than a silent fall back to text
identity. The sidecar admits text and the eight integer widths as key types and nothing else
(floats and node types are refused at generation time), so no other key identity can arise.

### Duplicates

Without `multi`, a repeated key is refused by the frontend *before* the target sees either
element — a container's own `Deserialize` (`HashMap`, `IndexMap`, `BTreeMap`) would silently
last-write-win:

```text
duplicate setting key "host" at line 2, column 1
```

with `("previously defined here", <span of the first one>)` in `related`. This is the AST layer's
own template and the AST layer's own refusal, on the serde path.

### `multi`

`key: <label> multi;` makes elements sharing a key accumulate instead:

```rust
#[derive(Deserialize)]
struct Document {
    settings: BTreeMap<String, Vec<Value>>,
}
```

```text
tag = a;    →   { "tag": [a, b], "name": [x] }
name = x;
tag = b;
```

A key takes its place where its first element appeared, elements keep source order within the
group, and under an integer key identity two spellings of one value merge into one group. The
sequence form is unchanged.

`multi` is a language-level decision, not only a target one: grouping loses global interleaving,
so a value written back out through the AST layer's `to_cst` renders in grouped order. See
[the AST guide](ast-guide.md#key-and-key--multi).

## Positions: `Spanned` and `Raw`

Two wrapper types carry what a grammar cannot produce as content. Both ride a private
newtype-struct protocol recognized by FLTK's own Deserializer, and both fail loudly rather than
degrade when that protocol cannot reach it (see [Buffering adapters](#buffering-adapters)).

### `Spanned`

```rust
#[derive(Deserialize)]
struct Located {
    name: fltk_serde_core::Spanned<String>,
}

let position = located.name.span().line_col_inner().expect("a parsed span locates itself");
println!("{} at line {}", located.name.value(), position.line + 1);
```

`Spanned<T>` derefs to `T`, so the rest of your code reads as if it were not there. Fields opt in
one at a time, so you pay for positions only where you want them.

**Spans never take part in equality** — the same doctrine the generated AST types follow. Two
values read from different files compare equal.

Over a collection or a keyed field, the span covers the elements it holds
(`Span::unknown()` when there are none). Over an absent optional flag it is `Span::unknown()`:
something that was never written has no location.

### `Raw`

`Raw<cst::T>` is a refusal to deserialize: it holds the CST node itself — full fidelity,
source-backed spans — for template bodies, macro arguments and other "define now, expand later"
content.

```rust
#[derive(Deserialize)]
struct Held {
    body: fltk_serde_core::Raw<cst::Expr>,
}

// later, when you know what it means:
let value: MyExpr = de::from_expr_cst(held.body.node())?;
```

`Raw<T>` is a cheap handle (an `Arc` clone), compares by deep CST equality where the node type
does, and never walks the deserializer it is handed. A `Raw` whose rule does not match the
position it sits at fails with both ends named:

```text
expected a `mylang::cst::Num` node for Raw, found rule `name`
```

A `Raw` over a `transparent;`-typed field holds the erased rule's *own* node — `Raw` is CST
fidelity, and the erasure the AST layer performs does not reach it.

## AST-typed fields

With `--ast-mod-path`, a field can be declared as a generated AST type and is spelled like any
other serde field:

```rust
#[derive(Deserialize)]
struct Config {
    exprs: ::fltk_ast_core::IndexMap<String, ast::Expr>,
}
```

What it means is that rule's `from_cst`, so folds, transparent chains, `type:` coercions and
every future AST behavior come along with no shape logic duplicated on this path. A `from_cst`
failure keeps its own message and span.

Three things to know:

- **Impls are per *rule* with a public AST type.** A `transparent;` or `flatten;` rule has no
  public type (its use sites carry the payload) and a `custom(...)` rule's type is yours, so
  neither gets one. The AST module's other exports — a sum variant's generated payload class, a
  value enum, a **field enum for a union label** — are not rules and get no impl either;
  declaring one is a "the trait `Deserialize` is not implemented" at your compile time. Name the
  rule's own type instead, which is the type that reaches all of them.
- **A mismatch is a deserialize-time error**, naming the expected rule and the actual one.
- **At a keyed region's map-entry value, the AST type converts the whole element**, key field
  included. The map form omits the key from the *fields* it serves; `from_cst` is a different
  mapping and the AST type of the element rule has the key as a member.

Like the wrappers, AST types deserialize only under FLTK's own Deserializer.

## Errors

| | Type |
|---|---|
| Deserialization failure | `fltk_serde_core::DeserializeError` |
| `from_str` failure | `fltk_serde_core::ParseToTargetError::{Parse, Deserialize}` |

`DeserializeError` carries three things — `message`, `span`, and `related`, a list of secondary
locations with their own explanations — mirroring `AstError`, which it converts from.

`Display` / `to_string()` renders **the message and the primary position only**: `"… at line L,
column C"` when the span resolves one, the bare message when it does not. Secondary locations are
carried, not rendered; a diagnostic renderer walks `related` itself:

```rust
match de::from_str::<Config>(&text, Some("app.conf")) {
    Err(ParseToTargetError::Deserialize(err)) => {
        eprintln!("{err}");
        for (note, span) in &err.related {
            eprintln!("  {note}: {span:?}");
        }
    }
    Err(ParseToTargetError::Parse(message)) => eprintln!("{message}"),
    Ok(config) => { /* … */ }
}
```

### Where a position comes from

serde's derive raises unknown-field, missing-field and invalid-type errors through
`serde::de::Error`, which carries no position. The frontend fills one in at the three places it
re-enters its own frames:

| Phase | Gets the span of | Typical message |
|---|---|---|
| Key | the offending child | ``unknown field `prot`, expected one of `host`, `port`, `verbose` at line 2, column 1`` |
| Value | the value child | `rule "word": "99999" is not in range for u16 (0 to 65535) at line 2, column 8` |
| End of a struct | the node itself | ``missing field `verbose` at line 1, column 1`` |

A position is filled in **only if the error does not have one already**, so an error raised deep
inside a value keeps its precise span and an outer frame's coarser one does not overwrite it.

The message text is serde's where serde raised it and FLTK's where FLTK did. The FLTK-owned
templates — the duplicate-key refusal, the scalar gates, the arity refusals — are shared with the
AST layer, so the two layers say the same thing about the same problem.

## The supported serde surface

**Externally tagged enums are the contract.** That is what the derive produces by default and
what sums, folds and enum-shaped rules serve.

| Target shape | Behavior |
|---|---|
| `#[serde(deny_unknown_fields)]` | Recommended — this is where the frontend's headline diagnostic comes from |
| `Option<T>` | Absent optional child → `None` |
| `Vec<T>` on a repeatable label | Always served, empty when there are no children; no `#[serde(default)]` needed |
| Tuples, tuple structs, tuple variants | Refused: `tuple targets are not supported by the FLTK serde frontend` |
| `&[u8]` / byte buffers | Refused: `byte targets are not supported by the FLTK serde frontend` |
| `i128` / `u128` | Refused by serde itself (`i128 is not supported`), positioned by FLTK |
| Internally / adjacently tagged enums | Not supported. serde routes them through its buffering representation (below): plain data may happen to work, the wrappers and AST types will not |
| `#[serde(untagged)]` enums | Same: plain data works, the wrappers and AST types do not (below) |
| `deserialize_any` targets (`serde_json::Value` and friends) | Served the self-describing shape from the table above. A keyed region is resolved to the **map form**, with the declared key type |
| Skipped fields | `deserialize_ignored_any` succeeds without walking anything, so a field the target ignores costs nothing and cannot fail |

### Buffering adapters

serde's derive buffers a value into its own representation and re-deserializes it from there
wherever it cannot know the target up front: **every field of a `#[serde(flatten)]`ed struct**,
and **every variant of an untagged enum**. That representation carries no newtype-struct name,
so the `Spanned` / `Raw` / AST-type protocol never reaches the Deserializer — even though the
source *is* FLTK's and the call is one `from_str`. The failure is loud and names the cause:

```text
Spanned<T> requires deserializing directly from FLTK source: neither a foreign Deserializer nor
an adapter that buffers the value first (`#[serde(flatten)]`, untagged enums) carries the
protocol it rides on
```

Inside an untagged enum, serde swallows the inner error and reports `data did not match any
variant`, so the message above may not survive; the variant simply does not match.

Plain data inside those adapters is fine. Keep `Spanned`, `Raw` and AST-typed fields outside
them.

### Shape checking is parse-time only

There is no generation-time check that your grammar and your target types agree — the target
types exist only at *your* compile time. A disagreement surfaces as a positioned deserialize
error at runtime, exactly as it does with serde_json and toml.

## Worked example: from one-key rules to a generic region

The shape this layer exists for. **Before** — every option is its own grammar rule:

```
channel_def     := "channel" : name:identifier , "{" , channel_option* , "}" , ;
channel_option  := option_protocol | option_port | option_verbose ;
option_protocol := "protocol" , ":" , value:identifier , ";" , ;
option_port     := "port"     , ":" , value:number     , ";" , ;
option_verbose  := "verbose"  , ":" , value:boolean    , ";" , ;
```

Adding an option means editing the grammar, regenerating, and updating whatever consumes the new
node type. A misspelled key is not a key at all — it is a syntax error, and the parser reports it
as an unexpected token where the closing brace was expected, with nothing to say about `protocol`
or `port`.

**After** — one generic entry rule, and the keys live in the consumer's struct:

```
channel_def    := "channel" : name:identifier , "{" , channel_option* , "}" , ;
channel_option := key:identifier , ":" , (value:boolean | value:word) , ";" , ;
identifier     := text:/[a-z_][a-z0-9_]*/ ;
word           := text:/[a-zA-Z0-9_.]+/ ;
boolean        := true:"true" | false:"false" ;
```

```
rule identifier    { transparent; }
rule word          { transparent; }
rule boolean       { bool: true; transparent; }
rule channel_option { key: key; }
```

The leaf shaping is the quick start's and is not optional here: a `key:` label must resolve to
text or to an integer, so the rule it references has to be `transparent;` (a key that still has a
node type is a generation error), and `Value<bool>` needs the `bool: true;` that makes `boolean`'s
value a boolean rather than a string.

```rust
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ChannelOptions {
    protocol: Value<String>,
    port: Value<u16>,
    verbose: Option<Value<bool>>,
}
```

```text
unknown field `prot`, expected one of `protocol`, `port`, `verbose` at line 4, column 5
```

Adding an option is now a field on a struct. Required vs optional is `Option<T>`. The value's
type is the field's type, checked by the same gates the AST layer's `type:` uses. The grammar
stopped growing a rule per key, and the diagnostic improved rather than degraded.

## Compatibility

The generated module is **public API for out-of-tree consumers** (CLAUDE.md), and so is what it
serves:

- **Accepted lexemes** = the grammar's terminals ∩ the `fltk-ast-core` scalar gates. Changing a
  gate changes what parses downstream.
- **Field names** are the model's field names (labels after sidecar renames); **variant names**
  are the model's variant names; **externally tagged** is the sum contract. Renaming a rule, a
  label or a sidecar-driven name is a breaking change for every target written against it.
- **Keyed-region acceptance is declaration-driven and target-independent**: the same source gets
  the same accept/refuse verdict into any map target.
- **Error text**: the FLTK-owned templates (duplicate key, the scalar gates, the `line`/`column`
  rendering) are stable surface. The serde-derive-owned phrasing (unknown field, missing field)
  is serde's and is not ours to stabilize.
- **The generator and `fltk-serde-core` are released in lockstep** (same repo, same version). The
  description vocabulary a generated `de.rs` is written against is public-but-internal protocol
  between the two; regenerating with a newer FLTK against an older pinned runtime fails at
  compile time, which is the intent.

## Runtime dependencies

| Dependency | Notes |
|---|---|
| `serde` | With the `derive` feature, for your own targets |
| `fltk-serde-core` | pyo3-free. Re-exports everything else the generated module names, including the scalar gates |

A `de.rs`-only consumer needs no other FLTK crate: `fltk-serde-core` re-exports what the
generated module refers to, so there is one version of everything. A crate that also compiles
`ast.rs` adds `fltk-ast-core`, and every generated CST crate already has `fltk-cst-core`.

Generated Rust names the runtime by absolute path (`::fltk_serde_core::…`), so a rule called
`error` or `span` cannot collide with anything your preamble imported.
