# Dispositions — pre-pass review (round 1)

Base: `49e9701` · Pre-fix HEAD: `486406d`
Notes: `notes-prepass-slop.md` (5 findings), `notes-prepass-scope.md` (no findings).

---

## slop-1
- Disposition: Fixed
- Action: `fltk/fegen/gsm2parser.py` (`_source_text` init comment, ~:130-135). The comment
  claimed "The registry's SourceText entry stays pointed at the `span` module (§2.4) so it drives
  only the agnostic annotation surface." Both halves were false: increment 14 (D3.2) repointed the
  SourceText registry entry to `terminalsrc` (verified in this same file at the `register_type`
  call ~:101-106 and in `context.py:128-137`), and the `_source_text` field carries no annotation
  for any registry entry to drive (it is set via the constructor init-list as a plain assignment).
  Rewrote the comment to state the SourceText registry entry now points at `terminalsrc` and that
  the explicit module-qualified `MethodAccess` call — not the registry — is what fixes the
  construction target. Also dropped the stale `(§2.4)` tag.
- Severity assessment: Misleading-comment only; no runtime effect. A reviewer auditing why the
  `MethodAccess` workaround exists would have been told the registry "stays at `span`" when it does
  not, obscuring the actual decoupling rationale.

## slop-2
- Disposition: Fixed
- Action: `fltk/plumbing.py` (exec'd-parser `from __future__` comment, ~:125-129). The comment said
  "The committed parsers import `fltk.fegen.pyrt.span` only under TYPE_CHECKING (§2.2), so the
  eager-annotation side effect that used to resolve `span.Span` at exec time is gone." This
  described a superseded intermediate state (increment 5, removed in increment 13): the committed
  parsers no longer import `fltk.fegen.pyrt.span` at all — they annotate with `terminalsrc.Span`
  and import `terminalsrc` at runtime (confirmed: no `span` import in `fltk_parser.py`). Rewrote to
  explain the exec'd parser's span annotations reference `terminalsrc.Span`, that `terminalsrc` is
  bound in `parser_globals`, and that `from __future__` keeps them lazy and consistent with the
  committed parsers. Dropped `(§2.2)`.
- Severity assessment: Misleading-comment only. A maintainer asking "why the future-import?" would
  have been pointed at a module the committed parsers no longer reference.

## slop-3
- Disposition: Fixed
- Action: `fltk/fegen/genparser.py` (lazy-annotation comment, ~:108-113). Removed the stale
  "(and its warning)" — the `warnings.warn(...)` was deleted from `span.py` in increment 1, so the
  parenthetical referenced a thing that no longer exists. Also folded in the slop-5 cleanup here
  (dropped `delta D3.3`, `§2.1`, `§2.2/D3.3`), keeping the plain rationale.
- Severity assessment: Misleading-comment only. The "(and its warning)" implied a guarantee about
  a warning that has been removed.

## slop-4
- Disposition: Fixed
- Action: `fltk/unparse/pyrt.py:61-76` (`is_span`). Hardened the native-span branch to resolve
  `Span` defensively: `native_span = getattr(sys.modules.get("fltk._native"), "Span", None)` then
  `return native_span is not None and isinstance(obj, native_span)`. Added a docstring note
  explaining the namespace-package case.
- Severity assessment: Real, low-probability crash. `fltk/_native/` is a stub-only directory
  (`__init__.pyi`, no compiled module — verified by `ls`), so in a pure-Python build `import
  fltk._native` succeeds as a *namespace package* lacking `Span`; this is exactly why test modules
  guard with `_rust_available = hasattr(_fltk_native, "Span")` (`tests/test_error_formatter.py:13`,
  `fltk/fegen/pyrt/test_span_protocol_assignability.py:28`). Once any code (e.g. `span.py`'s probe)
  has left that name-less namespace package in `sys.modules`, the old `native.Span` access raised
  `AttributeError` in `is_span` — on every generated unparser's span-child dispatch hot path,
  turning a graceful "no native span" into a hard unparser crash. The pre-existing sibling
  `gsm2tree.py:_get_native_span_type()` shares the same latent gap but is out of this finding's
  scope (untouched pre-existing code); not expanded here.

## slop-5
- Disposition: Fixed
- Action: Rewrote the design-doc-reference comments this diff introduced/modified so each is
  self-contained, removing the opaque internal shorthand (`§N`, `DN.N`, `delta D...`, `"Concept A"`,
  `R2`, `increment-N`) and stating the rationale in plain terms. Sites edited:
  `fltk/fegen/gsm2parser.py` (parser-span-annotation block ~:48-55, SourceText block ~:96, init
  comment ~:130, `_make_span_expr` docstring ~:303); `fltk/fegen/genparser.py` (~:108, folded with
  slop-3); `fltk/iir/context.py` (Span-entry ~:117, SourceText-entry ~:132); `fltk/unparse/
  gsm2unparser.py` (~:329, ~:386, ~:1034, ~:1136, imports-assembly ~:1836); `fltk/fegen/pyrt/
  span_protocol.py` (TYPE_CHECKING `Self` note ~:9, `merge` docstring ~:71, `TODO` comment ~:90 —
  TODO slug kept, only the `(delta D5.2)` tag dropped); `fltk/fegen/gsm2tree.py` (~:196, ~:730);
  `fltk/fegen/gsm2tree_rs.py` (~:329). All are generator-source Python comments (not strings
  emitted into generated artifacts), so no regeneration or committed-artifact drift results.
  Scope: only references *introduced or modified by this diff* (49e9701..486406d). Pre-existing
  earlier-ADR references left untouched as out of scope — e.g. `gsm2tree.py`'s mutator/equality
  `§2.2`/`§2.4`/`§3` and `"probe D4"` (`:893` at base, from commit `1f5ad7a`), and
  `gsm2tree_rs.py`'s lock-discipline `§2.3`/`§1`/`§2.8`.
- Severity assessment: Maintainability/readability. The shorthand is unresolvable without the ADR
  draft + implementation log in hand and rots as those docs are superseded; no runtime effect.

---

Verification: `make check` GREEN (`check: all steps passed (check-ci + cargo-deny)`) — lint,
format-check, pyright, full pytest, all cargo lanes, cargo-deny. Targeted: `is_span` guard tests,
`TestUnparsing`/`TestIntegration` round-trips, `test_python_parser_span_backend`,
`test_span_protocol_assignability` all pass. No hybrid path reintroduced; the Python pipeline still
imports no Rust (the `is_span` native branch resolves lazily via `sys.modules`, unchanged in intent).
