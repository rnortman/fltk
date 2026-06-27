reuse-1:
- File: `fltk/unparse/gsm2unparser_rs.py:99-103`
- Snippet:
  ```python
  segments = self._cst_mod_path.split("::")
  if segments[-1] == "cst":
      cst_import = f"use {self._cst_mod_path};"
  else:
      cst_import = f"use {self._cst_mod_path} as cst;"
  ```
- What's duplicated: identical four-line block for generating the Rust `use … as cst;` / `use …;` import from a `cst_mod_path` string.
- Existing function/utility: same logic at `fltk/fegen/gsm2parser_rs.py:305-309` inside `RustParserGenerator._gen_header`. The comment in the new file even says "# CST module import (mirrors gsm2parser_rs._gen_header)". The `_rust_str_lit` helper in that same file was extracted to module level and is already imported by `gsm2unparser_rs`; this companion snippet was not.
- Consequence: if the import-generation rule ever changes (e.g. to handle a path whose last segment happens to equal `cst` for unrelated reasons, or to emit a `#[allow(…)]` above it), one copy will drift from the other. The logic is simple today, but the duplication is structural — two generators with independent copies of the same decision.
