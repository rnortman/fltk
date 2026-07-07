# Deep quality review — round base 87dbc0d, HEAD 9a085e9

Scope: this round's slice — `fltk/lsp/engine.py` (AnalysisEngine, §4.7),
`fltk/lsp/highlight_cli.py` + `pyproject.toml` scripts entry (§4.8), `fltk/lsp/fltklsp.fltklsp`
dogfood fixture (§8), and the three new test files (`test_engine.py`, `test_highlight_cli.py`,
`test_dogfood.py`). Adjacent code (`plumbing.py`, `classify.py`, `lsp_config.py`,
`unparse_cli.py`, `TODO.md`) read to verify patterns.

## quality-1: `TODO(lsp-classify-hotpath)`'s stated landing condition arrived — and was skipped

`TODO.md` (`lsp-classify-hotpath`) defers three classify hot-path inefficiencies, and its own
deferral rationale is explicit: all three are "cheapest to address when the §4.7 `AnalysisEngine`
lands (it holds grammar-derived state for the parser's lifetime, so it is the natural owner of
the once-per-grammar tables)". This round landed that engine (`fltk/lsp/engine.py:38-85`,
commit 79a55c3) — and item (1) was not addressed: `AnalysisEngine.highlight` (`engine.py:84`)
calls `classify.classify(parsed.cst, self._parser_result.grammar, ...)`, which still runs
`build_grammar_tables(grammar)` per call (`classify.py:372`, and again at `:211` via
`default_tokens`) — a full grammar walk plus recompiling every terminal regex, per highlight
request, inside the object whose docstring says it "owns the expensive one-time setup ... once,
then turns text into semantic tokens on every `highlight` call".

Consequence: the seam the M2 server will call per keystroke now has the O(grammar)+regex-compile
cost baked into its contract, and fixing it later means changing `classify`'s public signature
under the engine after M2 wraps it — exactly the churn the TODO was written to avoid. Meanwhile
the TODO text itself now describes a future ("when the AnalysisEngine lands") that has already
happened, so the entry silently rots into a plain wishlist item with its trigger spent.

Fix: burn down at least item (1) in this round's spirit — build the tables once in
`AnalysisEngine.__init__` (e.g. the TODO's own suggestion: a `Classifier` constructed from the
grammar, or a required tables parameter on `classify`/`default_tokens`) and call through it in
`highlight`. If that is deliberately deferred again, the TODO entry must be rewritten with a new
concrete trigger (e.g. "before M2 wraps the engine") so it doesn't point at a met condition.

## quality-2: `AnalysisEngine.from_paths` reimplements `plumbing.parse_lsp_config_file`

`fltk/lsp/engine.py:71-72`: `config_text = lsp_path.read_text() if lsp_path is not None else ""`
followed by `load_lsp_config(config_text, grammar)`. The design (§3) added
`plumbing.parse_lsp_config_file(path, grammar)` for exactly this step, and it exists
(`plumbing.py:274-297`) with an existence check and the formatted
`"LSP config file not found: {path}"` message. `from_paths` bypasses it, so a missing `.fltklsp`
surfaces as a bare `FileNotFoundError` from `Path.read_text()` instead.

Consequence: two file→config paths for the same artifact that will drift (error message,
encoding handling, any normalization later added to the plumbing wrapper never reaches the
engine) — and the engine is the canonical consumer every future caller (the M2 server) goes
through, so the plumbing wrapper becomes dead-in-practice API the moment its intended caller
skips it.

Fix: `resolved_config = plumbing.parse_lsp_config_file(lsp_path, grammar) if lsp_path is not
None else load_lsp_config("", grammar)`.

## quality-3: CLI error surface is inconsistent — missing files produce raw tracebacks

`fltk/lsp/highlight_cli.py:85-91`. The command formats *content* errors cleanly
(`except ValueError` → stderr + exit 1, pretty exceptions disabled), but a missing/unreadable
file at any of the three paths escapes as an uncaught exception → raw Python traceback:
`--grammar` (`plumbing.parse_grammar_file` raises `FileNotFoundError`, not `ValueError`),
`--lsp` (`lsp_path.read_text()` inside `from_paths`), and `FILE` (`file.read_text()` at line 91,
outside any handler). So the most common CLI mistake — a typo'd path — gets the worst output,
while the subtler mistake (bad spec content) gets the clean one. `unparse_cli.py` has no
handling at all, so "matches unparse_cli behavior" doesn't cover this; the new CLI
half-establishes the good pattern and contradicts it within one function.

Consequence: this is the project's first console script and the template the M2 server CLI will
copy; the inconsistent surface propagates. No test can pin missing-file behavior as "exit 1 +
message" today (the existing exit-1 tests only cover content errors).

Fix: use typer's path validation on all three parameters (`exists=True, dir_okay=False,
readable=True`) for a clean usage error, or broaden to `except (ValueError, OSError)` and move
`file.read_text()` inside the handler; add a missing-file test either way.

## quality-4: `_THEME` re-enumerates the token legend as unchecked raw strings

`fltk/lsp/highlight_cli.py:30-47` hand-lists all 16 legend members as string keys with no tie
to the canonical `TOKEN_LEGEND` frozenset (`lsp_config.py:45`). `_render` deliberately passes
unknown token types through uncolored, so any divergence is silent.

Consequence: §4.5 explicitly anticipates legend evolution (M2 registers custom types; the
legend is frozen "for round 1" only). The first legend addition that forgets a theme entry
renders invisibly uncolored — discovered by a user squinting at a terminal, not by CI.

Fix: one assertion, in `test_highlight_cli.py` or at module import:
`set(_THEME) == TOKEN_LEGEND - {"none"}` (adjusted for whether `none` is a legend member).
Keeps the theme private and non-configurable per the design while pinning coverage.

## quality-5: copy-pasted test fixtures, and one helper duplicated under two names

- `_GRAMMAR` and `_LSP` are byte-identical between `test_engine.py:13-21` and
  `test_highlight_cli.py:12-20` (unlike earlier rounds' per-file grammars, which genuinely
  differ).
- The exact-span token-lookup helper exists twice with identical bodies and *different names*:
  `_type_of` (`test_engine.py:30-35`) and `_token_type` (`test_dogfood.py:20-25`).

The prior checkpoint's review flagged this exact pattern (its quality-5: `_token_for` copies,
conftest suggestion); this round added three more copies instead of consolidating — the
propagation failure mode in action.

Consequence: the helper encodes nontrivial assertion semantics (exact start+end match,
exactly-one-token) that every future token test needs; when those semantics change (e.g. token
merging alters what "one token spanning substr" means), one copy gets fixed and the others
silently keep the old semantics. The cloned grammars likewise fork on first divergent need.

Fix: add `fltk/lsp/conftest.py` (none exists) with a shared `token_type_at(tokens, text,
substr)` helper and the shared hello-grammar/`_LSP` fixtures; also home for the previously
flagged `_token_for` copies. Keep genuinely test-specific grammars local.

No other findings. The dogfood fixture's comments describe current behavior with no design-doc
references (a hygiene point the earlier rounds were dinged for — clean here); the `[project.scripts]`
entry matches the user-approved decision (§9); engine/CLI docstrings are terse and current;
value-based error propagation from `highlight` (tokens-or-message) is the designed observability
shape for this layer.
