//! Spacing-spec resolution: the post-processing pass over a [`Doc`] tree.
//!
//! Direct port of `fltk/unparse/resolve_specs.py`. It rewrites the spacing-control
//! nodes (`AfterSpec`/`BeforeSpec`/`SeparatorSpec`) and `Join` nodes that the
//! generated unparser emits into concrete spacing, in the same passes the Python
//! version uses:
//!
//! 1. expand `Join`s into docs interleaved with `SeparatorSpec`s,
//! 2. extract boundary specs recursively to the top level,
//! 3. resolve the remaining specs by pattern matching,
//! 4. collapse `HardLine` + soft-break sequences.
//!
//! The internal passes operate on `Rc<Doc>` rather than `&Doc`/owned `Doc` so that
//! unchanged subtrees are shared by refcount bump, mirroring Python's frozen-dataclass
//! sharing (a leaf "passes through unchanged" as the same object). Recursion is left
//! as-is for this milestone (design §3 / answered open question 1: the renderer is
//! already iterative and resolve mirrors Python's recursion exactly).

use std::collections::VecDeque;
use std::rc::Rc;

use crate::doc::Doc;

/// A pattern mutator over the resolver working set: returns `Some(replacement)` when
/// its pattern matches the front of the working set, or `None` otherwise. Port of the
/// `PatternMutator` type in `resolve_specs.py`.
type Mutator = fn(&VecDeque<Rc<Doc>>) -> Option<Vec<Rc<Doc>>>;

/// `(leading_specs, remaining_docs, trailing_specs)` produced by boundary-spec extraction.
type BoundarySplit = (Vec<Rc<Doc>>, Vec<Rc<Doc>>, Vec<Rc<Doc>>);

/// `(processed_doc, leading_specs, trailing_specs)` produced by recursive extraction.
type ExtractResult = (Rc<Doc>, Vec<Rc<Doc>>, Vec<Rc<Doc>>);

/// Resolve all spacing-control nodes in a `Doc` tree into concrete spacing.
///
/// Port of `resolve_spacing_specs` (`resolve_specs.py:32`). See the module docs for
/// the pass breakdown.
pub fn resolve_spacing_specs(doc: Doc) -> Doc {
    // Take ownership so the root can be moved straight into the working `Rc` instead of
    // deep-cloning the whole tree on entry. Callers hold an owned `Doc` from
    // `accumulator.doc()`, so this is a free move at the call site.
    let resolved = resolve_rc(&Rc::new(doc));
    rc_to_owned(resolved)
}

/// Unwrap an owned `Rc<Doc>` into a `Doc`, cloning the (shallow) top node only when the
/// `Rc` is still shared.
fn rc_to_owned(rc: Rc<Doc>) -> Doc {
    Rc::try_unwrap(rc).unwrap_or_else(|rc| (*rc).clone())
}

/// `Rc`-threaded core of [`resolve_spacing_specs`]; also the recursion target for
/// preserved-trivia resolution.
fn resolve_rc(doc: &Rc<Doc>) -> Rc<Doc> {
    // Initial pass: expand Join nodes.
    let expanded = expand_joins(doc);
    // First pass: extract all boundary specs recursively.
    let (extracted, leading, trailing) = extract_all_boundary_specs(&expanded);
    // Second pass: pattern-based resolution.
    let resolved = if !leading.is_empty() || !trailing.is_empty() {
        let mut all = leading;
        all.push(extracted);
        all.extend(trailing);
        resolve_patterns(&concat_rc(all))
    } else {
        resolve_patterns(&extracted)
    };
    // Final pass: collapse HardLine + Line/SoftLine sequences throughout the tree.
    collapse_hardline_sequences(&resolved)
}

/// `Rc`-based analog of [`crate::doc::concat`]: flatten nested `Concat`s, drop `Nil`s,
/// collapse to a single child or `Nil` where possible. Mirrors `combinators.concat`,
/// but threads `Rc` so shared children are reused rather than deep-cloned.
fn concat_rc(docs: Vec<Rc<Doc>>) -> Rc<Doc> {
    let mut flattened: Vec<Rc<Doc>> = Vec::new();
    for d in docs {
        match &*d {
            Doc::Concat(inner) => flattened.extend(inner.iter().cloned()),
            Doc::Nil => {}
            _ => flattened.push(d),
        }
    }
    match flattened.len() {
        0 => Rc::new(Doc::Nil),
        1 => flattened.pop().expect("len checked == 1"),
        _ => Rc::new(Doc::Concat(flattened)),
    }
}

/// Initial pass: expand `Join` nodes into docs with `SeparatorSpec`s between them.
///
/// Port of `_expand_joins` (`resolve_specs.py:67`). The separator goes into the
/// `SeparatorSpec`'s `preserved_trivia` so it takes priority over other separators.
fn expand_joins(doc: &Rc<Doc>) -> Rc<Doc> {
    match &**doc {
        Doc::Join { docs, separator } => {
            if docs.is_empty() {
                return Rc::new(Doc::Nil);
            }
            let mut expanded: Vec<Rc<Doc>> = Vec::new();
            let mut trailing_separators: Vec<Rc<Doc>> = Vec::new();
            let mut need_sep = false;
            for d in docs {
                if let Doc::SeparatorSpec {
                    preserved_trivia: None,
                    ..
                } = &**d
                {
                    if !need_sep {
                        // Leading separators are preserved.
                        expanded.push(d.clone());
                    } else {
                        // This might be a trailing separator.
                        trailing_separators.push(d.clone());
                    }
                    continue;
                }
                let expanded_child = expand_joins(d);
                let is_after_before =
                    matches!(&**d, Doc::AfterSpec { .. } | Doc::BeforeSpec { .. });
                if need_sep && !is_after_before {
                    // TODO(unparser-join-sep-resolve): every gap stores a clone of the same
                    // `separator` Rc as preserved_trivia, so resolution re-runs the full
                    // pipeline on the identical separator subtree once per gap (M-1 times for
                    // an M-element join). Resolve the separator once and reuse it (e.g. cache
                    // keyed on `Rc::as_ptr`); output is unchanged since each run is identical.
                    expanded.push(Rc::new(Doc::SeparatorSpec {
                        spacing: None,
                        preserved_trivia: Some(separator.clone()),
                        required: false,
                    }));
                }
                expanded.push(expanded_child);
                trailing_separators.clear();
                if !is_after_before {
                    need_sep = true;
                }
            }
            expanded.extend(trailing_separators);
            concat_rc(expanded)
        }
        Doc::Concat(docs) => {
            let expanded: Vec<Rc<Doc>> = docs.iter().map(expand_joins).collect();
            concat_rc(expanded)
        }
        Doc::Group(content) => Rc::new(Doc::Group(expand_joins(content))),
        Doc::Nest { indent, content } => Rc::new(Doc::Nest {
            indent: *indent,
            content: expand_joins(content),
        }),
        _ => doc.clone(),
    }
}

/// First pass: recursively extract leading/trailing boundary specs.
///
/// Port of `_extract_all_boundary_specs` (`resolve_specs.py:121`). Returns the
/// processed doc plus the leading and trailing specs that bubbled up to this level.
fn extract_all_boundary_specs(doc: &Rc<Doc>) -> ExtractResult {
    match &**doc {
        Doc::Concat(docs) => {
            let mut processed: Vec<Rc<Doc>> = Vec::new();
            for child in docs {
                let (processed_child, child_leading, child_trailing) =
                    extract_all_boundary_specs(child);
                processed.extend(child_leading);
                processed.push(processed_child);
                processed.extend(child_trailing);
            }
            let (leading, remaining, trailing) = extract_boundary_specs(processed);
            (concat_rc(remaining), leading, trailing)
        }
        Doc::Group(content) => {
            let (processed_content, inner_leading, inner_trailing) =
                extract_all_boundary_specs(content);
            (
                Rc::new(Doc::Group(processed_content)),
                inner_leading,
                inner_trailing,
            )
        }
        Doc::Nest { indent, content } => {
            let (processed_content, inner_leading, inner_trailing) =
                extract_all_boundary_specs(content);
            (
                Rc::new(Doc::Nest {
                    indent: *indent,
                    content: processed_content,
                }),
                inner_leading,
                inner_trailing,
            )
        }
        _ => (doc.clone(), Vec::new(), Vec::new()),
    }
}

/// Extract leading `BeforeSpec`/`SeparatorSpec`s and trailing `AfterSpec`/`SeparatorSpec`s
/// from a doc list.
///
/// Port of `_extract_boundary_specs` (`resolve_specs.py:152`). Returns
/// `(leading_specs, remaining_docs, trailing_specs)`.
fn extract_boundary_specs(mut docs: Vec<Rc<Doc>>) -> BoundarySplit {
    // Pop the trailing run from the end (O(1) each) and reverse once to restore order,
    // rather than `insert(0, …)` per element (O(t²)).
    let mut trailing_specs: Vec<Rc<Doc>> = Vec::new();
    while docs
        .last()
        .is_some_and(|d| matches!(&**d, Doc::AfterSpec { .. } | Doc::SeparatorSpec { .. }))
    {
        trailing_specs.push(docs.pop().expect("last() was Some"));
    }
    trailing_specs.reverse();

    // Drain the leading run in one shift (O(n)), rather than `remove(0)` per element (O(n·l)).
    let leading_count = docs
        .iter()
        .take_while(|d| matches!(&***d, Doc::BeforeSpec { .. } | Doc::SeparatorSpec { .. }))
        .count();
    let leading_specs: Vec<Rc<Doc>> = docs.drain(..leading_count).collect();

    (leading_specs, docs, trailing_specs)
}

/// Second pass: apply pattern-based resolution to spacing specs.
///
/// Port of `_resolve_patterns` (`resolve_specs.py:171`).
fn resolve_patterns(doc: &Rc<Doc>) -> Rc<Doc> {
    match &**doc {
        Doc::Concat(docs) => concat_rc(resolve_concat_patterns(docs)),
        Doc::Group(content) => Rc::new(Doc::Group(resolve_patterns(content))),
        Doc::Nest { indent, content } => Rc::new(Doc::Nest {
            indent: *indent,
            content: resolve_patterns(content),
        }),
        _ => concat_rc(resolve_concat_patterns(std::slice::from_ref(doc))),
    }
}

/// Resolve control nodes in a sequence of docs by pattern matching.
///
/// Port of `_resolve_concat_patterns` (`resolve_specs.py:198`). Maintains a sliding
/// working set, always trying to collapse consecutive specs first, then applying the
/// precedence-ordered pattern mutators, then emitting the head when nothing matches.
fn resolve_concat_patterns(docs: &[Rc<Doc>]) -> Vec<Rc<Doc>> {
    // Mutators in order of precedence (size, mutator), matching `resolve_specs.py:211`.
    const MUTATORS: [(usize, Mutator); 6] = [
        (3, mutate_after_sep_before),
        (2, mutate_after_sep),
        (2, mutate_sep_before),
        (2, mutate_text_newline),
        (1, mutate_standalone_sep),
        (1, mutate_standalone_after_before),
    ];
    // Largest pattern size (the `(3, _)` entry).
    const MAX_PATTERN_SIZE: usize = 3;

    let mut working_set: VecDeque<Rc<Doc>> = VecDeque::new();
    let mut output: Vec<Rc<Doc>> = Vec::new();
    let mut iter = docs.iter();

    loop {
        // Step 1: fill the working set to MAX_PATTERN_SIZE + 1 so consecutive specs that
        // span beyond the largest pattern are visible.
        while working_set.len() < MAX_PATTERN_SIZE + 1 {
            let Some(next_doc) = iter.next() else {
                break;
            };
            // Recursively resolve Group/Nest/Concat children before pattern matching.
            let processed = match &**next_doc {
                Doc::Group(_) | Doc::Nest { .. } | Doc::Concat(_) => resolve_patterns(next_doc),
                _ => next_doc.clone(),
            };
            working_set.push_back(processed);
        }

        if working_set.is_empty() {
            break;
        }

        // Step 2: always try to collapse consecutive specs first.
        if let Some(result) = mutate_consecutive_specs(&working_set) {
            working_set.clear();
            working_set.extend(result);
            continue;
        }

        // Step 3: try each mutator in precedence order.
        let mut mutated = false;
        for &(pattern_size, mutator) in MUTATORS.iter() {
            if working_set.len() < pattern_size {
                continue;
            }
            if let Some(result) = mutator(&working_set) {
                for _ in 0..pattern_size {
                    working_set.pop_front();
                }
                for d in result.into_iter().rev() {
                    working_set.push_front(d);
                }
                mutated = true;
                break;
            }
        }

        // Step 4: nothing matched - emit the head.
        if !mutated {
            output.push(working_set.pop_front().expect("working_set non-empty"));
        }
    }

    output
}

/// Recursively collapse `HardLine` + `Line`/`SoftLine` sequences throughout the tree.
///
/// Port of `_collapse_hardline_sequences` (`resolve_specs.py:285`).
fn collapse_hardline_sequences(doc: &Rc<Doc>) -> Rc<Doc> {
    match &**doc {
        Doc::Concat(docs) => {
            let processed: Vec<Rc<Doc>> = docs.iter().map(collapse_hardline_sequences).collect();
            concat_rc(collapse_hardline_list(processed))
        }
        Doc::Group(content) => Rc::new(Doc::Group(collapse_hardline_sequences(content))),
        Doc::Nest { indent, content } => Rc::new(Doc::Nest {
            indent: *indent,
            content: collapse_hardline_sequences(content),
        }),
        _ => doc.clone(),
    }
}

/// Collapse `HardLine` followed by `Line`/`SoftLine` in a flat doc list.
///
/// Port of `_collapse_hardline_list` (`resolve_specs.py:308`).
fn collapse_hardline_list(docs: Vec<Rc<Doc>>) -> Vec<Rc<Doc>> {
    // `_MIN_COLLAPSIBLE_LENGTH` is 2 (`resolve_specs.py:29`).
    if docs.len() < 2 {
        return docs;
    }
    let mut result: Vec<Rc<Doc>> = Vec::new();
    let mut i = 0usize;
    let n = docs.len();
    while i < n {
        let is_collapsible = matches!(&*docs[i], Doc::HardLine { .. })
            && i + 1 < n
            && matches!(&*docs[i + 1], Doc::Line | Doc::SoftLine);
        result.push(docs[i].clone());
        // Keep the HardLine, skip the redundant soft break.
        i += if is_collapsible { 2 } else { 1 };
    }
    result
}

// ---- Pattern mutators (ports of the `_mutate_*` helpers) --------------------------

/// Pattern: `AfterSpec, SeparatorSpec, BeforeSpec`. Port of `_mutate_after_sep_before`.
fn mutate_after_sep_before(ws: &VecDeque<Rc<Doc>>) -> Option<Vec<Rc<Doc>>> {
    if ws.len() < 3 {
        return None;
    }
    if let (
        Doc::AfterSpec { spacing: after },
        Doc::SeparatorSpec {
            spacing: sep_spacing,
            preserved_trivia,
            ..
        },
        Doc::BeforeSpec { spacing: before },
    ) = (&*ws[0], &*ws[1], &*ws[2])
    {
        let spacing = resolve_spacing(after, before, sep_spacing, preserved_trivia);
        return Some(spacing.map(|s| vec![s]).unwrap_or_default());
    }
    None
}

/// Pattern: `AfterSpec, SeparatorSpec`. Port of `_mutate_after_sep`.
fn mutate_after_sep(ws: &VecDeque<Rc<Doc>>) -> Option<Vec<Rc<Doc>>> {
    if ws.len() < 2 {
        return None;
    }
    if let (
        Doc::AfterSpec { spacing: after },
        Doc::SeparatorSpec {
            spacing: sep_spacing,
            preserved_trivia,
            required,
        },
    ) = (&*ws[0], &*ws[1])
    {
        if let Some(trivia) = preserved_trivia {
            return Some(vec![resolve_rc(trivia)]);
        }
        if sep_spacing.is_some() || *required {
            let result_spacing = pick_spacing_with_blank_lines(after, sep_spacing);
            return Some(vec![result_spacing]);
        }
        // No separator, ignore after spec.
        return Some(Vec::new());
    }
    None
}

/// Pattern: `SeparatorSpec, BeforeSpec`. Port of `_mutate_sep_before`.
fn mutate_sep_before(ws: &VecDeque<Rc<Doc>>) -> Option<Vec<Rc<Doc>>> {
    if ws.len() < 2 {
        return None;
    }
    if let (
        Doc::SeparatorSpec {
            spacing: sep_spacing,
            preserved_trivia,
            required,
        },
        Doc::BeforeSpec { spacing: before },
    ) = (&*ws[0], &*ws[1])
    {
        if let Some(trivia) = preserved_trivia {
            return Some(vec![resolve_rc(trivia)]);
        }
        if sep_spacing.is_some() || *required {
            let result_spacing = pick_spacing_with_blank_lines(before, sep_spacing);
            return Some(vec![result_spacing]);
        }
        // No separator, ignore before spec.
        return Some(Vec::new());
    }
    None
}

/// Choose between an `AfterSpec`/`BeforeSpec` spacing and a separator's spacing,
/// preferring the separator only when it is a `HardLine` with more blank lines.
///
/// Factors the shared blank-line-preservation logic from `_mutate_after_sep` and
/// `_mutate_sep_before` (`resolve_specs.py:368`, `:401`).
fn pick_spacing_with_blank_lines(primary: &Rc<Doc>, sep_spacing: &Option<Rc<Doc>>) -> Rc<Doc> {
    if let Some(sep_sp) = sep_spacing {
        if let Doc::HardLine {
            blank_lines: sep_bl,
        } = &**sep_sp
        {
            if *sep_bl > 0 {
                let primary_has_fewer = match &**primary {
                    Doc::HardLine { blank_lines } => *blank_lines < *sep_bl,
                    _ => true,
                };
                if primary_has_fewer {
                    return sep_sp.clone();
                }
            }
        }
    }
    primary.clone()
}

/// Pattern: `Text("\n"), SeparatorSpec(spacing=Some(_))` -> `HardLine`. Port of
/// `_mutate_text_newline`.
fn mutate_text_newline(ws: &VecDeque<Rc<Doc>>) -> Option<Vec<Rc<Doc>>> {
    if ws.len() < 2 {
        return None;
    }
    if let Doc::Text(content) = &*ws[0] {
        if content == "\n" {
            if let Doc::SeparatorSpec {
                spacing: Some(_), ..
            } = &*ws[1]
            {
                return Some(vec![Rc::new(Doc::HardLine { blank_lines: 0 })]);
            }
        }
    }
    None
}

/// Pattern: standalone `SeparatorSpec`. Port of `_mutate_standalone_sep`.
fn mutate_standalone_sep(ws: &VecDeque<Rc<Doc>>) -> Option<Vec<Rc<Doc>>> {
    if ws.is_empty() {
        return None;
    }
    if let Doc::SeparatorSpec {
        spacing,
        preserved_trivia,
        ..
    } = &*ws[0]
    {
        if let Some(trivia) = preserved_trivia {
            return Some(vec![resolve_rc(trivia)]);
        }
        if let Some(sp) = spacing {
            return Some(vec![sp.clone()]);
        }
        // SeparatorSpec with no spacing and no trivia - remove it.
        return Some(Vec::new());
    }
    None
}

/// Pattern: standalone `AfterSpec` or `BeforeSpec` (ignored). Port of
/// `_mutate_standalone_after_before`.
fn mutate_standalone_after_before(ws: &VecDeque<Rc<Doc>>) -> Option<Vec<Rc<Doc>>> {
    if ws.is_empty() {
        return None;
    }
    if matches!(&*ws[0], Doc::AfterSpec { .. } | Doc::BeforeSpec { .. }) {
        return Some(Vec::new());
    }
    None
}

/// Collapse all consecutive specs of the same kind in the working set.
///
/// Port of `_mutate_consecutive_specs` (`resolve_specs.py:466`). Returns `Some` only
/// when at least one merge happened (matching the Python `merged` flag).
fn mutate_consecutive_specs(ws: &VecDeque<Rc<Doc>>) -> Option<Vec<Rc<Doc>>> {
    if ws.len() < 2 {
        return None;
    }
    let n = ws.len();
    let mut result: Vec<Rc<Doc>> = Vec::new();
    let mut i = 0usize;
    let mut merged = false;

    while i < n {
        match &*ws[i] {
            Doc::BeforeSpec { spacing } => {
                let mut j = i + 1;
                let mut merged_spacing: Option<Rc<Doc>> = Some(spacing.clone());
                while j < n {
                    let Doc::BeforeSpec { spacing: nxt } = &*ws[j] else {
                        break;
                    };
                    merged = true;
                    merged_spacing = merge_spacing(merged_spacing.as_ref(), Some(nxt));
                    j += 1;
                }
                if let Some(ms) = merged_spacing {
                    result.push(Rc::new(Doc::BeforeSpec { spacing: ms }));
                }
                i = j;
            }
            Doc::AfterSpec { spacing } => {
                let mut j = i + 1;
                let mut merged_spacing: Option<Rc<Doc>> = Some(spacing.clone());
                while j < n {
                    let Doc::AfterSpec { spacing: nxt } = &*ws[j] else {
                        break;
                    };
                    merged = true;
                    merged_spacing = merge_spacing(merged_spacing.as_ref(), Some(nxt));
                    j += 1;
                }
                if let Some(ms) = merged_spacing {
                    result.push(Rc::new(Doc::AfterSpec { spacing: ms }));
                }
                i = j;
            }
            Doc::SeparatorSpec {
                spacing,
                preserved_trivia,
                required,
            } => {
                let j = i + 1;
                if let Some(Doc::SeparatorSpec {
                    spacing: next_spacing,
                    preserved_trivia: next_trivia,
                    required: next_required,
                }) = ws.get(j).map(|d| &**d)
                {
                    let curr_trivia = preserved_trivia.is_some();
                    let next_has_trivia = next_trivia.is_some();
                    if curr_trivia && next_has_trivia {
                        // Both have trivia - keep both (process next next iteration).
                        result.push(ws[i].clone());
                        i += 1;
                    } else if curr_trivia {
                        // Only curr has trivia - keep curr, skip next.
                        merged = true;
                        result.push(ws[i].clone());
                        i = j + 1;
                    } else if next_has_trivia {
                        // Only next has trivia - skip curr, process next next iteration.
                        merged = true;
                        i = j;
                    } else {
                        // Neither has trivia - merge them.
                        merged = true;
                        let merged_spacing = merge_spacing(spacing.as_ref(), next_spacing.as_ref());
                        let merged_required = *required || *next_required;
                        if merged_spacing.is_some() || merged_required {
                            result.push(Rc::new(Doc::SeparatorSpec {
                                spacing: merged_spacing,
                                preserved_trivia: None,
                                required: merged_required,
                            }));
                        }
                        i = j + 1;
                    }
                } else {
                    // No consecutive SeparatorSpec - keep curr as is.
                    result.push(ws[i].clone());
                    i += 1;
                }
            }
            _ => {
                result.push(ws[i].clone());
                i += 1;
            }
        }
    }

    if merged {
        Some(result)
    } else {
        None
    }
}

/// Resolve spacing when both after and before specs flank a separator.
///
/// Port of `_resolve_spacing` (`resolve_specs.py:545`).
fn resolve_spacing(
    after: &Rc<Doc>,
    before: &Rc<Doc>,
    sep_spacing: &Option<Rc<Doc>>,
    sep_preserved_trivia: &Option<Rc<Doc>>,
) -> Option<Rc<Doc>> {
    if let Some(trivia) = sep_preserved_trivia {
        return Some(resolve_rc(trivia));
    }
    // Faithful port of the Python `_resolve_spacing` (resolve_specs.py:555): when the
    // separator has neither trivia nor spacing this fails *regardless* of `required`.
    // The asymmetry with `mutate_after_sep`/`mutate_sep_before` (which consult `required`
    // and tolerate `spacing == None`) is intentional and mirrors the Python backend
    // exactly; matching its behavior here is required for cross-backend parity, so this
    // `assert!` deliberately stands in for the Python `raise RuntimeError` rather than
    // adding a `required` guard that the Python side does not have.
    assert!(
        sep_spacing.is_some(),
        "Separator has neither preserved trivia nor spacing"
    );
    merge_spacing(Some(after), Some(before))
}

/// Merge two optional spacing docs by the precedence rules.
///
/// Port of `_merge_spacing` (`resolve_specs.py:563`): HardLine (most blanks) >
/// Line > Nbsp > SoftLine > Nil, with the second operand winning ties of
/// unrelated kinds.
fn merge_spacing(spacing1: Option<&Rc<Doc>>, spacing2: Option<&Rc<Doc>>) -> Option<Rc<Doc>> {
    let (a, b) = match (spacing1, spacing2) {
        (None, None) => return None,
        (None, Some(b)) => return Some(b.clone()),
        (Some(a), None) => return Some(a.clone()),
        (Some(a), Some(b)) => (a, b),
    };

    if a == b {
        return Some(a.clone());
    }

    // HardLine wins over everything.
    match (&**a, &**b) {
        (Doc::HardLine { blank_lines: ba }, Doc::HardLine { blank_lines: bb }) => {
            return Some(if ba >= bb { a.clone() } else { b.clone() });
        }
        (Doc::HardLine { .. }, _) => return Some(a.clone()),
        (_, Doc::HardLine { .. }) => return Some(b.clone()),
        _ => {}
    }

    // Line wins over SoftLine, Nbsp, Nil.
    if matches!(&**a, Doc::Line) || matches!(&**b, Doc::Line) {
        return Some(Rc::new(Doc::Line));
    }

    // Nbsp wins over SoftLine, Nil.
    if matches!(&**a, Doc::Nbsp) {
        return Some(a.clone());
    }
    if matches!(&**b, Doc::Nbsp) {
        return Some(b.clone());
    }

    // SoftLine wins over Nil.
    if matches!(&**a, Doc::SoftLine) || matches!(&**b, Doc::SoftLine) {
        return Some(Rc::new(Doc::SoftLine));
    }

    // Default: use spacing2 (it's closer to the following content).
    Some(b.clone())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::doc::{hardline, line, nil, softline, text};

    // ---- Test builders (raw, unflattened, mirroring the Python `Concat([...])`) ----

    fn rc(d: Doc) -> Rc<Doc> {
        Rc::new(d)
    }

    fn cat(docs: Vec<Doc>) -> Doc {
        Doc::Concat(docs.into_iter().map(rc).collect())
    }

    fn after(spacing: Doc) -> Doc {
        Doc::AfterSpec {
            spacing: rc(spacing),
        }
    }

    fn before(spacing: Doc) -> Doc {
        Doc::BeforeSpec {
            spacing: rc(spacing),
        }
    }

    fn sep(spacing: Option<Doc>, trivia: Option<Doc>, required: bool) -> Doc {
        Doc::SeparatorSpec {
            spacing: spacing.map(rc),
            preserved_trivia: trivia.map(rc),
            required,
        }
    }

    #[test]
    fn problematic_sequence_collapses() {
        // Port of test_problematic_sequence.
        let doc = cat(vec![
            text("rule"),
            text("+"),
            sep(Some(nil()), None, false),
            after(line()),
            sep(Some(nil()), None, false),
            sep(Some(nil()), None, false),
            sep(Some(nil()), None, false),
            sep(Some(nil()), None, false),
            sep(Some(nil()), None, false),
            text(";"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![text("rule"), text("+"), line(), text(";")])
        );
    }

    #[test]
    fn multiple_consecutive_separator_specs_collapse() {
        // Port of test_multiple_consecutive_separator_specs.
        let doc = cat(vec![
            text("a"),
            sep(Some(nil()), None, false),
            sep(Some(nil()), None, false),
            sep(Some(nil()), None, false),
            text("b"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(resolved, cat(vec![text("a"), text("b")]));
    }

    #[test]
    fn separator_after_after_keeps_after_spacing() {
        // Port of test_separator_after_separator_after.
        let doc = cat(vec![
            text("x"),
            after(line()),
            sep(Some(nil()), None, false),
            sep(Some(nil()), None, false),
            text("y"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(resolved, cat(vec![text("x"), line(), text("y")]));
    }

    #[test]
    fn extract_boundary_specs_basic() {
        // Port of test_extract_boundary_specs_basic.
        let docs = vec![
            rc(before(line())),
            rc(before(softline())),
            rc(text("content")),
            rc(after(line())),
            rc(after(softline())),
        ];
        let (leading, remaining, trailing) = extract_boundary_specs(docs);
        assert_eq!(leading, vec![rc(before(line())), rc(before(softline()))]);
        assert_eq!(remaining, vec![rc(text("content"))]);
        assert_eq!(trailing, vec![rc(after(line())), rc(after(softline()))]);
    }

    #[test]
    fn extract_boundary_specs_no_specs() {
        let docs = vec![rc(text("a")), rc(text("b")), rc(text("c"))];
        let (leading, remaining, trailing) = extract_boundary_specs(docs);
        assert!(leading.is_empty());
        assert_eq!(remaining, vec![rc(text("a")), rc(text("b")), rc(text("c"))]);
        assert!(trailing.is_empty());
    }

    #[test]
    fn group_boundary_specs_combine_with_separators() {
        // Port of test_group_with_boundary_specs.
        let doc = cat(vec![
            text("before"),
            sep(Some(nil()), None, true),
            Doc::Group(rc(cat(vec![
                before(line()),
                text("inside"),
                after(softline()),
            ]))),
            sep(Some(line()), None, true),
            text("after"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![
                text("before"),
                line(),
                Doc::Group(rc(text("inside"))),
                softline(),
                text("after"),
            ])
        );
    }

    #[test]
    fn nest_boundary_specs_combine_with_separators() {
        // Port of test_nest_with_boundary_specs.
        let doc = cat(vec![
            text("before"),
            sep(Some(nil()), None, true),
            Doc::Nest {
                indent: 1,
                content: rc(cat(vec![before(softline()), text("nested"), after(line())])),
            },
            sep(Some(nil()), None, true),
            text("after"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![
                text("before"),
                softline(),
                Doc::Nest {
                    indent: 1,
                    content: rc(text("nested")),
                },
                line(),
                text("after"),
            ])
        );
    }

    #[test]
    fn consecutive_before_specs_merge_hardline_blanks() {
        // Port of test_consecutive_before_specs.
        let doc = cat(vec![
            text("before"),
            sep(Some(nil()), None, true),
            before(hardline(0)),
            before(hardline(1)),
            text("after"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![text("before"), hardline(1), text("after")])
        );
    }

    #[test]
    fn consecutive_after_specs_merge_hardline_blanks() {
        // Port of test_consecutive_after_specs.
        let doc = cat(vec![
            text("before"),
            after(hardline(1)),
            after(hardline(0)),
            sep(Some(nil()), None, true),
            text("after"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![text("before"), hardline(1), text("after")])
        );
    }

    #[test]
    fn mixed_consecutive_specs_resolve_to_line() {
        // Port of test_mixed_consecutive_specs.
        let doc = cat(vec![
            text("a"),
            after(line()),
            after(softline()),
            sep(Some(nil()), None, true),
            before(softline()),
            before(line()),
            text("b"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(resolved, cat(vec![text("a"), line(), text("b")]));
    }

    #[test]
    fn nested_separator_spec_with_outer_specs() {
        // Port of test_nested_separator_spec_with_outer_spec.
        let doc = cat(vec![
            text("{"),
            after(line()),
            Doc::Nest {
                indent: 1,
                content: rc(cat(vec![
                    sep(Some(nil()), None, false),
                    text("nested"),
                    sep(Some(nil()), None, false),
                ])),
            },
            before(softline()),
            text("}"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![
                text("{"),
                line(),
                Doc::Nest {
                    indent: 1,
                    content: rc(text("nested")),
                },
                softline(),
                text("}"),
            ])
        );
    }

    #[test]
    fn deeply_nested_after_spec_combines_with_separator() {
        // Port of test_deeply_nested_after_spec_with_separator.
        let doc = cat(vec![
            Doc::Group(rc(cat(vec![
                text("use"),
                sep(Some(line()), None, true),
                Doc::Nest {
                    indent: 1,
                    content: rc(cat(vec![
                        sep(Some(nil()), None, false),
                        text("content"),
                        text(";"),
                        after(line()),
                    ])),
                },
            ]))),
            sep(Some(nil()), None, false),
            text("next"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![
                Doc::Group(rc(cat(vec![
                    text("use"),
                    line(),
                    Doc::Nest {
                        indent: 1,
                        content: rc(cat(vec![text("content"), text(";")])),
                    },
                ]))),
                line(),
                text("next"),
            ])
        );
    }

    #[test]
    fn preserved_trivia_overrides_spacing() {
        // A separator with preserved trivia wins over a flanking AfterSpec.
        let doc = cat(vec![
            text("a"),
            after(line()),
            sep(Some(nil()), Some(text("/*c*/")), false),
            text("b"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(resolved, cat(vec![text("a"), text("/*c*/"), text("b")]));
    }

    #[test]
    fn join_expands_with_separator_between_elements() {
        // The Join separator becomes preserved trivia and resolves to itself.
        let doc = Doc::Join {
            docs: vec![rc(text("a")), rc(text("b")), rc(text("c"))],
            separator: rc(text(",")),
        };
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![text("a"), text(","), text("b"), text(","), text("c")])
        );
    }

    #[test]
    fn empty_join_resolves_to_nil() {
        let doc = Doc::Join {
            docs: Vec::new(),
            separator: rc(text(",")),
        };
        assert_eq!(resolve_spacing_specs(doc), nil());
    }

    #[test]
    fn hardline_followed_by_soft_break_collapses() {
        // HardLine + Line/SoftLine collapses to just the HardLine.
        let doc = cat(vec![
            text("a"),
            hardline(0),
            line(),
            text("b"),
            hardline(1),
            softline(),
            text("c"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![
                text("a"),
                hardline(0),
                text("b"),
                hardline(1),
                text("c")
            ])
        );
    }

    #[test]
    fn standalone_separator_without_spacing_or_trivia_disappears() {
        let doc = cat(vec![text("a"), sep(None, None, false), text("b")]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(resolved, cat(vec![text("a"), text("b")]));
    }

    #[test]
    fn text_newline_before_separator_becomes_hardline() {
        // mutate_text_newline: Text("\n") + SeparatorSpec(spacing=Some) -> HardLine{0}.
        let doc = cat(vec![text("\n"), sep(Some(line()), None, false), text("x")]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(resolved, cat(vec![hardline(0), text("x")]));
    }

    #[test]
    fn extract_boundary_specs_only_leading() {
        // Port of test_extract_boundary_specs_only_leading.
        let docs = vec![
            rc(before(line())),
            rc(before(softline())),
            rc(text("content")),
        ];
        let (leading, remaining, trailing) = extract_boundary_specs(docs);
        assert_eq!(leading, vec![rc(before(line())), rc(before(softline()))]);
        assert_eq!(remaining, vec![rc(text("content"))]);
        assert!(trailing.is_empty());
    }

    #[test]
    fn extract_boundary_specs_only_trailing() {
        // Port of test_extract_boundary_specs_only_trailing.
        let docs = vec![
            rc(text("content")),
            rc(after(line())),
            rc(after(softline())),
        ];
        let (leading, remaining, trailing) = extract_boundary_specs(docs);
        assert!(leading.is_empty());
        assert_eq!(remaining, vec![rc(text("content"))]);
        assert_eq!(trailing, vec![rc(after(line())), rc(after(softline()))]);
    }

    #[test]
    fn extract_boundary_specs_all_specs() {
        // Port of test_extract_boundary_specs_all_specs.
        let docs = vec![
            rc(before(line())),
            rc(before(softline())),
            rc(after(line())),
        ];
        let (leading, remaining, trailing) = extract_boundary_specs(docs);
        assert_eq!(leading, vec![rc(before(line())), rc(before(softline()))]);
        assert!(remaining.is_empty());
        assert_eq!(trailing, vec![rc(after(line()))]);
    }

    #[test]
    fn extract_boundary_specs_empty_list() {
        // Port of test_extract_boundary_specs_empty_list.
        let docs: Vec<Rc<Doc>> = Vec::new();
        let (leading, remaining, trailing) = extract_boundary_specs(docs);
        assert!(leading.is_empty());
        assert!(remaining.is_empty());
        assert!(trailing.is_empty());
    }

    #[test]
    #[should_panic(expected = "Separator has neither preserved trivia nor spacing")]
    fn separator_without_trivia_or_spacing_in_triple_panics() {
        // resolve_spacing's assert: After/Sep(None,None)/Before triple with a spacingless,
        // triviales separator fails, mirroring the Python RuntimeError.
        let doc = cat(vec![after(line()), sep(None, None, false), before(line())]);
        let _ = resolve_spacing_specs(doc);
    }

    #[test]
    fn separator_hardline_blank_lines_win_over_after_spec() {
        // pick_spacing_with_blank_lines: a separator HardLine with more blank lines beats
        // the flanking AfterSpec spacing.
        let doc = cat(vec![
            text("a"),
            after(line()),
            sep(Some(hardline(2)), None, true),
            text("b"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(resolved, cat(vec![text("a"), hardline(2), text("b")]));
    }

    #[test]
    fn nested_group_nest_extraction() {
        // Port of test_nested_group_nest_extraction.
        let doc = cat(vec![
            text("outer"),
            sep(Some(nil()), None, true),
            Doc::Group(rc(Doc::Nest {
                indent: 2,
                content: rc(cat(vec![
                    before(line()),
                    before(softline()),
                    text("deeply"),
                    text("nested"),
                    after(softline()),
                    after(line()),
                ])),
            })),
            sep(Some(nil()), None, true),
            text("end"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![
                text("outer"),
                line(),
                Doc::Group(rc(Doc::Nest {
                    indent: 2,
                    content: rc(cat(vec![text("deeply"), text("nested")])),
                })),
                line(),
                text("end"),
            ])
        );
    }

    #[test]
    fn multiple_nested_groups() {
        // Port of test_multiple_nested_groups.
        let doc = Doc::Group(rc(cat(vec![
            text("start"),
            sep(Some(nil()), None, true),
            Doc::Group(rc(cat(vec![
                before(line()),
                text("inner"),
                after(softline()),
            ]))),
            sep(Some(line()), None, true),
            text("end"),
        ])));
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            Doc::Group(rc(cat(vec![
                text("start"),
                line(),
                Doc::Group(rc(text("inner"))),
                softline(),
                text("end"),
            ])))
        );
    }

    #[test]
    fn complex_multilevel_extraction() {
        // Port of test_complex_multilevel_extraction.
        let doc = cat(vec![
            text("a"),
            sep(Some(nil()), None, true),
            Doc::Group(rc(cat(vec![
                before(line()),
                Doc::Nest {
                    indent: 1,
                    content: rc(cat(vec![
                        before(softline()),
                        Doc::Group(rc(cat(vec![before(nil()), text("content"), after(nil())]))),
                        after(softline()),
                    ])),
                },
                after(line()),
            ]))),
            sep(Some(line()), None, true),
            text("b"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![
                text("a"),
                line(),
                Doc::Group(rc(Doc::Nest {
                    indent: 1,
                    content: rc(Doc::Group(rc(text("content")))),
                })),
                line(),
                text("b"),
            ])
        );
    }

    #[test]
    fn empty_group_with_specs() {
        // Port of test_empty_group_with_specs.
        let doc = cat(vec![
            text("before"),
            sep(Some(nil()), None, true),
            Doc::Group(rc(cat(vec![before(line()), after(softline())]))),
            sep(Some(nil()), None, true),
            text("after"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![
                text("before"),
                line(),
                Doc::Group(rc(nil())),
                softline(),
                text("after"),
            ])
        );
    }

    #[test]
    fn consecutive_groups_with_specs() {
        // Port of test_consecutive_groups_with_specs.
        let doc = cat(vec![
            Doc::Group(rc(cat(vec![text("first"), after(line())]))),
            sep(Some(softline()), None, true),
            Doc::Group(rc(cat(vec![before(softline()), text("second")]))),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![
                Doc::Group(rc(text("first"))),
                line(),
                Doc::Group(rc(text("second"))),
            ])
        );
    }

    #[test]
    fn deeply_nested_empty_structures() {
        // Port of test_deeply_nested_empty_structures.
        let doc = cat(vec![
            text("start"),
            sep(Some(nil()), None, true),
            Doc::Group(rc(Doc::Nest {
                indent: 1,
                content: rc(Doc::Group(rc(cat(vec![before(line()), after(line())])))),
            })),
            sep(Some(nil()), None, true),
            text("end"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![
                text("start"),
                line(),
                Doc::Group(rc(Doc::Nest {
                    indent: 1,
                    content: rc(Doc::Group(rc(nil()))),
                })),
                line(),
                text("end"),
            ])
        );
    }

    #[test]
    fn consecutive_specs_inside_group() {
        // Port of test_consecutive_specs_inside_group.
        let doc = cat(vec![
            text("before"),
            sep(Some(nil()), None, false),
            Doc::Group(rc(cat(vec![
                before(hardline(0)),
                before(hardline(1)),
                text("content"),
            ]))),
            text("after"),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![
                text("before"),
                hardline(1),
                Doc::Group(rc(text("content"))),
                text("after"),
            ])
        );
    }

    #[test]
    fn consecutive_leading_specs_in_group() {
        // Port of test_consecutive_leading_specs_in_group — the consecutive-spec-merging
        // regression target (trailing specs of one Group merging with leading specs of
        // the next across the gap).
        let doc = cat(vec![
            sep(Some(nil()), None, false),
            Doc::Group(rc(cat(vec![
                text("extern_type"),
                sep(Some(line()), None, true),
                text("CxxState"),
                sep(Some(nil()), None, false),
                text(";"),
                after(hardline(0)),
                sep(Some(nil()), None, false),
            ]))),
            Doc::Group(rc(cat(vec![
                before(hardline(0)),
                before(hardline(1)),
                text("//"),
                text(" "),
                text("Hello, Cog!"),
            ]))),
        ]);
        let resolved = resolve_spacing_specs(doc);
        assert_eq!(
            resolved,
            cat(vec![
                Doc::Group(rc(cat(vec![
                    text("extern_type"),
                    line(),
                    text("CxxState"),
                    text(";"),
                ]))),
                hardline(1),
                Doc::Group(rc(cat(vec![text("//"), text(" "), text("Hello, Cog!"),]))),
            ])
        );
    }
}
