"""Post-processing pass to resolve spacing control nodes."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from typing import Final

from fltk.unparse.combinators import (
    HARDLINE,
    LINE,
    SOFTLINE,
    AfterSpec,
    BeforeSpec,
    Concat,
    Doc,
    Group,
    HardLine,
    Join,
    Line,
    Nbsp,
    Nest,
    SeparatorSpec,
    SoftLine,
    Text,
    concat,
)


def resolve_spacing_specs(doc: Doc) -> Doc:
    """Post-process a Doc tree to resolve control nodes.

    This function walks the Doc tree and resolves AfterSpec, BeforeSpec,
    and SeparatorSpec nodes according to these rules:

    1. Smart merge of before/after if both are present
    2. SeparatorSpec is the fallback when no before/after specs apply
    3. If there is no SeparatorSpec, then After/Before are ignored
    4. If there is preserved trivia, that overrides everything

    This is done in three passes:
    - Initial pass: Expand Join nodes into docs with SeparatorSpecs
    - First pass: Extract all boundary specs recursively
    - Second pass: Apply pattern-based resolution
    """
    # Initial pass: Expand Join nodes
    expanded_doc = _expand_joins(doc)

    # First pass: Extract all boundary specs recursively
    extracted_doc, leading, trailing = _extract_all_boundary_specs(expanded_doc)
    # Second pass: Pattern-based resolution
    if leading or trailing:
        # If we have boundary specs at the top level, wrap in Concat to process them
        all_docs = [*leading, extracted_doc, *trailing]
        resolved_doc = _resolve_patterns(Concat(all_docs))
    else:
        resolved_doc = _resolve_patterns(extracted_doc)

    # import prettyprinter as pp
    # pp.install_extras()
    # print("BEFORE")
    # pp.pprint(doc)
    # print('EXPANDED')
    # pp.pprint(expanded_doc)
    # print("EXTRACTED")
    # pp.pprint(extracted_doc)
    # print("AFTER")
    # pp.pprint(resolved_doc)

    return resolved_doc


def _expand_joins(doc: Doc) -> Doc:
    """Initial pass: Expand Join nodes into docs with SeparatorSpecs.

    Join nodes are expanded into their constituent docs with SeparatorSpec
    nodes between them. The separator is placed in the preserved_trivia field
    to give it priority over other separators.
    """
    if isinstance(doc, Join):
        # Expand Join into docs with separators between
        if not doc.docs:
            return concat([])

        expanded = []
        trailing_separators = []
        need_sep = False
        for d in doc.docs:
            if isinstance(d, SeparatorSpec) and d.preserved_trivia is None:
                if not need_sep:
                    # Leading separators are preserved
                    expanded.append(d)
                else:
                    # This might be a trailing separator
                    trailing_separators.append(d)
                continue
            expanded_child = _expand_joins(d)

            if need_sep and not isinstance(d, AfterSpec | BeforeSpec):
                # Put the separator in preserved_trivia so it takes priority
                separator_spec = SeparatorSpec(spacing=None, preserved_trivia=doc.separator, required=False)
                expanded.append(separator_spec)
            expanded.append(expanded_child)
            trailing_separators.clear()
            if not isinstance(d, AfterSpec | BeforeSpec):
                need_sep = True
        expanded.extend(trailing_separators)

        return concat(expanded)

    elif isinstance(doc, Concat):
        # Recursively expand joins in all child docs
        expanded_docs = [_expand_joins(d) for d in doc.docs]
        return concat(expanded_docs)

    elif isinstance(doc, Group):
        return Group(_expand_joins(doc.content))

    elif isinstance(doc, Nest):
        return Nest(content=_expand_joins(doc.content), indent=doc.indent)

    else:
        # Leaf nodes pass through unchanged
        return doc


def _extract_all_boundary_specs(doc: Doc) -> tuple[Doc, list[Doc], list[Doc]]:
    """First pass: Recursively extract all boundary specs.

    Returns:
        A tuple of (processed_doc, leading_specs, trailing_specs)
    """
    if isinstance(doc, Concat):
        # Recursively process remaining docs
        processed_docs = []
        for child in doc.docs:
            processed_child, child_leading, child_trailing = _extract_all_boundary_specs(child)
            # Add extracted specs inline
            processed_docs.extend(child_leading)
            processed_docs.append(processed_child)
            processed_docs.extend(child_trailing)

        leading_specs, remaining_docs, trailing_specs = _extract_boundary_specs(processed_docs)
        return concat(remaining_docs), leading_specs, trailing_specs

    elif isinstance(doc, Group | Nest):
        processed_content, inner_leading, inner_trailing = _extract_all_boundary_specs(doc.content)

        if isinstance(doc, Group):
            return Group(processed_content), inner_leading, inner_trailing
        else:
            return Nest(content=processed_content, indent=doc.indent), inner_leading, inner_trailing
    else:
        # Leaf nodes pass through unchanged
        return doc, [], []


def _extract_boundary_specs(docs: list[Doc]) -> tuple[list[Doc], list[Doc], list[Doc]]:
    """Extract leading BeforeSpecs/SeparatorSpecs and trailing AfterSpecs/SeparatorSpecs from a list of docs.

    Returns:
        A tuple of (leading_specs, remaining_docs, trailing_specs)
    """
    # Extract trailing AfterSpecs and SeparatorSpecs
    trailing_specs = []
    while docs and isinstance(docs[-1], AfterSpec | SeparatorSpec):
        trailing_specs.insert(0, docs.pop())

    # Extract leading BeforeSpecs and SeparatorSpecs
    leading_specs = []
    while docs and isinstance(docs[0], BeforeSpec | SeparatorSpec):
        leading_specs.append(docs.pop(0))

    return leading_specs, docs, trailing_specs


def _resolve_patterns(doc: Doc) -> Doc:
    """Second pass: Apply pattern-based resolution to spacing specs.

    This processes the document after all boundary specs have been extracted
    and applies the pattern matching rules to resolve them into actual spacing.
    """
    if isinstance(doc, Concat):
        # Apply pattern resolution to the sequence
        resolved_docs = _resolve_concat_patterns(doc.docs)
        return concat(resolved_docs)
    elif isinstance(doc, Group):
        return Group(_resolve_patterns(doc.content))
    elif isinstance(doc, Nest):
        return Nest(content=_resolve_patterns(doc.content), indent=doc.indent)
    else:
        # Leaf nodes pass through
        resolved_docs = _resolve_concat_patterns([doc])
        return concat(resolved_docs)


# Type for pattern mutator functions
# They take a working set and return either:
# - None if pattern doesn't match
# - A new list of docs if pattern matches and was mutated
PatternMutator = Callable[[deque[Doc]], list[Doc] | None]


def _resolve_concat_patterns(docs: Sequence[Doc]) -> list[Doc]:
    """Resolve control nodes in a sequence of docs using pattern matching.

    This is the second pass - all boundary specs have already been extracted,
    so we just need to apply the pattern matching rules.
    """
    # Validate all docs are instances
    for i, doc in enumerate(docs):
        if not isinstance(doc, Doc):
            msg = f"_resolve_concat_patterns received {type(doc).__name__} at index {i} instead of a Doc instance"
            raise RuntimeError(msg)

    # Mutators in order of precedence
    mutators: list[tuple[int, PatternMutator]] = [
        # Pattern: AfterSpec, SeparatorSpec, BeforeSpec
        (3, _mutate_after_sep_before),
        # Pattern: AfterSpec, SeparatorSpec
        (2, _mutate_after_sep),
        # Pattern: SeparatorSpec, BeforeSpec
        (2, _mutate_sep_before),
        # Pattern: Text('\n') + space combinator -> HARDLINE
        (2, _mutate_text_newline),
        # Pattern: standalone SeparatorSpec
        (1, _mutate_standalone_sep),
        # Pattern: standalone AfterSpec or BeforeSpec
        (1, _mutate_standalone_after_before),
    ]

    # Find maximum pattern size
    max_pattern_size = max(size for size, _ in mutators)

    # Initialize working set and output
    working_set = deque[Doc]()
    output: list[Doc] = []
    doc_iter = iter(docs)

    while True:
        # Step 1: Fill working set to max_pattern_size + 1 to ensure we can see consecutive specs
        # that might span beyond the largest pattern
        while len(working_set) < max_pattern_size + 1:
            try:
                next_doc = next(doc_iter)
                # Recursively process Group and Nest nodes
                if isinstance(next_doc, Group | Nest | Concat):
                    next_doc = _resolve_patterns(next_doc)
                working_set.append(next_doc)
            except StopIteration:
                break

        # If working set is empty, we're done
        if not working_set:
            break

        # Step 2: Always try to collapse consecutive specs first
        result = _mutate_consecutive_specs(working_set)
        if result is not None:
            # Replace entire working set with collapsed result
            working_set.clear()
            working_set.extend(result)
            continue  # Go back to start of loop

        # Step 3: Try each other mutator in order
        mutated = False
        for pattern_size, mutator in mutators:
            # Only try mutator if we have enough items
            if len(working_set) >= pattern_size:
                # Extract the items this mutator will examine
                result = mutator(working_set)
                if result is not None:
                    # Pattern matched and was mutated
                    # Remove the consumed items from working set
                    for _ in range(pattern_size):
                        working_set.popleft()
                    # Add mutated results back to front of working set
                    for doc in reversed(result):
                        working_set.appendleft(doc)
                    mutated = True
                    break

        # Step 4: If no mutator matched, pop and produce the head
        if not mutated:
            output.append(working_set.popleft())

    return output


def _mutate_after_sep_before(working_set: deque[Doc]) -> list[Doc] | None:
    """Pattern: AfterSpec, SeparatorSpec, BeforeSpec."""
    pattern_size: Final = 3
    if len(working_set) < pattern_size:
        return None

    if (
        isinstance(working_set[0], AfterSpec)
        and isinstance(working_set[1], SeparatorSpec)
        and isinstance(working_set[2], BeforeSpec)
    ):
        after_spec = working_set[0]
        sep_spec = working_set[1]
        before_spec = working_set[2]

        spacing = _resolve_spacing(after_spec, before_spec, sep_spec)
        return [spacing] if spacing is not None else []

    return None


def _mutate_after_sep(working_set: deque[Doc]) -> list[Doc] | None:
    """Pattern: AfterSpec, SeparatorSpec."""
    pattern_size = 2
    if len(working_set) < pattern_size:
        return None

    if isinstance(working_set[0], AfterSpec) and isinstance(working_set[1], SeparatorSpec):
        after_spec = working_set[0]
        sep_spec = working_set[1]

        if sep_spec.preserved_trivia:
            # Recursively resolve the preserved trivia
            resolved_trivia = resolve_spacing_specs(sep_spec.preserved_trivia)
            return [resolved_trivia]
        elif sep_spec.spacing is not None or sep_spec.required:
            # Use the after spacing
            return [after_spec.spacing] if after_spec.spacing is not None else []
        else:
            # No separator, ignore after spec
            return []

    return None


def _mutate_sep_before(working_set: deque[Doc]) -> list[Doc] | None:
    """Pattern: SeparatorSpec, BeforeSpec."""
    pattern_size = 2
    if len(working_set) < pattern_size:
        return None

    if isinstance(working_set[0], SeparatorSpec) and isinstance(working_set[1], BeforeSpec):
        sep_spec = working_set[0]
        before_spec = working_set[1]

        if sep_spec.preserved_trivia:
            # Recursively resolve the preserved trivia
            resolved_trivia = resolve_spacing_specs(sep_spec.preserved_trivia)
            return [resolved_trivia]
        elif sep_spec.spacing is not None or sep_spec.required:
            # Use the before spacing
            return [before_spec.spacing] if before_spec.spacing is not None else []
        else:
            # No separator, ignore before spec
            return []

    return None


def _mutate_standalone_sep(working_set: deque[Doc]) -> list[Doc] | None:
    """Pattern: standalone SeparatorSpec."""
    if len(working_set) < 1:
        return None

    if isinstance(working_set[0], SeparatorSpec):
        sep_spec = working_set[0]

        if sep_spec.preserved_trivia:
            # Recursively resolve the preserved trivia
            resolved_trivia = resolve_spacing_specs(sep_spec.preserved_trivia)
            return [resolved_trivia]
        elif sep_spec.spacing is not None:
            # Return the spacing instance
            return [sep_spec.spacing]
        else:
            # SeparatorSpec with no spacing and no trivia - remove it
            return []

    return None


def _mutate_standalone_after_before(working_set: deque[Doc]) -> list[Doc] | None:
    """Pattern: standalone AfterSpec or BeforeSpec."""
    if len(working_set) < 1:
        return None

    if isinstance(working_set[0], AfterSpec | BeforeSpec):
        # Standalone after/before specs are ignored
        return []

    return None


def _mutate_text_newline(working_set: deque[Doc]) -> list[Doc] | None:
    """Pattern: Text('\n') followed by SeparatorSpec with spacing -> HARDLINE."""
    min_consecutive_size = 2
    if len(working_set) < min_consecutive_size:
        return None

    if isinstance(working_set[0], Text) and working_set[0].content == "\n":
        # Check if next element is a SeparatorSpec with spacing
        next_doc = working_set[1]
        if isinstance(next_doc, SeparatorSpec) and next_doc.spacing is not None:
            # Convert Text('\n') + SeparatorSpec to just HARDLINE
            return [HARDLINE]

    return None


def _mutate_consecutive_specs(working_set: deque[Doc]) -> list[Doc] | None:
    """Collapse all consecutive spacing specs (BeforeSpec, AfterSpec, SeparatorSpec) in the working set."""
    min_consecutive_size = 2
    if len(working_set) < min_consecutive_size:
        return None

    # Collapse all consecutive specs of the same type
    result = []
    i = 0
    merged = False
    while i < len(working_set):
        curr = working_set[i]

        # Check if this starts a run of consecutive specs of the same type
        if isinstance(curr, BeforeSpec | AfterSpec | SeparatorSpec):
            j = i + 1

            # For BeforeSpec: merge consecutive BeforeSpecs
            if isinstance(curr, BeforeSpec):
                merged_spacing = curr.spacing
                while j < len(working_set) and isinstance(nxt := working_set[j], BeforeSpec):
                    merged = True
                    merged_spacing = _merge_spacing(merged_spacing, nxt.spacing)
                    j += 1
                if merged_spacing:
                    result.append(BeforeSpec(spacing=merged_spacing))
                i = j

            # For AfterSpec: merge consecutive AfterSpecs
            elif isinstance(curr, AfterSpec):
                merged_spacing = curr.spacing
                while j < len(working_set) and isinstance(nxt := working_set[j], AfterSpec):
                    merged = True
                    merged_spacing = _merge_spacing(merged_spacing, nxt.spacing)
                    j += 1
                if merged_spacing:
                    result.append(AfterSpec(spacing=merged_spacing))
                i = j

            # For SeparatorSpec: handle consecutive SeparatorSpecs
            elif isinstance(curr, SeparatorSpec):
                # Look ahead to see if we have consecutive SeparatorSpecs
                if j < len(working_set) and isinstance(next_item := working_set[j], SeparatorSpec):
                    # We have two consecutive SeparatorSpecs
                    if curr.preserved_trivia and next_item.preserved_trivia:
                        # Both have trivia - keep both
                        result.append(curr)
                        i += 1
                    elif curr.preserved_trivia:
                        # Only curr has trivia - keep curr, skip next
                        merged = True
                        result.append(curr)
                        i = j + 1
                    elif next_item.preserved_trivia:
                        # Only next has trivia - skip curr, process next on next iteration
                        merged = True
                        i = j
                    else:
                        # Neither has trivia - merge them
                        merged = True
                        merged_spacing = _merge_spacing(curr.spacing, next_item.spacing)
                        merged_required = curr.required or next_item.required
                        if merged_spacing is not None or merged_required:
                            result.append(
                                SeparatorSpec(spacing=merged_spacing, preserved_trivia=None, required=merged_required)
                            )
                        i = j + 1
                else:
                    # No consecutive SeparatorSpec - keep curr as is
                    result.append(curr)
                    i += 1
        else:
            # Not a spec, keep as is
            result.append(curr)
            i += 1

    return result if merged else None


def _resolve_spacing(after_spec: AfterSpec, before_spec: BeforeSpec, sep_spec: SeparatorSpec) -> Doc | None:
    """Resolve spacing when both after and before specs are present.

    Returns the resolved spacing or None if no spacing should be added.
    """
    # If there's preserved trivia, use it (recursively resolved)
    if sep_spec.preserved_trivia:
        return resolve_spacing_specs(sep_spec.preserved_trivia)

    # If separator doesn't allow spacing, ignore both specs
    if sep_spec.spacing is None:
        msg = f"Separator has neither preserved trivia nor spacing: {sep_spec}"
        raise RuntimeError(msg)

    # Smart merge of after and before specs
    return _merge_spacing(after_spec.spacing, before_spec.spacing)


def _merge_spacing(spacing1: Doc | None, spacing2: Doc | None) -> Doc | None:
    """Merge two spacing instances according to precedence rules."""
    if spacing1 is None and spacing2 is None:
        return None
    if spacing1 is None:
        return spacing2
    if spacing2 is None:
        return spacing1

    if spacing1 == spacing2:
        return spacing1

    # Handle specific combinations
    if isinstance(spacing1, HardLine) or isinstance(spacing2, HardLine):
        # HardLine wins over everything
        if isinstance(spacing1, HardLine) and isinstance(spacing2, HardLine):
            # Use the one with more blank lines
            return spacing1 if spacing1.blank_lines >= spacing2.blank_lines else spacing2
        return spacing1 if isinstance(spacing1, HardLine) else spacing2

    if isinstance(spacing1, Line) or isinstance(spacing2, Line):
        # Line wins over SoftLine, Nbsp, Nil
        return LINE

    if isinstance(spacing1, Nbsp) or isinstance(spacing2, Nbsp):
        # Nbsp wins over SoftLine, Nil
        return spacing1 if isinstance(spacing1, Nbsp) else spacing2

    if isinstance(spacing1, SoftLine) or isinstance(spacing2, SoftLine):
        # SoftLine wins over Nil
        return SOFTLINE

    # Default: use spacing2 (it's closer to the following content)
    return spacing2
