"""Generator tests for the Rust serde backend (``RustSerdeGenerator``).

These assert structural properties of the emitted ``de.rs`` source string; they do not compile
it.  What the descriptions *mean* — how a keyed field is served, where an error is positioned,
which alternative a dispatch table selects — is tested against the runtime in
``crates/fltk-serde-core/src/de.rs``'s own suite, over the same vocabulary written by hand.  The
model-side answers the descriptions rest on live in ``fltk/fegen/test_ast_model.py``.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

from fltk.fegen import ast_config as ac
from fltk.fegen import ast_model as am
from fltk.fegen import ast_test_grammars as fixtures
from fltk.fegen import gsm, gsm2serde_rs

RUNTIME = "::fltk_serde_core"

HOIST_GRAMMAR = """
tuned  := title:word , w:limits? ;
limits := "[" . cap:num , ":" , deep:extras . "]" ;
extras := depth:num? , tag:word* , mark:"~"? ;
word   := w:/[a-z]+/ ;
num    := d:/[0-9]+/ ;
"""
HOIST_SIDECAR = """
rule word   { transparent; }
rule num    { transparent; }
rule limits { flatten; }
rule extras { flatten; }
"""
"""Two nested ``flatten;`` wrappers, so a field reaches its children two steps down.

The transitive path is the one description a runtime cannot reconstruct from a single wrapper
label, which is why the model publishes the whole thing and the emitter writes it down.
"""

CUSTOM_GRAMMAR = "doc := stamp:when , n:num ;\nwhen := v:/[0-9-]+/ ;\nnum := d:/[0-9]+/ ;\n"
CUSTOM_SIDECAR = 'rule when { custom(rust: "app::When"); }\n'
"""A rule the AST layer hands to a user-written type, which the serde path serves as text."""

PAYLOAD_GRAMMAR = "entry := key:word . '=' . value:num | bare:num ;\nword := w:/[a-z]+/ ;\nnum := d:/[0-9]+/ ;\n"
PAYLOAD_SIDECAR = "rule word { transparent; }\nrule num { transparent; }\n"
"""A sum whose first alternative names two labels, so it has no single child to be its payload
and the model generates a product for it."""

PRESENCE_GRAMMAR = 'doc := n:num . bang:"!"? ;\nnum := d:/[0-9]+/ ;\n'
"""An optional labeled literal beside a node child: whether it was written is the whole value."""

KEY_TYPE_GRAMMAR = (
    "cfg := row* ;\nrow := k:key_val , '=' , v:word , ';' ;\nkey_val := d:/-?[0-9]+/ ;\nword := w:/[a-z]+/ ;\n"
)
"""A keyed region whose key rule takes whichever coercion the sidecar declares."""

KEY_KIND_CASES = [
    ("text", "Text"),
    ("i8", "I8"),
    ("i16", "I16"),
    ("i32", "I32"),
    ("i64", "I64"),
    ("u8", "U8"),
    ("u16", "U16"),
    ("u32", "U32"),
    ("u64", "U64"),
]
"""Every key type the sidecar admits, and the ``KeyKind`` the runtime must be told it is.

Written out here as well as in the emitter so the pairing is asserted rather than mirrored: an
entry pairing ``i8`` with ``I16`` is valid Rust that gates and compares keys at the wrong width.
"""


def model_for(grammar_text: str, sidecar: str | None = None) -> am.AstModel:
    return fixtures.model_for(grammar_text, sidecar, ac.Backend.RUST)


def generate(grammar_text: str, sidecar: str | None = None, **kwargs: str) -> str:
    return gsm2serde_rs.generate_de_rs(model_for(grammar_text, sidecar), **kwargs)


def item(src: str, header: str) -> str:
    """The emitted top-level item starting with ``header``, through its own closing line."""
    start = src.index(header)
    end = src.index("\n};\n", start) if header.startswith("static") else src.index("\n}\n", start)
    return src[start : end + 2]


def shape(src: str, rule_name: str) -> str:
    """The ``static`` describing how one rule's nodes are served."""
    return item(src, f"static {am.serde_shape_name(rule_name)}: ")


def impl_block(src: str, class_name: str) -> str:
    """The ``NodeShape`` impl for one rule's CST node type."""
    return item(src, f"impl {RUNTIME}::NodeShape for cst::{class_name} {{")


class TestForms:
    """Each node form of the model, as the description that serves it."""

    def test_a_terminal_only_rule_is_a_terminal_form(self) -> None:
        src = generate("doc := v:/[a-z]+/ ;\n")
        assert f"form: {RUNTIME}::Form::Terminal {{ text_from: None }}," in shape(src, "doc")

    def test_text_from_names_the_child_the_text_comes_from(self) -> None:
        src = generate(fixtures.LEAF_GRAMMAR, fixtures.LEAF_SIDECAR)
        assert 'text_from: Some("content")' in shape(src, "quoted")

    def test_a_product_serves_one_field_per_model_field_in_order(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        emitted = shape(src, "setting")
        assert re.search(r'name: "key",\s+label: "key",\s+container: ::fltk_serde_core::Container::Single', emitted)
        assert emitted.index('name: "key"') < emitted.index('name: "value"')

    def test_a_field_renamed_by_the_sidecar_is_served_under_the_new_name(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        emitted = shape(src, "metric_def")
        assert 'name: "metric_kind"' in emitted
        assert 'label: "type"' in emitted

    def test_an_optional_labeled_literal_is_a_presence_flag(self) -> None:
        src = generate(PRESENCE_GRAMMAR)
        assert f"container: {RUNTIME}::Container::Presence" in shape(src, "doc")

    def test_a_repetition_is_a_collection(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.CONFIG_SIDECAR)
        assert f"container: {RUNTIME}::Container::Collection" in shape(src, "config")

    def test_an_enum_shaped_rule_carries_its_variants_and_their_labels(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.CONFIG_SIDECAR)
        emitted = shape(src, "metric_type")
        assert f'{RUNTIME}::Variant {{ name: "Counter", label: "counter" }}' in emitted
        assert "truthy: None," in emitted

    def test_a_bool_rule_names_the_alternative_that_is_true(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.CONFIG_SIDECAR)
        assert 'truthy: Some("true"),' in shape(src, "boolean")

    def test_a_transparent_product_is_erased_to_its_one_field(self) -> None:
        src = generate(fixtures.MERGED_GRAMMAR, fixtures.MERGED_SIDECAR)
        emitted = shape(src, "wrapped")
        assert f"form: {RUNTIME}::Form::Transparent {{" in emitted
        assert 'label: "v",' in emitted

    def test_a_flattened_wrapper_keeps_a_product_shape_of_its_own(self) -> None:
        """Its use sites splice its fields, but the wrapper's own node is still served."""
        src = generate(HOIST_GRAMMAR, HOIST_SIDECAR)
        assert f"form: {RUNTIME}::Form::Product {{" in shape(src, "limits")

    def test_a_custom_rule_is_served_as_its_own_source_text(self) -> None:
        src = generate(CUSTOM_GRAMMAR, CUSTOM_SIDECAR)
        assert f"form: {RUNTIME}::Form::Terminal {{ text_from: None }}," in shape(src, "when")


class TestKeyedFields:
    """A ``key:`` region, whose declared key type is what makes two elements duplicates."""

    def test_a_keyed_field_names_the_element_field_that_keys_it(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        emitted = shape(src, "server_def")
        assert f"container: {RUNTIME}::Container::Map({RUNTIME}::Key {{" in emitted
        assert 'name: "key",' in emitted
        assert f"kind: {RUNTIME}::KeyKind::Text," in emitted
        assert "multi: false," in emitted

    def test_multi_is_carried_through(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.MULTI_SIDECAR)
        assert "multi: true," in shape(src, "server_def")

    def test_an_integer_type_on_the_key_field_becomes_its_declared_width(self) -> None:
        """The one ``type:`` coercion the serde path reads, because identity precedes any target."""
        src = generate(
            "cfg := row* ;\nrow := k:key_num , '=' , v:word , ';' ;\nkey_num := d:/[0-9]+/ ;\nword := w:/[a-z]+/ ;\n",
            "rule key_num { type: u16; transparent; }\nrule word { transparent; }\nrule row { key: k; }\n",
        )
        assert f"kind: {RUNTIME}::KeyKind::U16," in shape(src, "cfg")

    def test_every_admitted_key_type_is_covered_by_the_cases_below(self) -> None:
        """The emitter's table covers exactly what ``check_key_type`` lets through.

        The runtime's ``KeyKind`` inventory is the other half of this; a key type admitted by the
        sidecar with no spelling here would reach a consumer's build as a compile error, so the
        two sets are pinned against each other rather than related by a naming convention.
        """
        declared = {key_type for key_type, _ in KEY_KIND_CASES}
        assert declared == {am.ScalarKind.TEXT.value} | ac.INTEGER_SCALAR_TYPES
        assert declared == set(gsm2serde_rs._KEY_KINDS)

    @pytest.mark.parametrize(("key_type", "kind"), KEY_KIND_CASES, ids=[case[0] for case in KEY_KIND_CASES])
    def test_each_key_type_is_served_at_the_width_it_declares(self, key_type: str, kind: str) -> None:
        """The width is what gates the key text and what decides identity, so a mis-paired entry
        accepts keys its own gate would refuse and compares them over the wrong range — and it is
        still valid Rust, so nothing downstream catches it."""
        coercion = "" if key_type == am.ScalarKind.TEXT.value else f"type: {key_type}; "
        src = generate(
            KEY_TYPE_GRAMMAR,
            f"rule key_val {{ {coercion}transparent; }}\nrule word {{ transparent; }}\nrule row {{ key: k; }}\n",
        )
        assert f"kind: {RUNTIME}::KeyKind::{kind}," in shape(src, "cfg")


class TestSumAndFold:
    """The two forms whose description is a table the runtime evaluates."""

    def test_a_sum_rule_points_at_the_shared_dispatch_table(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.CONFIG_SIDECAR)
        assert f"static {am.signature_constant_name('stanza')}: {RUNTIME}::dispatch::Table" in src
        assert f"table: &{am.signature_constant_name('stanza')}," in shape(src, "stanza")

    def test_the_table_is_named_through_the_serde_runtime(self) -> None:
        """A ``de.rs``-only consumer depends on ``serde`` and ``fltk-serde-core`` and no more."""
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.CONFIG_SIDECAR)
        assert "::fltk_ast_core::" not in src

    def test_an_alternative_naming_one_label_carries_that_child(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.CONFIG_SIDECAR)
        emitted = item(src, f"static {am.serde_alternatives_name('stanza')}: ")
        assert f'{RUNTIME}::Content::Child {{ label: "server_def" }}' in emitted
        assert 'name: "ServerDef",' in emitted

    def test_an_alternative_naming_several_labels_carries_its_own_fields(self) -> None:
        src = generate(PAYLOAD_GRAMMAR, PAYLOAD_SIDECAR)
        emitted = item(src, f"static {am.serde_alternatives_name('entry')}: ")
        assert f"{RUNTIME}::Content::Fields {{" in emitted
        assert 'label: "key",' in emitted
        assert 'label: "value",' in emitted
        assert f'{RUNTIME}::Content::Child {{ label: "bare" }}' in emitted

    def test_a_fold_rule_describes_the_chain_its_operands_nest_into(self) -> None:
        src = generate(fixtures.FOLD_GRAMMAR, fixtures.FOLD_SIDECAR)
        emitted = item(src, f"static {am.serde_fold_name('expr')}: ")
        assert f"direction: {RUNTIME}::Direction::Left," in emitted
        assert 'operand_label: "term",' in emitted
        assert 'operator_label: "op",' in emitted
        assert f'lhs: "{am.FOLD_LHS}",' in emitted
        assert f"form: {RUNTIME}::Form::Fold(&{am.serde_fold_name('expr')})," in shape(src, "expr")


class TestHoists:
    """A field the node holds through one or more ``flatten;`` wrappers."""

    def test_the_whole_wrapper_path_is_written_down_outermost_first(self) -> None:
        src = generate(HOIST_GRAMMAR, HOIST_SIDECAR)
        emitted = shape(src, "tuned")
        assert (
            f'hoist: &[{RUNTIME}::Wrapper {{ label: "w", optional: true }}, '
            f'{RUNTIME}::Wrapper {{ label: "deep", optional: false }}]' in emitted
        )

    def test_a_field_the_node_holds_itself_has_no_path(self) -> None:
        src = generate(HOIST_GRAMMAR, HOIST_SIDECAR)
        emitted = shape(src, "tuned")
        title = emitted[emitted.index('name: "title"') : emitted.index('name: "cap"')]
        assert "hoist: &[]," in title

    def test_an_optional_step_is_marked_as_one(self) -> None:
        """An absent optional wrapper empties every field it carried; a required one is a
        missing child."""
        src = generate(HOIST_GRAMMAR, HOIST_SIDECAR)
        emitted = shape(src, "limits")
        assert f'hoist: &[{RUNTIME}::Wrapper {{ label: "deep", optional: false }}]' in emitted


class TestNodeShapeImpls:
    """What a generated module hands the runtime for one node: its span and its children."""

    def test_labels_are_translated_to_the_strings_the_description_names(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        emitted = impl_block(src, "Setting")
        assert "let label = label.as_ref().map(|label| match label {" in emitted
        assert 'cst::SettingLabel::Key => "key",' in emitted

    def test_a_terminal_child_is_handed_over_as_its_span(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        emitted = impl_block(src, "Identifier")
        assert f"cst::IdentifierChild::Span(span) => {RUNTIME}::Child::Text(span.clone())," in emitted

    def test_a_node_child_is_handed_over_as_an_erased_handle(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        emitted = impl_block(src, "Config")
        assert (
            f"cst::ConfigChild::Stanza(node) => {RUNTIME}::Child::Node({RUNTIME}::Node::new(node.clone()))," in emitted
        )

    def test_a_trivia_child_is_left_out(self) -> None:
        """It carries no label by construction, and its rule has no shape to reach it through."""
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        emitted = impl_block(src, "Config")
        assert "cst::ConfigChild::Trivia(_) => continue," in emitted

    def test_a_rule_with_no_labels_still_reports_its_children(self) -> None:
        """The unlabeled ones are what a sum rule's dispatch counts as belonging to nobody."""
        src = generate("doc := %'(' . inner:leaf . %')' ;\nleaf := $/[a-z]+/ ;\n")
        emitted = impl_block(src, "Leaf")
        assert "let label: Option<&'static str> = None;" in emitted
        # The loop binding is the other half of it: binding `label` here would shadow the line
        # above, and an unused binding is a hard build failure in a consumer under `-D warnings`.
        assert "for (_label, child) in self.children() {" in emitted

    def test_a_rule_holding_nothing_the_runtime_reads_reports_no_children(self) -> None:
        """Every child is suppressed or trivia, so there is no child arm and nothing to loop over
        — an empty `match` inside the loop would be unreachable code the consumer's build denies."""
        src = generate("doc := %'x' , inner:leaf ;\nleaf := %'y' . %'z' ;\n")
        emitted = impl_block(src, "Leaf")
        assert (
            f"fn labeled_children(&self) -> Vec<(Option<&'static str>, {RUNTIME}::Child)> {{\n        Vec::new()\n"
            in (emitted)
        )

    def test_the_node_span_is_the_node_s_own(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        assert "        self.span().clone()" in impl_block(src, "Setting")


class TestEntryPoints:
    """What a caller reaches the runtime through."""

    def test_every_rule_gets_a_per_rule_entry_point(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        for rule_name in ("config", "setting", "identifier", "boolean"):
            assert f"pub fn {am.serde_entry_name(rule_name)}<T: ::serde::de::DeserializeOwned>(" in src

    def test_a_transparent_rule_gets_one_too(self) -> None:
        """It emits no AST type, but its CST nodes are still a position a target reads from."""
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        assert f"pub fn {am.serde_entry_name('number')}<" in src

    def test_from_str_is_emitted_only_with_a_parser_module(self) -> None:
        assert "pub fn from_str<" not in generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR, parser_mod_path="super::parser")
        assert "pub fn from_str<" in src
        assert "use super::parser;" in src

    def test_from_str_targets_the_grammar_s_first_rule_by_default(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR, parser_mod_path="super::parser")
        assert "parser.apply__parse_config(0)" in src
        assert f"Ok({am.serde_entry_name('config')}(&parsed.result)?)" in src

    def test_a_named_goal_rule_is_what_from_str_parses(self) -> None:
        src = generate(
            fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR, parser_mod_path="super::parser", goal_rule="setting"
        )
        assert "parser.apply__parse_setting(0)" in src

    def test_an_unknown_goal_rule_is_a_generation_error(self) -> None:
        with pytest.raises(ValueError, match="goal rule 'nope' is not a rule of the grammar"):
            generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR, goal_rule="nope")

    def test_the_trivia_rule_is_refused_as_a_rule_that_is_never_served(self) -> None:
        """It is a rule of the grammar, so calling it unknown would contradict the grammar file."""
        with pytest.raises(ValueError, match="'_trivia' is a trivia rule, which a serde module never serves"):
            generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR, goal_rule="_trivia")

    def test_a_goal_rule_is_checked_even_where_no_entry_point_reads_it(self) -> None:
        """Naming an option that is then ignored would hide the typo until runtime."""
        with pytest.raises(ValueError):
            generate("doc := v:/[a-z]+/ ;\n", goal_rule="missing")


class TestAstTargets:
    """The ``Deserialize`` impls that let a target declare a generated AST type as a field."""

    def test_an_ast_type_gets_an_impl_that_is_one_call_over_its_from_cst(self) -> None:
        src = generate(fixtures.FOLD_GRAMMAR, fixtures.FOLD_SIDECAR, ast_mod_path="super::ast")
        constant = am.serde_ast_constant_name("expr")
        assert f'const {constant}: &str = "{am.serde_ast_name("expr")}";' in src
        assert "impl<'de> ::serde::Deserialize<'de> for ast::Expr {" in src
        assert f"{RUNTIME}::deserialize_ast(deserializer, {constant}, ast::Expr::from_cst)" in src

    def test_nothing_is_emitted_without_an_ast_module(self) -> None:
        """An option that silently emitted impls against a module the consumer never generated
        would be a compile error in their build, not ours."""
        src = generate(fixtures.FOLD_GRAMMAR, fixtures.FOLD_SIDECAR)
        assert "Deserialize<'de> for" not in src
        assert am.serde_ast_constant_name("expr") not in src

    def test_the_ast_module_is_imported_under_the_name_the_impls_use(self) -> None:
        src = generate(fixtures.FOLD_GRAMMAR, fixtures.FOLD_SIDECAR, ast_mod_path="crate::grammar::ast")
        assert "use crate::grammar::ast as ast;" in src or "use crate::grammar::ast;" in src

    def test_a_rule_with_no_ast_type_of_its_own_gets_no_impl(self) -> None:
        """A ``transparent;`` or ``flatten;`` rule's converter is a private helper of the AST
        module, and a ``custom(...)`` rule's type is the consumer's — an impl on it would be an
        orphan."""
        model = model_for(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        rules = am.serde_ast_rules(model)
        assert "config" in rules
        assert "identifier" not in rules  # transparent
        src = gsm2serde_rs.generate_de_rs(model, "super::cst", ast_mod_path="super::ast")
        assert am.serde_ast_constant_name("identifier") not in src

        # A `flatten;` wrapper emits no type either, so an impl on one would be an orphan and a
        # hard compile error in every consumer.
        hoisted = model_for(HOIST_GRAMMAR, HOIST_SIDECAR)
        assert "limits" not in am.serde_ast_rules(hoisted)
        hoisted_src = gsm2serde_rs.generate_de_rs(hoisted, "super::cst", ast_mod_path="super::ast")
        assert am.serde_ast_constant_name("limits") not in hoisted_src

        custom = model_for(CUSTOM_GRAMMAR, CUSTOM_SIDECAR)
        assert "when" not in am.serde_ast_rules(custom)

    def test_a_grammar_with_no_ast_type_at_all_imports_nothing(self) -> None:
        """The import would then be unused, which a consumer denying warnings cannot build."""
        src = generate(
            "doc := stamp:when ;\nwhen := v:/[0-9-]+/ ;\n",
            'rule when { custom(rust: "app::When"); }\nrule doc { transparent; }\n',
            ast_mod_path="super::ast",
        )
        assert "as ast;" not in src
        assert "use super::ast;" not in src

    def test_the_magic_name_prefix_is_the_one_the_runtime_recognizes(self) -> None:
        """ABI between the generated module and ``fltk-serde-core``: the two are released in
        lockstep, and a silent disagreement would fail every AST-typed field at runtime with
        nothing to point at."""
        wrappers = Path(__file__).parent.parent / "crates" / "fltk-serde-core" / "src" / "wrappers.rs"
        declared = re.search(r'pub const AST_NAME_PREFIX: &str = "([^"]*)";', wrappers.read_text())
        assert declared is not None, "the runtime declares the prefix"
        assert declared.group(1) == am.SERDE_AST_NAME_PREFIX


class TestHeader:
    """What the module says about itself."""

    def test_the_header_names_the_crates_a_consumer_has_to_depend_on(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        assert "//! Requires crates: `serde`, `fltk-serde-core`." in src

    def test_the_header_names_the_grammar_it_came_from(self) -> None:
        model = model_for(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR)
        src = gsm2serde_rs.generate_de_rs(model, "super::cst", "grammars/config.fltkg")
        assert src.startswith("//! Generated by fltk gen-rust-serde from `grammars/config.fltkg`. Do not edit.")

    def test_the_cst_module_is_imported_under_the_name_every_impl_uses(self) -> None:
        src = generate(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR, cst_mod_path="crate::grammar::cst")
        assert "use crate::grammar::cst;" in src

    def test_generation_is_idempotent(self) -> None:
        generator = gsm2serde_rs.RustSerdeGenerator(model_for(fixtures.CONFIG_GRAMMAR, fixtures.KEYED_SIDECAR))
        assert generator.generate() == generator.generate()


# A `static`/`fn` line binds its own name; a `use` line binds its alias, or the last segment of
# its path where it has none.  An `impl` block binds nothing, which is why it matches neither.
_ITEM_RE = re.compile(r"(?:pub(?:\([^)]*\))? )?(?:fn|static|const|mod|type) ([A-Za-z_]\w*)")
_USE_RE = re.compile(r"use ([A-Za-z_][\w:]*)(?: as ([A-Za-z_]\w*))?;")


def _module_level_names(source: str) -> set[str]:
    """Every name a generated serde module binds at module level."""
    names: set[str] = set()
    for line in source.splitlines():
        found = _ITEM_RE.match(line)
        if found is not None:
            names.add(found.group(1))
            continue
        used = _USE_RE.match(line)
        if used is not None:
            names.add(used.group(2) or used.group(1).rsplit("::", maxsplit=1)[-1])
    return names


class TestClaimTable:
    """Every module-level name the serde emitter writes must have run through the claim table.

    A ``de.rs`` is its own Rust module namespace, so it collides with nothing the AST module
    claims — and everything in it collides with everything else in it.  Reading the emitted
    source back is what makes an unclaimed name family an automatic failure rather than
    something a reviewer has to notice.
    """

    @pytest.mark.parametrize(
        ("name", "grammar", "sidecar"), fixtures.EXAMPLES, ids=[case[0] for case in fixtures.EXAMPLES]
    )
    def test_every_name_the_module_defines_was_claimed(self, name: str, grammar: str, sidecar: str) -> None:
        model = model_for(grammar, sidecar)
        source = gsm2serde_rs.generate_de_rs(
            model, "super::cst", parser_mod_path="super::parser", ast_mod_path="super::ast"
        )
        unclaimed = sorted(_module_level_names(source) - set(am.serde_claims(model)))
        assert not unclaimed, f"{name}: unclaimed generated names {unclaimed}"

    def test_the_sweep_reaches_every_name_family(self) -> None:
        """An extractor returning an empty set would make the sweep above pass on anything."""
        model = model_for(fixtures.FOLD_GRAMMAR, fixtures.FOLD_SIDECAR)
        source = gsm2serde_rs.generate_de_rs(
            model, "super::cst", parser_mod_path="super::parser", ast_mod_path="super::ast"
        )
        names = _module_level_names(source)
        assert {
            am.serde_shape_name("expr"),
            am.serde_ast_constant_name("expr"),
            am.serde_fold_name("expr"),
            am.signature_constant_name("factor"),
            am.serde_alternatives_name("factor"),
            am.serde_entry_name("expr"),
            am.SERDE_FROM_STR,
            "cst",
            "parser",
            "ast",
        } <= names

    def test_two_things_wanting_one_name_is_a_generation_error(self) -> None:
        """No grammar reaches this: rule names are unique and lowercase, and the spellings are
        fixed transforms of them.  The guard is what keeps a name family added later — the
        AST-typed field constants, a second entry point — from silently clobbering one.
        """
        model = model_for("doc := v:/[a-z]+/ ;\n")
        rules = model.grammar.rules
        doubled = dataclasses.replace(model, grammar=dataclasses.replace(model.grammar, rules=(*rules, rules[0])))
        with pytest.raises(am.AstModelError, match="collides with"):
            am.serde_claims(doubled)

    def test_the_doubled_grammar_is_a_faithful_stand_in(self) -> None:
        """The white-box fixture above is only evidence if the undoubled model claims cleanly."""
        model = model_for("doc := v:/[a-z]+/ ;\n")
        assert isinstance(model.grammar, gsm.Grammar)
        assert am.serde_shape_name("doc") in am.serde_claims(model)
