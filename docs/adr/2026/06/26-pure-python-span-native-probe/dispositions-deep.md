# Deep-review dispositions

Round 1. Base `49e9701e927d1403065f902b99d54acd7c129e41`, prior HEAD `ab38ec777920f4761f124e56b3cedc995acee46a`.
Reviewers: error-handling, correctness, security, test, reuse, quality, efficiency.

No `scope-*` reviewer in this set, so no scope-aggregate escalation question arose. `make check`
is green (lint, format-check, pyright, full pytest, all cargo lanes, cargo-deny) after the fixes.

---

## errhandling-1

- Disposition: TODO(span-selector-broken-native-diagnostic)
- Action: TODO.md entry `span-selector-broken-native-diagnostic` + `TODO(...)` comment at
  `fltk/fegen/pyrt/span.py:8` (the `try/except` selector). The finding is valid: `except Exception`
  swallows a present-but-broken native extension (ABI/OSError/SystemError), not just the expected
  absent-native `ImportError`, with no diagnostic.
- Severity assessment: A broken native `.so` silently degrades `span.Span` to the pure-Python type;
  the only signal is `test_span_protocol.py`'s identity assertion failing, so a production user can
  be confused why a "native" install runs pure-Python. Real but rare and non-corrupting.
- Why TODO not Fixed: (a) pre-existing breadth — this diff only removed `warnings.warn`, not the
  catch; (b) the right fix is genuinely debatable: narrowing to `except ImportError` trades selector
  robustness for diagnosability and would have to stay correct for the pure-Python namespace-package
  case (which raises `ImportError` for the missing `Span`), while log-and-fallback re-adds a
  diagnostic the user explicitly asked removed for the absent case; (c) the identical pattern in
  `span_protocol.py` (`AnySpan`) must move in lockstep — the error-handling reviewer flagged it for
  completeness. `span.py` is now out of the generated pipeline, so impact is confined to the
  standalone selector. A respond-mode behavioral change in a user-sensitive area is the wrong tool;
  the TODO surfaces it for a deliberate call.

## correctness (whole review)

- Disposition: No findings — nothing to action. Verified the reviewer's traced invariants match the
  source (registry split collision-free; construction registry-independent; `is_span` dual-backend;
  hybrid removal clean).

## security (whole review)

- Disposition: No findings — nothing to action. The change removes an `importlib.import_module`
  ACE sink (hybrid `_load_rust_cst_classes`); net surface reduction.

## test-1

- Disposition: Fixed
- Action: Added `test_native_present_unparse_round_trip` to
  `tests/test_python_parser_span_backend.py` — skips unless `fltk._native` importable, generates a
  Python parser+unparser, parses, asserts `type(cst.span) is terminalsrc.Span` AND round-trips
  `unparse_cst` → `render_doc` to the expected text, all in one native-present test.
- Severity assessment: Real. This is exactly the regression the design §4/D6 specified ("the case
  that raises `ValueError("Unparsing failed")` on the §2.1-only tree"). The properties were split
  across files with no native-present coupling; a reversion of `is_span` to probe-bound behavior
  would not be pinned by any single intent-documenting test. (In native-present CI the existing
  `TestUnparsing` would still fail, but the dedicated regression now makes the guard explicit.)

## test-2

- Disposition: Fixed
- Action: Parameterized `test_committed_protocol_source_names_no_native_no_selector` and
  `test_committed_cst_source_imports_no_native_no_selector`
  (`fltk/fegen/test_cst_protocol.py`) over ALL five committed protocol / concrete-CST modules
  (bootstrap, fltk, regex, toy, unparsefmt) via `ALL_PROTOCOL_MODULES` / `ALL_CONCRETE_CST_MODULES`,
  instead of only the `fltk_cst` pair.
- Severity assessment: Low (the generator is one code path and pyright over committed `fltk/` is the
  real gate), but the test claimed to "complete the coverage for the committed concrete-CST and
  protocol modules" while asserting on only two of ten files. Parameterizing makes the test honest
  and cheap; verified all 5 pairs pass.

## test-3

- Disposition: TODO(spanprotocol-native-linecol)
- Action: Augmented the existing `spanprotocol-native-linecol` TODO (TODO.md + the code comment at
  `fltk/fegen/pyrt/span_protocol.py:87`) with the explicit constraint that resolving it must not make
  `SpanProtocol`'s structural surface native-dependent without adding a stub-stability guard for the
  generated pipeline — because the source-level "names no native" tests do NOT cover transitive
  stub-sensitivity introduced via `span_protocol.py` itself.
- Severity assessment: Not a current defect — the reviewer concedes `AnySpan` is unused by the
  pipeline and `SpanProtocol` is stub-independent at HEAD, so the property holds and is correctly
  pinned. The risk is purely a FUTURE change (resolving the linecol TODO) silently breaking R2.
- Why TODO not Fixed: the differential pyright run D6 named was deliberately and reasonably rejected
  by the implementer (renaming the committed stub mid-test is repo-mutating and fragile; no
  precedent in the suite), and a clean structural guard is hard to write because `AnySpan`
  legitimately names native in the same module. The proportionate response is to bind the
  guard-requirement to the exact future change (the existing slug) that would open the hole.

## test-4

- Disposition: Fixed
- Action: Strengthened the concrete-CST check (in the test-2 parameterized rewrite) from an
  import-line-only check to a context-bounded one: every line containing `fltk._native` must be the
  runtime `sys.modules.get("fltk._native")` lookup. This catches a stray `fltk._native.Span`
  lazy-string annotation (no import line) that the old import-only check would miss; added a comment
  explaining the principled asymmetry with the protocol check.
- Severity assessment: Low-moderate. A generator regression emitting a native annotation as a
  `from __future__`-lazy string with no import would have passed the old CST test (caught only later
  by pyright). The new form closes that blind spot at the pytest level.

## reuse-1

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: Two ~15-line self-contained test fixtures (`_make_word_grammar` vs
  `_make_regex_grammar`) in different files; the drift risk on a `gsm` API change is shared by dozens
  of fixtures across the suite, not specific to this pair.
- Rationale: The reviewer's own suggested remedy — call `_make_regex_grammar` from the other file —
  means importing a private `_`-prefixed helper across test modules
  (`tests/test_regex_portability.py:47` → `tests/test_python_parser_span_backend.py`), which makes
  the test module non-self-contained and couples it to unrelated changes in another file's private
  API. The alternative (a new shared test-util module) is disproportionate for two tiny fixtures.
  Keeping per-module self-contained fixtures is the better, established pattern; the proposed dedup
  is a net negative for test isolation.

## reuse-2

- Disposition: TODO(unparser-source-helper)
- Action: TODO.md entry `unparser-source-helper` + `TODO(...)` comment at the duplication site
  (`fltk/unparse/test_is_span_guard.py`, `_generate_unparser_source`). The finding is valid: that
  helper re-implements `plumbing.generate_unparser`'s 7-step assembly (4 call sites) because plumbing
  exposes no pre-`exec` source.
- Severity assessment: Real maintainability/drift risk — a change to the unparser assembly list must
  be mirrored in both `plumbing.generate_unparser` and the test helper.
- Why TODO not Fixed: the clean fix is a production-code API change (split source-gen from `exec` in
  plumbing, used by both `generate_unparser` and `genunparser.py`) that is out of scope for a
  respond-mode patch and risks rippling through both assembly sites; deferred with a concrete,
  located plan.

## quality-1

- Disposition: Fixed
- Action: `fltk/fegen/gsm2parser.py:146` — changed the module-reference `VarByName`'s
  `typ=self.SourceTextType` (it names the `terminalsrc` MODULE, not the `SourceText` class) to
  `typ=iir.Type.make(cname="module")`, matching the module-VarByName convention used at 5 sites in
  `gsm2unparser.py`; added an explanatory comment. Verified via `make gencode` that emitted parser
  output is byte-identical (no committed-artifact drift) and `make check` (pyright) stays green.
- Severity assessment: Cosmetic/consistency — output was already correct (correctness reviewer
  confirmed), but the `typ` misrepresented the denotation and established a third constructor-call
  idiom. The fix removes the divergent pattern at zero output cost.

## quality-2

- Disposition: Won't-Do
- Action: No change to the protocol check's methodology (the explanatory asymmetry is now documented
  by the test-4 fix).
- Severity assessment: The reviewer wants the protocol check narrowed from full-text
  `"fltk._native" not in text` to a line-level import check, for symmetry with the CST check.
- Rationale: Narrowing would actively WEAKEN the protocol check and reintroduce the very blind spot
  test-4 closes. The protocol module legitimately contains ZERO `fltk._native` references (verified:
  grep count 0 across all five protocol files), so the strict full-text "appears nowhere" is both
  correct and the strongest check — it catches a stray native annotation string as well as an import.
  A line-level import check would silently pass a lazy-string `fltk._native.Span` annotation. The
  asymmetry with the CST check (which has one known runtime `sys.modules.get` reference and so uses a
  context-bounded check) is principled, not accidental, and is now commented. quality-2's false-
  positive scenario (a hand-added comment naming native) cannot occur in machine-generated output.

## quality-3

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: Three codegen sites emit `from __future__ import annotations` via different
  idioms — `genparser.py:113` (pygen text helper), `plumbing.py:130` and `gsm2unparser.py:1845`
  (raw AST, the latter with an explicit `asname=None`).
- Rationale: The divergence is stylistic-only across genuinely distinct generation paths
  (committed-file generation works in pygen-land; the two in-memory paths work in raw-AST-land), and
  `from __future__ import annotations` is a stable statement with no realistic churn. `asname=None`
  vs omitted is behaviorally identical (the AST default). A shared helper would have to bridge the
  pygen/raw-AST representation boundary, introducing cross-module utility coupling among three
  independent generator entry points for zero behavioral benefit — disproportionate to the nit.

## efficiency-1

- Disposition: Won't-Do
- Action: No change to `fltk/unparse/pyrt.py:77` (`is_span`).
- Severity assessment: Per the reviewer's own measurement, sub-microsecond per non-`terminalsrc.Span`
  child (a `sys.modules.get` + `getattr` + `isinstance`), dominated by Doc construction/rendering —
  "a minor regression, not a scale ceiling," and explicitly marked "optional."
- Rationale: The current form deliberately matches the blessed lazy `_get_native_span_type()`
  resolution pattern in `gsm2tree.py` (the reviewer notes "consistency is a legitimate reason to
  leave it"). Memoizing would diverge from that pattern and add cache-correctness subtlety (must
  cache only a successful resolution so a late `fltk._native` import is still picked up) for a
  negligible saving. The consistency and simplicity are worth more than the micro-optimization.
