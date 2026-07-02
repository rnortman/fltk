# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/01/01-spanprotocol-native-linecol/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 1 finding.

## Findings walk

### design-1 — Fixed

Claim: the stub-stability guard as originally specified (native-free class-body text + try-enclosed
native imports) has a joint gap — a name bound by a legal try-enclosed `fltk._native` import and
referenced inside a protocol class body passes both checks. Consequence: the exact regression the
guard exists to catch (protocol structural surface becoming native-dependent, making generated-
pipeline consumers' pyright behavior stub-sensitive) lands with all tests green, satisfying
request.md's load-bearing guard constraint in letter only.

Premise verified against source: `fltk/fegen/pyrt/span_protocol.py:120` contains
`from fltk._native import Span as _RustSpan` inside the try-block (119-124), exactly the alias
pattern the evasion extends. The alias name contains no `_native` substring, so the original
substring check misses it; the import is try-enclosed and not under `TYPE_CHECKING`, so the
placement check passes. The evasion also works at runtime with the extension present, supporting
the reviewer's "plausible accidental edit" framing. Finding is sound with real consequence —
should-fix severity (guard-integrity gap in a not-yet-implemented test, but the guard is a
load-bearing request.md constraint).

Fix verified in `design.md`:
- § "New stub-stability guard" now carries the "Close the alias channel" bullet: collect the
  asname-or-name of every `fltk._native` import alias module-wide; assert none is referenced
  within either protocol class body — as an `ast.Name`, attribute-chain root, or identifier token
  inside a string annotation. Scoped to class bodies so the legitimate `AnySpan` use of
  `_RustSpan` below the classes stays legal. This matches the reviewer's suggested fix and closes
  the described channel by name resolution rather than substring matching.
- Test plan item 2 updated in step: "no native-import-bound alias referenced in either class
  body" is listed among the guard's assertions.

Assessment: fix addresses the consequence at the named section; both claimed edits present and
mutually consistent. Accept.

## Disputed items

None.

## Approved

1 finding: 1 Fixed verified.

---

## Verdict: APPROVED

The sole finding's disposition is verified against the design doc and source. No disputes.
