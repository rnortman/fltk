# Deep Efficiency Review — span-start-end-api

Commit reviewed: 1144c7f615093b087550946f4dbe79653821b852 (base 1f75363)

Scope: `fltk/fegen/pyrt/span_protocol.py` (2 `@property` stubs added to a `typing.Protocol`,
docstrings updated) + `tests/test_span_protocol.py` (test rename + 3 new tests).

No findings.

Rationale: the change is purely a type-surface and documentation change. The added
`start`/`end` are `@property` stubs on a `Protocol` whose bodies are `...` — no runtime
computation, no loops, no I/O, no allocation. Both backends already expose `start`/`end`
(Python dataclass fields; Rust `get_start`/`get_end` getters), so nothing new is computed
at access time. None of the watched patterns apply: no redundant work, no sequential-when-
parallel ops, no hot-path/startup bloat, no recurring no-op updates, no existence pre-checks,
no unbounded structures or leaks, no overly broad reads.
