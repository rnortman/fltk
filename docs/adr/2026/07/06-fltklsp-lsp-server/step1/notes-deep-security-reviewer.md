# Security review notes — final round: AnalysisEngine (§4.7), fltk-highlight CLI (§4.8), dogfood fixture (§8)

Reviewed: `git diff 87dbc0d..9a085e9` (HEAD 9a085e9; commits 79a55c3, 2962bd3, 9a085e9).
(Supersedes the previous round's notes at this path; that round's ReDoS observation is carried
forward and broadened as security-2 below.)

Trust-boundary framing: the CLI reads workspace-supplied `.fltkg` grammar, `.fltklsp` spec, and
source files — all attacker-controlled when the user points the tool at an untrusted repo.

Boundaries checked and found sound (context, not findings):

- **exec of runtime-generated parser code** (`fltk/plumbing.py:118,145`, reached from
  `AnalysisEngine.__init__` at `fltk/lsp/engine.py:56`): the workspace grammar drives codegen, but
  generation is AST-node-based (no source-string interpolation; the only `ast.parse` in
  `fltk/iir/py/compiler.py:18` parses the empty string), grammar identifiers are constrained by
  `fltk.fltkg` to `/[_a-z][_a-z0-9]*/`, and literal/regex payloads land as AST constants. No
  injection path from grammar content into executed code.
- **Parse-error text on stderr**: `errors.format_error_message`
  (`fltk/fegen/pyrt/errors.py:136-137`) escapes control characters in the quoted source line, so
  `typer.echo(result.error, err=True)` (`fltk/lsp/highlight_cli.py:97`) does not relay raw
  terminal control bytes.
- `--rule` flows into `getattr(parser, f"apply__parse_{rule_name}")`
  (`fltk/plumbing.py:187-191`); the fixed `apply__parse_` prefix confines resolution to generated
  parse methods.
- Dogfood fixture (`fltk/lsp/fltklsp.fltklsp`, `fltk/lsp/test_dogfood.py`): in-tree trusted
  fixtures, no secrets, no new surface.

## security-1 — Raw terminal-escape passthrough in `fltk-highlight` stdout

- **ID**: security-1
- **File:line**: `fltk/lsp/highlight_cli.py:56-77` (`_render`), emitted at
  `fltk/lsp/highlight_cli.py:99` (`sys.stdout.write(_render(text, result.tokens))`).
- **Issue**: `_render` writes the input file's content verbatim to stdout — both unpainted gaps
  (`text[cursor:token.start]`, trailing `text[cursor:]`) and painted segments
  (`text[token.start:token.end]` wrapped in SGR codes). No control-character filtering exists
  anywhere on the stdout path.
- **Trust boundary / data flow**: workspace-supplied source file → `file.read_text()`
  (`highlight_cli.py:95`) → `_render` → user's terminal, unmodified.
- **Consequence**: a hostile source file can embed terminal escape sequences the terminal then
  interprets rather than displays: OSC 52 to load attacker-chosen text into the user's clipboard
  (primed shell commands), OSC 0/2 title injection, cursor-movement/erase sequences to spoof or
  hide output, and — on terminals with known DCS/OSC-handling CVEs — historically worse. It also
  defeats the tool's own output integrity: an embedded `\x1b[0m\x1b[90m` lets malicious code
  restyle itself as a comment, undermining exactly the "look at unfamiliar code with semantic
  highlighting" use the tool exists for. Conditions: user runs `fltk-highlight` on an untrusted
  file with stdout attached to a terminal (the default). Asset: user's terminal/clipboard and
  the trustworthiness of the highlighted output.
- **Suggested fix**: sanitize every segment `_render` emits — strip or escape C0 controls other
  than `\n`/`\t` (at minimum `\x1b`, and C1 `\x9b`), e.g. reuse the `escape_control_chars` policy
  `fltk/fegen/pyrt/errors.py` already applies to error snippets, applied per-segment so the
  tool's own SGR framing stays intact.

## security-2 — Untrusted grammar + input can hang or crash the highlight pipeline (DoS)

- **ID**: security-2
- **File:line**: `fltk/lsp/engine.py:56` (parser generated from workspace grammar) and
  `fltk/lsp/engine.py:79` (`plumbing.parse_text` runs it over the document); surfaced via
  `fltk/lsp/highlight_cli.py:96-97`.
- **Issue**: grammar regex terminals are compiled and executed with Python's backtracking `re`
  engine against the input, and the generated parser is recursive-descent, with no timeout,
  input-size cap, or recursion guard anywhere in the `AnalysisEngine.highlight` seam.
- **Trust boundary / data flow**: untrusted workspace → `.fltkg` regexes + crafted source file →
  catastrophic backtracking; or recursive grammar + deeply nested input → unbounded Python
  recursion (`RecursionError` escaping `highlight` uncaught).
- **Consequence**: highlighting a hostile workspace pins a CPU indefinitely or crashes with a
  raw traceback. For the one-shot CLI this is a Ctrl-C annoyance; but per the design (§4.7) this
  same `AnalysisEngine` seam is what the long-lived LSP server wraps, where one stuck
  `highlight` call means a wedged language server with no user-visible cause. The server's
  debounce/stale-token policy does not bound a single stuck parse. Asset: editor/CI availability.
- **Suggested fix**: acceptable to accept for the CLI this round, but make it a decision, not an
  accident: document the workspace-trust posture on `AnalysisEngine.highlight` (and in the ADR),
  catch `RecursionError` in `highlight` and report it as a parse failure rather than letting it
  escape the seam, and plan for the server layer to run `highlight` under a cancellable worker
  with a wall-clock budget (and/or an input-size cap).

No other findings. Secrets: none in the diff. New dependency surface: none (`typer` was already a
dependency; the new `[project.scripts]` entry in `pyproject.toml` only exposes the CLI).
