# `.fltklsp` — proposed syntax and semantics

Design goal: one small sidecar file per grammar that drives syntax highlighting (phase 1)
and definitions/references (phase 2). The full syntax is designed now so phase 1 files
remain valid, unchanged, when phase 2 lands.

Style: the `.fltkfmt` language family — `//` line comments, statements terminated by `;`,
global statements plus `rule <name> { ... }` override blocks, anchors naming grammar
positions. Every rule name, label, and literal anchor is validated against the loaded GSM;
an anchor that matches nothing in the grammar is a load error (typos cannot silently
no-op — the property spelling-based highlighting systems can never offer).

## 1. Anchors

Same resolution as `.fltkfmt`, canonicalized on grammar names:

```
anchor := label | rule_name | literal
```

- Inside a `rule X { ... }` block, an identifier anchor matches items of `X`: first as a
  label, then as an unlabeled invoked-rule name. A literal anchor matches that literal item.
- At global scope, an identifier anchor matches: a label (anywhere in the grammar), or a
  rule (every node of that rule). If a name is both a label and a rule name in the grammar,
  the spec must disambiguate with an explicit prefix: `label:name` / `rule:name`.
- A global literal anchor matches that literal everywhere.

Known inherited limitation: two unlabeled invocations of the same rule within one
alternative are not independently addressable (same as `.fltkfmt`). Mitigation: label them
in the grammar. The loader warns on this ambiguity when an anchor hits it.

## 2. Highlighting: the `scope` statement

```
scope <anchor> ("," <anchor>)* ":" <scope-name> ";"
```

`scope-name` is a dotted name. The first segment must be a known token type (else load
error); remaining segments map to LSP semantic-token modifiers when they match standard
modifier names, and are otherwise carried as theme hints (used by the standalone
highlighter, dropped in LSP output).

Token types (initial legend): `keyword`, `comment`, `string`, `number`, `operator`,
`punctuation`, `variable`, `parameter`, `property`, `type`, `function`, `enumMember`,
`constant`, `macro`, `label`, `text`, and the special value `none` (suppress).

Examples:

```
scope doc: comment;                 // whole doc subtree, every occurrence
scope typespec: type;               // every item labeled `typespec`, grammar-wide
scope boolean, unit_identifier: constant;

rule condition_spec {
    scope "time_since_last_exec", "any_message", "new_message": function.builtin;
}
```

### 2.1 Classification semantics (painter's rules)

Classification happens per CST occurrence, from the parsed tree ("parse-then-paint"):

1. A `scope` statement paints the **entire span** of each matched node/item, including
   descendants.
2. **Explicit beats default.** Inside the span of any explicitly-scoped node, built-in
   defaults (§2.2) are suppressed entirely (so `scope doc: comment;` yields one uniform
   comment span; the `"//"` literal inside doesn't repaint as punctuation).
3. **Innermost explicit wins.** An explicit scope on a descendant overrides an ancestor's
   explicit scope within the descendant's span (so you can re-highlight pieces inside a
   painted region by adding inner statements).
4. Among explicit statements matching the *same* node: rule-block beats global; within the
   same tier, label/literal anchor beats rule-name anchor; remaining ties: the later
   statement in the file wins.
5. `none` is explicit: it suppresses both defaults and inherited paint for that span.

### 2.2 Built-in defaults

Applied wherever no enclosing explicit scope exists — an empty `.fltklsp` still yields a
usable baseline:

| Grammar element | Default token |
|---|---|
| Node of a trivia rule (`is_trivia_rule`) | `comment` |
| `Literal` matching `[A-Za-z_][A-Za-z0-9_]*` (incl. multi-word literals starting so) | `keyword` |
| Other `Literal` in `( ) [ ] { } , ; : .` | `punctuation` |
| Other `Literal` | `operator` |
| `Regex` whose pattern is quote-delimited | `string` |
| `Regex` whose pattern leads with a digit class | `number` |
| `Regex` matching identifier shape | `variable` |
| Any other `Regex` | `text` |

## 3. Definitions and references (phase 2 syntax, reserved now)

Three statements, valid only inside `rule` blocks (a def/ref is meaningless without the
producing rule for its declaration node):

```
def <anchor> ":" <kind> ";"
ref <anchor> ":" <kind> ("," <kind>)* ";"
namespace ";"
```

- **`def`** — each matched occurrence defines a symbol. The symbol's *name* is the anchor
  node's span text; its *selection range* is that span; its *declaration range* is the span
  of the enclosing rule node (drives document-symbol outlines). `<kind>` is a dotted name;
  the first segment maps to an LSP `SymbolKind` via a fixed table (`type`→Class,
  `function`→Function, `variable`→Variable, `constant`→Constant, `field`→Field,
  `enumMember`→EnumMember, `namespace`→Namespace, …; unknown first segments map to Object
  and remain usable as exact-match ref targets).
- **`ref`** — each matched occurrence is a reference resolving against symbols of any
  listed kind. Kinds match by prefix on the dotted name (`ref identifier: type;` sees
  `type.cog` and `type.schema` defs). The wildcard `*` means "any kind" (pure
  rename/find-references participation).
- **`namespace`** — the rule's node introduces a lexical scope: symbols defined in its
  subtree are visible only within it; resolution walks outward to file scope. Without any
  `namespace`, the file is one flat scope.

Defs/refs also feed highlighting: a def site with no explicit `scope` inherits its kind's
token type plus the `declaration` modifier; a resolved ref inherits the defining kind's
token type. (Explicit `scope` always wins.)

Cross-file resolution is **out of scope for this language.** A per-language Python resolver
hook (loaded by the server) maps unresolved references + the file's import constructs to
other files. Absent a resolver, all features degrade to same-file behavior.

## 4. Worked example: clockwork

```
// clockwork.fltklsp
scope doc: comment;

scope typespec, config_type, signal_type, input_type, output_type, state_type: type;
scope boolean, unit_identifier: constant;
scope string_literal: string;                    // default gets this; explicit for clarity
scope nonnegative_integer, integer, number: number;

rule condition_spec {
    scope "time_since_last_exec", "any_message", "new_message": function.builtin;
}
rule channel_option_publishers {
    scope "single", "multiple", "diagnostics", "bridge_status", "c2c_bridge_status": enumMember;
}
rule clk_generate_target { scope cpp, proto, go_proto, py, nanobind: macro; }

// --- phase 2 ---
rule cog        { def identifier: type.cog;      namespace; }
rule python_cog { def identifier: type.cog;      namespace; }
rule schema     { def identifier: type.schema;   namespace; }
rule enum       { def identifier: type.enum;     namespace; }
rule strong_type{ def identifier: type; }
rule tag        { def identifier: type.tag; }
rule channel    { def identifier: variable.channel; }
rule box        { def identifier: type.box;      namespace; }
rule schema_field { def name: field; }
rule enum_value   { def name: enumMember; }
rule new_stmt     { def identifier: variable; }
rule use_alias    { def alias: type; }

rule expr             { ref identifier: *; }
rule signal_reference { ref identifier: variable.signal; }
```

~30 lines for full highlighting plus outline/nav coverage of a large real grammar. Note the
things *only* the sidecar could know: `doc` is a comment (it's not trivia), `typespec`
exprs are types, `s`/`ms` are constants not keywords, entity heads are definitions.

## 5. Grammar sketch (`fltklsp.fltkg`)

Shares lexical tail conventions with `unparsefmt.fltkg`:

```
lsp_spec := , statement* ;
statement := scope_stmt | rule_config ;

rule_config := "rule" , rule_name:identifier , "{" , ( rule_statement , )* , "}" , ;
rule_statement := scope_stmt | def_stmt | ref_stmt | namespace_stmt ;

scope_stmt := "scope" : anchor_list , ":" , scope:scope_name , ";" , ;
def_stmt   := "def" : anchor , ":" , kind:dotted_name , ";" , ;
ref_stmt   := "ref" : anchor , ":" , kind_list , ";" , ;
namespace_stmt := "namespace" , ";" , ;

anchor_list := anchor , ( "," , anchor )* ;
anchor := ( qualifier:("label" | "rule") . ":" . )? name:identifier | literal ;
scope_name := none:"none" | dotted_name ;
kind_list := ( wildcard:"*" | dotted_name ) , ( "," , dotted_name )* ;
dotted_name := identifier . ( "." . identifier )* ;

identifier := name:/[a-zA-Z_][a-zA-Z0-9_]*/ ;
literal := value:/("([^"\n\\]|\\.)+"|'([^'\n\\]|\\.)+')/ ;

_trivia := ( line_comment | line_comment? : )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . newline:"\n" ;
```

## 6. Open questions

1. **Qualified-name resolution** — clockwork's `dotted_identifier` / `namespaced_identifier`
   (`ns::Type`, `a.b.c`): should the language grow a `qualified ref` form ("resolve segment
   1 in file scope, subsequent segments inside the previous symbol's namespace"), or is
   that resolver-hook territory from day one?
2. **Multi-def rules** — a rule defining several symbols of different kinds (rare; none in
   clockwork). Multiple `def` statements with distinct anchors cover it; is per-anchor
   disambiguation (§1 limitation) ever insufficient in practice?
3. **TextMate export** — with a `.fltklsp` in hand, a lossy `.tmLanguage.json` exporter
   (safe classes + opt-in keyword spellings) becomes possible for editors without LSP
   clients. Worth building, or does the standalone highlighter + LSP cover real needs?
4. **Completion** — keyword completion falls out of the grammar (expected-token sets at a
   position); symbol completion falls out of defs. Neither needs new syntax, but both need
   server design (reusing `ErrorTracker`'s expected-set machinery speculatively).
5. **Scope-name vocabulary** — frozen legend vs. extensible-with-declaration
   (`token mytype extends type;`). Start frozen; revisit on demand.
