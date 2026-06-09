Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Commit reviewed: 7a288b6

---

test-1
File: tests/test_phase4_fegen_rust_backend.py:163
`test_append_rejects_terminalsrc_span` receives `child_method` as a parameter (suppressed via `noqa: ARG002`) but does not call it. The test exercises rejection by `append_<label>` only — it never reads back through `child_<label>`. This is the correct scope for the rejection pin, but `child_method` is entirely unused. The `noqa` suppression is correct, and the test body is correct; the only concern is the mismatch between parameter list and use, which is cosmetic. No behavior gap — the design deliberately scopes test 3 to the append direction only.
Consequence: nil — `child_method` is intentionally unused here per design §3. No missed coverage.
Fix: none required; the `noqa: ARG002` is the right mechanism and the design accounts for this.

---

test-2
File: tests/test_phase4_fegen_rust_backend.py:136–146 (`test_sourceless_span_start_end`)
The fallback path in `_span_text` (`fltk2gsm.py:41`) uses `self.terminals[span.start : span.end]` — a slice on a `TerminalSource.terminals` object (not a raw `str`). The test verifies `.start` and `.end` are accessible integers (value-correct) and that `text()` is `None` and `has_source()` is `False`. It does not verify that the sourceless result can actually be used as the fallback slice argument (i.e., that `terminals[result.start : result.end]` evaluates correctly, which requires `start`/`end` to be plain `int`, not some proxy type). However, `result.start == 3` (integer equality) is sufficient to confirm the type — an opaque proxy would fail the equality assert or would need `__eq__` trickery. This is not a gap.
Consequence: nil — the integer equality assertions are sufficient to pin the fallback slice contract.

---

test-3
File: tests/test_phase4_fegen_rust_backend.py:148–160 (`test_source_bearing_span_text`)
`result.text() == "lo wor"` is the primary-path pin. The design notes ASCII text keeps codepoint-vs-byte questions out of scope. The test correctly covers: return type (`isinstance`), attribute values (`.start`, `.end`), source presence (`.has_source()`), and slice correctness (`.text()`). No gap.

---

test-4
File: tests/test_phase4_fegen_rust_backend.py:115–167 (parametrize coverage)
The three node/label triples match the three `fltk2gsm` visitors. `visit_rule` also calls `rule.child_name()` (line 20 of fltk2gsm.py), but `rule` is a `Rule` node — the `child_name()` on `Rule` returns an `Identifier` node, not a `Span`; `_span_text` is then called on the `Identifier`'s span via `visit_identifier`. This is not an omission — the test targets span-returning accessors specifically, and the `Rule.child_name()` → `Identifier` → `visit_identifier` → `identifier.child_name()` → Span path is already covered by the `Identifier` param. No gap.

---

test-5
File: tests/test_phase4_fegen_rust_backend.py:162–167 (`test_append_rejects_terminalsrc_span`)
The test confirms `TypeError` is raised. It does not assert the message content, which is reasonable — message strings are implementation details. The TypeError type is sufficient to pin the contract. The `pytest.raises(TypeError)` with no `match=` is acceptable here.
Consequence: nil — a future change that raises `TypeError` for a different reason (e.g., wrong message) would still pass this test, but the contract is that rejection occurs, not why; the design explicitly calls this a "deliberate contract pin."

---

No findings.

The three tests (9 parametrized cases) are non-vacuous: each asserts specific type and value properties required by the real production code path (`_span_text`). Assertions are not mere smoke-test ("didn't crash") — they pin the exact attributes that `_span_text`'s two code branches depend on. The rejection test pins a deliberate API constraint. No meaningful code path covered by the design is missing a test.
