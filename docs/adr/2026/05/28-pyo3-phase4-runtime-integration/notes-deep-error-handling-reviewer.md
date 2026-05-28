Commit reviewed: cdffac4

errhandling-1
File: fltk/plumbing.py:46-51 (_load_fegen_grammar)
Path: `fegen_fltkg.open()` → unhandled FileNotFoundError propagates into the caller (rust-backend branch of `parse_grammar`) with no wrapping context.
Why: No try/except around the `open()`. The exception message contains the fltk-internal path, which is diagnosable, but nothing in the call stack adds "this is FLTK's bundled fegen grammar, not a user file." The FileNotFoundError propagates as-is to the user who asked for `rust_fegen_cst_module=...`, giving an opaque internal path with no actionable message.
Consequence: On a corrupted or mis-packaged fltk install the user sees a bare `FileNotFoundError` with no guidance. On-call cannot distinguish "user passed wrong path" from "fltk package is broken."
Fix: Wrap `fegen_fltkg.open()` in try/except FileNotFoundError and re-raise as `RuntimeError("fltk internal fegen grammar missing; reinstall fltk: {path}")`.

errhandling-2
File: fltk/fegen/genparser.py:174 (generate command, `except RuntimeError`)
Path: Writing the shared CST file (`shared_cst.open("w") as f: f.write(...)`) is wrapped in `except RuntimeError`, but file I/O raises `OSError` (and its subclasses: `PermissionError`, `FileNotFoundError`). `RuntimeError` will never be raised by `open()` or `write()` on any normal filesystem.
Why: The catch clause is the wrong exception type; it will never fire, so I/O failures on this path propagate as unhandled `OSError` with no CLI error message and no `typer.Exit(1)`.
Consequence: If the output directory is not writable, the command crashes with a raw Python traceback instead of the intended "Error: Failed to write shared CST file" message. This is a pre-existing bug but this review scope includes lines touched in the diff — this `try/except` block is in code added in the diff (`generate` command was extended; the `except RuntimeError` exists at line 174 in the current file which is in the changed region).
Fix: Change `except RuntimeError` to `except OSError`.

No other findings. The `.expect()` calls in Rust (invariant: `count==1 but found==None`) are correct — they guard a logically impossible branch that can only be reached if the loop's own bookkeeping is broken, making `panic` appropriate. The `ImportError`-only catch in `_load_rust_cst_classes` is intentional and documented. The `assert` statements in `fltk2gsm.py` are pre-existing and unchanged in semantics (only `self.cst` substituted for module-level `cst`). The `exec_globals["Unparser"]` bare key access in `generate_unparser` is pre-existing and out of scope.
