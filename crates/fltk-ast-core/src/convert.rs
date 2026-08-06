use crate::error::AstError;

/// Convert a CST node into an AST value.
///
/// Generated converters are inherent associated functions (`Entry::from_cst`), not impls of
/// this trait — the trait is the escape hatch a `custom(...)` rule uses: the generator emits
/// no type and no converter for such a rule, and the containing rule's converter reaches the
/// user's type through here.
///
/// The CST node type is a parameter rather than an associated type so one AST type can be
/// built from more than one rule's node, and so the impl is legal for a foreign value type:
/// `C` is local to the crate writing the impl.
pub trait FromCst<C>: Sized {
    /// Build the AST value, or explain why the node cannot produce one.
    fn from_cst(cst: &C) -> Result<Self, AstError>;
}

/// Synthesize a CST node from an AST value — the reverse of [`FromCst`], and the other half
/// of what a `custom(...)` rule's type must provide.
///
/// The node this produces is fed to the generated formatter, so it must carry exactly the
/// children the parser would have produced for the rule.
pub trait ToCst<C> {
    /// Build the CST node, or explain why the value cannot produce one.
    fn to_cst(&self) -> Result<C, AstError>;
}

#[cfg(test)]
mod tests {
    use super::*;
    use fltk_cst_core::Span;

    /// A stand-in for a generated CST node: the text a terminal matched.
    struct Word(String);

    /// A stand-in for a `custom(...)` rule's user type, holding the reversed lexeme so a
    /// round trip through both traits proves each direction ran.
    #[derive(Debug, PartialEq)]
    struct Flipped(String);

    impl FromCst<Word> for Flipped {
        fn from_cst(cst: &Word) -> Result<Self, AstError> {
            if cst.0.is_empty() {
                return Err(AstError::new("rule 'word': empty", Span::unknown()));
            }
            Ok(Flipped(cst.0.chars().rev().collect()))
        }
    }

    impl ToCst<Word> for Flipped {
        fn to_cst(&self) -> Result<Word, AstError> {
            Ok(Word(self.0.chars().rev().collect()))
        }
    }

    /// The traits carry no logic of their own, so the only thing there is to assert about
    /// them is that the two bounds compose and that `C`-as-a-parameter admits a foreign
    /// value type, which is the stated reason for the parameter.
    #[test]
    fn the_traits_are_reachable_through_generic_code() {
        fn round_trip<C, T: FromCst<C> + ToCst<C>>(node: &C) -> Result<C, AstError> {
            T::from_cst(node)?.to_cst()
        }
        assert_eq!(round_trip::<Word, Flipped>(&Word("xy".to_string())).unwrap().0, "xy");
    }
}
