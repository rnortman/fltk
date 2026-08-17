//! Synthesis: rebuilding the CST an AST value stands for.
//!
//! `to_cst` walks one alternative's item positions in grammar order and appends exactly what the
//! parser would have appended there. Most of that walk is generated code, because it names the
//! CST node types, labels and child variants of one grammar. What lives here is the part that is
//! the same for every grammar: splitting a terminal-only rule's text back across the items it
//! was read from.
//!
//! A terminal-only rule carries text and nothing else, so the split is the inverse of reading
//! the node's own span: the alternative is spelled as one regex with a capture group per
//! included regex item, and each group's slice becomes a child span carrying its own source.
//! A literal item's text is a grammar constant, so its child carries position only.
//!
//! Every other node form holds fields instead, and the walk hands each field's values to the item
//! positions that can carry them: [`Cursor`] is that distribution, and [`check_group`],
//! [`alternative_fits`], [`filled`], [`check_consumed`], [`hoisted`] and [`wrapper_needed`] are
//! the questions a body asks about values whose shape the grammar cannot accommodate. Each has a
//! counterpart of the same name in `fltk.fegen.pyrt.astrt`, and the message templates are one
//! text under the translation `tests/test_ast_error_message_parity.py` enforces.

use std::fmt::Debug;
use std::sync::OnceLock;

use fltk_cst_core::Span;

use crate::error::AstError;
use crate::terminal::{source_span, TerminalPattern};

/// The upper bound of an item position the grammar sets no limit on.
pub const UNBOUNDED: usize = usize::MAX;

/// One alternative of a terminal-only rule, as a single regex over the node's text.
#[derive(Debug)]
pub struct TerminalAlt {
    /// The whole alternative as one regex, or `None` when its shape is not rebuildable.
    ///
    /// A repeated included item, a sub-expression or a rule reference leaves no determined split:
    /// one regex cannot say which slice of the text each occurrence took.
    pub pattern: Option<&'static str>,

    /// Per included item, in grammar order, the capture group holding that item's text.
    ///
    /// `None` is a literal: its text comes back from the grammar rather than from the value, so
    /// the child it contributes carries position only.
    pub groups: &'static [Option<&'static str>],
}

/// A terminal-only rule's alternatives, compiled on first use.
///
/// [`new`](TerminalShape::new) is `const`, so a generated module declares one `static` per rule
/// and pays for the regex compilation only if something actually serializes that rule.
#[derive(Debug)]
pub struct TerminalShape {
    alternatives: &'static [TerminalAlt],
    compiled: OnceLock<Vec<Option<TerminalPattern>>>,
}

/// Which alternative a node's text came from, and what each of its items takes.
#[derive(Debug, Clone, PartialEq)]
pub struct TerminalSplit {
    /// The index of the matched alternative, in grammar order.
    pub alternative: usize,

    /// One span per included item of that alternative, in grammar order.
    pub spans: Vec<Span>,
}

impl TerminalShape {
    /// Declare the alternatives of one terminal-only rule.
    pub const fn new(alternatives: &'static [TerminalAlt]) -> Self {
        Self {
            alternatives,
            compiled: OnceLock::new(),
        }
    }

    fn compiled(&self) -> &[Option<TerminalPattern>] {
        self.compiled
            .get_or_init(|| {
                self.alternatives
                    .iter()
                    .map(|alternative| alternative.pattern.map(TerminalPattern::new))
                    .collect()
            })
            .as_slice()
    }

    /// Split `text` across the items of the first alternative that matches all of it.
    ///
    /// Alternatives are tried in grammar order, which is the order the parser would have tried
    /// them in, so a text two alternatives could have matched comes back as the one the parse
    /// would have produced.
    pub fn split(&self, text: &str, rule: &str) -> Result<TerminalSplit, AstError> {
        if self.alternatives.iter().all(|alternative| alternative.pattern.is_none()) {
            // Must stay on one line: the parity test matches this template verbatim.
            return Err(AstError::new(
                format!("rule {rule:?}: the rule's shape cannot be rebuilt from text — every alternative holds a repeated terminal, a sub-expression or a rule reference, so no split of the text back into children is determined; restructure the rule or convert it by hand"),
                Span::unknown(),
            ));
        }
        for (index, (alternative, compiled)) in self.alternatives.iter().zip(self.compiled()).enumerate() {
            let Some(pattern) = compiled else {
                continue;
            };
            let regex = pattern.regex();
            let mut captures = regex.create_captures();
            regex.captures(text, &mut captures);
            if !captures.is_match() {
                continue;
            }
            let spans = alternative
                .groups
                .iter()
                .map(|group| match group {
                    // TODO(ast-synthesised-literal-spans): a non-captured piece gets no source,
                    // and the generated text accessors panic on it.
                    None => Span::unknown(),
                    Some(name) => {
                        let matched = captures
                            .get_group_by_name(name)
                            .expect("every group the plan names wraps a required item of the same pattern");
                        source_span(&text[matched.start..matched.end])
                    }
                })
                .collect();
            return Ok(TerminalSplit {
                alternative: index,
                spans,
            });
        }
        Err(AstError::new(
            format!("rule {rule:?}: text {text:?} is not something the rule could have matched"),
            Span::unknown(),
        ))
    }
}

/// One field's values, handed out to the item positions that can carry them.
///
/// Each position takes as many values as its quantifier allows, leaving behind whatever later
/// required positions for the same label still need. A position that can hold only some of the
/// values — one branch of a sub-expression alternation — takes them through
/// [`take_if`](Cursor::take_if), which is how the branches share one label.
#[derive(Debug)]
pub struct Cursor<'a, T: ?Sized> {
    values: Vec<&'a T>,
    position: usize,
}

impl<'a, T: ?Sized> Cursor<'a, T> {
    /// A cursor over one field's values, in the order the field holds them.
    pub fn new(values: Vec<&'a T>) -> Self {
        Self { values, position: 0 }
    }

    /// Up to `maximum` values, leaving `reserve` of them to the positions after this one.
    pub fn take(&mut self, maximum: usize, reserve: usize) -> Vec<&'a T> {
        self.take_if(maximum, reserve, |_value| true)
    }

    /// [`take`](Cursor::take), stopping at the first value this position cannot hold.
    pub fn take_if(&mut self, maximum: usize, reserve: usize, accepts: impl Fn(&T) -> bool) -> Vec<&'a T> {
        let mut taken = Vec::new();
        while taken.len() < maximum && self.remaining() > reserve && accepts(self.values[self.position]) {
            taken.push(self.values[self.position]);
            self.position += 1;
        }
        taken
    }

    /// How many values no position has taken yet.
    pub fn remaining(&self) -> usize {
        self.values.len() - self.position
    }
}

/// One `multi` keyed field's elements, its keys' groups in insertion order.
///
/// Grouping is what the map records, so the elements come out grouped and the source order that
/// interleaved two keys is not recoverable. A key whose group is empty carries no element to
/// render — the key lives on the element, not on the map — so it is refused rather than dropped
/// silently.
pub fn multi_values<'a, K: Debug + 'a, T: 'a>(
    grouped: impl IntoIterator<Item = (&'a K, &'a Vec<T>)>,
    rule: &str,
) -> Result<Vec<&'a T>, AstError> {
    let mut values = Vec::new();
    for (key, elements) in grouped {
        if elements.is_empty() {
            return Err(AstError::new(
                format!("rule {rule:?}: the {key:?} key has no element to render it on"),
                Span::unknown(),
            ));
        }
        values.extend(elements.iter());
    }
    Ok(values)
}

/// The labels of `states` that carry something, for alternative and branch selection.
pub fn populated<'a>(states: &[(&'a str, bool)]) -> Vec<&'a str> {
    states
        .iter()
        .filter(|(_label, state)| *state)
        .map(|(label, _state)| *label)
        .collect()
}

/// Whether an alternative can carry exactly the populated fields.
pub fn alternative_fits(present: &[&str], required: &[&str], labels: &[&str]) -> bool {
    required.iter().all(|label| present.contains(label)) && present.iter().all(|label| labels.contains(label))
}

/// The values an item position took, once its own lower bound is known to be met.
///
/// A required position left empty would put a CST missing a required child in front of the
/// formatter, which can only report that something is wrong with the whole node; the shortfall is
/// the user's data and is named here instead.
pub fn filled(available: usize, minimum: usize, rule: &str, label: &str) -> Result<(), AstError> {
    if available < minimum {
        return Err(AstError::new(
            format!(
                "rule {rule:?}: the grammar needs {minimum} {label:?} value(s) at this position, but {available} were available"
            ),
            Span::unknown(),
        ));
    }
    Ok(())
}

/// Every field value must have found an item position to occupy.
pub fn check_consumed(rule: &str, label: &str, remaining: usize) -> Result<(), AstError> {
    if remaining > 0 {
        return Err(AstError::new(
            format!("rule {rule:?}: the grammar has no place for {remaining} more {label:?} value(s)"),
            Span::unknown(),
        ));
    }
    Ok(())
}

/// No branch of an alternation can carry this value.
///
/// `kind` names the type of the value that arrived, which is what the position rejected: on this
/// backend that is the field's declared Rust type, where the Python backend names the runtime
/// class of the value.
pub fn unplaceable(rule: &str, label: &str, kind: &str) -> AstError {
    AstError::new(
        format!("rule {rule:?}: no item position accepts a {kind} value for {label:?}"),
        Span::unknown(),
    )
}

/// One field a flattened wrapper requires, checked before the wrapper is rebuilt.
pub fn hoisted<'a, T>(value: Option<&'a T>, rule: &str, field: &str) -> Result<&'a T, AstError> {
    value.ok_or_else(|| {
        AstError::new(
            format!(
                "rule {rule:?}: the flattened wrapper needs a {field:?} value, but it is absent; populate it, or leave every field hoisted out of the wrapper empty"
            ),
            Span::unknown(),
        )
    })
}

/// Whether an optional `flatten;` wrapper has to be rebuilt around its hoisted fields.
///
/// The wrapper is what the grammar spells; the AST holds only its contents, so it is emitted
/// exactly when something it would carry is populated. A value whose hoisted fields all sit at
/// their absent defaults therefore renders without the wrapper, as an absent one does.
pub fn wrapper_needed(states: &[bool]) -> bool {
    states.iter().any(|state| *state)
}

/// The generated formatter declined to render a synthesised CST.
///
/// Synthesis appends what the parser would have appended, which is the positional contract the
/// formatter checks, so either the grammar has a shape the formatter cannot rebuild from any CST —
/// in which case parsing the same text and formatting the result fails the same way — or the
/// synthesis itself is wrong.
pub fn unrenderable(rule: &str) -> AstError {
    AstError::new(
        // Must stay on one line: the parity test matches this template verbatim.
        format!("the formatter could not render a synthesised {rule:?} node; either the grammar has a shape the formatter cannot rebuild from a CST — parsing the same text and formatting the result fails the same way — or this is a bug in FLTK's AST synthesis"),
        Span::unknown(),
    )
}

/// One set of labels as a diagnostic spells it: sorted, without repeats, quoted, comma-separated.
///
/// Written out rather than left to `{:?}`, so the rendering is not mistaken for a message template
/// of its own, and so the ordering and the deduplication a diagnostic reports are stated in the one
/// place that decides them: a label two branches of an alternation share is one offer, not two.
fn label_list(labels: &[&str]) -> String {
    let mut sorted: Vec<&str> = labels.to_vec();
    sorted.sort_unstable();
    sorted.dedup();
    let mut rendered = String::from("[");
    for (index, label) in sorted.iter().enumerate() {
        if index > 0 {
            rendered.push_str(", ");
        }
        rendered.push('"');
        rendered.push_str(label);
        rendered.push('"');
    }
    rendered.push(']');
    rendered
}

/// The populated fields of one sub-expression alternation must suit a single branch.
///
/// `branches` is the labels each branch carries. `demanded` says every branch needs a value, so
/// leaving all of them empty renders nothing where the grammar requires something. `exclusive`
/// narrows the second test to the labels this alternation alone can supply: a label the
/// alternative also uses elsewhere may legitimately be populated from there, and a repeatable
/// alternation may draw one label's values from several branches in turn.
pub fn check_group(
    rule: &str,
    present: &[&str],
    branches: &[&[&str]],
    exclusive: &[&str],
    demanded: bool,
) -> Result<(), AstError> {
    if demanded && present.is_empty() {
        let union: Vec<&str> = branches.iter().flat_map(|labels| labels.iter().copied()).collect();
        let offered = label_list(&union);
        return Err(AstError::new(
            format!("rule {rule:?}: the grammar needs one of {offered} at this position, but none is populated"),
            Span::unknown(),
        ));
    }
    let narrowed: Vec<&str> = present.iter().copied().filter(|label| exclusive.contains(label)).collect();
    if narrowed.is_empty() || branches.iter().any(|labels| narrowed.iter().all(|label| labels.contains(label))) {
        return Ok(());
    }
    let offered = branches.iter().map(|labels| label_list(labels)).collect::<Vec<_>>().join(" | ");
    let narrowed = label_list(&narrowed);
    Err(AstError::new(
        format!(
            "rule {rule:?}: {narrowed} cannot come from one branch of this alternation, which carries {offered}; populate the fields of a single branch"
        ),
        Span::unknown(),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// `number := val:/-?[0-9]+/ ;` — one included regex item.
    static NUMBER: TerminalShape = TerminalShape::new(&[TerminalAlt {
        pattern: Some("(?P<g0>-?[0-9]+)"),
        groups: &[Some("g0")],
    }]);

    /// `string_literal := "\"" . content:/[^"]*/ . "\"" ;` — suppressed quotes, so the
    /// pattern carries them and only the content is a child.
    static STRING_LITERAL: TerminalShape = TerminalShape::new(&[TerminalAlt {
        pattern: Some("(?:\")(?P<g0>[^\"]*)(?:\")"),
        groups: &[Some("g0")],
    }]);

    /// `tag := $"#" . name:/[a-z]+/ ;` — an included literal beside an included regex, so the
    /// first child carries position only.
    static TAG: TerminalShape = TerminalShape::new(&[TerminalAlt {
        pattern: Some("(?:#)(?P<g0>[a-z]+)"),
        groups: &[None, Some("g0")],
    }]);

    /// Two alternatives, the first of which also matches a prefix of the second's texts.
    static EITHER: TerminalShape = TerminalShape::new(&[
        TerminalAlt {
            pattern: Some("(?P<g0>[a-z]+)"),
            groups: &[Some("g0")],
        },
        TerminalAlt {
            pattern: Some("(?P<g0>[a-z]+)(?P<g1>[0-9]+)"),
            groups: &[Some("g0"), Some("g1")],
        },
    ]);

    /// A rule whose every alternative holds a repeated included item.
    static UNSPLITTABLE: TerminalShape = TerminalShape::new(&[TerminalAlt {
        pattern: None,
        groups: &[],
    }]);

    /// `parts := p:/[a-z]/* | w:/[0-9]+/ ;` — one alternative a repeated item leaves
    /// unrebuildable, one a single regex spells.
    static MIXED: TerminalShape = TerminalShape::new(&[
        TerminalAlt {
            pattern: None,
            groups: &[],
        },
        TerminalAlt {
            pattern: Some("(?P<g0>[0-9]+)"),
            groups: &[Some("g0")],
        },
    ]);

    fn texts(split: &TerminalSplit) -> Vec<Option<String>> {
        split.spans.iter().map(|span| span.text().map(|text| text.to_string())).collect()
    }

    #[test]
    fn one_included_regex_takes_the_whole_text() {
        let split = NUMBER.split("-42", "number").expect("the text is a number");
        assert_eq!(split.alternative, 0);
        assert_eq!(texts(&split), vec![Some("-42".to_string())]);
    }

    #[test]
    fn a_child_span_carries_its_own_source() {
        let split = NUMBER.split("7", "number").expect("the text is a number");
        assert!(split.spans[0].has_source());
        assert_eq!(split.spans[0].start(), 0);
        assert_eq!(split.spans[0].end(), 1);
    }

    #[test]
    fn a_suppressed_literal_stays_out_of_the_children() {
        let split = STRING_LITERAL
            .split("\"hi\"", "string_literal")
            .expect("the text is a quoted string");
        assert_eq!(texts(&split), vec![Some("hi".to_string())]);
    }

    #[test]
    fn an_included_literal_contributes_a_sourceless_child() {
        let split = TAG.split("#host", "tag").expect("the text is a tag");
        assert_eq!(split.spans[0], Span::unknown());
        assert_eq!(texts(&split), vec![None, Some("host".to_string())]);
    }

    #[test]
    fn a_group_is_read_by_name_not_by_position() {
        // The user's own terminal carries a capture group of its own, which shifts every index.
        static NESTED: TerminalShape = TerminalShape::new(&[TerminalAlt {
            pattern: Some("(?:(a|b)+)(?P<g0>[0-9]+)"),
            groups: &[Some("g0")],
        }]);
        let split = NESTED.split("ab12", "nested").expect("the text matches");
        assert_eq!(texts(&split), vec![Some("12".to_string())]);
    }

    #[test]
    fn the_split_is_measured_in_codepoints() {
        static UNICODE: TerminalShape = TerminalShape::new(&[TerminalAlt {
            pattern: Some("(?P<g0>[^ ]+)(?: )(?P<g1>[^ ]+)"),
            groups: &[Some("g0"), Some("g1")],
        }]);
        let split = UNICODE.split("café bar", "unicode").expect("the text matches");
        assert_eq!(split.spans[0].end(), 4, "four codepoints, five bytes");
        assert_eq!(texts(&split), vec![Some("café".to_string()), Some("bar".to_string())]);
    }

    #[test]
    fn alternatives_are_tried_in_grammar_order() {
        let split = EITHER.split("ab12", "either").expect("the second alternative matches");
        assert_eq!(split.alternative, 1);
        assert_eq!(texts(&split), vec![Some("ab".to_string()), Some("12".to_string())]);
        let split = EITHER.split("ab", "either").expect("the first alternative matches");
        assert_eq!(split.alternative, 0);
    }

    #[test]
    fn a_partial_match_is_not_a_match() {
        let error = NUMBER.split("42x", "number").expect_err("the terminal does not accept a trailing letter");
        assert_eq!(
            error.message,
            "rule \"number\": text \"42x\" is not something the rule could have matched"
        );
        assert_eq!(error.span, Span::unknown());
    }

    #[test]
    fn a_shape_no_alternative_can_rebuild_names_the_shape_not_the_text() {
        let error = UNSPLITTABLE.split("anything", "parts").expect_err("no alternative can be rebuilt");
        assert!(
            error.message.starts_with("rule \"parts\": the rule's shape cannot be rebuilt from text"),
            "{}",
            error.message
        );
        assert!(error.message.contains("restructure the rule or convert it by hand"));
    }

    #[test]
    fn a_rebuildable_alternative_still_serves_the_text_it_matches() {
        let split = MIXED.split("42", "parts").expect("the second alternative matches");
        assert_eq!(split.alternative, 1, "the index counts the unrebuildable alternative too");
        assert_eq!(texts(&split), vec![Some("42".to_string())]);
    }

    #[test]
    fn text_only_an_unrebuildable_alternative_could_have_matched_names_the_text() {
        // Some alternative can be rebuilt, so the shape is not what is being reported: the text
        // is, even though it is the rule's shape that leaves it nowhere to go.
        let error = MIXED.split("abc", "parts").expect_err("no rebuildable alternative matches");
        assert_eq!(
            error.message,
            "rule \"parts\": text \"abc\" is not something the rule could have matched"
        );
    }

    #[test]
    fn compilation_happens_once() {
        static ONCE: TerminalShape = TerminalShape::new(&[TerminalAlt {
            pattern: Some("(?P<g0>[0-9]+)"),
            groups: &[Some("g0")],
        }]);
        let first = ONCE.compiled().as_ptr();
        assert!(ONCE.split("1", "once").is_ok());
        assert_eq!(first, ONCE.compiled().as_ptr(), "the compiled alternatives are cached");
    }

    #[test]
    fn a_position_takes_up_to_its_maximum() {
        let values = [1, 2, 3];
        let mut cursor = Cursor::new(values.iter().collect());
        assert_eq!(cursor.take(2, 0), vec![&1, &2]);
        assert_eq!(cursor.remaining(), 1);
        assert_eq!(cursor.take(UNBOUNDED, 0), vec![&3]);
        assert_eq!(cursor.remaining(), 0);
    }

    #[test]
    fn a_reserve_leaves_what_a_later_required_position_needs() {
        let values = [1, 2];
        let mut cursor = Cursor::new(values.iter().collect());
        assert_eq!(cursor.take(UNBOUNDED, 1), vec![&1], "one value is held back");
        assert_eq!(cursor.take(UNBOUNDED, 0), vec![&2]);
    }

    #[test]
    fn a_position_stops_at_the_first_value_it_cannot_hold() {
        let values = [1, 2, 9, 3];
        let mut cursor = Cursor::new(values.iter().collect());
        assert_eq!(cursor.take_if(UNBOUNDED, 0, |value| *value < 5), vec![&1, &2]);
        assert_eq!(cursor.remaining(), 2, "the value it declined is still there");
    }

    #[test]
    fn populated_labels_are_the_ones_carrying_something() {
        assert_eq!(populated(&[("a", true), ("b", false), ("c", true)]), vec!["a", "c"]);
    }

    #[test]
    fn an_alternative_fits_what_it_requires_and_nothing_it_lacks() {
        assert!(alternative_fits(&["a"], &["a"], &["a", "b"]));
        assert!(!alternative_fits(&[], &["a"], &["a", "b"]), "a required label is absent");
        assert!(!alternative_fits(&["c"], &[], &["a", "b"]), "a populated label is not carried");
    }

    #[test]
    fn a_short_run_of_values_names_the_shortfall() {
        assert_eq!(filled(2, 2, "pair", "a"), Ok(()));
        assert_eq!(
            filled(1, 2, "pair", "a").unwrap_err().message,
            "rule \"pair\": the grammar needs 2 \"a\" value(s) at this position, but 1 were available"
        );
    }

    #[test]
    fn a_value_no_position_took_is_named() {
        assert_eq!(check_consumed("pair", "a", 0), Ok(()));
        assert_eq!(
            check_consumed("pair", "a", 2).unwrap_err().message,
            "rule \"pair\": the grammar has no place for 2 more \"a\" value(s)"
        );
    }

    #[test]
    fn a_value_no_branch_accepts_names_its_type() {
        assert_eq!(
            unplaceable("val", "x", "String").message,
            "rule \"val\": no item position accepts a String value for \"x\""
        );
    }

    #[test]
    fn a_wrapper_missing_a_required_field_says_which() {
        assert_eq!(hoisted(Some(&1), "schedule", "interval"), Ok(&1));
        let error = hoisted::<i64>(None, "schedule", "interval").unwrap_err();
        assert!(
            error.message.starts_with("rule \"schedule\": the flattened wrapper needs a \"interval\" value"),
            "{}",
            error.message
        );
        assert!(error.message.ends_with("leave every field hoisted out of the wrapper empty"));
    }

    #[test]
    fn an_optional_wrapper_is_rebuilt_only_for_something_it_carries() {
        assert!(!wrapper_needed(&[false, false]));
        assert!(wrapper_needed(&[false, true]));
        assert!(!wrapper_needed(&[]));
    }

    #[test]
    fn one_branch_of_an_alternation_has_to_carry_every_populated_label() {
        let branches: &[&[&str]] = &[&["a"], &["b"]];
        assert_eq!(check_group("decl", &["a"], branches, &["a", "b"], true), Ok(()));
        assert_eq!(
            check_group("decl", &[], branches, &["a", "b"], true).unwrap_err().message,
            "rule \"decl\": the grammar needs one of [\"a\", \"b\"] at this position, but none is populated"
        );
        assert_eq!(
            check_group("decl", &["a", "b"], branches, &["a", "b"], true)
                .unwrap_err()
                .message,
            "rule \"decl\": [\"a\", \"b\"] cannot come from one branch of this alternation, \
             which carries [\"a\"] | [\"b\"]; populate the fields of a single branch"
        );
    }

    #[test]
    fn a_node_the_formatter_declined_names_both_possibilities() {
        let error = unrenderable("config");
        assert!(
            error.message.starts_with("the formatter could not render a synthesised \"config\" node"),
            "{}",
            error.message
        );
        assert!(error.message.contains("a bug in FLTK's AST synthesis"));
        assert_eq!(error.span, Span::unknown());
    }

    #[test]
    fn a_multi_map_hands_out_its_groups_in_insertion_order() {
        let groups = [("a".to_string(), vec![1, 3]), ("b".to_string(), vec![2])];
        assert_eq!(
            multi_values(groups.iter().map(|(key, run)| (key, run)), "entry"),
            Ok(vec![&1, &3, &2])
        );
    }

    #[test]
    fn a_key_with_no_element_has_nothing_to_render_it_on() {
        let groups: Vec<(String, Vec<u8>)> = vec![("a".to_string(), Vec::new())];
        assert_eq!(
            multi_values(groups.iter().map(|(key, run)| (key, run)), "entry")
                .unwrap_err()
                .message,
            "rule \"entry\": the \"a\" key has no element to render it on"
        );
    }

    #[test]
    fn a_label_two_branches_carry_is_offered_once() {
        // `( a:x , b:y | a:x , c:z )`: `a` sits in both branches, and the offer is a set of labels.
        let branches: &[&[&str]] = &[&["a", "b"], &["a", "c"]];
        assert_eq!(
            check_group("decl", &[], branches, &["a", "b", "c"], true).unwrap_err().message,
            "rule \"decl\": the grammar needs one of [\"a\", \"b\", \"c\"] at this position, but none is populated"
        );
    }

    #[test]
    fn a_label_the_alternative_supplies_elsewhere_is_not_judged_here() {
        // `exclusive` is empty for a repeatable alternation, so only the demanded test applies.
        let branches: &[&[&str]] = &[&["a"], &["b"]];
        assert_eq!(check_group("decl", &["a", "b"], branches, &[], false), Ok(()));
    }
}

