# Efficiency review — cst-python-feature-gate

Reviewed: e6a9117..431ab53 (HEAD 431ab53). Diff is mostly cfg-gating (compile-time only, no runtime cost added); generated-file regeneration matches generator output; Makefile lane additions are design-mandated and their cargo invocations share target-dir artifacts across identical feature resolutions. Two findings.

Style note: concise, precise, no padding; audience is a smart LLM/human.

## efficiency-1: `Span::text()` does up to three full linear scans of the source per call — now the mode-independent native API, and the gaps report misses this dominant cost

`crates/fltk-cst-core/src/span.rs:230-262` (native `pub fn text`).

The body (moved verbatim from `#[pymethods]`, so pre-existing logic — but this diff is what promotes it to the public native API intended for the phase-2 Rust parser, and this diff authors the gaps report whose job is to record native-API cost):

1. `src.char_indices().nth(start)` — scans from byte 0, O(start).
2. `src.char_indices().nth(end)` — **restarts from byte 0**, O(end), even though `end >= start` is already established and the scan could resume from `byte_start`.
3. On `nth(end) == None`, falls back to `src.chars().count()` — a third full O(len) scan. This is not a rare path: it fires for **every span ending exactly at end-of-source** (e.g. the root node's span, any trailing token), so reading a full-source span costs three complete traversals of the source text.

Plus the `String` allocation per call.

**Consequence:** per-span-read cost is O(source_len), not O(span_len). A phase-2 parser (or any tree traversal calling `text()` per node, as `spike_tests.rs:traverse_items_children_down_to_leaf_spans` already models) pays O(nodes × source_len) — quadratic-ish scaling that becomes the dominant CST read cost on large inputs. It also bites today's Python callers via `py_text`, identically. gaps.md item 2 records only the `String` allocation and item 3 the missing byte-offset helpers; the repeated codepoint→byte scans — the larger asymptotic term — are recorded nowhere.

**Fix:** single forward pass: find `byte_start` via `char_indices().nth(start)`, then continue the *same* iterator `(end - start)` chars to find `byte_end`, treating iterator exhaustion as `byte_end = src.len()` only when exactly `end - start` chars were consumed — eliminates the restart and the separate `chars().count()`. Behavior-preserving (same `None` cases), so it does not violate the "findings only, no fixes" spike rule (this is increment-1 code, not spike code). At minimum, add the scan cost to gaps.md alongside item 2/3 so the phase-2 byte-offset design accounts for it.

## efficiency-2: `make gencode` generates the identical poc_grammar artifact twice

`Makefile:128-132` (gencode): `gen-rust-cst poc_grammar.fltkg → src/cst_generated.rs` and, later, `$(MAKE) gen-rust-cst GRAMMAR=...poc_grammar.fltkg RS_OUT=crates/fltk-cst-spike/src/cst.rs`. The two outputs are byte-identical at HEAD (verified: `diff -q` clean; implementation log states "identical to src/cst_generated.rs — same source grammar").

**Consequence:** one redundant generator run per `gencode` invocation — an extra `uv run python` subprocess (interpreter startup + grammar parse + full generation) plus a sub-make. Dev-time only (gencode is a manual regen entrypoint, not in `check`), so the cost is seconds of wall time per regen, recurring every regen, forever.

**Fix (optional, low impact):** emit once and copy (`cp src/cst_generated.rs crates/fltk-cst-spike/src/cst.rs`) with a comment noting the two files are definitionally the same generator output of the same grammar — also makes the "these must be identical" invariant explicit instead of incidental. If intentional divergence of the spike grammar is anticipated, keep as is and ignore this finding.
