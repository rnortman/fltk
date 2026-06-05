# Implementation Log: Clean Protocol-Only Consumer API

## Increment 1 — `terminalsrc.SpanKind` + `Span.kind` field (§2.1)

Add `SpanKind` enum with cross-backend bridge and `kind` field to `terminalsrc.Span`.
