//! Covering spans, for positioning a diagnostic over more than one child.

use fltk_cst_core::Span;

/// The smallest span covering every positioned span handed in.
///
/// Unknown spans are skipped rather than merged: the sentinel is `(-1, -1)`, so merging one
/// would move the result's start off the source. Spans from two different sources cannot merge
/// at all, and the span so far is the honest answer there. With nothing positioned to cover,
/// the result is [`Span::unknown`].
///
/// This is the lenient merge a frame positions *itself* with — a wrapper over a collection
/// field, an error about a run of children. It is deliberately not the merge
/// [`fold_left`](crate::fold_left) builds a chain's links with: a span baked into a value must
/// be correct, while a span on a one-off diagnostic can fall back.
pub fn merged_span<I: IntoIterator<Item = Span>>(spans: I) -> Span {
    let unknown = Span::unknown();
    let mut merged: Option<Span> = None;
    for span in spans.into_iter().filter(|span| *span != unknown) {
        merged = Some(match merged {
            None => span,
            Some(so_far) => so_far.merge(&span).unwrap_or(so_far),
        });
    }
    merged.unwrap_or(unknown)
}

#[cfg(test)]
mod tests {
    use fltk_cst_core::SourceText;

    use super::*;

    #[test]
    fn nothing_positioned_covers_nothing() {
        assert_eq!(merged_span([]), Span::unknown());
        assert_eq!(merged_span([Span::unknown(), Span::unknown()]), Span::unknown());
    }

    #[test]
    fn the_cover_runs_from_the_first_start_to_the_last_end() {
        let source = SourceText::from_str("abcdefgh", None);
        let merged = merged_span([
            Span::new_with_source(1, 3, &source),
            Span::new_with_source(5, 7, &source),
        ]);
        assert_eq!(merged.start(), 1);
        assert_eq!(merged.end(), 7);
    }

    #[test]
    fn an_unknown_span_is_skipped_rather_than_merged() {
        let source = SourceText::from_str("abcdefgh", None);
        let merged = merged_span([
            Span::unknown(),
            Span::new_with_source(2, 4, &source),
            Span::unknown(),
        ]);
        assert_eq!(merged.start(), 2);
        assert_eq!(merged.end(), 4);
    }

    #[test]
    fn a_span_from_another_source_leaves_the_cover_so_far() {
        let source = SourceText::from_str("abcdefgh", None);
        let other = SourceText::from_str("abcdefgh", None);
        let merged = merged_span([
            Span::new_with_source(1, 3, &source),
            Span::new_with_source(5, 7, &other),
        ]);
        assert_eq!(merged, Span::new_with_source(1, 3, &source));
    }
}
