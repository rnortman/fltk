import ast
import textwrap
from collections.abc import Sequence
from typing import Iterable, TypeVar

_T = TypeVar("_T")


def _strip_module(mod: ast.Module, expect: type[_T]) -> _T:
    assert isinstance(mod, ast.Module), f"Not a module but a {type(mod)} {mod}"  # noqa: S101
    assert len(mod.body) == 1  # noqa: S101
    result = mod.body[0]
    if not isinstance(result, expect):
        msg = f"Expected {expect} but got {result}"
        raise ValueError(msg)
    return result


def module(imports: Iterable[str | Sequence[str]] = ()):
    result = ast.parse("")
    assert isinstance(result, ast.Module)  # noqa: S101
    for imp in imports:
        result.body.append(import_(imp))
    return result


def import_(imp: str | Sequence[str]) -> ast.Import:
    if not isinstance(imp, str):
        imp = ".".join(imp)
    tree = ast.parse(f"import {imp}")
    result = _strip_module(tree, ast.Import)
    return result


def function(name: str, args: str, return_type: str) -> ast.FunctionDef:
    tree = ast.parse(textwrap.dedent(f"""def {name}({args}) -> {return_type}: pass"""))
    result = _strip_module(tree, ast.FunctionDef)
    result.body = []
    return result


def expr(expr_py: str) -> ast.expr:
    tree = ast.parse(expr_py, mode="eval")
    assert isinstance(tree, ast.Expression)  # noqa: S101
    assert isinstance(tree.body, ast.expr)  # noqa: S101
    return tree.body


def stmt(stmt_py: str) -> ast.stmt:
    return _strip_module(ast.parse(stmt_py), ast.stmt)


def dataclass(name: str, bases: Iterable[str] = ()) -> ast.ClassDef:
    tree = ast.parse(
        textwrap.dedent(
            f"""
            @dataclasses.dataclass
            class {name}({', '.join(bases)}):
                pass
        """
        )
    )
    result = _strip_module(tree, ast.ClassDef)
    result.body = []
    return result


def klass(name: str, bases: Iterable[str] = ()) -> ast.ClassDef:
    tree = ast.parse(
        textwrap.dedent(
            f"""
            class {name}({', '.join(bases)}):
                pass
        """
        )
    )
    result = _strip_module(tree, ast.ClassDef)
    result.body = []
    return result


def if_(condition: ast.expr, body: Iterable[ast.stmt], orelse: Iterable[ast.stmt]) -> ast.If:
    orelse = list(orelse)
    if orelse:
        tree = ast.parse(
            textwrap.dedent(
                """
                if x:
                  pass
                else:
                  pass
            """
            )
        )
    else:
        tree = ast.parse(
            textwrap.dedent(
                """
            if x:
              pass
            """
            )
        )
    result = _strip_module(tree, ast.If)
    result.test = condition
    result.body = list(body)
    if orelse:
        result.orelse = orelse
    return result


def while_(condition: ast.expr, body: Iterable[ast.stmt]) -> ast.While:
    tree = ast.parse(
        textwrap.dedent(
            """
            while x:
              pass
            """
        )
    )
    result = _strip_module(tree, ast.While)
    result.test = condition
    result.body = list(body)
    return result
