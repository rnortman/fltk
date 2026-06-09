# Deep correctness review — rust-cst-child-span-test

Reviewed: c505f3c..7a288b6 (HEAD 7a288b6, "Add TestChildSpanAccessorContract + retire rust-cst-child-span-test TODO"). Test-only diff: `tests/test_phase4_fegen_rust_backend.py`, `TODO.md`, implementation log.

Style note: concise, precise, complete, unambiguous; no padding. Audience: smart LLM/human.

Verified against source (not just the design doc):

- `tests/rust_cst_fegen/src/cst.rs` is `include!("../../../src/cst_fegen.rs")`, so the standalone `fegen_rust_cst` module the tests import has byte-identical generated code to the embedded backend reviewed below.
- Triples are correct: `Identifier.append_name`/`child_name` (`src/cst_fegen.rs:4535,4564`), `Literal.append_value`/`child_value` (`:5293,5322`), `RawString.append_value`/`child_value` (`:4914,4943`). All three child enums are Span-only and structurally identical.
- Zero-arg construction `node_class()` is valid: `#[new] #[pyo3(signature = (*, span = None))]` defaults to `Span::unknown()` (`src/cst_fegen.rs:4394-4405`).
- Slice math: `"hello world!"[3:9] == "lo wor"` — correct; `Span.text()` uses codepoint indices matching Python slicing (`crates/fltk-cst-core/src/span.rs:218-248`), ASCII input keeps byte/codepoint divergence out of scope as designed.
- `result.text() is None` / `has_source() is False` / `is True`: `text()` returns `Option<String>` (None for sourceless), `has_source()` returns Rust `bool` → Python bool singletons; identity assertions are sound (`span.rs:218,298`).
- `isinstance(result, Span)` with `Span` imported from `fltk._native`: sound — `to_pyobject` constructs via the cached canonical `fltk._native.Span` type (`get_span_type`, `src/cst_fegen.rs:44-54`; `IdentifierChild::to_pyobject` `:4308-4323`), not the cdylib-local registration, so the pin holds even though the test crosses cdylibs.
- Cross-cdylib append path: test passes `fltk._native.Span` into a `fegen_rust_cst` node; fast-path `extract::<Span>()` fails (different type registration), slow path `is_instance(fltk._native.Span)` + `downcast_unchecked` succeeds (`src/cst_fegen.rs:16-42`) — exactly the consumer-facing path the design targets.
- Rejection path: `tsrc.Span` fails both `is_instance_of::<Span>()` and `is_instance(span_type)` → `PyTypeError` "unsupported child type" (`src/cst_fegen.rs:4325-4338`, mirrored for Literal/RawString).
- `tsrc.Span(3, 9)`: frozen dataclass with positional `start`, `end` (`fltk/fegen/pyrt/terminalsrc.py:48-53`) — constructs without error today (see correctness-1).
- No `is` identity assertions on returned spans; matches the clone-on-extraction TODO constraint.
- Implementation log's "31 tests" reconciles: 4 (AC8) + 9 (new) + 15 (AC6) + 3 (AC9). Confirmed by running the file: 31 passed.
- TODO.md edit removes only the `rust-cst-child-span-test` entry; `rust-cst-child-node-identity` untouched. Comment block at old lines 111-113 removed; slug fully retired (no remaining `TODO(rust-cst-child-span-test)` in tree).

## Findings

### correctness-1

- `tests/test_phase4_fegen_rust_backend.py:163-167` (`test_append_rejects_terminalsrc_span`).
- The `pytest.raises(TypeError)` block contains three operations besides the rejection under test: the `tsrc.Span(3, 9)` constructor call, the `getattr` bound-method lookup, and the call's argument binding. `pytest.raises` has no `match=`, so a `TypeError` from any of these passes the test.
- Why: today `tsrc.Span(3, 9)` constructs cleanly and the only `TypeError` source is `extract_from_pyobject`'s rejection ("Identifier: unsupported child type ..."). But the test exists to pin against future drift; under that same drift the guard can go vacuous — e.g. a `terminalsrc.Span` signature change making `(3, 9)` raise `TypeError`, or a generated `append_<label>` arity change making the call itself raise `TypeError` before any child-type check runs.
- Consequence: the test passes for the wrong reason exactly in the future-change scenarios it is designed to catch — `append_<label>` could silently re-admit arbitrary children (the contract the design's test 3 explicitly pins as "fails loudly ... rather than the contract drifting silently") while this test stays green.
- Suggested fix: construct the span outside the block and pin the message: `bad = tsrc.Span(3, 9)` then `with pytest.raises(TypeError, match="unsupported child type"): getattr(node, append_method)(bad)`.

No other findings.
