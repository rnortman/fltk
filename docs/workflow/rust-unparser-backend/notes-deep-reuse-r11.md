## reuse-1

File: `tests/test_rust_unparser_pyi.py:64-80` (`_pyright_available` function + `pyright_available` fixture)

The new file defines a private `_pyright_available()` function (lines 64-75) that checks `shutil.which("uv")` and runs `["uv", "run", "pyright", "--version"]`, then wraps it as a session-scoped `pyright_available` fixture (lines 78-80). This body is character-for-character identical to the `pyright_available` session fixture already in:

- `tests/test_gsm2tree_rs.py:2165-2177`
- `tests/test_clean_protocol_consumer_api.py:74-86`

The natural shared home is `tests/pyright_test_utils.py`, which was introduced precisely to avoid this kind of scatter. The module docstring on line 1-5 of `pyright_test_utils.py` already names the files it is used by; `test_rust_unparser_pyi.py` should join that list rather than re-implementing the check. As the pattern propagates to additional `test_rust_*` files the three-way divergence risk grows: a future change (e.g. a different `--version` flag or a `uv` path issue) has to be found and patched in three places.

Existing: `tests/pyright_test_utils.py` (no `pyright_available` helper currently lives there, though the infrastructure for session-scoped sharing exists via the module).

---

## reuse-2

File: `tests/test_rust_unparser_pyi.py:106-113` (inline `pyrightconfig.json` write inside `consumer_pyright_diagnostics`)

```python
(tmpdir / "pyrightconfig.json").write_text(
    json.dumps(
        {
            "pythonVersion": "3.10",
            "venvPath": str(_REPO_ROOT),
            "venv": ".venv",
            "extraPaths": [str(_REPO_ROOT), str(_REPO_ROOT / "fltk" / "_stubs")],
        }
    )
)
```

`tests/pyright_test_utils.py:67-75` already provides `write_pyright_config(tmpdir)` for exactly the base three keys (`pythonVersion`, `venvPath`, `venv`). The new code duplicates those three keys inline and appends `extraPaths`. The shared utility could accept an optional `extra_paths` argument; instead, a new inline variant is introduced. The same base pattern is also present a third time in `test_gsm2tree_rs.py:2221-2223` (`_write_pyi_tmpdir`). Each copy must be updated independently if, for example, the venv path convention or the Python version target changes.

Existing: `tests/pyright_test_utils.write_pyright_config` — `tests/pyright_test_utils.py:67-75`.
