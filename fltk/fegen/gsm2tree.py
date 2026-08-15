from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Callable, Iterable, MutableMapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from fltk import pygen
from fltk.fegen import cst_ergonomics, gsm, naming
from fltk.fegen.pyrt.label_protocol import label_canonical_name
from fltk.iir import model as iir
from fltk.iir import typemodel
from fltk.iir.py import compiler as pycompiler
from fltk.iir.py import reg as pyreg

if TYPE_CHECKING:
    from fltk.iir.context import CompilerContext

ModelType = str | typemodel.TypeKey

INLINE_NOT_EXPANDED_MSG = (
    "INLINE disposition must be expanded with gsm.expand_inline_dispositions() before code generation"
)

ErgonomicMember = Literal["bare", "text", "rule_text", "variant"]

# Fully qualified because the generated modules import the module, not the name.
LABEL_PROTOCOL_ANNOTATION = "fltk.fegen.pyrt.label_protocol.LabelProtocol"

PROTOCOL_MODULE_ALIAS = "_cstp"


def _child_types_widen(model_types: Iterable[ModelType]) -> bool:
    """True when the protocol annotation for these child types differs from the concrete one.

    Rule references are the only model types whose two renderings differ (``"Rule"`` concretely,
    ``_cstp.Rule`` on the protocol surface); library types such as Span are spelled identically on
    both.
    """
    return any(isinstance(model_type, str) for model_type in model_types)


def _widened_entry_stmts(expr: str, *, name: str, widened: bool) -> tuple[list[str], str]:
    """Bind ``expr`` to a deliberately untyped local when it is protocol-typed, else pass it through.

    Returns (statements to emit first, expression naming the value).  Mutator inputs are annotated
    with the protocol surface while the ``children`` list keeps its concrete element type, so a
    value on its way into the list needs a static escape hatch.  ``typing.Any`` is used rather than
    a ``typing.cast`` to the concrete element type because a cast is equally unchecked — pyright
    validates nothing about a cast's operand — while its type argument is a string literal that no
    formatter can wrap, and the concrete element type of a node with many child classes does not
    fit on a line.  The local is consumed by the very next statement.  Runtime type safety rests on
    the mutators' isinstance guards, not on these annotations.
    """
    if not widened:
        return [], expr
    return [f"{name}: typing.Any = {expr}"], name


@dataclass(frozen=True)
class _ChildTypes:
    """One node's child/label annotations in both flavors: concrete for reads, protocol for inputs.

    ``concrete_child`` may carry quoted forward references (the in-module annotation form).
    ``widened`` says whether an entry built from the inputs can differ from the children element
    type; it is derived from the node's model, not by comparing the rendered annotations.
    """

    concrete_child: str
    input_child: str
    concrete_label: str
    input_label: str
    widened: bool

    def entry(self, label_expr: str, child_expr: str) -> tuple[list[str], str]:
        """Statements preparing one children entry, and the expression naming it."""
        return _widened_entry_stmts(f"({label_expr}, {child_expr})", name="entry", widened=self.widened)

    def entries(self, expr: str, *, widened: bool | None = None) -> tuple[list[str], str]:
        """Statements preparing a sequence of children entries, and the expression naming it."""
        return _widened_entry_stmts(expr, name="entries", widened=self.widened if widened is None else widened)


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
            self.rule_models[rule.name] = self.model_for_rule(rule)

        # Computed once: all emission surfaces share the same plan, so a member exists on
        # all of them or on none.
        self.rule_plans: dict[str, cst_ergonomics.RulePlan] = {
            rule.name: cst_ergonomics.plan_rule(rule, self.rule_models[rule.name]) for rule in self.grammar.rules
        }

    def plan_for_rule(self, rule_name: str) -> cst_ergonomics.RulePlan | None:
        """The ergonomic member plan for a rule, or None for a model with no backing rule."""
        return self.rule_plans.get(rule_name)

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
        """Emit the module-level NodeKind enum with cross-backend eq/hash.

        Emitted into the protocol module only; the concrete module imports that one so both
        surfaces' ``kind`` Literals are the same type.
        """
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
            canonical = label_canonical_name(class_name, python_name)
            stmts.append(pygen.stmt(f'{class_name}.Label.{python_name}._fltk_canonical_name = "{canonical}"'))
        return stmts

    def gen_py_module(self, protocol_module_name: str) -> ast.Module:
        """Emit the concrete CST dataclass module.

        ``protocol_module_name`` is the importable name of this grammar's protocol module; the
        emitted source contains ``from <protocol_module_name> import NodeKind`` plus, under
        TYPE_CHECKING, ``import <protocol_module_name> as _cstp`` for the mutator input
        annotations.  Never derived here — the caller knows the pair it is writing to disk or has
        registered.
        """
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
        # span_protocol (guarded under TYPE_CHECKING below) is NOT needed at runtime.
        # Without this, 'span: fltk.fegen.pyrt.span_protocol.SpanProtocol' would evaluate
        # eagerly and require the import on any pure-Python install.
        module.body.insert(0, pygen.stmt("from __future__ import annotations"))
        # span_protocol under TYPE_CHECKING: annotations are lazy (from __future__ above),
        # so it is only needed by pyright for type resolution, not at runtime.
        module.body.append(
            pygen.if_(
                pygen.expr("typing.TYPE_CHECKING"),
                [
                    # Backend-agnostic span protocol: pyright resolves
                    # fltk.fegen.pyrt.span_protocol.SpanProtocol in the span field and span-typed
                    # child annotations. Names neither the span selector nor fltk._native.
                    pygen.stmt("import fltk.fegen.pyrt.label_protocol"),
                    pygen.stmt("import fltk.fegen.pyrt.span_protocol"),
                    # Mutator inputs are annotated against the protocol node types; annotations are
                    # lazy strings here, so the alias is needed by pyright only.
                    pygen.stmt(f"import {protocol_module_name} as {PROTOCOL_MODULE_ALIAS}"),
                ],
                [],
            )
        )

        # NodeKind is imported from the protocol module so the per-node `kind` Literal names the
        # same enum on both surfaces (protocol-attribute invariance requires it).  Makes the pair
        # mandatory: importing this module without its protocol module is a ModuleNotFoundError.
        # Placed among the imports (before TYPE_CHECKING) to avoid E402.
        module.body.insert(
            len([stmt for stmt in module.body if isinstance(stmt, ast.Import | ast.ImportFrom)]),
            pygen.stmt(f"from {protocol_module_name} import NodeKind"),
        )

        # Module-level helper: lazily resolve fltk._native.Span so the generated module never
        # imports the native extension at load time (preserves pure-Python importability).
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

            # Cross-backend equality contract: canonical-name-keyed eq/hash.
            self._emit_cross_backend_eq_hash(label_enum)

            klass.body.append(label_enum)
        if not model.types:
            msg = (
                f"Model class `{class_name}` "
                "would have no members; ensure there is at least one term included in the model."
            )
            raise RuntimeError(msg)
        child_annotation = self.py_annotation_for_model_types(model_types=model.types, in_module=True)
        # Must match the Protocol generator's label_annotation pattern.
        label_annotation = "typing.Optional[Label]" if labels else "None"
        types = _ChildTypes(
            concrete_child=child_annotation,
            input_child=self.protocol_annotation_for_model_types(
                model_types=model.types, class_name=class_name, module_alias=PROTOCOL_MODULE_ALIAS
            ),
            concrete_label=f"typing.Optional[{class_name}.Label]" if labels else "None",
            input_label=f"typing.Optional[{LABEL_PROTOCOL_ANNOTATION}]" if labels else "None",
            # The label side widens whenever the node has labels (concrete enum vs LabelProtocol);
            # a label-free node's slot is None on both surfaces.
            widened=_child_types_widen(model.types) or bool(labels),
        )
        # MUST NOT be ClassVar — pyright rejects ClassVar against the Protocol's instance-attr declaration.
        # Uses node_kind_member_name to stay in sync with the Protocol generator.
        kind_member = self.node_kind_member_name(rule_name) if rule_name else class_name.upper()
        klass.body.extend(
            [
                pygen.stmt(f"kind: typing.Literal[NodeKind.{kind_member}] = NodeKind.{kind_member}"),
                pygen.stmt(
                    "span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan"
                ),
                pygen.stmt(
                    f"children: list[tuple[{label_annotation}, {child_annotation}]]"
                    " = dataclasses.field(default_factory=list)"
                ),
            ]
        )

        child_annotation_by_labels = {
            label: self.py_annotation_for_model_types(model_types=label_types, in_module=True)
            for label, label_types in model.labels.items()
        }
        input_child_annotation_by_labels = {
            label: self.protocol_annotation_for_model_types(
                model_types=label_types, class_name=f"{class_name}.{label}", module_alias=PROTOCOL_MODULE_ALIAS
            )
            for label, label_types in model.labels.items()
        }
        # TODO(cst-mutator-append-parity): append/extend/extend_children and the per-label mutators
        # store their argument without an isinstance check, while insert/replace_at and the Rust
        # backend's append reject a foreign-backend child.  The same split applies to labels: a
        # protocol label sentinel is stored by append/extend and rejected by insert/replace_at.
        append_fn = pygen.function(
            "append",
            f"self, child: {types.input_child}, label: {types.input_label} = None",
            "None",
        )
        prep, entry = types.entry("label", "child")
        append_fn.body.extend(pygen.stmt(stmt) for stmt in prep)
        append_fn.body.append(pygen.stmt(f"self.children.append({entry})"))
        klass.body.append(append_fn)

        extend_fn = pygen.function(
            "extend",
            f"self, children: typing.Iterable[{types.input_child}], label: {types.input_label} = None",
            "None",
        )
        prep, entries = types.entries("((label, child) for child in children)")
        extend_fn.body.extend(pygen.stmt(stmt) for stmt in prep)
        extend_fn.body.append(pygen.stmt(f"self.children.extend({entries})"))
        klass.body.append(extend_fn)

        extend_children_fn = pygen.function(
            "extend_children",
            # Assumes the protocol module defines the node class under the same name.
            f"self, other: {PROTOCOL_MODULE_ALIAS}.{class_name}",
            "None",
        )
        # Always widened: `other` is the protocol node type even when nothing else here widens.
        prep, entries = types.entries("other.children", widened=True)
        extend_children_fn.body.extend(pygen.stmt(stmt) for stmt in prep)
        extend_children_fn.body.append(pygen.stmt(f"self.children.extend({entries})"))
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

        klass.body.extend(self._emit_py_mutators(class_name, types, model))

        multi_type = len(model.types) > 1

        def label_widened(label: str) -> bool:
            """True when append_<label>/extend_<label> accept more than the list element type.

            Only the child side can widen here: these methods supply the label themselves, as the
            concrete enum member.
            """
            return _child_types_widen(model.labels[label])

        def concrete_body_for(method: str, label: str) -> list[ast.stmt]:
            lann = child_annotation_by_labels[label]
            upper = label.upper()
            if method == "append":
                prep, entry = _widened_entry_stmts(
                    f"({class_name}.Label.{upper}, child)", name="entry", widened=label_widened(label)
                )
                return [pygen.stmt(stmt) for stmt in (*prep, f"self.children.append({entry})")]
            if method == "extend":
                prep, entries = _widened_entry_stmts(
                    f"(({class_name}.Label.{upper}, child) for child in children)",
                    name="entries",
                    widened=label_widened(label),
                )
                return [pygen.stmt(stmt) for stmt in (*prep, f"self.children.extend({entries})")]
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
                input_annotation_for=lambda label: input_child_annotation_by_labels[label],
            )
        )

        plan = self.plan_for_rule(rule_name)
        if plan is not None:
            klass.body.extend(
                self._emit_label_ergonomics(
                    plan=plan,
                    annotation_for=lambda label: child_annotation_by_labels[label],
                    body_for=lambda member, label: self._concrete_ergonomic_body(
                        plan=plan, class_name=class_name, member=member, label=label
                    ),
                    variant_return="Label",
                    multiple_container="list",
                )
            )

        stmts: list[ast.stmt] = [klass]
        stmts.extend(self._emit_label_canonical_name_assignments(class_name, labels))
        return stmts

    @staticmethod
    def _concrete_ergonomic_body(
        *,
        plan: cst_ergonomics.RulePlan,
        class_name: str,
        member: ErgonomicMember,
        label: str,
    ) -> list[ast.stmt]:
        """Method bodies for the ergonomic accessors on a concrete dataclass.

        The per-label accessors delegate to the corresponding quintet member, so the
        count-checking behaviour and the ValueError messages are identical by construction.

        ``<label>_text`` raises ``TypeError`` when a non-Span child is stored under a span
        label — only reachable through the untyped mutators.
        """
        if member == "bare":
            arity = plan.bare_accessors[label]
            if arity == cst_ergonomics.ArityClass.REQUIRED_SINGLE:
                return [pygen.stmt(f"return self.child_{label}()")]
            if arity == cst_ergonomics.ArityClass.OPTIONAL_SINGLE:
                return [pygen.stmt(f"return self.maybe_{label}()")]
            return [pygen.stmt(f"return list(self.children_{label}())")]
        if member == "text":
            arity = plan.text_accessors[label]
            wrong_type_msg = f"{class_name}.{label}_text: child labelled '{label}' is not a Span"
            if arity == cst_ergonomics.ArityClass.REQUIRED_SINGLE:
                return ast.parse(
                    f"""\
child = self.child_{label}()
try:
    return child.text_or_raise()
except AttributeError:
    msg = "{wrong_type_msg}"
    raise TypeError(msg) from None
"""
                ).body
            return ast.parse(
                f"""\
child = self.maybe_{label}()
if child is None:
    return None
try:
    return child.text_or_raise()
except AttributeError:
    msg = "{wrong_type_msg}"
    raise TypeError(msg) from None
"""
            ).body
        if member == "rule_text":
            return [pygen.stmt("return self.span.text_or_raise()")]
        if member == "variant":
            return ast.parse(
                f"""\
for label, _child in self.children:
    if label is not None:
        return label
msg = "{class_name}.variant: node has no labeled child"
raise ValueError(msg)
"""
            ).body
        msg = f"Unknown ergonomic member: {member!r}"
        raise ValueError(msg)

    def _emit_py_mutators(
        self,
        class_name: str,
        types: _ChildTypes,
        model: ItemsModel,
    ) -> list[ast.stmt]:
        """Emit insert / remove_at / replace_at / clear on the concrete dataclass.

        Validation is strict: child and label are type-checked before mutation, consistent with
        New API is strict from day one; grandfathered append/extend are unchanged.
        Lazy native-Span resolution via module-level _get_native_span_type().

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
        # When Span types are present, native Span must be checked lazily.
        # Static checks use `isinstance(child, A | B)` (UP038 / Python 3.10+ union syntax).
        # Dynamic check uses a class-level tuple _MUTATOR_ALLOWED_CHILD_TYPES that starts with
        # the static types and is updated once (in-place, lock-free) when fltk._native is first
        # seen.  fltk._native never unloads once imported, so positive memoisation is safe.
        # The tuple is a ClassVar (not an instance field) but declared without a type annotation
        # in the dataclass body to avoid being treated as a dataclass field.
        check_child_fn = pygen.function("_check_child_type_for_mutators", f"self, child: {types.input_child}", "None")
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
                "_check_label_type_for_mutators", f"self, label: {types.input_label}, method: str", "None"
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
                "_check_label_type_for_mutators", f"self, label: {types.input_label}, method: str", "None"
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
        # Validation order: child → label → index, matching the Rust backend.
        # Explicit clamping is required: CPython's list.insert raises OverflowError for indices
        # beyond ssize_t (e.g. 10**25), so we clamp after operator.index to match Rust's behaviour
        # for arbitrarily-large ints (pinned by test_insert_clamp_large_positive).
        insert_fn = pygen.function(
            "insert",
            f"self, index: int, child: {types.input_child}, label: {types.input_label} = None",
            "None",
        )
        prep, entry = types.entry("label", "child")
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
"""
            ).body
        )
        insert_fn.body.extend(ast.parse("\n".join([*prep, f"self.children.insert(idx, {entry})", ""])).body)
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
        # Returns stay concrete: a concrete child/label satisfies the protocol's element type
        # covariantly, so downstream reads keep their concrete types.
        if model.labels:
            remove_ret = f"tuple[typing.Optional[Label], {types.concrete_child}]"
        else:
            remove_ret = f"tuple[None, {types.concrete_child}]"
        remove_fn = pygen.function("remove_at", "self, index: int", remove_ret)
        remove_fn.body.extend(_emit_bounds_check_stmts("remove_at"))
        remove_fn.body.extend(ast.parse("return self.children.pop(norm)\n").body)
        fns.append(remove_fn)

        # replace_at(index, child, label=None) -> None — strict bounds check + parity message.
        # Validation order: child → label → index, matching the Rust backend.
        replace_fn = pygen.function(
            "replace_at",
            f"self, index: int, child: {types.input_child}, label: {types.input_label} = None",
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
        replace_prep, replace_entry = types.entry("label", "child")
        replace_fn.body.extend(ast.parse("\n".join([*replace_prep, f"self.children[norm] = {replace_entry}", ""])).body)
        fns.append(replace_fn)

        # clear() -> None
        clear_fn = pygen.function("clear", "self", "None")
        clear_fn.body.append(pygen.stmt("self.children.clear()"))
        fns.append(clear_fn)

        return fns

    def model_for_item(self, item: gsm.Item) -> ItemsModel:
        if isinstance(item.term, gsm.Identifier):
            if item.term.value not in self.grammar.identifiers:
                msg = f"Identifier {item.term.value} not in grammar"
                raise ValueError(msg)
            return ItemsModel(types={item.term.value})
        if isinstance(item.term, gsm.Literal | gsm.Regex):
            return ItemsModel(types={self.Span.key})
        if isinstance(item.term, Sequence):
            return self.model_for_alternatives(item.term)
        msg = f"Term type {item.term}"
        raise NotImplementedError(msg)

    def model_for_items(self, items: gsm.Items) -> ItemsModel:
        model = ItemsModel()
        for item in items.items:
            if item.disposition == gsm.Disposition.INLINE:
                raise ValueError(INLINE_NOT_EXPANDED_MSG)
            if item.disposition == gsm.Disposition.SUPPRESS:
                assert not isinstance(item.term, Sequence)
                continue
            item_model = self.model_for_item(item)
            model.incorporate(item_model)
            if item.label:
                assert not isinstance(item.term, Sequence)
                model.labels[item.label] |= item_model.types
        return model

    def model_for_alternatives(self, alternatives: Iterable[gsm.Items]) -> ItemsModel:
        model = ItemsModel()
        for alternative in alternatives:
            model.incorporate(self.model_for_items(alternative))
        return model

    def protocol_node_name(self, rule_name: str) -> str:
        """Rule name → Protocol class name.

        Protocol classes live in a separate *_cst_protocol.py module from concrete CST classes, so bare
        names (e.g. 'Rule') do not collide with the concrete 'Rule' dataclass — they are always
        module-qualified in annotations (e.g. cstp.Rule).  No suffix is needed.
        """
        return self.class_name_for_rule_node(rule_name)

    def protocol_label_namespace_name(self, rule_name: str) -> str:
        """Rule name → the protocol module's module-level label namespace class name.

        Label constants live in a module-level ``<Class>Label`` namespace rather than nested in
        the node protocol: pyright types an ``enum.auto()`` member as its value type when checking
        a class object against a namespace protocol, so a nested ``Label`` requirement could never
        be satisfied by a concrete backend's ``Label`` enum.
        """
        return f"{self.protocol_node_name(rule_name)}Label"

    def protocol_annotation_for_model_types(
        self, *, model_types: Iterable[ModelType], class_name: str = "", module_alias: str = ""
    ) -> str:
        """Return a Python annotation string for model_types.

        Uses the bare Protocol class name (same as the concrete class name) for rule references, and
        library-type annotations for everything else.

        ``module_alias``, when given, qualifies rule references with it (e.g. ``_cstp.Rule``) and
        leaves them unquoted: the annotation is being emitted into a module other than the protocol
        module, where the names are reachable only through that alias and are not forward references.

        Quoting asymmetry is intentional: rule references are quoted strings (e.g. '"Rule"') because they are
        forward references to Protocol classes defined later in the same module, while library types (e.g.
        fltk.fegen.pyrt.terminalsrc.Span) are unquoted module paths resolved at import time.  The generated module
        carries `from __future__ import annotations`, which makes all annotations lazy, so the explicit quoting on
        rule refs is redundant there — but kept for clarity and consistency with how fltk_cst.py emits forward refs.
        """
        parts = []
        for model_type in model_types:
            if isinstance(model_type, str):
                node_name = self.protocol_node_name(model_type)
                if module_alias:
                    # Reached through the alias from another module: not a forward reference.
                    parts.append(f"{module_alias}.{node_name}")
                else:
                    # rule reference -> Protocol node name (quoted forward ref)
                    parts.append(f'"{node_name}"')
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
        shape in _emit_cross_backend_eq_hash, so a sentinel compares equal to either backend's
        label with the same canonical name.  Each member of a ``<Class>Label`` namespace is one
        of these instances, statically typed as LabelProtocol; the sentinel class itself is not
        an enum.Enum and is private to the protocol module.
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

    def gen_protocol_module(self, *, emit_kind_literal: bool = True) -> ast.Module:
        """Generate a *_cst_protocol.py module with Protocol classes describing the CST module surface.

        emit_kind_literal controls the per-node ``kind`` discriminant. Default True
        emits the precise ``kind: typing.Literal[NodeKind.X]`` form, which is always valid protocol
        output (the module-level NodeKind enum is emitted unconditionally). Passing False emits the
        degraded ``kind: object`` form. py_module plays no role in protocol output.
        """
        module = ast.parse("")
        assert isinstance(module, ast.Module)
        module.body.append(pygen.stmt("from __future__ import annotations"))
        module.body.append(pygen.import_(("enum",)))
        module.body.append(pygen.import_(("typing",)))
        module.body.append(pygen.import_(("fltk", "fegen", "pyrt", "terminalsrc")))
        # span_protocol under TYPE_CHECKING so it does not pull in a concrete backend at protocol
        # module load time (no-runtime-cost constraint; test_protocol_import_does_not_import_concrete_backends).
        # fltk.fegen.pyrt.span_protocol.SpanProtocol is the backend-agnostic span contract; it names
        # neither the span selector nor fltk._native.
        # With `from __future__ import annotations` all annotations are lazy strings — this import
        # is needed only by pyright, not at runtime.
        module.body.append(
            pygen.if_(
                pygen.expr("typing.TYPE_CHECKING"),
                [
                    pygen.stmt("import fltk.fegen.pyrt.label_protocol"),
                    pygen.stmt("import fltk.fegen.pyrt.span_protocol"),
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
            stmts = self._protocol_class_for_model_with_assignments(
                class_name, model, rule, emit_kind_literal=emit_kind_literal
            )
            module.body.extend(stmts)

        module.body.append(self._protocol_span_class())
        module.body.append(self._cst_module_protocol())

        # Emit __all__ to prevent _ProtocolLabelMember from leaking as a public symbol
        # via wildcard imports / IDE autocomplete.  Build the list from the same sources
        # used to emit the actual classes so it cannot drift from the generated output.
        # Sorted for deterministic output across regenerations.
        public_names = sorted(
            {self.protocol_node_name(rule) for rule in self.rule_models}
            | {self.protocol_label_namespace_name(rule) for rule, model in self.rule_models.items() if model.labels}
            | {"NodeKind", "Span", "CstModule"}
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

    def gen_protocol_module_text(self, *, emit_kind_literal: bool = True) -> str:
        """Return the protocol-module source text, with the file-level ruff suppression prefix.

        Single home for the protocol-text rendering formula shared by the Python ``generate
        --protocol`` path (genparser.py) and the Rust ``RustCstGenerator.generate_protocol``
        path (gsm2tree_rs.py), so the two render byte-identical bytes through one code path
        (the cross-path byte-identity test is the guardrail).

        File-level ruff suppressions:
        - N802: CstModule @property methods have PascalCase names matching module attributes
          (intentional).
        - E501 is NOT added: ``make fix`` reformats the generated file so no line exceeds the
          limit, and including E501 causes RUF100 (unused noqa) after ``make fix``.
        - F821 is NOT added: forward references to protocol classes resolve via ``from __future__
          import annotations`` and ruff does not raise F821 for them; including F821 causes
          RUF100 (unused noqa) after ``make fix``.
        """
        return "# ruff: noqa: N802\n" + ast.unparse(self.gen_protocol_module(emit_kind_literal=emit_kind_literal))

    def _protocol_class_for_model_with_assignments(
        self, class_name: str, model: ItemsModel, rule_name: str, *, emit_kind_literal: bool
    ) -> list[ast.stmt]:
        """Generate a Protocol class plus, for a labeled rule, its label namespace class.

        Returns a list: [ClassDef] or [ClassDef, label-namespace ClassDef].  The namespace is a
        plain class whose members are LabelProtocol-typed sentinels carrying the unchanged
        ``<Class>.Label.<MEMBER>`` canonical names.
        """
        klass = self._protocol_class_for_model(class_name, model, rule_name, emit_kind_literal=emit_kind_literal)
        stmts: list[ast.stmt] = [klass]
        labels = sorted(model.labels.keys())
        if labels:
            namespace = pygen.klass(name=f"{class_name}Label")
            namespace.body.append(
                pygen.stmt(
                    f'"""Sentinels equal to either backend\'s {class_name} labels, for identifying one.\n\n'
                    "    They are not a backend's own label objects, so insert() and replace_at() reject\n"
                    "    them on every backend; pass those a label read off the node being mutated (from\n"
                    '    children, remove_at() or variant()).\n    """'
                )
            )
            for label in labels:
                python_name = label.upper()
                canonical = label_canonical_name(class_name, python_name)
                namespace.body.append(
                    pygen.stmt(
                        f"{python_name}: typing.Final[{LABEL_PROTOCOL_ANNOTATION}]"
                        f' = _ProtocolLabelMember("{canonical}")'
                    )
                )
            stmts.append(namespace)
        return stmts

    def _emit_label_quintet(
        self,
        *,
        labels: list[str],
        annotation_for: Callable[[str], str],
        body_for: Callable[[Literal["append", "extend", "children", "child", "maybe"], str], list[ast.stmt]],
        input_annotation_for: Callable[[str], str],
    ) -> list[ast.FunctionDef]:
        """Emit the per-label quintet of accessor methods shared by both generators.

        Returns a flat list of FunctionDefs (append_<l>, extend_<l>, children_<l>, child_<l>,
        maybe_<l>) for each label, in order.  Callers append into their own class body.

        Parameters
        ----------
        labels:
            Sorted list of label names (empty → returns []).
        annotation_for:
            Maps label name → child type annotation string for that label, used for the three
            accessors' return types.
        body_for:
            Maps (method_name, label) → list of body statements.
            method_name is one of "append", "extend", "children", "child", "maybe".
            Protocol callers return [pygen.stmt("...")] for every call.
        input_annotation_for:
            Maps label name → the child type accepted by append_<l> / extend_<l>.  Stated by every
            caller, like ``variant_return`` on _emit_label_ergonomics: the concrete classes accept
            the protocol child types while returning their own, so a default here would silently
            give one surface the other's annotations.
        """
        fns: list[ast.FunctionDef] = []
        for label in labels:
            lann = annotation_for(label)
            iann = input_annotation_for(label)

            fn = pygen.function(f"append_{label}", f"self, child: {iann}", "None")
            fn.body = body_for("append", label)
            fns.append(fn)

            fn = pygen.function(f"extend_{label}", f"self, children: typing.Iterable[{iann}]", "None")
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

    def _emit_label_ergonomics(
        self,
        *,
        plan: cst_ergonomics.RulePlan,
        annotation_for: Callable[[str], str],
        body_for: Callable[[ErgonomicMember, str], list[ast.stmt]],
        variant_return: str,
        multiple_container: str,
    ) -> list[ast.FunctionDef]:
        """Emit the arity-aware ergonomic accessors.

        Returns a flat list of FunctionDefs: per label in sorted order the bare accessor
        ``<label>()`` and the span shortcut ``<label>_text()``, then the rule-level ``text()``
        and ``variant()``.  Which of those the plan contains is decided in cst_ergonomics, so
        all emission surfaces stay member-for-member identical.

        Parameters
        ----------
        plan:
            The rule's member plan.
        annotation_for:
            Maps label name → child type annotation string for that label.
        body_for:
            Maps (member kind, label) → list of body statements.  The label is the empty string
            for the rule-level members.  Protocol callers return [pygen.stmt("...")] throughout.
        variant_return:
            Return annotation for ``variant()``, stated by every caller because it is the one
            member whose type differs per surface: the concrete classes return their own nested
            ``Label`` enum, the protocol returns the backend-agnostic LabelProtocol.
        multiple_container:
            Container for a MULTIPLE-arity bare accessor's return type, stated by every caller for
            the same reason as ``variant_return``.  The concrete classes
            return a ``list``; the protocol demands only ``typing.Sequence``, because ``list`` is
            invariant and a backend returning a list of its own node classes could otherwise never
            satisfy a protocol promising a list of protocol nodes.
        """
        fns: list[ast.FunctionDef] = []

        for label in sorted(set(plan.bare_accessors) | set(plan.text_accessors)):
            bare_arity = plan.bare_accessors.get(label)
            if bare_arity is not None:
                lann = annotation_for(label)
                if bare_arity == cst_ergonomics.ArityClass.REQUIRED_SINGLE:
                    ret = lann
                elif bare_arity == cst_ergonomics.ArityClass.OPTIONAL_SINGLE:
                    ret = f"typing.Optional[{lann}]"
                else:
                    ret = f"{multiple_container}[{lann}]"
                fn = pygen.function(label, "self", ret)
                fn.body = body_for("bare", label)
                fns.append(fn)

            text_arity = plan.text_accessors.get(label)
            if text_arity is not None:
                ret = "str" if text_arity == cst_ergonomics.ArityClass.REQUIRED_SINGLE else "typing.Optional[str]"
                fn = pygen.function(f"{label}_text", "self", ret)
                fn.body = body_for("text", label)
                fns.append(fn)

        if plan.rule_text:
            fn = pygen.function("text", "self", "str")
            fn.body = body_for("rule_text", "")
            fns.append(fn)

        if plan.variant:
            fn = pygen.function("variant", "self", variant_return)
            fn.body = body_for("variant", "")
            fns.append(fn)

        return fns

    def _protocol_class_for_model(
        self, class_name: str, model: ItemsModel, rule_name: str, *, emit_kind_literal: bool
    ) -> ast.ClassDef:
        """Generate a Protocol class for a single CST node.

        rule_name is required to emit the correct kind discriminant.
        emit_kind_literal selects the discriminant form (see gen_protocol_module).
        """
        klass = pygen.klass(name=class_name, bases=["typing.Protocol"])

        labels = sorted(model.labels.keys())

        # Runtime default enables cst.<Node>.kind narrowing.
        # py_module plays no role in protocol output.
        if rule_name and emit_kind_literal:
            member = self.node_kind_member_name(rule_name)
            klass.body.append(pygen.stmt(f"kind: typing.Literal[NodeKind.{member}] = NodeKind.{member}"))
        else:
            klass.body.append(pygen.stmt("kind: object"))

        klass.body.append(pygen.stmt("span: fltk.fegen.pyrt.span_protocol.SpanProtocol"))

        child_annotation = self.protocol_annotation_for_model_types(model_types=model.types, class_name=class_name)

        label_annotation = f"typing.Optional[{LABEL_PROTOCOL_ANNOTATION}]" if labels else "None"
        child_element = f"tuple[{label_annotation}, {child_annotation}]"

        # children is a read-only property returning a Sequence: a plain protocol attribute is
        # invariant and would reject every backend's concrete list element type, while a
        # read-only property accepts them covariantly.  Mutation goes through the mutators.
        children_fn = pygen.function("children", "self", f"typing.Sequence[{child_element}]")
        children_fn.decorator_list = [pygen.expr("property")]
        children_fn.body.append(pygen.stmt("..."))
        klass.body.append(children_fn)

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

        child_ret = child_element
        child_fn = pygen.function("child", "self", child_ret)
        child_fn.body.append(pygen.stmt("..."))
        klass.body.append(child_fn)

        # Order must match the concrete class.
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
                input_annotation_for=protocol_annotation_for,
            )
        )

        plan = self.plan_for_rule(rule_name)
        if plan is not None:
            klass.body.extend(
                self._emit_label_ergonomics(
                    plan=plan,
                    annotation_for=protocol_annotation_for,
                    body_for=lambda _member, _label: [pygen.stmt("...")],
                    variant_return=LABEL_PROTOCOL_ANNOTATION,
                    multiple_container="typing.Sequence",
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

    def model_for_rule(self, rule: gsm.Rule) -> ItemsModel:
        try:
            return self.rule_models[rule.name]
        except KeyError:
            pass
        model = self.model_for_alternatives(rule.alternatives)

        if self.rule_has_whitespace_separators(rule):
            if rule.is_trivia_rule:
                model.incorporate(ItemsModel(types={self.Span.key}))
            else:
                model.incorporate(ItemsModel(types={"_trivia"}))

        self.rule_models[rule.name] = model
        return self.rule_models[rule.name]
