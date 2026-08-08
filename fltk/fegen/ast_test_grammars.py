"""The worked-example grammars and ``.fltkast`` sidecars the AST suites share.

Six examples carry most of the AST layer's coverage: a config language (products, a sum,
optional and keyed collections, every scalar erasure), an expression grammar (a precedence fold
and the recursion it closes), a task definition (a flattened wrapper at an optional use site), the
leaf node forms, a merged document (multi-alternative erased and flattened rules, a custom
coercion), and a fold over a custom operand (the shape nothing can name a teardown sentinel for).
Each is exercised by the model tests, the Python emitter's runtime tests and the Rust
emitter's source tests, so they live here rather than once per suite: the one-model-two-emitters
claim is only as strong as the two backends being fed the same input, and a grammar spelled
separately in each suite drifts apart silently.  ``EXAMPLES`` is the roster, for the suites that
sweep every one of them.

Also here: the grammar pipeline every AST suite needs — a parsed grammar is INLINE-expanded by
the parser, and ``build_ast_model`` additionally requires the trivia rule added and classified.
"""

from __future__ import annotations

import dataclasses

from fltk.fegen import ast_config as ac
from fltk.fegen import ast_model as am
from fltk.fegen import gsm
from fltk.iir.context import create_default_context
from fltk.plumbing import parse_grammar

CONFIG_GRAMMAR = r"""
config     := , stanza* ;
stanza     := server_def | metric_def ;
server_def := "server" : name:identifier , "{" , setting* , "}" , ;
setting    := key:identifier , "=" , value:value , ";" , ;
metric_def := "metric" : name:identifier , ":" , type:metric_type ,
              ("interval" : interval:number)? , ";" , ;
metric_type := counter:"counter" | gauge:"gauge" | histogram:"histogram" ;
value      := string:string_literal | number:number | flag:boolean | list:list ;
list       := "[" , (value , ("," , value)* , ","?)? , "]" ;
boolean    := true:"true" | false:"false" ;
identifier := name:/[a-z_][a-z0-9_]*/ ;
number     := val:/-?[0-9]+/ ;
string_literal := "\"" . content:/[^"\\]*/ . "\"" ;
"""
"""A config language: the serde-competitive case, with a `type` label needing a rename."""

CONFIG_TEXT = """
server web {
  host = "localhost";
  port = 8080;
  debug = true;
  tags = [1, 2];
}
metric hits : counter interval 30 ;
"""
"""One document of ``CONFIG_GRAMMAR``, covering every stanza and value form it has."""

CONFIG_SIDECAR = """
rule identifier     { transparent; }
rule number         { type: i64; transparent; }
rule string_literal { text_from: content; transparent; }
rule boolean        { bool: true; transparent; }
rule metric_type    { transparent; }
rule server_def     { field setting { name: settings; } }
rule config         { field stanza  { name: stanzas; } }
rule metric_def     { field type    { name: metric_kind; } }
"""
"""Erases every mechanical leaf of the config language, so the fields carry plain values."""

KEYED_SIDECAR = CONFIG_SIDECAR + "rule setting { key: key; }\n"
"""``CONFIG_SIDECAR`` with the setting list keyed, so ``ServerDef.settings`` is a map."""

MULTI_SIDECAR = CONFIG_SIDECAR + "rule setting { key: key multi; }\n"
"""``KEYED_SIDECAR``'s accumulating form: one key of ``ServerDef.settings`` holds a run."""

# Each repetition carries a leading separator, which is what lets a second operator follow
# whitespace.
FOLD_GRAMMAR = """
expr    := term , ( , op:add_op , term)* ;
term    := factor , ( , op:mul_op , factor)* ;
factor  := num:number | paren:paren_expr ;
paren_expr := "(" , expr , ")" , ;
add_op  := plus:"+" | minus:"-" ;
mul_op  := times:"*" | divide:"/" ;
number  := val:/[0-9]+/ ;
"""
"""Two precedence levels over parenthesized operands: folds, and one by-value cycle."""

FOLD_SIDECAR = """
rule expr       { fold_left: op; }
rule term       { fold_left: op; }
rule add_op     { transparent; }
rule mul_op     { transparent; }
rule paren_expr { transparent; }
rule number     { type: i64; transparent; }
"""
"""Folds both precedence levels and erases the operators, operands and the paren wrapper."""

TASK_GRAMMAR = """
task_def  := "task" : name:identifier , schedule? , "{" , setting* , "}" , ;
schedule  := "every" : interval:number . unit:time_unit ;
time_unit := sec:"s" | min:"m" | hour:"h" ;
setting   := key:identifier , "=" , value:number , ";" , ;
identifier := name:/[a-z_][a-z0-9_]*/ ;
number     := val:/-?[0-9]+/ ;
"""
"""``schedule`` is a wrapper carrying no meaning of its own, used at optional arity."""

TASK_SIDECAR = """
rule identifier { transparent; }
rule number     { type: i64; transparent; }
rule schedule   { flatten; }
rule time_unit  { transparent; }
rule task_def   { field setting { name: settings; } }
"""
"""Hoists the wrapper's fields into ``TaskDef`` and erases the leaves around them."""


LEAF_GRAMMAR = (
    "doc := n:num , t:tag , q:quoted , c:count , r:ratio , f:flag , p:pick ;\n"
    "num := d:/[0-9]+/ ;\n"
    'tag := $"#" . name:/[a-z]+/ | name:/[A-Z]+/ ;\n'
    'quoted := "\\"" . content:/[^"]*/ . "\\"" ;\n'
    "count := c:/-?[0-9]+/ ;\n"
    "ratio := v:/[0-9.]+/ ;\n"
    'flag := yes:"yes" | no:"no" ;\n'
    'pick := a:"a" | b:"b" ;\n'
)
"""The node forms whose whole CST node comes out of their own value.

Every terminal-only shape the serialize direction has to split text back across: one included
regex, two alternatives whose item lists differ, an included literal beside a regex, suppressed
quotes around a redirected text, and two coercions.  Plus the two enum-shaped spellings, the value
enum and the boolean.
"""

LEAF_SIDECAR = (
    "rule quoted { text_from: content; }\n"
    "rule count  { type: i64; }\n"
    "rule ratio  { type: f32; }\n"
    "rule flag   { bool: yes; }\n"
)
"""Redirects one text, coerces two and maps one enum to a boolean, leaving every rule its type."""


MERGED_GRAMMAR = """
doc := i:import , w:wrapped , t:tagged , m:amount , c:choice , p:pick ;
import := "import" : name:word | "import" : name:word : "as" : alias:word ;
wrapped := v:word | "(" . v:word . ")" ;
tagged := label:word , bracket? ;
bracket := "[" . n:num . "]" | "{" . n:num . "}" ;
choice := a:word | b:word ;
pick := ( x:word | y:num ) . "!" ;
amount := $/[0-9]+/ ;
word := w:/[a-z]+/ ;
num := d:/[0-9]+/ ;
"""
"""Two alternatives one of which extends the other, plus the multi-plan private helpers.

``wrapped`` and ``bracket`` are the only shape whose reverse helper is emitted once per
alternative — an erased product and a flattened wrapper with more than one alternative — so this
is the grammar behind every ``_erased_..._to_cst_alt<N>`` / ``_flat_..._to_cst_alt<N>`` name.
``amount`` carries a ``type: custom(...)`` coercion, whose render call no other example reaches.
"""

MERGED_SIDECAR = """
rule wrapped { transparent; }
rule bracket { flatten; }
rule choice  { product; }
rule word    { transparent; }
rule num     { type: i64; transparent; }
rule amount  { type: custom(rust_type: "crate::merged::Cents",
                            rust_parse: "crate::merged::parse_cents",
                            rust_unparse: "crate::merged::render_cents",
                            py_type: "fltk.fegen.ast_test_grammars.Cents",
                            py_parse: "fltk.fegen.ast_test_grammars.parse_cents",
                            py_unparse: "fltk.fegen.ast_test_grammars.render_cents"); }
"""
"""Erases and flattens the multi-alternative rules, and coerces ``amount`` on both backends.

The Rust paths point into the gate crate's own support module; the Python ones point at the three
definitions below, so a model built for either backend resolves.
"""

CUSTOM_FOLD_GRAMMAR = 'expr := d:atom , ( , op:sign , d:atom)* ;\nsign := p:"+" | m:"-" ;\natom := v:/[0-9]+/ ;\n'
"""A fold whose operand is handed to a user-written type, so no sentinel can be named for it."""

CUSTOM_FOLD_SIDECAR = 'rule expr { fold_left: op; }\nrule atom { custom(python: "pkg.mod.Atom", rust: "app::Atom"); }\n'
"""Both backends' spellings of the same custom operand, so the two halves of the residual —
the model naming no witness and the emitter writing no ``Drop`` — are checked against one input.
"""

EXAMPLES: tuple[tuple[str, str, str], ...] = (
    ("config", CONFIG_GRAMMAR, KEYED_SIDECAR),
    ("fold", FOLD_GRAMMAR, FOLD_SIDECAR),
    ("task", TASK_GRAMMAR, TASK_SIDECAR),
    ("leaf", LEAF_GRAMMAR, LEAF_SIDECAR),
    ("merged", MERGED_GRAMMAR, MERGED_SIDECAR),
    ("custom_fold", CUSTOM_FOLD_GRAMMAR, CUSTOM_FOLD_SIDECAR),
)
"""Every shared example as one name/grammar/sidecar row, for a suite that sweeps all of them.

The claim-table exhaustiveness sweep is the caller that has to see all of them: its whole value
is that a name family emitted by some grammar cannot escape the table.  Keeping the roster beside
the grammars makes adding a fixture and adding it to the sweep one edit in one file.
"""


@dataclasses.dataclass(frozen=True)
class Cents:
    """The Python half of ``MERGED_SIDECAR``'s ``type: custom(...)`` value type."""

    count: int


def parse_cents(text: str) -> Cents:
    """Read a count of cents from the text its terminal matched."""
    return Cents(int(text))


def render_cents(value: Cents) -> str:
    """Render a count of cents back to the text its terminal accepts."""
    return str(value.count)


def classify(grammar: gsm.Grammar) -> gsm.Grammar:
    """One grammar with the trivia rule added and every rule's trivia use classified."""
    return gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, create_default_context()))


def classified_grammar(grammar_text: str) -> gsm.Grammar:
    """One grammar's text, parsed and trivia-processed as ``build_ast_model`` requires it."""
    return classify(parse_grammar(grammar_text))


def model_for(
    grammar_text: str,
    sidecar: str | None = None,
    backend: ac.Backend = ac.Backend.PYTHON,
) -> am.AstModel:
    """The AST model of one grammar, shaped by ``sidecar`` when there is one.

    ``backend`` names the generation target the sidecar is resolved for, which decides which
    ``custom(...)`` entries it has to carry.
    """
    grammar = classified_grammar(grammar_text)
    config = None if sidecar is None else ac.load_ast_config(sidecar, grammar, {backend})
    return am.build_ast_model(grammar, config)
