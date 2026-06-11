# Correctness review — Phase 2 Rust parser generator

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Reviewed: `490bccf..b95f772` (HEAD b95f772). Focus: `fltk/fegen/gsm2parser_rs.py` traced line-by-line against the behavioral reference `fltk/fegen/gsm2parser.py`, the GSM model (`gsm.py`), the CST generator contracts (`gsm2tree_rs.py:1038-1093`, union/span/single append signatures), the Phase 1 runtime (`memo.rs`, `errors.rs`), and the committed generated artifacts. Both fixture crates' `cargo test` runs pass locally (exit 0).

Verified equivalent to the Python reference (no findings): alternative ordering and first-match-wins; required/optional item control flow incl. WS_REQUIRED else-return; `+` progress check (`is_required()` ⇔ `min() != ZERO`, gsm.py); suppressed-item handling in both single and multiple paths (Rust skips the temp-node append Python performs, but the temp is discarded at the alternative level in both — final trees identical); INLINE raising on every path (the SUPPRESS check precedes, but dispositions are mutually exclusive); rule_id/RULE_NAMES alignment (both `grammar.rules` order post-trivia-processing); `_rust_str_lit` escaping (round-trips patterns through `REGEX_PATTERNS` verbatim); span placeholder `-1` + final `set_span` matching `_make_span_expr` semantics; trivia capture sites guarded by runtime `capture_trivia` replacing Python's two-module split; `error_position` `-1` sentinel handling. The fegen `block_comment` lookahead-removal grammar change (fegen.fltkg:21) was traced for acceptance-language equivalence: old and new rules accept exactly the same comments (terminate at first `*/`); only the `content`/`end` span boundary shifts for `**/`-style endings, which the implementation log documents.

## Findings

### correctness-1: trivia-rule separator regex is `[\s]+`, Python reference uses `\s+`

- **File:line**: `fltk/fegen/gsm2parser_rs.py:494` (`ws_pattern = r"[\s]+"`).
- **What's wrong**: The Python generator emits `\s+` for separators inside trivia rules (`gsm2parser.py:643`: `trivia_pattern = r"\s+"`; see the removed `fltk_trivia_parser.py:1169` line, `regex="\\s+"`). The design (§2.2) explicitly states "The trivia-rule separator pattern `r"\s+"` (gsm2parser.py:643) goes through the same table." The Rust generator instead uses `[\s]+`.
- **Why**: Confirmed in committed output: `tests/rust_cst_fegen/src/parser.rs:15` has `"[\\s]+"` at `REGEX_PATTERNS[3]`, consumed at the trivia-subexpression WS_REQUIRED separator (`parser.rs:1131`), while the Python parsers for the same grammar reported `\s+` at the corresponding failure site.
- **Consequence**: Matching behavior is identical (`[\s]` ≡ `\s`), but `ErrorTracker::fail_regex` records the verbatim pattern (`errors.rs`), so error messages diverge: Rust reports `REGEX: '[\\s]+'` where Python reports `REGEX: '\\s+'` for any failure at a trivia-rule separator — reachable in the fegen grammar via `_trivia := ( line_comment | line_comment? : | block_comment )+`. This breaks the Phase 3 error-message-parity requirement the design names as the reason `consume_regex` takes a table index at all (§2.2 item 4).
- **Fix**: Change `ws_pattern` to `r"\s+"` and regenerate both `parser.rs` artifacts. (Side effect: the pattern no longer dedups against the default trivia rule's `[\s]+` content regex — that is the Python-parity-correct outcome.)

### correctness-2: union-label append path is never compiled by any fixture; fixture grammar omits the design-required union label

- **File:line**: `fltk/fegen/gsm2parser_rs.py:785-790` (union arms of `_gen_append_code_for_consumed`); `fltk/fegen/test_data/rust_parser_fixture.fltkg`.
- **What's wrong**: Design §2.6 B requires the fixture grammar to contain "a union label (two node types under one label)". The shipped grammar has none — every label is single-typed (`atom := num:num | name:name` uses two distinct labels). `grep 'Child::'` over both committed `parser.rs` files finds only `::Trivia(...)`/`::Span(...)` separator captures; no `append_<lbl>(cst::<X>Child::<Class>(...))` or `append_<lbl>(cst::<X>Child::Span(...))` statement exists in any compiled artifact. The only coverage is a text-substring assertion (`test_gsm2parser_rs.py:676-760`), which cannot prove the emitted form type-checks against the CST API.
- **Why**: The design's safety argument for append/variant mismatches (§3: "impossible by construction ... the failure is a Rust compile error in generated code") presumes the fixture lanes compile every append form. Two of the eight rows of the §2.3 decision table (union node, union span) compile nowhere in-repo. Textual cross-check against `gsm2tree_rs.py` union `append_<lbl>(child: {enum_name})` (gsm2tree_rs.py:~1331) shows the emitted form is consistent today, but nothing gates it.
- **Consequence**: A future regression in either generator's union handling (e.g. variant naming) ships green through `make check` and first fails in an out-of-tree consumer's build — exactly the failure mode CLAUDE.md says cannot be evaluated by in-tree absence.
- **Fix**: Add a union-label rule to `rust_parser_fixture.fltkg` (e.g. `val := item:num | item:name`, plus a span/node mix for the `Child::Span` arm), regenerate `cst.rs`/`parser.rs`, add a native test.

### correctness-3: `RustParserGenerator.generate()` is not idempotent — second call returns uncompilable output

- **File:line**: `fltk/fegen/gsm2parser_rs.py:164-168` with `self._fn_bodies` accumulation (`:91`, appends at `:398,418,481,577,629,702`).
- **What's wrong**: `generate()` re-runs `_gen_rule` for every rule on each call. `_cache_parser_info` dedups the registry, but every `_emit_*`/`_gen_*` method unconditionally appends to `self._fn_bodies`, so a second `generate()` on the same instance emits every function body twice (duplicate `fn` definitions — invalid Rust), returned silently as a normal string.
- **Why**: The Python reference does all generation in `__init__` exactly once; the Rust generator moved generation into `generate()` without a guard or reset. The determinism test (`test_gsm2parser_rs.py:382-388`) constructs two instances, so this is untested.
- **Consequence**: Any caller (future CLI option, test, or Phase 3 plumbing) that calls `generate()` twice gets corrupt output with no error — a silent invariant violation rather than a loud failure.
- **Fix**: Memoize the result (`if self._generated is not None: return self._generated`) or raise on second call.

### correctness-4: sub-expression path under `+`/`*` items inserts an extra `one` segment, diverging from the Python reference's generated names

- **File:line**: `fltk/fegen/gsm2parser_rs.py:590-591` (`self._gen_consume_term((*path, "one"), ...)`) → `:684` (`alts_path = (*path, "alts")`).
- **What's wrong**: For a multiple-quantified sub-expression item, the inner alternatives function is registered at `(*path, "one", "alts")`, producing e.g. `parse__trivia__alt0__item0__one__alts` (see `tests/rust_cst_fegen/src/parser.rs:1103+`). Python registers it at `(*path, "alts")` (`gsm2parser.py:355-357` called from `gen_item_parser_multiple:523-524`), producing `parse__trivia__alt0__item0__alts` in `fltk_trivia_parser.py`.
- **Why**: The design (§2.1) commits to "`self.parsers: dict[tuple[str, ...], RustParserFn]` keyed by the same path tuples" and "the same method-family names ... for side-by-side auditability"; this is the one place the path tuples differ.
- **Consequence**: No runtime behavior difference (names are internal and collision-free). Cost is exactly the auditability the naming scheme exists for: a side-by-side diff of Python vs Rust generated parsers shows phantom structural differences at every repeated sub-expression.
- **Fix**: Pass `path` (not `(*path, "one")`) to `_gen_consume_term` in `_gen_item_multiple` and regenerate.

### correctness-5: sub-expression terms recognized via `isinstance(term, list)`, rejecting valid tuple-typed GSM terms

- **File:line**: `fltk/fegen/gsm2parser_rs.py:664`.
- **What's wrong**: `gsm.Term` is `Union[..., Sequence[Items]]` (gsm.py) and the Python reference dispatches with `isinstance(term, Sequence)` (`gsm2parser.py:355`). The Rust generator checks `isinstance(term, list)` only.
- **Why**: `fltk2gsm.visit_alternatives` happens to return a `list` (fltk2gsm.py:47-48), so the CLI path works; but a programmatically built grammar using a tuple of `gsm.Items` — valid per the GSM type — falls through to the final `else` and raises `NotImplementedError("Unknown term type: <class 'tuple'>")`.
- **Consequence**: Valid GSM input accepted by the Python backend is rejected by the Rust backend, with a misleading error claiming the term type is unknown. Fail-loud, but a gratuitous input-domain divergence between backends.
- **Fix**: Match the reference: `isinstance(term, Sequence)` (with `str` already excluded by the earlier `Literal`/`Regex` arms since GSM terms are never bare strings) or `isinstance(term, (list, tuple))`.

## Observations (not findings; other lanes or accepted)

- Design §2.2 item 4 says regex call sites carry the pattern in a preceding `//` comment; not implemented (no comments emitted). Auditability/scope lane.
- Design §2.2 says the header's "from `<source_name>`" clause is omitted when `source_name is None`; implementation substitutes `<unknown>` instead (`gsm2parser_rs.py:74`). Cosmetic scope deviation.
- The `block_comment` separator change `,` → `.` (fegen.fltkg:21) additionally removes the trivia-mode unlabeled whitespace child after `/*` (removed code in `fltk_trivia_parser.py:1293-1298`) and folds that whitespace into `content`'s span. The implementation log documents the `end`-span shift but not this trivia-capture CST-shape change; both Python parsers were regenerated consistently, so cross-backend equivalence holds.
- `_gen_alternative`'s `if item_idx < len(alt.sep_after)` guard silently skips separators on a malformed `Items` (items/sep_after length mismatch) where Python would IndexError; fltk2gsm asserts equal lengths, so unreachable via the CLI.
- Empty-match inner-loop divergence (`*`/`+` over a nullable term) is mirrored from Python by design (§3) and additionally pre-empted by `gsm.validate_no_repeated_nil_items`.
