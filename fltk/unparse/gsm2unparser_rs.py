"""Rust unparser code generator for fltk.fegen grammars.

Generates a standalone ``.rs`` file implementing the unparsing pipeline -- CST ->
``Doc`` combinator tree (built through the ``DocAccumulator``) over the Rust CST
produced by :class:`fltk.fegen.gsm2tree_rs.RustCstGenerator` -- plus an optional
``#[cfg(feature = "python")]`` PyO3 wrapper.  It mirrors the structure of
:class:`fltk.fegen.gsm2parser_rs.RustParserGenerator`: a single :meth:`generate`
returns the complete file as a string and is memoized to prevent double-emit.

The generated pure-Rust layer links against the pyo3-free runtime crate
``fltk-unparser-core`` (``crates/fltk-unparser-core``), which provides ``Doc``,
``DocAccumulator``, ``UnparseResult``, ``resolve_spacing_specs``, ``Renderer``, and
``RendererConfig``.  The generator imports the generation-time ``FormatterConfig``
(:mod:`fltk.unparse.fmt_config`) and bakes its spacing/anchor/disposition decisions
into the emitted method bodies, exactly as the Python ``UnparserGenerator`` does --
the only runtime inputs to the generated unparser are the CST node and the
render-time width/indent config.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Literal

from fltk.fegen import gsm, naming
from fltk.fegen.gsm2parser_rs import cst_module_import, rust_str_lit
from fltk.fegen.gsm2tree_rs import RustCstGenerator
from fltk.unparse.combinators import Concat, Doc, HardLine, Line, Nbsp, Nil, SoftLine, Text
from fltk.unparse.fmt_config import AnchorConfig, FormatterConfig, ItemSelector, Normal, Omit, OperationType, RenderAs


class RustUnparserGenerator:
    """Generates a complete ``.rs`` unparser file from a :class:`gsm.Grammar`.

    Takes a raw ``gsm.Grammar`` (not yet trivia-processed), constructs an internal
    :class:`RustCstGenerator` to reuse trivia classification and the static naming
    helpers, and produces a string containing a complete ``.rs`` file.
    """

    def __init__(
        self,
        grammar: gsm.Grammar,
        formatter_config: FormatterConfig | None = None,
        cst_mod_path: str = "super::cst",
        source_name: str | None = None,
    ):
        self._cst = RustCstGenerator(grammar)
        # Work from the grammar with trivia rules added and classified.
        self._grammar = self._cst.grammar
        # FormatterConfig is consumed at generation time (baked into method bodies).
        self._formatter_config = formatter_config or FormatterConfig()
        self._cst_mod_path = cst_mod_path
        # None means "omit the 'from <source_name>' clause" in the header.
        self._source_name: str | None = source_name

        # Memoized result of generate() — set on first call to prevent double-emit
        # (matching RustParserGenerator.generate).
        self._generated: str | None = None

        # Set by _doc_to_rust_expr whenever it emits a bare ``Doc::`` constructor; read by
        # _gen_header to gate the ``Doc`` import.  A grammar that emits no spacing/anchor Doc
        # never references the bare ``Doc`` type (Text/Concat use fully-qualified
        # ``fltk_unparser_core::`` paths), so importing it unconditionally would be an unused
        # import under ``-D warnings`` -- parity with the parser backend gating its Regex/OnceLock
        # import on ``self._regex_patterns`` (gsm2parser_rs.py).
        self._uses_doc_type = False

    def generate(self) -> str:
        """Generate the complete ``.rs`` unparser source.

        Idempotent: a second call on the same instance returns the previously
        generated string without re-running emission.
        """
        if self._generated is not None:
            return self._generated

        # Generate the body sections first: _gen_rule_methods runs _doc_to_rust_expr, which sets
        # self._uses_doc_type as a side effect.  The header's conditional ``Doc`` import then
        # reflects whether any bare ``Doc::`` constructor was actually emitted.
        struct = self._gen_struct()  # Unparser struct + constructor.
        rule_methods = self._gen_rule_methods()  # per-rule unparse methods (entry + alt dispatch).
        python_bindings = self._gen_python_bindings()  # optional PyO3 wrapper (gated behind `python`).
        header = self._gen_header()  # inner attributes + imports (depends on _uses_doc_type above).

        # Assemble in file order: header, struct, per-rule methods, optional PyO3 wrapper.
        parts: list[str] = [header, struct, rule_methods, python_bindings]
        self._generated = "\n".join(p for p in parts if p) + "\n"
        return self._generated

    # ------------------------------------------------------------------
    # .pyi type stub for the Python surface
    # ------------------------------------------------------------------

    def generate_pyi(self, protocol_module: str) -> str:
        """Return a complete ``.pyi`` type stub for the generated unparser's Python surface.

        The PyO3 wrapper (:meth:`_gen_python_bindings`) exposes two Python classes:
        ``Unparser`` -- a no-arg constructor plus, per grammar rule, a full-pipeline
        ``unparse_{rule}(node, max_width, indent_width) -> str | None`` method
        and an additive ``unparse_{rule}_doc(node) -> Doc | None`` method -- and
        ``Doc`` -- the resolved-document handle with ``render`` / ``__repr__``.  This stub
        describes that surface so downstream code gets a type-checked ``Unparser``,
        pure-Python and independent of whether the extension is
        compiled.

        ``protocol_module`` is the import path of the committed CST protocol module for this
        grammar (e.g. ``'mylang.cst_protocol'``), aliased ``_proto``.  Each ``unparse_*``
        method's ``node`` parameter is annotated ``_proto.{ClassName}`` -- the same
        config-agnostic protocol type the CST ``.pyi`` uses for its child/accessor surface
        (:meth:`fltk.fegen.gsm2tree_rs.RustCstGenerator.generate_pyi`) -- so a downstream caller
        can pass a Rust-CST node (which structurally conforms to the protocol) without a cast.
        Unlike the CST, the unparser has no module-level conformance protocol of its own (there
        is no ``UnparserModule`` analog of ``CstModule``); the protocol module is referenced only
        to type the ``node`` parameters against the same identities the CST surface uses.

        Callers write this string next to the generated ``.rs`` (``--pyi-output`` overrides the
        path), exactly as the CST backend does.
        """
        lines: list[str] = []
        lines.append("from __future__ import annotations")
        # Emit return types as the PEP 604 `X | None` union, never `typing.Optional[...]`: ruff
        # rewrites `Optional` -> `| None` in fixable code but does NOT auto-fix the now-unused
        # `import typing` (F401) in a stub file, so a committed stub written with `Optional` gains a
        # permanent `make check` failure.  Emitting the union directly (and importing no `typing`)
        # keeps the raw generator output gate-clean for every downstream consumer -- and matches the
        # committed CST `.pyi`, which also carries `| None` as its canonical post-`ruff --fix` form.
        lines.append(f"import {protocol_module} as _proto")
        lines.append("")
        # `Doc`: the resolved-document handle. It is the unparser extension's own
        # class -- there is no protocol for it -- so the `unparse_*_doc` return annotations below
        # reference it by its stub-local name (resolved lazily via the future-annotations import).
        lines.append("class Doc:")
        lines.append("    def render(self, max_width: int = ..., indent_width: int = ...) -> str: ...")
        lines.append("    def __repr__(self) -> str: ...")
        lines.append("")
        # `Unparser`: no-arg constructor + per-rule string and Doc methods. Iterate the
        # trivia-processed grammar, so the synthetic `_trivia` rule yields `unparse__trivia` /
        # `unparse__trivia_doc` over `_proto.Trivia`, matching the emitted PyO3 surface.
        lines.append("class Unparser:")
        lines.append("    def __init__(self) -> None: ...")
        for rule in self._grammar.rules:
            class_name = self._class_name(rule.name)
            lines.append(
                f"    def unparse_{rule.name}(self, node: _proto.{class_name}, "
                f"max_width: int = ..., indent_width: int = ...) -> str | None: ..."
            )
            lines.append(f"    def unparse_{rule.name}_doc(self, node: _proto.{class_name}) -> Doc | None: ...")
        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _gen_header(self) -> str:
        lines: list[str] = []
        if self._source_name is not None:
            escaped = rust_str_lit(self._source_name)
            lines.append(f"//! Generated by fltk gen-rust-unparser from `{escaped}`. Do not edit.")
        else:
            lines.append("//! Generated by fltk gen-rust-unparser. Do not edit.")
        # Allow double-underscore names used in generated unparse function paths
        # (e.g. unparse_{rule}__alt{N}__item{M}).
        lines.append("#![allow(non_snake_case)]")
        lines.append("")

        # The core walk uses DocAccumulator / UnparseResult unconditionally.  ``Doc`` (the bare
        # type) is referenced only by a ``Doc::`` constructor emitted from _doc_to_rust_expr, so
        # gate its import on self._uses_doc_type -- a grammar with no spacing/anchor Doc emits
        # none, and an unconditional import would be unused under ``-D warnings`` (parity with the
        # parser backend gating its Regex/OnceLock import).  The pipeline types
        # (Renderer / RendererConfig / resolve_spacing_specs) are consumed only by the
        # python_bindings module (via `super::`), so gate their import behind the `python` feature
        # -- otherwise a python-off build sees them as unused imports (the names stay
        # available to the wrapper).
        lines.append("use fltk_unparser_core::{DocAccumulator, UnparseResult};")
        if self._uses_doc_type:
            lines.append("use fltk_unparser_core::Doc;")
        lines.append('#[cfg(feature = "python")]')
        lines.append("use fltk_unparser_core::{Renderer, RendererConfig, resolve_spacing_specs};")
        lines.append("")

        # CST module import (shared helper with gsm2parser_rs._gen_header).
        lines.append(cst_module_import(self._cst_mod_path))
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Unparser struct + constructor
    # ------------------------------------------------------------------

    def _gen_struct(self) -> str:
        """Emit the pure-Rust ``Unparser`` unit struct and its ``new`` constructor.

        The struct is a unit struct: the ``FormatterConfig`` is baked into the
        per-rule methods at generation time, and ``terminals`` is unnecessary
        because Rust spans carry their own source.  Render config is
        supplied at render time, not construction.
        """
        lines: list[str] = []
        lines.append("/// Generated unparser.")
        lines.append("///")
        lines.append("/// The `FormatterConfig` is baked into the per-rule methods at generation time;")
        lines.append("/// render width/indent is supplied at render time, not construction.")
        lines.append("#[derive(Default)]")
        lines.append("pub struct Unparser;")
        lines.append("")
        lines.append("impl Unparser {")
        lines.append("    pub fn new() -> Self {")
        lines.append("        Unparser")
        lines.append("    }")
        lines.append("}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Naming helpers
    # ------------------------------------------------------------------

    def _class_name(self, rule_name: str) -> str:
        """Return the CamelCase CST struct name for a rule (shared with the parser/CST backends)."""
        return self._cst.class_name_for_rule(rule_name)

    # Matches a complete Rust string literal (honoring ``\"`` escapes) so its *content* can be
    # blanked before scanning a body line for a ``node`` identifier use (see _node_param).
    _RUST_STR_LITERAL_RE = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"')

    @classmethod
    def _node_param(cls, body_lines: Sequence[str]) -> str:
        """Return ``"node"`` if any body line references the ``node`` param, else ``"_node"``.

        Some emitted method bodies never read the CST node: a ``SUPPRESS`` item (reconstructed
        from the grammar, :meth:`_gen_suppressed_item_body`), an ``INLINE`` literal (fixed text,
        no child extraction), and the degenerate empty-alternative body all use only
        ``pos``/``acc``.  Naming the unused parameter ``_node`` keeps the generated unparser
        warning-clean under ``-D warnings`` (clippy ``unused_variables``) without a blanket
        ``#[allow]``.  The ``\\bnode\\b`` word-boundary match deliberately does not count
        ``trivia_node`` (a distinct binding) as a use.

        String-literal *content* is blanked before the scan: a re-emitted literal whose text is
        (or contains) the word ``node`` -- e.g. a required-suppressed or ``INLINE`` ``"node"``
        literal emitting ``text("node")`` -- would otherwise false-match ``\\bnode\\b`` and name
        an unused ``node`` parameter, tripping clippy ``unused_variables`` under ``-D warnings``.
        A genuine ``node`` use (``node.children()`` ...) is never inside a string literal, so
        blanking literal content is lossless.
        """
        return (
            "node"
            if any(re.search(r"\bnode\b", cls._RUST_STR_LITERAL_RE.sub('""', line)) for line in body_lines)
            else "_node"
        )

    # ------------------------------------------------------------------
    # Per-rule unparse methods: rule entry + alternative dispatch
    # ------------------------------------------------------------------

    def _gen_rule_methods(self) -> str:
        """Emit the ``impl Unparser`` block holding one method per rule plus its alternatives.

        Mirrors the Python ``UnparserGenerator``'s per-rule emission: a public
        ``unparse_{rule}`` entry method that threads an initial ``DocAccumulator`` through
        any rule-level anchor operations and dispatches the rule's alternatives, plus one
        private ``unparse_{rule}__alt{N}`` method per alternative.  Iterates
        ``self._grammar`` (trivia-processed), so the synthetic ``_trivia`` rule yields
        ``unparse__trivia`` just as the Python backend does.  Each ``__alt{N}`` body walks
        the alternative's items, threading the accumulator/position through one
        ``__alt{N}__item{M}`` method per item.  Each ``__item{M}`` routes on
        disposition/quantifier: ``SUPPRESS`` items, single ``INCLUDE``/``INLINE`` literal
        terms (with their ``Span`` child extraction/validation), single identifier
        (rule-reference) terms, single regex terms, single sub-expression
        (nested-alternatives) terms, and multiple-quantifier (``+``/``*``) loops emit their
        full body.  Separator/trivia processing (:meth:`_gen_trivia_processing`) emits both
        branches: a trivia rule consuming its own whitespace ``Span`` children, and a non-trivia
        rule looking up a ``Trivia`` child, calling ``unparse__trivia``, and wrapping preserved
        output in a ``SeparatorSpec``.  The two trivia utility methods the non-trivia branch
        relies on (``_has_preservable_trivia`` / ``_count_newlines_in_trivia``) are emitted once
        at the head of the impl block (:meth:`_gen_trivia_helper_methods`).
        """
        parts: list[str] = ["impl Unparser {"]
        parts.extend(self._gen_trivia_helper_methods())
        for rule in self._grammar.rules:
            parts.append(self._gen_rule(rule))
        parts.append("}")
        return "\n".join(parts)

    def _gen_rule(self, rule: gsm.Rule) -> str:
        """Emit the entry method, per-alternative bodies, and per-item methods for one rule."""
        class_name = self._class_name(rule.name)
        # Method-name prefix for this rule: the entry method is `unparse_{rule}`, its
        # alternatives are `unparse_{rule}__alt{N}`, and its items
        # `unparse_{rule}__alt{N}__item{M}`. Nested sub-expressions extend this prefix
        # (see _gen_subexpr_methods), so all per-alternative/-item naming is prefix-driven.
        prefix = f"unparse_{rule.name}"
        blocks = [self._gen_rule_entry(rule, class_name)]
        for alt_idx, alt in enumerate(rule.alternatives):
            blocks.extend(self._gen_alternative(prefix, rule.name, class_name, alt_idx, alt))
        return "\n\n".join(blocks)

    def _gen_rule_entry(self, rule: gsm.Rule, class_name: str) -> str:
        """Emit ``pub fn unparse_{rule}`` — initial accumulator, rule anchors, alt dispatch.

        Builds a fresh ``DocAccumulator``, applies RULE_START anchor operations
        (group/nest/join begin), tries each alternative from ``pos = 0``, and on the first
        success applies RULE_END anchor operations (the matching pops) before returning.
        Returns ``None`` if every alternative fails.
        """
        rule_name = rule.name
        lines: list[str] = []
        lines.append(f"    pub fn unparse_{rule_name}(&self, node: &cst::{class_name}) -> Option<UnparseResult> {{")
        lines.append("        let acc = DocAccumulator::new();")

        # RULE_START anchors: rebind `acc` through the push operations, in config order.
        start_anchor = self._formatter_config.get_anchor_config(rule_name, "before", ItemSelector.RULE_START, "")
        if start_anchor:
            for op in start_anchor.operations:
                if op.operation_type == OperationType.GROUP_BEGIN:
                    lines.append("        let acc = acc.push_group();")
                elif op.operation_type == OperationType.NEST_BEGIN:
                    lines.append(f"        let acc = acc.push_nest({op.indent or 1});")
                elif op.operation_type == OperationType.JOIN_BEGIN:
                    if op.separator is None:
                        msg = "JOIN_BEGIN operation missing required separator"
                        raise RuntimeError(msg)
                    try:
                        separator_expr = self._doc_to_rust_expr(op.separator)
                    except ValueError as exc:
                        msg = f"Rule {rule_name!r} JOIN_BEGIN separator uses unsupported Doc type: {exc}"
                        raise ValueError(msg) from exc
                    lines.append(f"        let acc = acc.push_join({separator_expr});")
                else:
                    # Exhaustive over the OperationTypes a RULE_START anchor carries (the three
                    # begin ops). A SPACING/END/future member reaching here would silently drop a
                    # push and emit an unbalanced accumulator stack, so fail loudly at generation
                    # time -- mirroring the item-level anchor guard in `_item_anchor_lines`.
                    msg = (
                        f"Unsupported OperationType in RULE_START anchor for rule {rule_name!r}: {op.operation_type!r}"
                    )
                    raise ValueError(msg)

        # RULE_END anchors: a chain of pops applied to the successful result accumulator.
        pop_chain = ""
        end_anchor = self._formatter_config.get_anchor_config(rule_name, "after", ItemSelector.RULE_END, "")
        if end_anchor:
            for op in end_anchor.operations:
                if op.operation_type == OperationType.NEST_END:
                    pop_chain += ".pop_nest()"
                elif op.operation_type == OperationType.GROUP_END:
                    pop_chain += ".pop_group()"
                elif op.operation_type == OperationType.JOIN_END:
                    pop_chain += ".pop_join()"
                else:
                    # Exhaustive over the OperationTypes a RULE_END anchor carries (the three end
                    # ops); anything else would silently drop a pop and unbalance the accumulator
                    # stack, so fail loudly -- mirroring the item-level anchor guard.
                    msg = f"Unsupported OperationType in RULE_END anchor for rule {rule_name!r}: {op.operation_type!r}"
                    raise ValueError(msg)

        # Dispatch alternatives: clone `acc` for every attempt but the last, which moves it.
        lines.extend(self._gen_alt_dispatch_loop(f"unparse_{rule_name}", len(rule.alternatives), "0", pop_chain))
        lines.append("    }")
        return "\n".join(lines)

    def _gen_alt_dispatch_loop(self, prefix: str, n_alts: int, start_pos: str, pop_chain: str = "") -> list[str]:
        """Emit the shared "try each ``{prefix}__alt{N}``, return the first success" dispatch loop.

        Shared by :meth:`_gen_rule_entry` (rule entry, ``start_pos="0"``, optional RULE_END
        ``pop_chain``) and :meth:`_gen_alts_dispatch` (a sub-expression's nested ``__alts``
        dispatch, ``start_pos="pos"``, no anchors).  ``acc`` is cloned for every attempt but the
        last, which moves it; the loop ends with the ``None`` all-alternatives-failed
        fall-through.  When ``pop_chain`` is non-empty the success path rebuilds the result
        accumulator through the RULE_END pops before returning; otherwise it returns the
        alternative's result unchanged.
        """
        lines: list[str] = []
        for alt_idx in range(n_alts):
            acc_arg = "acc" if alt_idx == n_alts - 1 else "acc.clone()"
            lines.append(f"        if let Some(r) = self.{prefix}__alt{alt_idx}(node, {start_pos}, {acc_arg}) {{")
            if pop_chain:
                lines.append(f"            let acc = r.accumulator{pop_chain};")
                lines.append("            return Some(UnparseResult::new(acc, r.new_pos));")
            else:
                lines.append("            return Some(r);")
            lines.append("        }")
        lines.append("        None")
        return lines

    def _gen_alternative(self, prefix: str, rule_name: str, class_name: str, alt_idx: int, alt: gsm.Items) -> list[str]:
        """Emit the ``{prefix}__alt{N}`` body method plus one ``{prefix}__alt{N}__item{M}`` per item.

        ``prefix`` is the method-name prefix of the enclosing dispatch (``unparse_{rule}`` for
        a rule, ``{item_prefix}__alts`` for a nested sub-expression).  ``rule_name`` /
        ``class_name`` always name the enclosing *rule*: a sub-expression's children are
        inlined into the parent rule's CST node, so nested methods walk the same
        ``cst::{class_name}`` node and query the same label/child enums (mirroring the
        parser-backend ``_gen_subexpr_term``).

        Returns a flat list of method-source blocks: the alternative body, each item method,
        and (for a sub-expression item) the nested ``__alts`` method tree appended by
        :meth:`_gen_item_method`.
        """
        blocks = [self._gen_alternative_body(prefix, rule_name, class_name, alt_idx, alt)]
        for item_idx, item in enumerate(alt.items):
            blocks.extend(self._gen_item_method(prefix, rule_name, class_name, alt_idx, item_idx, item))
        return blocks

    def _gen_alternative_body(self, prefix: str, rule_name: str, class_name: str, alt_idx: int, alt: gsm.Items) -> str:
        """Emit ``unparse_{rule}__alt{N}`` — the per-item accumulator/position walk.

        A required item (non-optional quantifier) fails the whole alternative via ``?``
        when its method returns ``None``; an optional item keeps the prior
        accumulator/position when absent.  On success an item's result accumulator is
        merged in (the default ``Normal`` disposition).

        Each item is wrapped with its configured before/after-item spacing
        (:meth:`_item_spacing_lines`), mirroring the Python
        ``gen_alternative_unparser`` (``gsm2unparser.py:1602`` ff.): the ``BeforeSpec`` is
        added unconditionally before the item method call (so it persists in ``acc`` even
        when an optional item is absent, matching the Python ``accumulator_var`` threading),
        and the ``AfterSpec`` is added only on the success path — for an optional item that
        means *inside* the ``if let Some`` block.  Each item is also bracketed by its
        configured item-level anchor push/pop operations
        (:meth:`_item_anchor_lines`): before-anchors are emitted *ahead* of the
        before-spacing (matching the Python ``_gen_anchor_operations_before_item`` →
        ``_gen_before_item_spacing`` order, ``gsm2unparser.py:1602``/``:1605``), and
        after-anchors *after* the item block — both unconditional at the 8-space indent
        (the Python after-anchor runs at ``method.block`` scope, ``:1656``, not inside the
        optional ``if_not_none`` block).  ``rule_name`` always names the enclosing rule (a
        sub-expression's items query the parent rule's config, as in the Python backend).

        Each item's formatter disposition
        (:meth:`fltk.unparse.fmt_config.FormatterConfig.get_item_disposition`) is honored, porting
        the Python ``gen_alternative_unparser`` disposition branch (``gsm2unparser.py:1600`` ff.):
        a ``Normal`` item merges its own accumulator and gets before/after-item spacing; an
        ``Omit`` item is still called (to advance ``pos`` and validate the CST) but its produced
        ``Doc`` is discarded; a ``RenderAs`` item's output is likewise discarded and replaced by
        the configured spacing ``Doc``.  Before-spacing is emitted only for ``Normal`` items (the
        Python ``not isinstance(item_disposition, Omit | RenderAs)`` gate, ``:1604``).  Because the
        accumulator is threaded by value, a ``Normal`` required item moves ``acc`` into the call
        and reassigns it from the result, whereas an ``Omit``/``RenderAs`` required item needs the
        prior ``acc`` afterward and so clones it into the call (the optional path always clones).

        The alternative's initial separator (before the first item) and each item's trailing
        separator are processed by :meth:`_gen_trivia_processing` (porting the Python
        ``gen_alternative_unparser`` separator calls, ``gsm2unparser.py:1588``/``:1658``).  Both
        branches are emitted: a trivia rule consuming its own unlabeled whitespace ``Span``
        children, and a regular rule's ``Trivia``-child lookup + ``SeparatorSpec`` preservation.
        """
        lines: list[str] = []
        # A non-empty alternative always reads `node` (its item calls / trivia processing); the
        # degenerate empty-alternative body uses only acc/pos, so name the param `_node` there.
        node_param = "node" if alt.items else "_node"
        lines.append(
            f"    fn {prefix}__alt{alt_idx}"
            f"(&self, {node_param}: &cst::{class_name}, pos: usize, acc: DocAccumulator) -> Option<UnparseResult> {{"
        )
        if not alt.items:
            # Degenerate empty alternative: pass the accumulator/position through unchanged.
            lines.append("        Some(UnparseResult::new(acc, pos))")
            lines.append("    }")
            return "\n".join(lines)

        # Thread `pos`/`acc` through the items (cheap-clone the accumulator for optional
        # attempts so a missing optional item leaves the prior accumulator intact).
        lines.append("        let mut pos = pos;")
        lines.append("        let mut acc = acc;")
        # Initial separator before the first item (Python gen_alternative_unparser :1588).
        lines.extend(self._gen_trivia_processing(rule_name, class_name, alt.initial_sep, "        "))
        for item_idx, item in enumerate(alt.items):
            item_fn = f"{prefix}__alt{alt_idx}__item{item_idx}"
            # Per-item formatter disposition (Normal / Omit / RenderAs). Normal is the common
            # case; Omit/RenderAs still call the item method (to advance pos and validate the
            # CST) but discard its produced Doc.
            item_disposition = self._formatter_config.get_item_disposition(rule_name, item)
            is_normal = isinstance(item_disposition, Normal)
            # Item-level before-anchor push/pop, then before-spacing. Anchors are unconditional
            # (8-space indent), ahead of the call; before-spacing is emitted only for Normal
            # items (the Python `not isinstance(item_disposition, Omit | RenderAs)` gate,
            # `gsm2unparser.py:1604`). Anchors precede spacing, matching the Python order.
            lines.extend(self._item_anchor_lines(rule_name, item, "before", "        "))
            if is_normal:
                lines.extend(self._item_spacing_lines(rule_name, item, "before", "        "))
            if item.quantifier.is_optional():
                # Optional: always clone acc for the call so an absent optional leaves the prior
                # accumulator intact; the disposition-dependent merge runs only on the matched path.
                lines.append(f"        if let Some(r) = self.{item_fn}(node, pos, acc.clone()) {{")
                lines.append("            pos = r.new_pos;")
                lines.extend(self._item_disposition_success_lines(rule_name, item, item_disposition, "            "))
                lines.append("        }")
            else:
                # Required: a Normal item moves acc into the call and reassigns it from the
                # result; an Omit/RenderAs item needs the prior acc afterward (to leave it
                # unchanged or rebuild it with the render-as spacing), so it clones acc instead.
                acc_arg = "acc" if is_normal else "acc.clone()"
                lines.append(f"        let r = self.{item_fn}(node, pos, {acc_arg})?;")
                lines.append("        pos = r.new_pos;")
                lines.extend(self._item_disposition_success_lines(rule_name, item, item_disposition, "        "))
            # Item-level after-anchor push/pop — unconditional (8-space indent), *after* the
            # item block (outside the optional `if let`), matching the Python after-anchor's
            # method.block scope (always applied, even when an optional item is absent).
            lines.extend(self._item_anchor_lines(rule_name, item, "after", "        "))
            # Separator after this item (Python gen_alternative_unparser :1658). The guard
            # mirrors `item_idx < len(items.sep_after)` (item_idx < len(items.items) always holds).
            if item_idx < len(alt.sep_after):
                lines.extend(self._gen_trivia_processing(rule_name, class_name, alt.sep_after[item_idx], "        "))
        lines.append("        Some(UnparseResult::new(acc, pos))")
        lines.append("    }")
        return "\n".join(lines)

    def _item_disposition_success_lines(
        self,
        rule_name: str,
        item: gsm.Item,
        item_disposition: Normal | Omit | RenderAs,
        indent: str,
    ) -> list[str]:
        """Return the success-path accumulator lines for an item, honoring its formatter disposition.

        Ports the disposition branch of the Python ``gen_alternative_unparser``
        (``gsm2unparser.py:1628``/``:1644``).  ``pos`` is advanced by the caller for every
        disposition; this method decides only what becomes of the *accumulator* on the success
        path:

        - ``Normal``: merge the item's own accumulator (``acc = r.accumulator;``) and add any
          configured after-item spacing.
        - ``RenderAs``: discard the item's output and add the configured replacement spacing
          ``Doc`` via ``add_non_trivia`` (the prior ``acc`` is kept — the caller cloned it into the
          item call so it survives the call).
        - ``Omit``: emit nothing — the item's output is dropped entirely (the caller's cloned-in
          ``acc`` is left unchanged).

        The ``RenderAs`` spacing routes through :meth:`_doc_to_rust_expr` (inheriting its
        Group/Nest/Join/Comment rejection); a rejected Doc re-raises with rule/item context,
        mirroring :meth:`_item_spacing_lines` and the JOIN_BEGIN separator paths.
        """
        if isinstance(item_disposition, RenderAs):
            try:
                doc_expr = self._doc_to_rust_expr(item_disposition.spacing)
            except ValueError as exc:
                item_id = f"label={item.label!r}" if item.label else f"term={type(item.term).__name__}"
                msg = f"Rule {rule_name!r} render-as for {item_id} uses unsupported Doc type: {exc}"
                raise ValueError(msg) from exc
            return [f"{indent}acc = acc.add_non_trivia({doc_expr});"]
        if isinstance(item_disposition, Omit):
            return []
        if not isinstance(item_disposition, Normal):
            # Unreachable with the current Normal | Omit | RenderAs union, but use an explicit
            # raise (not assert, which `python -O` strips) so an unknown disposition type fails
            # loudly at generation time instead of silently emitting Normal-disposition Rust --
            # matching the explicit-raise routing guards in the `_gen_*_term_body` methods.
            item_id = f"label={item.label!r}" if item.label else f"term={type(item.term).__name__}"
            msg = (
                f"Internal error: unrecognized disposition type {type(item_disposition).__name__!r} "
                f"for rule {rule_name!r} item {item_id}"
            )
            raise RuntimeError(msg)
        return [f"{indent}acc = r.accumulator;", *self._item_spacing_lines(rule_name, item, "after", indent)]

    def _item_spacing_lines(
        self, rule_name: str, item: gsm.Item, position: Literal["before", "after"], indent: str
    ) -> list[str]:
        """Return the ``acc = acc.add_non_trivia(<spec>);`` line for an item's before/after spacing.

        Ports the Python ``_gen_before_item_spacing`` / ``_gen_after_item_spacing``
        (``gsm2unparser.py:825``/``:804``): query the generation-time ``FormatterConfig`` for
        the item's spacing at ``position`` (``"before"`` or ``"after"``), wrap the resulting
        spacing ``Doc`` in a ``BeforeSpec`` / ``AfterSpec`` control node via the
        ``fltk_unparser_core`` ``before_spec`` / ``after_spec`` constructors, and add it as
        non-trivia.  Returns ``[]`` when no spacing is configured (the common default-config
        case), so unconfigured items emit nothing.

        The spacing ``Doc`` is always a primitive (``_spacing_cst_to_doc`` only yields
        Nil/Nbsp/Line/SoftLine/HardLine), but it is routed through :meth:`_doc_to_rust_expr`
        anyway — matching the Python backend, whose ``_create_before_spec``/``_create_after_spec``
        run the spacing through ``_doc_to_combinator_expr`` and so reject a Group/Nest/Join
        spacing identically.
        """
        # `position` is `Literal["before", "after"]`, so this if/elif is exhaustive at the type
        # level (Pyright enforces it at every call site). The `Literal` is erased at runtime,
        # though, so a subclass or untyped caller passing any other value would otherwise reach
        # the `spacing`/`ctor` reads below with both names unbound -- surfacing as an
        # `UnboundLocalError` that names neither the rule nor the bad position. The explicit
        # `else` raise makes the contract violation diagnosable, mirroring the explicit-raise
        # routing guards elsewhere in this file (e.g. `_item_disposition_success_lines`).
        if position == "before":
            spacing = self._formatter_config.get_before_spacing(rule_name, item)
            ctor = "before_spec"
        elif position == "after":
            spacing = self._formatter_config.get_after_spacing(rule_name, item)
            ctor = "after_spec"
        else:
            item_id = f"label={item.label!r}" if item.label else f"term={type(item.term).__name__}"
            msg = f"Internal error: unexpected position {position!r} for rule {rule_name!r} item {item_id}"
            raise ValueError(msg)
        if spacing is None:
            return []
        # `_doc_to_rust_expr` rejects Group/Nest/Join/Comment spacing (parity with the Python
        # backend's `_doc_to_combinator_expr`); re-raise with rule/item/position context so the
        # offending config entry is identifiable, mirroring `_gen_rule_entry`'s JOIN_BEGIN wrap.
        try:
            doc_expr = self._doc_to_rust_expr(spacing)
        except ValueError as exc:
            item_id = f"label={item.label!r}" if item.label else f"term={type(item.term).__name__}"
            msg = f"Rule {rule_name!r} {position}-spacing for {item_id} uses unsupported Doc type: {exc}"
            raise ValueError(msg) from exc
        spec_expr = f"fltk_unparser_core::{ctor}({doc_expr})"
        return [f"{indent}acc = acc.add_non_trivia({spec_expr});"]

    def _item_anchor_config(
        self, rule_name: str, item: gsm.Item, position: Literal["before", "after"]
    ) -> AnchorConfig | None:
        """Return the item-level ``AnchorConfig`` for an item at ``position``, or ``None``.

        Thin delegation to
        :meth:`fltk.unparse.fmt_config.FormatterConfig.get_item_anchor_config`, which owns the
        shared LABEL/LITERAL lookup and its load-bearing before/after selector asymmetry -- the
        canonical, tested definition both backends resolve against.  Mirrors the anchor-config
        lookup in the Python ``_gen_anchor_operations_before_item`` (``gsm2unparser.py:1481``)
        and ``_gen_anchor_operations_after_item`` (``:1525``).
        """
        return self._formatter_config.get_item_anchor_config(rule_name, item, position)

    def _item_anchor_lines(
        self, rule_name: str, item: gsm.Item, position: Literal["before", "after"], indent: str
    ) -> list[str]:
        """Return the ``acc = acc.push_*()`` / ``acc = acc.pop_*()`` lines for an item's anchors.

        Ports the Python ``_gen_anchor_operations_before_item`` /
        ``_gen_anchor_operations_after_item`` (``gsm2unparser.py:1472``/``:1517``): for a
        label-/literal-selected anchor (resolved by :meth:`_item_anchor_config`), emit the
        accumulator push/pop *state transitions* at item granularity —
        ``GROUP_BEGIN``/``NEST_BEGIN``/``JOIN_BEGIN`` → ``push_group`` /
        ``push_nest(indent)`` / ``push_join(<sep>)`` and ``GROUP_END``/``NEST_END``/``JOIN_END``
        → ``pop_group`` / ``pop_nest`` / ``pop_join`` — by reassigning the ``let mut acc`` the
        alternative body threads.  ``SPACING`` ops are skipped here (already handled by
        :meth:`_item_spacing_lines`).  The ``push_join`` separator goes through
        :meth:`_doc_to_rust_expr` and so inherits its Group/Nest/Join rejection.
        Returns ``[]`` when no anchor is configured (the common default-config case).

        Unlike the rule-level ``RULE_START``/``RULE_END`` anchors in :meth:`_gen_rule_entry`
        (which shadow-rebind ``acc`` at entry and append a ``.pop_*()`` chain to the result
        accumulator), these mutate the alternative body's ``let mut acc`` in place, with both
        before- and after-anchors handling the full operation set — exactly as the Python
        item-level helpers do.
        """
        anchor_config = self._item_anchor_config(rule_name, item, position)
        if anchor_config is None:
            return []
        lines: list[str] = []
        for op in anchor_config.operations:
            if op.operation_type == OperationType.SPACING:
                # Already handled by _item_spacing_lines.
                continue
            if op.operation_type == OperationType.GROUP_BEGIN:
                lines.append(f"{indent}acc = acc.push_group();")
            elif op.operation_type == OperationType.NEST_BEGIN:
                lines.append(f"{indent}acc = acc.push_nest({op.indent or 1});")
            elif op.operation_type == OperationType.GROUP_END:
                lines.append(f"{indent}acc = acc.pop_group();")
            elif op.operation_type == OperationType.NEST_END:
                lines.append(f"{indent}acc = acc.pop_nest();")
            elif op.operation_type == OperationType.JOIN_BEGIN:
                item_id = f"label={item.label!r}" if item.label else f"term={type(item.term).__name__}"
                if op.separator is None:
                    # Name the rule/position/item, mirroring the unsupported-Doc-type wrap below,
                    # so a missing-separator config error is diagnosable without a stack trace.
                    msg = (
                        f"Rule {rule_name!r} {position}-anchor JOIN_BEGIN for {item_id} "
                        f"is missing the required separator"
                    )
                    raise RuntimeError(msg)
                try:
                    separator_expr = self._doc_to_rust_expr(op.separator)
                except ValueError as exc:
                    msg = (
                        f"Rule {rule_name!r} {position}-anchor JOIN_BEGIN for {item_id} "
                        f"uses unsupported Doc type: {exc}"
                    )
                    raise ValueError(msg) from exc
                lines.append(f"{indent}acc = acc.push_join({separator_expr});")
            elif op.operation_type == OperationType.JOIN_END:
                lines.append(f"{indent}acc = acc.pop_join();")
            else:
                # The branches above are exhaustive over the current OperationType enum
                # (SPACING is skipped; the six begin/end ops are handled). A new enum member
                # reaching here would silently drop a push/pop and emit an unbalanced
                # accumulator stack, so fail loudly at generation time instead.
                msg = f"Unsupported OperationType in item anchor: {op.operation_type!r}"
                raise ValueError(msg)
        return lines

    def _gen_item_method(
        self, prefix: str, rule_name: str, class_name: str, alt_idx: int, item_idx: int, item: gsm.Item
    ) -> list[str]:
        """Emit the ``{prefix}__alt{N}__item{M}`` method, plus nested methods for a sub-expression.

        The accumulator is threaded by value and the
        position by ``usize``.  The body routes on disposition/quantifier
        (:meth:`_gen_item_body`): a ``SUPPRESS`` item via :meth:`_gen_suppressed_item_body`;
        a single (non-multiple) ``INCLUDE``/``INLINE`` literal term via
        :meth:`_gen_literal_term_body`, a single identifier (rule-reference) term via
        :meth:`_gen_identifier_term_body`, a single regex term via
        :meth:`_gen_regex_term_body`, and a single sub-expression term via
        :meth:`_gen_subexpr_term_body`.  A multiple-quantifier (``+``/``*``) item loops over a
        per-occurrence ``__inner`` method (:meth:`_gen_quantified_loop_body`).

        Returns a list of method-source blocks: the item method itself, followed by either the
        ``{item_prefix}__inner`` per-occurrence method (when the item routes to a quantified
        loop — :meth:`_item_routes_to_quantified_loop`) or, for a non-quantified
        sub-expression item (:meth:`_item_routes_to_subexpr`), the nested ``__alts`` dispatch
        and its alternatives/items, recursively.
        """
        item_prefix = f"{prefix}__alt{alt_idx}__item{item_idx}"
        body = self._gen_item_body(item_prefix, rule_name, class_name, item)
        # A SUPPRESS or INLINE-literal item body never reads `node`; name the param accordingly
        # so the generated method is unused-variable clean under -D warnings.
        node_param = self._node_param(body)
        lines: list[str] = [
            f"    fn {item_prefix}"
            f"(&self, {node_param}: &cst::{class_name}, pos: usize, acc: DocAccumulator) -> Option<UnparseResult> {{"
        ]
        lines.extend(body)
        lines.append("    }")
        blocks = ["\n".join(lines)]
        if self._item_routes_to_quantified_loop(item):
            # A multiple-quantifier item's body loops over a per-occurrence __inner method,
            # emitted here as a sibling (along with its own nested __alts tree if it is a
            # sub-expression). This precedes the sub-expression branch: a quantified
            # sub-expression's nested methods hang off __inner, not the item method directly.
            blocks.extend(self._gen_inner_methods(item_prefix, rule_name, class_name, item))
        elif self._item_routes_to_subexpr(item):
            assert isinstance(item.term, list | tuple)  # narrowed by _item_routes_to_subexpr
            blocks.extend(self._gen_subexpr_methods(item_prefix, rule_name, class_name, item.term))
        return blocks

    def _item_routes_to_quantified_loop(self, item: gsm.Item) -> bool:
        """Return ``True`` iff this item's body is a multiple-quantifier (``+``/``*``) loop.

        Mirrors the routing in :meth:`_gen_item_body`: a non-suppressed item with a multiple
        quantifier reaches :meth:`_gen_quantified_loop_body` (and so needs its
        ``{item_prefix}__inner`` sibling method).  ``SUPPRESS`` is excluded because a
        suppressed quantified item is reconstructed as the grammar minimum by
        :meth:`_gen_suppressed_item_body` (the Python ``gen_item_unparser`` checks ``SUPPRESS``
        before the multiple-quantifier branch, ``gsm2unparser.py:462``), never as a loop.  Like
        :meth:`_item_routes_to_subexpr`, this single predicate keeps the body-routing and
        sibling-emission decisions from drifting.
        """
        return item.disposition != gsm.Disposition.SUPPRESS and item.quantifier.is_multiple()

    def _item_routes_to_subexpr(self, item: gsm.Item) -> bool:
        """Return ``True`` iff this item's body routes to a sub-expression ``__alts`` call.

        Mirrors the routing in :meth:`_gen_item_body` / :meth:`_gen_term_body`: a
        sub-expression term (``Sequence[Items]`` — a ``list``/``tuple`` of nested
        alternatives) reaches :meth:`_gen_subexpr_term_body` only when the item is neither
        ``SUPPRESS`` (handled by :meth:`_gen_suppressed_item_body`) nor multiple-quantified
        (a multiple-quantified sub-expression routes to :meth:`_gen_quantified_loop_body`,
        whose ``__inner`` method owns the nested ``__alts`` tree).  When this holds,
        :meth:`_gen_item_method` must also emit the nested ``__alts`` method tree the call
        targets, so this single predicate keeps the body-routing and sibling-emission
        decisions from drifting.
        """
        return (
            item.disposition != gsm.Disposition.SUPPRESS
            and not item.quantifier.is_multiple()
            and isinstance(item.term, list | tuple)
        )

    def _gen_item_body(self, item_prefix: str, rule_name: str, class_name: str, item: gsm.Item) -> list[str]:
        """Emit the body lines (8-space indented) of an ``__item{M}`` method.

        Routing order: ``SUPPRESS`` is checked first (suppressed items are not in the CST
        and so cannot be position-extracted), then multiple-quantifier loops
        (:meth:`_gen_quantified_loop_body`), then single-term handling.  The ``SUPPRESS``
        branch, the multiple-quantifier loop, and the single-term
        ``Identifier``/``Literal``/``Regex``/sub-expression branches all emit their full body.
        ``item_prefix`` is the item method's name, used to name the generated ``__inner``
        (quantified loop) or ``__alts`` (sub-expression) method this body delegates to.
        """
        if item.disposition == gsm.Disposition.SUPPRESS:
            return self._gen_suppressed_item_body(item)
        if self._item_routes_to_quantified_loop(item):
            return self._gen_quantified_loop_body(item_prefix, item)
        return self._gen_term_body(item_prefix, rule_name, class_name, item)

    def _gen_quantified_loop_body(self, item_prefix: str, item: gsm.Item) -> list[str]:
        """Emit the loop body of a multiple-quantifier (``+``/``*``) item.

        Ports ``_gen_quantified_item_body`` (``gsm2unparser.py:533``): repeatedly call the
        per-occurrence ``{item_prefix}__inner`` method (emitted as a sibling by
        :meth:`_gen_inner_methods`), threading the accumulator/position through each match
        and stopping at the first occurrence that fails or when the children are exhausted.
        ``acc`` is cloned for each attempt (mirroring the optional-item pattern) so a failed
        occurrence leaves the accumulator at its last-successful value, exactly as the Python
        backend keeps ``accumulator`` unchanged when the inner returns ``None``.

        For a ``+`` quantifier (``min() == Arity.ONE``) the loop tracks ``match_count`` and the
        whole item fails (``return None``) when nothing matched, reproducing the Python
        minimum-occurrence check (``gsm2unparser.py:611``).  A ``*`` quantifier
        (``min() == Arity.ZERO``) needs neither the counter nor the check: zero occurrences is
        a valid result.
        """
        inner_fn = f"{item_prefix}__inner"
        is_plus = item.quantifier.min() == gsm.Arity.ONE
        lines: list[str] = []
        lines.append("        let mut current_pos = pos;")
        lines.append("        let mut acc = acc;")
        if is_plus:
            lines.append("        let mut match_count = 0usize;")
        lines.append("        while current_pos < node.children().len() {")
        lines.append(f"            let Some(r) = self.{inner_fn}(node, current_pos, acc.clone()) else {{")
        lines.append("                break;")
        lines.append("            };")
        lines.append("            acc = r.accumulator;")
        lines.append("            current_pos = r.new_pos;")
        if is_plus:
            lines.append("            match_count += 1;")
        lines.append("        }")
        if is_plus:
            lines.append("        if match_count == 0 {")
            lines.append("            return None;")
            lines.append("        }")
        lines.append("        Some(UnparseResult::new(acc, current_pos))")
        return lines

    def _gen_inner_methods(self, item_prefix: str, rule_name: str, class_name: str, item: gsm.Item) -> list[str]:
        """Emit the ``{item_prefix}__inner`` per-occurrence method for a quantified item.

        Mirrors the Python backend, which generates the inner unparser via
        ``gen_term_unparser((*path, "inner"), item, rule_name)`` (``gsm2unparser.py:546``): the
        inner handles a *single* occurrence of the term (the quantifier is irrelevant to one
        occurrence), so its body is :meth:`_gen_term_body` over the same ``item``.  When the
        term is a sub-expression (``Sequence[Items]``) the nested ``__alts`` method tree it
        delegates to is appended as siblings, exactly as :meth:`_gen_item_method` does for a
        non-quantified sub-expression item.
        """
        inner_prefix = f"{item_prefix}__inner"
        body = self._gen_term_body(inner_prefix, rule_name, class_name, item)
        # A single-occurrence INLINE-literal inner body never reads `node`; name the param to
        # match so the generated inner method is unused-variable clean under -D warnings.
        node_param = self._node_param(body)
        lines: list[str] = [
            f"    fn {inner_prefix}"
            f"(&self, {node_param}: &cst::{class_name}, pos: usize, acc: DocAccumulator) -> Option<UnparseResult> {{"
        ]
        lines.extend(body)
        lines.append("    }")
        blocks = ["\n".join(lines)]
        if isinstance(item.term, list | tuple):
            blocks.extend(self._gen_subexpr_methods(inner_prefix, rule_name, class_name, item.term))
        return blocks

    def _gen_term_body(self, item_prefix: str, rule_name: str, class_name: str, item: gsm.Item) -> list[str]:
        """Emit the body of a single (non-suppressed, non-multiple) term.

        Dispatches on term kind, mirroring ``gen_term_unparser``.  The ``Identifier``,
        ``Literal``, ``Regex``, and sub-expression (nested-alternatives) branches emit their
        full body; an unrecognized term kind raises, matching the Python backend's
        ``gen_term_unparser`` ``else`` (``gsm2unparser.py:1820``).
        """
        if isinstance(item.term, gsm.Identifier):
            return self._gen_identifier_term_body(rule_name, class_name, item)
        if isinstance(item.term, gsm.Literal):
            return self._gen_literal_term_body(rule_name, class_name, item)
        if isinstance(item.term, gsm.Regex):
            return self._gen_regex_term_body(rule_name, class_name, item)
        if isinstance(item.term, list | tuple):
            # Sub-expression (nested alternatives): delegate to the generated __alts dispatch.
            # _gen_term_body is reached only for non-suppressed, non-multiple items, so this
            # isinstance check is the term-kind half of _item_routes_to_subexpr, which gates
            # whether _gen_item_method also emits the nested method tree this call targets.
            return self._gen_subexpr_term_body(item_prefix)
        # Unknown term kind (e.g. Invocation): mirror the Python backend's ValueError.
        msg = f"Internal error: Unrecognized term type {type(item.term).__name__} in rule {rule_name!r}"
        raise ValueError(msg)

    def _gen_subexpr_term_body(self, item_prefix: str) -> list[str]:
        """Emit the body of a sub-expression (nested-alternatives) term.

        Ports the ``isinstance(term, list)`` branch of ``gen_term_unparser``
        (``gsm2unparser.py:1791``): the item delegates to the generated ``{item_prefix}__alts``
        dispatch, passing the current ``node``/``pos``/``acc`` through, and returns its result
        directly.  The sub-expression's own label and disposition are intentionally not
        handled here — its children are inlined into the parent CST node, and each inner item
        carries its own label/term handling (matching the Python branch, which ignores both).

        The ``__alts`` dispatch and the nested alternative/item methods it calls are emitted
        as sibling methods by :meth:`_gen_subexpr_methods` (invoked from
        :meth:`_gen_item_method`).
        """
        return [f"        self.{item_prefix}__alts(node, pos, acc)"]

    def _gen_subexpr_methods(
        self, item_prefix: str, rule_name: str, class_name: str, alternatives: Sequence[gsm.Items]
    ) -> list[str]:
        """Emit the nested ``__alts`` dispatch and its alternatives/items for a sub-expression.

        Mirrors the parser backend's ``_gen_subexpr_term`` (``gsm2parser_rs.py:831``) and the
        Python unparser's nested ``gen_alternatives_unparser(..., is_rule_unparser=False)``
        (``gsm2unparser.py:1801``): a ``{item_prefix}__alts`` method tries each
        ``{item_prefix}__alts__alt{K}`` from the *passed* ``pos`` (no rule-level anchors,
        unlike the rule entry) and returns the first success, then the nested alternatives are
        generated through the same :meth:`_gen_alternative` machinery (so a deeper
        sub-expression nested inside one recurses).  All nested methods walk the same enclosing
        ``cst::{class_name}`` node — the sub-expression's children are inlined into the parent.
        """
        alts_prefix = f"{item_prefix}__alts"
        blocks = [self._gen_alts_dispatch(alts_prefix, class_name, len(alternatives))]
        for alt_idx, sub_alt in enumerate(alternatives):
            blocks.extend(self._gen_alternative(alts_prefix, rule_name, class_name, alt_idx, sub_alt))
        return blocks

    def _gen_alts_dispatch(self, alts_prefix: str, class_name: str, n_alts: int) -> str:
        """Emit the ``{alts_prefix}`` nested-alternatives dispatch method.

        Parallels :meth:`_gen_rule_entry`'s alternative dispatch but for a sub-expression: it
        tries each ``{alts_prefix}__alt{K}`` from the *passed* ``pos`` (a sub-expression starts
        mid-node, not at 0) and applies no rule-level anchor operations, returning the first
        alternative that succeeds (Python ``gen_alternatives_unparser`` with
        ``is_rule_unparser=False``).  ``acc`` is cloned for every attempt but the last, which
        moves it.
        """
        lines: list[str] = []
        lines.append(
            f"    fn {alts_prefix}(&self, node: &cst::{class_name}, pos: usize, acc: DocAccumulator) "
            f"-> Option<UnparseResult> {{"
        )
        lines.extend(self._gen_alt_dispatch_loop(alts_prefix, n_alts, "pos"))
        lines.append("    }")
        return "\n".join(lines)

    def _gen_identifier_term_body(self, rule_name: str, class_name: str, item: gsm.Item) -> list[str]:
        """Emit the body of an identifier (rule-reference) term.

        The child at ``pos`` is validated (bounds + optional label, via
        :meth:`_gen_child_prelude`) and its rule-reference child-enum variant is matched to
        extract the ``Shared<{RefClass}>`` handle; the handle is read-locked and the
        referenced rule's ``unparse_{ref_rule}`` is called.  On success the child's
        accumulator is merged via ``add_accumulator`` and ``pos`` advances by one; a failed
        child unparse (``?``) or a mismatched child variant (``_ => return None``) fails the
        enclosing alternative.

        The catch-all ``_ => return None`` arm is emitted only when the child enum has more
        than one variant: for a single-variant enum the one binding arm is exhaustive and a
        catch-all would be an ``unreachable_patterns`` error (matching the span path's
        ``num_variants > 1`` guard and the CST generator's ``_child_enum_block``).
        """
        if not isinstance(item.term, gsm.Identifier):
            # Internal routing invariant: _gen_term_body dispatches Identifier terms here.
            # Use an explicit raise (not assert, which `python -O` strips) so a misrouted
            # term names its rule instead of silently reading item.term.value off the wrong
            # type and emitting plausible-but-wrong Rust.
            msg = (
                f"Internal error: _gen_identifier_term_body reached with "
                f"{type(item.term).__name__} term in rule {rule_name!r}"
            )
            raise RuntimeError(msg)
        if item.disposition != gsm.Disposition.INCLUDE:
            # An inlined (`!`) rule reference is not a CST child: gsm2tree incorporates the
            # inlined rule's model into the parent rather than adding a child variant, so there
            # is no child position to extract. The Python backend rejects this too
            # (_extract_and_validate_nonsequence_child raises for non-INCLUDE dispositions);
            # reject identically for cross-backend parity rather than emit
            # INCLUDE-shaped extraction that references nonexistent enum variants.
            msg = (
                f"Cannot generate unparser for rule {rule_name!r}: identifier term "
                f"'{item.term.value}' has disposition {item.disposition}; only INCLUDE "
                "identifier references can be unparsed (an inlined rule reference is not a "
                "CST child and cannot be reconstructed)."
            )
            raise RuntimeError(msg)
        ref_rule_name = item.term.value
        ref_class = self._class_name(ref_rule_name)
        num_variants = self._cst.num_child_variants(rule_name)
        child_enum = self._cst.child_enum_name(class_name)

        # Identifier always reads child_tuple.1 to extract the Shared handle.
        lines = self._gen_child_prelude(class_name, item, need_tuple=True)
        if num_variants > 1:
            lines.append("        let shared = match &child_tuple.1 {")
            lines.append(f"            cst::{child_enum}::{ref_class}(shared) => shared,")
            lines.append("            _ => return None,")
            lines.append("        };")
        else:
            # Single-variant child enum: the destructure is irrefutable, so an irrefutable `let`
            # is the idiomatic form (clippy::infallible_destructuring_match rejects a single-arm
            # match here).
            lines.append(f"        let cst::{child_enum}::{ref_class}(shared) = &child_tuple.1;")
        lines.append("        let guard = shared.read();")
        lines.append(f"        let child_result = self.unparse_{ref_rule_name}(&guard)?;")
        lines.append("        let acc = acc.add_accumulator(&child_result.accumulator);")
        lines.append("        Some(UnparseResult::new(acc, pos + 1))")
        return lines

    def _gen_literal_term_body(self, rule_name: str, class_name: str, item: gsm.Item) -> list[str]:
        """Emit the body of an INCLUDE/INLINE literal term.

        The literal text is re-emitted via ``add_non_trivia(text(...))``.  For ``INCLUDE``
        the literal occupies a ``Span`` child position, so the child at ``pos`` is validated
        (:meth:`_gen_validate_span_child`) and ``pos`` advances by one; other dispositions
        (``INLINE``) emit the text without consuming a CST position.
        """
        if not isinstance(item.term, gsm.Literal):
            # Internal routing invariant (see _gen_identifier_term_body): explicit raise
            # rather than an -O-strippable assert, so a misrouted term names its rule instead
            # of silently embedding a regex pattern / rule name as literal text.
            msg = (
                f"Internal error: _gen_literal_term_body reached with "
                f"{type(item.term).__name__} term in rule {rule_name!r}"
            )
            raise RuntimeError(msg)
        text_expr = f'fltk_unparser_core::text("{rust_str_lit(item.term.value)}")'
        lines: list[str] = []
        if item.disposition == gsm.Disposition.INCLUDE:
            lines.extend(self._gen_validate_span_child(rule_name, class_name, item))
            lines.append(f"        let acc = acc.add_non_trivia({text_expr});")
            lines.append("        Some(UnparseResult::new(acc, pos + 1))")
        else:
            lines.append(f"        let acc = acc.add_non_trivia({text_expr});")
            lines.append("        Some(UnparseResult::new(acc, pos))")
        return lines

    def _gen_regex_term_body(self, rule_name: str, class_name: str, item: gsm.Item) -> list[str]:
        """Emit the body of a regex term.

        Ports the ``Regex`` branch of ``gen_term_unparser`` (``gsm2unparser.py:1750``).
        Unlike a literal (whose text is fixed at generation time), a regex's text is the
        captured source: the child at ``pos`` is validated (bounds + optional label, via
        :meth:`_gen_child_prelude`) and its ``Span`` is bound, then its text is read via
        ``span.text()`` and the position advances by one.

        Only ``INCLUDE`` regex terms are supported.  The Python backend's ``Regex`` branch
        extracts the ``Span`` child *unconditionally* (``gsm2unparser.py:1756`` calls
        ``_extract_and_validate_nonsequence_child``, whose first statement raises for any
        non-``INCLUDE`` disposition, ``:267``): a regex has no fixed text to re-emit and no
        extractable CST child under a non-``INCLUDE`` disposition.  This backend rejects a
        non-``INCLUDE`` (``INLINE``) regex identically for cross-backend parity
        with an explicit ``raise`` that survives ``python -O`` -- where the ``CstGenerator``'s
        ``INLINE``-must-be-``Identifier`` assert (``gsm2tree.py:630``) is stripped.

        Because the Rust CST carries no ``terminals`` fallback, a ``None`` from
        ``span.text()`` (a sourceless span) makes the enclosing rule ``return None`` via
        ``?`` -- a deliberate failure mode, rather than silently emitting empty
        text.

        The catch-all ``_ => return None`` arm on the ``Span``-binding ``match`` is emitted
        only when the child enum has more than one variant (matching the span/identifier
        paths' ``num_variants > 1`` guard and the CST generator's ``_child_enum_block``):
        for a single-variant (``Span``-only) enum the one binding arm is exhaustive and a
        catch-all would be an ``unreachable_patterns`` error.
        """
        if not isinstance(item.term, gsm.Regex):
            # Internal routing invariant (see _gen_literal_term_body / _gen_identifier_term_body):
            # explicit raise rather than an -O-strippable assert, so a misrouted term names its
            # rule instead of silently emitting span.text() for a literal/identifier (which would
            # read the captured source rather than the fixed literal text).
            msg = (
                f"Internal error: _gen_regex_term_body reached with "
                f"{type(item.term).__name__} term in rule {rule_name!r}"
            )
            raise RuntimeError(msg)
        if item.disposition != gsm.Disposition.INCLUDE:
            # Reject non-INCLUDE (INLINE) regex, matching the Python backend's unconditional
            # _extract_and_validate_nonsequence_child rejection (see docstring): a regex's text
            # is the captured source, so there is no fixed text to re-emit and no CST child to
            # extract under a non-INCLUDE disposition.
            msg = (
                f"Cannot generate unparser for rule {rule_name!r}: regex term has disposition "
                f"{item.disposition}; only INCLUDE regex terms can be unparsed."
            )
            raise RuntimeError(msg)
        num_variants = self._cst.num_child_variants(rule_name)
        child_enum = self._cst.child_enum_name(class_name)

        # Regex always reads child_tuple.1 to bind the captured Span.
        lines = self._gen_child_prelude(class_name, item, need_tuple=True)
        if num_variants > 1:
            lines.append("        let span = match &child_tuple.1 {")
            lines.append(f"            cst::{child_enum}::Span(span) => span,")
            lines.append("            _ => return None,")
            lines.append("        };")
        else:
            # Single-variant child enum: irrefutable destructure via `let` (clippy
            # ::infallible_destructuring_match rejects a single-arm match here).
            lines.append(f"        let cst::{child_enum}::Span(span) = &child_tuple.1;")
        # TODO(unparser-none-path-diagnostics): a `None` from `span.text()` (a sourceless/sentinel
        # span) propagates up via `?` to the public `unparse_*` entry point with no record of which
        # labeled span lacked source. In the fltkfmt pipeline spans always carry source, so this is
        # an invariant-violation path; if/when diagnostics are added, log the failing label here
        # before returning None, and keep the Python backend in lockstep for parity.
        lines.append("        let text = span.text()?;")
        lines.append("        let acc = acc.add_non_trivia(fltk_unparser_core::text(text));")
        lines.append("        Some(UnparseResult::new(acc, pos + 1))")
        return lines

    def _gen_child_prelude(self, class_name: str, item: gsm.Item, *, need_tuple: bool) -> list[str]:
        """Emit the shared bounds/label prelude for a non-sequence child at ``pos``.

        Common to the ``Span`` (literal/regex) and rule-reference (identifier) child
        validations: bind ``node.children()``, bounds-check (``pos >= children.len()`` ->
        ``return None``), optionally bind the child tuple, and (when the item is labeled)
        check ``child_tuple.0`` against the expected ``cst::{CN}Label::{Variant}``.  The
        caller appends the term-specific child-enum variant handling.

        ``need_tuple`` requests the ``let child_tuple = &children[pos];`` binding for callers
        that read ``child_tuple.1`` (the identifier path's ``Shared`` extraction, the span
        path's variant ``match``).  The tuple is *also* bound whenever the item is labeled,
        so the label check below always has its operand regardless of ``need_tuple`` — the
        method self-enforces the "labeled ⇒ tuple bound" invariant rather than relying on
        callers to pass ``need_tuple=True`` for labeled items.
        """
        lines: list[str] = []
        lines.append("        let children = node.children();")
        lines.append("        if pos >= children.len() {")
        lines.append("            return None;")
        lines.append("        }")
        if need_tuple or item.label:
            lines.append("        let child_tuple = &children[pos];")
        if item.label:
            label_enum = self._cst.label_enum_name(class_name)
            variant = naming.snake_to_upper_camel(item.label)
            lines.append(f"        if child_tuple.0 != Some(cst::{label_enum}::{variant}) {{")
            lines.append("            return None;")
            lines.append("        }")
        return lines

    def _gen_validate_span_child(self, rule_name: str, class_name: str, item: gsm.Item) -> list[str]:
        """Emit the bounds/label/type validation for a ``Span`` (literal/regex) child at ``pos``.

        The shared bounds/label prelude (:meth:`_gen_child_prelude`) plus a child-enum
        variant check that the value is ``cst::{CN}Child::Span(_)``; a non-``Span`` variant
        takes the ``_ => return None`` arm, letting the enclosing alternative fail.

        The variant ``match`` (and its catch-all) is emitted only when the child enum has
        more than one variant, matching the CST generator's ``num_variants > 1`` guard in
        ``_child_enum_block``.  For a single-variant (``Span``-only) enum the type is
        statically guaranteed, so only the bounds (and any label) check remain -- emitting
        an unconditional ``match`` there would either be a vacuous single-arm match or, with
        a catch-all, an ``unreachable_patterns`` error.
        """
        num_variants = self._cst.num_child_variants(rule_name)
        # _gen_child_prelude binds child_tuple on its own whenever the item is labeled, so we
        # only need to request it here for the variant match (num_variants > 1).
        need_tuple = num_variants > 1

        lines = self._gen_child_prelude(class_name, item, need_tuple=need_tuple)
        if num_variants > 1:
            child_enum = self._cst.child_enum_name(class_name)
            lines.append("        match &child_tuple.1 {")
            lines.append(f"            cst::{child_enum}::Span(_) => {{}}")
            lines.append("            _ => return None,")
            lines.append("        }")
        return lines

    def _gen_suppressed_item_body(self, item: gsm.Item) -> list[str]:
        """Emit the body of a ``SUPPRESS`` item.

        Suppressed items are absent from the CST, so the position is never advanced and the
        node is never read.  The grammar minimum is reconstructed:

        - optional (``?``/``*``, ``min == 0``): emit nothing, pass acc/pos through.
        - required literal: re-emit the literal text via ``add_non_trivia(text(...))``.
        - required regex / identifier / sub-expression: cannot be reconstructed from the
          CST -- raise at generation time with the same messages as the Python backend.
        """
        if item.quantifier.is_optional():
            # Optional suppressed items contribute the grammar minimum of zero occurrences.
            return ["        Some(UnparseResult::new(acc, pos))"]
        if isinstance(item.term, gsm.Literal):
            text_expr = f'fltk_unparser_core::text("{rust_str_lit(item.term.value)}")'
            return [
                f"        let acc = acc.add_non_trivia({text_expr});",
                "        Some(UnparseResult::new(acc, pos))",
            ]
        if isinstance(item.term, gsm.Regex):
            msg = (
                f"Cannot generate unparser: required suppressed regex '{item.term.value}' "
                "cannot be recreated from CST. Consider adding a label to include it."
            )
            raise RuntimeError(msg)
        if isinstance(item.term, gsm.Identifier):
            msg = (
                f"Cannot generate unparser: required suppressed rule reference '{item.term.value}' "
                "cannot be recreated from CST. Consider removing the suppression."
            )
            raise RuntimeError(msg)
        msg = (
            f"Cannot generate unparser: required suppressed term of type {type(item.term).__name__} "
            "cannot be recreated from CST. Consider adding a label or removing the suppression."
        )
        raise RuntimeError(msg)

    # ------------------------------------------------------------------
    # Separator / trivia processing
    # ------------------------------------------------------------------

    def _gen_trivia_processing(
        self, rule_name: str, class_name: str, separator: gsm.Separator, indent: str
    ) -> list[str]:
        """Emit separator/trivia processing for one inter-item gap.

        Ports the dispatch of ``_gen_trivia_processing`` (``gsm2unparser.py:1084``).  Only a
        ``WS_REQUIRED``/``WS_ALLOWED`` separator produces output (a ``NO_WS`` separator emits
        nothing, matching the Python early return, ``:1098``).  For a WS separator inside a
        *trivia rule* the trivia-rule branch (:meth:`_gen_trivia_rule_processing`) consumes the
        rule's own unlabeled whitespace ``Span`` children and counts newlines.

        For a WS separator inside a *non-trivia rule* the non-trivia-rule branch
        (:meth:`_gen_non_trivia_rule_processing`) looks up a ``Trivia`` child at ``pos``, calls
        the generated ``unparse__trivia``, and wraps preserved output in a ``SeparatorSpec``.
        ``rule_name`` names the enclosing rule (a sub-expression's separators query the parent
        rule, as in the Python backend, which looks the rule up by ``rule_name``); ``class_name``
        is its CST struct.
        """
        if separator not in (gsm.Separator.WS_REQUIRED, gsm.Separator.WS_ALLOWED):
            return []
        rule = self._grammar.identifiers.get(rule_name)
        if rule is not None and rule.is_trivia_rule:
            return self._gen_trivia_rule_processing(rule_name, class_name, separator, indent)
        return self._gen_non_trivia_rule_processing(rule_name, class_name, separator, indent)

    def _gen_trivia_rule_processing(
        self, rule_name: str, class_name: str, separator: gsm.Separator, indent: str
    ) -> list[str]:
        """Emit the trivia-rule branch of ``_gen_trivia_processing`` (``gsm2unparser.py:1103``).

        A trivia rule (e.g. ``_trivia``) captures the whitespace matched by its own WS
        separators as unlabeled ``Span`` children.  At each WS gap this consumes that
        whitespace child (advancing ``pos``), counts its newlines, and emits the appropriate
        ``SeparatorSpec``:

        - ``preserve_blanks > 0``: a blank line (``>= 2`` newlines) emits a ``HardLine`` with the
          configured blank-line count; a single newline (``>= 1``) emits a plain ``HardLine``
          (line structure for comments); no newline uses the default separator spacing.
        - ``preserve_blanks == 0``: a newline (``>= 1``) emits a plain ``HardLine``; no newline
          uses the default separator spacing.

        When the child at ``pos`` is *not* an unlabeled whitespace ``Span`` (labeled, or a
        different child variant), a ``WS_REQUIRED`` gap fails the alternative (``return None``)
        and a ``WS_ALLOWED`` gap emits the default separator spacing.  Out of bounds, a
        ``WS_REQUIRED`` gap likewise fails and a ``WS_ALLOWED`` gap emits nothing (matching the
        Python ``if_in_bounds`` having an ``orelse`` only for ``WS_REQUIRED``, ``:1113``/``:1259``).

        ``preserve_blanks`` reads the *global* ``trivia_config.preserve_blanks`` exactly as the
        Python branch does (``:1168``), not the rule-aware ``get_preserve_blanks``.
        """
        is_required = separator == gsm.Separator.WS_REQUIRED
        child_enum = self._cst.child_enum_name(class_name)
        preserve_blanks = self._get_preserve_blanks()

        i0 = indent
        i1 = indent + "    "
        i2 = indent + "        "
        i3 = indent + "            "

        lines: list[str] = []
        lines.append(f"{i0}if pos < node.children().len() {{")
        # Unlabeled whitespace span: label is None and the child value is a Span. A labeled or
        # non-Span child takes the else arm (the Python `is_unlabeled and is_span` guard, :1140).
        lines.append(f"{i1}if let (None, cst::{child_enum}::Span(span)) = &node.children()[pos] {{")
        lines.append(f"{i2}pos += 1;")
        # Borrowing accessor (no per-gap String allocation); the slice is only scanned for newlines.
        lines.append(f"{i2}let newline_count = span.text_str().map(|t| t.matches('\\n').count()).unwrap_or(0);")
        # Trivia-rule branch preserves comment line structure even at preserve_blanks == 0
        # (preserve_line_at_zero=True), matching gsm2unparser.py:1216-1242.
        lines.extend(
            self._gen_newline_separator_ladder(
                rule_name=rule_name,
                separator=separator,
                is_required=is_required,
                preserve_blanks=preserve_blanks,
                preserve_line_at_zero=True,
                outer_indent=i2,
                inner_indent=i3,
            )
        )
        lines.append(f"{i1}}} else {{")
        if is_required:
            # WS_REQUIRED with no whitespace span present: the alternative cannot match.
            lines.append(f"{i2}return None;")
        else:
            lines.extend(self._add_default_separator_spec_lines(rule_name, separator, i2))
        lines.append(f"{i1}}}")
        if is_required:
            # WS_REQUIRED out of bounds: the alternative cannot match. (WS_ALLOWED emits no
            # else arm — matching the Python `if_in_bounds` orelse only for WS_REQUIRED.)
            lines.append(f"{i0}}} else {{")
            lines.append(f"{i1}return None;")
            lines.append(f"{i0}}}")
        else:
            lines.append(f"{i0}}}")
        return lines

    def _gen_non_trivia_rule_processing(
        self, rule_name: str, class_name: str, separator: gsm.Separator, indent: str
    ) -> list[str]:
        """Emit the non-trivia-rule branch of ``_gen_trivia_processing`` (``gsm2unparser.py:1265``).

        A regular (non-trivia) rule with a WS separator captures the inter-item whitespace and
        comments as a single ``Trivia`` child node.  At each WS gap this — guarded by
        ``!acc.last_was_trivia()`` so two consecutive trivia gaps do not double-emit — looks up the
        child at ``pos``; when it is a ``Trivia`` child it read-locks the ``Shared<Trivia>`` and:

        - **preservable trivia** (``_has_preservable_trivia``): calls the generated
          ``unparse__trivia`` and, on success, wraps the trivia's own ``Doc`` in a
          ``SeparatorSpec`` (``spacing=None``, ``preserved_trivia=Some(...)``) so trivia
          preservation takes precedence over default spacing.  On failure
          (``unparse__trivia`` returns ``None``) no separator spec is emitted — a faithful
          port of Python's ``if_trivia_success`` having no ``orelse`` (``gsm2unparser.py:1321``);
          ``pos`` advances past the ``Trivia`` child either way.
        - **no preservable content**: with ``preserve_blanks > 0`` it counts the trivia's newlines
          (``_count_newlines_in_trivia``) and emits a blank-line / single-newline / default
          ``SeparatorSpec`` (as the trivia-rule branch does). With ``preserve_blanks == 0`` it emits
          the configured default ``SeparatorSpec`` *unconditionally* — no newline check. This is
          the one place the non-trivia branch deliberately differs from the trivia-rule branch: the
          Python non-trivia ``preserve_blanks == 0`` arm does no line-structure preservation
          (``gsm2unparser.py:1392-1399``), whereas the trivia-rule branch keeps a single-newline
          ``HardLine`` for comments. The shared :meth:`_gen_newline_separator_ladder` encodes the
          difference via ``preserve_line_at_zero``.

        ``pos`` always advances past the ``Trivia`` child (Python ``:1402``).  When the child at
        ``pos`` is not a ``Trivia`` node, or ``pos`` is out of bounds, the default separator
        spacing is emitted — regardless of ``WS_REQUIRED`` vs ``WS_ALLOWED`` (the non-trivia branch
        never ``return None``s, unlike the trivia-rule branch).

        The ``_ => { … }`` not-a-``Trivia`` arm is emitted only when the rule's child enum has
        more than one variant (matching the ``num_child_variants > 1`` guard used by the term
        bodies / the CST generator's ``_child_enum_block``): for a ``Trivia``-only child enum the
        single ``Trivia`` arm is exhaustive and a catch-all would be an ``unreachable_patterns``
        error.  A WS separator on a non-trivia rule always implies a ``Trivia`` child variant
        (the captured inter-item trivia), so the ``Trivia`` arm itself always resolves.

        ``preserve_blanks`` reads the *global* ``trivia_config.preserve_blanks`` exactly as the
        Python branch does (``:1341``), not the rule-aware ``get_preserve_blanks``.
        """
        is_required = separator == gsm.Separator.WS_REQUIRED
        child_enum = self._cst.child_enum_name(class_name)
        trivia_class = self._cst.class_name_for_rule(gsm.TRIVIA_RULE_NAME)
        num_variants = self._cst.num_child_variants(rule_name)
        preserve_blanks = self._get_preserve_blanks()

        i0 = indent
        i1 = indent + "    "
        i2 = indent + "        "
        i3 = indent + "            "
        i4 = indent + "                "
        i5 = indent + "                    "
        i6 = indent + "                        "

        lines: list[str] = []
        # Skip a fresh separator spec right after a trivia child was already consumed
        # (Python `if not accumulator.last_was_trivia`, gsm2unparser.py:1266).
        lines.append(f"{i0}if !acc.last_was_trivia() {{")
        lines.append(f"{i1}if pos < node.children().len() {{")
        lines.append(f"{i2}match &node.children()[pos].1 {{")
        lines.append(f"{i3}cst::{child_enum}::{trivia_class}(trivia_shared) => {{")
        lines.append(f"{i4}let trivia_node = trivia_shared.read();")
        lines.append(f"{i4}if self._has_preservable_trivia(&trivia_node) {{")
        # Preservable trivia: render it and wrap in a SeparatorSpec carrying the preserved Doc.
        # TODO(unparser-none-path-diagnostics): there is no `else` arm here, so when
        # `_has_preservable_trivia` confirmed comments exist but `unparse__trivia` returns None
        # (a label mismatch or a sourceless content span), the None is silently discarded and the
        # comment is dropped from the formatted output with zero diagnostic signal. Decide a
        # cross-backend policy (log-and-continue / debug_assert / halt), emit a matching
        # diagnostic in the `else`, and mirror it in the Python backend to preserve parity.
        lines.append(f"{i5}if let Some(trivia_result) = self.unparse__trivia(&trivia_node) {{")
        lines.extend(
            self._add_separator_spec_lines(
                rule_name=rule_name,
                spacing=None,
                preserved_trivia_expr="trivia_result.accumulator.doc()",
                required=is_required,
                indent=i6,
                context="preserved trivia spacing",
            )
        )
        lines.append(f"{i5}}}")
        lines.append(f"{i4}}} else {{")
        # No preservable content: newline-driven spacing when preserve_blanks > 0, else the
        # configured default. Unlike the trivia-rule branch, the preserve_blanks == 0 case is an
        # *unconditional* default with no newline check -- the Python non-trivia arm does no
        # newline preservation here (gsm2unparser.py:1392-1399). Bind newline_count only when the
        # ladder reads it (preserve_blanks > 0), so the == 0 case has no unused binding.
        if preserve_blanks > 0:
            lines.append(f"{i5}let newline_count = self._count_newlines_in_trivia(&trivia_node);")
        lines.extend(
            self._gen_newline_separator_ladder(
                rule_name=rule_name,
                separator=separator,
                is_required=is_required,
                preserve_blanks=preserve_blanks,
                preserve_line_at_zero=False,
                outer_indent=i5,
                inner_indent=i6,
            )
        )
        lines.append(f"{i4}}}")
        # Always advance past the consumed Trivia child (Python :1402).
        lines.append(f"{i4}pos += 1;")
        lines.append(f"{i3}}}")
        if num_variants > 1:
            # Child at pos is not a Trivia node: default separator spacing (Python if_trivia.orelse).
            lines.append(f"{i3}_ => {{")
            lines.extend(self._add_default_separator_spec_lines(rule_name, separator, i4))
            lines.append(f"{i3}}}")
        lines.append(f"{i2}}}")
        lines.append(f"{i1}}} else {{")
        # Out of bounds: default separator spacing (Python if_in_bounds.orelse).
        lines.extend(self._add_default_separator_spec_lines(rule_name, separator, i2))
        lines.append(f"{i1}}}")
        lines.append(f"{i0}}}")
        return lines

    def _gen_trivia_helper_methods(self) -> list[str]:
        """Emit the two trivia utility methods the non-trivia-rule branch calls.

        Ports the Python ``UnparserGenerator``'s ``_gen_has_preservable_trivia_method`` and
        ``_gen_count_newlines_in_trivia_method`` (``gsm2unparser.py:846``/``:971``), emitted once
        per ``Unparser``.  (The Python ``_count_newlines`` span helper has no Rust analog: it is
        inlined as ``span.text().map(|t| t.matches('\\n').count()).unwrap_or(0)`` wherever a span's
        newlines are counted.)  Both reference ``cst::Trivia`` / ``cst::TriviaChild``,
        which always exist (the synthetic ``_trivia`` rule is always present).
        """
        return [
            self._gen_has_preservable_trivia_method(),
            self._gen_count_newlines_in_trivia_method(),
        ]

    def _gen_has_preservable_trivia_method(self) -> str:
        """Emit ``_has_preservable_trivia`` (port of ``gsm2unparser.py:846``).

        Generation-time triage over ``trivia_config.preserve_node_names``:

        - ``None``  → preserve everything: the body is ``true``.
        - ``None``/empty config, or no configured name names an actual trivia child type → the
          body is ``false``.
        - otherwise → loop the trivia node's children and ``return true`` on the first child whose
          variant is one of the configured (and actually-present) trivia child node types.

        The configured names are filtered against the trivia rule's real node-child class names
        (``_child_variants_for_rule``).  The Python backend builds an ``isinstance`` against a CST
        class per configured name; a name that is not an actual trivia child never matches at
        runtime (returning ``False``).  The Rust backend cannot emit a match arm for a
        nonexistent ``TriviaChild`` variant (compile error), so a non-matching name is dropped —
        reproducing the Python "never matches" outcome rather than diverging.
        """
        trivia_class = self._cst.class_name_for_rule(gsm.TRIVIA_RULE_NAME)
        trivia_child_enum = self._cst.child_enum_name(trivia_class)
        tc = self._formatter_config.trivia_config

        if tc is not None and tc.preserve_node_names is None:
            param = "_trivia_node"
            body = ["        true"]
        else:
            if tc is None or not tc.preserve_node_names:
                filtered: list[str] = []
            else:
                child_set = set(self._cst.child_class_names_for_rule(gsm.TRIVIA_RULE_NAME))
                filtered = [n for n in sorted(tc.preserve_node_names) if n in child_set]
            if not filtered:
                param = "_trivia_node"
                body = ["        false"]
            else:
                param = "trivia_node"
                arms = " | ".join(f"cst::{trivia_child_enum}::{n}(_)" for n in filtered)
                # `if let` (rather than a single-arm `match` with a `_ => {}` catch-all) keeps the
                # generated helper clippy-clean (`single_match`) regardless of how many trivia
                # child variants exist; or-patterns in `if let` are stable.
                body = [
                    "        for child in trivia_node.children() {",
                    f"            if let {arms} = &child.1 {{",
                    "                return true;",
                    "            }",
                    "        }",
                    "        false",
                ]

        # A grammar with no non-trivia WS gap (or, for _count_newlines_in_trivia, with
        # preserve_blanks == 0) never calls this helper; allow(dead_code) keeps such generated
        # unparsers (a supported downstream case) clippy-clean.
        lines = [
            "    #[allow(dead_code)]",
            f"    fn _has_preservable_trivia(&self, {param}: &cst::{trivia_class}) -> bool {{",
        ]
        lines.extend(body)
        lines.append("    }")
        return "\n".join(lines)

    def _gen_count_newlines_in_trivia_method(self) -> str:
        """Emit ``_count_newlines_in_trivia`` (port of ``gsm2unparser.py:971``).

        Sums the newline count of every ``Span`` child of a ``Trivia`` node, using the same
        inline ``span.text().map(...)`` form as the trivia-rule branch (the
        ``_count_newlines`` substitute).  When the trivia child enum has more than one variant
        the ``Span`` child is selected with ``if let`` (not a single-arm ``match`` plus a
        ``_ => {}`` catch-all, which clippy flags as ``single_match``); a ``Span``-only trivia
        rule keeps an exhaustive single-arm ``match`` (no wildcard, already clippy-clean).  The
        ``Span`` variant always exists because a trivia rule always captures whitespace.
        """
        trivia_class = self._cst.class_name_for_rule(gsm.TRIVIA_RULE_NAME)
        trivia_child_enum = self._cst.child_enum_name(trivia_class)
        num_variants = self._cst.num_child_variants(gsm.TRIVIA_RULE_NAME)
        lines = [
            # Called only from the non-trivia branch's preserve_blanks > 0 path; a grammar with
            # preserve_blanks == 0 leaves it uncalled, so allow(dead_code) keeps that (default,
            # downstream-supported) generated unparser clippy-clean.
            "    #[allow(dead_code)]",
            f"    fn _count_newlines_in_trivia(&self, trivia: &cst::{trivia_class}) -> usize {{",
            "        let mut count = 0usize;",
            "        for child in trivia.children() {",
        ]
        # Borrowing accessor (no per-Span String allocation); the slice is only scanned.
        count_stmt = "                count += span.text_str().map(|t| t.matches('\\n').count()).unwrap_or(0);"
        if num_variants > 1:
            lines.extend(
                [
                    f"            if let cst::{trivia_child_enum}::Span(span) = &child.1 {{",
                    count_stmt,
                    "            }",
                ]
            )
        else:
            lines.extend(
                [
                    "            match &child.1 {",
                    f"                cst::{trivia_child_enum}::Span(span) => {{",
                    "    " + count_stmt,
                    "                }",
                    "            }",
                ]
            )
        lines.extend(
            [
                "        }",
                "        count",
                "    }",
            ]
        )
        return "\n".join(lines)

    def _get_preserve_blanks(self) -> int:
        """Return the configured ``preserve_blanks`` (0 when no ``trivia_config``).

        Shared by both trivia branches, which read the *global*
        ``trivia_config.preserve_blanks`` exactly as the Python backend does
        (``gsm2unparser.py:1168``/``:1341``), not the rule-aware ``get_preserve_blanks``.
        """
        if self._formatter_config.trivia_config:
            return self._formatter_config.trivia_config.preserve_blanks
        return 0

    def _gen_newline_separator_ladder(
        self,
        *,
        rule_name: str,
        separator: gsm.Separator,
        is_required: bool,
        preserve_blanks: int,
        preserve_line_at_zero: bool,
        outer_indent: str,
        inner_indent: str,
    ) -> list[str]:
        """Emit the ``newline_count`` -> ``SeparatorSpec`` ladder shared by both trivia branches.

        Assumes a ``newline_count`` binding is already in scope (the trivia-rule branch counts
        the whitespace span's newlines inline; the non-trivia branch counts them via
        ``_count_newlines_in_trivia``).  Ports the ``preserve_blanks`` branching of
        ``_gen_trivia_processing`` (``gsm2unparser.py:1172``/``:1216`` for the trivia-rule branch,
        ``:1348``/``:1392`` for the non-trivia branch):

        - ``preserve_blanks > 0``: a blank line (``>= 2`` newlines) emits a ``HardLine`` carrying
          the configured count; a single newline (``>= 1``) emits a plain ``HardLine``; otherwise
          the default separator spacing.
        - ``preserve_blanks == 0`` with ``preserve_line_at_zero`` (the trivia-rule branch): a
          newline (``>= 1``) emits a plain ``HardLine`` to keep comment line structure; otherwise
          the default spacing.
        - ``preserve_blanks == 0`` without ``preserve_line_at_zero`` (the non-trivia branch): the
          default separator spacing unconditionally -- no newline check, matching the Python
          non-trivia ``preserve_blanks == 0`` arm (``gsm2unparser.py:1392-1399``).  This caller
          must not bind ``newline_count`` (the ladder never reads it here).
        """
        o = outer_indent
        i = inner_indent
        lines: list[str] = []
        if preserve_blanks > 0:
            lines.append(f"{o}if newline_count >= 2 {{")
            lines.extend(
                self._add_separator_spec_lines(
                    rule_name=rule_name,
                    spacing=HardLine(blank_lines=preserve_blanks),
                    preserved_trivia_expr=None,
                    required=is_required,
                    indent=i,
                    context="trivia blank-line spacing",
                )
            )
            lines.append(f"{o}}} else if newline_count >= 1 {{")
            lines.extend(
                self._add_separator_spec_lines(
                    rule_name=rule_name,
                    spacing=HardLine(blank_lines=0),
                    preserved_trivia_expr=None,
                    required=is_required,
                    indent=i,
                    context="trivia newline spacing",
                )
            )
            lines.append(f"{o}}} else {{")
            lines.extend(self._add_default_separator_spec_lines(rule_name, separator, i))
            lines.append(f"{o}}}")
        elif preserve_line_at_zero:
            lines.append(f"{o}if newline_count >= 1 {{")
            lines.extend(
                self._add_separator_spec_lines(
                    rule_name=rule_name,
                    spacing=HardLine(blank_lines=0),
                    preserved_trivia_expr=None,
                    required=is_required,
                    indent=i,
                    context="trivia newline spacing",
                )
            )
            lines.append(f"{o}}} else {{")
            lines.extend(self._add_default_separator_spec_lines(rule_name, separator, i))
            lines.append(f"{o}}}")
        else:
            lines.extend(self._add_default_separator_spec_lines(rule_name, separator, o))
        return lines

    def _add_separator_spec_lines(
        self,
        *,
        rule_name: str,
        spacing: Doc | None,
        preserved_trivia_expr: str | None,
        required: bool,
        indent: str,
        context: str,
    ) -> list[str]:
        """Emit ``acc = acc.add_trivia(separator_spec(...));`` for one ``SeparatorSpec``.

        Ports ``_add_separator_spec`` (``gsm2unparser.py:1429``) → ``_create_separator_spec``
        (``:446``): the ``spacing`` ``Doc`` (when present) routes through
        :meth:`_doc_to_rust_expr` — inheriting its Group/Nest/Join/Comment rejection, re-raised
        with rule/``context`` so the offending config entry is identifiable — and the result wraps
        in the ``fltk_unparser_core::separator_spec(spacing, preserved_trivia, required)``
        constructor.  ``preserved_trivia_expr`` is a pre-built Rust expression string (or ``None``);
        the trivia-rule branch always passes ``None`` (the non-trivia branch will supply it).
        """
        if spacing is None:
            spacing_arg = "None"
        else:
            try:
                doc_expr = self._doc_to_rust_expr(spacing)
            except ValueError as exc:
                msg = f"Rule {rule_name!r} {context} uses unsupported Doc type: {exc}"
                raise ValueError(msg) from exc
            spacing_arg = f"Some({doc_expr})"
        trivia_arg = "None" if preserved_trivia_expr is None else f"Some({preserved_trivia_expr})"
        required_arg = "true" if required else "false"
        spec = f"fltk_unparser_core::separator_spec({spacing_arg}, {trivia_arg}, {required_arg})"
        return [f"{indent}acc = acc.add_trivia({spec});"]

    def _add_default_separator_spec_lines(self, rule_name: str, separator: gsm.Separator, indent: str) -> list[str]:
        """Emit the default ``SeparatorSpec`` for a separator (port of ``_add_default_separator_spec``, ``:1447``).

        Queries the generation-time ``FormatterConfig`` for the separator's spacing
        (``get_spacing_for_separator``) and wraps it via :meth:`_add_separator_spec_lines` with
        no preserved trivia and ``required`` set for a ``WS_REQUIRED`` separator.
        """
        spacing = self._formatter_config.get_spacing_for_separator(rule_name, separator)
        return self._add_separator_spec_lines(
            rule_name=rule_name,
            spacing=spacing,
            preserved_trivia_expr=None,
            required=separator == gsm.Separator.WS_REQUIRED,
            indent=indent,
            context=f"default {separator.name} separator spacing",
        )

    # ------------------------------------------------------------------
    # Doc -> Rust expression
    # ------------------------------------------------------------------

    def _doc_to_rust_expr(self, doc: Doc) -> str:
        """Convert a ``FormatterConfig`` ``Doc`` combinator to a Rust ``Doc`` expression.

        Mirrors :meth:`fltk.unparse.gsm2unparser.UnparserGenerator._doc_to_combinator_expr`
        **exactly**: it covers ``Nil``, ``Nbsp``, ``Line``,
        ``SoftLine``, ``HardLine``, ``Text``, and ``Concat``, and raises the same
        ``ValueError("Unknown Doc type: …")`` on anything else -- including ``Group``,
        ``Nest``, and ``Join`` (and ``Comment``, which the spacing config never
        produces).

        The group/nest/join rejection is load-bearing: a ``.fltkfmt``
        ``join … by group(…)`` / ``nest(…)`` / ``join(…)`` yields a ``Group``/``Nest``/
        ``Join`` separator ``Doc`` that the **Python** backend already rejects here.
        The Rust backend must reject it identically rather than silently emit a
        ``Doc::Group``/``Nest``/``Join``, or the two backends diverge.

        Literal text is escaped via the parser backend's :func:`rust_str_lit`.
        """
        # Nil/Nbsp/Line/SoftLine/HardLine emit a bare ``Doc::`` constructor and so require the
        # ``Doc`` type import; Text/Concat use fully-qualified ``fltk_unparser_core::`` paths and
        # do not.  Record that the ``Doc`` import is needed so _gen_header can gate it.
        if isinstance(doc, Nil | Nbsp | Line | SoftLine | HardLine):
            self._uses_doc_type = True
        if isinstance(doc, Nil):
            return "Doc::Nil"
        elif isinstance(doc, Nbsp):
            return "Doc::Nbsp"
        elif isinstance(doc, Line):
            return "Doc::Line"
        elif isinstance(doc, SoftLine):
            return "Doc::SoftLine"
        elif isinstance(doc, HardLine):
            return f"Doc::HardLine {{ blank_lines: {doc.blank_lines} }}"
        elif isinstance(doc, Text):
            return f'fltk_unparser_core::text("{rust_str_lit(doc.content)}")'
        elif isinstance(doc, Concat):
            inner = ", ".join(self._doc_to_rust_expr(d) for d in doc.docs)
            return f"fltk_unparser_core::concat(vec![{inner}])"
        else:
            msg = f"Unknown Doc type: {doc}"
            raise ValueError(msg)

    # ------------------------------------------------------------------
    # PyO3 wrapper block
    # ------------------------------------------------------------------

    @staticmethod
    def _gen_py_unparse_prelude_lines(rule_name: str) -> list[str]:
        """Return the shared opening lines of a per-rule PyO3 ``unparse_{rule}*`` method body.

        Both the string-returning ``unparse_{rule}`` and the Doc-returning
        ``unparse_{rule}_doc`` method bodies (emitted in :meth:`_gen_python_bindings`) begin
        identically: read-lock the CST handle, call the inner unparser (``None`` -> ``Ok(None)``),
        and resolve the accumulator's spacing specs.  They diverge only afterward (render to a
        ``String`` vs. wrap the resolved ``Doc`` in a ``PyDoc``).  Single-sourcing the prelude
        here keeps a future change (e.g. a depth-exceeded guard before the ``let Some(r)`` line)
        from having to be mirrored across both method generators.
        """
        return [
            "            let guard = node.shared().read();",
            f"            let Some(r) = self.inner.unparse_{rule_name}(&guard) else {{",
            "                return Ok(None);",
            "            };",
            "            let resolved = resolve_spacing_specs(r.accumulator.doc());",
        ]

    def _gen_python_bindings(self) -> str:
        """Generate the ``python``-gated PyO3 wrapper block for the unparser.

        Parallels :meth:`fltk.fegen.gsm2parser_rs.RustParserGenerator._gen_python_bindings`:
        a ``#[cfg(feature = "python")] mod python_bindings { ... }`` block
        holding a ``#[pyclass(name = "Unparser")] struct PyUnparser`` (so the Python-visible
        class name is ``Unparser``, preserving the public symbol from the Python backend) with
        a no-arg ``#[new]`` constructor, one method per grammar rule, and a
        ``register_classes`` registrar plus its gated ``pub use`` re-export.

        Each per-rule method runs the **full pipeline** and returns the formatted string
        (a deliberate, documented rendered-string divergence from the
        Python backend's intermediate ``UnparseResult`` return):

            #[pyo3(signature = (node, max_width = 80, indent_width = 4))]
            fn unparse_{rule}(&self, node: PyRef<'_, cst::Py{CN}>, max_width, indent_width)
                -> PyResult<Option<String>> {
                let guard = node.shared().read();
                let Some(r) = self.inner.unparse_{rule}(&guard) else { return Ok(None); };
                let resolved = resolve_spacing_specs(r.accumulator.doc());
                let cfg = RendererConfig { indent_width, max_width };
                Ok(Some(Renderer::new(cfg).render(&resolved)))
            }

        The wrapper accepts only the Rust CST handle ``cst::Py{CN}`` (via ``PyRef``), unwraps
        ``shared()`` and read-locks it, exactly as the parser bindings unwrap handles -- a
        pure-Python CST object is rejected by pyo3's argument extraction, enforcing the
        "pair the Rust unparser with the Rust parser" rule.  ``resolve_spacing_specs`` takes
        its ``Doc`` by value (the deep-r1 review change to the core signature), so the design's
        ``&r.accumulator.doc()`` becomes ``r.accumulator.doc()``.

        Rules are iterated as in :meth:`_gen_rule_methods` (and the parser backend), so the
        synthetic ``_trivia`` rule yields an ``unparse__trivia`` method here too, matching the
        Python backend's per-rule public surface.

        Additively, each rule
        also gets an ``unparse_{rule}_doc(node) -> Option<PyDoc>`` method that runs unparse +
        ``resolve_spacing_specs`` and returns the *resolved* ``Doc`` wrapped in a ``PyDoc``
        handle (a ``#[pyclass(name = "Doc", unsendable)]`` -- ``unsendable`` because the core
        ``Doc`` uses ``Rc``).  ``PyDoc::render(max_width, indent_width)`` renders it, so a
        caller can render the same resolved document at multiple widths without re-walking the
        CST, or inspect it via ``repr``.  The string-returning ``unparse_{rule}`` methods are
        unchanged -- the Doc exposure is purely additive.
        """
        lines: list[str] = []
        lines.append('#[cfg(feature = "python")]')
        lines.append("mod python_bindings {")
        lines.append("    use pyo3::prelude::*;")
        lines.append("    use super::cst;")
        lines.append("    use super::Unparser;")
        # The pipeline types live in the root `use fltk_unparser_core::{...}`;
        # reference them through `super::` so that root import is the single source of truth.
        lines.append("    use super::{Renderer, RendererConfig, resolve_spacing_specs};")
        lines.append("")
        lines.append("    /// Generated unparser, callable from Python.")
        lines.append("    ///")
        lines.append("    /// Each `unparse_{rule}` method runs the full pipeline (unparse -> resolve ->")
        lines.append("    /// render) over a Rust-CST handle and returns the formatted string. It accepts")
        lines.append("    /// only the Rust-backed `Py{ClassName}` handles, so a Python caller must pair")
        lines.append("    /// this unparser with the Rust parser backend.")
        lines.append('    #[pyclass(name = "Unparser")]')
        lines.append("    pub struct PyUnparser {")
        lines.append("        inner: Unparser,")
        lines.append("    }")
        lines.append("")
        # PyDoc: the additive intermediate-Doc handle. `unsendable` because the
        # core `Doc` uses `Rc` (the unparser-core crate is single-threaded), so
        # a `PyDoc` may only be touched on the thread that created it. The field uses the
        # fully-qualified `fltk_unparser_core::Doc` path so no extra import is needed (and so it
        # never collides with the header's `_uses_doc_type`-gated `use fltk_unparser_core::Doc;`).
        lines.append("    /// A resolved formatting document, returned by the `unparse_{rule}_doc`")
        lines.append("    /// methods so a caller can render it at multiple widths without re-walking the")
        lines.append("    /// CST, or inspect it via `repr`.")
        lines.append('    #[pyclass(name = "Doc", unsendable)]')
        lines.append("    pub struct PyDoc {")
        lines.append("        resolved: fltk_unparser_core::Doc,")
        lines.append("    }")
        lines.append("")
        lines.append("    #[pymethods]")
        lines.append("    impl PyDoc {")
        lines.append("        /// Render this resolved document to a string at the given width/indent.")
        lines.append("        #[pyo3(signature = (max_width = 80, indent_width = 4))]")
        lines.append("        fn render(&self, max_width: usize, indent_width: usize) -> String {")
        lines.append("            let cfg = RendererConfig { indent_width, max_width };")
        lines.append("            Renderer::new(cfg).render(&self.resolved)")
        lines.append("        }")
        lines.append("")
        lines.append("        fn __repr__(&self) -> String {")
        lines.append('            format!("Doc({:?})", self.resolved)')
        lines.append("        }")
        lines.append("    }")
        lines.append("")
        lines.append("    #[pymethods]")
        lines.append("    impl PyUnparser {")
        lines.append("        #[new]")
        lines.append("        fn new() -> Self {")
        lines.append("            PyUnparser {")
        lines.append("                inner: Unparser::new(),")
        lines.append("            }")
        lines.append("        }")
        for rule in self._grammar.rules:
            class_name = self._class_name(rule.name)
            lines.append("")
            lines.append("        #[pyo3(signature = (node, max_width = 80, indent_width = 4))]")
            lines.append(
                f"        fn unparse_{rule.name}"
                f"(&self, node: PyRef<'_, cst::Py{class_name}>, max_width: usize, indent_width: usize) "
                "-> PyResult<Option<String>> {"
            )
            lines.extend(self._gen_py_unparse_prelude_lines(rule.name))
            lines.append("            let cfg = RendererConfig { indent_width, max_width };")
            lines.append("            Ok(Some(Renderer::new(cfg).render(&resolved)))")
            lines.append("        }")
            # Additive: a doc-returning method that runs unparse + resolve and
            # wraps the resolved Doc in a PyDoc, so a caller can render at multiple widths or
            # inspect it without re-walking the CST. The string method above is unchanged.
            lines.append("")
            lines.append(
                f"        fn unparse_{rule.name}_doc"
                f"(&self, node: PyRef<'_, cst::Py{class_name}>) -> PyResult<Option<PyDoc>> {{"
            )
            lines.extend(self._gen_py_unparse_prelude_lines(rule.name))
            lines.append("            Ok(Some(PyDoc { resolved }))")
            lines.append("        }")
        lines.append("    }")
        lines.append("")
        lines.append("    pub fn register_classes(module: &Bound<'_, pyo3::types::PyModule>) -> PyResult<()> {")
        lines.append("        module.add_class::<PyUnparser>()?;")
        lines.append("        module.add_class::<PyDoc>()?;")
        lines.append("        Ok(())")
        lines.append("    }")
        lines.append("}")
        lines.append('#[cfg(feature = "python")]')
        lines.append("pub use python_bindings::register_classes;")
        return "\n".join(lines)
