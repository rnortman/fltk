import ast
from typing import cast, Any, Callable, Dict, Iterable, Iterator, TypeVar, Union

import astor  # type: ignore

from fltk.iir import model as iir
from fltk.iir import typemodel
from fltk.iir.py import reg as pyreg
from fltk import pygen


def compile(mod: iir.Module) -> ast.Module:
    result = ast.parse("")
    for stmt in mod.block.body:
        if isinstance(stmt, iir.ClassDef):
            result.body.append(compile_class(stmt.klass))
        if isinstance(stmt, iir.Function):
            result.body.append(compile_function(stmt))
        raise NotImplementedError(f"Module-level statement {stmt}")
    return result


def iir_type_to_py_annotation(typ: iir.Type) -> str:
    if isinstance(typ, iir.PrimitiveType):
        return pyreg.lookup(typ).name
    if typ is iir.Void:
        return "None"
    if typ.instantiates is iir.Maybe:
        return f"Optional[{iir_type_to_py_annotation(typ.get_arg_as_type('value_type'))}]"
    try:
        type_info = pyreg.lookup(typ)
    except KeyError:
        try:
            type_info = pyreg.lookup(typ.root_type())
        except KeyError:
            print("\n".join(str(x) for x in pyreg._type_registry.keys()))
            print(typ)
            assert False, f"Unknown type: {typ}"
    name = type_info.import_name()
    args = typ.get_args()
    if args:

        def _arg_annotation(arg: typemodel.Argument) -> str:
            if isinstance(arg, iir.Type):
                return iir_type_to_py_annotation(arg)
            return str(arg)

        return f"{name}[{','.join(_arg_annotation(arg) for arg in args.values())}]"
    return name


def compile_class(klass: iir.ClassType) -> ast.ClassDef:
    assert klass.cname is not None
    assert all(bc.cname for bc in klass.base_classes)
    result_ast = pygen.dataclass(name=klass.cname, bases=[cast(str, bc.cname) for bc in klass.base_classes])
    if klass.doc:
        result_ast.body.append(pygen.stmt(f'"""{klass.doc}"""'))

    T = TypeVar("T", iir.Field, iir.Method)

    def _ensure_in_class(attr: T) -> None:
        if attr.in_class is None:
            attr.in_class = klass
        elif attr.in_class is not klass:
            raise ValueError(f"Attribute {attr} is in a different class instance than {klass}")

    for field in klass.get_fields():
        _ensure_in_class(field)
        result_ast.body.append(pygen.stmt(f"{field.name}: {iir_type_to_py_annotation(field.typ)}"))

    if ctr := klass.constructor:
        _ensure_in_class(ctr)
        method = klass.def_method(
            name="__init__",
            doc=ctr.doc,
            params=ctr.params,
            mutable_self=True,
            using_self=ctr.self_expr,
            return_type=iir.Void,
        )
        for fld, init in ctr.init_list:
            if isinstance(init, iir.InitFromParamType):
                method.block.body.append(
                    iir.AssignStatement(
                        parent_block=method.block,
                        target=ctr.self_expr.fld[fld.name].store(),
                        expr=ctr.get_param(fld.name).move()
                    )
                )
            else:
                method.block.body.append(
                    iir.AssignStatement(
                        parent_block=method.block,
                        target=ctr.self_expr.fld[fld.name].store(),
                        expr=init
                    )
                )
        for stmt in ctr.block.body:
            stmt.parent_block = method.block
            method.block.body.append(stmt)
        result_ast.body.append(compile_function(method))
        for stmt in ctr.block.body:
            stmt.parent_block = ctr.block

    for method in klass.get_methods():
        result_ast.body.append(compile_function(method))

    assert all(isinstance(attr, (iir.Field, iir.Method)) for attr in klass.block.get_leaf_scope().identifiers.values())

    print(astor.to_source(result_ast))
    return result_ast


def compile_function(function: iir.Function) -> ast.FunctionDef:
    assert function.name is not None
    result_ast = pygen.function(
        name=function.name,
        args=", ".join(f"{p.name}: {iir_type_to_py_annotation(p.typ)}" for p in function.params),
        return_type=iir_type_to_py_annotation(function.return_type)
    )

    if function.doc:
        result_ast.body.append(pygen.stmt(f'"""{function.doc}"""'))
    elif not function.block.body:
        result_ast.body.append(pygen.stmt("pass"))

    def _ensure_in_function(stmt: iir.Statement) -> None:
        if stmt.parent_block is not None and stmt.parent_block is not function.block:
            raise ValueError(f"Function contains statement from another block: {stmt}")
        stmt.parent_block = function.block

    for stmt in function.block.body:
        _ensure_in_function(stmt)
        result_ast.body.extend(compile_stmt(stmt))

    return result_ast


def compile_block(block: iir.Block) -> Iterator[ast.stmt]:
    def _ensure_in_block(stmt: iir.Statement) -> None:
        if stmt.parent_block is not None and stmt.parent_block is not block:
            raise ValueError(f"Block contains statement from another block: {stmt}")
        stmt.parent_block = block

    for stmt in block.body:
        _ensure_in_block(stmt)
        yield from compile_stmt(stmt)


def compile_stmt(stmt: iir.Statement) -> Iterator[ast.stmt]:
    if isinstance(stmt, iir.AssignStatement):
        yield from compile_assign(stmt)
        return
    if isinstance(stmt, iir.Return):
        print(stmt.expr)
        print(repr(compile_expr(stmt.expr)))
        yield ast.Return(pygen.expr(compile_expr(stmt.expr)))
        return
    if isinstance(stmt, iir.VarDef):
        typ = stmt.var.typ

        if stmt.init:
            if stmt.var.typ is iir.Auto:
                yield pygen.stmt(f"{stmt.var.name} = {compile_expr(stmt.init)}")
            else:
                yield pygen.stmt(f"{stmt.var.name}: {iir_type_to_py_annotation(typ)} = {compile_expr(stmt.init)}")
        else:
            if stmt.var.typ is not iir.Auto:
                yield pygen.stmt(f"{stmt.var.name}: {iir_type_to_py_annotation(typ)}")
        return
    if isinstance(stmt, iir.If):
        yield from compile_if(stmt)
        return
    raise NotImplementedError(f"Statement type {stmt}")


def compile_assign(stmt: iir.AssignStatement) -> Iterator[ast.stmt]:
    target = stmt.target
    if isinstance(target, iir.FieldAccess):
        target_expr = f"{compile_expr(target.bound_to)}.{target.member_name}_"
    elif isinstance(target, iir.Store):
        target_expr = target.var.name
    else:
        assert False, target
    value_expr = compile_expr(stmt.expr)
    yield pygen.stmt(f"{target_expr} = {value_expr}")
    return


def compile_if(stmt: iir.If) -> Iterator[ast.stmt]:
    if stmt.orelse is None:
        orelse: Iterable[ast.stmt] = []
    elif isinstance(stmt.orelse, iir.If):
        raise NotImplementedError("elif: {stmt}")
    else:
        assert isinstance(stmt.orelse, iir.Block)
        orelse = compile_block(stmt.orelse)

    yield pygen.if_(condition=pygen.expr(compile_expr(stmt.condition)), body=compile_block(stmt.block), orelse=orelse)


def compile_expr(expr: iir.Expr) -> str:
    if isinstance(expr, iir.SelfExpr):
        return "self"
    if isinstance(expr, (iir.Load, iir.Move)):
        return expr.var.name
    if isinstance(expr, iir.BinOp):
        return f"({compile_expr(expr.lhs)}) {expr.op} ({compile_expr(expr.rhs)})"
    if isinstance(expr, iir.Constant):
        return str(expr.val)
    if isinstance(expr, iir.MemberAccess):
        return f"{compile_expr(expr.bound_to)}.{expr.member_name}"
    if isinstance(expr, iir.MethodCall):
        assert not expr.args
        return f"{compile_expr(expr.bound_method.bound_to)}.{expr.bound_method.member_name}()"
    assert False, expr
