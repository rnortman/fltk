from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Callable, Iterable, MutableMapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from fltk import pygen
from fltk.fegen import gsm, naming
from fltk.iir import model as iir
from fltk.iir import typemodel
from fltk.iir.py import compiler as pycompiler
from fltk.iir.py import reg as pyreg

if TYPE_CHECKING:
    from fltk.iir.context import CompilerContext

ModelType = str | typemodel.TypeKey


@dataclass()
class ItemsModel:
    labels: MutableMapping[str, set[ModelType]] = field(default_factory=lambda: defaultdict(set))
    types: set[ModelType] = field(default_factory=set)

    def incorporate(self, other: ItemsModel):
        for label, models in other.labels.items():
            self.labels[label] |= models
        self.types |= other.types


class CstGenerator:
    def __init__(self, grammar: gsm.Grammar, py_module: pyreg.Module, context: CompilerContext):
        self.grammar = grammar
        self.py_module = py_module
        self.context = context
        self.rule_models: dict[str, ItemsModel] = {}
        self.iir_types: dict[str, iir.Type] = {}

        self.Span = iir.Type.make(cname="Span")

        for rule in self.grammar.rules:
            self.rule_models[rule.name] = self.model_for_rule(rule, [])

    def class_name_for_rule_node(self, rule_name: str) -> str:
        return naming.snake_to_upper_camel(rule_name)

    def rule_has_whitespace_separators(self, rule: gsm.Rule) -> bool:
        """Check if a rule has any whitespace separators that would allow trivia."""
        return self._check_items_for_whitespace_separators(rule.alternatives)

    def _check_items_for_whitespace_separators(self, alternatives_list: Sequence[gsm.Items]) -> bool:
        """Recursively check Items for whitespace separators, including in sub-expressions."""
        for alternatives in alternatives_list:
            if alternatives.initial_sep in (gsm.Separator.WS_REQUIRED, gsm.Separator.WS_ALLOWED):
                return True

            for separator in alternatives.sep_after:
                if separator in (gsm.Separator.WS_REQUIRED, gsm.Separator.WS_ALLOWED):
                    return True

            for item in alternatives.items:
                if isinstance(item.term, list):  # Sub-expression is a list of Items
                    if self._check_items_for_whitespace_separators(item.term):
                        return True
        return False

    def iir_type_for_rule(self, rule_name: str) -> iir.Type:
        try:
            return self.iir_types[rule_name]
        except KeyError:
            pass
        name = self.class_name_for_rule_node(rule_name)
        typ = iir.Type.make(cname=name)
        self.context.python_type_registry.register_type(pyreg.TypeInfo(typ=typ, module=self.py_module, name=name))
        self.iir_types[rule_name] = typ
        return typ

    def iir_type_for_model_type(self, model_type: ModelType) -> iir.Type:
        if isinstance(model_type, str):
            return self.iir_type_for_rule(model_type)
        return typemodel.lookup_type(model_type)

    def py_annotation_for_model_types(self, *, model_types: Iterable[ModelType], in_module: bool = False) -> str:
        iir_types = [self.iir_type_for_model_type(model_type) for model_type in model_types]
        assert len(iir_types) > 0
        py_types = sorted(pycompiler.iir_type_to_py_annotation(typ, self.context) for typ in iir_types)
        if in_module:
            py_types = sorted(f'"{typ.removeprefix(".".join(self.py_module.import_path) + ".")}"' for typ in py_types)
        if len(py_types) > 1:
            return f"typing.Union[{', '.join(py_types)}]"
        return py_types[0]

    def node_kind_member_name(self, rule_name: str) -> str:
        """Return the NodeKind enum member name for a rule (uppercased class name)."""
        return self.class_name_for_rule_node(rule_name).upper()

    @staticmethod
    def _emit_cross_backend_eq_hash(enum_klass: ast.ClassDef) -> None:
        """Append cross-backend __eq__ and __hash__ to an enum ClassDef.

        Assumes each member has a plain string attribute ``_fltk_canonical_name`` (not a
        property) set after class creation via ``_emit_canonical_name_assignments``.  That
        attribute is an immutable per-member value, so __hash__ reads it without rebuilding
        any string on every call.

        A bare ``_fltk_canonical_name: str`` annotation is emitted inside the class body so
        that pyright knows the attribute exists; it carries no default and does not affect
        runtime behaviour.  The actual value is assigned post-class by the caller.
        """
        # Bare annotation so pyright knows the attribute exists on instances.
        enum_klass.body.append(pygen.stmt("_fltk_canonical_name: str"))

        # __eq__: same-type fast path (identity/member-name), then canonical-name cross-type,
        # then NotImplemented for foreign operands (so Python invokes the reflected __eq__).
        eq_fn = pygen.function("__eq__", "self, other: object", "bool")
        eq_fn.body.extend(
            [
                pygen.stmt("if other is self: return True"),
                pygen.stmt("if type(other) is type(self): return self.name == other.name"),  # type: ignore[union-attr]
                pygen.stmt("cn = getattr(other, '_fltk_canonical_name', None)"),
                pygen.stmt("if cn is not None: return self._fltk_canonical_name == cn"),
                pygen.stmt("return NotImplemented"),
            ]
        )
        enum_klass.body.append(eq_fn)

        # __hash__: hash of the pre-computed canonical name (no string rebuild per call).
        hash_fn = pygen.function("__hash__", "self", "int")
        hash_fn.body.append(pygen.stmt("return hash(self._fltk_canonical_name)"))
        enum_klass.body.append(hash_fn)

    def _node_kind_enum(self) -> ast.ClassDef:
        """Emit the module-level NodeKind enum with cross-backend eq/hash."""
        node_kind = pygen.klass(name="NodeKind", bases=["enum.Enum"])
        for rule in self.grammar.rules:
            member = self.node_kind_member_name(rule.name)
            node_kind.body.append(pygen.stmt(f"{member} = enum.auto()"))

        self._emit_cross_backend_eq_hash(node_kind)

        return node_kind

    def _emit_node_kind_canonical_name_assignments(self) -> list[ast.stmt]:
        """Emit post-class statements that assign _fltk_canonical_name on each NodeKind member.

        Enum members are immutable singletons; assigning a plain string attribute after class
        creation avoids rebuilding the f-string on every __eq__/__hash__ call (efficiency-1).
        """
        stmts: list[ast.stmt] = []
        for rule in self.grammar.rules:
            member = self.node_kind_member_name(rule.name)
            canonical = f"NodeKind.{member}"
            stmts.append(pygen.stmt(f'NodeKind.{member}._fltk_canonical_name = "{canonical}"'))
        return stmts

    def _emit_label_canonical_name_assignments(self, class_name: str, labels: list[str]) -> list[ast.stmt]:
        """Emit post-class statements that assign _fltk_canonical_name on each Label member.

        Same rationale as _emit_node_kind_canonical_name_assignments: per-member plain string
        avoids per-call f-string rebuild in __eq__/__hash__ (efficiency-1).
        """
        stmts: list[ast.stmt] = []
        for label in labels:
            python_name = label.upper()
            canonical = f"{class_name}.Label.{python_name}"
            stmts.append(pygen.stmt(f'{class_name}.Label.{python_name}._fltk_canonical_name = "{canonical}"'))
        return stmts

    def gen_py_module(self) -> ast.Module:
        imports = [
            pyreg.Module(("dataclasses",)),
            pyreg.Module(("enum",)),
            pyreg.Module(("operator",)),
            pyreg.Module(("sys",)),
            pyreg.Module(("typing",)),
            pyreg.Module(("fltk", "fegen", "pyrt", "terminalsrc")),
        ]
        module = pygen.module(module.import_path for module in imports)
        # from __future__ import annotations makes all annotations lazy strings so that
        # fltk._native (guarded under TYPE_CHECKING below) is NOT needed at runtime.
        # Without this, 'span: terminalsrc.Span | fltk._native.Span' would evaluate
        # eagerly and fail with ImportError on any pure-Python install.
        module.body.insert(0, pygen.stmt("from __future__ import annotations"))
        # Both imports under TYPE_CHECKING: annotations are lazy (from __future__ above),
        # so these are only needed by pyright for type resolution, not at runtime.
        # This mirrors the protocol generator (gen_protocol_module) exactly, keeping
        # concrete CST modules importable in pure-Python environments.
        module.body.append(
            pygen.if_(
                pygen.expr("typing.TYPE_CHECKING"),
                [
                    # Backend-selector span module: pyright resolves fltk.fegen.pyrt.span.Span
                    # in child/terminal span type annotations.
                    pygen.stmt("import fltk.fegen.pyrt.span"),
                    # Rust extension: resolves fltk._native.Span in the span annotation union.
                    pygen.stmt("import fltk._native"),
                ],
                [],
            )
        )

        # Emit module-level NodeKind enum before the node classes.
        module.body.append(self._node_kind_enum())
        # Assign _fltk_canonical_name as a plain string attribute on each NodeKind member
        # after the class is fully constructed, so __hash__/__eq__ avoid per-call f-string
        # rebuilds (efficiency-1: members are immutable singletons, value is invariant).
        module.body.extend(self._emit_node_kind_canonical_name_assignments())

        # Module-level helper: lazily resolve fltk._native.Span so the generated module never
        # imports the native extension at load time (preserves pure-Python importability, §2.2).
        # sys is imported at the top of generated modules to support lazy native-Span resolution.
        module.body.extend(
            ast.parse(
                """\
def _get_native_span_type():
    m = sys.modules.get("fltk._native")
    return m.Span if m is not None else None
"""
            ).body
        )

        for rule, model in self.rule_models.items():
            module.body.extend(self.py_class_for_model(self.class_name_for_rule_node(rule), model, rule))

        return module

    def py_class_for_model(self, class_name: str, model: ItemsModel, rule_name: str = "") -> list[ast.stmt]:
        """Emit the dataclass for a rule node plus its post-class Label canonical-name assignments.

        Returns a list of statements: the ClassDef followed by one assignment statement per Label
        member that sets ``_fltk_canonical_name`` as a plain string attribute.  Plain attributes
        avoid per-call f-string rebuilds in __eq__/__hash__ (efficiency-1: members are immutable
        singletons, the canonical string is invariant).
        """
        klass = pygen.dataclass(class_name)

        labels = sorted(model.labels.keys())
        if labels:
            label_enum = pygen.klass(name="Label", bases=["enum.Enum"])
            for label in labels:
                label_enum.body.append(pygen.stmt(f"{label.upper()} = enum.auto()"))

            # Cross-backend equality contract (§2.2): canonical-name-keyed eq/hash.
            # _emit_cross_backend_eq_hash uses self._fltk_canonical_name, which is a plain string
            # attribute set post-class (not a property) — see _emit_label_canonical_name_assignments.
            self._emit_cross_backend_eq_hash(label_enum)

            klass.body.append(label_enum)
        if not model.types:
            msg = (
                f"Model class `{class_name}` "
                "would have no members; ensure there is at least one term included in the model."
            )
            raise RuntimeError(msg)
        child_annotation = self.py_annotation_for_model_types(model_types=model.types, in_module=True)
        # Mirror the Protocol generator's label_annotation pattern: when the node has labels, use
        # Optional[Label]; when label-free, use None (matching Protocol/Rust reference exactly).
        label_annotation = "typing.Optional[Label]" if labels else "None"
        # kind: instance attribute (dataclass field with default) for NodeKind discriminant (§2.4).
        # MUST NOT be ClassVar — pyright rejects ClassVar against the Protocol's instance-attr declaration.
        # Use node_kind_member_name for the member name to stay in sync with the Protocol generator.
        kind_member = self.node_kind_member_name(rule_name) if rule_name else class_name.upper()
        klass.body.extend(
            [
                pygen.stmt(f"kind: typing.Literal[NodeKind.{kind_member}] = NodeKind.{kind_member}"),
                pygen.stmt(
                    "span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span"
                    " = fltk.fegen.pyrt.terminalsrc.UnknownSpan"
                ),
                pygen.stmt(
                    f"children: list[tuple[{label_annotation}, {child_annotation}]]"
                    " = dataclasses.field(default_factory=list)"
                ),
            ]
        )

        child_annotation_by_labels = {
            label: self.py_annotation_for_model_types(model_types=types, in_module=True)
            for label, types in model.labels.items()
        }
        append_fn = pygen.function(
            "append",
            f"self, child: {child_annotation}, label: {label_annotation} = None",
            "None",
        )
        append_fn.body.append(pygen.stmt("self.children.append((label, child))"))
        klass.body.append(append_fn)

        extend_fn = pygen.function(
            "extend",
            f"self, children: typing.Iterable[{child_annotation}], label: {label_annotation} = None",
            "None",
        )
        extend_fn.body.append(pygen.stmt("self.children.extend((label, child) for child in children)"))
        klass.body.append(extend_fn)

        extend_children_fn = pygen.function(
            "extend_children",
            f"self, other: '{class_name}'",
            "None",
        )
        extend_children_fn.body.append(pygen.stmt("self.children.extend(other.children)"))
        klass.body.append(extend_children_fn)

        child_fn = pygen.function("child", "self", f"tuple[{label_annotation}, {child_annotation}]")
        child_fn.body.extend(
            [
                pygen.if_(
                    pygen.expr("(n := len(self.children)) != 1"),
                    [
                        pygen.stmt('msg = f"Expected one child but have {n}"'),
                        pygen.stmt("raise ValueError(msg)"),
                    ],
                    (),
                ),
                pygen.stmt("return self.children[0]"),
            ]
        )
        klass.body.append(child_fn)

        # Four named mutators: insert / remove_at / replace_at / clear (§2.4)
        # Validation helpers: emitted inline per-class (they reference class-specific Label enum
        # and allowed child types).  Lazy native-Span resolution via the module-level helper.
        klass.body.extend(self._emit_py_mutators(class_name, child_annotation, label_annotation, model))

        multi_type = len(model.types) > 1

        def concrete_body_for(method: str, label: str) -> list[ast.stmt]:
            lann = child_annotation_by_labels[label]
            upper = label.upper()
            if method == "append":
                return [pygen.stmt(f"self.children.append(({class_name}.Label.{upper}, child))")]
            if method == "extend":
                return [pygen.stmt(f"self.children.extend(({class_name}.Label.{upper}, child) for child in children)")]
            if method == "children":
                child_expr = f"typing.cast({lann}, child)" if multi_type else "child"
                return [
                    pygen.stmt(
                        f"return ({child_expr} for label, child in self.children"
                        f" if label == {class_name}.Label.{upper})"
                    )
                ]
            if method == "child":
                return [
                    pygen.stmt(f"children = list(self.children_{label}())"),
                    pygen.if_(
                        pygen.expr("(n := len(children)) != 1"),
                        [
                            pygen.stmt(f'msg = f"Expected one {label} child but have {{n}}"'),
                            pygen.stmt("raise ValueError(msg)"),
                        ],
                        (),
                    ),
                    pygen.stmt("return children[0]"),
                ]
            if method == "maybe":
                return [
                    pygen.stmt(f"children = list(self.children_{label}())"),
                    pygen.if_(
                        pygen.expr("(n := len(children)) > 1"),
                        [
                            pygen.stmt(f'msg = f"Expected at most one {label} child but have {{n}}"'),
                            pygen.stmt("raise ValueError(msg)"),
                        ],
                        (),
                    ),
                    pygen.stmt("return children[0] if children else None"),
                ]
            msg = f"Unknown method: {method!r}"
            raise ValueError(msg)

        klass.body.extend(
            self._emit_label_quintet(
                labels=labels,
                annotation_for=lambda label: child_annotation_by_labels[label],
                body_for=concrete_body_for,
            )
        )

        stmts: list[ast.stmt] = [klass]
        stmts.extend(self._emit_label_canonical_name_assignments(class_name, labels))
        return stmts

    def _emit_py_mutators(
        self,
        class_name: str,
        child_annotation: str,
        label_annotation: str,
        model: ItemsModel,
    ) -> list[ast.stmt]:
        """Emit insert / remove_at / replace_at / clear on the concrete dataclass.

        Validation is strict: child and label are type-checked before mutation, consistent with
        §2.2 (new API is strict from day one; grandfathered append/extend are unchanged).
        Lazy native-Span resolution via module-level _get_native_span_type() (§2.2 asymmetry).

        Returns a list of stmts: an optional class-variable assignment followed by FunctionDef
        nodes.  The class-variable (_MUTATOR_ALLOWED_CHILD_TYPES) is emitted only when the node
        has Span-typed children (the has_span_types path in _check_child_type_for_mutators).
        """
        fns: list[ast.stmt] = []

        # Collect allowed concrete child classes (rule references → class names; Span types).
        allowed_classes: list[str] = []
        for mt in model.types:
            if isinstance(mt, str):
                # rule reference → class name in this module
                allowed_classes.append(self.class_name_for_rule_node(mt))
            else:
                # Span type key → fltk.fegen.pyrt.terminalsrc.Span
                # (native Span also accepted, resolved lazily — see _validate_child helper)
                allowed_classes.append("fltk.fegen.pyrt.terminalsrc.Span")

        # Deduplicate and sort for deterministic output.
        # Sort is required because model.types is a set (hash order varies per PYTHONHASHSEED);
        # without sorting, each make gencode run can produce differently-ordered isinstance unions
        # and _MUTATOR_ALLOWED_CHILD_TYPES tuples with no semantic difference — pure churn.
        # The sorted-annotation precedent is py_annotation_for_model_types (gsm2tree.py:88).
        seen: set[str] = set()
        unique_classes: list[str] = []
        for c in sorted(allowed_classes):
            if c not in seen:
                seen.add(c)
                unique_classes.append(c)

        # Determine if there are Span types among the model types (need native Span check).
        has_span_types = any(not isinstance(mt, str) for mt in model.types)

        # When Span types are present, emit _MUTATOR_ALLOWED_CHILD_TYPES as a plain None assignment
        # (not an annotated field) so dataclasses does not treat it as a field.  It is lazily
        # initialised to the static-type tuple on first call to _check_child_type_for_mutators
        # and memoised there.  None initial value avoids forward-reference issues at class body
        # parse time (the static type names are not yet in scope when the class body executes).
        if has_span_types:
            fns.extend(ast.parse("_MUTATOR_ALLOWED_CHILD_TYPES = None\n").body)

        # Emit _check_child_type: validates that child is an allowed type.
        # When Span types are present, native Span must be checked lazily (§2.2 asymmetry).
        # Static checks use `isinstance(child, A | B)` (UP038 / Python 3.10+ union syntax).
        # Dynamic check uses a class-level tuple _MUTATOR_ALLOWED_CHILD_TYPES that starts with
        # the static types and is updated once (in-place, lock-free) when fltk._native is first
        # seen.  fltk._native never unloads once imported, so positive memoisation is safe.
        # The tuple is a ClassVar (not an instance field) but declared without a type annotation
        # in the dataclass body to avoid being treated as a dataclass field.
        check_child_fn = pygen.function("_check_child_type_for_mutators", f"self, child: {child_annotation}", "None")
        if has_span_types:
            # _MUTATOR_ALLOWED_CHILD_TYPES starts as None; lazily initialised to the static-type
            # tuple on first call, then memoised.  Native Span is appended once when fltk._native
            # is first seen (it never unloads, so positive memoisation is safe).
            static_allowed_tuple = "(" + ", ".join(unique_classes) + ",)"
            check_child_fn.body.extend(
                ast.parse(
                    f"""\
_allowed = {class_name}._MUTATOR_ALLOWED_CHILD_TYPES
if _allowed is None:
    _allowed = {static_allowed_tuple}
    {class_name}._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
_ns = _get_native_span_type()
if _ns is not None and _ns not in _allowed:
    {class_name}._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
    _allowed = {class_name}._MUTATOR_ALLOWED_CHILD_TYPES
if not isinstance(child, _allowed):
    msg = f"{class_name}: unsupported child type {{type(child).__name__}}"
    raise TypeError(msg)
"""
                ).body
            )
        elif len(unique_classes) == 1:
            # Single type: simple isinstance — no tuple needed
            check_child_fn.body.extend(
                ast.parse(
                    f"""\
if not isinstance(child, {unique_classes[0]}):
    msg = f"{class_name}: unsupported child type {{type(child).__name__}}"
    raise TypeError(msg)
"""
                ).body
            )
        else:
            # Multiple non-span types: use union syntax (UP038)
            union_expr = " | ".join(unique_classes)
            check_child_fn.body.extend(
                ast.parse(
                    f"""\
if not isinstance(child, {union_expr}):
    msg = f"{class_name}: unsupported child type {{type(child).__name__}}"
    raise TypeError(msg)
"""
                ).body
            )
        fns.append(check_child_fn)

        # Emit _check_label_type: validates that label is None or an instance of Label.
        if model.labels:
            # Node has labels: label must be None or Label enum.
            # Use the static class name (not type(self).__name__) to match Rust's pinned message text.
            # Assign it to a local _cn so the f-string line stays within the 120-char ruff limit for
            # nodes with long class names.
            check_label_fn = pygen.function(
                "_check_label_type_for_mutators", f"self, label: {label_annotation}, method: str", "None"
            )
            check_label_fn.body.extend(
                ast.parse(
                    f"""\
if label is not None and not isinstance(label, {class_name}.Label):
    _cn = "{class_name}"
    msg = f"{{_cn}}.{{method}}: label argument is not a {{_cn}}_Label; got {{type(label).__name__}}"
    raise TypeError(msg)
"""
                ).body
            )
            fns.append(check_label_fn)
        else:
            # Label-free node: any non-None label is an error
            check_label_fn = pygen.function(
                "_check_label_type_for_mutators", f"self, label: {label_annotation}, method: str", "None"
            )
            check_label_fn.body.extend(
                ast.parse(
                    f"""\
if label is not None:
    msg = f"{class_name}.{{method}}: no labels defined for this node; got {{type(label).__name__}} label"
    raise TypeError(msg)
"""
                ).body
            )
            fns.append(check_label_fn)

        # insert(index, child, label=None) — list.insert clamping semantics via explicit clamp.
        # Validation order: child → label → index, matching the Rust backend (§3).
        # Explicit clamping is required: CPython's list.insert raises OverflowError for indices
        # beyond ssize_t (e.g. 10**25), so we clamp after operator.index to match Rust's behaviour
        # for arbitrarily-large ints (§3, pinned by test_insert_clamp_large_positive).
        insert_fn = pygen.function(
            "insert",
            f"self, index: int, child: {child_annotation}, label: {label_annotation} = None",
            "None",
        )
        insert_fn.body.extend(
            ast.parse(
                """\
self._check_child_type_for_mutators(child)
self._check_label_type_for_mutators(label, "insert")
idx = operator.index(index)
n = len(self.children)
if idx < 0:
    idx = max(n + idx, 0)
else:
    idx = min(idx, n)
self.children.insert(idx, (label, child))
"""
            ).body
        )
        fns.append(insert_fn)

        def _emit_bounds_check_stmts(method_name: str) -> list[ast.stmt]:
            """Emit the shared normalize+bounds-check block for remove_at and replace_at.

            Produces: operator.index call, len read, negative-index normalisation,
            and IndexError raise on out-of-range.  Both callers diverge only in the
            statement that follows the check (pop vs assignment).
            """
            return ast.parse(
                f"""\
idx = operator.index(index)
n = len(self.children)
norm = idx + n if idx < 0 else idx
if norm < 0 or norm >= n:
    msg = f"{class_name}.{method_name}: index {{index}} out of range ({{n}} children)"
    raise IndexError(msg)
"""
            ).body

        # remove_at(index) -> tuple[label, child] — strict bounds check + parity message.
        if model.labels:
            remove_ret = f"tuple[{label_annotation}, {child_annotation}]"
        else:
            remove_ret = f"tuple[None, {child_annotation}]"
        remove_fn = pygen.function("remove_at", "self, index: int", remove_ret)
        remove_fn.body.extend(_emit_bounds_check_stmts("remove_at"))
        remove_fn.body.extend(ast.parse("return self.children.pop(norm)\n").body)
        fns.append(remove_fn)

        # replace_at(index, child, label=None) -> None — strict bounds check + parity message.
        # Validation order: child → label → index, matching the Rust backend (§3).
        replace_fn = pygen.function(
            "replace_at",
            f"self, index: int, child: {child_annotation}, label: {label_annotation} = None",
            "None",
        )
        replace_fn.body.extend(
            ast.parse(
                """\
self._check_child_type_for_mutators(child)
self._check_label_type_for_mutators(label, "replace_at")
"""
            ).body
        )
        replace_fn.body.extend(_emit_bounds_check_stmts("replace_at"))
        replace_fn.body.extend(ast.parse("self.children[norm] = (label, child)\n").body)
        fns.append(replace_fn)

        # clear() -> None
        clear_fn = pygen.function("clear", "self", "None")
        clear_fn.body.append(pygen.stmt("self.children.clear()"))
        fns.append(clear_fn)

        return fns

    def model_for_item(self, item: gsm.Item, inline_stack: list[str]) -> ItemsModel:
        if isinstance(item.term, gsm.Identifier):
            if item.term.value not in self.grammar.identifiers:
                msg = f"Identifier {item.term.value} not in grammar"
                raise ValueError(msg)
            return ItemsModel(types={item.term.value})
        if isinstance(item.term, gsm.Literal | gsm.Regex):
            return ItemsModel(types={self.Span.key})
        if isinstance(item.term, Sequence):
            return self.model_for_alternatives(item.term, inline_stack)
        msg = f"Term type {item.term}"
        raise NotImplementedError(msg)

    def model_for_items(self, items: gsm.Items, inline_stack: list[str]) -> ItemsModel:
        model = ItemsModel()
        for item in items.items:
            if item.disposition == gsm.Disposition.SUPPRESS:
                assert not isinstance(item.term, Sequence)
                continue
            if item.disposition == gsm.Disposition.INLINE:
                assert isinstance(item.term, gsm.Identifier)
                inline_rule = self.grammar.identifiers[item.term.value]
                assert isinstance(inline_rule, gsm.Rule)
                inline_model = self.model_for_rule(inline_rule, inline_stack)
                model.incorporate(inline_model)
            else:
                item_model = self.model_for_item(item, inline_stack)
                model.incorporate(item_model)
                if item.label:
                    assert not isinstance(item.term, Sequence)
                    model.labels[item.label] |= item_model.types
        return model

    def model_for_alternatives(self, alternatives: Iterable[gsm.Items], inline_stack: list[str]) -> ItemsModel:
        model = ItemsModel()
        for alternative in alternatives:
            model.incorporate(self.model_for_items(alternative, inline_stack))
        return model

    def protocol_node_name(self, rule_name: str) -> str:
        """Rule name → Protocol class name.

        Protocol classes live in a separate *_cst_protocol.py module from concrete CST classes, so bare
        names (e.g. 'Rule') do not collide with the concrete 'Rule' dataclass — they are always
        module-qualified in annotations (e.g. cstp.Rule).  No suffix is needed.
        """
        return self.class_name_for_rule_node(rule_name)

    def protocol_annotation_for_model_types(self, *, model_types: Iterable[ModelType], class_name: str = "") -> str:
        """Return a Python annotation string for model_types.

        Uses the bare Protocol class name (same as the concrete class name) for rule references, and
        library-type annotations for everything else.

        Quoting asymmetry is intentional: rule references are quoted strings (e.g. '"Rule"') because they are
        forward references to Protocol classes defined later in the same module, while library types (e.g.
        fltk.fegen.pyrt.terminalsrc.Span) are unquoted module paths resolved at import time.  The generated module
        carries `from __future__ import annotations`, which makes all annotations lazy, so the explicit quoting on
        rule refs is redundant there — but kept for clarity and consistency with how fltk_cst.py emits forward refs.
        """
        parts = []
        for model_type in model_types:
            if isinstance(model_type, str):
                # rule reference -> Protocol node name (quoted forward ref)
                parts.append(f'"{self.protocol_node_name(model_type)}"')
            else:
                # library type (Span, etc.) -> use the existing iir-to-annotation path (unquoted)
                iir_type = typemodel.lookup_type(model_type)
                parts.append(pycompiler.iir_type_to_py_annotation(iir_type, self.context))
        # Sort for deterministic output; quoted rule names (starting with '"') sort before unquoted library
        # paths alphabetically by ASCII order, but both categories are distinct and sort is stable within each.
        parts = sorted(set(parts))  # deduplicate then sort for deterministic Union member order
        if not parts:
            rule_ctx = f" for rule {class_name!r}" if class_name else ""
            msg = f"Rule node{rule_ctx} has no child types in its model; cannot generate annotation"
            raise ValueError(msg)
        if len(parts) > 1:
            return f"typing.Union[{', '.join(parts)}]"
        return parts[0]

    @staticmethod
    def _emit_protocol_label_member_class() -> list[ast.stmt]:
        """Emit the module-level _ProtocolLabelMember sentinel class for protocol Label members.

        Instances carry _fltk_canonical_name and a cross-backend __eq__/__hash__ matching the
        shape in _emit_cross_backend_eq_hash.  The static type of each Label member stays object
        (ClassVar[object]) — this sentinel is not an enum.Enum, preserving the structural-mismatch
        contract (test_boundary_probe_documents_label_mismatch).
        """
        stmts = ast.parse(
            """\
class _ProtocolLabelMember:
    _fltk_canonical_name: str
    def __init__(self, canonical_name: str) -> None:
        self._fltk_canonical_name = canonical_name
    def __eq__(self, other: object) -> bool:
        if other is self: return True
        if type(other) is type(self): return self._fltk_canonical_name == other._fltk_canonical_name
        cn = getattr(other, '_fltk_canonical_name', None)
        if cn is not None: return self._fltk_canonical_name == cn
        return NotImplemented
    def __hash__(self) -> int:
        return hash(self._fltk_canonical_name)
    def __repr__(self) -> str:
        return f'_ProtocolLabelMember({self._fltk_canonical_name!r})'
"""
        ).body
        return stmts  # type: ignore[return-value]

    def gen_protocol_module(self) -> ast.Module:
        """Generate a *_cst_protocol.py module with Protocol classes describing the CST module surface."""
        module = ast.parse("")
        assert isinstance(module, ast.Module)
        module.body.append(pygen.stmt("from __future__ import annotations"))
        module.body.append(pygen.import_(("enum",)))
        module.body.append(pygen.import_(("typing",)))
        module.body.append(pygen.import_(("fltk", "fegen", "pyrt", "terminalsrc")))
        # Both imports under TYPE_CHECKING so neither pulls in a concrete backend at protocol
        # module load time (no-runtime-cost constraint; test_protocol_import_does_not_import_concrete_backends).
        # fltk.fegen.pyrt.span is the backend-selector (may activate fltk._native at import time).
        # fltk._native is the Rust extension.
        # With `from __future__ import annotations` all annotations are lazy strings — these imports
        # are needed only by pyright, not at runtime.
        module.body.append(
            pygen.if_(
                pygen.expr("typing.TYPE_CHECKING"),
                [
                    pygen.stmt("import fltk.fegen.pyrt.span"),
                    pygen.stmt("import fltk._native"),
                ],
                [],
            )
        )

        # Emit a protocol-local runtime NodeKind enum (identical members + canonical strings +
        # cross-backend bridge to the concrete module's NodeKind).  This replaces the former
        # TYPE_CHECKING-guarded import so the protocol module owns its own runtime values and
        # does NOT eagerly import a concrete backend at module load (Constraint: no-runtime-cost).
        module.body.append(self._node_kind_enum())
        module.body.extend(self._emit_node_kind_canonical_name_assignments())

        # Emit the _ProtocolLabelMember sentinel class used to give Label members runtime values.
        module.body.extend(self._emit_protocol_label_member_class())

        for rule in self.rule_models:
            model = self.rule_models[rule]
            class_name = self.protocol_node_name(rule)
            stmts = self._protocol_class_for_model_with_assignments(class_name, model, rule)
            module.body.extend(stmts)

        module.body.append(self._protocol_span_class())
        module.body.append(self._cst_module_protocol())

        # Emit __all__ to prevent _ProtocolLabelMember from leaking as a public symbol
        # via wildcard imports / IDE autocomplete.  Build the list from the same sources
        # used to emit the actual classes so it cannot drift from the generated output.
        # Sorted for deterministic output across regenerations.
        public_names = sorted(
            {self.protocol_node_name(rule) for rule in self.rule_models} | {"NodeKind", "Span", "CstModule"}
        )
        # Insert after the last import / TYPE_CHECKING block so __all__ appears near the top of
        # the module.  Derive the position structurally rather than hardcoding a count so it
        # stays correct if the preamble ever changes.
        last_import_idx = max(
            (
                i
                for i, stmt in enumerate(module.body)
                if isinstance(stmt, ast.ImportFrom | ast.Import)
                or (
                    isinstance(stmt, ast.If)
                    and isinstance(stmt.test, ast.Attribute)
                    and isinstance(stmt.test.value, ast.Name)
                    and stmt.test.value.id == "typing"
                    and stmt.test.attr == "TYPE_CHECKING"
                )
            ),
            default=-1,
        )
        all_stmt = ast.Assign(
            targets=[ast.Name(id="__all__", ctx=ast.Store())],
            value=ast.List(
                elts=[ast.Constant(value=name) for name in public_names],
                ctx=ast.Load(),
            ),
            lineno=0,
            col_offset=0,
        )
        module.body.insert(last_import_idx + 1, all_stmt)

        return module

    def _protocol_class_for_model_with_assignments(
        self, class_name: str, model: ItemsModel, rule_name: str
    ) -> list[ast.stmt]:
        """Generate a Protocol class plus post-class Label member sentinel assignments.

        Returns a list: [ClassDef, assignment-stmts...].
        """
        klass = self._protocol_class_for_model(class_name, model, rule_name)
        stmts: list[ast.stmt] = [klass]
        # Emit post-class sentinel assignments for each Label member.
        labels = sorted(model.labels.keys())
        for label in labels:
            python_name = label.upper()
            canonical = f"{class_name}.Label.{python_name}"
            stmts.append(pygen.stmt(f'{class_name}.Label.{python_name} = _ProtocolLabelMember("{canonical}")'))
        return stmts

    def _emit_label_quintet(
        self,
        *,
        labels: list[str],
        annotation_for: Callable[[str], str],
        body_for: Callable[[Literal["append", "extend", "children", "child", "maybe"], str], list[ast.stmt]],
    ) -> list[ast.FunctionDef]:
        """Emit the per-label quintet of accessor methods shared by both generators.

        Returns a flat list of FunctionDefs (append_<l>, extend_<l>, children_<l>, child_<l>,
        maybe_<l>) for each label, in order.  Callers append into their own class body.

        Parameters
        ----------
        labels:
            Sorted list of label names (empty → returns []).
        annotation_for:
            Maps label name → child type annotation string for that label.
        body_for:
            Maps (method_name, label) → list of body statements.
            method_name is one of "append", "extend", "children", "child", "maybe".
            Protocol callers return [pygen.stmt("...")] for every call.
        """
        fns: list[ast.FunctionDef] = []
        for label in labels:
            lann = annotation_for(label)

            fn = pygen.function(f"append_{label}", f"self, child: {lann}", "None")
            fn.body = body_for("append", label)
            fns.append(fn)

            fn = pygen.function(f"extend_{label}", f"self, children: typing.Iterable[{lann}]", "None")
            fn.body = body_for("extend", label)
            fns.append(fn)

            fn = pygen.function(f"children_{label}", "self", f"typing.Iterator[{lann}]")
            fn.body = body_for("children", label)
            fns.append(fn)

            fn = pygen.function(f"child_{label}", "self", lann)
            fn.body = body_for("child", label)
            fns.append(fn)

            fn = pygen.function(f"maybe_{label}", "self", f"typing.Optional[{lann}]")
            fn.body = body_for("maybe", label)
            fns.append(fn)

        return fns

    def _protocol_class_for_model(self, class_name: str, model: ItemsModel, rule_name: str) -> ast.ClassDef:
        """Generate a Protocol class for a single CST node.

        rule_name is required to emit the correct kind discriminant.
        """
        klass = pygen.klass(name=class_name, bases=["typing.Protocol"])

        labels = sorted(model.labels.keys())

        # Nested Label class (if this node has labels)
        if labels:
            label_class = pygen.klass(name="Label")
            for label in labels:
                # Use ClassVar[object] rather than ClassVar[Label] to avoid the
                # self-referential annotation that pyright flags as reportUndefinedVariable
                # inside the nested class body.  The only guarantee we need is attribute
                # presence (so label == self.cst.Items.Label.NO_WS typechecks); the exact
                # type of the constant is immaterial for Protocol-level checking.
                # Value is set post-class by _protocol_class_for_model_with_assignments.
                label_class.body.append(pygen.stmt(f"{label.upper()}: typing.ClassVar[object]"))
            klass.body.append(label_class)

        # kind discriminant: emit Literal[NodeKind.X] with runtime default value.
        # The protocol-local NodeKind is now a real runtime enum, so the default is readable as
        # cst.<Node>.kind on the class object, enabling native .kind narrowing (probe D4).
        if rule_name and self.py_module.import_path:
            member = self.node_kind_member_name(rule_name)
            klass.body.append(pygen.stmt(f"kind: typing.Literal[NodeKind.{member}] = NodeKind.{member}"))
        else:
            klass.body.append(pygen.stmt("kind: object"))

        klass.body.append(pygen.stmt("span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span"))

        child_annotation = self.protocol_annotation_for_model_types(model_types=model.types, class_name=class_name)

        if labels:
            klass.body.append(pygen.stmt(f"children: list[tuple[typing.Optional[Label], {child_annotation}]]"))
        else:
            klass.body.append(pygen.stmt(f"children: list[tuple[None, {child_annotation}]]"))

        label_annotation = "typing.Optional[Label]" if labels else "None"

        append_fn = pygen.function(
            "append", f"self, child: {child_annotation}, label: {label_annotation} = None", "None"
        )
        append_fn.body.append(pygen.stmt("..."))
        klass.body.append(append_fn)

        extend_fn = pygen.function(
            "extend", f"self, children: typing.Iterable[{child_annotation}], label: {label_annotation} = None", "None"
        )
        extend_fn.body.append(pygen.stmt("..."))
        klass.body.append(extend_fn)

        extend_children_fn = pygen.function("extend_children", f"self, other: '{class_name}'", "None")
        extend_children_fn.body.append(pygen.stmt("..."))
        klass.body.append(extend_children_fn)

        if labels:
            child_ret = f"tuple[typing.Optional[Label], {child_annotation}]"
        else:
            child_ret = f"tuple[None, {child_annotation}]"
        child_fn = pygen.function("child", "self", child_ret)
        child_fn.body.append(pygen.stmt("..."))
        klass.body.append(child_fn)

        # Four named mutator stubs (§2.4, matching concrete class order)
        insert_fn = pygen.function(
            "insert",
            f"self, index: int, child: {child_annotation}, label: {label_annotation} = None",
            "None",
        )
        insert_fn.body.append(pygen.stmt("..."))
        klass.body.append(insert_fn)

        remove_fn = pygen.function("remove_at", "self, index: int", child_ret)
        remove_fn.body.append(pygen.stmt("..."))
        klass.body.append(remove_fn)

        replace_fn = pygen.function(
            "replace_at",
            f"self, index: int, child: {child_annotation}, label: {label_annotation} = None",
            "None",
        )
        replace_fn.body.append(pygen.stmt("..."))
        klass.body.append(replace_fn)

        clear_fn = pygen.function("clear", "self", "None")
        clear_fn.body.append(pygen.stmt("..."))
        klass.body.append(clear_fn)

        def protocol_annotation_for(label: str) -> str:
            return self.protocol_annotation_for_model_types(
                model_types=model.labels[label], class_name=f"{class_name}.{label}"
            )

        klass.body.extend(
            self._emit_label_quintet(
                labels=labels,
                annotation_for=protocol_annotation_for,
                body_for=lambda _method, _label: [pygen.stmt("...")],
            )
        )

        return klass

    def _protocol_span_class(self) -> ast.ClassDef:
        """Generate a Protocol class for Span so consumers can write `case cst.Span.kind:`.

        The Span protocol class exposes `kind` with a runtime Literal[SpanKind.SPAN] default,
        allowing Shape 2 (`case cst.Span.kind:`) to narrow a child-union arm to Span.
        """
        klass = pygen.klass(name="Span", bases=["typing.Protocol"])
        klass.body.append(
            pygen.stmt(
                "kind: typing.Literal[fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN]"
                " = fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN"
            )
        )
        return klass

    def _cst_module_protocol(self) -> ast.ClassDef:
        """Generate the CstModule Protocol describing the module-level surface."""
        klass = pygen.klass(name="CstModule", bases=["typing.Protocol"])
        for rule in self.rule_models:
            node_name = self.protocol_node_name(rule)
            class_name = self.class_name_for_rule_node(rule)
            # @property returning type[<NodeName>] — covariant, satisfies concrete module's class attribute
            prop_fn = pygen.function(class_name, "self", f"type[{node_name}]")
            # Add @property decorator
            prop_fn.decorator_list = [pygen.expr("property")]
            prop_fn.body.append(pygen.stmt("..."))
            klass.body.append(prop_fn)
        # Note: no Span property. Span is a common-lib type (fltk.fegen.pyrt.terminalsrc.Span /
        # fltk._native.Span); neither backend's generated CST module exports a module-level Span.
        # Promising it here would certify an attribute that raises AttributeError at runtime on
        # every backend. Consumers obtain Span from fltk.fegen.pyrt.span or fltk._native directly.
        return klass

    def model_for_rule(self, rule: gsm.Rule, inline_stack: list[str]) -> ItemsModel:
        if rule.name in inline_stack:
            msg = f"Recursive cycle of inlined rules: {[*inline_stack, rule.name]}"
            raise ValueError(msg)
        inline_stack.append(rule.name)
        try:
            return self.rule_models[rule.name]
        except KeyError:
            pass
        model = self.model_for_alternatives(rule.alternatives, inline_stack)

        if self.rule_has_whitespace_separators(rule):
            if rule.is_trivia_rule:
                model.incorporate(ItemsModel(types={self.Span.key}))
            else:
                model.incorporate(ItemsModel(types={"_trivia"}))

        self.rule_models[rule.name] = model
        return self.rule_models[rule.name]
