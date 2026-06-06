# `_cst_const` vs `cst` in fltk2gsm.py — Diagnostic Investigation

Concise. Precise. No fluff. Audience: smart LLM/human.

## 1. What is `_cst_const` and where is it imported?

`fltk/fegen/fltk2gsm.py:8`:
```python
from fltk.fegen import fltk_cst as _cst_const
```

`_cst_const` is bound to the **concrete implementation module** `fltk.fegen.fltk_cst` — the generated Python CST module that contains real `enum.Enum` subclasses. Specifically, `fltk_cst.Items.Label` is an `enum.EnumMeta` (a real Python enum), so `fltk_cst.Items.Label.NO_WS` is a live `enum.Enum` member at runtime.

This import is a **normal unconditional runtime import** — not guarded by `TYPE_CHECKING`.

## 2. What is `cst` bound to?

`fltk/fegen/fltk2gsm.py:11-12`:
```python
if TYPE_CHECKING:
    from fltk.fegen import fltk_cst_protocol as cst
```

`cst` is bound to `fltk.fegen.fltk_cst_protocol` **only under `TYPE_CHECKING`** — i.e., only during static analysis (pyright, mypy), never at runtime. At runtime the name `cst` does not exist in `fltk2gsm`'s module namespace.

`fltk_cst_protocol` is a Protocol-based stub module. Its `Items.Label` is a plain class body with `ClassVar[object]` annotations:

```python
# fltk/fegen/fltk_cst_protocol.py:101-105
class Items(typing.Protocol):
    class Label:
        ITEM: typing.ClassVar[object]
        NO_WS: typing.ClassVar[object]
        WS_ALLOWED: typing.ClassVar[object]
        WS_REQUIRED: typing.ClassVar[object]
```

These are **annotation-only declarations**. At runtime, `fltk_cst_protocol.Items.Label` is an empty plain class — `NO_WS` and the other names do not exist as attributes (`AttributeError` at runtime, confirmed empirically).

## 3. Why can the code NOT simply write `cst.Items.Label.NO_WS` at runtime?

The direct blocker is: **`cst` does not exist at runtime**. It is imported inside `if TYPE_CHECKING:` (line 11), so at runtime it is unbound. Any expression `cst.Items.Label.NO_WS` outside a string annotation would raise `NameError: name 'cst' is not defined`.

Even if `cst` were importable at runtime (i.e., the `TYPE_CHECKING` guard were removed), the underlying protocol class `fltk_cst_protocol.Items.Label` has **no attribute values** for `NO_WS` etc. — only `ClassVar[object]` annotations. Those annotations are not values; accessing them raises `AttributeError` (confirmed empirically: `AttributeError: type object 'Label' has no attribute 'NO_WS'`).

So there are two independent blockers:
- **Blocker A (name):** `cst` is `TYPE_CHECKING`-only; it does not exist at runtime.
- **Blocker B (value):** Even if the import were unconditional, `fltk_cst_protocol.Items.Label.NO_WS` has no runtime value — the Protocol's `Label` class is a stub with only type annotations, not a real enum.

The `_cst_const` alias exists precisely to give runtime code access to the concrete enum values from `fltk_cst`, while `cst` (the protocol type) serves only the type-checker.

## 4. Can a clean `cst.X.Label.Y` form be achieved without the alias?

Yes, under one specific structural change: **rename the runtime `fltk_cst` import to `cst` and remove the `TYPE_CHECKING`-guarded protocol import**, while ensuring pyright accepts the concrete class in place of the protocol.

Concretely, what would have to change:

1. **Remove the `TYPE_CHECKING` guard** on `fltk_cst_protocol`. Replace:
   ```python
   if TYPE_CHECKING:
       from fltk.fegen import fltk_cst_protocol as cst
   ```
   with an unconditional import of `fltk_cst_protocol as cst` (or rewrite it differently; see below).

2. **Provide runtime values in the protocol's Label stubs** — or switch the `cst` name at runtime to `fltk_cst` directly. The clean option is: import `fltk_cst as cst` unconditionally and annotate with `fltk_cst_protocol` types via a `TYPE_CHECKING` cast or type: ignore. Alternatively, annotate using the concrete types from `fltk_cst` directly (which are the real enum members).

3. **Pyright concern:** The current design separates the concrete `fltk_cst` from the protocol `fltk_cst_protocol` so that the type checker sees the protocol interface (structural subtyping for cross-backend compatibility). If `cst` is rebound to `fltk_cst` at runtime, pyright would need to be told (via `TYPE_CHECKING` branch or type stubs) that `fltk_cst` satisfies the protocol. Since `fltk_cst.Items` does implement `fltk_cst_protocol.Items` (structural), this should work, but would require verifying that pyright's structural check passes without the current protocol-alias indirection.

**No circular import blocker** exists here: `fltk_cst.py` does not import from `fltk2gsm.py` (confirmed: `grep -n "fltk_cst_protocol\|fltk2gsm" fltk_cst.py` returns nothing).

**Summary of required changes for clean form:**
- Import `fltk_cst as cst` unconditionally (replacing `_cst_const`).
- For type-checker annotation, either: (a) keep `TYPE_CHECKING` import of `fltk_cst_protocol as cst` to shadow the runtime binding for pyright (the `from __future__ import annotations` means annotations are strings; this works), or (b) annotate with concrete `fltk_cst` types directly.
- Option (a) is already half-present — what's missing is making the unconditional name `cst` point to `fltk_cst` rather than keeping it as `_cst_const`. The `from __future__ import annotations` at line 1 means all annotations are lazy strings, so the `TYPE_CHECKING`-only `cst` binding is sufficient for pyright even if it doesn't exist at runtime — this is the standard pattern. The only gap is that the runtime alias uses a different name (`_cst_const`) instead of `cst`.

**Minimal clean fix:** Add `from fltk.fegen import fltk_cst as cst` as an unconditional runtime import, and either remove `_cst_const` entirely (replacing all uses) or keep it as a local alias. The `TYPE_CHECKING` block's `from fltk.fegen import fltk_cst_protocol as cst` would shadow `cst` for pyright only (since `from __future__ import annotations` is in effect), giving pyright the protocol type while runtime gets the concrete enum. This is a clean, achievable refactor with no architectural blocker.
