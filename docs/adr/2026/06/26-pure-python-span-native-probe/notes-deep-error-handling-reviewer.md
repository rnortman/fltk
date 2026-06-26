# Error-handling review — base 49e9701..HEAD ab38ec7

## errhandling-1

**File:line** `fltk/fegen/pyrt/span.py:8–14`

**The broken error path**

`except Exception:` now falls back to `terminalsrc` silently, with no warning, no log, and no
structured error.  Before this diff the unconditional terminalsrc import at the top of the file
provided the fallback, and the `except` block emitted `warnings.warn(...)`.  Now both the
unconditional import and the warning are gone; the fallback is entirely inside the `except` clause,
and the clause is still `except Exception:`.

```python
try:
    from fltk._native import SourceText, Span, UnknownSpan  # type: ignore[assignment]
except Exception:          # ← catches OSError, SystemError, AttributeError, …
    from fltk.fegen.pyrt.terminalsrc import SourceText, Span, UnknownSpan
```

**Why — where the error goes**

`ImportError` / `ModuleNotFoundError` is the expected case (native not installed) and is correctly
handled by the fallback.  But `except Exception:` also catches:

- `OSError` — ABI mismatch (Python version upgrade, wrong `manylinux` wheel, `.so` corruption).
- `SystemError` — C-level initialization crash in the native extension.
- `AttributeError`, `ValueError`, `RuntimeError` — any exception raised during `fltk._native`
  module-level code.

All of these are swallowed with no record.  Before the diff, at least a `UserWarning` fired.
After the diff there is nothing.

**Consequence — silent failure mode**

A developer or on-call engineer who has `fltk._native` installed but broken (Python version
mismatch after an upgrade, corrupted `.so`, extension initialization bug) will see `span.Span is
terminalsrc.Span` rather than `fltk._native.Span` and have no diagnostic signal — no warning, no
log entry, no exception — to explain the discrepancy.  Tests that assert `span.Span is
fltk._native.Span` (e.g., `test_span_protocol.py:43–54`) will fail, but the cause will look
identical to "native simply not installed."  The `test_reload_without_native_emits_no_warning`
test in `tests/test_span_protocol.py` exercises only `sys.modules["fltk._native"] = None` (clean
ImportError), so the ABI-mismatch / OSError path is not covered there and the issue is invisible.

**What must change**

Narrow the catch to `except ImportError:`.  `ImportError` (including `ModuleNotFoundError`) is the
only expected case: native is simply absent.  Any other exception from a present-but-broken native
extension should propagate so the caller sees the true failure.  If silent fallback is desired even
for broken extensions, the minimum change is to log the exception at WARNING level (including the
full traceback via `exc_info=True`) so on-call can distinguish "native not installed" from "native
crashed on load."

The same `except Exception:` breadth exists in `fltk/fegen/pyrt/span_protocol.py:113–118`
(`AnySpan` block) but that code was present before this diff and is unchanged here; it is noted
for completeness.
