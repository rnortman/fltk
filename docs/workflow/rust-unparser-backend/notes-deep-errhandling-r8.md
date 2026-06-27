## errhandling-1

**File:** `fltk/fegen/genparser.py:454`

**Broken error path:** `parse_format_config_file(format_config)` can raise `OSError` subclasses beyond `FileNotFoundError` — specifically `PermissionError` (file exists, not readable) and `IsADirectoryError` (path is a directory, not a file). The handler on line 454 only catches `(ValueError, FileNotFoundError)`, so those propagate uncaught.

**Why:** `parse_format_config_file` (`fltk/plumbing.py:247–253`) pre-checks `config_path.exists()` and raises a synthetic `FileNotFoundError` for the not-found case, but then calls `config_path.open()` bare. Any `OSError` from `open()` that isn't `FileNotFoundError` — e.g. `PermissionError` on a file the process can't read, `IsADirectoryError` if the path resolves to a directory — propagates through `parse_format_config_file` and through `gen_rust_unparser`'s handler, which doesn't catch it.

**Consequence:** A user who passes `--format-config` with a path that exists but isn't readable gets a raw Python traceback instead of the clean `Error: … / exit 1` that every other failure path in this function produces. On-call can still read the traceback (the path and errno are present), but it breaks the CLI contract of this command and is inconsistent with the grammar-file error handling in `_read_and_parse_grammar`, which wraps `open()` in `except Exception`.

**Fix:** Widen the handler to `except (ValueError, OSError) as e:`. `FileNotFoundError` is an `OSError` subclass, so the existing "file not found" message (emitted by `parse_format_config_file` before `open()`) is still surfaced cleanly. No existing test behavior changes.
