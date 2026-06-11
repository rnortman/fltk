use std::fmt;

/// Error type for native (GIL-free) CST accessor operations.
///
/// Returned by `child_<lbl>`, `maybe_<lbl>`, and the generic `child()` accessors
/// when the tree is structurally malformed (wrong child count) or when a child stored
/// under a label has an unexpected variant type.
///
/// Generated Python pymethods do NOT route through this type — they keep direct
/// `PyErr` construction to avoid churning Python error messages.
///
/// `#[non_exhaustive]` allows future variants without breaking downstream match arms.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum CstError {
    /// Wrong number of children match the given label.
    ///
    /// `label`: the label string (e.g. `"name"`).
    /// `expected`: the expected count (e.g. `"1"` or `"0 or 1"`).
    /// `found`: the actual count of children whose label field matched.
    ChildCount {
        /// The label being queried (static string from generated code).
        label: &'static str,
        /// Human-readable expected quantity (e.g. `"1"`, `"0 or 1"`).
        expected: &'static str,
        /// The actual count of label-matching children.
        found: usize,
    },

    /// A child's variant type did not match the expected single-typed label.
    ///
    /// Only reachable when the tree has been mutated via the generic `push_child`/
    /// `append` mutators to store a variant of the wrong type under a single-typed label.
    /// Count is valid (exactly the expected number of label-matching children) when this
    /// error is returned — `ChildCount` always takes priority when both would apply.
    UnexpectedChildType {
        /// The label being queried.
        label: &'static str,
    },
}

impl fmt::Display for CstError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CstError::ChildCount {
                label,
                expected,
                found,
            } => write!(
                f,
                "Expected {expected} {label} child(ren) but have {found}"
            ),
            CstError::UnexpectedChildType { label } => {
                write!(f, "Child stored under label '{label}' has an unexpected type")
            }
        }
    }
}

impl std::error::Error for CstError {}
