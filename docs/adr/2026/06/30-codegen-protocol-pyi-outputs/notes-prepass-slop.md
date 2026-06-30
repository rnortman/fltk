## Slop findings — prepass

Commit reviewed: 7682e2fa5461dbac03a7184911042944f97613bc

---

### slop-1

**File:** `docs/adr/2026/06/30-codegen-protocol-pyi-outputs/implementation-log.md` (entire file)

**Quote:** `## Increment 1 — Python generate: protocol becomes opt-in (§2.1)` … `## Increment 2` … `Deviation (minor):` … `Note: the 5 pyright errors … pre-exist on the base commit`

**What's wrong:** This is an LLM implementation process log committed to the codebase — increment-by-increment narration of what was done, deviation notes, and "note: pre-existing" asides. It's not an ADR (no context/decision/consequences structure per CLAUDE.md). It reads as the LLM talking to itself about what it did, preserved verbatim.

**Consequence:** Any reviewer opening the ADR directory finds a verbose agent scratchpad committed as a project artifact. It implies the implementation process is part of the project record, which it isn't; the decisions belong in a proper ADR and the narrative belongs in commit messages or a PR description.

**Suggested fix:** Replace with a proper ADR — context, decision, consequences — and move the incremental notes to the PR description or discard them. If a design document already exists alongside this, the implementation log adds no durable value.

---

### slop-2

**Files:** `rust.bzl:1338,1362-1363`; `genparser.py` (comment in gen_rust_cst body); `fltk/fegen/gsm2lib_rs.py` (`_render_init_pyi` docstring)

**Quote (representative):**
- `rust.bzl`: `# Mirror the CLI's '...' check, surfacing the misconfiguration at analysis time (§2.5).`
- `rust.bzl`: `# ... keeping it on the same dogfooded path as the in-tree markers (§2.2).`
- `genparser.py`: `# Write order: .rs, then the protocol .py, then the .pyi (design §2.2).`
- `gsm2lib_rs.py` docstring: `Shared by gen-rust-cst / gen-rust-unparser … (design §2.2).`

**What's wrong:** Code comments and docstrings cite design-document sections (§2.2, §2.5, §2.5-§2.6) as justification. These are task-context references — they only mean something to someone who has the design doc open. A maintainer six months from now won't know what §2.2 says.

**Consequence:** The comments read as the LLM sourcing its own design doc instead of explaining the code's intent in standalone terms. When the design doc is not in the reader's hands, the §-citations are dead weight and mark the comments as LLM-generated rather than author-written.

**Suggested fix:** Strip the §-citations; expand the sentence to say what the constraint actually is in plain English. E.g., `(§2.5)` → `(matches the CLI guard: --protocol-output requires --protocol-module)`.

---

### slop-3

**File:** `fltk/fegen/genparser.py` — gen_rust_cst body and gen_rust_unparser body

**Quote:**
```python
if init_pyi_output is not None and init_pyi_text is not None:
    _write_output_file(init_pyi_output, init_pyi_text, "stub-package __init__.pyi")
```

**What's wrong:** The second conjunct (`init_pyi_text is not None`) is unreachable. When `init_pyi_output is not None`, `_render_init_pyi` either returns a non-None string or exits via `typer.Exit`. There is no code path where `init_pyi_output is not None` and `_render_init_pyi` returns `None`. The double-None guard is a silent "just in case" fallback with no explanation.

**Consequence:** If the condition were ever true (the None branch silently skips the write), it would mean the marker was requested but not written — a silent data loss. The guard implies the function can return None when `init_pyi_output` is not None, which it cannot; the misleading condition will confuse future readers.

**Suggested fix:** Either `assert init_pyi_text is not None` after the call (to surface the impossible case), or simplify to `if init_pyi_output is not None:` and drop the second conjunct.

---

### slop-4

**Files:** `fltk/fegen/test_genparser.py` (new test functions); `tests/test_gsm2tree_rs.py` (`TestGenerateProtocol.test_parses_as_valid_python`)

**Quote:**
```python
import ast  # noqa: PLC0415
```
(inside test function bodies; appears in at least two new test functions in test_genparser.py and one method in test_gsm2tree_rs.py)

**What's wrong:** `ast` is imported locally inside test functions to suppress the PLC0415 ("import not at top of module") lint check, instead of adding a top-level `import ast`. The same diff adds `import ast` correctly at the top of `test_gsm2lib_rs.py`. The local-import-with-noqa pattern is inconsistent and is a workaround for a lint issue rather than the fix (a top-level import).

**Consequence:** The inconsistency signals the imports were added piecemeal without reviewing the file's existing import block. A reader seeing `import ast  # noqa: PLC0415` inside a test body will wonder what prevents a top-level import here, find no reason, and conclude it was accidental.

**Suggested fix:** Add `import ast` at the top of `test_genparser.py` and `tests/test_gsm2tree_rs.py` (alongside existing imports) and remove the local imports with their noqa comments.
