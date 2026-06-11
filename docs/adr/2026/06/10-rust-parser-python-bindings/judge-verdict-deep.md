Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

# Judge verdict — deep review

Phase: deep. Base b668897..HEAD 685e21a (round-2 fix commit 685e21a; round-1 fix a06a422; reviewed commit b107645). Round 2 — APPROVED or ESCALATE only.
Notes: 7 reviewer files; 19 findings. Dispositions: `dispositions-deep.md`. Prior verdict: round 1 REWORK on errhandling-2, security-1 residual, reuse-1, quality-4, plus quality-3 relabel.

## Added TODOs walk

### correctness-3 — TODO(parser-bindings-name-collision) at fltk/fegen/gsm2parser_rs.py:807-810, TODO.md:88
Q1 (worth doing): yes — pyo3 `add_class` silently shadows; a downstream grammar with a rule named `parser` gets an unreachable CST node class; generated classes are public API for out-of-tree consumers (CLAUDE.md).
Q2 (design/owner input required): yes — generation-time rejection vs namespacing is an owner-level public-surface call (rejection makes the Rust backend refuse grammars the Python backend accepts, cutting against the near-drop-in goal). Unchanged from round 1; TODO.md entry + code comment present at HEAD.
Assessment: TODO acceptable (round-1 finding stands).

### security-1 — TODO(parser-depth-limit) / TODO(apply-depth-limit) (pre-existing, TODO.md:45, 76-78)
Q1: yes — uncatchable process abort on attacker-nestable input, strictly worse than Python's `RecursionError`.
Q2: yes for the depth limit itself — configurable cap value, error channel, generated-parser/runtime wiring (TODO.md:78 enumerates the open decisions). Both TODO entries present at HEAD.
Round-1 disputed residual (interim Python-visible warning): resolved — see security-1 in the other-findings walk.
Assessment: depth-limit TODO acceptable.

No other TODO dispositions remain. Round-1 do-now verdicts (errhandling-2, reuse-1, quality-4) were all implemented in round 2; their TODO.md entries and code comments are removed — verified by repo-wide grep: zero hits for `parity-test-error-msg-format-validation`, `parity-test-corpus-deduplication`, `gen-python-bindings-template-style` outside the ADR directory.

## Other findings walk — round-2 reworked items

### errhandling-2 — Fixed (was TODO, round-1 do-now)
Claim: hard-coded two-space indentation in `_parse_error_message`; drift silently yields empty `rule_sections` that compare equal both sides, masking structural divergence.
Diff at tests/parser_parity.py:80-85: after parsing, counts lines containing `'From rule "'` and asserts the count equals `len(rule_sections)`, with a diagnostic naming the indentation assumption and embedding the message.
The round-1 landmine (TODO.md's recorded fix — "assert rule_sections non-empty when `Expected:` present" — would have broken the no-failure stub form, which contains `Expected:` with legitimately zero rule sections) was avoided: the count-based check passes 0==0 on the stub form, which now flows through this parser via the errhandling-1 no-error branch (parser_parity.py:137-143). Any misclassified `From rule` line (count > parsed sections) fails loudly. TODO entry and docstring TODO removed.
Assessment: fix addresses the consequence and resolves the recorded-fix conflict correctly. Accept.

### security-1 (residual) — Fixed (interim warning)
Claim residual from round 1: interim Python-visible stack-depth warning rejected on a false premise (responder claimed pyo3 has no docstring mechanism; pyo3 surfaces `///` on `#[pyclass]` as `__doc__`).
Diff at fltk/fegen/gsm2parser_rs.py (`boilerplate` template): five `///` doc-comment lines emitted above `#[pyclass(name = "Parser")]` — abort behavior, uncatchability from Python, and the upstream-limit / known-stack-thread mitigations. Both generated artifacts updated (tests/rust_cst_fegen/src/parser.rs:1344-1348, tests/rust_parser_fixture/src/parser.rs:1090-1094 — verified in diff). pyo3 surfaces `///` pyclass doc comments as Python `__doc__`; the warning is now visible at the boundary untrusted input crosses.
Assessment: the doable-now mitigation is done; the false rationale is moot. Depth-limit TODO stands (walked above). Accept.

### reuse-1 — Fixed (was TODO, round-1 do-now)
Claim: `test_parity` dispatch body duplicated verbatim across both parity modules; contract changes require two edits.
Diff: `run_parity_corpus_entry(py_p, rust_p, ts, rule, text, expected)` extracted into tests/parser_parity.py:151-192 — full SUCCESS/PARTIAL/FAIL dispatch including the round-1 strictness fixes (PARTIAL unconditional non-None asserts; FAIL outcome-agreement and position-agreement asserts). Both `test_parity` bodies now construct parsers + TerminalSource and delegate (test_rust_parser_parity_fegen.py, test_rust_parser_parity_fixture.py — verified in diff). TODO comments removed from both modules; TODO.md entry removed. Unused imports cleaned (`PARTIAL` dropped in fegen; fixture retains `PARTIAL` for corpus literals — correct; fegen retains `_assert_messages_equiv`/`assert_cst_equal`/`assert_error_equiv` for comparator self-tests — correct).
Assessment: matches the reviewer's spec exactly. Accept.

### quality-4 — Fixed (was TODO, round-1 do-now)
Claim: `_gen_python_bindings` built invariant boilerplate via ~35 `lines.append` calls, the only such method in the file.
Diff at fltk/fegen/gsm2parser_rs.py:812-915: non-parametric skeleton converted to two template strings (`boilerplate`, `closing`); per-rule `apply__parse_<rule>` loop retained between them — exactly the reviewer's prescribed split. Output stability: regenerated artifacts diff only by the intentional `///` warning lines plus two blank-line removals (trailing separators), confirming `make gencode` was run and committed artifacts match generator output. Generator unit tests: 48 passed (run at HEAD), including `test_python_bindings_deterministic`, bindings-block scoping, and class-name pinning. TODO entry and docstring TODO removed.
Assessment: accept.

### quality-3 — relabel verified
Dispositions doc now reads "Disposition: Fixed" with the Makefile policy comments and the efficiency-1 line removal as the action. Nothing deferred, no slug — label now matches substance.
Assessment: accept.

## Disputed items

None. All four round-1 disputed dispositions and the label correction were resolved as directed.

## Approved

19 findings: 15 Fixed verified (errhandling-1, errhandling-2, errhandling-4, correctness-1, correctness-2, security-1 interim warning, test-1, test-2, test-3, test-4, reuse-1, quality-1, quality-2, quality-4, efficiency-1) + quality-3 Fixed (relabeled), 2 Won't-Do sound (errhandling-3, test-5), 2 TODO dispositions acceptable (correctness-3; security-1 depth limit). Round-1 verified items not re-walked except where round 2 touched them.

---

## Verdict: APPROVED

All dispositions acceptable at HEAD 685e21a. Round 2.
