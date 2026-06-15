# FLTK Grammar Language (`.fltkg`) — Syntax & High-Level Semantics

Syntax/high-level layer for the persistent FLTK grammar reference. Every construct is
grounded in code. Deep parser/CST mechanics are deferred to the code-level pass; this pass
fixes the surface (what you can write) and its meaning (what each construct does to the
parser and CST).

Primary sources read in full:
- `fltk/fegen/fegen.fltkg` — the FLTK grammar **for** FLTK grammars (self-describing; the
  authoritative syntax definition).
- `fltk/fegen/gsm.py` — Grammar Semantic Model; the semantic data structures and validators.
- `fltk/fegen/bootstrap.fltkg` and `fltk/fegen/fltk.fltkg` — bootstrap and extended (partly
  aspirational) grammar variants.
- `fltk/fegen/fltk2gsm.py` — `Cst2Gsm`: maps the parsed grammar CST → GSM; this is where
  defaulting rules (disposition defaults, label-from-identifier) live.
- `fltk/fegen/gsm2tree.py` — `CstGenerator`: maps GSM → generated CST node classes (the
  public-API surface).
- `fltk/fegen/gsm2parser.py` — `ParserGenerator`: maps GSM → parser; separator/trivia semantics.
- `fltk/fegen/naming.py` — `snake_to_upper_camel`, the name-derivation function.
- Consumer/fixture grammars: `fltk/unparse/toy.fltkg`, `fltk/unparse/unparsefmt.fltkg`,
  `fltk/fegen/test_data/{poc_grammar,rust_parser_fixture,phase4_roundtrip,collision_fixture}.fltkg`.

---

## 1. The self-describing grammar

The canonical syntax spec is `fltk/fegen/fegen.fltkg` (22 lines). It is a `.fltkg` grammar
that describes `.fltkg` grammars. Reproduced verbatim (`fegen.fltkg:1-22`):

```
grammar := , rule+ ;
rule := name:identifier , ":=" , alternatives , ";" , ;
alternatives := items , ( "|" , items , )* ;
items :=
  ( no_ws:"." | ws_allowed:"," | ws_required:":" )? ,
  item ,
  ( ( no_ws:"." | ws_allowed:"," | ws_required:":" ) , item , )* ,
  ( no_ws:"." | ws_allowed:"," | ws_required:":" )? ,
  ;
item := ( label:identifier . ":" )? . disposition? . term . quantifier? , ;
term :=
  identifier | literal | "/" . regex:raw_string . "/" | "(" , alternatives , ")" ;
disposition := suppress:"%" | include:"$" | inline:"!" ;
quantifier := optional:"?" | one_or_more:"+" | zero_or_more:"*" ;
identifier := name:/[_a-z][_a-z0-9]*/ ;
raw_string := value:/([^\/\n\\]|\\.)+/ ;
literal := value:/("([^"\n\\]|\\.)+"|'([^'\n\\]|\\.)+')/ ;
_trivia := ( line_comment | line_comment? : | block_comment )+ ;
line_comment := prefix:"//" . content:/[^\n]*/ . "\n" ;
block_comment := start:"/*" . content:/(?:[^*]|\*+[^\/\*])*/ . end:/\*+\// ;
```

This file is both the spec and a worked example of every construct. The remaining sections
read it construct-by-construct and tie each to its GSM and code-generation meaning.

`bootstrap.fltkg` is a near-identical, slightly older variant (no `ws_required:":"` third
separator; `_trivia` is a plain alternation rather than the `( ... )+` form;
`block_comment` uses literal `start`/`end` rather than regex `end`). `fltk.fltkg` is an
**extended, explicitly-incomplete** variant ("This grammar is actually broken and was never
completed", `fltk.fltkg:2`) that sketches additional constructs — `invocation`,
`expression`/`add`, and `var` (`let X : Stack[String]`) — corresponding to the
`Invocation`/`Expression`/`Add`/`Var` GSM types (`gsm.py:267-288`) that are **not** wired
into the active pipeline. Treat `fegen.fltkg` as ground truth for what the toolchain
currently parses.

---

## 2. Lexical structure

A grammar is plain UTF-8 text. There are no statement keywords; structure comes entirely
from the operators `:=`, `;`, `|`, the separators `. , :`, dispositions `% $ !`,
quantifiers `? + *`, parentheses, quotes, and `/.../` regex delimiters.

Span offsets are **codepoint-indexed, not byte-indexed** — multibyte literals and regexes
are supported and span offsets count characters (`rust_parser_fixture.fltkg:39-45`, the
`arrow := %"→"` and `latin_word := /[À-ÿ]+/` fixtures pin this).

### 2.1 Identifiers (rule names / labels)
`identifier := name:/[_a-z][_a-z0-9]*/ ;` (`fegen.fltkg:16`). Lowercase snake_case:
must start with `_` or `a-z`, then `_`, `a-z`, `0-9`. No uppercase, no leading digit.
(The aspirational `fltk.fltkg:87` and `unparsefmt.fltkg:87` define a looser identifier
regex allowing uppercase, but `fegen.fltkg` — the live spec — is lowercase-only.)

### 2.2 Literals (string terminals)
`literal := value:/("([^"\n\\]|\\.)+"|'([^'\n\\]|\\.)+')/ ;` (`fegen.fltkg:18`).
A literal is a double- or single-quoted string. Backslash escapes allowed; the string may
not span a newline and may not be empty (the `+` requires ≥1 char). The captured text is
later decoded with `ast.literal_eval` (`fltk2gsm.py:166`), so Python string-escape rules
apply (`\n`, `\t`, `\"`, etc.). Examples: `":="`, `"|"`, `"//"`, `'group'`.

### 2.3 Regexes
`term ... | "/" . regex:raw_string . "/" | ...` with
`raw_string := value:/([^\/\n\\]|\\.)+/ ;` (`fegen.fltkg:13,17`). A regex term is written
between `/` delimiters; the inner text is a `raw_string` (any char except unescaped `/`,
newline, or `\`; `\.` escapes allowed). The raw text is stored verbatim as `gsm.Regex.value`
(`fltk2gsm.py:168-170`) and compiled with Python `re` (`gsm.py:168`). Examples:
`/[0-9]+/`, `/[_a-z][_a-z0-9]*/`, `/\s+/`.

### 2.4 Comments / trivia
Comments are defined **as grammar rules** in the trivia rule, not as built-in lexer syntax
(`fegen.fltkg:19-21`):
- `line_comment := prefix:"//" . content:/[^\n]*/ . "\n" ;` — `//` to end of line.
- `block_comment := start:"/*" . content:/(?:[^*]|\*+[^\/\*])*/ . end:/\*+\// ;` — `/* ... */`.

See §8 for how the `_trivia` rule governs whitespace/comment handling globally.

---

## 3. Rule definitions (`:=`) and grammar structure

`grammar := , rule+ ;` (`fegen.fltkg:2`): a grammar is one or more rules, with a leading
`,` (WS_ALLOWED) so leading whitespace/comments are tolerated.

`rule := name:identifier , ":=" , alternatives , ";" , ;` (`fegen.fltkg:3`): a rule is
`name := <alternatives> ;`. The `:=` separates name from body; `;` terminates. GSM:
`gsm.Rule(name, alternatives)` (`gsm.py:27-40`), where `name` is the rule's identifier and
`alternatives` is a `Sequence[Items]` (one `Items` per `|`-alternative).
`Cst2Gsm.visit_rule` (`fltk2gsm.py:18-22`) builds it; `Grammar.identifiers` is a
`name → Rule` map (`gsm.py:22-24`, built in `visit_grammar`, `fltk2gsm.py:14-16`).

**Rule → generated artifacts (high-level mapping):**
- Each rule generates **one CST node class** named by `snake_to_upper_camel(rule_name)`
  (`gsm2tree.py:46-47`, `class_name_for_rule_node`). E.g. `line_comment` → `LineComment`.
- Each rule contributes **one `NodeKind` enum member**, the uppercased class name
  (`gsm2tree.py:95-97`, `node_kind_member_name`; enum built in `_node_kind_enum`,
  `gsm2tree.py:134-143`). E.g. `LineComment` → `NodeKind.LINECOMMENT`.
- Each rule generates **one parser method** (a packrat/memoized recursive-descent parser;
  the parser supports left recursion — `rust_parser_fixture.fltkg:30-37` exercises direct
  and indirect left recursion as a pinned fixture).

**Name-derivation contract** (`naming.py:7-22`, `snake_to_upper_camel`): lowercase the whole
string, split on `_`, `capitalize()` each segment, join. Consecutive/leading/trailing
underscores collapse (`a__b → AB`, `_foo_bar → FooBar`, `foo_ → Foo`). A name consisting of
only underscores derives to `""` and is **rejected** by `validate_no_underscore_only_names`
(`gsm.py:323-345`) for both rule names and labels — but `_foo`-style names are fine. This is
why the trivia rule `_trivia` (leading underscore) is legal.

---

## 4. Alternation (`|`) and sub-expressions (parentheses)

`alternatives := items , ( "|" , items , )* ;` (`fegen.fltkg:4`): one or more
`items` sequences separated by `|`. Each alternative is a separate `gsm.Items`
(`fltk2gsm.py:47-48`, `visit_alternatives` → list of `Items`). A rule's body is its list of
alternatives; a sub-expression's body is likewise a list of alternatives.

**Sub-expressions** are a `term` form: `"(" , alternatives , ")"` (`fegen.fltkg:13`). A
parenthesized group is a nested `alternatives` — i.e. a `Sequence[Items]` term
(`gsm.py:175-181`, `Term` union includes `Sequence[Items]`; built at `fltk2gsm.py:131-132`).
Sub-expressions:
- May contain their own `|` alternation and their own internal separators
  (`rust_parser_fixture.fltkg:59-61`, `grouped := %"(" , (left:num | left:name) , %")"`).
- Carry an **implicit `include` disposition** when no explicit disposition is given
  (`fltk2gsm.py:119`: `if label or isinstance(term, Sequence): disposition = INCLUDE`).
- Are recursed into for child-model construction (`gsm2tree.py:620-621`,
  `model_for_item` → `model_for_alternatives`), and for trivia-reachability /
  validation walks (`gsm.py:300-302`, `_for_each_item`; `gsm.py:400-403`).

**Nil/empty semantics** (used by validators): a rule is nil if **any** alternative is nil
(`gsm.py:59`); an `Items` is nil iff its initial separator is nil and every item and its
trailing separator are nil (`gsm.py:96-117`); a parenthesized term is nil if **any** of its
alternatives is nil (`gsm.py:188-190`).

---

## 5. Items and separators (`.` `,` `:`) — whitespace semantics

`items` (`fegen.fltkg:5-10`) is the core sequencing construct: an optional **leading**
separator, then a sequence of `item`s each preceded (after the first) by a separator, then
an optional **trailing** separator. The three separators are mutually exclusive choices at
each slot: `no_ws:"."`, `ws_allowed:","`, `ws_required:":"`.

GSM representation: `gsm.Items(items, sep_after, initial_sep)` (`gsm.py:82-93`).
- `initial_sep`: the leading separator, default `Separator.NO_WS` (`gsm.py:93`).
- `sep_after[i]`: the separator that follows `items[i]`.
- `Separator` enum: `NO_WS`, `WS_REQUIRED`, `WS_ALLOWED` (`gsm.py:66-69`).

`Cst2Gsm.visit_items` (`fltk2gsm.py:50-106`) parses the interleaved item/separator stream:
detects a leading separator, then walks item/sep pairs, defaulting a missing trailing
separator to `NO_WS` (`fltk2gsm.py:93-102`).

**Whitespace meaning of each separator** (the operative semantics, from the parser
generator `_gen_separator_handling`, `gsm2parser.py:620-697`):

| Token | `Separator` | Between items: trivia (whitespace/comments)... |
|-------|-------------|-----------------------------------------------|
| `.`   | `NO_WS`     | **not consumed** — items must be adjacent. Generator emits no separator code (`gsm2parser.py:642-643`). |
| `,`   | `WS_ALLOWED`| **optional** — trivia consumed if present; absence is fine (`orelse` is not a failure). |
| `:`   | `WS_REQUIRED`| **required** — trivia must be present, else the parse fails at that point (`gsm2parser.py:696-697` returns `Failure` when `WS_REQUIRED` and no trivia matched). |

Separator nil-ness (`gsm.py:71-79`, `Separator.can_be_nil`): `NO_WS` and `WS_ALLOWED` are
nil-able; `WS_REQUIRED` is **never** nil (it forces a trivia match, and the trivia rule
itself cannot be nil — see §8). This is why a leading/trailing `:` makes an `Items`
non-nilable (`gsm.py:102-103`).

The leading separator handles whitespace before the first item; the trailing separator
handles whitespace after the last (commonly seen as the trailing `,` on most rules in
`fegen.fltkg` and `unparsefmt.fltkg`, allowing whitespace/comments before the next `;` or
construct). Real grammars use all three:
`stmt := lhs:atom : "=" : rhs:atom ;` (`rust_parser_fixture.fltkg:19`, WS_REQUIRED around
the operator); `from_spec := "from" : ( after:"after" : )? . from_anchor:anchor ;`
(`unparsefmt.fltkg:40`, mixing `:` and `.`).

Whitespace separators in a rule (including inside sub-expressions) are what flag a rule as
"has whitespace separators" → trivia-bearing (`gsm2tree.py:49-67`,
`rule_has_whitespace_separators` / `_check_items_for_whitespace_separators`).

---

## 6. Items, labels, dispositions, quantifiers

`item := ( label:identifier . ":" )? . disposition? . term . quantifier? , ;`
(`fegen.fltkg:11`). An item is: optional `label:` prefix, optional disposition glyph,
the term, optional quantifier. GSM: `gsm.Item(label, disposition, term, quantifier)`
(`gsm.py:120-125`); built by `Cst2Gsm.visit_item` (`fltk2gsm.py:108-128`), which is where
the **defaulting** logic lives.

### 6.1 Terms
`term := identifier | literal | "/" . regex:raw_string . "/" | "(" , alternatives , ")" ;`
(`fegen.fltkg:13`). Four kinds (`fltk2gsm.py:130-140`, `visit_term`; GSM `Term` union
`gsm.py:175-181`):
1. **identifier** → `gsm.Identifier` — a reference to another rule (`gsm.py:132-139`). The
   referenced rule must exist (`gsm2tree.py:614-616` raises otherwise).
2. **literal** → `gsm.Literal` (decoded string) (`gsm.py:142-148`).
3. **regex** → `gsm.Regex` (raw pattern) (`gsm.py:151-172`).
4. **sub-expression** → `Sequence[Items]` (§4).

Child-model contribution per term (`gsm2tree.py:612-623`, `model_for_item`):
- identifier → child type is the referenced rule's node type (`types={rule_name}`).
- literal / regex → child type is a `Span` (`types={self.Span.key}`, `gsm2tree.py:618-619`).
- sub-expression → contributes the union of its alternatives' models.

### 6.2 Labels (`label:term`) and labeled child access
A label is an `identifier` followed by `:` before the term (`fegen.fltkg:11`). It names the
child so generated code can fetch it by name. Defaulting (`fltk2gsm.py:113-116`): if no
explicit label is written **and the term is a bare rule reference**, the label defaults to
the rule's own name (`if label is None and isinstance(term, gsm.Identifier): label =
term.value`). So `expr := term , ...` (`toy.fltkg:1`) auto-labels the `term` child `term`.

Labels become a per-node nested `Label` enum and a **quintet of accessor methods per label**
(`gsm2tree.py:820-867`, `_emit_label_quintet`):
- `append_<label>(child)` / `extend_<label>(children)` — mutators.
- `children_<label>() -> Iterator[T]` — all children with that label.
- `child_<label>() -> T` — exactly one (raises if not exactly one).
- `maybe_<label>() -> Optional[T]` — zero-or-one.

Labels feed `ItemsModel.labels` (`gsm2tree.py:640-642`); a single label may map to multiple
types ("union label"), which widens the accessor's return annotation to a `typing.Union`
(`rust_parser_fixture.fltkg:53`, `val := item:num | item:name | item:/[!@#$]+/`, pins the
union-label case). Underscore-only labels are rejected (`gsm.py:305-320`).

Generic accessors exist regardless of labels: `children: list[tuple[Optional[Label], T]]`
(the raw child list, `gsm2tree.py:273`), `child()` returning the sole `(label, child)` pair
(`gsm2tree.py:307-321`), plus `append`/`extend`/`extend_children` and mutators
`insert`/`remove_at`/`replace_at`/`clear` (`gsm2tree.py:283-326, 386-610`).

### 6.3 Dispositions (`%` suppress, `$` include, `!` inline) — effect on the CST
`disposition := suppress:"%" | include:"$" | inline:"!" ;` (`fegen.fltkg:14`). GSM enum
`Disposition.{SUPPRESS, INCLUDE, INLINE}` (`gsm.py:194-197`). Disposition controls whether
and how a matched term appears in the parent's CST children list.

**Defaulting** (`fltk2gsm.py:117-122`) when no disposition glyph is written:
- If the item has a label **or** the term is a sub-expression → **INCLUDE**.
- Otherwise → **SUPPRESS**.

So by default: labeled things and groups are kept; bare unlabeled literals/regex/rule-refs
are dropped. This is why `rule := name:identifier , ":=" , alternatives , ";" , ;` keeps
`name` and `alternatives` (labeled) but drops the `":="` and `";"` literals from the CST.

Effect on the model/CST (`gsm2tree.py:625-643`, `model_for_items`):
- **`%` SUPPRESS** — term is parsed but contributes **no** child; skipped in the model
  (`gsm2tree.py:628-630`). Used to consume required punctuation:
  `paren_expr := %"(" , inner:atom , %")"` (`rust_parser_fixture.fltkg:16`).
  Asserts the term is not a sub-expression (`gsm2tree.py:629`).
- **`$` INCLUDE** — term contributes a child (its own node type, or a `Span` for
  literals/regex). An unlabeled `$`-literal appears as an **unlabeled** child Span
  (`rust_parser_fixture.fltkg:48`, `tagged := $"tag" . value:/[a-z]+/`).
- **`!` INLINE** — the referenced rule is parsed, but instead of nesting its node as one
  child, the rule's **own children are spliced into the parent** ("inlined"). Only valid on
  a bare rule-reference identifier (`gsm2tree.py:631-636` asserts `isinstance(item.term,
  gsm.Identifier)`; it pulls the referenced rule's model and `incorporate`s it directly into
  the parent model). Used by `fltk.fltkg:11` (`!alternatives`) and `:34` (`"(" ,
  !alternatives , ")"`). Recursive inlining cycles are detected and rejected
  (`gsm2tree.py:1008-1012`, `model_for_rule` tracks an `inline_stack`).

### 6.4 Quantifiers (`?` `+` `*`)
`quantifier := optional:"?" | one_or_more:"+" | zero_or_more:"*" ;` (`fegen.fltkg:15`).
Absent quantifier → required (exactly one). GSM `Quantifier` (`gsm.py:200-264`) exposes
`min()`/`max()` over an `Arity` enum (`ZERO`, `ONE`, `MULTIPLE`):

| Token | GSM constant | min..max | meaning |
|-------|--------------|----------|---------|
| (none)| `REQUIRED`   | 1..1     | exactly one (`fltk2gsm.py:124-126` default). |
| `?`   | `NOT_REQUIRED`| 0..1    | optional. |
| `+`   | `ONE_OR_MORE`| 1..many  | one or more. |
| `*`   | `ZERO_OR_MORE`| 0..many | zero or more. |

`is_optional()` = `min == ZERO`; `is_multiple()` = `max == MULTIPLE` (`gsm.py:213-220`).
An item can be nil if its quantifier is optional or its term is nil
(`gsm.py:127-129`, `Item.can_be_nil`).

Quantifier interaction with the CST: a `+`/`*` (multiple) label naturally yields several
children under one label; `child_<label>()` (exactly-one) vs `children_<label>()` (iterator)
vs `maybe_<label>()` (zero-or-one) let callers pick the cardinality they expect. Fixtures:
`items := item:atom+`, `opt_item := item:atom?`, `zero_items := item:atom*`
(`rust_parser_fixture.fltkg:22-28`).

**Constraint — no repeated nil items** (`gsm.py:418-453`,
`validate_no_repeated_nil_items`): a `+` or `*` item whose term can match empty is rejected
(it would loop forever). This is checked recursively into sub-expressions. The check is an
under-approximation for context-sensitive regexes, so both parser backends keep a runtime
loop guard as defense-in-depth (`gsm.py:438-444`).

---

## 7. Spans and the CST node shape

Every generated CST node (a `@dataclass`, `gsm2tree.py:237`) carries
(`gsm2tree.py:262-273`):
- `kind: Literal[NodeKind.X]` — the rule discriminant (default = its own NodeKind member).
- `span: terminalsrc.Span | fltk._native.Span` (default `UnknownSpan`) — source-text
  position covering the matched text. Span type is a union of the Python-backend span and
  the Rust-extension native span; offsets are codepoint-indexed.
- `children: list[tuple[Optional[Label], child]]` — ordered children, each tagged with its
  label (or `None`).

A node references only its children — no parent/sibling pointers (consistent with CLAUDE.md
"CST Design"). Literals/regex matched with `$`/`include` appear as `Span` children;
rule-references appear as the referenced rule's node; suppressed (`%`) terms produce **gaps**
in span coverage but no child entry. The `kind`/`Label`/`NodeKind` members carry a
cross-backend `__eq__`/`__hash__` keyed on a `_fltk_canonical_name` string
(`gsm2tree.py:99-156`) so Python-backend and Rust-backend enum members compare equal — part
of the drop-in-replacement contract.

A `*_cst_protocol.py` module of `typing.Protocol` classes mirrors the concrete CST module
(`gsm2tree.py:721-...`, `gen_protocol_module`) describing the same surface (kind, span,
children, the label quintet) for structural typing across backends.

---

## 8. The trivia rule (`_trivia`) and global whitespace handling

`_trivia` is a **reserved rule name** (`gsm.py:18`, `TRIVIA_RULE_NAME = "_trivia"`). It
defines what counts as inter-token whitespace/comments. In `fegen.fltkg:19` it is:
`_trivia := ( line_comment | line_comment? : | block_comment )+ ;`.

How it governs the grammar:
- **Auto-injection**: if a grammar defines no `_trivia`, a built-in one matching `[\s]+` is
  added (`gsm.py:477-504`, `add_trivia_rule_to_grammar`).
- **Reachability classification**: rules reachable from `_trivia` are flagged
  `is_trivia_rule=True` (`gsm.py:348-379` `classify_trivia_rules`; `_mark_trivia_reachable*`
  `gsm.py:382-403`). So `line_comment`/`block_comment` become trivia rules transitively.
- **Separation invariant**: a non-trivia rule may **not** reference a trivia rule directly
  (`gsm.py:456-474`, `validate_trivia_separation`) — trivia is consumed only via whitespace
  separators, never named as a term.
- **Non-nil invariant**: `_trivia` must not be able to match empty (`gsm.py:406-415`,
  `validate_trivia_rule_not_nil`); this is what makes `WS_REQUIRED` (`:`) meaningful.
- **Where it runs**: at every `,` (optional) or `:` (required) separator position, the
  parser invokes trivia parsing (`gsm2parser.py:674-694` for non-trivia rules; within a
  trivia rule itself it falls back to a raw `\s+` regex to avoid recursion,
  `gsm2parser.py:655-665`). `.` (NO_WS) positions skip trivia entirely.
- **Trivia capture (optional)**: when `context.capture_trivia` is set, consumed trivia is
  appended as an unlabeled `Span` child (`gsm2parser.py:666-673, 688-694`); otherwise it is
  discarded.

---

## 9. End-to-end mapping (grammar → parser → CST)

Putting it together for a single rule:

1. **Parse the `.fltkg` text** with the FLTK grammar parser (`fltk_parser.py`, itself
   generated from `fegen.fltkg`) → a CST of `cst.Grammar`/`cst.Rule`/`cst.Items`/... nodes.
2. **CST → GSM** via `Cst2Gsm` (`fltk2gsm.py`): produces `gsm.Grammar` of `Rule`s, each a
   list of `Items` alternatives of `Item`s (label, disposition, term, quantifier). This is
   where disposition defaults (§6.3), label-from-identifier (§6.2), and trailing-separator
   defaulting (§5) are applied.
3. **GSM transforms/validation**: `classify_trivia_rules` (§8) + name/nil/trivia validators
   (`gsm.py:323-474`); `add_trivia_rule_to_grammar` if needed.
4. **GSM → CST node classes** via `CstGenerator` (`gsm2tree.py`): one
   `snake_to_upper_camel(name)` dataclass per rule, with `kind`/`span`/`children`, the
   per-label accessor quintet, generic accessors and mutators; plus the module-level
   `NodeKind` enum and a parallel `*_cst_protocol.py`. (A Rust backend, `gsm2tree_rs.py`,
   emits equivalent node types for the native extension.)
5. **GSM → parser** via `ParserGenerator` (`gsm2parser.py`): one memoized recursive-descent
   parse method per rule; alternation tries each `Items`; sequencing walks items applying
   separator/trivia handling (§5/§8); dispositions decide what gets `append`ed to the
   result node; quantifiers drive the repeat/optional loops. Left recursion is handled by
   the packrat memoizer (`rust_parser_fixture.fltkg:30-37` is the pinned fixture).

---

## 10. Construct → meaning quick reference

| Surface syntax | Construct | GSM | CST / parser effect |
|----------------|-----------|-----|---------------------|
| `name := ... ;` | rule definition | `Rule(name, alternatives)` | one node class `UpperCamel(name)`, one `NodeKind` member, one parser method |
| `a | b` | alternation | multiple `Items` in `Rule.alternatives` / sub-expr | parser tries each; node child types = union over alternatives |
| `( ... )` | sub-expression | `Sequence[Items]` term | implicit INCLUDE; children spliced/grouped per its dispositions |
| `.` | NO_WS separator | `Separator.NO_WS` | no trivia between items |
| `,` | WS_ALLOWED separator | `Separator.WS_ALLOWED` | optional trivia |
| `:` | WS_REQUIRED separator | `Separator.WS_REQUIRED` | mandatory trivia (parse fails if absent) |
| `?` | optional quantifier | `NOT_REQUIRED` (0..1) | child may be absent; `maybe_<l>()` |
| `+` | one-or-more | `ONE_OR_MORE` (1..N) | ≥1 children; `children_<l>()` |
| `*` | zero-or-more | `ZERO_OR_MORE` (0..N) | ≥0 children; `children_<l>()` |
| `%term` | suppress disposition | `Disposition.SUPPRESS` | parsed, no child (span gap) |
| `$term` | include disposition | `Disposition.INCLUDE` | child kept (Span for literal/regex) |
| `!rule` | inline disposition | `Disposition.INLINE` | referenced rule's children spliced into parent |
| `lbl:term` | label | `Item.label` | nested `Label` enum + `append/extend/children/child/maybe_<lbl>` |
| `"..."` / `'...'` | literal | `Literal` | matches exact text; default-suppressed unless labeled/`$` |
| `/.../` | regex | `Regex` | matches `re` pattern; child is a `Span` if included |
| `_trivia` | trivia rule | reserved `Rule` | defines whitespace/comments consumed at `,`/`:` |

---

## 11. Open factual questions (deferred to code-level pass)

- Exact parser control-flow for alternation backtracking, the packrat memo table, and the
  left-recursion seed-growing algorithm (`gsm2parser.py` / `gsm2parser_rs.py` internals;
  the `nest_sum`/`grow_seed` fixture in `rust_parser_fixture.fltkg:71-73` hints at it).
- Precise span-merging rules across suppressed gaps and the `UnknownSpan` sentinel
  (`gsm2tree.py:269`, `terminalsrc`).
- The dormant `invocation`/`expression`/`var` constructs (`fltk.fltkg`, GSM `Invocation`/
  `Add`/`Var` at `gsm.py:267-288`): defined in GSM but apparently unreachable from the live
  `fegen.fltkg` pipeline — confirm whether any generator path consumes them.
- Rust-backend node/accessor emission parity details (`gsm2tree_rs.py`, 133K — the public
  drop-in-replacement surface) belong to the code-level pass.
