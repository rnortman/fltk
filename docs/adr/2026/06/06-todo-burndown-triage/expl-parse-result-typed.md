# Exploration: `parse-result-typed` TODO

Concise, no fluff. Audience: smart human/LLM. Findings only.

---

## Claim vs. Reality: Field Name

The TODO claim uses two names for the same field: "result.result" and "ParseResult.cst". These refer to **different objects**:

- `ParseResult` (defined at `fltk/plumbing_types.py:26-33`) has field `cst: Any | None`.
- `ApplyResult` (defined at `fltk/fegen/pyrt/memo.py:69-71`) has field `result: ResultType` and is `Generic[PosType, ResultType]`.

The five cast call sites all call `cast("cst.Grammar", result.result)` where `result` is an `ApplyResult`, **not** a `ParseResult`. The comments at those sites say "result.result is typed Any (ParseResult.cst: Any)" — this is misleading: `ApplyResult.result` is typed `ResultType` in the `Generic` definition, but the generators (`fltk_parser.py`, `bootstrap_parser.py`, etc.) are produced by `exec()` at runtime and have no static return-type annotations visible to pyright at the call sites, so `result` itself is effectively `Any`, making `result.result` also `Any`.

---

## The Five Cast Sites

All five cast the `.result` field of an `ApplyResult`, not the `.cst` field of a `ParseResult`.

| File | Line | Variable type |
|------|------|---------------|
| `fltk/fegen/genparser.py` | 63 | `result` = `parser.apply__parse_grammar(0)` return, parser instantiated from runtime-exec'd class |
| `fltk/plumbing.py` | 149 | same — Python path in `parse_grammar()` |
| `fltk/plumbing.py` | 177 | same — Rust path in `parse_grammar()` |
| `fltk/unparse/genunparser.py` | 51 | same — `parse_grammar_file()` local |
| `fltk/test_plumbing.py` | 577 | same — test directly calls `fltk_parser.Parser.apply__parse_grammar(0)` |

The fltk_parser itself **does** have a static return type: `fltk/fegen/fltk_parser.py:97-99` shows `apply__parse_grammar(self, pos: int) -> fltk.fegen.pyrt.memo.ApplyResult[int, fltk.fegen.fltk_cst.Grammar] | None`. So at the `test_plumbing.py:577` site (which uses `fltk_parser.Parser` directly), `result.result` is already typed `fltk_cst.Grammar` statically — the cast is redundant there.

At the four other sites, the parser is created from a runtime-`exec()`'d class and the variable holding it is untyped (`Any`), so `result` is `Any` → `result.result` is `Any`.

---

## ParseResult.cst: Actual State

`fltk/plumbing_types.py:29`: `cst: Any | None`

`ParseResult` is a plain `@dataclass`, not `Generic`. It is constructed at `fltk/plumbing.py:312`, `322`, `324`:

```python
return ParseResult(None, text, False, f"No parse method for rule '{rule_name}'")
return ParseResult(None, text, False, error_msg)
return ParseResult(result.result, text, True)   # result.result is Any here
```

`parse_text()` signature at `fltk/plumbing.py:293`: `-> ParseResult` (non-generic). This is the **public API function** consumed downstream.

---

## Downstream Consumers of ParseResult.cst

Within the repo, `parse_result.cst` is accessed uncast at:
- `fltk/unparse/test_unparser.py` (many call sites, passing `.cst` directly to `unparse_cst()`)
- `fltk/unparse/test_omit_functionality.py:65`
- `fltk/unparse/test_unparser_edge_cases.py:49`
- `fltk/fegen/test_trivia_whitespace_capture.py:31, 93`
- `fltk/test_plumbing.py` (multiple)
- `fltk/test_plumbing_integration.py` (multiple)
- `fltk/unparse/test_initial_sep_unparser.py`
- `fltk/unparse/test_group_nest_combination.py`
- `fltk/unparse_cli.py:122`
- `tests/test_phase4_rust_fixture.py:110, 119, 128, 137, 146, 442`

These pass `.cst` to `unparse_cst(unparser_result, cst, terminals, ...)` which accepts `cst: Any` (`fltk/plumbing.py:426`). None of the in-tree call sites annotate or cast `.cst`.

---

## Generic Fix Feasibility

**Construction bottleneck**: `parse_text()` (`fltk/plumbing.py:293-324`) is the sole public constructor path for `ParseResult`. Its `rule_name` is a runtime string; `T` cannot be inferred by the type checker from a string. A generic `parse_text[T]() -> ParseResult[T]` would require the caller to supply `T` explicitly, e.g. `parse_text[MyNode](...)`, which is valid Python/pyright syntax but requires callers to know the CST type statically. Failure cases construct `ParseResult(None, ...)` where `cst=None`, consistent with `cst: T | None`.

**The five commented cast sites** are about `ApplyResult.result`, not `ParseResult.cst`. Making `ParseResult` generic would not eliminate these casts. Those casts are needed because the parser class is exec'd and the variable is `Any`. The only fix for those sites is type-annotating the variable holding the exec'd parser result (e.g., using a Protocol or cast at the exec site).

**Downstream annotation impact**: `ParseResult` is returned by `parse_text()` in `fltk/plumbing.py`, which is public API. Changing `-> ParseResult` to `-> ParseResult[T]` would cause annotation churn at every in-tree and out-of-tree call site that annotates `parse_result: ParseResult` (non-generic). All in-tree usages found use bare `ParseResult` in the return type annotation of `parse_text` and in some test helpers. Out-of-tree consumers using type annotations would need to change `ParseResult` to `ParseResult[SomeNode]` everywhere — a breaking annotation change per CLAUDE.md.

---

## TODO Claim Accuracy Summary

| Claim | Actual |
|-------|--------|
| "ParseResult.cst is Any" | **Correct.** `fltk/plumbing_types.py:29`. |
| "five scattered cast() calls" | **Correct count, wrong attribution.** They are at `ApplyResult.result`, not at `ParseResult.cst`. `ParseResult.cst` is never cast in-tree — it is passed as `Any` directly. |
| "result.result" vs "ParseResult.cst" | **Two different fields on two different classes.** The TODO conflates them. |
| "making ParseResult generic would eliminate the five casts" | **Incorrect.** The casts are on `ApplyResult.result` returned by exec'd parser methods. Making `ParseResult` generic does not affect those sites. |
| "Location: fltk/plumbing_types.py" | **Partially correct** — that is where `ParseResult` is defined, but the actual cast sites involve `ApplyResult` from `fltk/fegen/pyrt/memo.py`. |

---

## Open Factual Questions

- Whether out-of-tree consumers annotate variables as `parse_result: ParseResult` (no data; CLAUDE.md notes real consumers are not visible in-repo).
- Whether `parse_text()` is actually the public API entry point for downstream consumers, or whether they call lower-level parser methods directly (would affect cast-site relevance).
