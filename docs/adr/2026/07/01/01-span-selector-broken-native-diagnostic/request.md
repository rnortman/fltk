### 16. `span-selector-broken-native-diagnostic` — DO (narrow the catch)

- **Problem:** the backend selector's `except Exception` silently falls back to
  pure-Python for *any* failure — a present-but-broken native extension (ABI mismatch,
  corrupted `.so`) is indistinguishable from a clean pure-Python install.
- **Ground truth:** both cited sites confirmed; in-tree consumers are tests-only, so this
  is downstream-facing robustness for the standalone selector utility.
- **What the work looks like:** the TODO's option (a): narrow to `except ImportError` at
  both `span.py` and the `AnySpan` block in lockstep (absent-native still raises
  `ImportError`, so the legitimate fallback keeps working; a genuinely broken extension
  now propagates loudly), plus a test for the non-ImportError path.
- **The case for skipping:** zero in-tree impact; some ABI breaks surface as ImportError
  anyway and would still fall back silently.
- **Recommendation: Do** — small, "robust as fuck"-aligned, decision already framed.
