# Quality review — batch r11 (committed .pyi + protocol module + pyright tests, OQ-3)

Commit reviewed: fabdc5a2ea6f4ca1ecc42386a4a5f40a8e776dd4

---

## quality-1

**File:line** `tests/test_rust_unparser_pyi.py:74-90`

**Issue — redundant single-call-site wrapper (`_pyright_available`)**

`_pyright_available()` is a private helper whose only call site is the `pyright_available`
fixture two lines below it. Every analogous fixture in the codebase — `test_gsm2tree_rs.py:2166`,
`test_clean_protocol_consumer_api.py:75`, `fltk/fegen/test_cst_protocol.py:39` — inlines the
same `shutil.which("uv")` + subprocess logic directly in the fixture body. The new file splits
that into a helper and a one-line fixture wrapper, adding a layer that carries no abstraction
value: there is no second call site, and the comment ("mirrors the protocol-consumer test gate")
describes the inline code, not a meaningful extracted concept.

**Consequence** — Diverges from the established pattern without benefit. Future readers will
search for why this file uses a helper when the others don't. If the duplicated
`pyright_available` body is ever consolidated into a conftest or `pyright_test_utils`, the
wrapper is one more artifact to clean up and one more difference to reconcile. The indirection
also makes the "skip if pyright unavailable" flow harder to follow at a glance.

**Fix** — Remove `_pyright_available()` and inline its body directly into the
`pyright_available` fixture, matching the three existing files.

---

## quality-2

**File:line** `tests/test_rust_unparser_pyi.py:106-115` / `tests/pyright_test_utils.py:67-75`

**Issue — workaround for `write_pyright_config` lacking `extra_paths` support**

`pyright_test_utils.write_pyright_config(tmpdir)` exists to centralise the
`pyrightconfig.json` boilerplate; `test_clean_protocol_consumer_api.py` and
`fltk/fegen/test_cst_protocol.py` both import and use it. The new fixture bypasses it with an
inline `json.dumps({"pythonVersion": "3.10", "venvPath": ..., "venv": ..., "extraPaths": [...]})`,
duplicating the config structure, because `write_pyright_config` has no parameter for
`extraPaths`. The limitation is in the helper (not in the call site), and the call site silently
works around it.

**Consequence** — Every future test that needs `extraPaths` — and any grammar that commits a
`.pyi` stub under `fltk/_stubs` will need the identical `[repo_root, fltk/_stubs]` setup — must
either bypass `write_pyright_config` or copy the pattern from this file. The helper's raison
d'être is owning the config; bypassing it hollow it out. The two parallel copies (helper vs.
inline) will silently diverge if the Python target version or venv path ever changes — the
helper gets updated and the inline copy doesn't (or vice versa).

**Fix** — Add `extra_paths: list[str] | None = None` to `write_pyright_config` in
`pyright_test_utils.py`. Merge the list into the config dict when non-None. Use the helper in
the new fixture: `write_pyright_config(tmpdir, extra_paths=[str(_REPO_ROOT), str(_REPO_ROOT / "fltk" / "_stubs")])`.

---

## quality-3

**File:line** `Makefile:285-291` (the new protocol-module generation step in `gencode`)

**Issue — `;`-chained shell commands mask generator and copy failures**

```makefile
tmpdir=$$(mktemp -d); \
uv run python -m fltk.fegen.genparser generate ... --output-dir $$tmpdir; \
cp $$tmpdir/rust_parser_fixture_cst_protocol.py tests/rust_parser_fixture_cst_protocol.py; \
rm -rf $$tmpdir
```

Shell commands joined with `;` ignore prior exit codes. The exit code of the whole compound
statement is the exit code of the last command (`rm -rf $$tmpdir`), which is almost always 0.
If `uv run python ...` fails (e.g., a generator regression), or if `cp` fails (file not
generated), Make sees the recipe line succeed because `rm -rf` exits 0. The old committed
`rust_parser_fixture_cst_protocol.py` is silently left unchanged while `make gencode` reports
success. All other `gencode` steps use separate recipe lines (each checked by Make) or `$(MAKE)`
sub-invocations; only this step uses the `;`-joined pattern.

**Consequence** — A generator bug or invocation error during `make gencode` goes undetected at
the point of failure. The developer sees no error, the committed file is stale, and the mismatch
is only caught later by `make check`'s `git diff` gate — at which point the cause is unclear.
The pattern is also fragile to copy if a second grammar needs the same temp-dir extraction.

**Fix** — Replace `;` with `&&` for the commands where failure matters, and ensure cleanup still
runs. A minimal correct form:

```makefile
tmpdir=$$(mktemp -d) && \
uv run python -m fltk.fegen.genparser generate \
    fltk/fegen/test_data/rust_parser_fixture.fltkg rust_parser_fixture rust_parser_fixture_cst \
    --output-dir $$tmpdir && \
cp $$tmpdir/rust_parser_fixture_cst_protocol.py tests/rust_parser_fixture_cst_protocol.py; \
rm -rf $$tmpdir
```

(Trailing `rm -rf` uses `;` intentionally so cleanup runs even if `cp` fails; the overall exit
code of the line is then that of `rm -rf`, which is always 0. If you need the line to fail when
`cp` fails, capture the status before cleanup: `status=$$?; rm -rf $$tmpdir; exit $$status`.)
