//! The Deserializer: a described CST tree served as serde's data model.
//!
//! The target type drives everything. A field typed `u16` reaches `deserialize_u16`, which runs
//! the `type: u16` scalar gate over the source text the node covers; a field typed `String`
//! reaches `deserialize_str`, which serves the same text; a struct reaches `deserialize_struct`,
//! which serves one map entry per model field. Nothing here inspects the target — that is
//! serde's job — and nothing decides a value's type ahead of being asked for one.
//!
//! Positions come from the tree, messages from whoever raised them. serde's derive reports
//! unknown fields, missing fields and type mismatches through `serde::de::Error`, which carries
//! no position, so every frame that re-enters generated shape data fills one in on the way out:
//! the field's own child span in the key and value phases, the node's span at the end of a
//! struct. [`DeserializeError::positioned`] fills only an unpositioned error, so an inner
//! frame's precise span survives the outer frame it passes through.

use std::collections::HashMap;
use std::rc::Rc;

use fltk_ast_core::{
    dispatch, duplicate_key, fold_left, fold_right, merged_span, node_text, one, optional, presence, scalar,
    text as child_text, unexpected_child, AstError,
};
use fltk_cst_core::Span;
use serde::de::value::{StrDeserializer, StringDeserializer};
use serde::de::{
    DeserializeOwned, DeserializeSeed, Deserializer, EnumAccess, IntoDeserializer, MapAccess, SeqAccess, VariantAccess,
    Visitor,
};

use crate::channel::{self, Payload};
use crate::error::DeserializeError;
use crate::tree::{
    Alternative, Child, Container, Content, Direction, Field, Fold, Form, Key, KeyKind, Node, Variant, Wrapper,
};
use crate::wrappers::{AST_NAME_PREFIX, RAW_NAME, SPANNED_NAME};

/// Deserialize `T` from one CST node.
pub fn from_node<T: DeserializeOwned>(node: Node) -> Result<T, DeserializeError> {
    T::deserialize(Value::Node(node))
}

/// One position in the tree, as serde's data model sees it.
#[derive(Clone)]
enum Value {
    /// A node, served as whatever its rule's shape says.
    Node(Node),
    /// One element of a keyed field, served as the map form's value: the node without the
    /// field that keys it, which is the map key it arrived under.
    Element { node: Node, key_field: &'static str },
    /// A terminal's span, named by the rule and label it was read under so a failure to reach
    /// its text can say where it came from.
    Text {
        span: Span,
        rule: &'static str,
        label: &'static str,
    },
    /// Whether an optional labeled literal was written, and where it was written: the
    /// literal's own span when it is there, and nowhere when it is not.
    Flag(bool, Span),
    /// A field's children, in source order.
    Seq(Vec<Value>),
    /// A keyed field's elements, in source order, and what keys them.
    Keyed { key: Key, items: Vec<Value> },
    /// A sum alternative's own view of the node it matched: the alternative's fields rather
    /// than the whole rule's, which is what a generated payload holds.
    Payload { node: Node, fields: &'static [Field] },
    /// An externally tagged value: the variant name a sum alternative or a fold chain node
    /// carries, and what it carries.
    Tagged { name: &'static str, payload: Box<Value> },
    /// One link of a fold chain: the operator, and the two sub-chains it joins.
    Link {
        fold: &'static Fold,
        op: Box<Value>,
        lhs: Box<Value>,
        rhs: Box<Value>,
        /// Covers everything below this link in the nesting.
        span: Span,
    },
}

impl Value {
    /// Where this value is, which is where an error about it is reported.
    ///
    /// A sequence covers its elements' spans — that is what a `Spanned` over a collection
    /// field covers — and an empty one, like an unwritten presence flag, is nowhere in
    /// particular.
    fn span(&self) -> Span {
        match self {
            Value::Node(node) | Value::Element { node, .. } | Value::Payload { node, .. } => node.span(),
            Value::Text { span, .. } => span.clone(),
            Value::Flag(_, span) => span.clone(),
            Value::Seq(items) | Value::Keyed { items, .. } => covering(items),
            Value::Tagged { payload, .. } => payload.span(),
            Value::Link { span, .. } => span.clone(),
        }
    }

    /// What this value is, for the "found …" half of a mismatch.
    fn describe(&self) -> &'static str {
        match self.node() {
            Some(node) => match node.shape().form {
                Form::Product { .. } | Form::Sum { .. } | Form::Fold(_) => "a map",
                Form::Terminal { .. } => "a string",
                Form::Enum { truthy: Some(_), .. } => "a boolean",
                Form::Enum { .. } => "a string",
                // Erased before it is served, so a mismatch describes the payload and not
                // this; only a payload that could not be read reaches here.
                Form::Transparent { .. } => "a value",
            },
            None => match self {
                Value::Text { .. } => "a string",
                Value::Flag(..) => "a boolean",
                Value::Seq(_) => "a sequence",
                Value::Keyed { .. } | Value::Tagged { .. } | Value::Link { .. } => "a map",
                Value::Node(_) | Value::Element { .. } | Value::Payload { .. } => unreachable!("all are nodes"),
            },
        }
    }

    /// The node this value is positioned at, if it is at one.
    fn node(&self) -> Option<&Node> {
        match self {
            Value::Node(node) | Value::Element { node, .. } | Value::Payload { node, .. } => Some(node),
            _ => None,
        }
    }

    /// The product this value is positioned at, if it is one: its node, its fields, and the
    /// field left out because it is the map key the value arrived under.
    ///
    /// A sum alternative's payload is a product too, over the alternative's own fields rather
    /// than the rule's — the node is the same one either way.
    fn product(&self) -> Option<(&Node, &'static [Field], Option<&'static str>)> {
        let (node, key_field) = match self {
            Value::Payload { node, fields } => return Some((node, fields, None)),
            Value::Node(node) => (node, None),
            Value::Element { node, key_field } => (node, Some(*key_field)),
            _ => return None,
        };
        match node.shape().form {
            Form::Product { fields } => Some((node, fields, key_field)),
            _ => None,
        }
    }

    /// This position with the `transparent;` rules erased: an erased node is its one field's
    /// value, and a chain of them bottoms out at what the innermost carries.
    fn erased(self) -> Result<Value, DeserializeError> {
        let mut current = self;
        loop {
            match current {
                Value::Node(node) => match node.shape().form {
                    Form::Transparent { field } => current = transparent_value(&node, &field)?,
                    _ => return Ok(Value::Node(node)),
                },
                other => return Ok(other),
            }
        }
    }

    /// What this position actually serves, with the forms that stand for something else
    /// resolved: a transparent rule's node is its one field's value, a sum rule's node is its
    /// matched alternative under the alternative's name, and a fold rule's node is its chain.
    ///
    /// Resolved on demand rather than when the value is built, because a field the target
    /// never asks for is never walked: a node whose dispatch would fail, or whose fold
    /// interleaving is broken, costs nothing where nothing reads it. Idempotent, so a method
    /// that resolves and then delegates to one that resolves again is correct.
    fn served(self) -> Result<Value, DeserializeError> {
        let value = self.erased()?;
        if let Value::Node(node) = &value {
            match node.shape().form {
                Form::Sum { table, alternatives } => return sum_value(node, table, alternatives),
                Form::Fold(fold) => return fold_value(node, fold),
                _ => {}
            }
        }
        Ok(value)
    }

    /// The name of the variant an enum-shaped node matched, which is the string such a node is
    /// served as. Any other position has none, and is served its source text instead.
    fn variant_name(&self) -> Result<Option<&'static str>, DeserializeError> {
        let Some(node) = self.node() else {
            return Ok(None);
        };
        let Form::Enum { variants, .. } = node.shape().form else {
            return Ok(None);
        };
        matched_variant(node, variants).map(|variant| Some(variant.name))
    }

    /// The source text a scalar target reads, with the rule and span naming it.
    ///
    /// Served from any node, not only a terminal-only one: the span of a node *is* the lexeme,
    /// which is what makes `port: u16` work where the grammar's value side is a whole
    /// expression rule. A node whose span covers interior separators fails the gate, and the
    /// message names the text it refused.
    fn lexeme(self, expected: &str) -> Result<(String, &'static str, Span), DeserializeError> {
        let value = self.served()?;
        if let Some(node) = value.node() {
            let span = lexeme_span(node)?;
            return Ok((node_text(&span, node.rule())?, node.rule(), span));
        }
        match &value {
            Value::Text { span, rule, label } => Ok((child_text(span, rule, label, span)?, rule, span.clone())),
            _ => Err(value.unexpected(expected)),
        }
    }

    /// A target that wants something this position cannot be.
    fn unexpected(&self, expected: &str) -> DeserializeError {
        DeserializeError::new(
            format!("expected {expected}, found {}", self.describe()),
            self.span(),
        )
    }

    /// A target shape the frontend does not serve at all.
    fn unsupported(&self, what: &str) -> DeserializeError {
        DeserializeError::new(
            format!("{what} are not supported by the FLTK serde frontend"),
            self.span(),
        )
    }
}

/// One node together with its children, read out of it once.
///
/// [`Node::children`] allocates a fresh `Vec` on every call, so a node read under more than
/// one label — a product's fields, the steps of a hoist
/// path, a sum's dispatch and then the payload it selected — is walked once and bucketed from
/// that one answer.
struct Walked {
    node: Node,
    children: Vec<(Option<&'static str>, Child)>,
}

impl Walked {
    fn new(node: Node) -> Self {
        let children = node.children();
        Walked { node, children }
    }

    /// The children carrying one label, in source order.
    ///
    /// Unlabeled children — trivia, `$`-included literals — carry no label to match and are
    /// skipped, which is the same bucketing a product's fields get.
    fn labeled(&self, label: &'static str) -> Vec<Child> {
        self.children
            .iter()
            .filter(|(child_label, _)| *child_label == Some(label))
            .map(|(_, child)| child.clone())
            .collect()
    }

    /// The single child of a required label, refused through the shared arity template.
    fn required(&self, label: &'static str) -> Result<Child, AstError> {
        let children = self.labeled(label);
        let borrowed: Vec<&Child> = children.iter().collect();
        one(&borrowed, self.node.rule(), label, &self.node.span()).cloned()
    }
}

/// The single child of a required label on a node nothing else is read from.
fn required_child(node: &Node, label: &'static str) -> Result<Child, AstError> {
    Walked::new(node.clone()).required(label)
}

/// One step of a hoist path: the wrapper node its label carries, or `None` where an optional
/// step is not there.
///
/// A flattened wrapper occupies one item position, so each step takes at most one child; more
/// than one, or none where the step is required, is the shared arity refusal against the node
/// the step was taken from. A wrapper label carrying a terminal rather than a node is the
/// shared unexpected-kind refusal — both are reachable from a hand-built CST only.
fn step_into(parent: &Walked, step: &Wrapper) -> Result<Option<Node>, DeserializeError> {
    let children = parent.labeled(step.label);
    let rule = parent.node.rule();
    let span = parent.node.span();
    if children.is_empty() && step.optional {
        return Ok(None);
    }
    let borrowed: Vec<&Child> = children.iter().collect();
    let child = if step.optional {
        optional(&borrowed, rule, step.label, &span)?.cloned()
    } else {
        Some(one(&borrowed, rule, step.label, &span)?.clone())
    };
    let child = child.expect("an empty optional step returned already");
    let Child::Node(inner) = child else {
        return Err(unexpected_child(rule, step.label, &child.span()).into());
    };
    Ok(Some(inner))
}

/// The `flatten;` wrappers one node's hoisted fields are read through, each walked once.
///
/// Hoist paths share prefixes: every field flattened out of one wrapper names it, and a field
/// two wrappers down names both. Descending per field would re-read every wrapper on the way
/// once per field it serves, so each distinct prefix is descended into once here and the node
/// it reaches keeps its children for all of them.
#[derive(Default)]
struct Wrappers {
    /// One entry per path prefix already walked, and what it reached — `None` where an optional
    /// step on the way was not there, which empties every field below it.
    walked: Vec<(&'static [Wrapper], Option<Rc<Walked>>)>,
}

impl Wrappers {
    /// The node a hoist path ends at, taking only the steps not already taken.
    fn resolve(
        &mut self,
        root: &Rc<Walked>,
        path: &'static [Wrapper],
    ) -> Result<Option<Rc<Walked>>, DeserializeError> {
        if path.is_empty() {
            return Ok(Some(Rc::clone(root)));
        }
        if let Some((_, reached)) = self.walked.iter().find(|(prefix, _)| *prefix == path) {
            return Ok(reached.clone());
        }
        let (above, last) = path.split_at(path.len() - 1);
        let reached = match self.resolve(root, above)? {
            Some(parent) => step_into(&parent, &last[0])?.map(|node| Rc::new(Walked::new(node))),
            None => None,
        };
        self.walked.push((path, reached.clone()));
        Ok(reached)
    }
}

/// Where one field's children are, and what a refusal about them names: the node itself for an
/// ordinary field, and the wrapper its path ends at for a hoisted one.
///
/// `own` is the containing node's already-bucketed children, which is what an unhoisted field
/// takes. A hoisted field whose wrapper is absent takes nothing, so it is served as the empty
/// value of whatever container it is — no map entry for a single or optional field, an empty
/// sequence or map for a collection, `false` for a presence flag.
fn field_children(
    root: &Rc<Walked>,
    wrappers: &mut Wrappers,
    field: &Field,
    own: Vec<Child>,
) -> Result<(&'static str, Vec<Child>, Span), DeserializeError> {
    if field.hoist.is_empty() {
        let span = own.first().map_or_else(|| root.node.span(), Child::span);
        return Ok((root.node.rule(), own, span));
    }
    match wrappers.resolve(root, field.hoist)? {
        Some(holder) => {
            let children = holder.labeled(field.label);
            let span = children.first().map_or_else(|| holder.node.span(), Child::span);
            Ok((holder.node.rule(), children, span))
        }
        None => Ok((root.node.rule(), Vec::new(), root.node.span())),
    }
}

/// The span whose text a node's lexeme comes from: its own, or the `text_from:` child's.
fn lexeme_span(node: &Node) -> Result<Span, DeserializeError> {
    let Form::Terminal {
        text_from: Some(label),
    } = node.shape().form
    else {
        return Ok(node.span());
    };
    Ok(required_child(node, label)?.span())
}

/// The alternative an enum-shaped node matched: the first, in declaration order, whose label
/// one of the node's children carries.
///
/// Declaration order rather than child order: a parse puts exactly one alternative's children
/// there, and a hand-built node carrying two must resolve the same way on every layer that
/// can be handed it.
fn matched_variant(node: &Node, variants: &'static [Variant]) -> Result<&'static Variant, DeserializeError> {
    let children = node.children();
    variants
        .iter()
        .find(|variant| children.iter().any(|(label, _)| *label == Some(variant.label)))
        .ok_or_else(|| {
            DeserializeError::new(
                format!("rule {:?}: no alternative label is present", node.rule()),
                node.span(),
            )
        })
}

/// The span covering a run of values, which is where a frame over all of them is positioned.
fn covering(items: &[Value]) -> Span {
    merged_span(items.iter().map(Value::span))
}

/// A transparent rule's node as the value of its one field, which is what a use site carries.
///
/// The rule is erased, so nothing wraps the payload: a `transparent;` rule over a single
/// `value:` field serves what `value:` holds and no map around it. A node without the payload
/// has no value at all, refused through the shared arity template.
fn transparent_value(node: &Node, field: &Field) -> Result<Value, DeserializeError> {
    let root = Rc::new(Walked::new(node.clone()));
    let own = if field.hoist.is_empty() {
        root.labeled(field.label)
    } else {
        Vec::new()
    };
    let (rule, children, span) = field_children(&root, &mut Wrappers::default(), field, own)?;
    match field_value(rule, field, children, &span)? {
        Some(value) => Ok(value),
        None => Err(one::<Child>(&[], rule, field.label, &span)
            .expect_err("no child fails the required arity")
            .into()),
    }
}

/// The (label, kind) pair one child occupies, as a dispatch table names it.
fn child_kind(child: &Child) -> &'static str {
    match child {
        Child::Text(_) => dispatch::TEXT_KIND,
        Child::Node(node) => node.rule(),
    }
}

/// A sum rule's node as the alternative its labeled children came from, tagged by name.
///
/// Selection is the shared evaluator's, so an alternative recovered here is the one the AST
/// converters would recover — including its refusal of a labeled child no alternative can
/// hold, which only a hand-built CST carries.
fn sum_value(
    node: &Node,
    table: &'static dispatch::Table,
    alternatives: &'static [Alternative],
) -> Result<Value, DeserializeError> {
    let walked = Walked::new(node.clone());
    let selected = table.select(walked.children.iter().map(|(label, child)| (*label, child_kind(child))));
    let alternative = selected.and_then(|index| alternatives.get(index)).ok_or_else(|| {
        DeserializeError::new(
            format!(
                "rule {:?}: no alternative matches the node's labeled children",
                node.rule()
            ),
            node.span(),
        )
    })?;
    let payload = match alternative.payload {
        Content::Child { label } => child_value(node.rule(), label, walked.required(label)?),
        Content::Fields { fields } => Value::Payload {
            node: node.clone(),
            fields,
        },
    };
    Ok(Value::Tagged {
        name: alternative.name,
        payload: Box::new(payload),
    })
}

/// A fold rule's node as the chain its flat run of children nests into.
///
/// The two runs are collected here — the labels are the only part of a fold this crate can
/// read — and handed to the runtime that the generated converters use, so the nesting order,
/// the merged link spans and the interleaving refusal are one implementation.
fn fold_value(node: &Node, fold: &'static Fold) -> Result<Value, DeserializeError> {
    let rule = node.rule();
    let span = node.span();
    let mut operands = Vec::new();
    let mut operators = Vec::new();
    for (label, child) in node.children() {
        let at = child.span();
        if label == Some(fold.operand_label) {
            operands.push((child_value(rule, fold.operand_label, child), at));
        } else if label == Some(fold.operator_label) {
            operators.push(child_value(rule, fold.operator_label, child));
        }
    }
    let operand = |value: Value| Value::Tagged {
        name: fold.operand_variant,
        payload: Box::new(value),
    };
    let link = |op: Value, lhs: Value, rhs: Value, span: Span| Value::Tagged {
        name: fold.binary_variant,
        payload: Box::new(Value::Link {
            fold,
            op: Box::new(op),
            lhs: Box::new(lhs),
            rhs: Box::new(rhs),
            span,
        }),
    };
    let chain = match fold.direction {
        Direction::Left => fold_left(rule, &span, operands, operators, operand, link),
        Direction::Right => fold_right(rule, &span, operands, operators, operand, link),
    };
    Ok(chain?)
}

/// A generated AST type at this position: the conversion its `Deserialize` impl handed in, run
/// over the node here, and the value it built handed back.
///
/// The AST layer's `from_cst` is the whole of the mapping, so a field declared as `ast::Expr`
/// gets folds, transparent chains and coercions with nothing on this path reimplementing them,
/// and a failure is the AST layer's own error carrying the span it was raised at.
///
/// `transparent;` rules are erased first, for the same reason the AST layer erases them: a use
/// site of an erased rule carries the payload's type, so the node an AST target names is the one
/// below the wrapper. Sum and fold rules are *not* resolved — their nodes are exactly what their
/// own AST types convert.
fn ast_value<'de, V: Visitor<'de>>(value: Value, rule: &str, visitor: V) -> Result<V::Value, DeserializeError> {
    let Some(conversion) = channel::take_conversion() else {
        // Nothing handed in a conversion, so whoever asked for this name is not the generated
        // impl that owns it.
        return Err(DeserializeError::new(
            format!("an AST value of rule `{rule}` is served only through its generated `Deserialize` impl"),
            value.span(),
        ));
    };
    let value = value.erased()?;
    let Some(node) = value.node() else {
        return Err(value.unexpected(&format!("a `{rule}` node to convert")));
    };
    let span = value.span();
    let built = conversion
        .run(node.carried())
        .map_err(|error| DeserializeError::from(error).positioned(span))?;
    channel::provide(Payload::Ast(built), move || visitor.visit_newtype_struct(value))
}

/// One `deserialize_<scalar>` method: the gate its `type:` counterpart runs, over the lexeme.
macro_rules! scalar_method {
    ($method:ident, $visit:ident, $parse:ident, $expected:literal) => {
        fn $method<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
            let (text, rule, span) = self.lexeme($expected)?;
            visitor.$visit(scalar::$parse(&text, rule, &span)?)
        }
    };
}

impl<'de> Deserializer<'de> for Value {
    type Error = DeserializeError;

    /// The self-describing shape: a product is a map, a terminal or a span child is a string,
    /// an enum-shaped rule is its variant name (or a boolean where it carries one), a presence
    /// flag is a boolean, and a collection is a sequence.
    ///
    /// A keyed field is the one position with two forms and no target to choose between them,
    /// so it is resolved here: the map form is served, which is the shape the rule's `key:`
    /// declares it to have.
    fn deserialize_any<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        let value = self.served()?;
        if let Some((node, fields, key_field)) = value.product() {
            return visit_product(node, fields, key_field, visitor);
        }
        if let Some(node) = value.node() {
            if let Form::Enum { variants, truthy } = node.shape().form {
                let variant = matched_variant(node, variants)?;
                return match truthy {
                    Some(label) => visitor.visit_bool(variant.label == label),
                    None => visitor.visit_borrowed_str(variant.name),
                };
            }
        }
        match value {
            Value::Flag(flag, _) => visitor.visit_bool(flag),
            Value::Seq(items) => visitor.visit_seq(Elements::new(items)),
            Value::Keyed { key, items } => visit_keyed(key, items, visitor),
            Value::Tagged { name, payload } => visit_tagged(name, *payload, visitor),
            Value::Link {
                fold,
                op,
                lhs,
                rhs,
                span,
            } => visit_link(fold, *op, *lhs, *rhs, span, visitor),
            other => {
                let (text, ..) = other.lexeme("a string")?;
                visitor.visit_string(text)
            }
        }
    }

    scalar_method!(deserialize_i8, visit_i8, parse_i8, "an i8");
    scalar_method!(deserialize_i16, visit_i16, parse_i16, "an i16");
    scalar_method!(deserialize_i32, visit_i32, parse_i32, "an i32");
    scalar_method!(deserialize_i64, visit_i64, parse_i64, "an i64");
    scalar_method!(deserialize_u8, visit_u8, parse_u8, "a u8");
    scalar_method!(deserialize_u16, visit_u16, parse_u16, "a u16");
    scalar_method!(deserialize_u32, visit_u32, parse_u32, "a u32");
    scalar_method!(deserialize_u64, visit_u64, parse_u64, "a u64");
    scalar_method!(deserialize_f32, visit_f32, parse_f32, "an f32");
    scalar_method!(deserialize_f64, visit_f64, parse_f64, "an f64");

    /// Only a presence flag and a `bool:`-shaped rule are booleans: the texts `true` and
    /// `false` are not special-cased, so a grammar's own boolean literals reach a `bool` target
    /// through the sidecar's `bool:` rather than by their spelling.
    fn deserialize_bool<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        let value = self.served()?;
        if let Some(node) = value.node() {
            if let Form::Enum {
                variants,
                truthy: Some(label),
            } = node.shape().form
            {
                return visitor.visit_bool(matched_variant(node, variants)?.label == label);
            }
        }
        match value {
            Value::Flag(flag, _) => visitor.visit_bool(flag),
            other => Err(other.unexpected("a boolean")),
        }
    }

    /// A variant name outlives any `'de`, so it is served borrowed and costs nothing; source
    /// text is already owned by the time it is read, and is handed over rather than copied.
    fn deserialize_str<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        let value = self.served()?;
        if let Some(name) = value.variant_name()? {
            return visitor.visit_borrowed_str(name);
        }
        let (text, ..) = value.lexeme("a string")?;
        visitor.visit_string(text)
    }

    fn deserialize_string<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        self.deserialize_str(visitor)
    }

    /// A `char` is a one-character lexeme; anything else is a length error naming the text.
    fn deserialize_char<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        let (text, rule, span) = self.lexeme("a char")?;
        let mut chars = text.chars();
        match (chars.next(), chars.next()) {
            (Some(one), None) => visitor.visit_char(one),
            _ => Err(DeserializeError::new(
                format!("rule {rule:?}: {text:?} is not a single character"),
                span,
            )),
        }
    }

    /// A field that is there at all is a value: an absent optional child leaves the field out
    /// of the map entirely, which is what makes serde's own `None` the answer for it.
    fn deserialize_option<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        visitor.visit_some(self)
    }

    fn deserialize_unit<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        visitor.visit_unit()
    }

    fn deserialize_unit_struct<V: Visitor<'de>>(
        self,
        _name: &'static str,
        visitor: V,
    ) -> Result<V::Value, Self::Error> {
        visitor.visit_unit()
    }

    /// The magic newtype-struct names are the wrapper protocol; every other newtype is
    /// transparent, as it is under any Deserializer.
    fn deserialize_newtype_struct<V: Visitor<'de>>(
        self,
        name: &'static str,
        visitor: V,
    ) -> Result<V::Value, Self::Error> {
        match name {
            SPANNED_NAME => {
                let span = self.span();
                channel::provide(Payload::span(span), move || visitor.visit_newtype_struct(self))
            }
            RAW_NAME => {
                let Some(node) = self.node() else {
                    return Err(self.unexpected("a node to hold as `Raw`"));
                };
                let payload = Payload::Node(node.carried());
                channel::provide(payload, move || visitor.visit_newtype_struct(self))
            }
            _ => match name.strip_prefix(AST_NAME_PREFIX) {
                Some(rule) => ast_value(self, rule, visitor),
                None => visitor.visit_newtype_struct(self),
            },
        }
    }

    /// A keyed field is a sequence too: its plain elements, key field included, which is what
    /// makes one grammar region serve both a map target and a `Vec` one.
    fn deserialize_seq<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        match self.served()? {
            Value::Seq(items) | Value::Keyed { items, .. } => visitor.visit_seq(Elements::new(items)),
            other => Err(other.unexpected("a sequence")),
        }
    }

    /// The map forms: a product's fields, a keyed field's entries, an externally tagged sum or
    /// fold value, and one link of a chain. Each is what the self-describing shape serves too,
    /// so the arms are not written twice.
    fn deserialize_map<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        let value = self.served()?;
        let is_map = value.product().is_some()
            || matches!(value, Value::Keyed { .. } | Value::Tagged { .. } | Value::Link { .. });
        if is_map {
            return value.deserialize_any(visitor);
        }
        Err(value.unexpected("a map"))
    }

    fn deserialize_struct<V: Visitor<'de>>(
        self,
        _name: &'static str,
        _fields: &'static [&'static str],
        visitor: V,
    ) -> Result<V::Value, Self::Error> {
        self.deserialize_map(visitor)
    }

    /// A sum rule and a fold chain are externally tagged enums that carry content; an
    /// enum-shaped rule names a unit variant, which is the same spelling with nothing in it;
    /// any other position names a variant by its own text.
    fn deserialize_enum<V: Visitor<'de>>(
        self,
        _name: &'static str,
        _variants: &'static [&'static str],
        visitor: V,
    ) -> Result<V::Value, Self::Error> {
        let value = self.served()?;
        if let Value::Tagged { name, payload } = value {
            return visitor.visit_enum(TaggedEnum {
                name,
                payload: *payload,
            });
        }
        if let Some(name) = value.variant_name()? {
            let variant: StrDeserializer<'de, Self::Error> = name.into_deserializer();
            return visitor.visit_enum(variant);
        }
        let (text, ..) = value.lexeme("an enum")?;
        let variant: StringDeserializer<Self::Error> = text.into_deserializer();
        visitor.visit_enum(variant)
    }

    /// A field or variant name, which reaches this only where a target deserializes one from
    /// the source itself; the map keys of a product come from the shape, not from here, and a
    /// keyed field's come from its elements' key children as ordinary values.
    fn deserialize_identifier<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        self.deserialize_str(visitor)
    }

    /// A value the target skipped: nothing is walked, and nothing about it has to be servable.
    fn deserialize_ignored_any<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        visitor.visit_unit()
    }

    fn deserialize_bytes<V: Visitor<'de>>(self, _visitor: V) -> Result<V::Value, Self::Error> {
        Err(self.unsupported("byte targets"))
    }

    fn deserialize_byte_buf<V: Visitor<'de>>(self, _visitor: V) -> Result<V::Value, Self::Error> {
        Err(self.unsupported("byte targets"))
    }

    fn deserialize_tuple<V: Visitor<'de>>(self, _len: usize, _visitor: V) -> Result<V::Value, Self::Error> {
        Err(self.unsupported("tuple targets"))
    }

    fn deserialize_tuple_struct<V: Visitor<'de>>(
        self,
        _name: &'static str,
        _len: usize,
        _visitor: V,
    ) -> Result<V::Value, Self::Error> {
        Err(self.unsupported("tuple-struct targets"))
    }
}

/// What a map key is deserialized from: a field name the shape supplies, or a value the source
/// does.
trait MapKey<'de> {
    fn deserialize_key<S: DeserializeSeed<'de>>(self, seed: S) -> Result<S::Value, DeserializeError>;
}

impl<'de> MapKey<'de> for &'static str {
    fn deserialize_key<S: DeserializeSeed<'de>>(self, seed: S) -> Result<S::Value, DeserializeError> {
        let key: StrDeserializer<'de, DeserializeError> = self.into_deserializer();
        seed.deserialize(key)
    }
}

impl<'de> MapKey<'de> for KeyValue {
    fn deserialize_key<S: DeserializeSeed<'de>>(self, seed: S) -> Result<S::Value, DeserializeError> {
        seed.deserialize(self)
    }
}

/// One keyed region's key, read from its element's key child under the declared [`KeyKind`].
#[derive(Clone)]
enum KeyValue {
    /// A text-typed key: the key child's source text.
    Text(String, Span),
    /// An integer-typed key: the value its gate read, and the width that gate was.
    Number(KeyKind, i128, Span),
}

impl KeyValue {
    /// Read one element's key child under the declared type, gate failures and all.
    fn read(kind: KeyKind, text: String, rule: &'static str, span: Span) -> Result<Self, DeserializeError> {
        macro_rules! gate {
            ($parse:ident) => {
                i128::from(scalar::$parse(&text, rule, &span)?)
            };
        }
        let number = match kind {
            KeyKind::Text => return Ok(KeyValue::Text(text, span)),
            KeyKind::I8 => gate!(parse_i8),
            KeyKind::I16 => gate!(parse_i16),
            KeyKind::I32 => gate!(parse_i32),
            KeyKind::I64 => gate!(parse_i64),
            KeyKind::U8 => gate!(parse_u8),
            KeyKind::U16 => gate!(parse_u16),
            KeyKind::U32 => gate!(parse_u32),
            KeyKind::U64 => gate!(parse_u64),
        };
        Ok(KeyValue::Number(kind, number, span))
    }

    /// What makes two elements one key: the text of a text key, the gated value of an integer
    /// one — so `7` and `007` are two keys under `Text` and one under any integer width.
    fn identity(&self) -> Identity {
        match self {
            KeyValue::Text(text, _) => Identity::Text(text.clone()),
            KeyValue::Number(_, number, _) => Identity::Number(*number),
        }
    }

    /// Where the key was written, which positions both a duplicate refusal's key phase and a
    /// key-target mismatch.
    fn span(&self) -> Span {
        match self {
            KeyValue::Text(_, span) | KeyValue::Number(_, _, span) => span.clone(),
        }
    }
}

/// A key's identity, which is what the duplicate check and `multi`'s grouping compare.
#[derive(Clone, PartialEq, Eq, Hash)]
enum Identity {
    Text(String),
    Number(i128),
}

impl Identity {
    /// The offending key as the shared `duplicate_key` template renders it: quoted for a text
    /// key, bare for an integer one.
    fn duplicate(&self, rule: &str, span: &Span, previous: &Span) -> AstError {
        match self {
            Identity::Text(text) => duplicate_key(rule, text, span, previous),
            Identity::Number(number) => duplicate_key(rule, number, span, previous),
        }
    }
}

/// A key is served from its declared type, never from what the target asks for: a `u16`-typed
/// key drives `visit_u16`, and serde's own forwarding fits it to whatever integer the target
/// names. A target whose key type disagrees with the declaration gets serde's invalid-type
/// error, positioned at the key child by the key phase.
impl<'de> Deserializer<'de> for KeyValue {
    type Error = DeserializeError;

    fn deserialize_any<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        macro_rules! serve {
            ($visit:ident, $ty:ty, $number:expr) => {
                visitor.$visit(<$ty>::try_from($number).expect("the gate range-checked this width"))
            };
        }
        match self {
            KeyValue::Text(text, _) => visitor.visit_string(text),
            KeyValue::Number(kind, number, _) => match kind {
                KeyKind::Text => unreachable!("a text key is not a number"),
                KeyKind::I8 => serve!(visit_i8, i8, number),
                KeyKind::I16 => serve!(visit_i16, i16, number),
                KeyKind::I32 => serve!(visit_i32, i32, number),
                KeyKind::I64 => serve!(visit_i64, i64, number),
                KeyKind::U8 => serve!(visit_u8, u8, number),
                KeyKind::U16 => serve!(visit_u16, u16, number),
                KeyKind::U32 => serve!(visit_u32, u32, number),
                KeyKind::U64 => serve!(visit_u64, u64, number),
            },
        }
    }

    /// The structural methods delegate as serde's convention has them, so a consumer newtype
    /// key (`struct Id(u16)`) or an `Option` one observes the declared representation with
    /// nothing here to arrange it.
    fn deserialize_option<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        visitor.visit_some(self)
    }

    fn deserialize_newtype_struct<V: Visitor<'de>>(
        self,
        _name: &'static str,
        visitor: V,
    ) -> Result<V::Value, Self::Error> {
        visitor.visit_newtype_struct(self)
    }

    fn deserialize_ignored_any<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
        visitor.visit_unit()
    }

    // `i128`/`u128` are left off: serde's own default methods refuse them, which is the
    // frontend's v1 contract for those widths everywhere else too.
    serde::forward_to_deserialize_any! {
        bool i8 i16 i32 i64 u8 u16 u32 u64 f32 f64 char str string bytes byte_buf
        unit unit_struct seq tuple tuple_struct map struct enum identifier
    }
}

/// One entry of a map: its key, where the key is, its value, and where the value is.
type Entry<K> = (K, Span, Value, Span);

/// The entries of a map, served in the order they were built.
///
/// Both map forms — a product's fields and a keyed field's entries — are this one machine, so
/// the rule that an error is positioned where it was raised and nowhere else has a single home.
/// They differ only in what a key is and in which spans the two phases pin, which their
/// builders decide.
struct MapEntries<K> {
    entries: std::vec::IntoIter<Entry<K>>,
    pending: Option<(Value, Span)>,
}

impl<K> MapEntries<K> {
    fn new(entries: Vec<Entry<K>>) -> Self {
        MapEntries {
            entries: entries.into_iter(),
            pending: None,
        }
    }
}

impl<'de, K: MapKey<'de>> MapAccess<'de> for MapEntries<K> {
    type Error = DeserializeError;

    /// The key phase, where `deny_unknown_fields` raises its unknown-field error and a key
    /// target the source text does not fit reports it: the key's own span positions both.
    fn next_key_seed<S: DeserializeSeed<'de>>(&mut self, seed: S) -> Result<Option<S::Value>, Self::Error> {
        let Some((key, key_span, value, span)) = self.entries.next() else {
            return Ok(None);
        };
        let key = key.deserialize_key(seed).map_err(|error| error.positioned(key_span))?;
        self.pending = Some((value, span));
        Ok(Some(key))
    }

    /// The value phase, where a wrong-type or coercion failure is raised: the value's span is
    /// what positions it.
    fn next_value_seed<S: DeserializeSeed<'de>>(&mut self, seed: S) -> Result<S::Value, Self::Error> {
        let (value, span) = self
            .pending
            .take()
            .expect("serde asks for a value only after the key it belongs to");
        seed.deserialize(value).map_err(|error| error.positioned(span))
    }

    fn size_hint(&self) -> Option<usize> {
        Some(self.entries.len())
    }
}

/// The externally tagged form as a self-describing value: a one-entry map, `{variant: content}`.
///
/// It is the shape serde's own externally tagged enums serialize to, so a `Value`-like or
/// untagged target — which has no variant to ask for and reaches this through
/// `deserialize_any` — reads a sum or a fold chain the same way it would read one from JSON.
fn visit_tagged<'de, V: Visitor<'de>>(
    name: &'static str,
    payload: Value,
    visitor: V,
) -> Result<V::Value, DeserializeError> {
    let span = payload.span();
    visitor.visit_map(MapEntries::new(vec![(name, span.clone(), payload, span)]))
}

/// One link of a fold chain as a map: the operator, and the two sub-chains it joins.
fn visit_link<'de, V: Visitor<'de>>(
    fold: &'static Fold,
    op: Value,
    lhs: Value,
    rhs: Value,
    span: Span,
    visitor: V,
) -> Result<V::Value, DeserializeError> {
    let mut entries = Vec::with_capacity(3);
    for (name, value) in [(fold.op, op), (fold.lhs, lhs), (fold.rhs, rhs)] {
        let at = value.span();
        entries.push((name, at.clone(), value, at));
    }
    visitor
        .visit_map(MapEntries::new(entries))
        .map_err(|error| error.positioned(span))
}

/// An externally tagged value as serde's enum access: the variant name, then its content.
struct TaggedEnum {
    name: &'static str,
    payload: Value,
}

impl<'de> EnumAccess<'de> for TaggedEnum {
    type Error = DeserializeError;
    type Variant = TaggedContent;

    fn variant_seed<S: DeserializeSeed<'de>>(self, seed: S) -> Result<(S::Value, Self::Variant), Self::Error> {
        let span = self.payload.span();
        let name: StrDeserializer<'de, Self::Error> = self.name.into_deserializer();
        let variant = seed.deserialize(name).map_err(|error| error.positioned(span.clone()))?;
        Ok((
            variant,
            TaggedContent {
                name: self.name,
                value: self.payload,
                span,
            },
        ))
    }
}

/// What one externally tagged variant carries, positioned where the content is.
struct TaggedContent {
    name: &'static str,
    value: Value,
    span: Span,
}

impl<'de> VariantAccess<'de> for TaggedContent {
    type Error = DeserializeError;

    /// A target declaring the variant as a unit one takes none of the content — but everything
    /// served this way carries some: a sum alternative has the labeled children it was selected
    /// by, and a fold's `Operand` / `Binary` have their operands. So the disagreement is
    /// reported rather than absorbed, which is what serde_json and toml do with the same target
    /// over `{"Variant": …}`; absorbing it would let a target that forgot a variant's fields
    /// succeed on every input while discarding what it parsed.
    fn unit_variant(self) -> Result<(), Self::Error> {
        Err(DeserializeError::new(
            format!(
                "variant {:?} carries content, found {}, expected a unit variant",
                self.name,
                self.value.describe()
            ),
            self.span,
        ))
    }

    fn newtype_variant_seed<S: DeserializeSeed<'de>>(self, seed: S) -> Result<S::Value, Self::Error> {
        let span = self.span;
        seed.deserialize(self.value).map_err(|error| error.positioned(span))
    }

    fn tuple_variant<V: Visitor<'de>>(self, _len: usize, _visitor: V) -> Result<V::Value, Self::Error> {
        Err(self.value.unsupported("tuple variants"))
    }

    fn struct_variant<V: Visitor<'de>>(
        self,
        _fields: &'static [&'static str],
        visitor: V,
    ) -> Result<V::Value, Self::Error> {
        let span = self.span;
        self.value
            .deserialize_map(visitor)
            .map_err(|error| error.positioned(span))
    }
}

/// Serve one product node as a map, positioning a missing-field error at the node itself.
///
/// `key_field` names the field to leave out, which is set only where the node is the value of
/// a keyed map entry and the field is the key it arrived under.
fn visit_product<'de, V: Visitor<'de>>(
    node: &Node,
    fields: &'static [Field],
    key_field: Option<&'static str>,
    visitor: V,
) -> Result<V::Value, DeserializeError> {
    let span = node.span();
    let map = product_entries(node, fields, key_field)?;
    visitor.visit_map(map).map_err(|error| error.positioned(span))
}

/// One entry per populated field of a product, in field order.
///
/// The children are bucketed once for the whole node rather than scanned once per field, and a
/// collection label arrives as a single sequence entry: serde's derive rejects a key it has
/// already seen, so a repeated label would fail against every struct target.
///
/// A hoisted field is not in that bucketing at all — its label belongs to a `flatten;` wrapper
/// and only coincidentally to this node — so it is read down its own path. Field order is the
/// model's either way, which is what keeps a hoisted field's entry where the model put it.
fn product_entries(
    node: &Node,
    fields: &'static [Field],
    key_field: Option<&'static str>,
) -> Result<MapEntries<&'static str>, DeserializeError> {
    let root = Rc::new(Walked::new(node.clone()));
    let mut buckets: Vec<Vec<Child>> = fields.iter().map(|_| Vec::new()).collect();
    for (label, child) in &root.children {
        let Some(label) = label else { continue };
        if let Some(index) = fields
            .iter()
            .position(|field| field.hoist.is_empty() && field.label == *label)
        {
            buckets[index].push(child.clone());
        }
    }
    let mut wrappers = Wrappers::default();
    let mut entries = Vec::with_capacity(fields.len());
    for (field, bucket) in fields.iter().zip(buckets) {
        if key_field == Some(field.name) {
            continue;
        }
        // Where an error about this field is reported, in both phases: its first child, or the
        // node holding it for a field with no children, which is where a missing one is missing
        // from.
        let (rule, bucket, span) = field_children(&root, &mut wrappers, field, bucket)?;
        if let Some(value) = field_value(rule, field, bucket, &span)? {
            entries.push((field.name, span.clone(), value, span));
        }
    }
    Ok(MapEntries::new(entries))
}

/// What one field's children add up to, or `None` where the field is not there at all.
///
/// `span` is where a refusal about the field is reported: its first child, or the node itself
/// where it has none.
fn field_value(
    rule: &'static str,
    field: &Field,
    bucket: Vec<Child>,
    span: &Span,
) -> Result<Option<Value>, DeserializeError> {
    let label = field.label;
    match field.container {
        Container::Presence => {
            // Through the shared helper rather than an emptiness test: more than one child
            // under a presence label is an arity error, not a `true`.
            // The written literal's own span rides along, so a `Spanned` over the flag is
            // positioned where the flag was written; an absent one is nowhere.
            let borrowed: Vec<&Child> = bucket.iter().collect();
            let flag = presence(&borrowed, rule, label, span)?;
            let at = bucket.first().map_or_else(Span::unknown, Child::span);
            Ok(Some(Value::Flag(flag, at)))
        }
        Container::Collection => Ok(Some(Value::Seq(
            bucket
                .into_iter()
                .map(|child| child_value(rule, label, child))
                .collect(),
        ))),
        Container::Map(key) => Ok(Some(Value::Keyed {
            key,
            items: bucket
                .into_iter()
                .map(|child| child_value(rule, label, child))
                .collect(),
        })),
        Container::Single | Container::Optional => {
            if bucket.is_empty() {
                return Ok(None);
            }
            if bucket.len() > 1 {
                // Reachable only from a hand-built or mutated CST; a parse puts the grammar's
                // own number of children under each label. The refusal is raised through the
                // arity helpers so its wording has one home.
                let children: Vec<&Child> = bucket.iter().collect();
                let refused = match field.container {
                    Container::Single => one(&children, rule, label, span).err(),
                    _ => optional(&children, rule, label, span).err(),
                };
                return Err(refused.expect("more than one child fails either arity").into());
            }
            let child = bucket.into_iter().next().expect("the bucket holds one child");
            Ok(Some(child_value(rule, label, child)))
        }
    }
}

/// One child as the position a value is deserialized from.
fn child_value(rule: &'static str, label: &'static str, child: Child) -> Value {
    match child {
        Child::Text(span) => Value::Text { span, rule, label },
        Child::Node(node) => Value::Node(node),
    }
}

/// Serve a keyed field as a map, one entry per distinct key.
fn visit_keyed<'de, V: Visitor<'de>>(key: Key, items: Vec<Value>, visitor: V) -> Result<V::Value, DeserializeError> {
    let span = covering(&items);
    let map = keyed_entries(key, items)?;
    visitor.visit_map(map).map_err(|error| error.positioned(span))
}

/// One key of a keyed field while its elements are being collected.
struct KeyedEntry {
    key: KeyValue,
    /// The first element carrying the key, which a duplicate is reported against.
    span: Span,
    elements: Vec<Value>,
}

/// One entry per distinct key of a keyed field, in the order the keys first occurred.
///
/// The entries are built up front rather than yielded as the elements are walked, because a
/// repeated key has to be answered before any of them is served: without `multi` it is a
/// redefinition and the whole map is refused, and with it the elements sharing a key are one
/// value. Leaving the answer to the target's map type is what this exists to avoid — a
/// container deserializing the entries itself would quietly keep the last of them.
///
/// What makes two elements one key is the sidecar's declared key type, not the target's: an
/// integer-typed key is its gated value, so `7` and `007` are one key, and a text-typed key is
/// its text, so they are two. Either way the verdict is the same for every target the region
/// is deserialized into.
fn keyed_entries(key: Key, items: Vec<Value>) -> Result<MapEntries<KeyValue>, DeserializeError> {
    let mut entries: Vec<KeyedEntry> = Vec::new();
    // The identity of each key to the entry holding it, so a region of many elements does not
    // rescan the keys before each of them.
    let mut index: HashMap<Identity, usize> = HashMap::new();
    for item in items {
        let Value::Node(node) = item else {
            return Err(item.unexpected("an element of a keyed collection"));
        };
        let key_value = element_key(&node, &key)?;
        let identity = key_value.identity();
        let rule = node.rule();
        let span = node.span();
        let element = Value::Element {
            node,
            key_field: key.name,
        };
        match index.get(&identity).copied() {
            Some(at) if key.multi => entries[at].elements.push(element),
            Some(at) => return Err(identity.duplicate(rule, &span, &entries[at].span).into()),
            None => {
                index.insert(identity, entries.len());
                entries.push(KeyedEntry {
                    key: key_value,
                    span,
                    elements: vec![element],
                });
            }
        }
    }
    let entries: Vec<Entry<KeyValue>> = entries
        .into_iter()
        .map(|entry| {
            let key_span = entry.key.span();
            let span = covering(&entry.elements);
            let value = if key.multi {
                Value::Seq(entry.elements)
            } else {
                entry
                    .elements
                    .into_iter()
                    .next()
                    .expect("an entry is created with its first element")
            };
            (entry.key, key_span, value, span)
        })
        .collect();
    Ok(MapEntries::new(entries))
}

/// The key one element carries, read from its key child under the declared key type.
fn element_key(node: &Node, key: &Key) -> Result<KeyValue, DeserializeError> {
    let child = required_child(node, key.label)?;
    let value = child_value(node.rule(), key.label, child);
    let (text, rule, span) = value.lexeme("a map key")?;
    KeyValue::read(key.kind, text, rule, span)
}

/// A field's values, in source order.
struct Elements {
    items: std::vec::IntoIter<Value>,
}

impl Elements {
    fn new(items: Vec<Value>) -> Self {
        Elements {
            items: items.into_iter(),
        }
    }
}

impl<'de> SeqAccess<'de> for Elements {
    type Error = DeserializeError;

    fn next_element_seed<T: DeserializeSeed<'de>>(&mut self, seed: T) -> Result<Option<T::Value>, Self::Error> {
        let Some(value) = self.items.next() else {
            return Ok(None);
        };
        let span = value.span();
        seed.deserialize(value)
            .map(Some)
            .map_err(|error| error.positioned(span))
    }

    fn size_hint(&self) -> Option<usize> {
        Some(self.items.len())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tree::{NodeShape, Shape};
    use crate::{Raw, Spanned};
    use fltk_cst_core::{Shared, SourceText};
    use serde::Deserialize;
    use std::cell::Cell;
    use std::collections::BTreeMap;
    use std::marker::PhantomData;

    thread_local! {
        /// How many times a mock node has been asked for its children.
        ///
        /// A real `labeled_children` allocates a fresh `Vec` every call, so this is what
        /// walking a tree costs per node. The test harness
        /// gives each test its own thread, so each test has its own count.
        static CHILD_READS: Cell<usize> = const { Cell::new(0) };
    }

    /// One rule of the miniature grammar the tests deserialize from, as a generated module
    /// would describe it: a node type, its shape, and the two accessors.
    macro_rules! mock_rule {
        ($node:ident, $shape:ident, $rule:literal, $form:expr) => {
            static $shape: Shape = Shape {
                rule: $rule,
                form: $form,
            };

            #[derive(Debug)]
            struct $node {
                span: Span,
                children: Vec<(Option<&'static str>, Child)>,
            }

            impl NodeShape for $node {
                fn shape() -> &'static Shape {
                    &$shape
                }

                fn node_span(&self) -> Span {
                    self.span.clone()
                }

                fn labeled_children(&self) -> Vec<(Option<&'static str>, Child)> {
                    CHILD_READS.with(|reads| reads.set(reads.get() + 1));
                    self.children.clone()
                }
            }
        };
    }

    // config := setting:setting* ;
    // setting := name:/[a-z]+/ , "=" , value:number , flag:"!"? , extra:/[a-z]+/? ;
    // number := /[0-9]+/ ;
    // quoted := '"' . inner:/[a-z]+/ . '"' ;
    mock_rule!(
        Config,
        CONFIG,
        "config",
        Form::Product {
            fields: &[Field {
                name: "settings",
                label: "setting",
                container: Container::Collection,
                hoist: &[],
            }],
        }
    );
    mock_rule!(
        Setting,
        SETTING,
        "setting",
        Form::Product {
            fields: &[
                Field {
                    name: "name",
                    label: "name",
                    container: Container::Single,
                    hoist: &[],
                },
                Field {
                    name: "value",
                    label: "value",
                    container: Container::Single,
                    hoist: &[],
                },
                Field {
                    name: "flag",
                    label: "flag",
                    container: Container::Presence,
                    hoist: &[],
                },
                Field {
                    name: "extra",
                    label: "extra",
                    container: Container::Optional,
                    hoist: &[],
                },
            ],
        }
    );
    mock_rule!(Number, NUMBER, "number", Form::Terminal { text_from: None });
    mock_rule!(
        Quoted,
        QUOTED,
        "quoted",
        Form::Terminal {
            text_from: Some("inner"),
        }
    );

    /// The four keyed twins of `config`, over the same `setting` element: the two `key: name;`
    /// spellings and the two `key: name;` + `type: u16;` ones. The declared key type is what
    /// makes two elements duplicates, so the same source under a text key and under an integer
    /// key is the fixture the identity rule is read off.
    macro_rules! keyed_rule {
        ($node:ident, $shape:ident, $rule:literal, $kind:expr, $multi:literal) => {
            mock_rule!(
                $node,
                $shape,
                $rule,
                Form::Product {
                    fields: &[Field {
                        name: "settings",
                        label: "setting",
                        container: Container::Map(Key {
                            name: "name",
                            label: "name",
                            kind: $kind,
                            multi: $multi,
                        }),
                        hoist: &[],
                    }],
                }
            );
        };
    }

    keyed_rule!(KeyedConfig, KEYED_CONFIG, "keyed_config", KeyKind::Text, false);
    keyed_rule!(MultiConfig, MULTI_CONFIG, "multi_config", KeyKind::Text, true);
    keyed_rule!(NumConfig, NUM_CONFIG, "num_config", KeyKind::U16, false);
    keyed_rule!(NumMultiConfig, NUM_MULTI_CONFIG, "num_multi_config", KeyKind::U16, true);

    // mode := fast:"fast" | slow:"slow" ;
    mock_rule!(
        Mode,
        MODE,
        "mode",
        Form::Enum {
            variants: &[
                Variant {
                    name: "Fast",
                    label: "fast",
                },
                Variant {
                    name: "Slow",
                    label: "slow",
                },
            ],
            truthy: None,
        }
    );
    // toggle := on:"on" | off:"off" ;   with `bool: on;`
    mock_rule!(
        Toggle,
        TOGGLE,
        "toggle",
        Form::Enum {
            variants: &[
                Variant {
                    name: "On",
                    label: "on",
                },
                Variant {
                    name: "Off",
                    label: "off",
                },
            ],
            truthy: Some("on"),
        }
    );

    // wrapped := '(' . inner:number . ')' ;    with `transparent;`
    // held := inner:wrapped ;                  with `transparent;`
    // listing: a transparent form over a collection field. No sidecar spells this — erasure is
    // admitted only over a single required field — so it is a runtime-only shape, here because
    // the runtime serves what a description says and not what an emitter happens to write.
    mock_rule!(
        Wrapped,
        WRAPPED,
        "wrapped",
        Form::Transparent {
            field: Field {
                name: "inner",
                label: "inner",
                container: Container::Single,
                hoist: &[],
            },
        }
    );
    mock_rule!(
        Held,
        HELD,
        "held",
        Form::Transparent {
            field: Field {
                name: "inner",
                label: "inner",
                container: Container::Single,
                hoist: &[],
            },
        }
    );
    mock_rule!(
        Listing,
        LISTING,
        "listing",
        Form::Transparent {
            field: Field {
                name: "items",
                label: "item",
                container: Container::Collection,
                hoist: &[],
            },
        }
    );

    // entry := key:/[a-z]+/ . '=' . value:number | bare:number ;
    //
    // The first alternative names two labels, so it has no single child to be its payload and
    // the model generates a product for it; the second names one and carries that child.
    static ENTRY_TABLE: dispatch::Table = dispatch::Table {
        pairs: &[
            dispatch::Pair {
                label: "key",
                kind: dispatch::TEXT_KIND,
            },
            dispatch::Pair {
                label: "value",
                kind: "number",
            },
            dispatch::Pair {
                label: "bare",
                kind: "number",
            },
        ],
        alternatives: &[
            dispatch::Alt {
                variant: 0,
                bounds: &[
                    dispatch::Bound {
                        label: "key",
                        pairs: &[0],
                        minimum: 1,
                        maximum: 1,
                    },
                    dispatch::Bound {
                        label: "value",
                        pairs: &[1],
                        minimum: 1,
                        maximum: 1,
                    },
                ],
                forbidden: &[2],
            },
            dispatch::Alt {
                variant: 1,
                bounds: &[dispatch::Bound {
                    label: "bare",
                    pairs: &[2],
                    minimum: 1,
                    maximum: 1,
                }],
                forbidden: &[0, 1],
            },
        ],
    };

    static ENTRY_ALTERNATIVES: [Alternative; 2] = [
        Alternative {
            name: "Pair",
            payload: Content::Fields {
                fields: &[
                    Field {
                        name: "key",
                        label: "key",
                        container: Container::Single,
                        hoist: &[],
                    },
                    Field {
                        name: "value",
                        label: "value",
                        container: Container::Single,
                        hoist: &[],
                    },
                ],
            },
        },
        Alternative {
            name: "Bare",
            payload: Content::Child { label: "bare" },
        },
    ];

    mock_rule!(
        Entry,
        ENTRY,
        "entry",
        Form::Sum {
            table: &ENTRY_TABLE,
            alternatives: &ENTRY_ALTERNATIVES,
        }
    );

    // chain := operand:number , (op:'+' , operand:number)* ;   under each fold direction.
    static LEFT_FOLD: Fold = Fold {
        direction: Direction::Left,
        operand_label: "operand",
        operator_label: "op",
        operand_variant: "Operand",
        binary_variant: "Binary",
        op: "operator",
        lhs: "lhs",
        rhs: "rhs",
    };
    static RIGHT_FOLD: Fold = Fold {
        direction: Direction::Right,
        operand_label: "operand",
        operator_label: "op",
        operand_variant: "Operand",
        binary_variant: "Binary",
        op: "operator",
        lhs: "lhs",
        rhs: "rhs",
    };

    mock_rule!(LeftChain, LEFT_CHAIN, "chain", Form::Fold(&LEFT_FOLD));
    mock_rule!(RightChain, RIGHT_CHAIN, "chain", Form::Fold(&RIGHT_FOLD));

    // tuned  := title:/[a-z]+/ , w:limits? ;
    // limits := '[' . cap:number , ':' , deep:extras . ']' ;   with `flatten;`
    // extras := depth:number? , tag:/[a-z]+/* , mark:'~'? ;    with `flatten;`
    //
    // `tuned` holds `cap` one wrapper down and `depth`/`tag`/`mark` two, so its field table is
    // the transitive hoist the model publishes as a path. The outer step is optional, which is
    // what degrades `cap` from a single field to an optional one.
    static OUTER_STEP: Wrapper = Wrapper {
        label: "w",
        optional: true,
    };
    static INNER_STEP: Wrapper = Wrapper {
        label: "deep",
        optional: false,
    };

    mock_rule!(
        Tuned,
        TUNED,
        "tuned",
        Form::Product {
            fields: &[
                Field {
                    name: "title",
                    label: "title",
                    container: Container::Single,
                    hoist: &[],
                },
                Field {
                    name: "cap",
                    label: "cap",
                    container: Container::Optional,
                    hoist: &[OUTER_STEP],
                },
                Field {
                    name: "depth",
                    label: "depth",
                    container: Container::Optional,
                    hoist: &[OUTER_STEP, INNER_STEP],
                },
                Field {
                    name: "tags",
                    label: "tag",
                    container: Container::Collection,
                    hoist: &[OUTER_STEP, INNER_STEP],
                },
                Field {
                    name: "mark",
                    label: "mark",
                    container: Container::Presence,
                    hoist: &[OUTER_STEP, INNER_STEP],
                },
            ],
        }
    );
    mock_rule!(
        Limits,
        LIMITS,
        "limits",
        Form::Product {
            fields: &[
                Field {
                    name: "cap",
                    label: "cap",
                    container: Container::Single,
                    hoist: &[],
                },
                Field {
                    name: "depth",
                    label: "depth",
                    container: Container::Optional,
                    hoist: &[INNER_STEP],
                },
                Field {
                    name: "tags",
                    label: "tag",
                    container: Container::Collection,
                    hoist: &[INNER_STEP],
                },
                Field {
                    name: "mark",
                    label: "mark",
                    container: Container::Presence,
                    hoist: &[INNER_STEP],
                },
            ],
        }
    );
    mock_rule!(
        Extras,
        EXTRAS,
        "extras",
        Form::Product {
            fields: &[
                Field {
                    name: "depth",
                    label: "depth",
                    container: Container::Optional,
                    hoist: &[],
                },
                Field {
                    name: "tags",
                    label: "tag",
                    container: Container::Collection,
                    hoist: &[],
                },
                Field {
                    name: "mark",
                    label: "mark",
                    container: Container::Presence,
                    hoist: &[],
                },
            ],
        }
    );

    // mixed := item:(number | setting)* ;
    //
    // One label carrying two rules, which the model types as a field enum: nothing about the
    // field says which rule a child is, so each is served as whatever its own shape is.
    mock_rule!(
        Mixed,
        MIXED,
        "mixed",
        Form::Product {
            fields: &[Field {
                name: "items",
                label: "item",
                container: Container::Collection,
                hoist: &[],
            }],
        }
    );

    fn node<T: NodeShape>(value: T) -> Node {
        Node::new(Shared::new(value))
    }

    /// An unlabeled child, which is what a real CST is mostly made of: trivia and
    /// `$`-included literals reach `labeled_children` with no label. Every mock node carries
    /// some, because the Deserializer's whole business with them is to skip them — a mock
    /// whose children are all labeled cannot witness that.
    fn trivia(source: &SourceText) -> (Option<&'static str>, Child) {
        (None, Child::Text(Span::new_with_source(0, 1, source)))
    }

    /// The whole of one source, as the span of a root node over it.
    fn whole(source: &SourceText) -> Span {
        Span::new_with_source(0, source.text().chars().count() as i64, source)
    }

    const SOURCE_TEXT: &str = "host = 1 !\nport = 99999\n";

    fn source() -> SourceText {
        SourceText::from_str(SOURCE_TEXT, None)
    }

    /// The span of one slice of the fixture text; every needle the tests use occurs once.
    fn span(source: &SourceText, needle: &str) -> Span {
        let start = source.text().find(needle).expect("the fixture text contains it");
        Span::new_with_source(start as i64, (start + needle.len()) as i64, source)
    }

    fn number(source: &SourceText, text: &str) -> Child {
        Child::Node(node(Number {
            span: span(source, text),
            children: Vec::new(),
        }))
    }

    fn setting(source: &SourceText, whole: &str, name: &str, value: &str, flag: bool) -> Child {
        let mut children = vec![
            trivia(source),
            (Some("name"), Child::Text(span(source, name))),
            trivia(source),
            (Some("value"), number(source, value)),
        ];
        if flag {
            children.push((Some("flag"), Child::Text(span(source, "!"))));
        }
        children.push(trivia(source));
        Child::Node(node(Setting {
            span: span(source, whole),
            children,
        }))
    }

    fn config(source: &SourceText, settings: Vec<Child>) -> Node {
        let mut children = vec![trivia(source)];
        for child in settings {
            children.push((Some("setting"), child));
            children.push(trivia(source));
        }
        node(Config {
            span: Span::new_with_source(0, SOURCE_TEXT.chars().count() as i64, source),
            children,
        })
    }

    fn host(source: &SourceText) -> Node {
        let Child::Node(node) = setting(source, "host = 1 !", "host", "1", true) else {
            unreachable!("the builder returns a node child")
        };
        node
    }

    /// A `number` node over its own source, for a target reading a scalar off a lexeme.
    fn lexeme_node(text: &str) -> (SourceText, Node) {
        let source = SourceText::from_str(text, None);
        let held = node(Number {
            span: whole(&source),
            children: Vec::new(),
        });
        (source, held)
    }

    /// A `setting` node whose only labeled child is a `value` carrying `text`, over its own
    /// source: the position a target reads a value from, with a span to report against.
    fn valued(text: &str) -> (SourceText, Node) {
        let source = SourceText::from_str(text, None);
        let span = whole(&source);
        let held = node(Setting {
            span: span.clone(),
            children: vec![
                trivia(&source),
                (
                    Some("value"),
                    Child::Node(node(Number {
                        span,
                        children: Vec::new(),
                    })),
                ),
            ],
        });
        (source, held)
    }

    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct SettingTarget {
        name: String,
        value: u16,
        flag: bool,
        extra: Option<String>,
    }

    #[derive(Debug, Deserialize, PartialEq)]
    struct ConfigTarget {
        settings: Vec<SettingTarget>,
    }

    #[test]
    fn a_product_serves_one_entry_per_field() {
        let source = source();
        let target: SettingTarget = from_node(host(&source)).unwrap();
        assert_eq!(
            target,
            SettingTarget {
                name: "host".to_string(),
                value: 1,
                flag: true,
                extra: None,
            }
        );
    }

    #[test]
    fn unlabeled_children_are_no_part_of_any_field() {
        let source = source();
        let only_trivia = node(Config {
            span: whole(&source),
            children: vec![trivia(&source), trivia(&source)],
        });
        let served: serde_json::Value = from_node(only_trivia).unwrap();
        assert_eq!(served, serde_json::json!({"settings": []}));
    }

    #[test]
    fn a_collection_is_always_present_and_keeps_source_order() {
        let source = source();
        let empty: ConfigTarget = from_node(config(&source, Vec::new())).unwrap();
        assert!(empty.settings.is_empty());

        let both = vec![
            setting(&source, "host = 1 !", "host", "1", true),
            setting(&source, "port = 99999", "port", "9999", false),
        ];
        let target: ConfigTarget = from_node(config(&source, both)).unwrap();
        let names: Vec<&str> = target.settings.iter().map(|entry| entry.name.as_str()).collect();
        assert_eq!(names, ["host", "port"]);
        assert!(target.settings[0].flag);
        assert!(!target.settings[1].flag);
    }

    #[test]
    fn an_optional_field_arrives_when_its_child_does() {
        let source = source();
        let with_extra = node(Setting {
            span: span(&source, "host = 1 !"),
            children: vec![
                (Some("name"), Child::Text(span(&source, "host"))),
                trivia(&source),
                (Some("value"), number(&source, "1")),
                (Some("extra"), Child::Text(span(&source, "port"))),
            ],
        });
        let target: SettingTarget = from_node(with_extra).unwrap();
        assert_eq!(target.extra.as_deref(), Some("port"));
        assert!(!target.flag);
    }

    #[test]
    fn an_unknown_field_is_positioned_at_the_offending_child() {
        #[derive(Debug, Deserialize)]
        #[serde(deny_unknown_fields)]
        struct NoFlag {
            #[allow(dead_code)]
            name: String,
            #[allow(dead_code)]
            value: u16,
        }
        let source = source();
        let error = from_node::<NoFlag>(host(&source)).unwrap_err();
        assert!(error.message.contains("unknown field"), "{}", error.message);
        // The `!` the target has no field for, not the node it sits in.
        assert_eq!(error.span, span(&source, "!"));
        assert!(error.to_string().ends_with("at line 1, column 10"), "{error}");
    }

    #[test]
    fn a_missing_field_is_positioned_at_the_node() {
        #[derive(Debug, Deserialize)]
        struct NeedsExtra {
            #[allow(dead_code)]
            extra: String,
        }
        let source = source();
        let error = from_node::<NeedsExtra>(host(&source)).unwrap_err();
        assert!(error.message.contains("missing field"), "{}", error.message);
        assert_eq!(error.span, span(&source, "host = 1 !"));
    }

    #[test]
    fn more_children_than_a_field_takes_is_the_shared_arity_refusal() {
        let source = source();
        let twice_named = node(Setting {
            span: span(&source, "host = 1 !"),
            children: vec![
                (Some("name"), Child::Text(span(&source, "host"))),
                (Some("name"), Child::Text(span(&source, "port"))),
                (Some("value"), number(&source, "1")),
            ],
        });
        let error = from_node::<SettingTarget>(twice_named).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"setting\": expected exactly one \"name\" child, found 2"
        );
        assert_eq!(error.span, span(&source, "host"));

        let twice_extra = node(Setting {
            span: span(&source, "host = 1 !"),
            children: vec![
                (Some("name"), Child::Text(span(&source, "host"))),
                (Some("value"), number(&source, "1")),
                (Some("extra"), Child::Text(span(&source, "port"))),
                (Some("extra"), Child::Text(span(&source, "host"))),
            ],
        });
        let error = from_node::<SettingTarget>(twice_extra).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"setting\": expected at most one \"extra\" child, found 2"
        );
        assert_eq!(error.span, span(&source, "port"));

        let twice_flagged = node(Setting {
            span: span(&source, "host = 1 !"),
            children: vec![
                (Some("name"), Child::Text(span(&source, "host"))),
                (Some("value"), number(&source, "1")),
                (Some("flag"), Child::Text(span(&source, "!"))),
                (Some("flag"), Child::Text(span(&source, "!"))),
            ],
        });
        let error = from_node::<SettingTarget>(twice_flagged).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"setting\": expected at most one \"flag\" child, found 2"
        );
        assert_eq!(error.span, span(&source, "!"));
    }

    #[test]
    fn a_scalar_runs_the_gate_of_the_width_the_target_names() {
        let source = source();
        let Child::Node(node) = setting(&source, "port = 99999", "port", "99999", false) else {
            unreachable!("the builder returns a node child")
        };
        let error = from_node::<SettingTarget>(node).unwrap_err();
        assert!(error.message.contains("in range for u16"), "{}", error.message);
        // The value child, not the setting it belongs to.
        assert_eq!(error.span, span(&source, "99999"));

        #[derive(Debug, Deserialize)]
        struct Wide {
            value: u32,
        }
        let wide: Wide = from_node(host(&source)).unwrap();
        assert_eq!(wide.value, 1);
    }

    /// Every `deserialize_<scalar>` method against the gate it is supposed to run.
    ///
    /// The methods are a macro table of `(method, visit, parse)` triples, and a mismatched
    /// triple compiles: an `i8` field wired to `parse_i16` would accept `200`. Reading each
    /// width's own boundary out of the message is what pins the correspondence.
    #[test]
    fn every_scalar_width_runs_its_own_gate() {
        macro_rules! integer_width {
            ($ty:ty, $width:literal, $over:literal) => {{
                let at_max = <$ty>::MAX.to_string();
                let (_source, held) = lexeme_node(&at_max);
                assert_eq!(from_node::<$ty>(held).unwrap(), <$ty>::MAX);

                let (_source, held) = lexeme_node($over);
                let error = from_node::<$ty>(held).unwrap_err();
                assert_eq!(
                    error.message,
                    format!(
                        "rule \"number\": {:?} is not in range for {} ({} to {})",
                        $over,
                        $width,
                        <$ty>::MIN,
                        <$ty>::MAX
                    )
                );
            }};
        }

        integer_width!(i8, "i8", "128");
        integer_width!(i16, "i16", "32768");
        integer_width!(i32, "i32", "2147483648");
        integer_width!(i64, "i64", "9223372036854775808");
        integer_width!(u8, "u8", "256");
        integer_width!(u16, "u16", "65536");
        integer_width!(u32, "u32", "4294967296");
        integer_width!(u64, "u64", "18446744073709551616");

        macro_rules! float_width {
            ($ty:ty, $width:literal, $over:literal) => {{
                let at_max = <$ty>::MAX.to_string();
                let (_source, held) = lexeme_node(&at_max);
                assert_eq!(from_node::<$ty>(held).unwrap(), <$ty>::MAX);

                let (_source, held) = lexeme_node($over);
                let error = from_node::<$ty>(held).unwrap_err();
                assert_eq!(
                    error.message,
                    format!("rule \"number\": {:?} is not in range for {}", $over, $width)
                );
            }};
        }

        float_width!(f32, "f32", "1e39");
        float_width!(f64, "f64", "1e400");
    }

    #[test]
    fn a_char_target_takes_a_one_character_lexeme_and_nothing_else() {
        let (_source, held) = lexeme_node("x");
        assert_eq!(from_node::<char>(held).unwrap(), 'x');

        // Characters, not bytes: a two-byte lexeme is still one character.
        let (_source, held) = lexeme_node("é");
        assert_eq!(from_node::<char>(held).unwrap(), 'é');

        let (source, held) = lexeme_node("host");
        let error = from_node::<char>(held).unwrap_err();
        assert_eq!(error.message, "rule \"number\": \"host\" is not a single character");
        assert_eq!(error.span, whole(&source));

        let (_source, held) = lexeme_node("");
        assert!(from_node::<char>(held).is_err());
    }

    #[test]
    fn text_from_reads_the_named_child_rather_than_the_node_span() {
        let quoted_source = SourceText::from_str("\"abc\"", None);
        let quoted = node(Quoted {
            span: Span::new_with_source(0, 5, &quoted_source),
            children: vec![
                trivia(&quoted_source),
                (Some("inner"), Child::Text(Span::new_with_source(1, 4, &quoted_source))),
                trivia(&quoted_source),
            ],
        });
        let text: String = from_node(quoted).unwrap();
        assert_eq!(text, "abc");
    }

    #[test]
    fn a_text_from_rule_needs_exactly_one_child_to_read_from() {
        let quoted_source = SourceText::from_str("\"abc\"", None);
        let missing = node(Quoted {
            span: Span::new_with_source(0, 5, &quoted_source),
            children: vec![trivia(&quoted_source)],
        });
        let error = from_node::<String>(missing).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"quoted\": expected exactly one \"inner\" child, found 0"
        );
        assert_eq!(error.span, Span::new_with_source(0, 5, &quoted_source));

        let doubled = node(Quoted {
            span: Span::new_with_source(0, 5, &quoted_source),
            children: vec![
                (Some("inner"), Child::Text(Span::new_with_source(1, 2, &quoted_source))),
                (Some("inner"), Child::Text(Span::new_with_source(2, 4, &quoted_source))),
            ],
        });
        let error = from_node::<String>(doubled).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"quoted\": expected exactly one \"inner\" child, found 2"
        );
    }

    #[test]
    fn a_boolean_target_is_served_by_a_presence_field_only() {
        let source = source();
        #[derive(Debug, Deserialize)]
        struct NameAsBool {
            #[allow(dead_code)]
            name: bool,
        }
        let error = from_node::<NameAsBool>(host(&source)).unwrap_err();
        assert_eq!(error.message, "expected a boolean, found a string");
        assert_eq!(error.span, span(&source, "host"));
    }

    #[test]
    fn an_unsupported_target_shape_says_so() {
        let source = source();
        #[derive(Debug, Deserialize)]
        struct Tupled {
            #[allow(dead_code)]
            value: (u8, u8),
        }
        let error = from_node::<Tupled>(host(&source)).unwrap_err();
        assert_eq!(
            error.message,
            "tuple targets are not supported by the FLTK serde frontend"
        );
    }

    /// A visitor nothing reaches: each refusal under test is raised before any `visit_`.
    struct Never;

    impl<'de> Visitor<'de> for Never {
        type Value = ();

        fn expecting(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            f.write_str("nothing")
        }
    }

    #[test]
    fn each_unsupported_shape_has_its_own_wording() {
        let source = source();
        let at = || Value::Node(host(&source));
        let cases = [
            (at().deserialize_bytes(Never), "byte targets"),
            (at().deserialize_byte_buf(Never), "byte targets"),
            (at().deserialize_tuple(2, Never), "tuple targets"),
            (at().deserialize_tuple_struct("Pair", 2, Never), "tuple-struct targets"),
        ];
        for (result, what) in cases {
            let error = result.unwrap_err();
            assert_eq!(
                error.message,
                format!("{what} are not supported by the FLTK serde frontend")
            );
        }
    }

    #[test]
    fn an_ignored_field_is_never_walked() {
        // A `value` child that would fail if served: an enum-shaped node no alternative
        // matched. A target with no field for it must not care.
        let source = SourceText::from_str("host", None);
        let broken = node(Setting {
            span: whole(&source),
            children: vec![
                (Some("name"), Child::Text(whole(&source))),
                (
                    Some("value"),
                    Child::Node(node(Mode {
                        span: whole(&source),
                        children: Vec::new(),
                    })),
                ),
            ],
        });

        #[derive(Debug, Deserialize)]
        struct OnlyName {
            name: String,
        }
        let target: OnlyName = from_node(broken).unwrap();
        assert_eq!(target.name, "host");
    }

    #[test]
    fn spanned_positions_a_field_and_merges_a_collection() {
        let source = source();
        #[derive(Debug, Deserialize)]
        struct Positioned {
            name: Spanned<String>,
        }
        let target: Positioned = from_node(host(&source)).unwrap();
        assert_eq!(*target.name, "host");
        assert_eq!(*target.name.span(), span(&source, "host"));

        #[derive(Debug, Deserialize)]
        struct PositionedAll {
            settings: Spanned<Vec<SettingTarget>>,
        }
        let both = vec![
            setting(&source, "host = 1 !", "host", "1", true),
            setting(&source, "port = 99999", "port", "9999", false),
        ];
        let whole: PositionedAll = from_node(config(&source, both)).unwrap();
        assert_eq!(whole.settings.span().start(), 0);
        assert_eq!(whole.settings.span().end(), span(&source, "port = 99999").end());

        let empty: PositionedAll = from_node(config(&source, Vec::new())).unwrap();
        assert_eq!(*empty.settings.span(), Span::unknown());
        assert_eq!(channel::take_span(), None);
    }

    #[test]
    fn a_presence_flag_is_positioned_where_it_was_written() {
        #[derive(Debug, Deserialize)]
        struct Flagged {
            flag: Spanned<bool>,
        }
        let source = source();
        let written: Flagged = from_node(host(&source)).unwrap();
        assert!(*written.flag);
        assert_eq!(*written.flag.span(), span(&source, "!"));

        // An absent flag has no source location of its own, and says so rather than
        // borrowing the node's.
        let Child::Node(unflagged) = setting(&source, "port = 99999", "port", "9999", false) else {
            unreachable!("the builder returns a node child")
        };
        let absent: Flagged = from_node(unflagged).unwrap();
        assert!(!*absent.flag);
        assert_eq!(*absent.flag.span(), Span::unknown());
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn raw_holds_the_node_at_the_position() {
        let source = source();
        #[derive(Debug, Deserialize)]
        struct Held {
            value: Raw<Number>,
        }
        let target: Held = from_node(host(&source)).unwrap();
        assert_eq!(target.value.node().read().span, span(&source, "1"));

        // A `Raw` of the wrong rule's node type names both ends of the mismatch.
        #[derive(Debug, Deserialize)]
        struct Mismatched {
            #[allow(dead_code)]
            value: Raw<Quoted>,
        }
        let error = from_node::<Mismatched>(host(&source)).unwrap_err();
        assert!(error.message.contains("found rule `number`"), "{}", error.message);
    }

    #[test]
    fn raw_at_a_position_that_is_not_a_node_says_so() {
        let source = source();
        #[derive(Debug, Deserialize)]
        struct RawName {
            #[allow(dead_code)]
            name: Raw<Number>,
        }
        let error = from_node::<RawName>(host(&source)).unwrap_err();
        assert_eq!(error.message, "expected a node to hold as `Raw`, found a string");
        assert_eq!(error.span, span(&source, "host"));
        assert_eq!(channel::depth(), 0);

        #[derive(Debug, Deserialize)]
        struct RawCollection {
            #[allow(dead_code)]
            settings: Raw<Setting>,
        }
        let both = vec![setting(&source, "host = 1 !", "host", "1", true)];
        let error = from_node::<RawCollection>(config(&source, both)).unwrap_err();
        assert_eq!(error.message, "expected a node to hold as `Raw`, found a sequence");
    }

    #[test]
    fn an_ordinary_newtype_target_is_transparent() {
        #[derive(Debug, Deserialize, PartialEq)]
        struct Port(u16);

        #[derive(Debug, Deserialize)]
        struct Wrapped {
            value: Port,
        }
        let source = source();
        let target: Wrapped = from_node(host(&source)).unwrap();
        assert_eq!(target.value, Port(1));
    }

    #[test]
    fn a_spanned_raw_takes_both_payloads_in_order() {
        let source = source();
        #[derive(Debug, Deserialize)]
        struct Nested {
            value: Spanned<Raw<Number>>,
        }
        let target: Nested = from_node(host(&source)).unwrap();
        assert_eq!(*target.value.span(), span(&source, "1"));
        assert_eq!(target.value.node().read().span, span(&source, "1"));
        assert_eq!(channel::depth(), 0);
    }

    /// A keyed region as `key = value` lines, over a source text built to match.
    ///
    /// The key spellings are the fixture's variable: the same lines read under a text-typed
    /// key and under an integer-typed one are what the identity rule is read off.
    struct Lines {
        source: SourceText,
        children: Vec<(Option<&'static str>, Child)>,
        /// Each element's key child, in source order.
        keys: Vec<Span>,
        /// Each element node, in source order.
        elements: Vec<Span>,
    }

    fn lines(entries: &[(&str, &str)]) -> Lines {
        let mut text = String::new();
        let mut cuts = Vec::new();
        for (key, value) in entries {
            let start = text.chars().count() as i64;
            text.push_str(key);
            let key_end = text.chars().count() as i64;
            text.push_str(" = ");
            let value_start = text.chars().count() as i64;
            text.push_str(value);
            let end = text.chars().count() as i64;
            text.push('\n');
            cuts.push((start, key_end, value_start, end));
        }
        let source = SourceText::from_str(&text, None);
        let mut children = vec![trivia(&source)];
        let mut keys = Vec::new();
        let mut elements = Vec::new();
        for (start, key_end, value_start, end) in cuts {
            let key = Span::new_with_source(start, key_end, &source);
            let element = Span::new_with_source(start, end, &source);
            children.push((
                Some("setting"),
                Child::Node(node(Setting {
                    span: element.clone(),
                    children: vec![
                        (Some("name"), Child::Text(key.clone())),
                        trivia(&source),
                        (
                            Some("value"),
                            Child::Node(node(Number {
                                span: Span::new_with_source(value_start, end, &source),
                                children: Vec::new(),
                            })),
                        ),
                    ],
                })),
            ));
            children.push(trivia(&source));
            keys.push(key);
            elements.push(element);
        }
        Lines {
            source,
            children,
            keys,
            elements,
        }
    }

    impl Lines {
        fn text_keyed(&self) -> Node {
            node(KeyedConfig {
                span: whole(&self.source),
                children: self.children.clone(),
            })
        }

        fn text_multi(&self) -> Node {
            node(MultiConfig {
                span: whole(&self.source),
                children: self.children.clone(),
            })
        }

        fn int_keyed(&self) -> Node {
            node(NumConfig {
                span: whole(&self.source),
                children: self.children.clone(),
            })
        }

        fn int_multi(&self) -> Node {
            node(NumMultiConfig {
                span: whole(&self.source),
                children: self.children.clone(),
            })
        }
    }

    /// A map target that keeps the order its entries were served in, which a `HashMap` would
    /// lose and an `IndexMap` would cost a dependency to keep.
    #[derive(Debug, PartialEq)]
    struct Ordered<K, V>(Vec<(K, V)>);

    struct OrderedVisitor<K, V>(PhantomData<fn() -> (K, V)>);

    impl<'de, K: Deserialize<'de>, V: Deserialize<'de>> Visitor<'de> for OrderedVisitor<K, V> {
        type Value = Ordered<K, V>;

        fn expecting(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            f.write_str("a map")
        }

        fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Self::Value, A::Error> {
            let mut entries = Vec::new();
            while let Some(entry) = map.next_entry::<K, V>()? {
                entries.push(entry);
            }
            Ok(Ordered(entries))
        }
    }

    impl<'de, K: Deserialize<'de>, V: Deserialize<'de>> Deserialize<'de> for Ordered<K, V> {
        fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
            deserializer.deserialize_map(OrderedVisitor(PhantomData))
        }
    }

    /// The same map, asked for as the self-describing shape rather than as a map: what
    /// `deserialize_any` decides for a keyed region is what this sees.
    #[derive(Debug, PartialEq)]
    struct SelfDescribed<K, V>(Vec<(K, V)>);

    impl<'de, K: Deserialize<'de>, V: Deserialize<'de>> Deserialize<'de> for SelfDescribed<K, V> {
        fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
            deserializer
                .deserialize_any(OrderedVisitor(PhantomData))
                .map(|ordered| SelfDescribed(ordered.0))
        }
    }

    /// The map form's value: no `name` field, so `deny_unknown_fields` fails unless the key
    /// field really is left out.
    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct Keyless {
        value: u16,
        flag: bool,
    }

    /// The sequence form's element, where the key is a field like any other.
    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct Keyful {
        name: String,
        value: u16,
        flag: bool,
    }

    fn keyless(value: u16) -> Keyless {
        Keyless { value, flag: false }
    }

    #[test]
    fn a_keyed_region_is_a_map_whose_values_leave_the_key_out() {
        #[derive(Debug, Deserialize)]
        struct Target {
            settings: Ordered<String, Keyless>,
        }
        let fixture = lines(&[("a", "1"), ("b", "2")]);
        let target: Target = from_node(fixture.text_keyed()).unwrap();
        assert_eq!(
            target.settings.0,
            vec![("a".to_string(), keyless(1)), ("b".to_string(), keyless(2))]
        );
    }

    #[test]
    fn a_keyed_region_is_a_sequence_when_the_target_is_one() {
        #[derive(Debug, Deserialize)]
        struct Target {
            settings: Vec<Keyful>,
        }
        let fixture = lines(&[("b", "2"), ("a", "1")]);
        let target: Target = from_node(fixture.text_keyed()).unwrap();
        let names: Vec<&str> = target.settings.iter().map(|entry| entry.name.as_str()).collect();
        assert_eq!(names, ["b", "a"]);
        assert_eq!(target.settings[0].value, 2);
    }

    #[test]
    fn a_duplicate_key_is_refused_where_the_second_element_is() {
        #[derive(Debug, Deserialize)]
        struct Target {
            #[allow(dead_code)]
            settings: Ordered<String, Keyless>,
        }
        let fixture = lines(&[("a", "1"), ("b", "2"), ("a", "3")]);
        let error = from_node::<Target>(fixture.text_keyed()).unwrap_err();
        assert_eq!(error.message, "duplicate setting key \"a\"");
        assert_eq!(error.span, fixture.elements[2]);
        assert_eq!(error.related.len(), 1);
        assert_eq!(error.related[0].0, "previously defined here");
        assert_eq!(error.related[0].1, fixture.elements[0]);
    }

    #[test]
    fn multi_groups_the_elements_sharing_a_key_under_the_first_of_them() {
        #[derive(Debug, Deserialize)]
        struct Target {
            settings: Ordered<String, Vec<Keyless>>,
        }
        let fixture = lines(&[("a", "1"), ("b", "2"), ("a", "3")]);
        let target: Target = from_node(fixture.text_multi()).unwrap();
        assert_eq!(
            target.settings.0,
            vec![
                ("a".to_string(), vec![keyless(1), keyless(3)]),
                ("b".to_string(), vec![keyless(2)]),
            ]
        );

        // The sequence form is the plain elements either way: grouping is the map form's.
        #[derive(Debug, Deserialize)]
        struct AsSeq {
            settings: Vec<Keyful>,
        }
        let flat: AsSeq = from_node(fixture.text_multi()).unwrap();
        assert_eq!(flat.settings.len(), 3);
    }

    #[test]
    fn a_self_describing_target_gets_the_map_form() {
        let fixture = lines(&[("a", "1"), ("b", "2")]);
        let value: serde_json::Value = from_node(fixture.text_keyed()).unwrap();
        assert_eq!(
            value,
            serde_json::json!({
                "settings": {
                    "a": {"value": "1", "flag": false},
                    "b": {"value": "2", "flag": false},
                }
            })
        );

        let grouped = lines(&[("a", "1"), ("a", "3")]);
        let value: serde_json::Value = from_node(grouped.text_multi()).unwrap();
        assert_eq!(
            value,
            serde_json::json!({
                "settings": {
                    "a": [{"value": "1", "flag": false}, {"value": "3", "flag": false}],
                }
            })
        );
    }

    #[test]
    fn a_keyed_element_that_is_not_a_node_is_refused() {
        let source = source();
        let text_element = node(KeyedConfig {
            span: whole(&source),
            children: vec![(Some("setting"), Child::Text(span(&source, "host")))],
        });

        #[derive(Debug, Deserialize)]
        struct Target {
            #[allow(dead_code)]
            settings: Ordered<String, Keyless>,
        }
        let error = from_node::<Target>(text_element).unwrap_err();
        assert_eq!(
            error.message,
            "expected an element of a keyed collection, found a string"
        );
        assert_eq!(error.span, span(&source, "host"));
    }

    #[test]
    fn an_element_needs_exactly_one_key_child() {
        let source = source();
        #[derive(Debug, Deserialize)]
        struct Target {
            #[allow(dead_code)]
            settings: Ordered<String, Keyless>,
        }

        let keyless_element = node(Setting {
            span: span(&source, "host = 1 !"),
            children: vec![trivia(&source), (Some("value"), number(&source, "1"))],
        });
        let region = node(KeyedConfig {
            span: whole(&source),
            children: vec![(Some("setting"), Child::Node(keyless_element))],
        });
        let error = from_node::<Target>(region).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"setting\": expected exactly one \"name\" child, found 0"
        );
        assert_eq!(error.span, span(&source, "host = 1 !"));

        let twice_keyed = node(Setting {
            span: span(&source, "host = 1 !"),
            children: vec![
                (Some("name"), Child::Text(span(&source, "host"))),
                (Some("name"), Child::Text(span(&source, "port"))),
                (Some("value"), number(&source, "1")),
            ],
        });
        let region = node(KeyedConfig {
            span: whole(&source),
            children: vec![(Some("setting"), Child::Node(twice_keyed))],
        });
        let error = from_node::<Target>(region).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"setting\": expected exactly one \"name\" child, found 2"
        );
    }

    #[test]
    fn an_integer_key_is_served_as_the_declared_width() {
        #[derive(Debug, Deserialize)]
        struct Target {
            settings: BTreeMap<u16, Keyless>,
        }
        let fixture = lines(&[("7", "1"), ("9", "2")]);
        let target: Target = from_node(fixture.int_keyed()).unwrap();
        assert_eq!(target.settings.keys().copied().collect::<Vec<u16>>(), vec![7, 9]);
        assert_eq!(target.settings[&7], keyless(1));

        // A consumer newtype over the declared width works through serde's own forwarding.
        #[derive(Debug, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
        struct Id(u16);

        #[derive(Debug, Deserialize)]
        struct Wrapped {
            settings: BTreeMap<Id, Keyless>,
        }
        let wrapped: Wrapped = from_node(fixture.int_keyed()).unwrap();
        assert_eq!(wrapped.settings.keys().collect::<Vec<&Id>>(), vec![&Id(7), &Id(9)]);

        // And the self-describing shape is a map with integer keys, not stringified ones.
        #[derive(Debug, Deserialize)]
        struct Described {
            settings: SelfDescribed<u16, Keyless>,
        }
        let described: Described = from_node(fixture.int_keyed()).unwrap();
        assert_eq!(described.settings.0, vec![(7, keyless(1)), (9, keyless(2))]);
    }

    #[test]
    fn two_spellings_of_one_integer_key_are_one_key() {
        #[derive(Debug, Deserialize)]
        struct Target {
            #[allow(dead_code)]
            settings: BTreeMap<u16, Keyless>,
        }
        let fixture = lines(&[("7", "1"), ("9", "2"), ("007", "3")]);
        let error = from_node::<Target>(fixture.int_keyed()).unwrap_err();
        // Bare, not quoted: the key is the gated value.
        assert_eq!(error.message, "duplicate setting key 7");
        assert_eq!(error.span, fixture.elements[2]);
        assert_eq!(error.related[0].1, fixture.elements[0]);
    }

    #[test]
    fn multi_merges_two_spellings_of_one_integer_key_into_one_group() {
        #[derive(Debug, Deserialize)]
        struct Target {
            settings: Ordered<u16, Vec<Keyless>>,
        }
        let fixture = lines(&[("007", "1"), ("9", "2"), ("7", "3")]);
        let target: Target = from_node(fixture.int_multi()).unwrap();
        // One group, at the first occurrence's position, elements in source order across
        // spellings; the served key is the gated value, so neither spelling is preferred.
        assert_eq!(
            target.settings.0,
            vec![(7, vec![keyless(1), keyless(3)]), (9, vec![keyless(2)])]
        );
    }

    #[test]
    fn a_key_text_the_declared_gate_refuses_fails_at_that_key_child() {
        #[derive(Debug, Deserialize)]
        struct Target {
            #[allow(dead_code)]
            settings: BTreeMap<u16, Keyless>,
        }
        let fixture = lines(&[("7", "1"), ("99999", "2")]);
        let error = from_node::<Target>(fixture.int_keyed()).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"setting\": \"99999\" is not in range for u16 (0 to 65535)"
        );
        assert_eq!(error.span, fixture.keys[1]);
    }

    #[test]
    fn a_target_key_type_disagreeing_with_the_declaration_is_a_type_error() {
        // An integer-declared key into a `String`-keyed target.
        #[derive(Debug, Deserialize)]
        struct Stringly {
            #[allow(dead_code)]
            settings: Ordered<String, Keyless>,
        }
        let fixture = lines(&[("7", "1")]);
        let error = from_node::<Stringly>(fixture.int_keyed()).unwrap_err();
        assert!(error.message.contains("invalid type: integer"), "{}", error.message);
        assert_eq!(error.span, fixture.keys[0]);

        // A text-declared key into an integer-keyed target.
        #[derive(Debug, Deserialize)]
        struct Numeric {
            #[allow(dead_code)]
            settings: BTreeMap<u16, Keyless>,
        }
        let fixture = lines(&[("a", "1")]);
        let error = from_node::<Numeric>(fixture.text_keyed()).unwrap_err();
        assert!(error.message.contains("invalid type: string"), "{}", error.message);
        assert_eq!(error.span, fixture.keys[0]);
    }

    #[test]
    fn a_text_key_keeps_two_spellings_of_one_number_apart() {
        #[derive(Debug, Deserialize)]
        struct Target {
            settings: Ordered<String, Keyless>,
        }
        let fixture = lines(&[("7", "1"), ("07", "2")]);
        let target: Target = from_node(fixture.text_keyed()).unwrap();
        assert_eq!(
            target.settings.0,
            vec![("7".to_string(), keyless(1)), ("07".to_string(), keyless(2))]
        );
    }

    #[derive(Debug, Deserialize, PartialEq)]
    enum ModeTarget {
        Fast,
        Slow,
    }

    /// An enum-shaped node over its own source, carrying the one child that picked a variant.
    /// The source is handed back with it: a span is only positioned while its text is alive.
    macro_rules! enum_node {
        ($node:ident, $text:literal, $label:literal) => {{
            let source = SourceText::from_str($text, None);
            let span = Span::new_with_source(0, $text.len() as i64, &source);
            let held = node($node {
                span: span.clone(),
                children: vec![(None, Child::Text(span.clone())), (Some($label), Child::Text(span))],
            });
            (source, held)
        }};
    }

    #[test]
    fn an_enum_shaped_rule_serves_the_matched_variants_name() {
        let (_source, fast) = enum_node!(Mode, "fast", "fast");
        assert_eq!(from_node::<ModeTarget>(fast.clone()).unwrap(), ModeTarget::Fast);
        // A string target gets the variant name too, not the literal the source spelled.
        assert_eq!(from_node::<String>(fast).unwrap(), "Fast");

        let (_source, slow) = enum_node!(Mode, "slow", "slow");
        assert_eq!(from_node::<ModeTarget>(slow).unwrap(), ModeTarget::Slow);
    }

    #[test]
    fn an_enum_node_carrying_two_labels_resolves_in_variant_order() {
        // Reachable only from a hand-built CST — a parse puts one alternative's children
        // there. A hand-built node carrying two must resolve the same way on every layer
        // that can be handed it.
        let source = SourceText::from_str("slowfast", None);
        let both = node(Mode {
            span: whole(&source),
            children: vec![
                (Some("slow"), Child::Text(Span::new_with_source(0, 4, &source))),
                (Some("fast"), Child::Text(Span::new_with_source(4, 8, &source))),
            ],
        });
        assert_eq!(from_node::<ModeTarget>(both).unwrap(), ModeTarget::Fast);
    }

    #[test]
    fn an_enum_node_matching_no_alternative_has_no_value() {
        let source = SourceText::from_str("fast", None);
        let empty = node(Mode {
            span: Span::new_with_source(0, 4, &source),
            children: vec![(None, Child::Text(Span::new_with_source(0, 4, &source)))],
        });
        let error = from_node::<ModeTarget>(empty).unwrap_err();
        // The wording the AST layer's own enum converters raise for the same node.
        assert_eq!(error.message, "rule \"mode\": no alternative label is present");
        assert_eq!(error.span, Span::new_with_source(0, 4, &source));
    }

    #[test]
    fn any_other_position_names_a_variant_by_its_own_text() {
        // The route a plain grammar identifier takes to a Rust enum, with no `Form::Enum`
        // rule in between.
        let (_source, held) = lexeme_node("Fast");
        assert_eq!(from_node::<ModeTarget>(held).unwrap(), ModeTarget::Fast);

        #[derive(Debug, Deserialize)]
        struct Chosen {
            #[allow(dead_code)]
            value: ModeTarget,
        }
        let (source, held) = valued("Quick");
        let error = from_node::<Chosen>(held).unwrap_err();
        assert!(error.message.contains("unknown variant"), "{}", error.message);
        assert_eq!(error.span, whole(&source));
    }

    #[test]
    fn a_bool_shaped_rule_serves_a_boolean() {
        let (_source, on) = enum_node!(Toggle, "on", "on");
        assert!(from_node::<bool>(on.clone()).unwrap());
        assert_eq!(from_node::<serde_json::Value>(on).unwrap(), serde_json::json!(true));

        let (_source, off) = enum_node!(Toggle, "off", "off");
        assert!(!from_node::<bool>(off).unwrap());
    }

    /// A `wrapped` node over its own source, holding one `number` under `inner`.
    fn wrapped(text: &str) -> (SourceText, Node) {
        let source = SourceText::from_str(text, None);
        let span = whole(&source);
        let held = node(Wrapped {
            span: span.clone(),
            children: vec![
                trivia(&source),
                (
                    Some("inner"),
                    Child::Node(node(Number {
                        span,
                        children: Vec::new(),
                    })),
                ),
            ],
        });
        (source, held)
    }

    #[test]
    fn a_transparent_rule_is_erased_to_the_value_of_its_one_field() {
        let (_source, held) = wrapped("42");
        assert_eq!(from_node::<u16>(held).unwrap(), 42);

        // A transparent field is the payload wherever it sits, not a one-entry map around it.
        let source = SourceText::from_str("7", None);
        let inner = node(Wrapped {
            span: whole(&source),
            children: vec![(
                Some("inner"),
                Child::Node(node(Number {
                    span: whole(&source),
                    children: Vec::new(),
                })),
            )],
        });
        let setting = node(Setting {
            span: whole(&source),
            children: vec![
                (Some("name"), Child::Text(whole(&source))),
                (Some("value"), Child::Node(inner)),
            ],
        });
        let served: serde_json::Value = from_node(setting).unwrap();
        assert_eq!(served, serde_json::json!({"name": "7", "value": "7", "flag": false}));
    }

    #[test]
    fn transparency_is_erased_all_the_way_down() {
        let (source, inner) = wrapped("13");
        let outer = node(Held {
            span: whole(&source),
            children: vec![trivia(&source), (Some("inner"), Child::Node(inner))],
        });
        assert_eq!(from_node::<u16>(outer).unwrap(), 13);
    }

    #[test]
    fn a_transparent_rule_without_its_payload_is_the_shared_arity_refusal() {
        let source = SourceText::from_str("()", None);
        let empty = node(Wrapped {
            span: whole(&source),
            children: vec![trivia(&source)],
        });
        let error = from_node::<u16>(empty).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"wrapped\": expected exactly one \"inner\" child, found 0"
        );
        assert_eq!(error.span, whole(&source));
    }

    #[test]
    fn a_transparent_rule_over_a_collection_serves_the_sequence() {
        let source = SourceText::from_str("1 2", None);
        let listing = node(Listing {
            span: whole(&source),
            children: vec![
                (
                    Some("item"),
                    Child::Node(node(Number {
                        span: span(&source, "1"),
                        children: Vec::new(),
                    })),
                ),
                trivia(&source),
                (
                    Some("item"),
                    Child::Node(node(Number {
                        span: span(&source, "2"),
                        children: Vec::new(),
                    })),
                ),
            ],
        });
        assert_eq!(from_node::<Vec<u8>>(listing).unwrap(), vec![1, 2]);
    }

    #[derive(Debug, Deserialize, PartialEq)]
    enum EntryTarget {
        Pair { key: String, value: u16 },
        Bare(u16),
    }

    /// An `entry` node matching the first alternative: a key and a value.
    fn pair_entry() -> (SourceText, Node) {
        let source = SourceText::from_str("a = 1", None);
        let held = node(Entry {
            span: whole(&source),
            children: vec![
                (Some("key"), Child::Text(span(&source, "a"))),
                trivia(&source),
                (
                    Some("value"),
                    Child::Node(node(Number {
                        span: span(&source, "1"),
                        children: Vec::new(),
                    })),
                ),
            ],
        });
        (source, held)
    }

    /// An `entry` node matching the second alternative: one child, which is the payload.
    fn bare_entry() -> (SourceText, Node) {
        let source = SourceText::from_str("5", None);
        let held = node(Entry {
            span: whole(&source),
            children: vec![
                trivia(&source),
                (
                    Some("bare"),
                    Child::Node(node(Number {
                        span: whole(&source),
                        children: Vec::new(),
                    })),
                ),
            ],
        });
        (source, held)
    }

    #[test]
    fn a_sum_rule_is_the_externally_tagged_enum_of_its_matched_alternative() {
        let (_source, pair) = pair_entry();
        assert_eq!(
            from_node::<EntryTarget>(pair).unwrap(),
            EntryTarget::Pair {
                key: "a".to_string(),
                value: 1,
            }
        );

        // The one-label alternative carries its child itself: a newtype variant, not a map.
        let (_source, bare) = bare_entry();
        assert_eq!(from_node::<EntryTarget>(bare).unwrap(), EntryTarget::Bare(5));
    }

    #[derive(Debug, Deserialize, PartialEq)]
    enum UnitTarget {
        Bare,
    }

    #[derive(Debug, Deserialize, PartialEq)]
    enum TupleTarget {
        Pair(String, u16),
    }

    #[test]
    fn a_variant_a_target_declares_as_a_unit_one_still_carries_its_content() {
        // Every alternative carries something, so a unit variant is a target-shape
        // disagreement: reported, never absorbed by dropping what the alternative parsed.
        let (source, bare) = bare_entry();
        let error = from_node::<UnitTarget>(bare).unwrap_err();
        assert_eq!(
            error.message,
            "variant \"Bare\" carries content, found a string, expected a unit variant"
        );
        assert_eq!(error.span, whole(&source));
    }

    #[test]
    fn a_tuple_variant_target_is_the_unsupported_refusal_of_its_own() {
        let (source, pair) = pair_entry();
        let error = from_node::<TupleTarget>(pair).unwrap_err();
        assert_eq!(
            error.message,
            "tuple variants are not supported by the FLTK serde frontend"
        );
        assert_eq!(error.span, whole(&source));
    }

    #[test]
    fn a_self_describing_target_reads_a_sum_as_a_one_entry_map() {
        let (_source, pair) = pair_entry();
        let served: serde_json::Value = from_node(pair).unwrap();
        // The alternative's own fields and nothing else of the rule's.
        assert_eq!(served, serde_json::json!({"Pair": {"key": "a", "value": "1"}}));

        let (_source, bare) = bare_entry();
        let served: serde_json::Value = from_node(bare).unwrap();
        assert_eq!(served, serde_json::json!({"Bare": "5"}));
    }

    #[test]
    fn a_node_no_alternative_of_its_rule_accepts_is_refused() {
        // Both labels of the first alternative and the second's as well: neither fits.
        let source = SourceText::from_str("a = 1", None);
        let mixed = node(Entry {
            span: whole(&source),
            children: vec![
                (Some("key"), Child::Text(span(&source, "a"))),
                (
                    Some("value"),
                    Child::Node(node(Number {
                        span: span(&source, "1"),
                        children: Vec::new(),
                    })),
                ),
                (
                    Some("bare"),
                    Child::Node(node(Number {
                        span: span(&source, "1"),
                        children: Vec::new(),
                    })),
                ),
            ],
        });
        let error = from_node::<EntryTarget>(mixed).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"entry\": no alternative matches the node's labeled children"
        );
        assert_eq!(error.span, whole(&source));

        // A labeled child matching no pair of the table matches no alternative.
        let alien = node(Entry {
            span: whole(&source),
            children: vec![
                (
                    Some("bare"),
                    Child::Node(node(Number {
                        span: span(&source, "1"),
                        children: Vec::new(),
                    })),
                ),
                (Some("stray"), Child::Text(span(&source, "a"))),
            ],
        });
        let error = from_node::<EntryTarget>(alien).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"entry\": no alternative matches the node's labeled children"
        );
    }

    #[test]
    fn a_sum_node_is_held_whole_by_raw_and_never_dispatched() {
        let (source, pair) = pair_entry();
        let held: Raw<Entry> = from_node(pair).unwrap();
        assert_eq!(held.node().read().span, whole(&source));

        // And a field the target has no use for is not dispatched either: this node matches
        // no alternative, and nothing asks it to.
        let broken = node(Entry {
            span: whole(&source),
            children: Vec::new(),
        });
        let setting = node(Setting {
            span: whole(&source),
            children: vec![
                (Some("name"), Child::Text(span(&source, "a"))),
                (Some("value"), Child::Node(broken)),
            ],
        });

        #[derive(Debug, Deserialize)]
        struct OnlyName {
            name: String,
        }
        let target: OnlyName = from_node(setting).unwrap();
        assert_eq!(target.name, "a");
    }

    #[derive(Debug, Deserialize, PartialEq)]
    enum ChainTarget {
        Operand(u16),
        Binary {
            operator: String,
            lhs: Box<ChainTarget>,
            rhs: Box<ChainTarget>,
        },
    }

    /// A fold rule's node, whose children are the flat run the grammar matched:
    /// `1+2+3` is three operands with an operator between each pair.
    struct Chain {
        source: SourceText,
        children: Vec<(Option<&'static str>, Child)>,
    }

    fn chain(text: &str) -> Chain {
        let source = SourceText::from_str(text, None);
        let mut children = Vec::new();
        let mut at = 0i64;
        for (index, part) in text.split('+').enumerate() {
            if index > 0 {
                children.push((Some("op"), Child::Text(Span::new_with_source(at, at + 1, &source))));
                at += 1;
            }
            let end = at + part.chars().count() as i64;
            children.push((
                Some("operand"),
                Child::Node(node(Number {
                    span: Span::new_with_source(at, end, &source),
                    children: Vec::new(),
                })),
            ));
            children.push(trivia(&source));
            at = end;
        }
        Chain { source, children }
    }

    impl Chain {
        fn left(&self) -> Node {
            node(LeftChain {
                span: whole(&self.source),
                children: self.children.clone(),
            })
        }

        fn right(&self) -> Node {
            node(RightChain {
                span: whole(&self.source),
                children: self.children.clone(),
            })
        }
    }

    fn operand(value: u16) -> Box<ChainTarget> {
        Box::new(ChainTarget::Operand(value))
    }

    #[test]
    fn a_fold_chain_nests_the_way_its_direction_says() {
        let fixture = chain("1+2+3");
        assert_eq!(
            from_node::<ChainTarget>(fixture.left()).unwrap(),
            ChainTarget::Binary {
                operator: "+".to_string(),
                lhs: Box::new(ChainTarget::Binary {
                    operator: "+".to_string(),
                    lhs: operand(1),
                    rhs: operand(2),
                }),
                rhs: operand(3),
            }
        );
        assert_eq!(
            from_node::<ChainTarget>(fixture.right()).unwrap(),
            ChainTarget::Binary {
                operator: "+".to_string(),
                lhs: operand(1),
                rhs: Box::new(ChainTarget::Binary {
                    operator: "+".to_string(),
                    lhs: operand(2),
                    rhs: operand(3),
                }),
            }
        );
    }

    #[test]
    fn a_single_operand_chain_is_the_operand_and_no_link() {
        let fixture = chain("9");
        assert_eq!(
            from_node::<ChainTarget>(fixture.left()).unwrap(),
            ChainTarget::Operand(9)
        );
    }

    #[test]
    fn a_chain_whose_operators_do_not_interleave_is_the_shared_fold_refusal() {
        let source = SourceText::from_str("1 2", None);
        let uninterleaved = node(LeftChain {
            span: whole(&source),
            children: vec![
                (
                    Some("operand"),
                    Child::Node(node(Number {
                        span: span(&source, "1"),
                        children: Vec::new(),
                    })),
                ),
                (
                    Some("operand"),
                    Child::Node(node(Number {
                        span: span(&source, "2"),
                        children: Vec::new(),
                    })),
                ),
            ],
        });
        let error = from_node::<ChainTarget>(uninterleaved).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"chain\": a fold over 2 operand(s) needs 1 operator(s), but the node has 0"
        );
        assert_eq!(error.span, whole(&source));
    }

    #[test]
    fn a_self_describing_target_reads_a_chain_as_nested_one_entry_maps() {
        let fixture = chain("1+2");
        let served: serde_json::Value = from_node(fixture.left()).unwrap();
        assert_eq!(
            served,
            serde_json::json!({
                "Binary": {
                    "operator": "+",
                    "lhs": {"Operand": "1"},
                    "rhs": {"Operand": "2"},
                }
            })
        );
    }

    #[test]
    fn a_link_covers_everything_below_it() {
        #[derive(Debug, Deserialize)]
        enum Positioned {
            Operand(#[allow(dead_code)] u16),
            Binary {
                #[allow(dead_code)]
                operator: String,
                lhs: Spanned<Box<Positioned>>,
                #[allow(dead_code)]
                rhs: Spanned<Box<Positioned>>,
            },
        }
        let fixture = chain("1+2+3");
        let Positioned::Binary { lhs, .. } = from_node::<Positioned>(fixture.left()).unwrap() else {
            unreachable!("three operands make a link")
        };
        // The left sub-chain is `1+2`, whose link span is the merge of both operands.
        assert_eq!(lhs.span().start(), 0);
        assert_eq!(lhs.span().end(), 3);
    }

    // --- `flatten;` hoists ---------------------------------------------------------------

    const HOIST_TEXT: &str = "alpha [ 71 : 32 aa bb ~ ]";

    fn hoist_source() -> SourceText {
        SourceText::from_str(HOIST_TEXT, None)
    }

    /// The innermost wrapper, whose three fields are two hoists below `tuned`.
    fn extras(source: &SourceText, depth: Option<&str>, tags: &[&str], mark: bool) -> Child {
        let mut children = vec![trivia(source)];
        if let Some(text) = depth {
            children.push((Some("depth"), number(source, text)));
        }
        for tag in tags {
            children.push((Some("tag"), Child::Text(span(source, tag))));
            children.push(trivia(source));
        }
        if mark {
            children.push((Some("mark"), Child::Text(span(source, "~"))));
        }
        Child::Node(node(Extras {
            span: span(source, "32 aa bb ~"),
            children,
        }))
    }

    /// The outer wrapper: its own `cap` field, and the wrapper carrying the rest.
    fn limits(source: &SourceText, cap: &str, deep: Option<Child>) -> Child {
        let mut children = vec![trivia(source), (Some("cap"), number(source, cap))];
        if let Some(child) = deep {
            children.push((Some("deep"), child));
        }
        children.push(trivia(source));
        Child::Node(node(Limits {
            span: span(source, "[ 71 : 32 aa bb ~ ]"),
            children,
        }))
    }

    fn tuned(source: &SourceText, extra: Vec<(Option<&'static str>, Child)>) -> Node {
        let mut children = vec![trivia(source), (Some("title"), Child::Text(span(source, "alpha")))];
        children.extend(extra);
        children.push(trivia(source));
        node(Tuned {
            span: whole(source),
            children,
        })
    }

    /// The whole wrapper chain, which is the shape a parse of the fixture text produces.
    fn wrapped_tuned(source: &SourceText) -> Node {
        let deep = extras(source, Some("32"), &["aa", "bb"], true);
        tuned(source, vec![(Some("w"), limits(source, "71", Some(deep)))])
    }

    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct TunedTarget {
        title: String,
        cap: Option<u16>,
        depth: Option<u16>,
        tags: Vec<String>,
        mark: bool,
    }

    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct LimitsTarget {
        cap: u16,
        depth: Option<u16>,
        tags: Vec<String>,
        mark: bool,
    }

    #[test]
    fn a_hoisted_field_is_read_down_its_whole_wrapper_path() {
        let source = hoist_source();
        let target: TunedTarget = from_node(wrapped_tuned(&source)).unwrap();
        assert_eq!(
            target,
            TunedTarget {
                title: "alpha".to_string(),
                cap: Some(71),
                depth: Some(32),
                tags: vec!["aa".to_string(), "bb".to_string()],
                mark: true,
            }
        );
    }

    #[test]
    fn a_wrapper_is_read_once_however_many_fields_it_serves() {
        let source = hoist_source();
        let fixture = wrapped_tuned(&source);
        CHILD_READS.with(|reads| reads.set(0));
        let _: TunedTarget = from_node(fixture).unwrap();
        // Three nodes carry children here — `tuned` and the two wrappers below it — and four of
        // the five fields are read through one or both wrappers. Each node is asked for its
        // children once and every field is bucketed from that answer, so the count is the
        // number of nodes and not the number of (field, step) pairs.
        assert_eq!(CHILD_READS.with(Cell::get), 3);
    }

    #[test]
    fn a_wrapper_served_on_its_own_splices_the_wrappers_it_holds() {
        let source = hoist_source();
        let Child::Node(held) = limits(&source, "71", Some(extras(&source, None, &["aa"], false))) else {
            unreachable!("the builder returns a node child")
        };
        let target: LimitsTarget = from_node(held).unwrap();
        assert_eq!(
            target,
            LimitsTarget {
                cap: 71,
                depth: None,
                tags: vec!["aa".to_string()],
                mark: false,
            }
        );
    }

    #[test]
    fn an_absent_optional_wrapper_leaves_every_field_it_carried_empty() {
        let source = hoist_source();
        let target: TunedTarget = from_node(tuned(&source, Vec::new())).unwrap();
        assert_eq!(
            target,
            TunedTarget {
                title: "alpha".to_string(),
                cap: None,
                depth: None,
                tags: Vec::new(),
                mark: false,
            }
        );
    }

    #[test]
    fn an_absent_required_wrapper_is_the_shared_arity_refusal() {
        let source = hoist_source();
        let held = tuned(&source, vec![(Some("w"), limits(&source, "71", None))]);
        let error = from_node::<TunedTarget>(held).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"limits\": expected exactly one \"deep\" child, found 0"
        );
        // The wrapper that should have held it is where it is missing from.
        assert_eq!(error.span.start(), span(&source, "[ 71 : 32 aa bb ~ ]").start());
    }

    #[test]
    fn a_repeated_wrapper_label_is_refused_rather_than_taking_the_first() {
        let source = hoist_source();
        let deep = extras(&source, Some("32"), &[], false);
        let held = tuned(
            &source,
            vec![
                (Some("w"), limits(&source, "71", Some(deep.clone()))),
                (Some("w"), limits(&source, "71", Some(deep))),
            ],
        );
        let error = from_node::<TunedTarget>(held).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"tuned\": expected at most one \"w\" child, found 2"
        );
    }

    #[test]
    fn a_wrapper_label_carrying_a_terminal_has_no_node_to_descend_into() {
        let source = hoist_source();
        let held = tuned(&source, vec![(Some("w"), Child::Text(span(&source, "alpha")))]);
        let error = from_node::<TunedTarget>(held).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"tuned\": label \"w\" has a child of unexpected kind"
        );
    }

    #[test]
    fn a_hoisted_label_is_not_read_off_the_node_the_wrapper_hangs_from() {
        let source = hoist_source();
        let deep = extras(&source, Some("32"), &[], false);
        // A `cap` child of `tuned` itself, which the grammar puts inside the wrapper: the
        // field's label is the wrapper's, so this one belongs to no field at all.
        let held = tuned(
            &source,
            vec![
                (Some("cap"), number(&source, "32")),
                (Some("w"), limits(&source, "71", Some(deep))),
            ],
        );
        let target: TunedTarget = from_node(held).unwrap();
        assert_eq!(target.cap, Some(71));
    }

    #[test]
    fn a_failure_inside_a_wrapper_is_positioned_at_the_child_that_raised_it() {
        let source = hoist_source();
        // A `depth` child whose text no integer gate accepts, two wrappers down.
        let deep = extras(&source, Some("alpha"), &[], false);
        let held = tuned(&source, vec![(Some("w"), limits(&source, "71", Some(deep)))]);
        let error = from_node::<TunedTarget>(held).unwrap_err();
        assert_eq!(error.message, "rule \"number\": \"alpha\" is not a valid u16");
        assert_eq!(error.span.start(), span(&source, "alpha").start());
    }

    #[test]
    fn a_hoisted_field_keeps_the_place_the_model_gave_it() {
        let source = hoist_source();
        let served: Ordered<String, serde_json::Value> = from_node(wrapped_tuned(&source)).unwrap();
        let keys: Vec<&str> = served.0.iter().map(|(key, _)| key.as_str()).collect();
        assert_eq!(keys, ["title", "cap", "depth", "tags", "mark"]);
    }

    // --- generated AST types as targets ---------------------------------------------------

    /// What a generated `de.rs` writes for one rule's AST type: the magic name, and an impl
    /// that is one call handing `from_cst` in. Here `number`'s AST type coerces to `u16`, as a
    /// `type: u16;` sidecar line would make it.
    const NUMBER_AST_NAME: &str = "$__fltk_private_ast::number";

    #[derive(Debug, PartialEq)]
    struct NumberAst {
        value: u16,
        span: Span,
    }

    fn number_from_cst(node: &Shared<Number>) -> Result<NumberAst, AstError> {
        let span = node.read().span.clone();
        let text = node_text(&span, "number")?;
        Ok(NumberAst {
            value: scalar::parse_u16(&text, "number", &span)?,
            span,
        })
    }

    impl<'de> Deserialize<'de> for NumberAst {
        fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
            crate::deserialize_ast(deserializer, NUMBER_AST_NAME, number_from_cst)
        }
    }

    #[derive(Debug, Deserialize)]
    #[serde(deny_unknown_fields)]
    struct AstSettingTarget {
        name: String,
        value: NumberAst,
        flag: bool,
    }

    #[test]
    fn a_field_declared_as_a_generated_ast_type_is_what_from_cst_builds() {
        let source = source();
        let served: AstSettingTarget = from_node(host(&source)).unwrap();
        assert_eq!(served.name, "host");
        assert!(served.flag);
        assert_eq!(served.value.value, 1);
        assert_eq!(served.value.span.text().as_deref(), Some("1"));
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn an_ast_type_is_a_target_at_the_root_as_well_as_in_a_field() {
        let (source, held) = lexeme_node("42");
        let served: NumberAst = from_node(held).unwrap();
        assert_eq!(served.value, 42);
        assert_eq!(served.span.text().as_deref(), Some("42"));
        assert_eq!(channel::depth(), 0);
        drop(source);
    }

    #[test]
    fn an_ast_type_at_another_rules_node_names_both_rules_at_that_node() {
        let source = source();
        let error = from_node::<NumberAst>(host(&source)).unwrap_err();
        assert_eq!(
            error.message,
            "expected a `number` node for its AST type, found rule `setting`"
        );
        // Raised unpositioned by the conversion, positioned by the frame that ran it.
        assert_eq!(error.span.text().as_deref(), Some("host = 1 !"));
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn an_ast_type_at_a_terminal_child_is_refused_by_kind() {
        #[derive(Debug, Deserialize)]
        #[allow(dead_code)]
        struct NameAsAst {
            name: NumberAst,
        }

        let source = source();
        let error = from_node::<NameAsAst>(host(&source)).unwrap_err();
        assert_eq!(error.message, "expected a `number` node to convert, found a string");
        assert_eq!(error.span.text().as_deref(), Some("host"));
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn a_transparent_rule_is_erased_before_an_ast_type_sees_the_node() {
        // The AST layer erases the wrapper too, so the type a use site carries is the payload's
        // and the node the target names is the one below it.
        let (source, inner) = lexeme_node("42");
        let held = node(Held {
            span: whole(&source),
            children: vec![trivia(&source), (Some("inner"), Child::Node(inner))],
        });
        let served: NumberAst = from_node(held).unwrap();
        assert_eq!(served.value, 42);
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn a_from_cst_failure_is_the_ast_layers_own_error_at_its_own_span() {
        let (source, held) = lexeme_node("99999");
        let error = from_node::<NumberAst>(held).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"number\": \"99999\" is not in range for u16 (0 to 65535)"
        );
        assert_eq!(error.span.text().as_deref(), Some("99999"));
        assert_eq!(channel::depth(), 0);
        drop(source);
    }

    #[test]
    fn a_from_cst_failure_keeps_its_own_span_under_a_node_that_covers_more_than_it() {
        // The frame positions an error that arrived without a span; this one arrived with a
        // precise one, and the whole selling point of an AST-typed field is that it survives.
        let source = SourceText::from_str("port = 99999 !", None);
        let held = node(Setting {
            span: whole(&source),
            children: vec![
                trivia(&source),
                (Some("name"), Child::Text(span(&source, "port"))),
                trivia(&source),
                (Some("value"), number(&source, "99999")),
            ],
        });

        #[derive(Debug, Deserialize)]
        #[allow(dead_code)]
        struct SettingWithAstValue {
            name: String,
            value: NumberAst,
        }

        let error = from_node::<SettingWithAstValue>(held).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"number\": \"99999\" is not in range for u16 (0 to 65535)"
        );
        assert_eq!(error.span.text().as_deref(), Some("99999"), "not the whole setting");
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn spanned_over_an_ast_type_takes_both_payloads() {
        let (source, held) = lexeme_node("42");
        let served: Spanned<NumberAst> = from_node(held).unwrap();
        assert_eq!(served.value().value, 42);
        assert_eq!(served.span().text().as_deref(), Some("42"));
        assert_eq!(channel::depth(), 0);
        drop(source);
    }

    #[test]
    fn an_ast_name_nothing_provided_a_conversion_for_is_refused() {
        // Only the generated impl asks for the name, and it always hands the conversion in; a
        // caller spelling the name itself gets told so rather than a wrong value.
        #[derive(Debug)]
        struct Impostor;
        impl<'de> Deserialize<'de> for Impostor {
            fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
                deserializer.deserialize_newtype_struct(NUMBER_AST_NAME, ImpostorVisitor)
            }
        }
        struct ImpostorVisitor;
        impl<'de> Visitor<'de> for ImpostorVisitor {
            type Value = Impostor;

            fn expecting(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                f.write_str("nothing in particular")
            }

            fn visit_newtype_struct<D: Deserializer<'de>>(self, _d: D) -> Result<Self::Value, D::Error> {
                Ok(Impostor)
            }
        }

        let (source, held) = lexeme_node("42");
        let error = from_node::<Impostor>(held).unwrap_err();
        assert_eq!(
            error.message,
            "an AST value of rule `number` is served only through its generated `Deserialize` impl"
        );
        assert_eq!(error.span.text().as_deref(), Some("42"));
        assert_eq!(channel::depth(), 0);
        drop(source);
    }

    #[test]
    fn an_ast_typed_field_is_optional_and_repeatable_like_any_other() {
        // The containers put serde's own `OptionVisitor` and `SeqAccess` frames between the
        // impl handing its conversion in and the frame that runs it.
        #[derive(Debug, Deserialize)]
        #[serde(deny_unknown_fields)]
        struct OptionalAst {
            name: String,
            value: Option<NumberAst>,
            flag: bool,
            extra: Option<NumberAst>,
        }

        #[derive(Debug, Deserialize)]
        struct RepeatedAst {
            items: Vec<NumberAst>,
        }

        let source = source();
        let served: OptionalAst = from_node(host(&source)).unwrap();
        assert_eq!(served.name, "host");
        assert!(served.flag);
        assert_eq!(served.value.expect("the value child is there").value, 1);
        assert!(served.extra.is_none(), "an absent child never reaches the conversion");
        assert_eq!(channel::depth(), 0);

        let listed = SourceText::from_str("1 2", None);
        let held = node(Mixed {
            span: whole(&listed),
            children: vec![
                trivia(&listed),
                (Some("item"), number(&listed, "1")),
                trivia(&listed),
                (Some("item"), number(&listed, "2")),
            ],
        });
        let served: RepeatedAst = from_node(held).unwrap();
        assert_eq!(served.items.iter().map(|item| item.value).collect::<Vec<_>>(), [1, 2]);
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn an_ast_typed_field_inside_a_flattened_struct_says_what_lost_the_connection() {
        // A `#[serde(flatten)]` field is deserialized from entries the derive buffered into
        // serde's own representation, which carries no newtype-struct name — so the conversion
        // is never taken. The refusal is right; what it must not do is tell a consumer
        // deserializing FLTK source that their Deserializer is not FLTK's.
        #[derive(Debug, Deserialize)]
        #[allow(dead_code)]
        struct Outer {
            #[serde(flatten)]
            inner: Inner,
        }

        #[derive(Debug, Deserialize)]
        #[allow(dead_code)]
        struct Inner {
            value: NumberAst,
        }

        let source = source();
        let error = from_node::<Outer>(host(&source)).unwrap_err();
        assert!(error.message.contains(crate::wrappers::FOREIGN), "{}", error.message);
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn an_ast_typed_variant_of_an_untagged_enum_is_refused_loudly() {
        // The other adapter that buffers. serde swallows the inner error for an untagged enum,
        // so what is pinned here is that it fails and that the side channel is left as found.
        #[derive(Debug, Deserialize)]
        #[serde(untagged)]
        #[allow(dead_code)]
        enum Either {
            Number(NumberAst),
        }

        let (source, held) = lexeme_node("42");
        let error = from_node::<Either>(held).unwrap_err();
        assert!(!error.message.is_empty());
        assert_eq!(channel::depth(), 0);
        drop(source);
    }

    // --- union labels --------------------------------------------------------------------

    #[test]
    fn a_union_label_serves_each_child_as_its_own_rules_shape() {
        let source = source();
        let held = node(Mixed {
            span: whole(&source),
            children: vec![
                trivia(&source),
                (Some("item"), number(&source, "1")),
                trivia(&source),
                (Some("item"), setting(&source, "port = 99999", "port", "9999", false)),
            ],
        });
        let served: serde_json::Value = from_node(held).unwrap();
        assert_eq!(
            served,
            serde_json::json!({
                "items": [
                    "1",
                    {"name": "port", "value": "9999", "flag": false},
                ],
            })
        );
    }
}
