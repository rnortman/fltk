# Judge verdict — pre-pass (slop + scope)

Phase: pre-pass. Base 49e9701..HEAD ab38ec7 (dispositions applied in `ab38ec7`; slop review ran against pre-fix HEAD 486406d). Round 1.
Notes: `notes-prepass-slop.md` (5 findings), `notes-prepass-scope.md` (no findings). All 5 dispositioned **Fixed**.
Authoritative ground truth: `design-delta-python-rust-isolation.md` (supersedes original `design.md` §1.4/§2.4/§2.5/§2.6b/§5).

## Added TODOs walk

No finding was dispositioned TODO. One TODO comment exists in the base..HEAD range —
`TODO(spanprotocol-native-linecol)` (`span_protocol.py:87`) — but it was introduced by the delta
implementation (increment D3.1 / commit `152a075`), is design-blessed (delta D5.2/D8, with a matching
`TODO.md` entry), and is **not** a disposition in this pre-pass. The slop-5 fix only stripped its
`(delta D5.2)` shorthand tag and kept the slug. Nothing to score here.

## Other findings walk

### slop-1 — Fixed
Claim: `gsm2parser.py` `_source_text` comment said the registry's SourceText entry "stays pointed at the `span` module (§2.4)"; consequence is a reviewer auditing the `MethodAccess` workaround is told the wrong registry target.
Ground truth: delta D3.2 repoints SourceText → `terminalsrc` (`context.py:130-137`; `gsm2parser.py` re-registers to `terminalsrc`, comment :93-99). Confirmed `fltk_parser.py:17` constructs `terminalsrc.SourceText`. The old comment was factually wrong.
Fix (diff at `gsm2parser.py:130-136`): comment now states the SourceText registry entry "also points at `terminalsrc` now, but the `_source_text` field carries no annotation for it to drive… so this explicit module-qualified call is what fixes the construction target." Stale `(§2.4)` dropped.
Assessment: new comment matches the actual registry state and is not itself misleading. Accept.

### slop-2 — Fixed
Claim: `plumbing.py` future-import comment said committed parsers import `fltk.fegen.pyrt.span` "only under TYPE_CHECKING (§2.2)"; consequence is the future-import rationale names a module the committed parsers no longer reference.
Ground truth: `grep` confirms `fltk_parser.py` imports no `span` at all (delta D3.3 removed the dead `TYPE_CHECKING` span import); it imports `terminalsrc` and annotates `ApplyResult[int, terminalsrc.Span]` (`:83,:94`). Old comment wrong.
Fix (diff at `plumbing.py:125-129`): comment now says the exec'd parser annotates terminal spans with `terminalsrc.Span`, `terminalsrc` is bound in `parser_globals`, and lazy annotations match the committed parsers. This matches the slop reviewer's own suggested correction.
Assessment: accurate. Accept.

### slop-3 — Fixed
Claim: `genparser.py` comment's "(and its warning)" referred to the `warnings.warn(...)` removed from `span.py` this iteration; consequence is the comment implies a guarantee about a warning that no longer exists.
Ground truth: `grep` confirms `span.py` has no `warnings`/`warn(` references (removed in increment 1). Parenthetical was stale.
Fix (diff at `genparser.py:108-113`): "(and its warning)" removed; sentence now reads "never touches span.py's process-wide native-span probe in any environment." Also dropped the folded slop-5 tags (`delta D3.3`, `§2.1`, `§2.2/D3.3`).
Assessment: stale reference gone. Accept.

### slop-4 — Fixed (the one substantive finding)
Claim: `pyrt.py` `is_span` did `isinstance(obj, native.Span)` without guarding `AttributeError` when `fltk._native` is loaded but lacks `Span`; consequence is an uncaught `AttributeError` on every generated unparser's span-child dispatch in a mismatched/pure-Python build.
Ground truth: `fltk/_native/` is stub-only (`__init__.pyi`, no compiled module — confirmed by `ls`), so `import fltk._native` yields a namespace package without `Span`. The codebase already guards this exact case: `hasattr(_fltk_native, "Span")` in `test_span_protocol_assignability.py:28`, `test_error_formatter.py:13`, `test_span_protocol.py:16`. Real (if low-probability) crash; correctness/robustness.
Fix (diff at `pyrt.py:74-78`): `native_span = getattr(sys.modules.get("fltk._native"), "Span", None)` then `return native_span is not None and isinstance(obj, native_span)`. Handles all three states — absent (`getattr(None,…)`→None→False), present-without-Span (→None→False), present-with-Span (isinstance). Docstring note added explaining the namespace-package case.
Assessment: fix addresses the consequence at the named line and matches the reviewer's recommendation. Accept.

### slop-5 — Fixed (the volume finding)
Claim: production comments carry opaque ADR shorthand (`delta D3.3`, `Concept A`, `§2.1`, `D3.4/D3.5`, `increment-N`, `R2`); consequence is the code reads as a design diary unresolvable without the (mutable) ADR in hand.
Ground truth + scope check: a full sweep of `fltk/` production `.py` for the **delta** shorthand (`D[0-9].[0-9]`, `delta D`, `Concept [AB]`, `increment-N`, `R[0-9]`) now returns **zero** hits. The only remaining `§` references live in `gsm2tree.py` and `gsm2tree_rs.py` (mutator/equality `§2.2/§2.4/§3`, lock-discipline `§2.3/§1/§2.8`) — verified present at base `49e9701` (11 and 9 occurrences respectively) and **not** touched by this diff (no `+` shorthand lines added to those files). A diff-only slop review's scope is what the diff changed; pre-existing references in unmodified code are correctly out of scope, exactly as the disposition states. All this-diff sites the finding named (gsm2parser, genparser, context, gsm2unparser, span_protocol, gsm2tree imports, gsm2tree_rs) were rewritten to self-contained prose.
Assessment: in-scope shorthand fully removed; the scoping decision is sound. Accept.

## Disputed items

None.

## Approved

5 findings, all Fixed verified: 4 misleading-comment corrections (slop-1/2/3/5) accurate against the authoritative delta surface, 1 real robustness crash (slop-4) hardened. Scope reviewer: no findings.

---

## Verdict: APPROVED

All five dispositions acceptable. Comment corrections match the authoritative delta (SpanProtocol/terminalsrc registry split); the `is_span` `getattr` guard closes a real namespace-package `AttributeError`; slop-5's this-diff-only scoping is correct (remaining `§` refs are pre-existing in unmodified code).
