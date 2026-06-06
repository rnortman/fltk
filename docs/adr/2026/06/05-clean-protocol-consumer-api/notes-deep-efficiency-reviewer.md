# Efficiency review — clean-protocol-consumer-api

Commit reviewed: bc42280 (base 1e78b73).
Scope: terminalsrc.py (SpanKind/Span.kind), src/span.rs (kind getter), gsm2tree.py (protocol gen),
fltk2gsm.py (Shape-1 rewrite), generated fltk_cst_protocol.py.

## efficiency-1

File: `fltk/fegen/fltk2gsm.py:57,69` (`assert item.kind == cst.Item.kind`)

The narrowing assert is the design-sanctioned mechanism (replaces `typing.cast`), and `Item.kind`
runs once per item in `visit_items`. This is a parse-time path (grammar compilation), not a
per-request hot path. The added cost is one attribute read + bridge `__eq__` per item.

Consequence: negligible. Grammar parsing is a one-shot build step, not in any per-render/per-request
loop. No change warranted — noted only to confirm it was evaluated.

## efficiency-2 (non-issue, confirmed)

`src/span.rs:262-272` Rust `Span.kind` getter caches the shared Python `SpanKind.SPAN` in a
`GILOnceCell` (one import for the process) and returns `clone_ref` per call. `clone_ref` is a refcount
bump — the minimal cost to hand a `PyObject` back across the boundary; no per-call import or attribute
walk. Correct and efficient. The cache is process-lifetime and bounded (single object), no leak.

## efficiency-3 (non-issue, confirmed)

Protocol-module runtime additions (`fltk_cst_protocol.py`): a local `NodeKind` enum (14 members),
per-member `_fltk_canonical_name` precomputed at import (not rebuilt per `__eq__`/`__hash__` — same
pattern as the concrete module, see gsm2tree.py:145-156 docstring), and one `_ProtocolLabelMember`
sentinel per label. All are import-time, bounded by grammar size, created once. The former
`TYPE_CHECKING` import of the concrete `NodeKind` is removed, so the protocol module still does NOT
eagerly import a concrete backend — no startup-cost regression; it gains a small fixed set of objects.

## efficiency-4 (non-issue, confirmed)

`terminalsrc.Span` gains `kind` as a `compare=False, hash=False` slotted field with a constant default.
No effect on `Span.__eq__`/`__hash__` cost (excluded from the compared/hashed set). One extra slot per
Span instance (a shared enum reference, not a per-instance allocation). Spans are created in parser hot
loops (`consume_literal`/`consume_regex`), but the field default is a shared singleton reference — no
new allocation per Span. Acceptable.

## Verdict

No actionable efficiency findings. All runtime additions are import-time-bounded, precomputed, or
shared-singleton references; the Rust getter is cached; the per-item assert is parse-time only.
