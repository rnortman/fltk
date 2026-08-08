//! What a generated `de.rs` tells this crate about the tree it deserializes from.
//!
//! A CST is generated code: every rule has its own node struct, its own label enum and its own
//! child enum, so nothing written here can read a node's children in the abstract. What the
//! generated module supplies instead is one [`NodeShape`] impl per rule — where a node is, what
//! its labeled children are, and the [`Shape`] saying how the rule's nodes are served — and the
//! Deserializer over that description lives here rather than being emitted once per grammar.
//!
//! [`Node`] is the type-erased handle those impls are reached through: a child can be a node of
//! any rule, so one node's children are not of one type. Erasure is by `Rc<dyn ...>` over the
//! `Shared<T>` handle the CST already holds its children by, so reaching a child costs a
//! reference-count bump and no copy of the tree.
//!
//! This module is public because generated code names it, and is the protocol between this
//! crate and that generated code rather than a surface to build on.

use std::fmt;
use std::rc::Rc;

use fltk_ast_core::dispatch;
use fltk_cst_core::{Shared, Span};

use crate::channel::Carried;

/// How the Deserializer serves the nodes of one rule.
#[derive(Clone, Copy, Debug)]
pub struct Shape {
    /// The grammar rule, which is what diagnostics name.
    pub rule: &'static str,
    /// The serde data-model form its nodes take.
    pub form: Form,
}

/// The serde data model one rule's nodes are served as.
///
/// The forms are the model's node forms, minus the ones whose deserializers are not written
/// yet: a rule the generator classifies otherwise has no `Shape` to describe it, so no
/// unreachable arm stands here waiting for one.
#[derive(Clone, Copy, Debug)]
pub enum Form {
    /// A rule whose children are terminals only: a scalar over the node's source text, read
    /// from the node's own span or — under `text_from:` — from the named label's child.
    Terminal {
        /// The label whose child carries the text, when it is not the node's own span.
        text_from: Option<&'static str>,
    },
    /// A rule with labeled children: a map with one entry per field, in field order.
    Product {
        /// The fields, in the order the model declares them, which is the order they are
        /// served in.
        fields: &'static [Field],
    },
    /// A rule that is a choice between literal alternatives: one of [`variants`](Form::Enum),
    /// served as a unit variant to an enum target and as its name to a string one.
    Enum {
        /// The alternatives, each named by the label whose presence picks it.
        variants: &'static [Variant],
        /// The label of the alternative that is `true`, where the rule carries a boolean
        /// rather than a variant; every other alternative is then `false`.
        truthy: Option<&'static str>,
    },
    /// A rule whose alternatives carry values and are told apart by the labeled children a
    /// node holds: an externally tagged enum, `{Variant: content}`.
    Sum {
        /// How a node's labeled children decide which alternative it came from. The counting
        /// rule is the AST layer's, evaluated by the same code, so one node resolves to one
        /// alternative whichever layer is reading it.
        table: &'static dispatch::Table,
        /// The alternatives in grammar order, indexed by the variant the table selects.
        alternatives: &'static [Alternative],
    },
    /// A rule `fold_left:`/`fold_right:` turns into a binary chain over its operands.
    Fold(&'static Fold),
    /// A rule erased by `transparent;`: its nodes are served as the value of their one field,
    /// with no map around it, which is what its use sites carry.
    ///
    /// Only the single-field product spelling needs the arm — a terminal-only or enum-shaped
    /// rule is erased to a value the [`Form::Terminal`] and [`Form::Enum`] arms already serve.
    /// [`Field::name`] is not served here; it is carried because the emitter writes down the
    /// model's field and does not reshape it.
    Transparent { field: Field },
}

/// One alternative of a sum rule, as the externally tagged enum it is served as.
#[derive(Clone, Copy, Debug)]
pub struct Alternative {
    /// The variant name serde sees: the model's, after any sidecar rename.
    pub name: &'static str,
    /// What the variant carries.
    pub payload: Content,
}

/// What one sum alternative's variant carries.
///
/// The two arms are the model's two payload shapes: an alternative naming one label carries
/// that child's own value, and one naming several carries a generated product over them.
#[derive(Clone, Copy, Debug)]
pub enum Content {
    /// The value of the alternative's one labeled child — a newtype variant.
    Child { label: &'static str },
    /// A map over the fields the alternative's children make up — a struct variant. The fields
    /// are the alternative's own, not the whole rule's.
    Fields { fields: &'static [Field] },
}

/// Which way a fold rule nests its operands.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Direction {
    /// `a op b op c` is `(a op b) op c`.
    Left,
    /// `a op b op c` is `a op (b op c)`.
    Right,
}

/// A fold rule's chain, as the externally tagged shape the AST layer's type has.
///
/// A node holds the chain flat — operands with one operator between each pair — and the value
/// is the nesting: a lone operand is `{Operand: value}`, and anything longer is
/// `{Binary: {op, lhs, rhs}}` down to the operands. The nesting order, the span merging and
/// the interleaving diagnostic come from `fltk-ast-core`, so a chain reads the same way here
/// as the generated converters build it.
#[derive(Clone, Copy, Debug)]
pub struct Fold {
    pub direction: Direction,
    /// The label the operands carry, in source order.
    pub operand_label: &'static str,
    /// The label the operators carry: one between each operand pair.
    pub operator_label: &'static str,
    /// The variant name a bare operand is tagged with.
    pub operand_variant: &'static str,
    /// The variant name a link is tagged with.
    pub binary_variant: &'static str,
    /// The link's operator member, after any sidecar rename.
    pub op: &'static str,
    /// The link's two sub-chain members.
    pub lhs: &'static str,
    pub rhs: &'static str,
}

/// One alternative of an enum-shaped rule.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Variant {
    /// The name serde sees: the model's variant name, after any sidecar rename. It is the
    /// variant's identity on this path — a string target is served the name, not the literal
    /// the source spelled it with.
    pub name: &'static str,
    /// The CST label the matched alternative's child carries.
    pub label: &'static str,
}

/// One field of a product rule.
#[derive(Clone, Copy, Debug)]
pub struct Field {
    /// The map key it is served under: the model's field name, after any sidecar rename.
    pub name: &'static str,
    /// The CST label its children carry.
    pub label: &'static str,
    /// How many children it takes, and what that makes the value.
    pub container: Container,
    /// The `flatten;` wrappers between the node and the children this field takes, outermost
    /// first; empty for a field the node holds itself.
    pub hoist: &'static [Wrapper],
}

/// One `flatten;` wrapper a field is reached through.
///
/// A flattened rule has no value of its own: its fields are served as entries of the map its
/// use site is, so reading one means descending into the wrapper's node first. Hoisting is
/// transitive, which is why a field carries a path and not a single label.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Wrapper {
    /// The wrapper's own CST label in the node above it.
    pub label: &'static str,
    /// Whether that label's use site is optional: an absent optional wrapper means a field
    /// with nothing in it; an absent required wrapper is a missing-child error.
    pub optional: bool,
}

/// What a field's children add up to.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Container {
    /// Exactly one child. An absent one leaves the field out of the map, so a target that
    /// requires it reports serde's own missing-field error.
    Single,
    /// At most one child; absent leaves the field out of the map.
    Optional,
    /// Any number of children, served as a sequence — always present, empty when there are
    /// none, so a `Vec` target needs no `#[serde(default)]`.
    Collection,
    /// Whether an optional labeled literal was written: a `bool`, always present.
    Presence,
    /// Any number of children whose rule declares a key, served as either a map or a
    /// sequence — whichever the target asks for.
    Map(Key),
}

/// What keys a [`Container::Map`] field: one field of the element rule, which each element
/// carries as an ordinary child.
///
/// Which of the two forms a keyed field takes is the target's choice, and the key is where they
/// differ: a map target is served one entry per key, and its values leave the key field out —
/// repeating it inside the value would collide with `deny_unknown_fields` and say the same
/// thing twice. A sequence target is served the plain elements, key field included.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Key {
    /// The element field holding it, which is the name it is served under in the sequence
    /// form and the one left out of the map form's values.
    pub name: &'static str,
    /// The CST label the key child carries on an element node.
    pub label: &'static str,
    /// The type the sidecar resolved for the key field, which decides both what makes two
    /// elements duplicates and what the map form's keys are served as.
    pub kind: KeyKind,
    /// Whether elements sharing a key accumulate: the map form's values are then sequences of
    /// elements, and a repeated key is grouping rather than a redefinition.
    pub multi: bool,
}

/// The declared type of a keyed field's key: text, or one of the integer coercions.
///
/// This is the one place the serde path reads a `type:` coercion, and it is not a target
/// preference but the key's identity: two elements are the same key when their key children
/// mean the same value under this type, which has to be settled before any target sees a key.
/// A text key is two keys where `7` and `007` are written; an integer key is one. No runtime
/// case exists beyond these; a float or any other coercion on a key field is refused at
/// generation time before a `Shape` is emitted.
///
/// A key is served from its declared type too, never sniffed from the target: a target whose
/// key type disagrees gets serde's own invalid-type error at the key child rather than a
/// silent fall-back to text.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum KeyKind {
    /// The key child's source text.
    Text,
    /// `type: i8;` on the key field.
    I8,
    /// `type: i16;` on the key field.
    I16,
    /// `type: i32;` on the key field.
    I32,
    /// `type: i64;` on the key field.
    I64,
    /// `type: u8;` on the key field.
    U8,
    /// `type: u16;` on the key field.
    U16,
    /// `type: u32;` on the key field.
    U32,
    /// `type: u64;` on the key field.
    U64,
}

/// One child of a node, as the Deserializer reads it.
#[derive(Clone)]
pub enum Child {
    /// A terminal's span: the source text a scalar target is read from.
    Text(Span),
    /// A referenced rule's node.
    Node(Node),
}

impl Child {
    /// Where this child is, which is where an error about its value is reported.
    pub(crate) fn span(&self) -> Span {
        match self {
            Child::Text(span) => span.clone(),
            Child::Node(node) => node.span(),
        }
    }
}

impl fmt::Debug for Child {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Child::Text(span) => f.debug_tuple("Text").field(span).finish(),
            Child::Node(node) => f.debug_tuple("Node").field(node).finish(),
        }
    }
}

/// What a generated module implements for each of its CST node types.
///
/// The two accessors take the node's data struct — the caller holds the read guard.
pub trait NodeShape: Sized + 'static {
    /// How this rule's nodes are served.
    fn shape() -> &'static Shape;

    /// The node's own span.
    fn node_span(&self) -> Span;

    /// The node's children, in source order, each with the label it carries.
    ///
    /// Unlabeled children — trivia and `$`-included literals — may be dropped or handed over
    /// as `None`; the Deserializer serves labeled children only, so either is the same to it.
    fn labeled_children(&self) -> Vec<(Option<&'static str>, Child)>;
}

/// The erased half of [`NodeShape`]: one object-safe view over a `Shared<T>` handle.
trait Erased {
    fn shape(&self) -> &'static Shape;
    fn span(&self) -> Span;
    fn children(&self) -> Vec<(Option<&'static str>, Child)>;
    fn carried(&self) -> Carried;
}

impl<T: NodeShape> Erased for Shared<T> {
    fn shape(&self) -> &'static Shape {
        T::shape()
    }

    fn span(&self) -> Span {
        self.read().node_span()
    }

    fn children(&self) -> Vec<(Option<&'static str>, Child)> {
        self.read().labeled_children()
    }

    /// The handle itself, for a `Raw<T>` target and for a generated AST type's conversion: an
    /// `Arc` clone, so holding or converting a subtree copies nothing.
    fn carried(&self) -> Carried {
        Carried::new(T::shape().rule, self.clone())
    }
}

/// A CST node of some rule, with everything the Deserializer asks of it.
#[derive(Clone)]
pub struct Node(Rc<dyn Erased>);

impl Node {
    /// Hold one generated CST node handle.
    pub fn new<T: NodeShape>(node: Shared<T>) -> Self {
        Node(Rc::new(node))
    }

    /// The rule this node is an instance of.
    pub fn rule(&self) -> &'static str {
        self.0.shape().rule
    }

    /// How this node is served.
    pub(crate) fn shape(&self) -> &'static Shape {
        self.0.shape()
    }

    /// Where this node is in the source.
    pub(crate) fn span(&self) -> Span {
        self.0.span()
    }

    /// The node's labeled children, in source order.
    pub(crate) fn children(&self) -> Vec<(Option<&'static str>, Child)> {
        self.0.children()
    }

    /// This node's handle, erased: what a `Raw<T>` target takes, and what a generated
    /// `from_cst` is run over.
    pub(crate) fn carried(&self) -> Carried {
        self.0.carried()
    }
}

impl fmt::Debug for Node {
    /// The rule only: printing the subtree would recurse to a depth the source decides.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_tuple("Node").field(&self.rule()).finish()
    }
}
