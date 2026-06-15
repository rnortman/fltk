# Deep efficiency review: fix-forged-abi-segfault

Commit reviewed: 79460b6 (base d82e82f).

Scope: defensive gating fix on the cross-cdylib slow path of `extract_source_text`
(`crates/fltk-cst-core/src/cross_cdylib.rs`), plus docstring/test changes. Reviewed
against the catch list (unnecessary work, missed concurrency, hot-path bloat, no-op
updates, existence checks, memory, broad ops).

## Hot-path analysis (the one concern worth stating)

The change adds `check_instance_layout::<SourceText>()` (one `getattr("__basicsize__")`
+ `extract::<usize>()`) to `extract_source_text`. That function's *slow path* is, per its
own doc comment (cross_cdylib.rs:89-95) and design §1.3, the **normal** per-read path for
source-bearing span reads from out-of-tree consumer cdylibs — i.e. genuinely hot for those
consumers. So a new Python C-API round-trip there warrants scrutiny.

Conclusion: not a hot-path regression. The new call is placed **after** the cache-hit
early-return (lines 104-111) and only on the cache-*miss* arm (lines 113-122). The
`FLTK_FOREIGN_SOURCE_TEXT_TYPE` cache means cache-miss occurs once per distinct foreign
type (first read), not per read; steady-state per-read cost is the unchanged pointer-compare
in the cache-hit branch. The added getattr therefore runs at the same already-amortized
frequency as the pre-existing `check_abi_pair` (which itself does two getattrs). One extra
getattr on a once-per-type validation is negligible and unavoidable for the fix. Correct
placement.

## No findings.

- No redundant work: `check_abi_pair` and `check_instance_layout` each read distinct
  attributes; no duplicated getattr/extract between them. `size_of::<Layout>()` is a
  compile-time const in both.
- No missed concurrency: path is inherently sequential validation; `get_or_init` race is
  pre-existing and benign (both threads validate the same type).
- No new per-read/startup blocking work (see hot-path analysis above).
- No recurring no-op updates: `get_or_init` is idempotent and unchanged; no polling/interval.
- No existence-check/TOCTOU pattern introduced.
- Memory: no new unbounded structure; cache cell is a single `PyOnceLock<Py<PyType>>`,
  unchanged in cardinality.
- No overly broad read.

Tests are subprocess-isolated as required; no efficiency concern (subprocess spin-up cost
is intrinsic to crash-isolation and bounded to the few forge tests).
