# Deep error-handling review — span-selector-broken-native-diagnostic

Commit reviewed: 0fddc5ab62f00b13846c7b7771ad7ad011eda5af (base f71a765ec6300c23e5aa69a64df95b980e1dfbc9)

No findings.

## Basis

The change narrows `except Exception:` → `except ImportError:` at both backend-selector
sites (`fltk/fegen/pyrt/span.py:10`, `fltk/fegen/pyrt/span_protocol.py:123`). This is
precisely the error-handling fix under review, and it is correct on my axes:

- Expected condition (native genuinely absent → `ModuleNotFoundError`, an `ImportError`
  subclass) is validated and handled with an intentional silent fallback, pinned by
  tests.
- Unexpected condition (present-but-broken extension raising `OSError`/`SystemError`/
  `AttributeError`/etc.) now propagates loudly at import time instead of silently
  degrading to pure-Python. On-call gets a real traceback at the point of damage.
- No `let _ =`, no empty/broad catch, no default-on-error fallback lacking justification,
  no swallowed `?`-style propagation. `KeyboardInterrupt`/`SystemExit`/PanicException
  behavior is unchanged (they were never caught by `except Exception` either... actually
  they escape both).
- Both sites change in lockstep in one commit, closing the site-divergence hazard the
  design calls out.

## Noted, not a finding (deliberate, justified accepted limitation)

A broken extension whose failure surfaces as a plain `ImportError` (loader-level
`undefined symbol`, or a broken Python-level import inside `_native`'s init) still falls
back silently with zero diagnostic — a downstream consumer expecting the Rust backend
would degrade to pure-Python with no signal, and on-call could not tell from logs that
the built extension failed to load. This residual silent-failure mode is explicitly
identified and accepted in the design ("Considered and rejected: narrowing further to
`ModuleNotFoundError`") per requirements, so it is a justified fallback, not a swallow.
Flagging only so it is on record: the span.py code comment frames `ImportError` as
"the native backend is simply absent," which is not strictly exhaustive (an `ImportError`
can also mean a broken extension); a reader relying on the comment could over-trust that
all broken extensions propagate. Documentation nuance, not an error-handling defect.
