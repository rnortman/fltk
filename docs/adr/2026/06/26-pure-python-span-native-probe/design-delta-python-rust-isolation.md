# Design DELTA: Python pipeline never names Rust — agnostic span surface via `SpanProtocol`

Status: draft (delta)
Base design: `./design.md` (do NOT edit it; it is half-implemented)
Base commit of original design: `49e9701e927d1403065f902b99d54acd7c129e41`
Code state this delta targets: HEAD `88dd617` — original increments 1–10 committed (through §4.1
at `166737e`); original §2.5 regeneration NOT done; the original §2.1.1 `typing.cast` resolution
NOT implemented.
User directive (authoritative): `./notes-design-user-2.md`
Requirements: `./requirements.md` · User notes round 1: `./notes-design-user.md`

This is a **delta against `design.md`**. It supersedes specific sections (mapped in §D1) and keeps
the rest. It does **not** reintroduce the hybrid Python-parser/Rust-CST path (original §2.3/§4.1
stand).

---

## D0. Fact-find: confirming the user's hypothesis against the source

The user asked, before any proposal, whether pyright resolves the Python pipeline's span
annotations to `fltk._native`, and whether `span.py`'s `try/except` is the cause. Both are
**confirmed by direct pyright probes** against the real modules. The reality is in fact *worse*
than the user's framing.

**1. Pyright resolves the pipeline's `fltk.fegen.pyrt.span.Span` to `fltk._native.Span`.**
`span.py:8-14` re-exports under a `try/except`:

```python
try:
    from fltk._native import SourceText, Span, UnknownSpan   # type: ignore[assignment]
except Exception:
    from fltk.fegen.pyrt.terminalsrc import SourceText, Span, UnknownSpan
```

Pyright takes the `try`-branch binding as authoritative. The stub `fltk/_native/__init__.pyi` is
**committed** (`git ls-files` confirms) and always resolves, so pyright always binds
`span.Span → fltk._native.Span`. A probe constructing `ApplyResult[int, span.Span]` from a
`terminalsrc.Span` reports:

```
Type parameter "ResultType@ApplyResult" is invariant,
  but "fltk.fegen.pyrt.terminalsrc.Span" is not the same as "fltk._native.Span"
```

i.e. `span.Span` resolved to `fltk._native.Span`. **The user's hypothesis is correct**: the whole
pure-Python pipeline is type-checked as if it produces Rust spans. This is the same fact the
original implementation log records at increment 11 (the §2.5 blocker) — and it directly refutes
the original design's §1.4 claim that pyright sees "the union of both backends."

**2. The `try/except` makes pyright's result depend on whether `fltk._native` resolves.** Probe
run with the stub temporarily removed: `span.Span` resolves to **`Unknown`** (not the `except`
branch's `terminalsrc.Span` — pyright does *not* fall back), and the invariant-`ApplyResult` error
*disappears* (0 errors vs 1). So pyright produces **different** diagnostics and **different**
inferred types depending on `fltk._native` resolvability — exactly the property the user says must
not hold. The `try/except` reassignment is the mechanism (`span.py:8-14`); it gives pyright either
the Rust type (stub present) or `Unknown` (stub absent), never a stable pure-Python answer.

**Verdict: this is a real bug, not to be papered over.** The fix must make the Python pipeline's
static surface (a) never resolve to `fltk._native`, and (b) resolve identically regardless of
`fltk._native` resolvability.

---

## D1. What this delta supersedes / amends in `design.md`

| `design.md` section | Disposition |
|---|---|
| §1.4 ("backend-agnostic type name", claim pyright sees a union) | **Superseded.** Pyright sees `fltk._native.Span` (D0), not a union. The agnostic surface is carried by `SpanProtocol`, not by the `span.Span` selector name. |
| §2 thesis ("decouple construction from annotation"; keep frozen `span.Span` annotations) | **Amended.** Construction stays decoupled (terminalsrc). Annotations are *not* frozen at `span.Span`; they move to honest/agnostic types (D3). |
| §2.1.1 (wrap terminal-consume returns in `typing.cast("…span.Span", …)`) | **Superseded / deleted.** No cast. Root fix instead (D3.3). This is the "do not paper over it" the user demands. |
| §2.4 ("frozen public surface": registry stays `span`; CST/protocol/`.pyi` span annotations unchanged) | **Superseded.** Registry repoints to `SpanProtocol`; CST/protocol/`.pyi` span annotations change deliberately (D3.2, D3.4, D3.5, D7). |
| §2.5 (regen = parser files only; `typing.cast` makes pyright pass) | **Superseded.** Regen now also covers `*_cst.py` / `*_cst_protocol.py`; pyright passes because annotations are honest, not because of a cast (D3, D6). |
| §2.6(a) (dual-backend `is_span` runtime guard) | **Stands.** Already committed (increments 3). Unchanged. |
| §2.6(b) (unparser annotation lazy via `import fltk.fegen.pyrt.span` under `TYPE_CHECKING`) | **Amended.** The `TYPE_CHECKING` import becomes `span_protocol`; the annotation becomes `SpanProtocol` (D3.6). |
| §5 (cast chosen over honest annotations / variance / `SpanProtocol`) | **Superseded.** Honest annotations (parser) + `SpanProtocol` (CST surface) are chosen; the cast is rejected (D4). |

Everything else in `design.md` stands: §1.1–1.3, §2.1 (terminalsrc construction), §2.2 (no runtime
`span` import / warning removed — strengthened here), §2.3 (hybrid removed), §3 edge cases that
still apply, §4 tests (extended in D6), §4.1 (hybrid-test removal).

---

## D2. Root cause (restated at the level this delta fixes)

The original design fixed the **runtime** defect (pure-Python parser must construct
`terminalsrc.Span`, committed via §2.1) but kept the **static** annotation surface pointed at the
`span.py` selector / the explicit `… | fltk._native.Span` union (§2.4). D0 shows that surface
resolves to `fltk._native.Span` and is unstable. So two static defects remain:

1. **The parser** annotates its terminal spans `ApplyResult[int, span.Span]` (= `fltk._native.Span`)
   while constructing `terminalsrc.Span`. `ApplyResult.ResultType` is **invariant** (`memo.py:69`),
   so the regenerated parser fails pyright — the increment-11 blocker.
2. **The CST node / protocol / Rust `.pyi`** annotate the `span` field as the explicit union
   `fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span` and span-typed children as
   `fltk.fegen.pyrt.span.Span`. Both **name Rust** and resolve unstably.

Both are consequences of conflating two distinct concepts under one registry `Span` type
(`context.py:113-123`, `iir.Type.make(cname="Span")` — keyed solely by cname, so one shared
registry entry drives parser *and* CST *and* unparser annotations):

- **Concept A — the concrete pure-Python parser's span**: what the parser constructs and returns =
  `terminalsrc.Span`.
- **Concept B — the agnostic CST span contract**: what CST nodes expose to consumers, satisfied by
  *both* `terminalsrc.Span` (config 1) and `fltk._native.Span` (config 2).

This delta separates them.

---

## D3. Proposed architecture — a variance-forced split

> **Parser surface → Concept A → honest `terminalsrc.Span` / `terminalsrc.SourceText`** (the user's
> direction (b)).
> **CST node + protocol + Rust `.pyi` span field and span-typed children → Concept B →
> `fltk.fegen.pyrt.span_protocol.SpanProtocol`** (the user's direction (a)).

Each surface gets the type its variance constraints *force* (justified in D4). Neither direction
alone works everywhere; both are used, each where it is correct. The shared agnostic name across
protocol + both concrete backends becomes `SpanProtocol` — a single pure-Python name that names
neither backend and resolves identically with or without the native stub.

### D3.1 Root-fix `SpanProtocol` so concrete spans are actually assignable to it (`span_protocol.py`)

`SpanProtocol` as shipped (`span_protocol.py:9-86`) is **not** statically assignable from a concrete
span *value*. Pyright probes (cases A/B/D) reject `x: SpanProtocol = terminalsrc.Span(...)` and
`x: SpanProtocol = native_span` and `def f() -> SpanProtocol: return terminalsrc.Span(...)` with:

```
"merge" is an incompatible type
  Type "(other: Span) -> Span" is not assignable to type "(other: SpanProtocol) -> SpanProtocol"
    Parameter 1: type "SpanProtocol" is incompatible with type "Span"
```

`merge`/`intersect` declare `other: SpanProtocol` (a *wider* param than the concrete `Span`), which
is **contravariantly** incompatible — so `terminalsrc.Span` is not a structural subtype of
`SpanProtocol`. (Today this is masked: `SpanProtocol` is `@runtime_checkable` and the cross-backend
tests use runtime `isinstance`, which checks only attribute *presence*, not signatures. No
pyright-checked code currently assigns a concrete span into a `SpanProtocol` slot, so the gap is
latent.)

Two changes make `SpanProtocol` the usable agnostic span type. Both are **compatible refinements**
satisfied by both backends *at runtime* (and statically by `terminalsrc.Span`); both are *more*
correct than the status quo:

1. **Type `merge`/`intersect` with `Self`** (`typing_extensions.Self`; the project targets 3.10, so
   not `typing.Self`):

   ```python
   def merge(self, other: Self) -> Self: ...
   def intersect(self, other: Self) -> Self: ...
   ```

   Verified by pyright: with this, **`terminalsrc.Span` values** are assignable to a
   `SpanProtocol`-typed variable / parameter / return / dataclass field. **Native `fltk._native.Span`
   is *not* statically assignable** — its `line_col()` / `line_col_or_raise()` return the native
   `LineColPos`, a distinct nominal class from the protocol's `terminalsrc.LineColPos`
   (`span_protocol.py:6,67-79` vs `_native/__init__.pyi:67-68`), and the `Self` retyping does nothing
   to close that gap. Native conforms instead by `.pyi` *declaration* + runtime `isinstance` (D5.2);
   the residual static gap is tracked as `TODO(spanprotocol-native-linecol)` (D8). The `Self` retyping
   is also semantically *more* honest — `terminalsrc.Span.merge` raises at runtime when handed a
   different-source span, so "merge only with your own backend's span" (`Self`) is the true
   contract, not "merge with any `SpanProtocol`."

2. **Add the `kind` discriminant** (read-only property), required by Shape-2 match dispatch (D3.4
   detail):

   ```python
   @property
   def kind(self) -> typing.Literal[SpanKind.SPAN]: ...
   ```

   Both backends already expose `kind: Literal[SpanKind.SPAN]` (`terminalsrc.py:58`,
   `_native/__init__.pyi:70-75`), so adding it to the protocol breaks no conformance.

`SpanProtocol`'s body imports only `terminalsrc` (`SpanKind`, `LineColPos`); it does **not** name
`fltk._native`. (The module's separate `AnySpan` symbol does probe native at `:89-94`; it is a
standalone tested utility, *not* referenced by the pipeline — see D5.4.)

### D3.2 Repoint the type registry (`context.py`)

- **`Span` registration** (`context.py:113-123`): change module/name from
  `("fltk","fegen","pyrt","span") / "Span"` to `("fltk","fegen","pyrt","span_protocol") / "SpanProtocol"`.
  This single repoint flips every *registry-driven* span annotation — concrete CST span-typed
  children (`gsm2tree.py:88` path), protocol span-typed children (`:680` path), and the unparser's
  `_count_newlines` span param (`gsm2unparser.py:87` path) — to `SpanProtocol` automatically.
- **`SourceText` registration** (**TWO sites — both must move together**): `SourceText`
  (`iir.Type.make(cname="SourceText")`) is registered at `context.py:125-132` **and**
  re-registered for the *same key* at `gsm2parser.py:78-84` (`ParserGenerator.__init__`). Today both
  point at `("fltk","fegen","pyrt","span")`, so the second is a benign idempotent re-registration.
  Repoint **both** to `("fltk","fegen","pyrt","terminalsrc")` — or delete the `gsm2parser.py:78-84`
  re-registration entirely, since `context` now supplies the terminalsrc-keyed entry and the parser's
  construction sites no longer flow `SourceText` through the registry (committed §2.1). **Repointing
  only `context.py` and leaving `gsm2parser.py:78-84` at `span` is a hard crash**: the two `TypeInfo`s
  then differ for one key, and `ParserGenerator.__init__` raises
  `ValueError("Conflicting type registration")` (`context.py:19-25`). The order makes this certain —
  `genparser.py:83` calls `create_default_context()` (which registers `SourceText`→terminalsrc via
  `_register_builtin_types`) *before* constructing `ParserGenerator` (which would re-register
  →span) — so a literal "context only" edit breaks **all** Python-parser generation and the D6 regen
  could not even run. `SourceText` is used only by the parser (`_source_text` field); making it honest
  removes another selector reference. (No CST/protocol annotates `SourceText`, so no conformance
  impact.)

### D3.3 Parser keeps a concrete `terminalsrc.Span` annotation; the cast is eliminated (`gsm2parser.py`, `context.py`)

Because D3.2 points the shared `Span` registry entry at `SpanProtocol`, the parser — which must keep
**Concept A** for its invariant `ApplyResult[int, Span]` returns — needs a *distinct* concrete span
type:

- Introduce a parser-local concrete span type (e.g. `iir.Type.make(cname="TerminalSpanConcrete")`)
  registered to `("fltk","fegen","pyrt","terminalsrc") / "Span"`, registered in
  `ParserGenerator.__init__` alongside the other parser-local registrations (`gsm2parser.py:55-85`),
  and use it as `self.TerminalSpanType` for every parser **annotation**: the `consume_literal`/
  `consume_regex` `ApplyResult` result type (`:153`), the `span_var` locals (`:173`, `:221`), and
  the Literal/Regex item return types (`:355`, `:370`, `:665-667`). `get_parser_types()`
  (`context.py:60-74`) is called only by `gsm2parser`, so it may instead return the terminalsrc-keyed
  type directly — implementer's choice.
- Runtime construction is already terminalsrc (committed §2.1: `_make_span_expr` emits
  `fltk.fegen.pyrt.terminalsrc.Span.with_source(...)`; `_source_text` emits
  `terminalsrc.SourceText(...)`). No construction change.

Result: `consume_literal`/`consume_regex` return `ApplyResult[int, terminalsrc.Span]` and *construct*
`terminalsrc.Span` — exact-match, invariance trivially satisfied, **no `typing.cast`** (pyright probe
confirms 0 errors). The parser-produced `terminalsrc.Span` then flows into the `SpanProtocol`-typed
CST setters/field; `terminalsrc.Span` is assignable to `SpanProtocol` (after D3.1), so that boundary
also needs no cast (pyright-confirmed: `node.span = terminalsrc_span`, `node.append_x(terminalsrc_span)`,
`node.children.append((None, terminalsrc_span))` all clean).

The parser therefore references **no** span selector and **no** `SpanProtocol`: its annotations are
`terminalsrc.Span` / `terminalsrc.SourceText` (runtime-imported already, for construction) plus CST
node types. The §2.2 `TYPE_CHECKING import fltk.fegen.pyrt.span` (`genparser.py`, committed
increment 5) is now **dead** and is removed; nothing replaces it. `from __future__ import annotations`
may remain (harmless; avoids churn).

### D3.4 Concrete CST + protocol span field/children → `SpanProtocol` (`gsm2tree.py`)

- **`span` field** (concrete `gsm2tree.py:269`, protocol `:900`): replace the hardcoded
  `fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span` with
  `fltk.fegen.pyrt.span_protocol.SpanProtocol`. The concrete dataclass keeps its default
  `= fltk.fegen.pyrt.terminalsrc.UnknownSpan` (a `terminalsrc.Span`, assignable to `SpanProtocol`
  after D3.1 — pyright-confirmed).
- **Span-typed children** (the `child_annotation` union members, `children` list element, and the
  `append_*`/`children_*`/`child_*`/`maybe_*`/`insert`/`replace_at`/`extend_*` signatures): these
  flow from the registry (D3.2), so they become `SpanProtocol` automatically.
- **Imports** (`gsm2tree.py:190-202` concrete, `:735-744` protocol): drop the `TYPE_CHECKING`
  `import fltk.fegen.pyrt.span` and `import fltk._native`; add `import fltk.fegen.pyrt.span_protocol`.
  After this, generated CST/protocol modules name **neither** `fltk._native` **nor** the `span`
  selector — so pyright analyzing them resolves no native symbol and is stable regardless of the
  stub (the strongest form of the user's requirement).
- **`_protocol_span_class`** (the kind-only `cst.Span` marker, `:975-988`) is **unchanged**: it still
  provides `proto_cst.Span.kind` (the *value* in `case proto_cst.Span.kind:`). The *subject*
  `child.kind` typechecks because the child union's span member is now `SpanProtocol`, which carries
  `kind` (D3.1). Shape-2 dispatch is pyright-verified end-to-end (probe: `match child.kind: case
  SpanKind.SPAN` over a union containing the `SpanProtocol` arm — clean).
- **Runtime mutator validation** (`_check_child_type_for_mutators`, `_get_native_span_type()`,
  `_MUTATOR_ALLOWED_CHILD_TYPES`) is **unchanged**: it is runtime `isinstance` against concrete
  `terminalsrc.Span` + the lazily-resolved native type, independent of the static annotation.

### D3.5 Rust `.pyi` span field/children → `SpanProtocol` (`gsm2tree_rs.py`)

The Rust concrete CST must satisfy the same protocol. Today `gsm2tree_rs.py:357-358` annotates the
`span` field as the exact protocol union, with the comment "invariant attribute; narrower would fail
conformance" — i.e. the `.pyi` span positions are deliberately *identical* to the protocol's. When
the protocol moves to `SpanProtocol`, the `.pyi` follows:

- `span` field (`:358`) and span-typed children → `fltk.fegen.pyrt.span_protocol.SpanProtocol`.
- Imports (`:329-331`): add `import fltk.fegen.pyrt.span_protocol`; drop the now-unused
  `import fltk._native` / `import fltk.fegen.pyrt.span` if nothing else in the stub references them.

This keeps the Rust node *classes* as Rust types (no class renames — CLAUDE.md), while the span
*positions* use the agnostic contract — which is exactly what lets a consumer swap config 1 ↔ 2.
The runtime span objects in a Rust CST remain `fltk._native.Span`; the `.pyi` annotates them
agnostically as `SpanProtocol`, the same way the Python concrete annotates its `terminalsrc.Span`
runtime objects as `SpanProtocol`.

### D3.6 Unparser annotation → `SpanProtocol` (`gsm2unparser.py`) — amends §2.6(b)

- The `_count_newlines(self, span: …)` annotation derives from the registry `Span` type
  (`gsm2unparser.py:87`), so it becomes `SpanProtocol` automatically (D3.2).
- The §2.6(b) `TYPE_CHECKING import fltk.fegen.pyrt.span` (committed increment 6, in the
  `generate_unparser` imports assembly) changes to `import fltk.fegen.pyrt.span_protocol`.
- The §2.6(a) dual-backend `is_span` **runtime guard stands** (committed increment 3) — it is the
  runtime mechanism and is unaffected; the registry/annotation change touches only the static
  surface. After this, the generated unparser names neither `fltk._native` nor the `span` selector.

### D3.7 What committed code stands unchanged

- `span.py` warning removal (increment 1) and its `try/except` selector — **stands**. `span.py`
  remains a standalone, tested "active-backend" utility; **after this delta nothing in the pipeline
  imports it** (runtime or `TYPE_CHECKING`), which is precisely the isolation the user demands.
- §2.1 terminalsrc construction (increment 4) — **stands** (only parser *annotations* change).
- §2.3 hybrid removal (increment 7) and §4.1 hybrid-test cleanup (increments 8–10) — **stand**. The
  hybrid path is **not** reintroduced.
- §2.6(a) `is_span` (increment 3) — **stands**.

---

## D4. Why this split — picking and justifying the directions

The user offered (a) `SpanProtocol` everywhere agnostic, and (b) Python annotations always resolve
to the Python span/CST. The correct answer is **both, partitioned by what the type system forces** —
verified with pyright probes, not asserted:

- **"(b) everywhere" is impossible for the cross-backend surface.** The protocol's `span` field and
  `children` are **invariant** shared slots (mutable attribute; `list` element). For the Python
  concrete (`terminalsrc.Span`) *and* the Rust concrete (`fltk._native.Span`) to both satisfy one
  protocol, those slots must be a *single shared name* the runtime objects of *both* backends
  satisfy. A backend-specific `terminalsrc.Span` cannot be that name: the Rust `.pyi` would then
  annotate native-span children as `terminalsrc.Span`, lying about the Rust backend and violating
  "the Rust backend must still get Rust types" (CLAUDE.md). So the shared slot **cannot** be a pure
  pure-Python concrete type.

- **"(a) everywhere" is impossible for the parser.** The parser's terminal-consume returns are
  `ApplyResult[int, X]`, and `ApplyResult.ResultType` is **invariant**. Constructing `terminalsrc.Span`
  yields `ApplyResult[int, terminalsrc.Span]`; annotating it `ApplyResult[int, SpanProtocol]` is the
  *exact same invariance failure* as the native case (`terminalsrc.Span` ≠ `SpanProtocol` under
  invariance) and would force a `typing.cast` — the very paper-over the user rejects. The only
  cast-free annotation for an invariant return whose value is constructed as `terminalsrc.Span` is
  `terminalsrc.Span` itself.

- **The shared agnostic slot must be `SpanProtocol`** (the only native-free type both runtime
  backends satisfy), which requires the D3.1 root-fix to be assignable from concrete spans. This is
  the user's direction (a), applied exactly where invariance + cross-backend conformance demand it.

- **The cast (original §2.1.1/§5) is rejected.** It is unnecessary once the parser is honest
  (`terminalsrc.Span` matches its construction) and once `SpanProtocol` is assignable from concrete
  spans (so the parser→CST boundary needs none). Removing it is the "fix at the root" the user asked
  for.

So the split is *forced*, not preferential: invariant single-backend return → concrete
`terminalsrc.Span`; invariant cross-backend slot → `SpanProtocol`.

---

## D5. Edge cases / failure modes (delta to original §3)

1. **Pyright stability across stub presence/absence (the user's R2).** Generated CST/protocol/parser/
   unparser modules name neither `fltk._native` nor `span`. `SpanProtocol` resolves through
   `span_protocol.py`'s `SpanProtocol` class, which depends only on `terminalsrc`. So pyright's
   inferred types and diagnostics on the *generated pipeline* are identical with or without the
   native stub. Covered by a new regression (D6).
2. **Native `fltk._native.Span` is not *statically* a `SpanProtocol` (pre-existing, contained).**
   `fltk._native.Span.line_col()` returns the native `LineColPos`, which is not assignable to
   `SpanProtocol`'s `terminalsrc.LineColPos` return (distinct nominal classes; pyright-confirmed).
   This does **not** block the design: the only place a span *value* is statically assigned into a
   `SpanProtocol` slot inside `make check`'s pyright scope (`fltk/`, `*.py`) is the **Python** parser
   feeding `terminalsrc.Span` (which *is* statically `SpanProtocol` after D3.1). The Rust `.pyi`
   only *declares* `span: SpanProtocol` (no value assignment); cross-backend consumer tests live in
   `tests/` (out of pyright scope) and read spans rather than assign native spans into `SpanProtocol`
   slots. Recorded as `TODO(spanprotocol-native-linecol)` (D8) — unifying `LineColPos` across
   backends is a separate concern, not required here.
3. **Shape-2 `.kind` dispatch stays backend-agnostic.** `child.kind` over a union whose span member
   is `SpanProtocol` typechecks (D3.1 `kind`), and `case proto_cst.Span.kind:` matches both backends'
   `SpanKind.SPAN`. `test_span_kind_narrows_*` and `TestCrossBackendDualShapeDispatch`
   (`tests/test_clean_protocol_consumer_api.py:560-720`) remain valid (D6).
4. **`span.py` selector and `span_protocol.AnySpan` still probe native — but outside the pipeline.**
   No generated parser/CST/protocol/unparser imports `span.py` or `span_protocol` at runtime (grep-
   confirmed); `error_formatter.py` runtime-imports `SpanProtocol`, but generated parsers do not
   import `error_formatter`. So the pipeline never triggers a native probe, even indirectly. `span.py`
   and `AnySpan` remain as tested standalone utilities (`tests/test_span_protocol.py`). See D8 for
   whether the user wants them purged too.
5. **`SourceText` annotation honesty.** `_source_text: terminalsrc.SourceText` (D3.2) matches its
   `terminalsrc.SourceText(...)` construction; no selector, no native.
6. **Regen drift now includes CST/protocol files.** Unlike original §2.5 (parser-only), the regen
   changes `*_cst.py` and `*_cst_protocol.py` too (span field/children → `SpanProtocol`, imports).
   `make gencode` → `make fix` must produce exactly these diffs and `make check` (ruff + pyright)
   must be clean. This is the deliberate annotation-surface change (D7).

---

## D6. Test plan (delta to original §4)

Original §4 tests stand except where they assert the old surface. Added/changed:

- **Pyright-stability regression (new, central to the user's R2).** Assert that running pyright over
  a representative generated parser+CST+protocol triad yields identical results with the
  `fltk/_native/__init__.pyi` stub present vs. absent — same inferred span types, same diagnostics.
  This is the test that fails today (D0: `span.Span` → `fltk._native.Span` vs `Unknown`) and passes
  after the delta. (Reuse the `tests/pyright_test_utils` harness already used by
  `test_clean_protocol_consumer_api.py`.)
- **No native / no selector in the generated pipeline (new, source-level).** Assert the committed
  generated parser/CST/protocol/unparser sources contain **no** reference to `fltk._native` and **no**
  module-level or `TYPE_CHECKING` `import fltk.fegen.pyrt.span` (selector); CST/protocol carry
  `import fltk.fegen.pyrt.span_protocol` under `TYPE_CHECKING`; the parser carries neither (it uses
  runtime `terminalsrc`).
- **Pre-existing union-surface tests must be retargeted (these pin the OLD surface the delta
  changes).** D3.4/D3.5 move the protocol and Rust-`.pyi` span surface off the union, so the
  prior-work suites that exist *specifically* to pin `terminalsrc.Span | fltk._native.Span` break and
  must be given an explicit disposition rather than left to fail:
  - `tests/test_gsm2tree_rs.py` — `test_imports_span_module` (`:1153`, asserts
    `import fltk.fegen.pyrt.span` in the `.pyi`), `test_imports_fltk_native` (`:1156`, asserts
    `import fltk._native`), and `test_span_annotation_exact_protocol_union` (`:1222`, asserts
    `span: …terminalsrc.Span | fltk._native.Span`): **retarget** to assert the `.pyi` imports
    `fltk.fegen.pyrt.span_protocol`, imports **neither** `fltk._native` **nor** the `span` selector,
    and annotates `span: …span_protocol.SpanProtocol` (D3.5). (`tests/` is outside `make check` pyright
    scope, but these run under pytest and would otherwise fail the suite.)
  - `fltk/fegen/test_cst_protocol.py:487-614` — the "§4 item 8 — Protocol span additive-widening"
    suite (`test_python_backend_consumer_still_type_checks`,
    `test_rust_backend_span_satisfies_widened_protocol`,
    `test_python_backend_uncasted_callsite_annotation_churn`) asserts the protocol `span` field *is*
    the widened union and that a `fltk._native.Span` value satisfies it. Its premise is removed by
    D3.4, and this file lives under `fltk/` (in `make check` pyright scope). **Rework** it into a
    `SpanProtocol`-conformance suite (a `terminalsrc.Span`-typed consumer reads `node.span` as
    `SpanProtocol`; native conforms by runtime `isinstance`, per D5.2) **or retire** it — the
    implementer states which, rather than silently dropping coverage.
- **`SpanProtocol` assignability (new, pins D3.1).** Pyright-assert (in-scope module) that
  `x: SpanProtocol = terminalsrc.Span(...)` and a `SpanProtocol`-typed dataclass field default
  `= terminalsrc.UnknownSpan` and a `-> SpanProtocol: return terminalsrc.Span(...)` all typecheck —
  i.e. the `Self`/`kind` refinement holds. Runtime: `isinstance(terminalsrc.Span(0,1), SpanProtocol)`
  and (native present) `isinstance(fltk._native.Span(0,1), SpanProtocol)` both `True`.
- **Parser determinism + cast-free (amends §4 "no runtime span import").** Keep the §2.1 determinism
  regression (`type(node.span) is terminalsrc.Span` with native present); add an assertion that the
  regenerated parser source contains **no** `typing.cast(` around the terminal-consume `ApplyResult`
  construction and annotates `ApplyResult[int, fltk.fegen.pyrt.terminalsrc.Span]`.
- **Cross-backend dispatch + `.kind` narrowing (retained).** `TestCrossBackendDualShapeDispatch`,
  `test_span_kind_narrows_rust_backend_span_children`, `test_rust_native_span_dispatches_via_match_case`
  stay green (config-1 Python CST + genuine config-2 `fegen_rust_cst.parser` Rust CST).
- **`span.py` selector + `AnySpan` preserved.** `tests/test_span_protocol.py` (selector,
  silent-fallback, `TestAnySpanPython`) stays green — `span.py`/`AnySpan` are unchanged standalone
  utilities.
- **Unparser round-trip (retained from §2.6).** Native-present round-trip via `is_span` still works.
- **Regen drift.** `make gencode` → `make fix` yields only the intended parser + CST + protocol
  diffs; `make check` clean (ruff/format **and** pyright) with no cast.

---

## D7. CLAUDE.md disposition: this is a deliberate, user-directed annotation-surface change

Per CLAUDE.md, the generated CST/parser/protocol/`.pyi` annotation surfaces are public API and must
not churn *incidentally*. This delta changes them — `span` field and span-typed children move from
`terminalsrc.Span | fltk._native.Span` / `fltk.fegen.pyrt.span.Span` to
`fltk.fegen.pyrt.span_protocol.SpanProtocol` — and that change is **deliberate, justified, and
user-directed** ("change all type annotations to the span protocol, and Pyright never sees anything
else"), satisfying CLAUDE.md's "called-out decision" bar:

- **No generated public symbol is renamed.** Node classes, accessors, labels, enums are untouched.
  Only the *span type name* in annotations changes.
- **Reads are unaffected.** Consumers who read `node.span`/child spans and call span methods see no
  change (`SpanProtocol` carries the full span API).
- **The only churn** is for a consumer who *pinned a concrete span type* (`fltk._native.Span` or
  `fltk.fegen.pyrt.span.Span`) on a value sourced from a CST accessor. Pinning `fltk._native.Span`
  on a pure-Python CST was the *bug* this work removes; the agnostic replacement is `SpanProtocol`,
  which the requirements mandate for swap-ability. Migration: annotate with `SpanProtocol` (or rely
  on inference). This is the intended public-API evolution, not an incidental side effect.
- **The parser's internal annotation change** (`span.Span` → `terminalsrc.Span`) is parser-internal:
  no consumer annotates `ApplyResult[int, span]`; the public entry points return CST node types.

---

## D8. Open questions (genuine user-judgment only)

1. **Should the now-pipeline-unused native probes be purged too?** After this delta, nothing in the
   Python pipeline imports `span.py` (the selector) or triggers `span_protocol.AnySpan`'s native
   probe. Both remain as standalone, tested public utilities (`tests/test_span_protocol.py`). The
   **pipeline-scoped** reading of the directive ("the Python pipeline never imports rust, even
   indirectly") is satisfied without touching them.

   **The choice turns on which reading of R2 the user wants — make it with the scope explicit.** R2
   has a second, broader clause: "Pyright should produce the same results when analyzing Python code
   whether the Rust backend is importable or not." Read **repo-wide**, that is **not** met under
   keep-both: `span.py:8-14` (`span.Span` flips `fltk._native.Span` ↔ `Unknown` with the stub) and
   `span_protocol.py:89-94` (`AnySpan` flips `Span | _RustSpan` ↔ `Span`) remain stub-sensitive and
   are inside `make check` pyright scope (`fltk/`). The *generated pipeline*
   (parser/CST/protocol/unparser) is stub-stable either way (D5.1); only these two standalone
   utilities are not.

   **Default (this delta): keep both** — they are public, tested, and out of the pipeline; the
   pipeline-scoped R2 is satisfied. If the user wants the broad, repo-wide R2 (no stub-sensitive
   pyright result *anywhere* in `fltk/`), the *selector concept* must be retired (delete `span.py`,
   drop `AnySpan`'s native arm) — a separate public-API removal requiring its own decision. This
   delta surfaces the tradeoff rather than deciding it.

A `TODO(spanprotocol-native-linecol)` is recorded (D5.2) for making `fltk._native.Span` *statically*
conform to `SpanProtocol` (unify `LineColPos` across backends). It is not a user-judgment question —
it is a contained, pre-existing technical gap that does not block this delta — so it is tracked as a
TODO rather than raised here.
