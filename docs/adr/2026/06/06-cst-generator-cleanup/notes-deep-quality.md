Concise. Precise. No padding. Audience: smart LLM/human.

Commit reviewed: b72aea6

---

## quality-1

**File:line** `fltk/fegen/gsm2tree.py:550` (`_emit_label_quintet` signature) and `gsm2tree.py:289` (`concrete_body_for`)

**Issue** `body_for: Callable[[str, str], list[ast.stmt]]` passes the method name as a raw `str` — one of exactly five valid values (`"append"`, `"extend"`, `"children"`, `"child"`, `"maybe"`). The concrete implementation (`concrete_body_for`) handles these with a chain of `if method == "..."` guards and raises `ValueError` on an unrecognised string, which means typos or a future sixth accessor spelled differently silently fall through until runtime. The project already uses `typing.Literal` elsewhere (line 234, 621) and `from typing import TYPE_CHECKING` is in-file; a `Literal` union or a local `StrEnum`/`Literal` alias would narrow the type statically.

**Consequence** Adding a sixth accessor (e.g. `count_<l>`) requires editing the enum/Literal type, both call sites, and the `concrete_body_for` dispatch. Without a constrained type, pyright gives no coverage-exhaustion feedback — a new method name can be misspelled in one call site and the only signal is a runtime `ValueError` on the first code-generation run that exercises that path. The pattern will be replicated if a third caller (e.g. a Rust-backend protocol generator) is added.

**Fix** Change `body_for`'s first parameter type to `typing.Literal["append", "extend", "children", "child", "maybe"]`. No logic change; this is a zero-cost annotation tightening that makes pyright catch unknown method names at static-analysis time and documents the closed set explicitly for future maintainers.

---

## quality-2

**File:line** `fltk/fegen/gsm2tree.py:523`

**Issue** `__all__` is emitted via `pygen.stmt(f"__all__ = {public_names!r}")`. `list.__repr__` produces a valid Python list literal here (confirmed by inspection: `ast.Constant` nodes, alphabetically sorted strings, deterministic). However the approach bypasses pygen's AST-construction API by relying on `repr()` round-tripping cleanly through `ast.parse` inside `pygen.stmt`. The rest of the generator constructs AST nodes structurally; this is the sole site that serialises a Python value to a string and re-parses it. If `public_names` ever contained a name requiring quoting (non-identifier chars, embedded quotes), or if `pygen.stmt` ever switched to a non-`ast.parse` implementation, the output would silently corrupt.

**Consequence** Fragility is localised (the names are all identifiers today, so it is not a current bug), but the pattern is inconsistent with the rest of the generator and will confuse future readers who assume all AST construction goes through pygen. The structural equivalent — `ast.Assign(targets=[ast.Name(id='__all__', ...)], value=ast.List(elts=[ast.Constant(v) for v in public_names]))` — is explicit, cannot misquote, and matches the project's conventions.

**Fix** Build the `__all__` assignment using `ast.Assign` / `ast.List` / `ast.Constant` directly (or add a `pygen.all_(names)` helper if that matches the project's pygen-extension pattern), rather than interpolating `repr(list)` into a string.

---

No further findings.
