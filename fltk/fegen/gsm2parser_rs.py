"""Rust parser code generator for fltk.fegen grammars.

Generates a standalone .rs file implementing a packrat parser that
produces CST nodes from the generated cst.rs module.

Regex subset restriction: grammar regexes must use the common subset of Python ``re``
and ``regex-syntax`` (shared by the ``regex`` and ``regex-automata`` crates).  Lookahead,
lookbehind, and backreferences are not supported; ``regex_automata::meta::Regex`` rejects
them at compile time.  The generated ``#[test] fn all_regex_patterns_compile`` (emitted
into every generated parser) enforces this by attempting
``regex_automata::meta::Regex::new(pattern)`` for each pattern at ``cargo test`` time,
naming any unsupported pattern in the failure message.  See ADR
``docs/adr/2026/06/10-rust-parser-codegen/README.md`` §Regex subset for the full
constraint and the rationale for keeping it as the permanent default.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from dataclasses import dataclass

from fltk.fegen import gsm
from fltk.fegen.gsm2tree_rs import RustCstGenerator

# Code point thresholds for Rust string literal escaping
_CTRL_MAX = 0x20  # exclusive: code points < 0x20 get \u{XX} escaping
_DEL = 0x7F  # DEL character: also gets \u{XX} escaping


def _rust_str_lit(s: str) -> str:
    """Return the Rust string literal content (no outer quotes) for string s."""
    out = []
    for ch in s:
        cp = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif cp < _CTRL_MAX or cp == _DEL:
            out.append(f"\\u{{{cp:02x}}}")
        else:
            out.append(ch)
    return "".join(out)


@dataclass
class ResultTy:
    """Type information for a parser function's return value."""

    is_span: bool
    class_name: str | None  # None for span results; class name for node results


@dataclass
class RustParserFn:
    """Metadata for a generated Rust parser function."""

    name: str  # e.g. "parse_grammar" or "parse_grammar__alt0__item0__alts"
    apply_name: str  # "apply__parse_grammar" iff memoized, else == name
    cache_field: str | None  # "cache__parse_grammar" iff memoized, else None
    result: ResultTy
    rule_id: int | None  # index into grammar.rules iff memoized, else None
    inline_to_parent: bool


class RustParserGenerator:
    """Generates a complete .rs parser file from a gsm.Grammar.

    Takes a raw gsm.Grammar (not yet trivia-processed) and produces a string
    containing a complete, compilable .rs file.
    """

    def __init__(
        self,
        grammar: gsm.Grammar,
        cst_mod_path: str = "super::cst",
        source_name: str | None = None,
    ):
        self._cst = RustCstGenerator(grammar)
        # Work from the grammar with trivia rules added and classified
        self._grammar = self._cst.grammar
        self._cst_mod_path = cst_mod_path
        # None means "omit the 'from <source_name>' clause" in the header (design §2.2).
        self._source_name: str | None = source_name

        # Regex table: pattern -> index
        self._regex_patterns: list[str] = []
        self._regex_index: dict[str, int] = {}

        # Track which helper methods are needed
        self._uses_literal: bool = False
        self._uses_regex: bool = False

        # Parser function registry: path tuple -> RustParserFn
        self._parsers: dict[tuple[str, ...], RustParserFn] = {}

        # Rule ID counter (for memoized rules)
        self._rule_id_seq = itertools.count(0)

        # Accumulated function body code strings (in order)
        self._fn_bodies: list[str] = []

        # Memoized result of generate() — set on first call to prevent double-emit
        self._generated: str | None = None

        # First pass: register all top-level rule parser infos (memoized).
        # Also validate that every Identifier term in every rule body references
        # a rule present in the grammar.  Doing this here (a) catches dangling
        # references at construction time alongside the other validation, and (b)
        # ensures the bare dict lookup in _gen_consume_term never KeyErrors at
        # generation time.
        known_rule_names: set[str] = {rule.name for rule in self._grammar.rules}

        def _validate_term(rule_name: str, term: gsm.Term) -> None:
            """Recursively validate all Identifier terms in a term, including sub-expressions."""
            if isinstance(term, gsm.Identifier):
                if term.value not in known_rule_names:
                    msg = f"Rule '{rule_name}' references unknown rule '{term.value}'"
                    raise ValueError(msg)
            elif isinstance(term, list | tuple):
                # Sub-expression: list/tuple of Items — recurse into each alternative's items.
                for sub_alt in term:
                    for sub_item in sub_alt.items:
                        _validate_term(rule_name, sub_item.term)

        for rule in self._grammar.rules:
            class_name = self._cst._py_gen.class_name_for_rule_node(rule.name)
            result = ResultTy(is_span=False, class_name=class_name)
            path = (rule.name,)
            self._make_parser_info(path, result, memoize=True)
            for alt in rule.alternatives:
                for item in alt.items:
                    _validate_term(rule.name, item.term)

    def _regex_idx(self, pattern: str) -> int:
        """Add pattern to regex table if not present; return its index."""
        if pattern not in self._regex_index:
            self._regex_index[pattern] = len(self._regex_patterns)
            self._regex_patterns.append(pattern)
        return self._regex_index[pattern]

    def _make_parser_info(
        self,
        path: tuple[str, ...],
        result: ResultTy,
        *,
        memoize: bool = False,
        inline_to_parent: bool = False,
    ) -> RustParserFn:
        """Create and store a RustParserFn for the given path."""
        name = "parse_" + "__".join(path)
        if memoize:
            apply_name = "apply__" + name
            cache_field = "cache__" + name
            rule_id = next(self._rule_id_seq)
        else:
            apply_name = name
            cache_field = None
            rule_id = None

        fn = RustParserFn(
            name=name,
            apply_name=apply_name,
            cache_field=cache_field,
            result=result,
            rule_id=rule_id,
            inline_to_parent=inline_to_parent,
        )
        self._parsers[path] = fn
        return fn

    def _cache_parser_info(
        self,
        path: tuple[str, ...],
        result: ResultTy,
        *,
        memoize: bool = False,
        inline_to_parent: bool = False,
    ) -> RustParserFn:
        """Return existing RustParserFn for path, or create a new one."""
        if path in self._parsers:
            return self._parsers[path]
        return self._make_parser_info(path, result, memoize=memoize, inline_to_parent=inline_to_parent)

    def _class_name(self, rule_name: str) -> str:
        """Return CamelCase class name for a rule."""
        return self._cst._py_gen.class_name_for_rule_node(rule_name)

    def _child_enum_name(self, rule_name: str) -> str:
        return self._cst.child_enum_name(self._class_name(rule_name))

    def _label_type_info(self, rule_name: str, label: str) -> tuple[str, str | None, int]:
        """Delegate to the CST generator's label type info."""
        return self._cst._label_type_info(rule_name, label)

    def generate(self) -> str:
        """Generate the complete .rs parser source.

        Idempotent: a second call on the same instance returns the previously
        generated string without re-running emission (which would duplicate fn
        definitions and produce uncompilable output — correctness-3).
        """
        if self._generated is not None:
            return self._generated
        # Second pass: generate all function bodies
        for rule in self._grammar.rules:
            self._gen_rule(rule)

        parts: list[str] = []

        # Section 1: Header
        parts.append(self._gen_header())

        # Section 2: RULE_NAMES + regex table
        parts.append(self._gen_constants())

        # Section 3: Parser struct + constructors
        parts.append(self._gen_parser_struct())

        # Section 4: consume_literal / consume_regex helpers (only if used)
        if self._uses_literal or self._uses_regex:
            parts.append(self._gen_consume_helpers())

        # Section 5+: all accumulated function bodies
        parts.append("\n".join(self._fn_bodies))

        # Close the impl block
        parts.append("}")

        # Section 6: generated regex compile test (only when regex table is non-empty)
        if self._regex_patterns:
            parts.append(self._gen_regex_compile_test())

        # Section 7: python-gated bindings block
        parts.append(self._gen_python_bindings())

        self._generated = "\n".join(p for p in parts if p) + "\n"
        return self._generated

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _gen_header(self) -> str:
        lines = []
        if self._source_name is not None:
            escaped = _rust_str_lit(self._source_name)
            lines.append(f"//! Generated by fltk gen-rust-parser from `{escaped}`. Do not edit.")
        else:
            lines.append("//! Generated by fltk gen-rust-parser. Do not edit.")
        lines.append("//! **Stack depth note**: this parser is recursive-descent. Rule-application depth is")
        lines.append("//! bounded by `max_depth` (default `fltk_parser_core::DEFAULT_MAX_DEPTH`, configurable")
        lines.append("//! via `Parser::set_max_depth`). Exceeding it fails the parse with")
        lines.append("//! `Parser::depth_exceeded()` set (Python bindings raise `RecursionError`) rather than")
        lines.append("//! overflowing the native stack. **The default limit is sized for an ~8 MiB stack and")
        lines.append("//! ~5-7 native frames per rule application.** Callers on smaller thread stacks (Rust")
        lines.append("//! spawned threads use 2 MiB; async-runtime worker threads vary) or with grammars")
        lines.append("//! that have deep per-rule call structure must lower `max_depth` proportionally or")
        lines.append("//! size the stack accordingly. Check `depth_exceeded()` after parsing; a result")
        lines.append("//! produced with the flag set must be discarded.")
        lines.append("// Allow double-underscore names used in generated parse function paths.")
        lines.append("#![allow(non_snake_case)]")
        lines.append("")

        # OnceLock + Regex only if regex table is non-empty (populated during body gen)
        if self._regex_patterns:
            lines.append("use std::sync::OnceLock;")
            lines.append("use fltk_parser_core::regex_automata::meta::Regex;")
            lines.append("")

        lines.append("use fltk_cst_core::{Shared, SourceText, Span};")
        lines.append("use fltk_parser_core::{apply, ApplyResult, Cache, ErrorTracker, PackratState, TerminalSource};")
        lines.append("")

        # CST module import
        segments = self._cst_mod_path.split("::")
        if segments[-1] == "cst":
            cst_import = f"use {self._cst_mod_path};"
        else:
            cst_import = f"use {self._cst_mod_path} as cst;"
        lines.append(cst_import)
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Constants: RULE_NAMES + regex table
    # ------------------------------------------------------------------

    def _gen_constants(self) -> str:
        lines = []
        rule_names = [rule.name for rule in self._grammar.rules]
        n = len(rule_names)
        names_lit = ", ".join(f'"{_rust_str_lit(name)}"' for name in rule_names)
        lines.append(f"pub const RULE_NAMES: [&str; {n}] = [{names_lit}];")
        lines.append("")

        # generate() calls _gen_rule() for all rules before calling _gen_constants(), so
        # self._regex_patterns is complete here.

        if self._regex_patterns:
            r = len(self._regex_patterns)
            patterns_lit = ", ".join(f'"{_rust_str_lit(p)}"' for p in self._regex_patterns)
            lines.append(f"const REGEX_PATTERNS: [&str; {r}] = [{patterns_lit}];")
            # Static array of OnceLock<Regex>
            cells = ", ".join("OnceLock::new()" for _ in self._regex_patterns)
            lines.append(f"static REGEX_CELLS: [OnceLock<Regex>; {r}] = [{cells}];")
            lines.append("")
            lines.append("fn regex_at(idx: usize) -> &'static Regex {")
            lines.append("    REGEX_CELLS[idx].get_or_init(|| {")
            lines.append(
                "        Regex::new(REGEX_PATTERNS[idx])"
                '\n            .unwrap_or_else(|e| panic!("invalid regex pattern {:?}: {e}",'
                " REGEX_PATTERNS[idx]))"
            )
            lines.append("    })")
            lines.append("}")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Parser struct + constructors
    # ------------------------------------------------------------------

    def _gen_parser_struct(self) -> str:
        """Generate the Parser struct, its impl block header, and public accessors.

        Opens but does not close the impl Parser block; _gen_consume_helpers and
        the per-rule fn bodies are appended inside the same block by generate().
        """
        lines = []
        lines.append("pub struct Parser {")
        lines.append("    terminals: TerminalSource,")
        lines.append("    packrat: PackratState,")
        lines.append("    error_tracker: ErrorTracker,")
        lines.append("    capture_trivia: bool,")

        # One cache field per top-level (memoized) rule
        for rule in self._grammar.rules:
            path = (rule.name,)
            fn_info = self._parsers[path]
            class_name = self._class_name(rule.name)
            lines.append(f"    {fn_info.cache_field}: Cache<Shared<cst::{class_name}>>,")

        lines.append("}")
        lines.append("")

        # impl Parser constructors and helpers
        lines.append("impl Parser {")
        lines.append("    pub fn new(text: &str, capture_trivia: bool) -> Self {")
        lines.append("        Self::from_source_text(SourceText::from_str(text), capture_trivia)")
        lines.append("    }")
        lines.append("")
        lines.append("    pub fn from_source_text(source: SourceText, capture_trivia: bool) -> Self {")
        lines.append("        let terminals = TerminalSource::from_source_text(source);")
        lines.append("        Self {")
        lines.append("            terminals,")
        lines.append("            packrat: PackratState::default(),")
        lines.append("            error_tracker: ErrorTracker::default(),")
        lines.append("            capture_trivia,")
        for rule in self._grammar.rules:
            path = (rule.name,)
            fn_info = self._parsers[path]
            lines.append(f"            {fn_info.cache_field}: Cache::new(),")
        lines.append("        }")
        lines.append("    }")
        lines.append("")
        lines.append("    pub fn terminals(&self) -> &TerminalSource { &self.terminals }")
        lines.append("    pub fn capture_trivia(&self) -> bool { self.capture_trivia }")
        lines.append("    pub fn rule_names(&self) -> &'static [&'static str] { &RULE_NAMES }")
        lines.append("")
        lines.append("    /// Return a human-readable parse error message.")
        lines.append("    ///")
        lines.append("    /// If `depth_exceeded()` is true, returns a depth-limit diagnostic instead of")
        lines.append("    /// the normal longest-match error — the error tracker state is unreliable when")
        lines.append("    /// depth was exceeded.")
        lines.append("    pub fn error_message(&self) -> String {")
        lines.append("        if self.packrat.depth_exceeded() {")
        lines.append(
            '            return format!("parse aborted: depth limit exceeded (max_depth = {})",'
            " self.packrat.max_depth());"
        )
        lines.append("        }")
        lines.append(
            "        fltk_parser_core::format_error_message(&self.error_tracker, &self.terminals, &RULE_NAMES)"
        )
        lines.append("    }")
        lines.append("")
        lines.append("    pub fn error_position(&self) -> Option<i64> {")
        lines.append(
            "        (self.error_tracker.longest_parse_len >= 0).then_some(self.error_tracker.longest_parse_len)"
        )
        lines.append("    }")
        lines.append("")
        lines.append("    /// Set the maximum rule-application depth before the parse fails with the")
        lines.append("    /// depth-exceeded flag. Call before parsing.")
        lines.append("    /// Default: `fltk_parser_core::DEFAULT_MAX_DEPTH`.")
        lines.append("    pub fn set_max_depth(&mut self, max_depth: u32) { self.packrat.set_max_depth(max_depth); }")
        lines.append("")
        lines.append("    /// Return the current maximum rule-application depth limit.")
        lines.append("    pub fn max_depth(&self) -> u32 { self.packrat.max_depth() }")
        lines.append("")
        lines.append("    /// Return true if the depth limit was exceeded during parsing.")
        lines.append("    ///")
        lines.append("    /// When true, the parse result (even if `Some`) must be discarded — it may be")
        lines.append("    /// a partial or wrong parse. This instance is spent; construct a fresh `Parser`.")
        lines.append("    pub fn depth_exceeded(&self) -> bool { self.packrat.depth_exceeded() }")

        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Consume helpers
    # ------------------------------------------------------------------

    def _gen_consume_helpers(self) -> str:
        lines = []

        if self._uses_literal:
            lines.append(
                "    fn consume_literal(&mut self, pos: i64, literal: &'static str) -> Option<ApplyResult<Span>> {"
            )
            lines.append("        if let Some(span) = self.terminals.consume_literal(pos, literal) {")
            lines.append("            return Some(ApplyResult { pos: span.end(), result: span });")
            lines.append("        }")
            lines.append("        let rule_id = *self.packrat.invocation_stack.last()")
            lines.append('            .expect("consume_literal called outside apply__* frame");')
            lines.append("        self.error_tracker.fail_literal(pos, rule_id, literal);")
            lines.append("        None")
            lines.append("    }")
            lines.append("")

        if self._uses_regex:
            lines.append("    fn consume_regex(&mut self, pos: i64, regex_idx: usize) -> Option<ApplyResult<Span>> {")
            lines.append("        if let Some(span) = self.terminals.consume_regex(pos, regex_at(regex_idx)) {")
            lines.append("            return Some(ApplyResult { pos: span.end(), result: span });")
            lines.append("        }")
            lines.append("        let rule_id = *self.packrat.invocation_stack.last()")
            lines.append('            .expect("consume_regex called outside apply__* frame");')
            lines.append("        self.error_tracker.fail_regex(pos, rule_id, REGEX_PATTERNS[regex_idx]);")
            lines.append("        None")
            lines.append("    }")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Rule generation (second pass)
    # ------------------------------------------------------------------

    def _gen_rule(self, rule: gsm.Rule) -> None:
        """Generate all parser functions for a grammar rule."""
        path = (rule.name,)
        fn_info = self._parsers[path]
        class_name = self._class_name(rule.name)

        # apply__ wrapper (memoized)
        self._emit_apply_wrapper(fn_info, class_name)

        # parse_X function: tries alternatives, wraps result in Shared::new
        self._emit_rule_body(path, fn_info, class_name, rule)

    def _emit_apply_wrapper(self, fn_info: RustParserFn, class_name: str) -> None:
        """Emit the pub apply__ memoized wrapper."""
        lines = []
        rule_id = fn_info.rule_id
        lines.append(
            f"    pub fn {fn_info.apply_name}(&mut self, pos: i64) -> Option<ApplyResult<Shared<cst::{class_name}>>> {{"
        )
        lines.append(
            f"        apply(self, {rule_id}u32, pos,"
            f" |p| &mut p.packrat,"
            f" |p| &mut p.{fn_info.cache_field},"
            f" Self::{fn_info.name})"
        )
        lines.append("    }")
        lines.append("")
        self._fn_bodies.append("\n".join(lines))

    def _emit_rule_body(self, path: tuple[str, ...], fn_info: RustParserFn, class_name: str, rule: gsm.Rule) -> None:
        """Emit the private parse_X function that tries each alternative."""
        lines = []
        lines.append(f"    fn {fn_info.name}(&mut self, pos: i64) -> Option<ApplyResult<Shared<cst::{class_name}>>> {{")

        for alt_idx, alt in enumerate(rule.alternatives):
            alt_path = (*path, f"alt{alt_idx}")
            alt_fn = self._gen_alternative(alt_path, rule, alt)
            alt_var = f"alt{alt_idx}"
            lines.append(f"        if let Some({alt_var}) = self.{alt_fn.name}(pos) {{")
            lines.append(
                f"            return Some(ApplyResult {{ pos: {alt_var}.pos, result: Shared::new({alt_var}.result) }});"
            )
            lines.append("        }")

        lines.append("        None")
        lines.append("    }")
        lines.append("")
        self._fn_bodies.append("\n".join(lines))

    # ------------------------------------------------------------------
    # Alternative generation
    # ------------------------------------------------------------------

    def _gen_alternative(self, path: tuple[str, ...], rule: gsm.Rule, alt: gsm.Items) -> RustParserFn:
        """Generate the alternative body function and return its RustParserFn."""
        class_name = self._class_name(rule.name)
        result = ResultTy(is_span=False, class_name=class_name)
        fn_info = self._cache_parser_info(path, result)

        lines = []
        lines.append(f"    fn {fn_info.name}(&mut self, mut pos: i64) -> Option<ApplyResult<cst::{class_name}>> {{")
        lines.append("        let span_start = pos;")
        # Use Span::unknown() for the placeholder; set_span below supplies the real span.
        # Avoids an Arc clone of the source text on every (typically failing) alternative
        # attempt (efficiency-2).
        lines.append(f"        let mut result = cst::{class_name}::new(Span::unknown());")

        # Handle initial_sep
        if alt.initial_sep != gsm.Separator.NO_WS:
            sep_code = self._gen_separator_code(alt.initial_sep, rule)
            if sep_code:
                lines.append(sep_code)

        # Handle each item
        for item_idx, item in enumerate(alt.items):
            item_path = (*path, f"item{item_idx}")
            item_fn = self._gen_item(item_path, rule, item, class_name)

            item_var = f"item{item_idx}"
            if item.quantifier.is_optional():
                # Optional item: no else clause
                lines.append(f"        if let Some({item_var}) = self.{item_fn.name}(pos) {{")
                lines.append(f"            pos = {item_var}.pos;")
                append_code = self._gen_append_code(item, item_var, item_fn, rule, class_name)
                if append_code:
                    lines.append(f"            {append_code}")
                lines.append("        }")
            else:
                # Required item
                lines.append(f"        if let Some({item_var}) = self.{item_fn.name}(pos) {{")
                lines.append(f"            pos = {item_var}.pos;")
                append_code = self._gen_append_code(item, item_var, item_fn, rule, class_name)
                if append_code:
                    lines.append(f"            {append_code}")
                lines.append("        } else {")
                lines.append("            return None;")
                lines.append("        }")

            # sep_after for this item (if not last item or always)
            if item_idx < len(alt.sep_after):
                sep = alt.sep_after[item_idx]
                if sep != gsm.Separator.NO_WS:
                    sep_code = self._gen_separator_code(sep, rule)
                    if sep_code:
                        lines.append(sep_code)

        lines.append("        result.set_span(Span::new_with_source(span_start, pos, self.terminals.source_text()));")
        lines.append("        Some(ApplyResult { pos, result })")
        lines.append("    }")
        lines.append("")
        self._fn_bodies.append("\n".join(lines))

        return fn_info

    def _gen_separator_code(self, sep: gsm.Separator, rule: gsm.Rule) -> str:
        """Generate Rust code for a separator."""
        if sep == gsm.Separator.NO_WS:
            return ""

        child_enum = self._child_enum_name(rule.name)

        if rule.is_trivia_rule:
            # Within trivia rules, whitespace is just a regex (matches Python reference \s+).
            ws_pattern = r"\s+"
            ws_idx = self._regex_idx(ws_pattern)
            self._uses_regex = True
            trivia_span_variant = "Span"
            if sep == gsm.Separator.WS_ALLOWED:
                return (
                    f"        if let Some(ws) = self.consume_regex(pos, {ws_idx}) {{\n"
                    f"            pos = ws.pos;\n"
                    f"            if self.capture_trivia {{\n"
                    f"                result.push_child(None, cst::{child_enum}::{trivia_span_variant}(ws.result));\n"
                    f"            }}\n"
                    f"        }}"
                )
            else:  # WS_REQUIRED
                return (
                    f"        if let Some(ws) = self.consume_regex(pos, {ws_idx}) {{\n"
                    f"            pos = ws.pos;\n"
                    f"            if self.capture_trivia {{\n"
                    f"                result.push_child(None, cst::{child_enum}::{trivia_span_variant}(ws.result));\n"
                    f"            }}\n"
                    f"        }} else {{\n"
                    f"            return None;\n"
                    f"        }}"
                )
        else:
            # Non-trivia rules: call apply__parse__trivia
            trivia_class = self._class_name(gsm.TRIVIA_RULE_NAME)
            trivia_variant = trivia_class  # variant name in child enum
            if sep == gsm.Separator.WS_ALLOWED:
                return (
                    f"        if let Some(ws) = self.apply__parse__trivia(pos) {{\n"
                    f"            pos = ws.pos;\n"
                    f"            if self.capture_trivia {{\n"
                    f"                result.push_child(None, cst::{child_enum}::{trivia_variant}(ws.result));\n"
                    f"            }}\n"
                    f"        }}"
                )
            elif sep == gsm.Separator.WS_REQUIRED:
                return (
                    f"        if let Some(ws) = self.apply__parse__trivia(pos) {{\n"
                    f"            pos = ws.pos;\n"
                    f"            if self.capture_trivia {{\n"
                    f"                result.push_child(None, cst::{child_enum}::{trivia_variant}(ws.result));\n"
                    f"            }}\n"
                    f"        }} else {{\n"
                    f"            return None;\n"
                    f"        }}"
                )
            else:
                msg = f"Unhandled separator: {sep!r}"
                raise NotImplementedError(msg)

    # ------------------------------------------------------------------
    # Item generation
    # ------------------------------------------------------------------

    def _gen_item(self, path: tuple[str, ...], rule: gsm.Rule, item: gsm.Item, parent_class_name: str) -> RustParserFn:
        """Generate item parser function. Returns the RustParserFn."""
        if item.quantifier.is_multiple():
            return self._gen_item_multiple(path, rule, item, parent_class_name)
        else:
            return self._gen_item_single_or_optional(path, rule, item, parent_class_name)

    def _gen_item_single_or_optional(
        self, path: tuple[str, ...], rule: gsm.Rule, item: gsm.Item, parent_class_name: str
    ) -> RustParserFn:
        """Generate a single/optional item parser that delegates to the consume expression."""
        consume_expr, result_ty, inline_to_parent = self._gen_consume_term(path, item.term, rule, parent_class_name)

        fn_info = self._cache_parser_info(path, result_ty, inline_to_parent=inline_to_parent)

        # Emit the item parser function
        if result_ty.is_span:
            ret_type = "Span"
        elif result_ty.class_name == parent_class_name and inline_to_parent:
            ret_type = f"cst::{parent_class_name}"
        elif result_ty.class_name is not None:
            ret_type = f"Shared<cst::{result_ty.class_name}>"
        else:
            ret_type = "Span"

        lines = []
        lines.append(f"    fn {fn_info.name}(&mut self, pos: i64) -> Option<ApplyResult<{ret_type}>> {{")
        lines.append(f"        {consume_expr}")
        lines.append("    }")
        lines.append("")
        self._fn_bodies.append("\n".join(lines))

        return fn_info

    def _gen_item_multiple(
        self, path: tuple[str, ...], rule: gsm.Rule, item: gsm.Item, parent_class_name: str
    ) -> RustParserFn:
        """Generate a +/* item parser that loops and accumulates into parent node type."""
        # The item parser for multiple items returns the parent node type
        parent_result_ty = ResultTy(is_span=False, class_name=parent_class_name)
        fn_info = self._cache_parser_info(path, parent_result_ty, inline_to_parent=True)

        # Generate the consume expression for one item.
        # Pass path (not (*path, "one")) to match Python reference path tuple scheme
        # and preserve side-by-side auditability of generated function names (correctness-4).
        consume_expr, consumed_result_ty, one_is_inline = self._gen_consume_term(
            path, item.term, rule, parent_class_name
        )

        is_one_or_more = item.quantifier.is_required()

        lines = []
        lines.append(
            f"    fn {fn_info.name}(&mut self, mut pos: i64) -> Option<ApplyResult<cst::{parent_class_name}>> {{"
        )
        lines.append("        let span_start = pos;")
        # Use Span::unknown() for the placeholder; set_span below supplies the real span
        # (efficiency-2: avoids Arc clone on every loop entry).
        lines.append(f"        let mut result = cst::{parent_class_name}::new(Span::unknown());")
        # Per-iteration progress guard: a zero-width match (one_result.pos == pos before
        # the update) means the consume helper matched empty at this position.  Break
        # immediately so the loop terminates; the empty match is discarded without being
        # appended to the CST.  Placement before the pos assignment is load-bearing:
        # after the assignment the comparison would be vacuously true and break every
        # iteration.  Mirrors the identical Python guard in gsm2parser.py.
        lines.append("        while let Some(one_result) = {")
        lines.append(f"            {consume_expr}")
        lines.append("        } {")
        lines.append("            if one_result.pos <= pos { break; }")
        lines.append("            pos = one_result.pos;")
        # Generate append statement
        if one_is_inline:
            # Sub-expression that returns parent type: extend_children.
            # TODO(extend-children-owned): extend_children clones every child Arc even
            # though the donor (one_result.result) is immediately dropped.  A consuming
            # variant (e.g. extend_children_owned) using Vec::append would avoid the
            # atomic inc+dec pairs on the parse hot path.  Blocked on gsm2tree_rs adding
            # the method to the generated CST API.
            if item.disposition != gsm.Disposition.SUPPRESS:
                lines.append("            result.extend_children(&one_result.result);")
        else:
            append_code = self._gen_append_code_for_consumed(
                item, "one_result", consumed_result_ty, rule, parent_class_name
            )
            if append_code:
                lines.append(f"            {append_code}")
        lines.append("        }")
        if is_one_or_more:
            lines.append("        if pos == span_start {")
            lines.append("            return None;")
            lines.append("        }")
        lines.append("        result.set_span(Span::new_with_source(span_start, pos, self.terminals.source_text()));")
        lines.append("        Some(ApplyResult { pos, result })")
        lines.append("    }")
        lines.append("")
        self._fn_bodies.append("\n".join(lines))

        return fn_info

    # ------------------------------------------------------------------
    # Consume term expression generation
    # ------------------------------------------------------------------

    def _gen_consume_term(
        self,
        path: tuple[str, ...],
        term: gsm.Term,
        rule: gsm.Rule,
        parent_class_name: str,
    ) -> tuple[str, ResultTy, bool]:
        """Return (rust_expr, result_ty, inline_to_parent) for a term."""
        if isinstance(term, gsm.Identifier):
            rule_name = term.value
            class_name = self._class_name(rule_name)
            fn_info = self._parsers[(rule_name,)]
            result_ty = ResultTy(is_span=False, class_name=class_name)
            return f"self.{fn_info.apply_name}(pos)", result_ty, False

        elif isinstance(term, gsm.Literal):
            escaped = _rust_str_lit(term.value)
            self._uses_literal = True
            result_ty = ResultTy(is_span=True, class_name=None)
            return f'self.consume_literal(pos, "{escaped}")', result_ty, False

        elif isinstance(term, gsm.Regex):
            idx = self._regex_idx(term.value)
            self._uses_regex = True
            result_ty = ResultTy(is_span=True, class_name=None)
            return f"self.consume_regex(pos, {idx})", result_ty, False

        elif isinstance(term, list | tuple):
            # Sub-expression: parenthesized alternatives (gsm.Term is Sequence[Items];
            # fltk2gsm produces list, but tuple is also valid per the GSM type — correctness-5).
            return self._gen_subexpr_term(path, term, rule, parent_class_name)

        elif isinstance(term, gsm.Invocation):
            msg = f"Invocation terms are not supported in Rust parser generation: {term}"
            raise NotImplementedError(msg)

        else:
            msg = f"Unknown term type: {type(term)}"
            raise NotImplementedError(msg)

    def _gen_subexpr_term(
        self,
        path: tuple[str, ...],
        alternatives: Sequence[gsm.Items],
        rule: gsm.Rule,
        parent_class_name: str,
    ) -> tuple[str, ResultTy, bool]:
        """Generate a sub-expression (parenthesized alternatives) and return its call expression."""
        alts_path = (*path, "alts")
        parent_result_ty = ResultTy(is_span=False, class_name=parent_class_name)
        alts_fn = self._cache_parser_info(alts_path, parent_result_ty, inline_to_parent=True)

        # Generate the __alts function
        alts_lines = []
        alts_lines.append(
            f"    fn {alts_fn.name}(&mut self, pos: i64) -> Option<ApplyResult<cst::{parent_class_name}>> {{"
        )
        for alt_idx, alt in enumerate(alternatives):
            sub_alt_path = (*alts_path, f"alt{alt_idx}")
            sub_alt_fn = self._gen_alternative(sub_alt_path, rule, alt)
            alts_lines.append(f"        if let Some(r) = self.{sub_alt_fn.name}(pos) {{")
            alts_lines.append("            return Some(r);")
            alts_lines.append("        }")
        alts_lines.append("        None")
        alts_lines.append("    }")
        alts_lines.append("")
        self._fn_bodies.append("\n".join(alts_lines))

        return f"self.{alts_fn.name}(pos)", parent_result_ty, True

    # ------------------------------------------------------------------
    # Append code generation
    # ------------------------------------------------------------------

    def _gen_append_code(
        self,
        item: gsm.Item,
        item_var: str,
        item_fn: RustParserFn,
        rule: gsm.Rule,
        parent_class_name: str,
    ) -> str:
        """Generate the code to append an item result to the parent node."""
        result_ty = item_fn.result

        if item.disposition == gsm.Disposition.SUPPRESS:
            return ""

        if item.disposition == gsm.Disposition.INLINE:
            msg = "INLINE disposition is not supported in Rust parser generation"
            raise NotImplementedError(msg)

        if item_fn.inline_to_parent:
            # Sub-expression or multiple-items: extend children from item result
            return f"result.extend_children(&{item_var}.result);"

        return self._gen_append_code_for_consumed(item, item_var, result_ty, rule, parent_class_name)

    # ------------------------------------------------------------------
    # Python bindings block
    # ------------------------------------------------------------------

    def _gen_python_bindings(self) -> str:
        """Generate the python-gated bindings block for the parser."""
        # Boilerplate skeleton: all non-parametric structure in one template string.
        boilerplate = """\

#[cfg(feature = "python")]
mod python_bindings {
    use pyo3::exceptions::{PyRecursionError, PyValueError};
    use pyo3::prelude::*;
    use super::cst;
    use super::Parser;

    #[pyclass(frozen, name = "ApplyResult")]
    pub struct PyApplyResult {
        pos: i64,
        result: Py<PyAny>,
    }

    #[pymethods]
    impl PyApplyResult {
        #[getter]
        fn pos(&self) -> i64 { self.pos }
        #[getter]
        fn result(&self, py: Python<'_>) -> Py<PyAny> { self.result.clone_ref(py) }
    }

    /// Recursive-descent parser with a configurable rule-application depth limit.
    ///
    /// Rule-application depth is bounded by `max_depth` (default
    /// `fltk_parser_core::DEFAULT_MAX_DEPTH`). Exceeding the limit raises `RecursionError`
    /// instead of overflowing the native stack. A `Parser` instance that has raised
    /// `RecursionError` is spent; construct a fresh one.
    #[pyclass(name = "Parser")]
    pub struct PyParser {
        inner: Parser,
    }

    impl PyParser {
        fn check_pos(&self, pos: i64) -> PyResult<()> {
            let len = self.inner.terminals().len();
            if pos < 0 || pos > len {
                return Err(PyValueError::new_err(format!(
                    "pos {pos} out of range for input of length {len}"
                )));
            }
            Ok(())
        }
    }

    #[pymethods]
    impl PyParser {
        #[new]
        #[pyo3(signature = (text, capture_trivia = false, max_depth = None))]
        fn new(text: &str, capture_trivia: bool, max_depth: Option<u32>) -> Self {
            let mut inner = Parser::new(text, capture_trivia);
            if let Some(d) = max_depth {
                inner.set_max_depth(d);
            }
            PyParser { inner }
        }

        #[getter]
        fn capture_trivia(&self) -> bool { self.inner.capture_trivia() }

        #[getter]
        fn rule_names(&self) -> Vec<&'static str> { self.inner.rule_names().to_vec() }

        #[getter]
        fn max_depth(&self) -> u32 { self.inner.max_depth() }

        #[getter]
        fn depth_exceeded(&self) -> bool { self.inner.depth_exceeded() }

        fn error_message(&self) -> String { self.inner.error_message() }

        fn error_position(&self) -> Option<i64> { self.inner.error_position() }
"""

        # Per-rule apply methods (parametric: one method per grammar rule).
        per_rule_lines = []
        for rule in self._grammar.rules:
            fn_info = self._parsers[(rule.name,)]
            class_name = self._class_name(rule.name)
            apply_name = fn_info.apply_name
            per_rule_lines.append(
                f"        fn {apply_name}(&mut self, py: Python<'_>, pos: i64) -> PyResult<Option<PyApplyResult>> {{"
            )
            per_rule_lines.append("            self.check_pos(pos)?;")
            per_rule_lines.append(f"            let result = self.inner.{apply_name}(pos);")
            per_rule_lines.append("            if self.inner.depth_exceeded() {")
            per_rule_lines.append("                return Err(PyRecursionError::new_err(format!(")
            per_rule_lines.append(
                '                    "parse depth limit exceeded (max_depth = {})", self.inner.max_depth())));'
            )
            per_rule_lines.append("            }")
            per_rule_lines.append("            match result {")
            per_rule_lines.append("                Some(r) => {")
            per_rule_lines.append(
                f"                    let handle = cst::Py{class_name}::to_py_canonical(py, &r.result)?;"
            )
            per_rule_lines.append(
                "                    Ok(Some(PyApplyResult { pos: r.pos, result: handle.into_any() }))"
            )
            per_rule_lines.append("                }")
            per_rule_lines.append("                None => Ok(None),")
            per_rule_lines.append("            }")
            per_rule_lines.append("        }")
            per_rule_lines.append("")

        # Closing skeleton.
        closing = """\
    }

    pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
        module.add_class::<PyApplyResult>()?;
        module.add_class::<PyParser>()?;
        Ok(())
    }
}
#[cfg(feature = "python")]
pub use python_bindings::register_classes;"""

        return boilerplate + "\n".join(per_rule_lines) + closing

    # ------------------------------------------------------------------
    # Generated regex compile test
    # ------------------------------------------------------------------

    def _gen_regex_compile_test(self) -> str:
        """Emit the cfg(test) block that verifies all regex patterns compile.

        Emitted only when the regex table is non-empty (design §2.4).
        Runs under each downstream consumer's cargo test, naming any unsupported pattern.
        """
        lines = []
        lines.append("#[cfg(test)]")
        lines.append("mod generated_regex_tests {")
        lines.append("    #[test]")
        lines.append("    fn all_regex_patterns_compile() {")
        lines.append("        for pat in super::REGEX_PATTERNS.iter() {")
        lines.append("            if let Err(e) = fltk_parser_core::regex_automata::meta::Regex::new(pat) {")
        lines.append(
            '                panic!("grammar regex {pat:?} is not supported by regex_automata::meta::Regex: {e}");'
        )
        lines.append("            }")
        lines.append("        }")
        lines.append("    }")
        lines.append("}")
        return "\n".join(lines)

    def _gen_append_code_for_consumed(
        self,
        item: gsm.Item,
        item_var: str,
        result_ty: ResultTy,
        rule: gsm.Rule,
        _parent_class_name: str,
    ) -> str:
        """Generate append code given the consumed result type."""
        if item.disposition == gsm.Disposition.SUPPRESS:
            return ""

        if item.disposition == gsm.Disposition.INLINE:
            msg = "INLINE disposition is not supported in Rust parser generation"
            raise NotImplementedError(msg)

        child_enum = self._child_enum_name(rule.name)
        rule_name = rule.name

        if item.label is not None:
            label = item.label
            ref_type, single_node_cls, _total = self._label_type_info(rule_name, label)

            if ref_type == "&Span":
                return f"result.append_{label}({item_var}.result);"
            elif single_node_cls is not None:
                return f"result.append_{label}({item_var}.result);"
            # Union label: need to wrap in child enum variant
            elif result_ty.is_span:
                return f"result.append_{label}(cst::{child_enum}::Span({item_var}.result));"
            else:
                child_cls = result_ty.class_name
                return f"result.append_{label}(cst::{child_enum}::{child_cls}({item_var}.result));"
        # Unlabeled INCLUDE: push_child with None label
        elif result_ty.is_span:
            return f"result.push_child(None, cst::{child_enum}::Span({item_var}.result));"
        else:
            child_cls = result_ty.class_name
            return f"result.push_child(None, cst::{child_enum}::{child_cls}({item_var}.result));"
