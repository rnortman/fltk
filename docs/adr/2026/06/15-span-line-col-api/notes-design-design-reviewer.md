# Design review: cross-backend `line_col()` on `SpanProtocol`

Reviewer: design-reviewer. Adversarial fact-check of `design.md` against fltk source
(branch `span-line-col-api`) and the clockwork consumer.

Verification summary: the core mechanism is sound and the design is unusually well
source-anchored. Most cited file:line refs check out (Python `Span`/`LineColPos`/
`pos_to_line_col` at `terminalsrc.py:48-205`; Rust `pos_to_line_col` at
`fltk-parser-core/src/terminalsrc.rs:180-228`; `fltk-cst-core/src/span.rs` `Span`/
`SourceInner`/`text()`; `SpanProtocol` at `span_protocol.py:8-56`; clockwork
`cst_util.py`). The findings below are the gaps and inaccuracies that survived
the fact-check.

---

## design-1: Missing implementation step — the new `LineColPos` pyclass is never registered with the `_native` module

- Section: §2.5 "Rust backend implementation", §2.6 "The pyi stub".
- Quote: "A `LineColPos` pyclass in `fltk-cst-core/src/span.rs` (new), exposed via pyo3"
  / "additive, no existing symbol renamed."
- What's wrong: The design adds the pyclass to `fltk-cst-core/src/span.rs` and adds the
  pyi stub, but never accounts for the actual registration path. The pyo3 module entry
  point is `/home/rnortman/src/fltk/src/lib.rs`, which does `m.add_class::<Span>()?;`
  / `m.add_class::<SourceText>()?;` (lib.rs:14-15) and pulls those symbols via the
  re-export shim `src/span.rs` (`pub use fltk_cst_core::{SourceText, Span};`, src/span.rs:1-2).
  For `fltk._native.LineColPos` to exist at runtime, the implementer must ALSO: (a) export
  `LineColPos` from `fltk-cst-core/src/lib.rs` (currently `pub use span::{SourceText, Span, SpanError};`
  at lib.rs:18), (b) add it to the `src/span.rs` re-export, and (c) add
  `m.add_class::<LineColPos>()?;` in `src/lib.rs`. None of these three is mentioned in the design.
- Consequence: An implementer following §2.5/§2.6 literally produces a pyclass that compiles
  but is not importable as `fltk._native.LineColPos`; `py_line_col` returning `Py<LineColPos>`
  works, but the type is unregistered, the pyi stub (§2.6) describes a class the consumer
  cannot import or `isinstance`-check, and any test that does `from fltk._native import LineColPos`
  fails. This is a concrete, load-bearing omission in the "additive" surface plan.
- Suggested fix: Add an explicit step to §2.5: export `LineColPos` from `fltk-cst-core/src/lib.rs`,
  re-export through `src/span.rs`, and register with `m.add_class::<LineColPos>()?` in `src/lib.rs:14-15`.

## design-2: Wrong/over-stated source location for the Python "0-based" claim — `pos_to_line_col` does NOT add `+1`; clockwork does, and only in the display string

- Section: §2.1 "0- vs 1-based".
- Quote: "clockwork adds `+ 1` at the display layer, `cst_util.py:89`".
- What's wrong: The factual claim is *correct* but partially mis-stated in a way that matters
  for the equivalence argument. `cst_util.py:89` adds `+ 1` to BOTH line and col only for the
  human-readable `In <path>:L:C:` header (`f"...:{line_col.line + 1}:{line_col.col + 1}:..."`).
  The caret-indent line `cst_util.py:91` uses the **raw** `line_col.col` with no `+1`
  (`f"{' ' * line_col.col}^\n"`). The design's framing ("clockwork adds `+1` ... a behavior
  change, not additive") is sound, but a reader auditing the 0-based decision against the
  consumer needs to know there are TWO consumption sites with different arithmetic, one of
  which (the caret) breaks visibly if `line_col()` ever returned 1-based.
- Consequence: Minor — the conclusion (keep 0-based) is right and well-justified. But the
  single-line citation under-specifies the blast radius: an implementer who "fixes" col to
  1-based to match the header would silently shift every caret by one column. Worth pinning
  both sites so the 0-based invariant is anchored to the caret math too.
- Suggested fix: Cite `cst_util.py:91` (`' ' * line_col.col`, 0-based caret indent) alongside
  `:89`, noting the caret is the strict 0-based consumer.

## design-3: §3 edge-case table conflates `line_col()` (soft) with `line_col_or_raise()` semantics for the negative-start rows in a way that contradicts §2.1

- Section: §3 edge-case table, rows "UnknownSpan / Span(-1,-1)" and "Negative start, source attached"; cross-ref §2.1 empty/zero-width bullet.
- What's wrong: §2.1 says a source-bearing span over empty source `""` with `start=0`
  returns `LineColPos(line=0, col=-1, ...)` (a real value), while `start=-1` returns `None`.
  But the underlying ported algorithm (`terminalsrc.rs:482-502`, `pos_to_line_col_sentinel_minus_one`
  / `pos_to_line_col_empty_input`) shows `pos = -1` is an IN-DOMAIN sentinel that returns
  `LineColPos(line=0, col=-1)` — it does NOT return `None`. The design's `None`-on-`start<0`
  behavior is therefore a NEW guard the span method imposes on top of the ported algorithm,
  not "a property of the inherited algorithm" as §2.1/§3 repeatedly imply. The design does
  state the new guard ("`start < 0` ... returns `None` via the sourceless/negative-start rule"),
  but the surrounding prose ("a property of the inherited algorithm — see the empty-source note")
  blurs which behaviors are ported vs newly added.
- Consequence: An implementer who "ports `pos_to_line_col` faithfully" (the design's repeated
  instruction, e.g. §2.4 "exact port of pos_to_line_col body") will get `start=-1` →
  `LineColPos(line=0, col=-1)`, NOT `None` — directly contradicting the §3 table row that
  says `Span(-1,-1)` → `None`. The new `start<0 → None` guard must be applied in the span
  wrapper *before* delegating to the ported `_resolve_line_col`/`line_col_inner`, or the
  table is wrong. This is a real correctness fork that the "exact port" language obscures.
- Suggested fix: State explicitly that `start < 0 → None` is a NEW guard in the span-level
  method, applied before the ported bisect, and that the ported helper itself would return
  `(line=0, col=-1)` for `pos=-1`. Reconcile §2.1's "property of the inherited algorithm"
  wording (which is only true for the empty-source `start=0` row, not the `start=-1` rows).

## design-4: Unverifiable / over-precise line citation `terminalsrc.rs:496-502` is a TEST, not the implementation — fine, but §2.1 cites it as if it were the algorithm

- Section: §3 "Empty-source note", §2.1 empty/zero-width bullet.
- Quote: "`pos_to_line_col`'s clamp sets `pos = -1`, producing `line=0, col=-1` on the existing
  implementation (`terminalsrc.rs:496-502` confirms both backends agree)."
- What's wrong: `terminalsrc.rs:496-502` is the body of the `#[cfg(test)]`
  `pos_to_line_col_empty_input` test (asserts `lc.col == -1` for empty input with `pos=-1`),
  not the implementation. More importantly, the design's causal claim is slightly off: for
  empty source the clamp is NOT what produces `pos=-1` from `start=0`. With `source=""`,
  `len=0`; `pos_to_line_col(0)` hits `pos == len` → `pos -= 1` → `pos=-1` (terminalsrc.rs:186).
  So the empty-source `start=0` row DOES go through the clamp and yields `col=-1` — the claim
  is substantively correct, but it is anchored to a test rather than to the clamp at
  `terminalsrc.rs:186` / Python `terminalsrc.py:187-188`.
- Consequence: Low. The asserted behavior is real and test-backed (good), but citing the test
  as "the existing implementation" weakens the groundedness of the empty-source equivalence
  claim. An implementer should anchor the clamp behavior to `terminalsrc.py:187-188` /
  `terminalsrc.rs:185-186`, not the test.
- Suggested fix: Cite the clamp (`terminalsrc.py:187-188`, `terminalsrc.rs:185-186`) as the
  source of `col=-1`, and keep `:496-502` as the cross-backend *test* that pins it.

## design-5: Compromise #1 (duplicated Rust logic) is real and correctly characterized — but the proposed `TODO(linecol-dedup)` is unaccompanied by the required `TODO.md` entry

- Section: §7.1 "Line/col logic is duplicated", final mitigation paragraph.
- Quote: "a `TODO(linecol-dedup)` at the new `fltk-cst-core` implementation pointing at the
  parser-core original".
- What's wrong: The duplication compromise itself is accurate: `fltk._native` (root Cargo.toml)
  depends only on `fltk-cst-core` (Cargo.toml:25, `default-features = false`), and
  `pos_to_line_col`/`LineColPos` live in `fltk-parser-core` (terminalsrc.rs:19-23, 180-228),
  re-exported at `fltk-parser-core/src/lib.rs:27`. `parser-core` depends on `cst-core`
  (terminalsrc.rs:7 `use fltk_cst_core::{Span, SourceText}`), so the cycle/inversion argument
  holds. The dedup-via-moving-down alternative is correctly flagged as larger scope. BUT per
  the project TODO protocol (CLAUDE.md "TODO System": "Adding a TODO requires both an entry in
  `TODO.md` and a `TODO(slug)` comment"), the design proposes the `TODO(linecol-dedup)` code
  comment without specifying the matching `TODO.md` entry.
- Consequence: If implemented as written, the `TODO(linecol-dedup)` comment lands with no
  `TODO.md` row, violating the repo's documented two-part TODO invariant and failing the
  burndown/ground-truth audit the repo runs. Mechanical but real.
- Suggested fix: Add to §7.1 (or §4.5) that the `TODO(linecol-dedup)` requires a paired
  `TODO.md` entry with the same slug.

## design-6: ABI-probe "no marker bump" claim is correct, but the design omits that `SourceInner` is shared across the parser path — adding `line_ends` there is broader than "the Rust backend"

- Section: §2.5.3 "Line-ends cache on `SourceInner`", §7.2.
- Quote: "add `line_ends: OnceLock<Vec<i64>>` to `SourceInner` ... The cache is shared across
  all spans pointing to the same `Arc<SourceInner>`."
- What's wrong: The ABI reasoning is sound and verified: `SourceText` is `{ inner: Arc<SourceInner> }`
  (span.rs:56-58), the probe measures `size_of::<<SourceText as PyClassImpl>::Layout>()`
  (span.rs:128-138, 136-138), and `Arc<T>` is one pointer regardless of `T`, so the probe is
  unchanged — correct, no marker bump needed. However, `SourceInner` is the SAME type used by
  `fltk-parser-core::TerminalSource` (terminalsrc.rs:56-57 builds a `TerminalSource` from a
  `SourceText` whose `inner: Arc<SourceInner>`). `TerminalSource` ALSO holds its own
  `line_ends: OnceLock<Vec<i64>>` (terminalsrc.rs:46). After this change there would be TWO
  line-ends caches over the same source: one on `TerminalSource`, one on `SourceInner`. The
  design treats the `SourceInner` cache as purely "the Rust span backend," but it is structurally
  reachable from the parser crate too and creates a second, independently-populated copy of the
  same table.
- Consequence: Not a correctness bug (both caches derive deterministically from immutable
  `text`), but it is duplicated state and extra per-source memory on the parser hot path's
  shared allocation that the design does not acknowledge. A reviewer/owner should know the
  `SourceInner.line_ends` cache is not isolated to the span method — it rides on every
  parser-produced source. Worth a sentence so it's a conscious decision, not an accident.
- Suggested fix: Note in §2.5.3 that `SourceInner` is shared with `fltk-parser-core::TerminalSource`
  (which has its own `line_ends`), so this adds a second cache over the same text; confirm that
  is acceptable (it is, given immutability) rather than leaving it implicit.

## design-7: Runtime-checkable protocol-extension breakage is real and correctly disclosed — no fix needed, but one omission

- Section: §3 "Protocol `isinstance` breakage", §5.
- What's wrong: Nothing factually wrong. Adding `line_col`/`line_col_or_raise` to the
  `@runtime_checkable` `SpanProtocol` (span_protocol.py:8) does break `isinstance` for any
  out-of-tree class implementing only the current 7-method set — accurately disclosed, and the
  "same property applied to merge/intersect" precedent is plausible. Both in-tree backends are
  updated together (Python `Span` terminalsrc.py:48; Rust `Span` span.rs:382-604), keeping them
  conformant. The one thing not surfaced: `tests/test_span_protocol.py:103-108`
  (`TestProtocolHasNoStartEnd`) only asserts absence of `start`/`end`; the design's §4.2 plan to
  extend it with `callable(SpanProtocol.line_col)` is appropriate. No structural objection.
- Consequence: None beyond the disclosed protocol-extension breakage, which is inherent and per
  CLAUDE.md is an acceptable additive consequence (the generated public symbols are unchanged;
  only hand-written third-party `SpanProtocol` stubs need the two new methods). Recorded as
  confirmation, not a defect.

---

## Requirements coverage (spec → design)

- Cross-backend `line_col` on `SpanProtocol` without raw `.start`/`.end`: COVERED (§2.1, §2.7);
  `.start`/`.end` stay off the protocol (verified span_protocol.py:13-17).
- (line, column) for error reporting via protocol-typed surface: COVERED — returns reused
  `LineColPos` with `.line/.col/.line_span` (terminalsrc.py:155-159), which is exactly what
  clockwork's `format_line_with_error` consumes (cst_util.py:87-92).
- Identical Python/Rust results: ADDRESSED via codepoint counting on both backends (§2.5.5,
  verified: Rust stores codepoint indices span.rs:140-148, and `chars().enumerate()` not
  `char_indices()` at terminalsrc.rs:195-200). The cross-backend equivalence test (§4.1) is the
  load-bearing guard. Caveat: see design-3 (the `start<0` guard is a new fork the "exact port"
  language hides).
- Additive / no renames / no annotation churn: HOLDS for generated symbols and `SpanProtocol`
  callers; the only breakage is the runtime-checkable protocol-extension one (disclosed,
  inherent). But see design-1 — the additive Rust surface is incompletely specified (registration).
- Two flagged compromises real & correctly characterized: YES (design-5, design-6 add the
  missing TODO.md pairing and the shared-`SourceInner` nuance).

## Scope discipline

No over-reach. The design correctly defers `AnyLineColPos`/`LineColPosProtocol` (§2.7, §6.3) and
`end_line_col()` (§6.1) to open questions rather than building them. Reusing `LineColPos` instead
of inventing a tuple/new type is the right (non-abstracting) call. The source-bearing `line_span`
improvement is in scope (it is what unblocks the clockwork `cst_util.py:46` residual) and verified
as already true on the Rust `pos_to_line_col` path (terminalsrc.rs:216,220), so it is parity, not
a new invention.
