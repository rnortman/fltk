# Interim security review — rust-cst-native-span

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Base 6fd32e7 .. HEAD 767315f. Intermediate review; project deliberately unfinished. Known
gaps (§2.5/§2.6/§2.7/§2.8 incomplete; Rust parse-path regression) excluded per instructions.

Scope reviewed: trust boundaries = untrusted parser input text → byte offsets → native span
slicing; unsafe Rust / PyO3 boundary. Files: `crates/fltk-cst-core/src/span.rs` (Span/SourceText
moved here), `src/span.rs` (re-export shim), `extract_span`/`downcast_unchecked` in the four
generated `cst*.rs`, `fltk/fegen/pyrt/terminalsrc.py`, `fltk/fegen/pyrt/span.py`, `gsm2tree_rs.py`
diff, Cargo manifests. Large generated `.rs` not re-read in full (mechanically emitted).

## Findings

No findings.

Notes on what was checked and cleared (not defects):

- **Span byte-offset slicing under untrusted offsets** (`span.rs` `text`/`text_or_raise`,
  lines 176-236). Slices are the sink for attacker-influenced `start`/`end`. Both paths validate
  `start >= 0`, `end >= 0`, `start <= end`, `end <= src.len()`, and `is_char_boundary(start/end)`
  before the safe `src[start..end]`. No panic, no OOB, no invalid-UTF-8 slice on hostile offsets.
  Sentinel `(-1,-1)` handled. Safe.

- **`unsafe downcast_unchecked::<Span>`** (`extract_span`, generated `cst*.rs:35`). Guarded by
  `is_instance` against the canonical `fltk._native.Span` `PyType` before the unsafe cast; SAFETY
  argument (both cdylibs link the same `fltk-cst-core` rlib → identical layout) is sound. Non-Span
  input hits the `PyTypeError` tail, not the unsafe block. No type-confusion path from Python.

- **Python `with_source` source-type handling** (`terminalsrc.py`). Rejects non-`str`/`SourceText`
  with `TypeError`; no unchecked attribute use. `SourceText._text` private-by-convention only — not
  a security boundary.

- **Injection / secrets / crypto / SSRF / path-traversal / deserialization**: none present. Generated
  `format!` uses are repr and error strings only; no eval/exec/command/SQL/network sink introduced.

- **Dependencies** (Cargo manifests): only new dep is local `path = ...` `fltk-cst-core`, pyo3 0.23
  unchanged. `default-features = false` correctly prevents downstream double-activation of
  `pyo3/extension-module`. No new registry/network deps, no version footgun.
