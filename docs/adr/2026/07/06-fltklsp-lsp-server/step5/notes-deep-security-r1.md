# Security review — round 5 (resolver plugin API, gear demo, VS Code wiring)

Reviewed: `git diff 1e920dc..fe10193`. HEAD = fe10193.

Context calibration: `fltk-lsp` is a local dev tool the user launches themselves, and
`--resolver` loading arbitrary per-language Python is the design's stated purpose — the
user-supplied spec executing user-supplied code is not a finding. The trust boundaries that
matter are (a) *who* can influence which code/command actually gets executed (workspace
settings, cwd contents), and (b) untrusted workspace *file content* flowing into filesystem
operations.

## security-1

- **File:line**: `examples/gear/vscode/package.json:35-43` (the `gear.server.command`
  setting), `examples/gear/vscode/extension.js:47-52` (`serverCommand()`).
- **Issue**: `gear.server.command` is an arbitrary argv executed on activation, and it is
  declared with the default setting scope (`window`), which **workspace settings can set**.
  The extension also declares no `capabilities.untrustedWorkspaces`, relying on VS Code's
  implicit default (disabled in Restricted Mode) rather than an explicit posture.
- **Trust boundary / data flow**: a workspace's `.vscode/settings.json` (attacker-authored,
  ships inside any cloned repo) → `workspace.getConfiguration("gear").get("server.command")`
  → `child_process` spawn of `argv[0]` with `argv.slice(1)` the moment a `.gear` file opens.
- **Consequence**: arbitrary command execution on the user's machine. Workspace Trust blocks
  the fully-untrusted case by default, but the residual paths are real: a user who clicks
  "Trust" on a cloned-but-unaudited repo (the normal reflex for a repo they intend to build),
  or who has disabled workspace trust, executes whatever argv the repo's settings name — no
  prompt, no indication. This is the exact vuln class behind published LSP-extension CVEs
  (ESLint, Rust Analyzer, etc.), and this file is the demo/template downstream languages will
  copy.
- **Suggested fix**: declare the setting `"scope": "machine"` (VS Code's documented rule:
  settings that determine an executable path must be machine-scoped, so workspace settings
  cannot set them), and add an explicit
  `"capabilities": { "untrustedWorkspaces": { "supported": false } }` so the trust posture is
  deliberate rather than default. Both are one-line changes and cost the demo nothing (the
  demo's default path doesn't use the setting at all).

## security-2

- **File:line**: `fltk/lsp/resolver.py:181-183` (`_looks_like_path`), used by
  `_import_head` → `_import_file` (exec of the file).
- **Issue**: a `--resolver` spec head is treated as a *file* whenever
  `pathlib.Path(head).is_file()` — a **cwd-relative** check — even when the head contains no
  `/`, no `\`, and no `.py` suffix, i.e. even when it reads unambiguously as a module spec.
  Whether `--resolver mylang.resolvers:create_resolver` imports the installed module
  `mylang.resolvers` or `exec`s a file named `mylang.resolvers` in the server's cwd is
  decided by cwd contents.
- **Trust boundary / data flow**: attacker-controlled repo/workspace contents (a planted file
  named after a known language's resolver module, e.g. `mylang.resolvers`) → server launched
  with cwd inside that workspace (editors commonly spawn LSP servers with cwd = workspace
  root; nvim-lspconfig does by default) → `spec_from_file_location` + `exec_module` of the
  planted file at server startup.
- **Consequence**: arbitrary Python execution from workspace contents, triggered by opening a
  hostile project with an otherwise-correctly-configured editor. The user consented to
  running *their configured resolver module*, not files from the directory they opened. The
  ambiguity also makes the load nondeterministic across cwds — a correctness smell on top of
  the security one.
- **Suggested fix**: make spec interpretation cwd-independent: treat the head as a file only
  on the unambiguous signals (`.py` suffix or a path separator); drop the bare `is_file()`
  test. Anyone who wants a cwd-relative file can write `./name` or `name.py`. (The gear
  default and README already use explicit `.py` paths, so nothing shipped changes.)

## security-3

- **File:line**: `examples/gear/gear_resolver.py:82` (`root.joinpath(*parts)` from
  `_module_parts`), plus the resolver-author guidance block in `fltk/lsp/resolver.py:19-29`.
- **Issue**: the gear resolver builds a filesystem path directly from segments taken out of
  untrusted document text (`use a::b::…`). It is safe **in gear only by accident of the
  grammar**: `identifier := /[A-Za-z_][A-Za-z0-9_]*/` (`gear.fltkg`) excludes `.`, `/`, `\`,
  so `..` or absolute segments cannot parse. The file's docstring explicitly bills itself as
  "the worked example for writing your own resolver," and neither it nor the resolver-author
  guidance in `resolver.py` mentions that path construction from document content needs
  validation.
- **Trust boundary / data flow**: workspace file text (untrusted) → module-path segments →
  `pathlib.joinpath` → `host.document()` → disk read + parse; the resulting definition target
  is shown to the user (peek window renders the target file's text).
- **Consequence**: for a downstream language whose path segments admit `.`/`..`/separators
  (most real module systems admit at least `.`), a hostile project file gets the resolver to
  read and display arbitrary readable files outside the workspace (`use ....etc.passwd`-shaped
  traversal, or a `joinpath` reset via an absolute segment) — an information-disclosure
  primitive in every resolver copied from this template. Gear itself is not exploitable
  today.
- **Suggested fix**: harden the template so copies are safe by construction: in
  `gear_resolver.py`, reject segments that are not plain identifiers (or verify
  `target_path.resolve().is_relative_to(root.resolve())` before `host.document()`), with a
  comment saying why; add one line to `resolver.py`'s resolver-author guidance: "module-path
  segments come from untrusted document text — validate them (no separators, no `..`, no
  absolute parts) before touching the filesystem."

## Checked, no finding

- Secrets in the diff: none (no keys/tokens; test fixtures are synthetic).
- `--resolver` arbitrary-code load itself: by design, user-supplied, documented as such.
- Rename guard: fails closed on any exception, and re-checks the document version after the
  worker await (TOCTOU handled) — correct security posture.
- `ProjectHost` disk reads: confined to resolver-requested URIs and the suffix-filtered
  workspace walk; `os.walk` does not follow directory symlinks; dot-dirs skipped. Symlinked
  regular files can point outside the root, but the reader is the user's own local server
  displaying to the user's own editor — no cross-principal disclosure.
- Resolver exceptions: caught and logged via `window/logMessage` with `{exc!r}` only —
  degrades read paths, never crashes the loop; no sensitive data beyond local paths.
- `_split_spec` `:attr` parsing: last-`:`-with-identifier rule avoids Windows drive-letter
  confusion; failure modes all land in fail-fast `ResolverError` → stderr + exit 1 before
  protocol I/O.
