## slop-1

**File:** `fltk/unparse/gsm2unparser_rs.py:14-17`

**Quote:**
```
This module is built up incrementally (design ``design.md`` §2.2); this revision
provides the generator scaffold (constructor, memoized ``generate``, file header,
and the ``Unparser`` struct).  Rule-walking bodies, the PyO3 wrapper, and CLI/build
wiring land in later increments.
```

**What's wrong:** "This revision" in a module docstring is process narration — it describes the development history, not the module. The moment the next increment lands, this sentence becomes false.

**Consequence:** Future readers see "this revision provides the scaffold" and must mentally translate it as "this is all that existed at the time it was written" — which is meaningless information for anyone not in the original commit stream. Reads as LLM narrating its work.

**Fix:** Delete these two sentences. The module docstring's opening sentences already say what the module does.

---

## slop-2

**File:** `tests/test_rust_unparser_generator.py:8-9`

**Quote:**
```
This revision covers the generator scaffold only: header + ``Unparser`` struct.
Per-rule method assertions are added alongside the rule-walking increments.
```

**What's wrong:** Same "this revision" narration pattern in a test-module docstring. Immediately stale once more tests are added.

**Consequence:** A maintainer adding tests in a future increment must either leave a false docstring or clean it up. The information belongs in commit messages, not test-file documentation.

**Fix:** Delete these two sentences.

---

## slop-3

**File:** `crates/fltk-unparser-core/src/render.rs:82-84`

**Quote:**
```rust
/// Mutable output state shared by the two `render` helpers (`break_line` /
/// `append_content`), replacing the Python closures that captured `result`,
/// `current_column`, and `at_beginning_of_line` by `nonlocal`.
```

**What's wrong:** The third sentence describes what this struct *replaced* in the Python source, not what it *is* or what invariants it maintains. This is a translator's note, not documentation.

**Consequence:** Meaningless to any reader who is not simultaneously reading the Python original. As the codebases diverge the reference becomes actively misleading.

**Fix:** Drop the "replacing the Python closures…" sentence. If the design choice needs justification (Rust can't mutably capture the same binding in two closures), say that instead.

---

## slop-4

**File:** `crates/fltk-unparser-core/src/render.rs:236-238`

**Quote:**
```
/// `mode` and `indent` are threaded to match the Python tuple shape but do not
/// affect the decision (flat semantics throughout). Unhandled node types are
/// skipped, mirroring the Python helper's lack of an `else` branch.
```

**What's wrong:** "to match the Python tuple shape" and "mirroring the Python helper's lack of an `else` branch" are translator's notes. The Python tuple shape has no meaning once the Rust codebase stands alone.

**Consequence:** Explains the code by reference to an external artifact (the Python source). Readers unfamiliar with the Python original gain nothing from this; readers who do know it already understand.

**Fix:** Rewrite to describe the actual behavior: `mode` is always flat in `fits` (semantics mandate it); `indent` is threaded for Nest sub-items but does not influence the column count. Unhandled node types (spacing specs) contribute zero width — callers are expected to have resolved them, but `fits` is intentionally lenient.

---

## slop-5

**File:** `crates/fltk-unparser-core/src/result.rs:9-12`

**Quote:**
```
/// The `extract_span_text` / `count_span_newlines` / `is_span` helpers from `pyrt.py`
/// have no Rust analog: the Rust CST's child enum *is* the terminal-vs-rule
/// discriminant (generated code matches on it directly), and `Span::text()` carries
/// its own source, so there is no `terminals` string to slice (design §1, §2.1).
```

**What's wrong:** This module docstring documents what is *not* present by listing Python symbols that were deliberately not ported. This is design archaeology, not module documentation. A user of `UnparseResult` does not need to know about `pyrt.py` helpers that have no Rust counterpart.

**Consequence:** The module doc is longer and harder to parse because it explains absent functionality. If `pyrt.py` is ever refactored or renamed, this comment silently rots.

**Fix:** Delete this paragraph from the module docstring. If the porting rationale needs to be preserved, it belongs in the design doc or ADR, not in source.
