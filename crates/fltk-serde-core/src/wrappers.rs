//! The two wrapper types, and the magic newtype-struct names they are recognized by.
//!
//! Both are justified by the same criterion: they carry what a grammar cannot produce as
//! content. A source position is not in the text, and a subtree kept *as* syntax is a refusal
//! to deserialize at all.

use std::any::type_name;
use std::fmt;
use std::marker::PhantomData;
use std::ops::Deref;

use fltk_ast_core::AstError;
use fltk_cst_core::{Shared, Span};
use serde::de::{Deserializer, Error as _, Visitor};
use serde::Deserialize;

use crate::channel::{self, Payload};

/// The newtype-struct name [`Spanned`] asks to be deserialized as.
///
/// A generated Deserializer that sees this name provides the current value's span and
/// re-enters the visitor. The `$`-prefixed spelling is the `toml::Spanned` convention: no
/// grammar rule and no consumer struct can produce it, so the name cannot be claimed by
/// accident.
pub const SPANNED_NAME: &str = "$__fltk_private_Spanned";

/// The newtype-struct name [`Raw`] asks to be deserialized as.
pub const RAW_NAME: &str = "$__fltk_private_Raw";

/// The prefix of the per-rule newtype-struct names a generated AST type's `Deserialize` impl
/// asks for; the rule name follows (`$__fltk_private_ast::expr`).
///
/// Generated code writes the whole name as a literal constant. The prefix is exported so a
/// Deserializer can recognize the family and report a rule it has no AST type for.
pub const AST_NAME_PREFIX: &str = "$__fltk_private_ast::";

/// Why the payload a wrapper needs can be missing, which is not only "this Deserializer is not
/// FLTK's".
///
/// serde's derive buffers a value into its own representation and re-deserializes it from there
/// wherever it cannot know the target up front: every field of a `#[serde(flatten)]`ed struct,
/// and every variant of an untagged enum. That representation carries no newtype-struct name, so
/// the magic name never reaches the Deserializer even where the source is FLTK's and the call is
/// one `from_str`. Naming both causes is the difference between a message the consumer can act
/// on and one that diagnoses the wrong problem.
pub(crate) const FOREIGN: &str = "requires deserializing directly from FLTK source: neither a \
     foreign Deserializer nor an adapter that buffers the value first (`#[serde(flatten)]`, \
     untagged enums) carries the protocol it rides on";

/// A deserialized value plus the span of the source text it was read from.
///
/// Fields opt in one at a time (`name: Spanned<String>`), so a target that wants positions
/// for diagnostics pays for them only where it wants them. [`Deref`] to `T` keeps the rest of
/// the consumer's code reading as if the wrapper were not there.
///
/// # Equality
///
/// Two `Spanned` values are equal when their values are, whatever their spans — the same
/// doctrine the generated AST types follow. A value read from two different files is the same
/// value.
#[derive(Debug, Clone)]
pub struct Spanned<T> {
    value: T,
    span: Span,
}

impl<T> Spanned<T> {
    /// Pair a value with a span.
    pub fn new(value: T, span: Span) -> Self {
        Spanned { value, span }
    }

    /// The wrapped value.
    pub fn value(&self) -> &T {
        &self.value
    }

    /// The wrapped value, mutably.
    pub fn value_mut(&mut self) -> &mut T {
        &mut self.value
    }

    /// Discard the span and take the value.
    pub fn into_value(self) -> T {
        self.value
    }

    /// Where the value was read from.
    pub fn span(&self) -> &Span {
        &self.span
    }
}

impl<T> Deref for Spanned<T> {
    type Target = T;

    fn deref(&self) -> &T {
        &self.value
    }
}

impl<T: PartialEq> PartialEq for Spanned<T> {
    fn eq(&self, other: &Self) -> bool {
        self.value == other.value
    }
}

impl<T: Eq> Eq for Spanned<T> {}

impl<'de, T: Deserialize<'de>> Deserialize<'de> for Spanned<T> {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        deserializer.deserialize_newtype_struct(SPANNED_NAME, SpannedVisitor(PhantomData))
    }
}

struct SpannedVisitor<T>(PhantomData<fn() -> T>);

impl<'de, T: Deserialize<'de>> Visitor<'de> for SpannedVisitor<T> {
    type Value = Spanned<T>;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("a value read from FLTK source")
    }

    /// The span is taken before `T` is deserialized: `T` may itself provide payloads, and the
    /// one belonging to this frame is on top only until it does.
    fn visit_newtype_struct<D: Deserializer<'de>>(self, deserializer: D) -> Result<Self::Value, D::Error> {
        let span = channel::take_span().ok_or_else(|| D::Error::custom(format!("Spanned<T> {FOREIGN}")))?;
        Ok(Spanned {
            value: T::deserialize(deserializer)?,
            span,
        })
    }
}

/// A subtree kept as CST rather than deserialized: full fidelity, source-backed spans, and
/// re-entered later through a generated `from_<rule>_cst` entry point.
///
/// The motivating shape is "define now, expand later" content — template and macro bodies,
/// which are syntax the consumer wants to hold rather than interpret at parse time. It cannot
/// be done by re-encoding the way `serde_json::RawValue` holds text, because the CST is what
/// deserialization reads *from*; the node handle is what gets held, and cloning it is an `Arc`
/// clone.
///
/// Like `RawValue`, this works only under FLTK's own Deserializer.
pub struct Raw<T> {
    node: Shared<T>,
}

impl<T> Raw<T> {
    /// Hold a node.
    pub fn new(node: Shared<T>) -> Self {
        Raw { node }
    }

    /// The held node.
    pub fn node(&self) -> &Shared<T> {
        &self.node
    }

    /// Take the held node, to feed a `from_<rule>_cst` entry point.
    pub fn into_node(self) -> Shared<T> {
        self.node
    }
}

impl<T> Clone for Raw<T> {
    /// Shallow, like the handle it wraps: both `Raw`s then name one node.
    fn clone(&self) -> Self {
        Raw {
            node: self.node.clone(),
        }
    }
}

impl<T: PartialEq> PartialEq for Raw<T> {
    /// Deep CST equality, through `Shared`'s own pointer-first comparison.
    fn eq(&self, other: &Self) -> bool {
        self.node == other.node
    }
}

impl<T: Eq> Eq for Raw<T> {}

impl<T: fmt::Debug> fmt::Debug for Raw<T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_tuple("Raw").field(&self.node).finish()
    }
}

impl<'de, T: 'static> Deserialize<'de> for Raw<T> {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        deserializer.deserialize_newtype_struct(RAW_NAME, RawVisitor(PhantomData))
    }
}

struct RawVisitor<T>(PhantomData<fn() -> T>);

impl<'de, T: 'static> Visitor<'de> for RawVisitor<T> {
    type Value = Raw<T>;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "an FLTK `{}` node", type_name::<T>())
    }

    /// The node arrives on the side channel, so the deserializer positioned at it is never
    /// walked — that is the whole point of the type.
    fn visit_newtype_struct<D: Deserializer<'de>>(self, _deserializer: D) -> Result<Self::Value, D::Error> {
        let carried =
            channel::take_node().ok_or_else(|| D::Error::custom(format!("Raw<{}> {FOREIGN}", type_name::<T>())))?;
        let rule = carried.rule().to_string();
        carried.downcast::<Shared<T>>().map(Raw::new).map_err(|_| {
            D::Error::custom(format!(
                "expected a `{}` node for Raw, found rule `{rule}`",
                type_name::<T>()
            ))
        })
    }
}

/// The whole body of the `Deserialize` impl a generated AST type gets.
///
/// A field declared as a generated AST type (`body: ast::Expr`) is then spelled like every other
/// serde field, and what it means is `from_cst` — so folds, transparent chains, coercions and
/// every future AST behavior come along with no shape logic duplicated on this path.
///
/// `name` is the rule's magic newtype-struct name, whose suffix is the rule; `from_cst` is the
/// generated conversion, handed to the Deserializer through the side channel because only the
/// Deserializer knows which node this position holds. Where nothing takes the conversion — a
/// foreign Deserializer, or one of the buffering adapters [`FOREIGN`] names — the impl fails
/// loudly; that is `Raw`'s caveat, for the same reason.
///
/// A `name` without the [`AST_NAME_PREFIX`] is a broken protocol string rather than either of
/// those, and is refused as one: no Deserializer would recognize it, so letting it through would
/// report the mismatch as a missing payload while sitting on an FLTK Deserializer.
pub fn deserialize_ast<'de, D, C, T>(
    deserializer: D,
    name: &'static str,
    from_cst: fn(&Shared<C>) -> Result<T, AstError>,
) -> Result<T, D::Error>
where
    D: Deserializer<'de>,
    C: 'static,
    T: 'static,
{
    let Some(rule) = name.strip_prefix(AST_NAME_PREFIX) else {
        return Err(D::Error::custom(format!(
            "`{name}` is not an AST newtype-struct name: it must begin with `{AST_NAME_PREFIX}`"
        )));
    };
    channel::provide(Payload::conversion(rule, from_cst), || {
        deserializer.deserialize_newtype_struct(name, AstVisitor(PhantomData))
    })
}

struct AstVisitor<T>(PhantomData<fn() -> T>);

impl<'de, T: 'static> Visitor<'de> for AstVisitor<T> {
    type Value = T;

    fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "an FLTK node with the `{}` AST type", type_name::<T>())
    }

    /// The value is already built: the Deserializer ran the conversion this impl handed in, so
    /// the deserializer positioned here is never walked.
    fn visit_newtype_struct<D: Deserializer<'de>>(self, _deserializer: D) -> Result<Self::Value, D::Error> {
        let carried =
            channel::take_ast().ok_or_else(|| D::Error::custom(format!("`{}` {FOREIGN}", type_name::<T>())))?;
        carried.downcast::<T>().map_err(|carried| {
            D::Error::custom(format!(
                "expected the AST value of `{}`, found one of rule `{}`",
                type_name::<T>(),
                carried.rule()
            ))
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::channel::Payload;
    use crate::DeserializeError;
    use fltk_cst_core::SourceText;
    use serde::forward_to_deserialize_any;

    #[derive(Debug, PartialEq)]
    struct Node(u32);

    #[derive(Debug, PartialEq)]
    struct OtherNode;

    /// The generated Deserializer's protocol half, in miniature: it answers every scalar with
    /// one text and recognizes the two magic names.
    #[derive(Clone)]
    struct MockDe {
        span: Span,
        node: Shared<Node>,
        text: &'static str,
    }

    impl MockDe {
        fn new(text: &'static str) -> Self {
            let source = SourceText::from_str("first\nsecond", None);
            MockDe {
                span: Span::new_with_source(6, 12, &source),
                node: Shared::new(Node(9)),
                text,
            }
        }
    }

    impl<'de> Deserializer<'de> for MockDe {
        type Error = DeserializeError;

        fn deserialize_any<V: Visitor<'de>>(self, visitor: V) -> Result<V::Value, Self::Error> {
            visitor.visit_str(self.text)
        }

        fn deserialize_newtype_struct<V: Visitor<'de>>(
            self,
            name: &'static str,
            visitor: V,
        ) -> Result<V::Value, Self::Error> {
            if name.starts_with(AST_NAME_PREFIX) {
                let conversion = channel::take_conversion().expect("an AST impl provides its conversion");
                let carried = crate::Carried::new("node", self.node.clone());
                let built = conversion.run(carried).map_err(DeserializeError::from)?;
                return channel::provide(Payload::Ast(built), move || visitor.visit_newtype_struct(self));
            }
            let payload = match name {
                SPANNED_NAME => Some(Payload::span(self.span.clone())),
                RAW_NAME => Some(Payload::node("node", self.node.clone())),
                _ => None,
            };
            match payload {
                Some(payload) => channel::provide(payload, move || visitor.visit_newtype_struct(self)),
                None => visitor.visit_newtype_struct(self),
            }
        }

        forward_to_deserialize_any! {
            bool i8 i16 i32 i64 i128 u8 u16 u32 u64 u128 f32 f64 char str string bytes
            byte_buf option unit unit_struct seq tuple tuple_struct map struct enum
            identifier ignored_any
        }
    }

    #[test]
    fn spanned_carries_the_provided_span_and_value() {
        let spanned: Spanned<String> = Spanned::deserialize(MockDe::new("hello")).unwrap();
        assert_eq!(*spanned, "hello");
        assert_eq!(spanned.span().start(), 6);
        assert_eq!(spanned.span().line_col_inner().unwrap().line, 1);
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn spanned_equality_ignores_the_span() {
        let positioned = Spanned::new("x".to_string(), Span::new_sourceless(0, 1));
        let elsewhere = Spanned::new("x".to_string(), Span::new_sourceless(9, 10));
        let different = Spanned::new("y".to_string(), Span::new_sourceless(0, 1));
        assert_eq!(positioned, elsewhere);
        assert_ne!(positioned, different);
    }

    #[test]
    fn spanned_accessors_reach_the_value() {
        let mut spanned = Spanned::new(1u32, Span::unknown());
        assert_eq!(*spanned.value(), 1);
        *spanned.value_mut() = 2;
        assert_eq!(spanned.into_value(), 2);
    }

    #[test]
    fn raw_holds_the_provided_node() {
        let de = MockDe::new("ignored");
        let held = de.node.clone();
        let raw: Raw<Node> = Raw::deserialize(de).unwrap();
        assert!(raw.node().ptr_eq(&held));
        assert_eq!(*raw.into_node().read(), Node(9));
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn raw_at_a_wrong_rule_position_names_both_types() {
        let error = Raw::<OtherNode>::deserialize(MockDe::new("ignored")).unwrap_err();
        assert!(error.message.contains("found rule `node`"), "{}", error.message);
        assert!(error.message.contains("OtherNode"), "{}", error.message);
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn nested_wrappers_take_their_own_payloads() {
        let spanned: Spanned<Raw<Node>> = Spanned::deserialize(MockDe::new("ignored")).unwrap();
        assert_eq!(spanned.span().start(), 6);
        assert_eq!(*spanned.node().read(), Node(9));
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn raw_equality_is_deep() {
        let one: Raw<Node> = Raw::new(Shared::new(Node(1)));
        let same: Raw<Node> = Raw::new(Shared::new(Node(1)));
        let other: Raw<Node> = Raw::new(Shared::new(Node(2)));
        assert_eq!(one, same);
        assert_ne!(one, other);
        assert!(one.clone().node().ptr_eq(one.node()));
    }

    #[test]
    fn spanned_under_a_foreign_deserializer_fails_loudly() {
        let error = serde_json::from_str::<Spanned<u32>>("1").unwrap_err();
        assert!(error.to_string().contains(&format!("Spanned<T> {FOREIGN}")), "{error}");
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn a_spanned_field_under_a_foreign_deserializer_fails_loudly() {
        #[derive(Debug, Deserialize)]
        struct Config {
            #[allow(dead_code)]
            name: Spanned<String>,
        }
        let error = serde_json::from_str::<Config>(r#"{"name": "x"}"#).unwrap_err();
        assert!(error.to_string().contains(&format!("Spanned<T> {FOREIGN}")), "{error}");
    }

    #[test]
    fn raw_under_a_foreign_deserializer_fails_loudly() {
        let error = serde_json::from_str::<Raw<Node>>("1").unwrap_err();
        assert!(error.to_string().contains(FOREIGN), "{error}");
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn the_missing_payload_message_names_buffering_as_well_as_a_foreign_deserializer() {
        // The consumer whose Deserializer *is* FLTK's and who still lands here reached it
        // through a buffering adapter, so the message has to name that cause too.
        assert!(FOREIGN.contains("#[serde(flatten)]"), "{FOREIGN}");
        assert!(FOREIGN.contains("untagged"), "{FOREIGN}");
    }

    const NODE_AST_NAME: &str = "$__fltk_private_ast::node";
    const OTHER_AST_NAME: &str = "$__fltk_private_ast::other";

    /// A generated AST type and the `from_cst` behind it, in miniature.
    #[derive(Debug, PartialEq)]
    struct Built(u32);

    fn build(node: &Shared<Node>) -> Result<Built, AstError> {
        Ok(Built(node.read().0 + 1))
    }

    impl<'de> Deserialize<'de> for Built {
        fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
            deserialize_ast(deserializer, NODE_AST_NAME, build)
        }
    }

    /// The same, for a rule whose nodes are never at the position the mock serves.
    #[derive(Debug, PartialEq)]
    struct BuiltElsewhere(u32);

    fn build_elsewhere(_node: &Shared<OtherNode>) -> Result<BuiltElsewhere, AstError> {
        Ok(BuiltElsewhere(0))
    }

    impl<'de> Deserialize<'de> for BuiltElsewhere {
        fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
            deserialize_ast(deserializer, OTHER_AST_NAME, build_elsewhere)
        }
    }

    #[test]
    fn an_ast_target_is_built_by_the_deserializer_and_handed_back() {
        let built = Built::deserialize(MockDe::new("ignored")).unwrap();
        assert_eq!(built, Built(10));
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn an_ast_target_at_another_rules_position_names_both_rules() {
        let error = BuiltElsewhere::deserialize(MockDe::new("ignored")).unwrap_err();
        assert_eq!(
            error.message,
            "expected a `other` node for its AST type, found rule `node`"
        );
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn a_conversion_failure_keeps_the_span_from_cst_raised_it_at() {
        fn refuse(_node: &Shared<Node>) -> Result<Built, AstError> {
            Err(AstError::new("rule \"node\": nope", Span::new_sourceless(2, 5)))
        }
        #[derive(Debug)]
        struct Refused;
        impl<'de> Deserialize<'de> for Refused {
            fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
                deserialize_ast(deserializer, NODE_AST_NAME, refuse).map(|_: Built| Refused)
            }
        }

        let error = Refused::deserialize(MockDe::new("ignored")).unwrap_err();
        assert_eq!(error.message, "rule \"node\": nope");
        assert_eq!(error.span, Span::new_sourceless(2, 5));
    }

    #[test]
    fn an_ast_target_under_a_spanned_takes_its_own_payload() {
        let spanned: Spanned<Built> = Spanned::deserialize(MockDe::new("ignored")).unwrap();
        assert_eq!(*spanned.value(), Built(10));
        assert_eq!(spanned.span().start(), 6);
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn an_unprefixed_ast_name_names_the_malformed_protocol_string() {
        #[derive(Debug)]
        struct Malformed;
        impl<'de> Deserialize<'de> for Malformed {
            fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
                deserialize_ast(deserializer, "node", build).map(|_: Built| Malformed)
            }
        }

        let error = Malformed::deserialize(MockDe::new("ignored")).unwrap_err();
        assert_eq!(
            error.message,
            "`node` is not an AST newtype-struct name: it must begin with `$__fltk_private_ast::`"
        );
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn an_ast_target_under_a_foreign_deserializer_fails_loudly() {
        let error = serde_json::from_str::<Built>("1").unwrap_err();
        assert!(error.to_string().contains(FOREIGN), "{error}");
        assert_eq!(channel::depth(), 0);
    }

    /// A Deserializer holding up the protocol's other half wrongly: it runs the conversion and
    /// then answers with a value of some other rule's type.
    ///
    /// Generated code cannot produce this — `deserialize_ast` pairs `T` with the `from_cst`
    /// that builds it — but the protocol is public, so the visitor's downcast is what keeps a
    /// Deserializer that does produce it from handing the target a wrong value.
    #[derive(Clone, Copy)]
    struct WrongValueDe;

    impl<'de> Deserializer<'de> for WrongValueDe {
        type Error = DeserializeError;

        fn deserialize_any<V: Visitor<'de>>(self, _visitor: V) -> Result<V::Value, Self::Error> {
            Err(DeserializeError::custom("nothing but the AST protocol is served"))
        }

        fn deserialize_newtype_struct<V: Visitor<'de>>(
            self,
            _name: &'static str,
            visitor: V,
        ) -> Result<V::Value, Self::Error> {
            channel::take_conversion().expect("an AST impl provides its conversion");
            let built = crate::Carried::new("other", BuiltElsewhere(0));
            channel::provide(Payload::Ast(built), move || visitor.visit_newtype_struct(self))
        }

        forward_to_deserialize_any! {
            bool i8 i16 i32 i64 i128 u8 u16 u32 u64 u128 f32 f64 char str string bytes
            byte_buf option unit unit_struct seq tuple tuple_struct map struct enum
            identifier ignored_any
        }
    }

    #[test]
    fn an_ast_value_of_another_rules_type_is_refused_rather_than_handed_over() {
        let error = Built::deserialize(WrongValueDe).unwrap_err();
        assert_eq!(
            error.message,
            format!(
                "expected the AST value of `{}`, found one of rule `other`",
                type_name::<Built>()
            )
        );
        assert_eq!(channel::depth(), 0);
    }

    #[test]
    fn the_magic_names_are_unclaimable_spellings() {
        for name in [SPANNED_NAME, RAW_NAME, AST_NAME_PREFIX] {
            assert!(name.starts_with("$__fltk_private_"), "{name}");
        }
    }
}
