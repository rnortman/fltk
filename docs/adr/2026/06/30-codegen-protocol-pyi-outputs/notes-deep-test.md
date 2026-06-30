# Test review: codegen-protocol-pyi-outputs

Commit reviewed: 19348b3a8900ae0eaf883f3f7b3531b029d9a814

## Findings

**test-1** — `fltk/fegen/test_genparser.py`, `test_gen_rust_cst_init_pyi_requires_extension_name_and_submodules` and `test_gen_rust_unparser_init_pyi_requires_extension_name_and_submodules`

The `_render_init_pyi` guard is `if extension_name is None or submodules is None:` (genparser.py:559). Both tests invoke with `--extension-name` present and `--submodules` absent, covering only the `submodules is None` branch. The `extension_name is None` branch — user omits `--extension-name` but provides `--submodules` — is never exercised at the CLI level for either subcommand. A regression in argument-binding (wrong parameter name, wrong default) on the `extension_name` side goes undetected.

Fix: add a test that passes `--init-pyi-output` and `--submodules` while omitting `--extension-name`, for both `gen-rust-cst` and `gen-rust-unparser`, asserting non-zero exit, the expected error message, and no files written.

---

**test-2** — `fltk/fegen/test_genparser.py`, `test_gen_rust_cst_init_pyi_rejects_malformed_identifier` and `test_gen_rust_unparser_init_pyi_rejects_malformed_identifier`

Both tests exercise a malformed `--submodules` entry (`"cst,bad name"`), covering the `_validate_rust_ident(sub, "submodule")` path through `_render_init_pyi`. The parallel path — a malformed `--extension-name` (e.g., `"bad-name"` with hyphen) triggering `_validate_rust_ident(extension_name, "extension_name")` — is never tested at the CLI level. The unit test `test_render_stub_package_init_rejects_bad_extension_name` covers the helper itself but not the `ValueError → typer.Exit(1)` wiring in `_render_init_pyi`. A bug in that wiring (e.g., the caught exception swallowed without exit) would not be caught.

Fix: add one test per subcommand that passes `--extension-name "bad-ext"` (hyphen is not a valid Rust identifier) alongside `--init-pyi-output` and `--submodules`, asserting non-zero exit and no files written.

---

**test-3** — `fltk/fegen/test_genparser.py`, test names `test_gen_rust_cst_init_pyi_requires_extension_name_and_submodules` / `test_gen_rust_unparser_init_pyi_requires_extension_name_and_submodules`

Names claim both required options are tested; bodies only test the missing-submodules case (see test-1). A reader auditing coverage will incorrectly conclude the extension-name-missing path is exercised. No production behavior is wrong, but the misleading name conceals the gap identified in test-1 and will mislead future maintainers.

Fix: rename both tests to `…requires_submodules` (or split into two tests: one for the missing-extension-name case, one for the missing-submodules case, with accurate names).
