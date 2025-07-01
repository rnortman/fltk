import ast
from typing import (
    TYPE_CHECKING,
    Iterable,
    Iterator,
    Mapping,
    TypeVar,
    cast,
)

from fltk import pygen
from fltk.iir import model as iir
from fltk.iir import typemodel

if TYPE_CHECKING:
    from fltk.iir.context import CompilerContext


def compile(mod: iir.Module, context: "CompilerContext") -> ast.Module:  # noqa: A001
    result = ast.parse("")
    for stmt in mod.block.body:
        if isinstance(stmt, iir.ClassDef):
            result.body.append(compile_class(stmt.klass, context))
        if isinstance(stmt, iir.Function):
            result.body.append(compile_function(stmt, context))
        msg = f"Module-level statement {stmt}"
        raise NotImplementedError(msg)
    return result


def iir_type_to_py_constructor(typ: iir.Type, context: "CompilerContext") -> str:
    if isinstance(typ, iir.PrimitiveType):
        return ""
    if typ.instantiates is iir.Maybe:
        return iir_type_to_py_constructor(typ.get_arg_as_type("value_type"), context)

    registry = context.python_type_registry

    try:
        type_info = registry.lookup(typ)
    except KeyError:
        try:
            type_info = registry.lookup(typ.root_type())
        except KeyError:
            msg = f"Unknown type: {typ}"
            raise AssertionError(msg) from None
    name = type_info.import_name(concrete=True)
    return name


def iir_type_to_py_annotation(typ: iir.Type, context: "CompilerContext") -> str:
    registry = context.python_type_registry

    if isinstance(typ, iir.PrimitiveType):
        return registry.lookup(typ).name
    if typ is iir.Void:
        return "None"
    try:
        type_info = registry.lookup(typ)
    except KeyError:
        try:
            type_info = registry.lookup(typ.root_type())
        except KeyError:
            msg = f"Unknown type: {typ}"
            raise AssertionError(msg) from None
    name = type_info.import_name()
    args = typ.get_args()
    if args:

        def _arg_annotation(arg: typemodel.Argument) -> str:
            if isinstance(arg, iir.Type):
                return iir_type_to_py_annotation(arg, context)
            return str(arg)

        return f"{name}[{','.join(_arg_annotation(arg) for arg in args.values())}]"
    return name


def compile_class(klass: iir.ClassType, context: "CompilerContext") -> ast.ClassDef:
    assert klass.cname is not None  # noqa: S101
    assert all(bc.cname for bc in klass.base_classes)  # noqa: S101
    result_ast = pygen.klass(name=klass.cname, bases=[cast(str, bc.cname) for bc in klass.base_classes])
    if klass.doc:
        result_ast.body.append(pygen.stmt(f'"""{klass.doc}"""'))

    T = TypeVar("T", iir.Field, iir.Method)

    def _ensure_in_class(attr: T) -> None:
        if attr.in_class is None:
            attr.in_class = klass
        elif attr.in_class is not klass:
            msg = f"Attribute {attr} is in a different class instance than {klass}"
            raise ValueError(msg)

    ctr = klass.constructor or iir.Constructor(
        in_class=klass,
        doc="Auto-generated constructor for field initialization",
        params=[],
        init_list=[],
        mutable_self=True,
        block=iir.Block(
            parent_block=klass.block,
            inner_scope=iir.Scope(parent=klass.block.inner_scope),
            body=[],
        ),
    )
    _ensure_in_class(ctr)
    method = iir.Method(
        in_class=klass,
        name="__init__",
        doc=ctr.doc,
        params=ctr.params,
        mutable_self=True,
        block=iir.Block(
            parent_block=klass.block,
            inner_scope=iir.Scope(parent=klass.block.inner_scope),
            body=[],
        ),
        self_expr=ctr.self_expr,
        return_type=iir.Void,
    )

    initialized_fields = set()
    for fld, init in ctr.init_list:
        initialized_fields.add(fld.name)
        if isinstance(init, iir.InitFromParamType):
            method.block.body.append(
                iir.AssignStatement(
                    parent_block=method.block,
                    target=ctr.self_expr.fld[fld.name].store(),
                    expr=ctr.get_param(fld.name).move(),
                )
            )
        else:
            method.block.body.append(
                iir.AssignStatement(
                    parent_block=method.block,
                    target=ctr.self_expr.fld[fld.name].store(),
                    expr=init,
                )
            )
    for field in klass.get_fields():
        _ensure_in_class(field)
        if field.name not in initialized_fields:
            method.block.body.append(
                iir.VarDef(
                    parent_block=method.block,
                    var=iir.Var(
                        name=f"self.{field.name}",
                        typ=field.typ,
                        ref_type=iir.RefType.VALUE,
                        mutable=True,
                    ),
                    init=field.init,
                )
            )

    for stmt in ctr.block.body:
        stmt.parent_block = method.block
        method.block.body.append(stmt)
    result_ast.body.append(compile_function(method, context))
    for stmt in ctr.block.body:
        stmt.parent_block = ctr.block

    for method in klass.get_methods():
        result_ast.body.append(compile_function(method, context))

    assert all(  # noqa: S101
        isinstance(attr, (iir.Field, iir.Method)) for attr in klass.block.get_leaf_scope().identifiers.values()
    )
    return result_ast


def compile_function(function: iir.Function, context: "CompilerContext") -> ast.FunctionDef:
    assert function.name is not None  # noqa: S101
    params = [f"{p.name}: {iir_type_to_py_annotation(p.typ, context)}" for p in function.params]
    if isinstance(function, iir.Method):
        params = ["self", *params]
    result_ast = pygen.function(
        name=function.name,
        args=", ".join(params),
        return_type=iir_type_to_py_annotation(function.return_type, context),
    )

    if function.doc:
        result_ast.body.append(pygen.stmt(f'"""{function.doc}"""'))
    elif not function.block.body:
        result_ast.body.append(pygen.stmt("pass"))

    def _ensure_in_function(stmt: iir.Statement) -> None:
        if stmt.parent_block is not None and stmt.parent_block is not function.block:
            msg = f"Function contains statement from another block: {stmt}"
            raise ValueError(msg)
        stmt.parent_block = function.block

    for stmt in function.block.body:
        _ensure_in_function(stmt)
        result_ast.body.extend(compile_stmt(stmt, context))

    return result_ast


def compile_block(block: iir.Block, context: "CompilerContext") -> Iterator[ast.stmt]:
    def _ensure_in_block(stmt: iir.Statement) -> None:
        if stmt.parent_block is not None and stmt.parent_block is not block:
            msg = f"Block contains statement from another block: {stmt}"
            raise ValueError(msg)
        stmt.parent_block = block

    for stmt in block.body:
        _ensure_in_block(stmt)
        yield from compile_stmt(stmt, context)


def compile_stmt(stmt: iir.Statement, context: "CompilerContext") -> Iterator[ast.stmt]:
    if isinstance(stmt, iir.AssignStatement):
        yield from compile_assign(stmt, context)
        return
    if isinstance(stmt, iir.Return):
        yield ast.Return(pygen.expr(compile_expr(stmt.expr, context)))
        return
    if isinstance(stmt, iir.VarDef):
        typ = stmt.var.typ

        if stmt.init:
            if stmt.var.typ is iir.Auto:
                yield pygen.stmt(f"{stmt.var.name} = {compile_expr(stmt.init, context)}")
            else:
                yield pygen.stmt(
                    f"{stmt.var.name}: {iir_type_to_py_annotation(typ, context)} = {compile_expr(stmt.init, context)}"
                )
        elif stmt.var.typ is not iir.Auto:
            yield pygen.stmt(f"{stmt.var.name}: {iir_type_to_py_annotation(typ, context)}")
        return
    if isinstance(stmt, iir.If):
        yield from compile_if(stmt, context)
        return
    if isinstance(stmt, iir.WhileLoop):
        yield from compile_while(stmt, context)
        return
    if isinstance(stmt, iir.ExprStatement):
        yield pygen.stmt(compile_expr(stmt.expr, context))
        return
    msg = f"Statement type {stmt}"
    raise NotImplementedError(msg)


def compile_assign(stmt: iir.AssignStatement, context: "CompilerContext") -> Iterator[ast.stmt]:
    target = stmt.target
    if isinstance(target, iir.FieldAccess):
        target_expr = f"{compile_expr(target.bound_to, context)}.{target.member_name}"
    elif isinstance(target, iir.Store):
        target_expr = compile_expr(target.ref, context)
    else:
        raise AssertionError(target)
    value_expr = compile_expr(stmt.expr, context)
    yield pygen.stmt(f"{target_expr} = {value_expr}")
    return


def compile_if(stmt: iir.If, context: "CompilerContext") -> Iterator[ast.stmt]:
    if stmt.orelse is None:
        orelse: Iterable[ast.stmt] = []
    elif isinstance(stmt.orelse, iir.If):
        msg = "elif: {stmt}"
        raise NotImplementedError(msg)
    else:
        assert isinstance(stmt.orelse, iir.Block)  # noqa: S101
        orelse = list(compile_block(stmt.orelse, context))

    if isinstance(stmt.condition, iir.LetExpr):
        condition = pygen.expr(f"({stmt.condition.var.name} := {compile_expr(stmt.condition.result, context)})")
    else:
        condition = pygen.expr(compile_expr(stmt.condition, context))
    yield pygen.if_(condition=condition, body=compile_block(stmt.block, context), orelse=orelse)


def compile_while(stmt: iir.WhileLoop, context: "CompilerContext") -> Iterator[ast.stmt]:
    if isinstance(stmt.condition, iir.LetExpr):
        condition = pygen.expr(f"({stmt.condition.var.name} := {compile_expr(stmt.condition.result, context)})")
    else:
        condition = pygen.expr(compile_expr(stmt.condition, context))
    yield pygen.while_(condition=condition, body=compile_block(stmt.block, context))


def _format_args(args: Iterable[iir.Expr], kwargs: Mapping[str, iir.Expr], context: "CompilerContext") -> str:
    return ", ".join(
        [compile_expr(arg, context) for arg in args]
        + [f"{name}={compile_expr(val, context)}" for name, val in kwargs.items()]
    )


def compile_expr(expr: iir.Expr, context: "CompilerContext") -> str:
    if isinstance(expr, iir.SelfExpr):
        return "self"
    if isinstance(expr, iir.MemberAccess):
        return f"{compile_expr(expr.bound_to, context)}.{expr.member_name}"
    if isinstance(expr, (iir.Load, iir.Move)):
        return compile_expr(expr.ref, context)
    if isinstance(expr, iir.BinOp):
        return f"({compile_expr(expr.lhs, context)}) {expr.op} ({compile_expr(expr.rhs, context)})"
    if isinstance(expr, iir.Constant):
        return str(expr.val)
    if isinstance(expr, iir.MethodCall):
        return (
            f"{compile_expr(expr.bound_method.bound_to, context)}.{expr.bound_method.member_name}"
            f"({_format_args(args=expr.args, kwargs=expr.kwargs, context=context)})"
        )
    if isinstance(expr, iir.BoundMethod):
        return f"{compile_expr(expr.bound_method.bound_to, context)}.{expr.bound_method.member_name}"
    if isinstance(expr, iir.Construct):
        constructor = iir_type_to_py_constructor(expr.typ.root_type(), context)
        args_str = _format_args(args=expr.args, kwargs=expr.kwargs, context=context)
        return f"{constructor}({args_str})"
    if isinstance(expr, iir.Failure):
        return "None"
    if isinstance(expr, iir.Success):
        return compile_expr(expr.expr, context)
    if isinstance(expr, (iir.LiteralString, iir.LiteralInt)):
        return repr(expr.value)
    if isinstance(expr, iir.LiteralNull):
        return "None"
    if isinstance(expr, iir.LiteralSequence):
        return f"[{', '.join(compile_expr(e, context) for e in expr.values)}]"
    if isinstance(expr, iir.LiteralMapping):
        args = [f"{compile_expr(key, context)}: {compile_expr(val, context)}" for key, val in expr.key_values]
        return f"{{{', '.join(args)}}}"
    if isinstance(expr, (iir.VarByName, iir.Var)):
        return expr.name
    if isinstance(expr, iir.IsEmpty):
        return f"(len({compile_expr(expr.expr, context)}) == 0)"
    if isinstance(expr, iir.Subscript):
        return f"({compile_expr(expr.target, context)}[{compile_expr(expr.index, context)}])"

    raise AssertionError(repr(expr))
