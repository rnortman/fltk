# Slop pre-pass — base 49e9701 → HEAD 486406d

Scope: `fltk/`, `src/`, `tests/`. Docs-only paths excluded.

---

## slop-1

**File:** `fltk/fegen/gsm2parser.py:133–135`

**Quote:**
```python
# The registry's SourceText entry stays pointed at the `span` module (§2.4) so it drives only the agnostic
# annotation surface, never this runtime construction.
```

**What's wrong:** Factually incorrect. `context.py` changed the SourceText registry entry from `fltk.fegen.pyrt.span` to `fltk.fegen.pyrt.terminalsrc` in this same diff. The comment describes the pre-change state as if it were still true.

**Consequence:** A reviewer checking whether the `MethodAccess` workaround is justified reads that the registry "stays pointed at `span`" — but it now points at `terminalsrc`, the same target `MethodAccess` uses. The stated justification for the code structure is wrong, which will confuse anyone auditing this path.

**Fix:** Change the comment to reflect the actual post-change state: SourceText registry entry now points at `terminalsrc`, so `MethodAccess` is used to make the runtime construction call site explicit rather than relying on registry-driven indirection.

---

## slop-2

**File:** `fltk/plumbing.py:125–128`

**Quote:**
```python
# The committed parsers import `fltk.fegen.pyrt.span` only under
# TYPE_CHECKING (§2.2), so the eager-annotation side effect that used to resolve
# `span.Span` at exec time is gone
```

**What's wrong:** Factually incorrect. The committed parsers (e.g. `fltk_parser.py`) no longer import `fltk.fegen.pyrt.span` anywhere — not even under `TYPE_CHECKING`. They import `fltk.fegen.pyrt.terminalsrc` and annotate with `terminalsrc.Span`. The "only under TYPE_CHECKING" claim describes an intermediate state that was superseded.

**Consequence:** The stated reason for prepending `from __future__ import annotations` to the exec'd parser is wrong. A future maintainer asking "why is this future-import here?" gets a misleading answer that names a module that has been completely removed from committed parsers.

**Fix:** Update the comment to say the exec'd parser uses lazy annotations because its span annotations reference `fltk.fegen.pyrt.terminalsrc.Span` as a string, and evaluating them eagerly at exec time would require `terminalsrc` to already be bound in the exec'd module's globals (it is, but lazy is safer and consistent).

---

## slop-3

**File:** `fltk/fegen/genparser.py:111–113`

**Quote:**
```python
# never touches span.py's process-wide native-span probe (and its warning), in any
# environment (§2.2/D3.3).
```

**What's wrong:** "(and its warning)" refers to the `warnings.warn(...)` call in `span.py` that was **removed** in this same diff. There is no longer a warning to touch; the comment is stale from the moment it was written.

**Consequence:** A reader checking `span.py` for the referenced warning finds a comment that says "fall back silently" instead. The genparser comment now implies a behavior that does not exist, creating confusion about what property is being guaranteed.

**Fix:** Remove "(and its warning)"; keep the rest of the sentence.

---

## slop-4

**File:** `fltk/unparse/pyrt.py:74–75`

**Quote:**
```python
native = sys.modules.get("fltk._native")
return native is not None and isinstance(obj, native.Span)
```

**What's wrong:** No guard against `AttributeError` if `fltk._native` is loaded but lacks a `Span` attribute. The codebase already knows this scenario exists: `_rust_available = hasattr(_fltk_native, "Span")` appears in multiple test files precisely because a built `fltk._native` may not expose `Span` (e.g. an older or partial build). If `native` is a real module but has no `Span`, `native.Span` raises `AttributeError` instead of returning `False`.

**Consequence:** `is_span` — which is called in every generated unparser's span-child dispatch — raises an uncaught `AttributeError` in a mismatched-build environment, turning a graceful "no native span" into a hard crash of the entire unparser.

**Fix:** Use `getattr(native, "Span", None)` and guard: `native_span_cls = getattr(native, "Span", None); return native_span_cls is not None and isinstance(obj, native_span_cls)`.

---

## slop-5

**File:** Multiple production files — representative samples below

**Quote (gsm2parser.py ~line 46–52):**
```python
# Parser span annotations use a concrete pure-Python terminalsrc.Span (delta D3.3,
# "Concept A").  The generated Python parser unconditionally constructs and returns
# terminalsrc.Span (§2.1), so its invariant `ApplyResult[int, Span]` terminal-consume
# returns are annotated with that concrete type.  Annotating them with the shared
# agnostic registry `Span` (`get_parser_types()` above; that entry now drives the
# cross-backend CST/protocol surface, D3.4/D3.5) would be an invariant mismatch ...
```

Also: `gsm2tree.py` (8 occurrences of `D3.x`/`§2.x`), `genparser.py` (3), `context.py`, `gsm2unparser.py` (5), `span_protocol.py`.

**What's wrong:** Production code comments throughout the diff are annotated with opaque design-document references ("delta D3.3", "Concept A", "§2.1", "§2.4", "D3.4/D3.5", "increment-5", "R2"). These are internal shorthand from the ADR session; they carry no meaning to a reader without the design documents in hand. The comment blocks read as implementation-session notes that were never converted to self-contained explanations.

**Consequence:** The code reads as a design diary rather than maintained source. A future maintainer encountering "Concept A" or "delta D3.3" has no way to understand the intent without hunting the ADR, and the ADR itself may change or be superseded. The volume of such comments (18+ occurrences across 6 production files) is the defining LLM-composition tell in this diff.

**Fix:** Remove or rewrite these references. Where the rationale is worth preserving, state it in plain terms — e.g., "the Python parser always constructs `terminalsrc.Span`, so annotating it with `terminalsrc.Span` rather than the protocol avoids a type-mismatch without a cast." Design-doc section numbers belong in the ADR, not in the implementation.
