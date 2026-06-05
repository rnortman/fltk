# Judge verdict — design review

> Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Phase: design. Doc: `docs/adr/2026/06/05-clean-protocol-consumer-api/design.md`. Round 1.
Notes: `notes-design-design-reviewer.md` — 5 findings (design-1..5). Requirements anchor:
`requirements.md` (Shape 1/Shape 2 + AC 12, LOCKED). Empirical ground truth:
`narrowing-mechanism-probe.md`.

Procedural note: no `dispositions-design.md` exists in the dir. `design.md` (mtime 19:06) postdates
the reviewer notes (19:05) and was revised in place; the revised design text is the de facto
disposition for each finding. Each is adjudicated as a "Fixed"-class disposition: does the revised
design resolve the reviewer's stated gap, verified against source. Design phase → no TODO walk.
(This file replaces a stale prior verdict written against an earlier, superseded design that used a
per-label-accessor mechanism; that design and its findings no longer exist.)

## Findings walk

### design-1 — Protocol `Label` sentinel `__eq__`/`__hash__` must mirror the exact bridge (NotImplemented + canonical-name hash) or AC 6/7/10 symmetry breaks
Claim: §2.3c says "give the sentinel the bridge `__eq__`/`__hash__`" without pinning the shape. Shape 1
sites write `concrete_label == cst.X.Label.MEMBER` (concrete LEFT), so the concrete enum's bridge wins
and the sentinel's own `__eq__` is never reached there — that path works. BUT AC 7 requires both operand
orders (sentinel as subject) and AC 6 requires general `==`/`!=`. A naive sentinel returning `True/False`
for all foreign operands blocks reflected resolution / mis-answers; an identity/default `__hash__` makes
equal members hash unequal → AC 7 hash clause + set/dict use break. Consequence: silent AC 6/7/10 failure
on the Label axis. Real should-fix; correctly scoped (not a Shape-1 blocker, but an AC-7/AC-10 correctness
gap).
Source: bridge `__eq__` at `gsm2tree.py:117-124` returns `NotImplemented` for foreign operands (line
124) and resolves via `getattr(other,'_fltk_canonical_name',None)`; `__hash__ = hash(self._fltk_canonical_name)`
(line 131). Shape-1 concrete-LEFT sites at `fltk2gsm.py` confirmed by requirements Shape 1. Confirmed.
Disposition (revised design): §2.3c lines 213-227 now state in bold "**The sentinel's `__eq__`/`__hash__`
MUST be the EXACT `_emit_cross_backend_eq_hash` shape**", spell out identity fast-path → same-type
fast-path → `getattr(...,'_fltk_canonical_name',None)` → **`return NotImplemented` for foreign**, and
**`__hash__ = hash(self._fltk_canonical_name)`**, with the both-operand-order / hash-equality rationale
and the explicit "naive sentinel" failure modes. Test #5 (§4 lines 361-368) adds both-operand-order +
matching/non-matching + `hash(proto)==hash(concrete)` assertions guarding exactly this.
Assessment: the reviewer's requested fix is incorporated verbatim, source-accurate. Resolved.
Residual (not blocking, not raised by this reviewer): "EXACT shape" is in mild tension with the bridge's
same-type fast-path `self.name == other.name` (`gsm2tree.py:121`) — a plain `_ProtocolLabelMember`
sentinel has no `.name`. The design hedges by writing "same-type fast-path" generically (line 217), not
the literal `.name` line, and for a plain class the same-type path is redundant with the canonical-name
path. Caught at first sentinel-vs-sentinel test; low risk. Noted, not a REWORK trigger.

### design-2 — Rust `Span.kind` getter: "exactly like UNKNOWN_SPAN_CACHE" is the wrong import direction; acyclicity invariant was unstated
Claim: §2.2 framed the getter as identical to `UNKNOWN_SPAN_CACHE`, but that cache is
generated-Python → `fltk._native`; this getter is the inverse (`fltk._native` → pure-Python
`terminalsrc`). No cycle today, but the load-bearing invariant ("`terminalsrc` must not import
`fltk._native`") was unrecorded. Consequence: latent — a future `terminalsrc` native import turns the
cached cross-direction import into a deadlock at first `Span.kind` access. Low-now/latent should-fix.
Source: `terminalsrc.py:1-4` imports only `bisect, re, dataclasses, typing` — no `fltk._native`;
`UNKNOWN_SPAN_CACHE` direction per `cst_fegen.rs:158`. Confirmed.
Disposition (revised design): §2.2 lines 154-168 now read "**same `GILOnceCell` pattern** ... but in the
**opposite import direction**", spell out both directions, and add "**Acyclicity invariant (load-bearing,
must hold): `terminalsrc` must never import `fltk._native`.**" with the verified-at-design-time note and
the Rust-`#[pyclass] SpanKind` fallback retained as escape hatch.
Assessment: reframed exactly as requested; invariant now explicit. Resolved.

### design-3 — `Span.kind` `compare=False, hash=False`: state as REQUIRED, not "defensive"
Claim: wording understated necessity; excluding `kind` from compare/hash is mandatory to preserve the
"sourceless sentinel == source-bearing span at same position" invariant, not optional polish. Consequence:
negligible runtime (constant), but a future "tidy" edit could fold the field back into compare/hash.
Wording-accuracy note.
Source: `_source` is `compare=False, hash=False` at `terminalsrc.py:13`; mirrored in `src/span.rs:51-53`.
Confirmed.
Disposition (revised design): §2.1 lines 130-137 now state "`compare=False, hash=False` is **REQUIRED**,
not defensive polish" with the invariant rationale and the "keep it OUT of the compared set permanently"
directive.
Assessment: wording corrected as requested. Resolved.

### design-4 — (verification note, non-blocking) Option-A structural-mismatch claim confirmed against source
Claim: protocol `Label` stays a plain class (not `enum.Enum`), so adding an `object`-typed value preserves
the `test_boundary_probe_documents_label_mismatch` nominal mismatch. Verified by reviewer against
`test_cst_protocol.py`. No defect.
Disposition (revised design): §2.3c lines 230-234 + §3 + test #9 (§4 line 383-385) retain the plain-class /
`object`-type framing and the structural-mismatch test.
Assessment: verification note; design consistent. No action needed.

### design-5 — (verification note, non-blocking) "no eager concrete-backend import" test must whitelist `terminalsrc`
Claim: test #4 must assert absence of `fltk_cst` AND `fltk._native` specifically, not an over-strict
"enum+typing only" allowlist that would false-fail on the already-imported `terminalsrc`. Verified;
prevents a test-author mis-implementation.
Disposition (revised design): test #4 (§4 lines 353-360) now asserts `"fltk.fegen.fltk_cst" not in
sys.modules` AND `"fltk._native" not in sys.modules`, and explicitly warns against the over-strict
allowlist, noting `terminalsrc` presence is EXPECTED.
Assessment: verification note; design internally consistent and incorporates the caveat. No action needed.

## Disputed items

None. All five findings are should-fix / internal-accuracy / verification notes (each reviewer
consequence is "silent AC failure on the Label axis" (design-1, scoped to AC 6/7/10, not a Shape-1
blocker), "latent cross-language cycle" (design-2), or wording/verification (design-3/4/5)). None is a
round-1 blocker; the revised design resolves or already satisfies each against source.

## Approved

5 findings: design-1/2/3 resolved by revised design text verified against source (`gsm2tree.py:100-132`,
`terminalsrc.py:1-13`, `src/span.rs:51-53`); design-4/5 verification notes already satisfied by the design.
Coverage check (notes "Coverage / scope check", lines 124-140): Shapes 1+2 reproduced and empirically
pyright-clean on real Protocol classes (closes the probe's dataclass-only gap); AC 8/8a/11 (test #1, two
structurally different traversals), AC 12 (test #6, three-enum-class incl. Span axis collapsed to shared
`SpanKind.SPAN`), AC 6/7/10 (sentinel bridge), AC 1-5/9 (`fltk2gsm.py` clean + behavior-equiv) all mapped.
Rejected approaches (accessor / runtime_checkable / TypeIs-primary) all honored, none reintroduced; the
stale `notes-design-user.md` "COMMITTED MECHANISM: TypeIs" is correctly overridden by the LOCKED
requirements + probe. Five production changes map 1:1 to requirements; no bonus features, no premature
abstraction. Both formerly-open questions (`protocol-label-type-change` → Option A mandated by
requirements; Rust `Span` discriminant bridging → shared `SpanKind.SPAN`) resolved in-design, no user
escalation owed. No `scope-N` deferral.

---

## Verdict: APPROVED

All five reviewer findings resolved or already satisfied in the revised `design.md`, each verified
against source. design-1 (sentinel bridge incl. `NotImplemented` + canonical-name `__hash__`) and
design-2 (Rust `Span.kind` opposite-import-direction acyclicity invariant) — the two real should-fix
items — are now pinned in the design; design-3 wording corrected; design-4/5 verification notes
satisfied. No disputed items, no blocker, no scope omission. The mechanism is empirically grounded
(probe), Option A is the requirements-mandated path, and the Rust `Span` bridging is resolved.
