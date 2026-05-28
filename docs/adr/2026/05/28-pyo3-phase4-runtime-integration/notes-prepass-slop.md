# Prepass slop findings — Phase 4 runtime integration diff

Commit reviewed: 11dce0a (base f8a2fe1)

---

## slop-1

**File:line:** `docs/rust-cst-extension-guide.md:136`

**Quote:** `Concise. Precise. Audience: FLTK user building a Rust CST extension.`

**What's wrong:** This line is a stray writing instruction left inside the document body. It appears verbatim between the Overview header and the `---` separator, reading as paragraph text to anyone who opens the file.

**Consequence:** Ships a meta-instruction to users as if it were prose. Embarrassing in a published guide.

**Fix:** Delete the line.

---

## slop-2

**File:line:** `fltk/fegen/fltk2gsm.py:385`

**Quote:** `label = self.visit_identifier(cst_label).value if (cst_label := item.maybe_label()) else None`

**What's wrong:** `cst_label` uses the old bare module name rather than `self.cst` — it references nothing in scope (no `cst` import exists any more after the refactor). This is a walrus-expression where the call is `item.maybe_label()` (fine), but the variable name `cst_label` is just a local; the real issue is that `self.visit_identifier` is called but `cst_label` shadows nothing from `self.cst`. Actually the deeper issue: this line survived the refactor unchanged and still calls `cst_label` as a local variable name (acceptable), but the diff shows the old `cst.` references were removed everywhere *except* this one remaining call uses no `self.cst` dispatch at all — it passes `cst_label` (the raw CST node) to `self.visit_identifier`, which only reads `.child_name()` off it. That part is fine. However, `item.maybe_label()` returns a node whose type is backend-specific, and no `isinstance` check against `self.cst` is performed here. This is a latent inconsistency rather than a crash today, but it is the one spot in the function that bypasses the DI pattern established by the rest of the refactor.

**Consequence:** If a future caller needs isinstance dispatch on the label node, this spot will silently use the wrong backend class. Low immediate risk but inconsistent with the surrounding refactor intent.

**Fix:** No code change needed if `visit_identifier` only uses span access and never does isinstance. Add a one-line comment explaining why no `self.cst` dispatch is needed here, so reviewers don't flag it as an oversight.

---

## slop-3

**File:line:** `fltk/fegen/test_genparser.py:586–589` (module docstring)

**Quote:**
```
Covers the gen-rust-cst subcommand (Increment 3 / Phase 4 Tier 1 tests):
- test_gen_rust_cst_command_emits_source (AC6 Python half / design Test Plan §Tier 1)
- test_gen_rust_cst_sentinel_decoupled (design Test Plan §Tier 1)
- test_gen_rust_cst_no_double_trivia (deferred from Increment 2)
```

**What's wrong:** Implementation-log prose in a module docstring: "Increment 3", "deferred from Increment 2", "AC6 Python half / design Test Plan §Tier 1" are task-tracker references, not descriptions useful to a future test reader. Docstrings describe what the module tests, not its development history.

**Consequence:** Reads like LLM talking to itself. Signals the file was written by narrating the task rather than writing for the reader.

**Fix:** Replace with a plain description of what the module tests (e.g. "Tests for the `gen-rust-cst` CLI subcommand: source emission, sentinel decoupling, and no-double-trivia contract.").

---

## slop-4

**File:line:** `fltk/test_plumbing.py:1048–1050`

**Quote:**
```python
def test_python_backend_default_unchanged(self):
    """No rust_cst_module → Python backend, behavior identical to before."""
```

**What's wrong:** "behavior identical to before" is a narrative comment describing the change ("before" implies a prior state), not a description of the test invariant.

**Consequence:** Minor but characteristic LLM writing tell in a public docstring.

**Fix:** "No `rust_cst_module` argument → Python backend is used; parser and cst_module are populated as usual."

---

No other findings.
