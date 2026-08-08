//! The side channel: how a generated Deserializer hands a value to a `Deserialize` impl that
//! serde's data model has no room for.
//!
//! serde's `Deserializer` API can pass a wrapper type nothing but data-model values, and a
//! source span, a CST node handle and an already-built AST value are none of those. The
//! established answer (`toml::Spanned`, `serde_json::RawValue`) is a magic newtype-struct
//! name the paired Deserializer recognizes; what it recognizes the name *with* is this
//! module.
//!
//! The protocol is: the Deserializer sees the magic name, calls [`provide`] with the payload
//! and re-enters the visitor inside the closure, and the visitor calls the matching `take_*`
//! before doing anything else. It is a stack rather than a slot because wrappers nest —
//! `Spanned<Raw<T>>` has two live frames — and takes are LIFO.
//!
//! This module is public because generated code names it, and is the internal protocol
//! between this crate and that generated code rather than a surface to build on.

use std::any::Any;
use std::cell::RefCell;
use std::fmt;

use fltk_ast_core::AstError;
use fltk_cst_core::{Shared, Span};

thread_local! {
    /// One stack per thread. Deserialization is single-threaded within a call, and a payload
    /// is live only between a [`provide`] and the take inside it.
    static CHANNEL: RefCell<Vec<Payload>> = const { RefCell::new(Vec::new()) };
}

/// A value a generated Deserializer hands to the wrapper type positioned at it.
pub enum Payload {
    /// The span of the value the Deserializer is positioned at, for `Spanned<T>`.
    Span(Span),
    /// A cloned CST node handle, for `Raw<T>`.
    Node(Carried),
    /// A value a generated `from_cst` produced, for a generated AST type's `Deserialize`.
    Ast(Carried),
    /// A generated `from_cst` itself, travelling the other way: an AST type's `Deserialize`
    /// hands it in, and the Deserializer runs it over the node it is positioned at.
    Conversion(Conversion),
}

impl Payload {
    /// A span payload.
    pub fn span(span: Span) -> Self {
        Payload::Span(span)
    }

    /// A CST node payload. `rule` names the grammar rule the node is an instance of, which is
    /// what a type mismatch is reported against.
    pub fn node<T: 'static>(rule: impl Into<String>, handle: Shared<T>) -> Self {
        Payload::Node(Carried::new(rule, handle))
    }

    /// An AST value payload, named by the rule whose AST type it is.
    pub fn ast<T: 'static>(rule: impl Into<String>, value: T) -> Self {
        Payload::Ast(Carried::new(rule, value))
    }

    /// A conversion payload: one rule's generated `from_cst`, erased.
    pub fn conversion<C: 'static, T: 'static>(
        rule: &'static str,
        from_cst: fn(&Shared<C>) -> Result<T, AstError>,
    ) -> Self {
        Payload::Conversion(Conversion::new(rule, from_cst))
    }
}

impl fmt::Debug for Payload {
    /// Payload contents are type-erased and need not be `Debug`, so a payload prints as its
    /// kind and, where it has one, the rule it came from.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Payload::Span(span) => write!(f, "Payload::Span({span:?})"),
            Payload::Node(carried) => write!(f, "Payload::Node({})", carried.rule),
            Payload::Ast(carried) => write!(f, "Payload::Ast({})", carried.rule),
            Payload::Conversion(conversion) => write!(f, "Payload::Conversion({})", conversion.rule),
        }
    }
}

/// One rule's generated `from_cst`, with its CST node type and its result type erased.
///
/// The one payload that travels toward the Deserializer rather than away from it: a
/// `Deserialize` impl hands the conversion in, and the Deserializer runs it over the node
/// it is positioned at. A failure is still an [`AstError`] carrying its own span, so the
/// diagnostic is the AST layer's own.
pub struct Conversion {
    /// The rule whose AST type this builds.
    rule: &'static str,
    convert: Box<dyn FnOnce(Carried) -> Result<Carried, AstError>>,
}

impl Conversion {
    /// Erase one generated `from_cst`.
    pub fn new<C: 'static, T: 'static>(rule: &'static str, from_cst: fn(&Shared<C>) -> Result<T, AstError>) -> Self {
        Conversion {
            rule,
            convert: Box::new(move |carried: Carried| {
                let node: Shared<C> = carried.downcast().map_err(|carried| {
                    // The node at this position is an instance of another rule, so the AST type
                    // the target named is not the one the tree has there. Unpositioned: the
                    // frame running this holds the span.
                    AstError::new(
                        format!(
                            "expected a `{rule}` node for its AST type, found rule `{}`",
                            carried.rule()
                        ),
                        Span::unknown(),
                    )
                })?;
                from_cst(&node).map(|value| Carried::new(rule, value))
            }),
        }
    }

    /// The rule whose AST type this builds.
    pub fn rule(&self) -> &'static str {
        self.rule
    }

    /// Run the conversion over one CST node payload, and carry the value it built.
    pub fn run(self, node: Carried) -> Result<Carried, AstError> {
        (self.convert)(node)
    }
}

impl fmt::Debug for Conversion {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Conversion").field("rule", &self.rule).finish()
    }
}

/// A type-erased payload value plus the rule it came from.
pub struct Carried {
    rule: String,
    value: Box<dyn Any>,
}

impl fmt::Debug for Carried {
    /// The carried value is type-erased and need not be `Debug`, so only the rule prints.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Carried").field("rule", &self.rule).finish()
    }
}

impl Carried {
    /// Erase one value, named by the rule it came from.
    ///
    /// Crate-internal: the invariant that `rule` names the boxed value's own rule is what every
    /// downcast diagnostic rests on, and the constructors reaching generated code
    /// ([`Payload::node`], [`Payload::ast`], `NodeShape`'s erasure) establish it themselves.
    pub(crate) fn new<T: 'static>(rule: impl Into<String>, value: T) -> Self {
        Carried {
            rule: rule.into(),
            value: Box::new(value),
        }
    }

    /// The grammar rule the carried value came from, for diagnostics.
    pub fn rule(&self) -> &str {
        &self.rule
    }

    /// Recover the carried value, or hand the payload back untouched so the caller can name
    /// the rule it actually got in the error it raises.
    pub fn downcast<T: 'static>(self) -> Result<T, Self> {
        match self.value.downcast::<T>() {
            Ok(value) => Ok(*value),
            Err(value) => Err(Carried { rule: self.rule, value }),
        }
    }
}

/// Make `payload` available to the deserialization `f` performs, then clear it.
///
/// The payload is popped on the way out whether or not `f` took it, and the pop is a
/// truncation to the depth before the push, so an inner frame that returned early through a
/// serde error cannot leave the stack desynchronized for the next one.
pub fn provide<R>(payload: Payload, f: impl FnOnce() -> R) -> R {
    let depth = CHANNEL.with(|channel| {
        let mut stack = channel.borrow_mut();
        stack.push(payload);
        stack.len() - 1
    });
    let _guard = Unwind { depth };
    f()
}

/// Truncates the stack to the depth its frame pushed at, on every exit path including a
/// panic — which is what makes an untaken payload impossible to leak.
struct Unwind {
    depth: usize,
}

impl Drop for Unwind {
    fn drop(&mut self) {
        CHANNEL.with(|channel| channel.borrow_mut().truncate(self.depth));
    }
}

/// Take the innermost payload if it is the requested kind, and leave it alone if it is not.
///
/// A take under a foreign Deserializer finds an empty stack, and a take of the wrong kind
/// finds a payload belonging to an outer frame: both are `None`, and both are a loud error at
/// the caller rather than a silent default.
fn take_if(matches: fn(&Payload) -> bool) -> Option<Payload> {
    CHANNEL.with(|channel| {
        let mut stack = channel.borrow_mut();
        if stack.last().is_some_and(matches) {
            stack.pop()
        } else {
            None
        }
    })
}

/// Take the innermost span payload.
pub fn take_span() -> Option<Span> {
    match take_if(|payload| matches!(payload, Payload::Span(_))) {
        Some(Payload::Span(span)) => Some(span),
        _ => None,
    }
}

/// Take the innermost CST node payload.
pub fn take_node() -> Option<Carried> {
    match take_if(|payload| matches!(payload, Payload::Node(_))) {
        Some(Payload::Node(carried)) => Some(carried),
        _ => None,
    }
}

/// Take the innermost AST value payload.
pub fn take_ast() -> Option<Carried> {
    match take_if(|payload| matches!(payload, Payload::Ast(_))) {
        Some(Payload::Ast(carried)) => Some(carried),
        _ => None,
    }
}

/// Take the innermost conversion payload.
pub fn take_conversion() -> Option<Conversion> {
    match take_if(|payload| matches!(payload, Payload::Conversion(_))) {
        Some(Payload::Conversion(conversion)) => Some(conversion),
        _ => None,
    }
}

/// How many payloads are live on this thread. Test-only: the invariant every path has to
/// restore is that this is zero once the outermost `provide` returns.
#[cfg(test)]
pub(crate) fn depth() -> usize {
    CHANNEL.with(|channel| channel.borrow().len())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Debug, PartialEq)]
    struct Node(u32);

    fn sourceless() -> Span {
        Span::new_sourceless(3, 7)
    }

    #[test]
    fn a_provided_span_is_taken_inside_the_scope() {
        let taken = provide(Payload::span(sourceless()), take_span);
        assert_eq!(taken, Some(sourceless()));
        assert_eq!(depth(), 0);
    }

    #[test]
    fn an_untaken_payload_is_popped_on_the_way_out() {
        provide(Payload::span(sourceless()), || {
            assert_eq!(depth(), 1);
        });
        assert_eq!(depth(), 0);
    }

    #[test]
    fn nested_frames_take_innermost_first() {
        let order = provide(Payload::span(Span::new_sourceless(0, 1)), || {
            provide(Payload::span(Span::new_sourceless(2, 3)), || {
                let inner = take_span().unwrap();
                assert_eq!(depth(), 1);
                inner
            })
        });
        assert_eq!(order, Span::new_sourceless(2, 3));
        assert_eq!(depth(), 0);
    }

    #[test]
    fn an_early_return_from_an_inner_frame_still_pops_it() {
        let result: Result<(), &str> = provide(Payload::span(sourceless()), || {
            provide(Payload::node("expr", Shared::new(Node(1))), || Err("boom"))?;
            Ok(())
        });
        assert_eq!(result, Err("boom"));
        assert_eq!(depth(), 0);
    }

    #[test]
    fn a_take_of_the_wrong_kind_is_none_and_leaves_the_payload() {
        provide(Payload::span(sourceless()), || {
            assert!(take_node().is_none());
            assert!(take_ast().is_none());
            assert_eq!(take_span(), Some(sourceless()));
        });
    }

    #[test]
    fn a_take_with_nothing_provided_is_none() {
        assert!(take_span().is_none());
        assert!(take_node().is_none());
        assert!(take_ast().is_none());
    }

    #[test]
    fn a_node_payload_round_trips_through_its_handle() {
        let node = Shared::new(Node(7));
        let taken = provide(Payload::node("expr", node.clone()), take_node).unwrap();
        assert_eq!(taken.rule(), "expr");
        let recovered: Shared<Node> = taken.downcast().unwrap();
        assert!(recovered.ptr_eq(&node));
    }

    #[test]
    fn a_failed_downcast_hands_the_payload_back_with_its_rule() {
        let taken = provide(Payload::node("expr", Shared::new(Node(7))), take_node).unwrap();
        let returned = taken.downcast::<Shared<u32>>().unwrap_err();
        assert_eq!(returned.rule(), "expr");
        // Still recoverable at its real type: the failed attempt consumed nothing.
        assert_eq!(*returned.downcast::<Shared<Node>>().unwrap().read(), Node(7));
    }

    #[test]
    fn an_ast_payload_carries_a_plain_value() {
        let taken = provide(Payload::ast("expr", Node(4)), take_ast).unwrap();
        assert_eq!(taken.rule(), "expr");
        assert_eq!(taken.downcast::<Node>().unwrap(), Node(4));
    }

    #[test]
    fn node_and_ast_payloads_do_not_answer_for_each_other() {
        provide(Payload::ast("expr", Node(4)), || {
            assert!(take_node().is_none());
        });
        provide(Payload::node("expr", Shared::new(Node(4))), || {
            assert!(take_ast().is_none());
        });
    }

    /// A generated `from_cst`, in miniature.
    fn double(node: &Shared<Node>) -> Result<u32, AstError> {
        Ok(node.read().0 * 2)
    }

    #[test]
    fn a_conversion_runs_over_the_node_it_is_handed() {
        let conversion = provide(Payload::conversion("expr", double), take_conversion).unwrap();
        assert_eq!(conversion.rule(), "expr");
        let node = Payload::node("expr", Shared::new(Node(21)));
        let Payload::Node(carried) = node else {
            panic!("a node payload carries its handle")
        };
        let built = conversion.run(carried).unwrap();
        assert_eq!(built.rule(), "expr");
        assert_eq!(built.downcast::<u32>().unwrap(), 42);
    }

    #[test]
    fn a_conversion_over_another_rules_node_names_both_rules() {
        let conversion = Conversion::new("expr", double);
        let Payload::Node(carried) = Payload::node("stmt", Shared::new(7u32)) else {
            panic!("a node payload carries its handle")
        };
        let error = conversion.run(carried).unwrap_err();
        assert_eq!(error.message, "expected a `expr` node for its AST type, found rule `stmt`");
        // Unpositioned: the Deserializer frame running the conversion is what holds the span.
        assert_eq!(error.span, Span::unknown());
    }

    #[test]
    fn a_conversion_does_not_answer_for_another_payload_kind() {
        provide(Payload::conversion("expr", double), || {
            assert!(take_ast().is_none());
            assert!(take_node().is_none());
            assert!(take_span().is_none());
            assert!(take_conversion().is_some());
        });
        provide(Payload::ast("expr", Node(1)), || {
            assert!(take_conversion().is_none());
        });
    }

    #[test]
    fn payloads_print_their_kind_and_rule() {
        assert_eq!(format!("{:?}", Payload::ast("expr", Node(1))), "Payload::Ast(expr)");
        assert_eq!(
            format!("{:?}", Payload::conversion("expr", double)),
            "Payload::Conversion(expr)"
        );
        assert_eq!(
            format!("{:?}", Payload::node("expr", Shared::new(Node(1)))),
            "Payload::Node(expr)"
        );
        assert!(format!("{:?}", Payload::span(sourceless())).starts_with("Payload::Span("));
    }
}
