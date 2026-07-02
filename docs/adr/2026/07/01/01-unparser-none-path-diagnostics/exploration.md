# Exploration: `unparser-none-path-diagnostics`

Base commit: `8fd5ecf`. TODO text under review: `TODO.md:85-87`.

## TODO(unparser-none-path-diagnostics) comment inventory

Repo-wide `grep -rln "unparser-none-path-diagnostics"` hits exactly these files:

- `TODO.md:85` (the entry itself)
- `fltk/unparse/gsm2unparser_rs.py` — the only file with in-code `TODO(unparser-none-path-diagnostics)` comments, at lines **1091** and **1365** (two comments total, matching the TODO's "two `None`-return paths" claim; no others exist anywhere in the tree, including no hits under `crates/**/*.rs`).
- `docs/workflow/2026-06-27-rust-fltkfmt/{dispositions-deep.md, dispositions-final-deep.md, judge-verdict-deep.md, judge-verdict-final-deep.md, notes-final-deep-error-handling.md}` — prior review-chain artifacts that originated this TODO (disposition IDs `errhandling-1`/`errhandling-2` in the "deep" pass, `errhandling-2`/`errhandling-3` in the "final-deep" pass).

## Site 1 — non-trivia separator `if let Some(trivia_result)` with no `else`

Generator: `fltk/unparse/gsm2unparser_rs.py`, method `_gen_non_trivia_rule_processing` (`def` at line 1299). The TODO comment sits at lines 1365-1370, immediately above the code it describes:

- Line 1363: `if self._has_preservable_trivia(&trivia_node) {`
- Line 1371: `if let Some(trivia_result) = self.unparse__trivia(&trivia_node) {`
- Lines 1372-1382: on success, wraps the trivia's `Doc` into a `SeparatorSpec` via `_add_separator_spec_lines`.
- Line 1382: `}}` — closes the inner `if let Some(...)` block.
- Line 1383: `}} else {{` — this `else` belongs to the **outer** `if self._has_preservable_trivia(...)` (line 1363), not to the inner `if let Some(trivia_result)`. There is no `else` arm for the inner `if let`.

Confirmed as described: when `_has_preservable_trivia` returns true but `unparse__trivia` returns `None`, no `SeparatorSpec` is emitted and no diagnostic fires — the comment is silently dropped. `TODO.md`'s locator "~line 1346" is approximate/imprecise (line 1346 is actually `preserve_blanks = self._get_preserve_blanks()`, inside the same method's setup code, ~17-25 lines above the actual `if`/`if let` pair at 1363/1371); it points at the right method, not the exact line.

### Python-backend equivalent (site 1) — same gap, symmetric

`fltk/unparse/gsm2unparser.py`, `_gen_trivia_processing` (`def` at line 1084):

- Line 1306-1307: `has_preservable_call = ...; if_has_preservable = if_trivia.block.if_(has_preservable_call, orelse=True)`.
- Line 1310-1318: binds `trivia_result_var` to the `unparse__trivia` call result.
- Line 1321: `if_trivia_success = if_has_preservable.block.if_(trivia_result_var.load())` — **no `orelse=True` passed**.
- `Block.if_` signature (`fltk/iir/model.py:158`): `def if_(self, condition, *, let=None, orelse: bool = False)`. Default `orelse=False` means no else-block/IR node is generated at all.

So when `unparse__trivia` returns a falsy/`None` result here, the Python generator emits no else branch either — the comment is silently dropped with zero diagnostic, identical in kind to the Rust site. **No asymmetry between backends at site 1**; the TODO's framing (a joint policy decision needed to add a diagnostic to both backends) matches present behavior for this site.

## Site 2 — `let text = span.text()?;` in `_gen_regex_term_body`

Generator: `fltk/unparse/gsm2unparser_rs.py`, method `_gen_regex_term_body` (`def` at line 1028). The TODO comment is at lines 1091-1095; the code line it describes is:

- Line 1096: `lines.append("        let text = span.text()?;")`

`TODO.md`'s locator "~line 1077" is approximate (line 1077 is `num_variants = self._cst.num_child_variants(rule_name)`, ~19 lines above the actual `span.text()?` site); again it names the right function, not the exact line.

Rust `Span::text()` (`crates/fltk-cst-core/src/span.rs:421`, delegating to `text_str` at line 433) returns `None` under two distinct conditions folded into one: (a) no source attached (`self.source.as_ref()?` at line 434), or (b) source attached but invalid indices (negative, `start > end`, or `end` past codepoint count — lines 435-441 and continuation). The generated `span.text()?` cannot distinguish these; both propagate `None` silently up through `?` to the public `unparse_*` entry point.

### Python-backend equivalent (site 2) — NOT symmetric; already diverges today

The Python-generated unparser's regex-term codepath (`gsm2unparser.py:1750-1778`, `elif isinstance(term, gsm.Regex):`) calls `pyrt.extract_span_text(child_var, self.terminals)` (line 1764), not a raw `span.text()`. `extract_span_text` (`fltk/unparse/pyrt.py:34-50`) explicitly separates the two conditions that Rust's `text()` folds together:

```
text = span.text() if hasattr(span, "text") else None
if text is not None:
    return text
if hasattr(span, "has_source") and span.has_source():
    msg = f"span.text() returned None for source-bearing span {span!r}; codepoint offsets may be out of range"
    raise ValueError(msg)
return terminals[span.start : span.end]
```

- If `text()` is `None` **and** the span has no source at all → silent fallback to slicing `terminals` directly (this covers the pure-Python `terminalsrc.Span` sourceless case, which is an expected/normal path for that backend, not an error).
- If `text()` is `None` **and** the span *does* have a source (`has_source()` is `True`) → **raises `ValueError`** naming the span's `repr()`, rather than propagating `None` silently.

This `has_source()` check works uniformly across both span implementations that a Python-generated unparser can receive:
- Python-backend `terminalsrc.Span.has_source()` (`fltk/fegen/pyrt/terminalsrc.py:89-91`) returns `self._source is not None`.
- Rust-backend PyO3-exposed `fltk._native.Span` also exposes `has_source()` as a Python method (`crates/fltk-cst-core/src/span.rs:709-711`, `py_has_source` delegating to the Rust `has_source` at line 477).

So the exact scenario the TODO calls the "invariant-violation path" for the Rust generator — a source-bearing span whose `text()`/`text_str()` returns `None` because of bad offsets — is a case the Python backend **already handles today, loudly, with a diagnostic message identifying the span**, for either backend's span object, whereas the Rust-generated code's `span.text()?` silently discards the same condition with zero diagnostic. This is an existing asymmetry in current (base-commit `8fd5ecf`) behavior, not a symmetric gap the two backends jointly lack.

The Python-backend `terminalsrc.Span` also independently exposes a `text_or_raise()` method (`terminalsrc.py:73-87`) with the same raise-on-invalid-indices semantics, unused by `extract_span_text` but confirming the "raise rather than silently return None" pattern is an established convention on the Python side, not a one-off.

## Bearing on the TODO's cross-backend-policy claim

The TODO states: "Closing this needs a deliberate cross-backend policy decision (log-and-continue vs `debug_assert!` vs halt) applied to **both** the Rust generator and the Python unparser so backend behavior stays in parity." This framing fits site 1 (both backends silently drop today) but is inaccurate as stated for site 2: parity does not currently exist to "stay" in — the Python unparser already halts with a diagnostic (`raise ValueError(...)` naming the span) for the source-bearing/bad-offset condition, while the Rust generator's `span.text()?` is silent. Applying a policy "to both" for site 2 would need to either bring Rust up to Python's existing raise-with-message behavior, or deliberately relax Python's existing raise — either way it is a decision about reconciling an existing divergence, not selecting a policy from a blank, symmetric slate.
