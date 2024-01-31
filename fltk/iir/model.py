from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    Final,
    Generic,
    Iterable,
    Mapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from fltk.iir.py import reg as pyreg
from fltk.iir.typemodel import TYPE, ParamType, Type
from fltk.iir.typemodel import Argument as TypeArgument

_T = TypeVar("_T")

# "Built-in" types
#

Void: Final = Type.make(cname="Void")
pyreg.register_type(pyreg.TypeInfo(typ=Void, module=pyreg.Builtins, name="None"))

Auto: Final = Type.make(cname="Auto")


@dataclass
class PrimitiveType(Type):
    pass


UInt64: Final = PrimitiveType.make(cname="uint64")
pyreg.register_type(pyreg.TypeInfo(typ=UInt64, module=pyreg.Builtins, name="int"))

IndexInt: Final = PrimitiveType.make(cname="IndexInt")
pyreg.register_type(pyreg.TypeInfo(typ=IndexInt, module=pyreg.Builtins, name="int"))

SignedIndexInt: Final = PrimitiveType.make(cname="SignedIndexInt")
pyreg.register_type(pyreg.TypeInfo(typ=SignedIndexInt, module=pyreg.Builtins, name="int"))

Bool: Final = PrimitiveType.make(cname="bool")
pyreg.register_type(pyreg.TypeInfo(typ=Bool, module=pyreg.Builtins, name="bool"))

String: Final = Type.make(cname="string")
pyreg.register_type(pyreg.TypeInfo(typ=String, module=pyreg.Builtins, name="str"))


Maybe: Final = Type.make(cname="Maybe", params={"value_type": TYPE})
pyreg.register_type(pyreg.TypeInfo(typ=Maybe, module=pyreg.Module(("typing",)), name="Optional"))

GenericImmutableSequence: Final = Type.make(cname="ImmutableSequence", params={"value_type": TYPE})
pyreg.register_type(
    pyreg.TypeInfo(
        typ=GenericImmutableSequence,
        module=pyreg.Module(["typing"]),
        name="Sequence",
        concrete_name="list",
    )
)
GenericMutableSequence: Final = Type.make(cname="MutableSequence", params={"value_type": TYPE})

GenericImmutableHashmap: Final = Type.make(cname="ImmutableHashmap", params={"key_type": TYPE, "value_type": TYPE})
GenericMutableHashmap: Final = Type.make(cname="MutableHashmap", params={"key_type": TYPE, "value_type": TYPE})
pyreg.register_type(
    pyreg.TypeInfo(
        typ=GenericMutableHashmap,
        module=pyreg.Module(("collections", "abc")),
        name="MutableMapping",
        concrete_name="dict",
    )
)

#
# Expression/Statement base classes
#


class Expr:
    @property
    def fld(self) -> "FieldLookupProxy":
        return FieldLookupProxy(bind_to=self, mutable=False)

    @property
    def mut_fld(self) -> "FieldLookupProxy":
        return FieldLookupProxy(bind_to=self, mutable=True)

    @property
    def method(self) -> "MethodLookupProxy":
        return MethodLookupProxy(bind_to=self)


@dataclass
class Statement:
    parent_block: Optional["Block"]


#
# Scopes and blocks
#

Nameable = Any  # placeholder until I constrain this more


class Scope:
    def __init__(self, parent: Optional["Scope"] = None) -> None:
        self.parent = parent
        self.identifiers: dict[str, Nameable] = {}

    def define(self, name: str, entity: Nameable) -> None:
        if name in self.identifiers:
            msg = f"Attempt to redefine identifier {name}\n\nfrom\n{self.identifiers[name]}\n\nto\n{entity}"
            raise ValueError(msg)
        self.identifiers[name] = entity

    def lookup(self, name: str, *, recursive: bool = True) -> Optional[Nameable]:
        try:
            return self.identifiers[name]
        except KeyError:
            pass
        if recursive and self.parent is not None:
            return self.parent.lookup(name)
        return None

    def lookup_as(self, name: str, typ: type[_T], *, recursive: bool = True) -> _T:
        result = self.lookup(name=name, recursive=recursive)
        if result is None or not isinstance(result, typ):
            msg = f"Expected {typ} but got {result}"
            raise ValueError(msg)
        return result


@dataclass
class Block(Statement):
    inner_scope: Optional[Scope]
    body: MutableSequence[Statement]

    def get_leaf_scope(self) -> Scope:
        """Retrieve the innermost scope that applies to this block.

        If this block does not have its own inner scope, this will be a scope belonging to an ancestor block.

        Preconditions:
            A scope must apply to this block directly or in the ancestor chain.

        Raises:
            ValueError: If there is no applicable scope.

        Returns: The innermost applicable scope.
        """
        if self.inner_scope is not None:
            return self.inner_scope
        if self.parent_block is not None:
            return self.parent_block.get_leaf_scope()
        msg = "No scope associated with block."
        raise ValueError(msg)

    def var(
        self,
        *,
        name: str,
        typ: Type,
        ref_type: "RefType",
        mutable: bool = False,
        init: Optional[Expr] = None,
    ) -> "Var":
        result = Var(name=name, typ=typ, ref_type=ref_type, mutable=mutable)
        self.get_leaf_scope().define(name, result)
        self.body.append(VarDef(var=result, parent_block=self, init=init))
        return result

    def assign(self, target: Expr, expr: Expr) -> "AssignStatement":
        result = AssignStatement(parent_block=self, target=target, expr=expr)
        self.body.append(result)
        return result

    def expr_stmt(self, expr: Expr) -> "ExprStatement":
        result = ExprStatement(parent_block=self, expr=expr)
        self.body.append(result)
        return result

    def if_(self, condition: Expr, *, let: Optional["Var"] = None, orelse: bool = False) -> "If":
        result = If(
            parent_block=self,
            condition=condition,
            block=Block(
                parent_block=self,
                body=[],
                inner_scope=Scope(parent=self.get_leaf_scope()),
            ),
            orelse=(
                Block(
                    parent_block=self,
                    body=[],
                    inner_scope=Scope(parent=self.get_leaf_scope()),
                )
                if orelse
                else None
            ),
        )
        if let:
            result.block.get_leaf_scope().define(let.name, let)
            result.condition = LetExpr(var=let, result=result.condition)
        self.body.append(result)
        return result

    def while_(self, condition: Expr, let: Optional["Var"] = None) -> "WhileLoop":
        result = WhileLoop(
            parent_block=self,
            condition=condition,
            block=Block(
                parent_block=self,
                body=[],
                inner_scope=Scope(parent=self.get_leaf_scope()),
            ),
        )
        if let:
            result.block.get_leaf_scope().define(let.name, let)
            result.condition = LetExpr(var=let, result=result.condition)
        self.body.append(result)
        return result

    def return_(self, expr: Expr) -> "Return":
        self.body.append(ret := Return(expr=expr, parent_block=self))
        return ret


_ModuleSubclass = TypeVar("_ModuleSubclass", bound="Module")


@dataclass
class Module:
    name: str
    scope: Scope
    block: Block

    @classmethod
    def make(cls: type[_ModuleSubclass], name: str) -> _ModuleSubclass:
        scope = Scope()
        block = Block(parent_block=None, inner_scope=scope, body=[])
        return cls(name=name, scope=scope, block=block)

    def class_def(self, klass: "ClassType") -> "ClassDef":
        result = ClassDef(parent_block=self.block, klass=klass)
        if klass.cname is None:
            msg = f"Module-level class definitions cannot be anonymous: {klass}"
            raise ValueError(msg)
        self.scope.define(klass.cname, klass)
        self.block.body.append(result)
        return result


#
# Variables and variable load/store/move
#


class RefType(Enum):
    VALUE = 0
    BORROW = 1
    MUT_BORROW = 2
    OWNING = 3
    SHARED = 4
    SELF = 5


@dataclass
class ValRef(Expr):
    def load(self) -> "Load":
        return Load(self, mutable=False)

    def load_mut(self) -> "Load":
        if hasattr(self, "mutable"):
            assert self.mutable  # noqa: S101
        return Load(self, mutable=True)

    def store(self) -> "Store":
        return Store(self)

    def move(self) -> "Move":
        return Move(self)


@dataclass
class Var(ValRef):
    name: str
    typ: Type
    ref_type: RefType
    mutable: bool


@dataclass
class VarByName(Var):
    pass


@dataclass
class VarDef(Statement):
    var: Var
    init: Optional[Expr] = None


@dataclass
class VarDefExpr(Expr):
    var: Var
    init: Expr


@dataclass
class Load(Expr):
    ref: ValRef
    mutable: bool


@dataclass
class Move(Expr):
    ref: ValRef


@dataclass
class Store(Expr):
    ref: ValRef


@dataclass
class Construct(Expr):
    typ: Type
    args: Sequence[Expr]
    kwargs: Mapping[str, Expr]

    @classmethod
    def make(cls: type["Construct"], typ: Type, *args: Expr, **kwargs: Expr) -> "Construct":
        return cls(typ=typ, args=args, kwargs=kwargs)


@dataclass
class IsEmpty(Expr):
    expr: Expr


class SelfExpr(Expr):
    pass


@dataclass
class Success(Expr):
    result_type: Type
    expr: Expr


@dataclass
class Failure(Expr):
    result_type: Type


@dataclass
class Constant(Expr, Generic[_T]):
    typ: Type
    val: _T


TrueBool: Final = Constant(typ=Bool, val=True)
FalseBool: Final = Constant(typ=Bool, val=False)


@dataclass(frozen=True, eq=True, slots=True)
class LiteralString(Expr):
    value: str


@dataclass(frozen=True, eq=True, slots=True)
class LiteralInt(Expr):
    typ: Type
    value: int


@dataclass(frozen=True, eq=True, slots=True)
class LiteralSequence(Expr):
    values: Sequence[Expr]


@dataclass(frozen=True, eq=True, slots=True)
class LiteralMapping(Expr):
    key_values: Sequence[tuple[Expr, Expr]]


#
# Class member access
#


@dataclass
class MemberAccess:
    member_name: str
    bound_to: Expr


@dataclass
class MethodAccess(MemberAccess):
    def call(self, *args: Expr, **kwargs: Expr) -> "MethodCall":
        return MethodCall(self, args=args, kwargs=kwargs)

    def bind(self) -> "BoundMethod":
        return BoundMethod(self)


@dataclass
class MethodCall(Expr):
    bound_method: MethodAccess
    args: Sequence[Expr]
    kwargs: Mapping[str, Expr]


@dataclass
class BoundMethod(Expr):
    bound_method: MethodAccess


@dataclass
class Field(Var):
    in_class: "ClassType"
    init: Optional[Expr]


@dataclass
class FieldAccess(MemberAccess, ValRef):
    pass


#
# Functions/Methods
#


@dataclass
class Param(Var):
    pass


@dataclass
class Function:
    name: Optional[str]
    params: Sequence[Param]
    return_type: Type
    block: Block
    doc: Optional[str]

    def __post_init__(self) -> None:
        assert self.block.inner_scope is not None  # noqa: S101
        for param in self.params:
            self.block.inner_scope.define(param.name, param)

    def get_param(self, name: str) -> Param:
        assert self.block.inner_scope is not None  # noqa: S101
        result = self.block.inner_scope.lookup(name)
        assert isinstance(result, Param)  # noqa: S101
        assert result in self.params  # noqa: S101
        return result


@dataclass
class Method(Function):
    in_class: "ClassType"
    mutable_self: bool
    self_expr: SelfExpr


#
# Classes
#

_ClassTypeSubclass = TypeVar("_ClassTypeSubclass", bound="ClassType")


@dataclass(kw_only=True)
class ClassType(Type):
    defined_in: Module
    block: Block
    doc: Optional[str]
    base_classes: Sequence[Type]
    constructor: Optional["Constructor"]

    @classmethod
    def make(  # type: ignore[override]
        cls: type[_ClassTypeSubclass],
        *,
        cname: Optional[str] = None,
        params: Optional[Mapping[str, ParamType]] = None,
        instantiates: Optional["Type"] = None,
        arguments: Optional[Mapping[str, TypeArgument]] = None,
        defined_in: Module,
        doc: Optional[str] = None,
        outer_scope: Optional[Scope] = None,
    ) -> _ClassTypeSubclass:
        scope = Scope(parent=outer_scope)
        block = Block(parent_block=None, body=[], inner_scope=scope)
        return cls(
            cname=cname,
            instantiates=instantiates,
            arguments=(arguments if arguments is not None else {}),
            params=(params if params is not None else {}),
            block=block,
            base_classes=(),
            constructor=None,
            defined_in=defined_in,
            doc=doc,
        )

    def get_attr(self, name: str) -> Union[Field, Method]:
        result = self.block.get_leaf_scope().lookup(name, recursive=False)
        if not isinstance(result, (Field, Method)):
            msg = f"Class contains invalid member type {name} = {result}"
            raise ValueError(msg)
        return result

    def get_field(self, name: str) -> Field:
        result = self.block.get_leaf_scope().lookup(name, recursive=False)
        if not isinstance(result, Field):
            msg = f"Expected field at {name} but got {result}"
            raise ValueError(msg)
        return result

    def get_method(self, name: str) -> Method:
        result = self.block.get_leaf_scope().lookup(name, recursive=False)
        if not isinstance(result, Method):
            msg = f"Expected method at {name} but got {result}"
            raise ValueError(msg)
        return result

    def get_fields(self) -> Iterable[Field]:
        for attr in self.block.get_leaf_scope().identifiers.values():
            if isinstance(attr, Field):
                yield attr
        return

    def get_methods(self) -> Iterable[Method]:
        for attr in self.block.get_leaf_scope().identifiers.values():
            if isinstance(attr, Method):
                yield attr
        return

    def def_field(
        self,
        name: str,
        *,
        typ: Type,
        init: Optional[Expr],
        ref_type: RefType = RefType.VALUE,
        mutable: bool = False,
    ) -> Field:
        fld = Field(
            name=name,
            in_class=self,
            typ=typ,
            init=init,
            ref_type=ref_type,
            mutable=mutable,
        )
        self.block.get_leaf_scope().define(name, fld)
        return fld

    def def_constructor(
        self,
        *,
        params: Iterable[Param],
        doc: Optional[str] = None,
        init_list: Iterable[Tuple[Field, "InitListExpr"]] = (),
    ) -> "Constructor":
        if self.constructor is not None:
            msg = f"Constructor already defined for class {self.cname}"
            raise AssertionError(msg)
        self.constructor = Constructor(
            in_class=self,
            doc=doc,
            params=list(params),
            init_list=list(init_list),
            mutable_self=True,
            block=Block(
                parent_block=self.block,
                inner_scope=Scope(parent=self.block.inner_scope),
                body=[],
            ),
        )
        return self.constructor

    def def_method(
        self,
        name: str,
        *,
        params: Iterable[Param],
        return_type: Type,
        doc: Optional[str] = None,
        mutable_self: bool = False,
        using_self: Optional[SelfExpr] = None,
    ) -> Method:
        method = Method(
            name=name,
            in_class=self,
            params=list(params),
            return_type=return_type,
            doc=doc,
            mutable_self=mutable_self,
            block=Block(
                parent_block=self.block,
                inner_scope=Scope(parent=self.block.inner_scope),
                body=[],
            ),
            self_expr=using_self or SelfExpr(),
        )
        self.block.get_leaf_scope().define(name, method)
        return method


@dataclass
class ClassDef(Statement):
    klass: ClassType


class FieldLookupProxy:
    def __init__(self, *, bind_to: Expr, mutable: bool) -> None:
        self.bind_to = bind_to
        self.mutable = mutable

    def __getattr__(self, name: str) -> FieldAccess:
        return FieldAccess(
            member_name=name,
            bound_to=self.bind_to,
        )

    __getitem__ = __getattr__


class MethodLookupProxy:
    def __init__(self, bind_to: Expr) -> None:
        self.bind_to = bind_to

    def __getattr__(self, name: str) -> MethodAccess:
        return MethodAccess(name, self.bind_to)

    __getitem__ = __getattr__


class InitFromParamType:
    pass


INIT_FROM_PARAM: Final = InitFromParamType()

InitListExpr = Union[Expr, InitFromParamType]


class Constructor(Method):
    def __init__(self, *, init_list: Iterable[Tuple[Field, InitListExpr]], **kws: Any):
        super().__init__(name="", return_type=Void, self_expr=SelfExpr(), **kws)
        self.init_list = list(init_list)


@dataclass(kw_only=True)
class EnumType(Type):
    defined_in: Module
    doc: Optional[str]
    fields: MutableSequence[str]

    @classmethod
    def make(  # type: ignore[override]
        cls,
        *,
        cname: Optional[str] = None,
        defined_in: Module,
        doc: Optional[str] = None,
        fields: Iterable[str] = (),
    ) -> "EnumType":
        return cls(
            cname=cname,
            fields=list(fields),
            instantiates=None,
            arguments={},
            params={},
            defined_in=defined_in,
            doc=doc,
        )

    def add_field(self, field: str, *, ignore_if_exists: bool = False) -> None:
        if field not in self.fields:
            self.fields.append(field)
        elif not ignore_if_exists:
            msg = f"Field {field} already exists in enum {self}"
            raise ValueError(msg)


#
# Statements
#


@dataclass
class If(Statement):
    condition: Expr
    block: Block
    orelse: Optional[Union["If", Block]]


@dataclass
class WhileLoop(Statement):
    condition: Expr
    block: Block


@dataclass
class AssignStatement(Statement):
    target: Expr
    expr: Expr


@dataclass
class Return(Statement):
    expr: Expr


@dataclass
class ExprStatement(Statement):
    expr: Expr


#
# Operators
#


@dataclass
class BinOp(Expr):
    lhs: Expr
    rhs: Expr
    op: str


@dataclass
class GreaterThan(BinOp):
    op: str = ">"


@dataclass
class Subtract(BinOp):
    op: str = "-"


@dataclass
class Subscript(Expr):
    target: Expr
    index: Expr


#
# Other expressions
#


@dataclass(kw_only=True)
class LetExpr(Expr):
    result: Expr
    var: Var
