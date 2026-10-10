//! Synthesis: rebuilding the CST an AST value stands for.
//!
//! `to_cst` walks one alternative's item positions in grammar order and appends exactly what the
//! parser would have appended there. Most of that walk is generated code, because it names the
//! CST node types, labels and child variants of one grammar. What lives here is the part that is
//! the same for every grammar: splitting a terminal-only rule's text back across the items it
//! was read from.
//!
//! A terminal-only rule carries text and nothing else, so the split is the inverse of reading
//! the node's own span: the alternative's items are consumed from the text one at a time, exactly
//! as the generated parser consumes them — each regex an anchored prefix match at the current
//! offset, each literal a string comparison, a `+`/`*` item looping until a match fails or makes
//! no progress, and the first alternative that matches committed to. Each included regex
//! occurrence becomes a child span carrying its own source. A literal occurrence's text is a
//! grammar constant, so its child carries position only.
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
use regex_automata::meta::Regex;
use regex_automata::{Anchored, Input};

use crate::error::AstError;
use crate::terminal::{compile_terminal, source_span, TerminalPattern};

/// The upper bound of an item position the grammar sets no limit on.
pub const UNBOUNDED: usize = usize::MAX;

/// One flat item of a terminal-only alternative, consumed the way the generated parser does.
#[derive(Debug)]
pub struct TerminalStep {
    /// The literal's text, or the regex as the grammar spells it.
    pub term: &'static str,
    /// `term` is a literal, consumed by string comparison rather than as a regex.
    pub literal: bool,
    /// Each occurrence becomes a child; a suppressed step only consumes text.
    pub included: bool,
    /// 0 for an optional item, 1 otherwise.
    pub minimum: usize,
    /// 1, or [`UNBOUNDED`] for a repeated item.
    pub maximum: usize,
}

/// One alternative of a terminal-only rule.
#[derive(Debug)]
pub enum TerminalAlt {
    /// The alternative's items in grammar order, walked over the node's text.
    Walk(&'static [TerminalStep]),

    /// A `text_from:` alternative: the redirected text against its own terminal in one group.
    Redirected {
        /// The redirected item's terminal, wrapped in a named capture group.
        pattern: &'static str,
        /// Per included item, in grammar order, the capture group holding its text; `None` is a
        /// literal, whose text comes back from the grammar and whose child carries position only.
        groups: &'static [Option<&'static str>],
    },

    /// An alternative holding a sub-expression, which is not rebuilt from text.
    Unsupported,
}

#[derive(Debug)]
enum CompiledAlt {
    /// One prefix-matching regex per step; `None` for a literal step.
    Walk(Vec<Option<Regex>>),
    Redirected(TerminalPattern),
    Unsupported,
}

/// A terminal-only rule's alternatives, compiled on first use.
///
/// [`new`](TerminalShape::new) is `const`, so a generated module declares one `static` per rule
/// and pays for the regex compilation only if something actually serializes that rule.
#[derive(Debug)]
pub struct TerminalShape {
    alternatives: &'static [TerminalAlt],
    compiled: OnceLock<Vec<CompiledAlt>>,
}

/// Which alternative a node's text came from, and what each of its items takes.
#[derive(Debug, Clone, PartialEq)]
pub struct TerminalSplit {
    /// The index of the matched alternative, in grammar order.
    pub alternative: usize,

    /// One entry per included item of that alternative, in grammar order, holding one span per
    /// occurrence of the item.
    pub pieces: Vec<Vec<Span>>,
}

/// Where one occurrence of `step` starting at byte `pos` ends, or `None` when it does not match.
fn consume(step: &TerminalStep, regex: Option<&Regex>, text: &str, pos: usize) -> Option<usize> {
    match regex {
        None => text[pos..].starts_with(step.term).then(|| pos + step.term.len()),
        // The whole text stays the haystack so assertions see what precedes `pos`, as the
        // parser's own search does.
        Some(regex) => regex
            .search(&Input::new(text).anchored(Anchored::Yes).span(pos..text.len()))
            .map(|found| found.end()),
    }
}

fn occurrence_span(step: &TerminalStep, text: &str) -> Span {
    if step.literal {
        // TODO(ast-synthesised-literal-spans): a literal occurrence gets no source, and the
        // generated text accessors panic on it.
        Span::unknown()
    } else {
        source_span(text)
    }
}

/// Replay one alternative's items over `text` from its start.
///
/// Returns the included occurrences grouped per included step and the byte offset the walk
/// stopped at, or `None` when the alternative fails. A repeated step loops, stopping at the first
/// failed or non-advancing match; a single or optional step consumes once and keeps even an empty
/// match.
fn walk(steps: &[TerminalStep], regexes: &[Option<Regex>], text: &str) -> Option<(Vec<Vec<Span>>, usize)> {
    let mut pos = 0;
    let mut pieces = Vec::new();
    for (step, regex) in steps.iter().zip(regexes) {
        let mut occurrences = Vec::new();
        if step.maximum > 1 {
            let start = pos;
            while let Some(end) = consume(step, regex.as_ref(), text, pos) {
                if end <= pos {
                    break;
                }
                if step.included {
                    occurrences.push(occurrence_span(step, &text[pos..end]));
                }
                pos = end;
            }
            if step.minimum > 0 && pos == start {
                return None;
            }
        } else if let Some(end) = consume(step, regex.as_ref(), text, pos) {
            if step.included {
                occurrences.push(occurrence_span(step, &text[pos..end]));
            }
            pos = end;
        } else if step.minimum > 0 {
            return None;
        }
        if step.included {
            pieces.push(occurrences);
        }
    }
    Some((pieces, pos))
}

impl TerminalShape {
    /// Declare the alternatives of one terminal-only rule.
    pub const fn new(alternatives: &'static [TerminalAlt]) -> Self {
        Self {
            alternatives,
            compiled: OnceLock::new(),
        }
    }

    fn compiled(&self) -> &[CompiledAlt] {
        self.compiled
            .get_or_init(|| {
                self.alternatives
                    .iter()
                    .map(|alternative| match alternative {
                        TerminalAlt::Walk(steps) => CompiledAlt::Walk(
                            steps
                                .iter()
                                .map(|step| (!step.literal).then(|| compile_terminal(step.term, step.term)))
                                .collect(),
                        ),
                        TerminalAlt::Redirected { pattern, .. } => CompiledAlt::Redirected(TerminalPattern::new(pattern)),
                        TerminalAlt::Unsupported => CompiledAlt::Unsupported,
                    })
                    .collect()
            })
            .as_slice()
    }

    /// Split `text` across the items of the first alternative that matches it.
    ///
    /// Alternatives are tried in grammar order and the first one that matches is committed to, as
    /// the parser does: if it leaves text unconsumed, the text is refused rather than offered to
    /// the next alternative.
    pub fn split(&self, text: &str, rule: &str) -> Result<TerminalSplit, AstError> {
        if self
            .alternatives
            .iter()
            .all(|alternative| matches!(alternative, TerminalAlt::Unsupported))
        {
            // Must stay on one line: the parity test matches this template verbatim.
            return Err(AstError::new(
                format!("rule {rule:?}: the rule's shape cannot be rebuilt from text — every alternative holds a sub-expression, so no split of the text back into children is determined; restructure the rule or convert it by hand"),
                Span::unknown(),
            ));
        }
        for (index, (alternative, compiled)) in self.alternatives.iter().zip(self.compiled()).enumerate() {
            match (alternative, compiled) {
                (TerminalAlt::Walk(steps), CompiledAlt::Walk(regexes)) => {
                    let Some((pieces, end)) = walk(steps, regexes, text) else {
                        continue;
                    };
                    if end != text.len() {
                        let consumed = text[..end].chars().count();
                        // Must stay on one line: the parity test matches this template verbatim.
                        return Err(AstError::new(
                            format!("rule {rule:?}: text {text:?} is not something the rule could have matched — alternative {index} matches only its first {consumed} codepoint(s), and the parser commits to the first alternative that matches rather than trying the next"),
                            Span::unknown(),
                        ));
                    }
                    return Ok(TerminalSplit {
                        alternative: index,
                        pieces,
                    });
                }
                (TerminalAlt::Redirected { groups, .. }, CompiledAlt::Redirected(pattern)) => {
                    let regex = pattern.regex();
                    let mut captures = regex.create_captures();
                    regex.captures(text, &mut captures);
                    if !captures.is_match() {
                        continue;
                    }
                    let pieces = groups
                        .iter()
                        .map(|group| match group {
                            // TODO(ast-synthesised-literal-spans): a non-captured piece gets no
                            // source, and the generated text accessors panic on it.
                            None => vec![Span::unknown()],
                            Some(name) => {
                                let matched = captures
                                    .get_group_by_name(name)
                                    .expect("every group the plan names wraps a required item of the same pattern");
                                vec![source_span(&text[matched.start..matched.end])]
                            }
                        })
                        .collect();
                    return Ok(TerminalSplit {
                        alternative: index,
                        pieces,
                    });
                }
                // TODO(ast-terminal-subexpression-walk): replay a sub-expression alternative as the
                // parser does instead of passing over it.
                _ => continue,
            }
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

/// Whether `text` is one of a label's literal spellings.
///
/// Taken as `&str` so a `&String` member, a `&str` parameter and an `Option<&str>` item all
/// coerce at the call: one emitted form serves every place a reverse converter reads text from.
pub fn spelled(text: &str, spellings: &[&str]) -> bool {
    spellings.contains(&text)
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

    #[test]
    fn spelled_admits_exactly_the_label_spellings() {
        assert!(spelled("gray", &["gray", "grey"]));
        assert!(spelled("grey", &["gray", "grey"]));
        assert!(!spelled("xyz", &["gray", "grey"]));
        assert!(!spelled("Gray", &["gray", "grey"]));
        assert!(!spelled("", &["gray"]));
    }

    /// An included regex step.
    const fn re(term: &'static str, minimum: usize, maximum: usize) -> TerminalStep {
        TerminalStep {
            term,
            literal: false,
            included: true,
            minimum,
            maximum,
        }
    }

    /// An included literal step.
    const fn lit(term: &'static str, minimum: usize, maximum: usize) -> TerminalStep {
        TerminalStep {
            term,
            literal: true,
            included: true,
            minimum,
            maximum,
        }
    }

    /// `step` with its occurrences consumed but not kept.
    const fn suppressed(step: TerminalStep) -> TerminalStep {
        TerminalStep {
            included: false,
            ..step
        }
    }

    /// `number := val:/-?[0-9]+/ ;` — one included regex item.
    static NUMBER: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[re("-?[0-9]+", 1, 1)])]);

    /// `string_literal := "\"" . content:/[^"]*/ . "\"" ;` — suppressed quotes, so only the content
    /// is a child.
    static STRING_LITERAL: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[
        suppressed(lit("\"", 1, 1)),
        re("[^\"]*", 1, 1),
        suppressed(lit("\"", 1, 1)),
    ])]);

    /// `tag := $"#" . name:/[a-z]+/ ;` — an included literal beside an included regex, so the
    /// first child carries position only.
    static TAG: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[lit("#", 1, 1), re("[a-z]+", 1, 1)])]);

    /// `either := a:/[a-z]+/ | a:/[a-z]+/ . b:/[0-9]+/ ;` — the first alternative also matches a
    /// prefix of the second's texts.
    static EITHER: TerminalShape = TerminalShape::new(&[
        TerminalAlt::Walk(&[re("[a-z]+", 1, 1)]),
        TerminalAlt::Walk(&[re("[a-z]+", 1, 1), re("[0-9]+", 1, 1)]),
    ]);

    /// A rule whose every alternative holds a sub-expression.
    static UNSPLITTABLE: TerminalShape = TerminalShape::new(&[TerminalAlt::Unsupported]);

    /// `mixed := p:/[a-z]/* | w:/[0-9]+/ ;` — the first alternative matches every text, empty or not.
    static MIXED: TerminalShape = TerminalShape::new(&[
        TerminalAlt::Walk(&[re("[a-z]", 0, UNBOUNDED)]),
        TerminalAlt::Walk(&[re("[0-9]+", 1, 1)]),
    ]);

    /// `partial := ( "a" | "b" ) . x:/[0-9]/ | w:/[0-9]+/ ;` — a sub-expression alternative, then
    /// a walked one.
    static PARTIAL: TerminalShape =
        TerminalShape::new(&[TerminalAlt::Unsupported, TerminalAlt::Walk(&[re("[0-9]+", 1, 1)])]);

    /// `quoted := "<" . content:/[a-z]+/ . ">" ;` under `text_from: content;`.
    static REDIRECTED: TerminalShape = TerminalShape::new(&[TerminalAlt::Redirected {
        pattern: "(?P<g1>[a-z]+)",
        groups: &[None, Some("g1"), None],
    }]);

    /// Every included piece's occurrence texts, `None` for a sourceless span.
    fn texts(split: &TerminalSplit) -> Vec<Vec<Option<String>>> {
        split
            .pieces
            .iter()
            .map(|piece| piece.iter().map(|span| span.text().map(|text| text.to_string())).collect())
            .collect()
    }

    fn one(text: &str) -> Vec<Option<String>> {
        vec![Some(text.to_string())]
    }

    #[test]
    fn one_included_regex_takes_the_whole_text() {
        let split = NUMBER.split("-42", "number").expect("the text is a number");
        assert_eq!(split.alternative, 0);
        assert_eq!(texts(&split), vec![one("-42")]);
    }

    #[test]
    fn a_child_span_carries_its_own_source() {
        let split = NUMBER.split("7", "number").expect("the text is a number");
        assert!(split.pieces[0][0].has_source());
        assert_eq!(split.pieces[0][0].start(), 0);
        assert_eq!(split.pieces[0][0].end(), 1);
    }

    #[test]
    fn a_suppressed_literal_stays_out_of_the_children() {
        let split = STRING_LITERAL
            .split("\"hi\"", "string_literal")
            .expect("the text is a quoted string");
        assert_eq!(texts(&split), vec![one("hi")]);
    }

    #[test]
    fn an_included_literal_contributes_a_sourceless_child() {
        let split = TAG.split("#host", "tag").expect("the text is a tag");
        assert_eq!(split.pieces[0], vec![Span::unknown()]);
        assert_eq!(texts(&split), vec![vec![None], one("host")]);
    }

    #[test]
    fn a_terminal_with_groups_of_its_own_is_matched_alone() {
        static NESTED: TerminalShape =
            TerminalShape::new(&[TerminalAlt::Walk(&[re("(a|b)+", 1, 1), re("(?P<d>[0-9])+", 1, 1)])]);
        let split = NESTED.split("ab12", "nested").expect("the text matches");
        assert_eq!(texts(&split), vec![one("ab"), one("12")]);
    }

    #[test]
    fn the_split_is_measured_in_codepoints() {
        static UNICODE: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[
            re("[^ ]+", 1, 1),
            suppressed(lit(" ", 1, 1)),
            re("[^ ]+", 1, 1),
        ])]);
        let split = UNICODE.split("café bar", "unicode").expect("the text matches");
        assert_eq!(split.pieces[0][0].end(), 4, "four codepoints, five bytes");
        assert_eq!(texts(&split), vec![one("café"), one("bar")]);
    }

    #[test]
    fn a_repeated_multibyte_step_takes_one_codepoint_per_occurrence() {
        static LATIN: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[re("[À-ÿ]", 1, UNBOUNDED)])]);
        let split = LATIN.split("Àé", "latin").expect("the text matches");
        assert_eq!(texts(&split), vec![vec![Some("À".to_string()), Some("é".to_string())]]);
        assert!(split.pieces[0].iter().all(|span| span.end() == 1));
    }

    #[test]
    fn alternatives_are_tried_in_grammar_order() {
        let split = EITHER.split("ab", "either").expect("the first alternative matches");
        assert_eq!(split.alternative, 0);
        let error = EITHER.split("ab12", "either").expect_err("the first alternative commits");
        assert_eq!(
            error.message,
            "rule \"either\": text \"ab12\" is not something the rule could have matched — alternative 0 matches only its first 2 codepoint(s), and the parser commits to the first alternative that matches rather than trying the next"
        );
    }

    #[test]
    fn a_failed_alternative_falls_through_to_the_next() {
        static ALTS: TerminalShape = TerminalShape::new(&[
            TerminalAlt::Walk(&[re("[0-9]+", 1, 1)]),
            TerminalAlt::Walk(&[re("[a-z]+", 1, 1)]),
        ]);
        let split = ALTS.split("abc", "alts").expect("the second alternative matches");
        assert_eq!(split.alternative, 1);
        assert_eq!(texts(&split), vec![one("abc")]);
    }

    #[test]
    fn the_commitment_counts_codepoints_consumed() {
        let error = MIXED.split("éa", "mixed").expect_err("alternative 0 matches nothing and commits");
        assert!(error.message.contains("matches only its first 0 codepoint(s)"), "{}", error.message);
        static PREFIX: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[re("[^ ]+", 1, 1)])]);
        let error = PREFIX.split("éé x", "prefix").expect_err("the space is never consumed");
        assert!(error.message.contains("matches only its first 2 codepoint(s)"), "{}", error.message);
    }

    #[test]
    fn a_partial_match_is_not_a_match() {
        let error = NUMBER.split("x42", "number").expect_err("the terminal does not accept a leading letter");
        assert_eq!(
            error.message,
            "rule \"number\": text \"x42\" is not something the rule could have matched"
        );
        assert_eq!(error.span, Span::unknown());
    }

    #[test]
    fn a_shape_no_alternative_can_rebuild_names_the_shape_not_the_text() {
        let error = UNSPLITTABLE.split("anything", "parts").expect_err("no alternative can be rebuilt");
        assert_eq!(
            error.message,
            "rule \"parts\": the rule's shape cannot be rebuilt from text — every alternative holds a sub-expression, so no split of the text back into children is determined; restructure the rule or convert it by hand"
        );
    }

    #[test]
    fn a_rebuildable_alternative_still_serves_the_text_it_matches() {
        let split = PARTIAL.split("42", "partial").expect("the second alternative matches");
        assert_eq!(split.alternative, 1, "the index counts the unrebuildable alternative too");
        assert_eq!(texts(&split), vec![one("42")]);
        assert!(MIXED.split("42", "mixed").is_err(), "alternative 0 matches nothing and commits");
        let split = MIXED.split("abc", "mixed").expect("alternative 0 matches");
        assert_eq!(
            texts(&split),
            vec![vec![Some("a".to_string()), Some("b".to_string()), Some("c".to_string())]]
        );
    }

    #[test]
    fn text_only_an_unrebuildable_alternative_could_have_matched_names_the_text() {
        // Some alternative can be rebuilt, so the shape is not what is being reported: the text
        // is, even though it is the rule's shape that leaves it nowhere to go.
        let error = PARTIAL.split("abc", "partial").expect_err("no rebuildable alternative matches");
        assert_eq!(
            error.message,
            "rule \"partial\": text \"abc\" is not something the rule could have matched"
        );
    }

    #[test]
    fn a_star_step_may_take_no_occurrence() {
        static STAR: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[re("[a-z]", 0, UNBOUNDED), re("[0-9]+", 1, 1)])]);
        let split = STAR.split("42", "star").expect("zero letters, then digits");
        assert_eq!(texts(&split), vec![vec![], one("42")]);
    }

    #[test]
    fn an_optional_step_is_kept_when_present_and_omitted_when_absent() {
        static OPTIONAL: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[
            re("[a-z]+", 1, 1),
            re("[0-9]", 0, 1),
            lit("!", 0, 1),
        ])]);
        let split = OPTIONAL.split("ab5!", "optional").expect("every item is present");
        assert_eq!(texts(&split), vec![one("ab"), one("5"), vec![None]]);
        let split = OPTIONAL.split("ab", "optional").expect("the optional items are absent");
        assert_eq!(texts(&split), vec![one("ab"), vec![], vec![]]);
    }

    #[test]
    fn a_nullable_single_step_is_kept_empty() {
        static NULLABLE: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[re("a*", 1, 1), re("b", 1, 1)])]);
        let split = NULLABLE.split("b", "nullable").expect("`a*` matches empty");
        assert_eq!(texts(&split), vec![one(""), one("b")]);
        static NULLABLE_OPTIONAL: TerminalShape =
            TerminalShape::new(&[TerminalAlt::Walk(&[re("a*", 0, 1), re("b", 1, 1)])]);
        let split = NULLABLE_OPTIONAL.split("b", "nullable").expect("`a*?` matches empty");
        assert_eq!(texts(&split), vec![one(""), one("b")]);
        static EMPTY: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[re("a*", 1, 1)])]);
        let split = EMPTY.split("", "empty").expect("the empty text is matched");
        assert_eq!(texts(&split), vec![one("")]);
    }

    #[test]
    fn a_nullable_plus_step_fails_on_no_progress() {
        static PLUS: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[re("a*", 1, UNBOUNDED)])]);
        let error = PLUS.split("", "plus").expect_err("`(a*)+` cannot advance");
        assert_eq!(error.message, "rule \"plus\": text \"\" is not something the rule could have matched");
    }

    #[test]
    fn a_repeat_never_gives_back_what_it_took() {
        static GREEDY: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[re("a+", 1, 1), re("a", 1, 1)])]);
        let error = GREEDY.split("aa", "greedy").expect_err("`a+` takes both, leaving `a` nothing");
        assert_eq!(error.message, "rule \"greedy\": text \"aa\" is not something the rule could have matched");
    }

    #[test]
    fn a_shorter_first_alternative_commits() {
        static SHORT: TerminalShape = TerminalShape::new(&[
            TerminalAlt::Walk(&[re("a", 1, 1)]),
            TerminalAlt::Walk(&[re("ab", 1, 1)]),
        ]);
        let error = SHORT.split("ab", "short").expect_err("the parser commits to `a`");
        assert!(error.message.contains("alternative 0 matches only its first 1 codepoint(s)"), "{}", error.message);
    }

    #[test]
    fn a_repeated_literal_gives_one_sourceless_child_per_occurrence() {
        static BANGS: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[lit("!", 1, UNBOUNDED), re("[a-z]", 1, 1)])]);
        let split = BANGS.split("!!!x", "bangs").expect("three bangs and a letter");
        assert_eq!(texts(&split), vec![vec![None, None, None], one("x")]);
    }

    #[test]
    fn a_suppressed_repeat_consumes_without_children() {
        static SKIP: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[
            suppressed(re("[0-9]", 0, UNBOUNDED)),
            re("[a-z]+", 1, 1),
        ])]);
        let split = SKIP.split("123ab", "skip").expect("digits, then letters");
        assert_eq!(texts(&split), vec![one("ab")]);
    }

    #[test]
    fn a_later_step_sees_what_precedes_it() {
        // `^` holds only at the start of the whole text, as in the parser's own search.
        static ANCHOR: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[re("[a-z]", 1, 1), re("^[0-9]", 1, 1)])]);
        assert!(ANCHOR.split("a1", "anchor").is_err());
        static BOUNDARY: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[re("[a-z]+", 1, 1), re(r"\b[0-9]", 0, 1)])]);
        let split = BOUNDARY.split("ab", "boundary").expect("letters alone");
        assert_eq!(texts(&split), vec![one("ab"), vec![]]);
    }

    #[test]
    fn a_redirected_text_is_matched_whole_against_its_own_terminal() {
        let split = REDIRECTED.split("abc", "quoted").expect("the content matches");
        assert_eq!(texts(&split), vec![vec![None], one("abc"), vec![None]]);
        assert!(REDIRECTED.split("ab1", "quoted").is_err());
    }

    #[test]
    fn an_unsupported_alternative_is_passed_over_beside_a_redirect() {
        static BESIDE: TerminalShape = TerminalShape::new(&[
            TerminalAlt::Unsupported,
            TerminalAlt::Redirected {
                pattern: "(?P<g0>[a-z]+)",
                groups: &[Some("g0")],
            },
        ]);
        let split = BESIDE.split("abc", "beside").expect("the redirect matches");
        assert_eq!(split.alternative, 1);
    }

    #[test]
    fn compilation_happens_once() {
        static ONCE: TerminalShape = TerminalShape::new(&[TerminalAlt::Walk(&[re("[0-9]+", 1, 1)])]);
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

