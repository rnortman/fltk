# Deep error-handling review — fltklsp round 1 (checkpoint 2)

Base `debdeb6` → HEAD `0b001f2`. Scope: error observability and response on changed code only.
Changed under review: `fltk/lsp/classify.py` (new), `fltk/lsp/lsp_config.py` (resolve/load additions),
`fltk/plumbing.py` (wrappers). Not-yet-built features (§4.7 engine, §4.8 CLI, §8 dogfood) intentionally
absent — not faulted. Generated artifacts not audited.

Note: the prior checkpoint's errhandling-1/-2 (missing `else` on statement dispatch; qualifier binary
else) are now fixed in this tree — `lsp_config.py:216-218` raises `AssertionError` on an unhandled
statement, and `:154` asserts `maybe_rule() is not None`. Good.

---

## errhandling-1 — Unknown CST node kind silently under-classifies instead of failing loud

File: `fltk/lsp/classify.py:160-167` (`_default_intervals`) and `fltk/lsp/classify.py:253-259`
(`_explicit_intervals`).

Broken path: both tree walks do `rule = tables.kind_to_rule.get(node.kind.name)` and treat a miss as a
normal branch. In `_default_intervals`, `rule is None` ⇒ `table is None` ⇒ every span child of that node
is silently dropped (`if table is None: continue`, :171-172) while node children keep recursing. In
`_explicit_intervals`, `rule is None` ⇒ `matchers = ()` (:258-259) ⇒ that node's whole-node paints and
its rule-block child matchers never apply — silently, recursion continuing.

Why: `kind_to_rule` is built from `grammar.rules` keyed by `naming.snake_to_upper_camel(rule.name).upper()`
(:108), and every CST `node.kind.name` is by construction one of those keys — verified against the
generated `NodeKind` enum and `gsm2tree.node_kind_member_name` (gsm2tree.py:96), and trivia rules are
present in the trivia-classified grammar. So a `.get()` miss is not expected input; it is an invariant
violation (grammar/CST/naming divergence). It is caught by neither an assertion nor a log — the code
proceeds as if the node had no paints.

Consequence: if this file's copied naming derivation ever drifts from the generator's (it duplicates,
does not share, `node_kind_member_name`), or a future analysis-grammar transform introduces a node kind
with no matching rule, the classifier emits *zero* tokens for the affected nodes' terminals and silently
ignores all rule-scoped / def-derived / whole-node paints for them. The output is still a valid, sorted,
merged token stream — just missing coverage. No error, no diagnostic, nothing logged. On-call sees
"highlighting is blank/wrong for construct X" and cannot distinguish a naming-mismatch bug from an
intentional no-paint, nor locate the source. This is an invariant/logic error silently degrading output
instead of surfacing.

Must change: treat a `kind_to_rule` miss as the invariant violation it is — assert (naming the offending
`node.kind.name`) or raise/log at both sites, rather than `.get()` + silent skip. If a node kind can
legitimately be absent, document why and make the skip intentional and observable.

---

## errhandling-2 — Second `.get()` (tables lookup) folds a distinct desync into the same swallow

File: `fltk/lsp/classify.py:167` — `table = tables.tables.get(rule.name) if rule is not None else None`.

Broken path: an independent `.get()` on `tables.tables` whose miss (rule in `kind_to_rule` but absent
from `tables`) collapses into the same silent `if table is None: continue` drop of all span children.

Why: both maps are built from the same `grammar.rules` in `build_grammar_tables` (:107-108), so with
`rule is not None` this cannot miss today. But they are keyed differently (`tables` by `rule.name`,
`kind_to_rule` by uppercased camel), so a future edit populating one and not the other reintroduces a
miss that is indistinguishable — at this line — from the errhandling-1 unknown-kind miss.

Consequence: same silent under-classification, but from a different root (table/kind-map desync rather
than kind/grammar desync). Even a targeted fix at errhandling-1's site would not disambiguate this
cause, because the same `continue` absorbs both. On-call again gets missing tokens with no error.

Must change: since `rule is not None` guarantees `rule.name` is a `tables.tables` key, index directly
(`tables.tables[rule.name]`) so a desync raises `KeyError` at its origin instead of degrading to a
`None` table; or, if kept as `.get`, assert the invariant. Do not share the unknown-kind swallow path.

---

## errhandling-3 (minor) — `parse_lsp_config_file` docstring understates its uncaught error paths

File: `fltk/plumbing.py:281-296` (`parse_lsp_config_file`).

Broken path: the function guards `config_path.exists()` and raises `FileNotFoundError`, then does a
plain `config_path.open()` / `f.read()`. A `UnicodeDecodeError` (non-UTF-8 `.fltklsp`) or
`PermissionError`/`OSError` propagates uncaught. The docstring's `Raises:` lists only `LspConfigError`
and `FileNotFoundError`.

Why/consequence: propagation is an acceptable *response* here, so this is not a swallow — but the
documented handled set is wrong, and a decode error surfaces to the CLI (§4.8, not yet built) as a raw
traceback rather than the formatted "bad --lsp file" exit path the design promises. Low impact; flagged
for awareness so the CLI layer wraps these when it lands.

---

## Reviewed and found clean

- `load_lsp_config` (lsp_config.py:630-655): parse-failure path checks both a falsy result and
  `result.pos != len(terminals.terminals)` (trailing garbage), formats via `errors.format_error_message`,
  raises `LspConfigError` with context. Validate-before-resolve upholds `resolve_config`'s documented
  precondition. Good.
- `_resolve_local_anchor` / `_resolve_global_anchor` `assert name is not None` (:546, :578): correct —
  literal-or-name is a real invariant; assertion is the right crash response.
- `resolve_config` `if rule_index is None: continue` (:609-610): documented precondition (config already
  validated) makes the skip intentional; unknown rule already flagged by validation. OK.
- `_classify_span_text` returning `None` (no provenance) and def-kind-not-in-legend producing no paint:
  documented, intentional (design §4.5/§4.6); editor default shows through. Not a swallow.
- `_classify_regex_text` `text[0]` (:121): safe — only reached for spans passing `if not segment.strip()`.

---
---

# Deep error-handling review — final round (checkpoint 3): AnalysisEngine (§4.7), fltk-highlight CLI (§4.8), dogfood (§8)

Base `87dbc0d` → HEAD `9a085e9`. Scope this round: `fltk/lsp/engine.py` (new),
`fltk/lsp/highlight_cli.py` (new), `fltk/lsp/fltklsp.fltklsp` (new), `fltk/lsp/test_dogfood.py` (new).
Surrounding read: `fltk/plumbing.py`, `fltk/lsp/lsp_config.py`, `fltk/unparse_cli.py`.

## errhandling-4 — CLI file-IO errors escape as raw tracebacks; §4.8's "formatted message to stderr, exit 1" is unmet for the most common bad input

File: `fltk/lsp/highlight_cli.py:85-95` (the `except ValueError` guard at :87 and the unguarded
`file.read_text()` at :91), reaching `fltk/lsp/engine.py:70-71`.

Broken path: `main` guards only `AnalysisEngine.from_paths(...)` and only against `ValueError`
(comment at :87 asserts "grammar/.fltklsp load errors (LspConfigError is a ValueError)"). But the
file-loading steps raise `OSError` subclasses, not `ValueError`:
- `plumbing.parse_grammar_file(grammar_path)` raises `FileNotFoundError` for a missing `--grammar`
  (`plumbing.py:81-83` — it even builds a clean "Grammar file not found: …" string, then raises it as
  `FileNotFoundError`, which the `except ValueError` does not catch).
- `engine.from_paths` reads the spec via bare `lsp_path.read_text()` (`engine.py:71`) — a missing `--lsp`
  raises bare `FileNotFoundError`. This also bypasses the purpose-built `plumbing.parse_lsp_config_file`
  (`plumbing.py:274-297`), which exists precisely to emit a clean "LSP config file not found: …" message.
- The input `FILE` is read at `highlight_cli.py:91` **outside any try** — `FileNotFoundError` /
  `IsADirectoryError` / `PermissionError` / `UnicodeDecodeError` all propagate.

With `pretty_exceptions_enable=False`, all three propagate to a raw Python traceback. Verified against
the built module: `--grammar nope.fltkg`, `--lsp nope.fltklsp`, and a missing input `FILE` each dump a
full multi-frame traceback to stderr.

Why it's wrong: §4.8 promises ".fltklsp load errors or FILE parse errors: formatted message to stderr,
exit 1." A missing `--lsp` is a `.fltklsp` load error; a missing `FILE` is the single most common CLI
misuse. The `except ValueError` encodes an author belief ("load errors are ValueError") that is false for
the file-existence/read layer, so the intended handler silently fails to cover the case it was written
for. (This is errhandling-3's forward-looking prediction now realized in the built CLI.)

Consequence: exit code is 1 (Python's uncaught-exception default), so scripts keying on status still see
failure — but a user, or an M2 server that later drives this path, or on-call reading logs, cannot tell
"you typo'd a path" from an internal crash: the actionable "file not found: X" is buried under interpreter
frames. A non-UTF-8 input yields the same undifferentiated `UnicodeDecodeError` traceback. The clean
messages `plumbing` already constructs never reach the user.

Must change: widen the `try` at :85 to also cover `file.read_text()` at :91, and broaden the except from
`ValueError` to include `OSError`/`UnicodeDecodeError`, echoing `str(exc)` to stderr and `raise
typer.Exit(1)`. Prefer routing the `.fltklsp` read through `plumbing.parse_lsp_config_file` so its
"LSP config file not found" message is actually used. (Note: `unparse_cli.py` shares this untreated-IO
shape, so the design's "matches unparse_cli.py" is literally true — but §4.8's own wording is the stronger,
unmet contract.)

## errhandling-5 (minor) — `_render` trusts the sorted/non-overlapping token invariant with no assertion

File: `fltk/lsp/highlight_cli.py:52-74`.

Broken path: `_render` assumes `tokens` is sorted and non-overlapping (its docstring, and §4.6's output
invariant). It walks with one `cursor`, emitting the gap slice only when `token.start > cursor` and always
setting `cursor = token.end`. If `classify` ever emitted overlapping/out-of-order tokens, gap slices go
empty and overlapping segments render twice / mis-colored — no error, no assertion.

Why noted, not urgent: the invariant is `classify`'s responsibility (audited last round, out of this
slice) and this is a display-only tool, so the blast radius is a wrong-looking terminal dump, not
corrupted state. But it is the "invariant unreachable-in-theory, never asserted" pattern: a future
`classify` regression would surface as subtly wrong colors rather than a diagnosable failure at the seam.

Consequence: a classifier invariant break ships as silent mis-highlighting; whoever debugs it gets no
signal from the renderer that the token stream — not the theme — is at fault.

Must change (optional hardening): assert `token.start >= cursor` at the top of the loop so an upstream
invariant break fails loudly here instead of painting garbage. Low cost; makes the trusted invariant
self-checking.

## Reviewed and found clean (this round)

- `engine.highlight` (`engine.py:75-85`): parse failure is both reported and responded to —
  `HighlightResult(tokens=None, error=parsed.error_message)`; the `.success` guard keeps `classify` off a
  `None` CST. Correct expected-bad-input handling.
- `AnalysisEngine.__init__` (`engine.py:54`): `prepare_analysis_grammar` raising `ValueError` on
  `!`-grammars pre-empts the generator's raw `NotImplementedError` and is exercised by
  `test_engine.py::test_inline_grammar_rejected_at_construction`. `generate_parser`'s
  `RuntimeError("Generated parser class not found")` is an appropriate crash-on-invariant and propagates.
- `test_dogfood.py` / `fltklsp.fltklsp`: fixture + tests; no runtime error-handling surface.
- `_winner_segments` `best is None` skip (:296): a genuine inter-interval gap, not an error.
