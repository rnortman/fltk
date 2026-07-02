# Efficiency review — spanprotocol-native-linecol

Commit reviewed: ca06929cd0c5f8589fe9589e7d4135f907b1f9d6 (base 8adf9e3)

No findings.

Scope check: the diff is a static-type-surface change plus tests. `span_protocol.py`
adds a `LineColPosProtocol` and retypes two `SpanProtocol` method return annotations —
these are Protocol method stubs (`...` bodies) that are never executed at runtime, so
zero runtime cost. No production hot path, startup path, or per-request/per-render code
is touched. The new `test_span_protocol_native_free.py` does `ast.parse` once at module
import and re-walks the AST a few times across 4 tests — test-only, negligible, and not
in any product path. No unnecessary work, missed concurrency, memory, or broad-operation
concerns apply here.
