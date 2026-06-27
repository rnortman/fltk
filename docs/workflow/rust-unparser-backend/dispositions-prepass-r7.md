# Dispositions — prepass r7

Fix commit: `1fcae0bbe0063b83b1883eb439ababc9da6916d4`

scope-r7: no findings.

slop-1:
- Disposition: Fixed
- Action: `crates/fltk-unparser-core/src/accumulator.rs:69-72` — trimmed the `last_was_trivia()` docstring's verbose consumer-logic narration ("...to skip emitting a fresh separator spec right after a trivia child was already consumed") down to a single line noting it is read by the generated separator processing, while retaining the `gsm2unparser.py:1266` port citation (the parity-maintenance convention used for every ported symbol in these files).
- Severity assessment: Cosmetic. The doc was an outlier in verbosity versus its terse sibling accessors; tightening improves consistency with no behavioral impact.

slop-2:
- Disposition: Fixed
- Action: `crates/fltk-unparser-core/src/accumulator.rs:292` — removed the redundant comment `// The public accessor mirrors the private flag the mutators set.` from the test `last_was_trivia_accessor_reflects_state`; the test name already states the intent.
- Severity assessment: Cosmetic. Redundant test comment, zero behavioral impact.

slop-3:
- Disposition: Won't-Do
- Action: no change.
- Severity assessment: Cosmetic at most, and the finding's premise is false.
- Rationale (Won't-Do): The finding's premise — that `separator_spec`'s docstring "opens its docstring with 'Port of…'" — is factually incorrect. The docstring opens with a behavioral description: `/// Build a [Doc::SeparatorSpec] control node — the default inter-token separator, resolved away at render time by [resolve_spacing_specs]` (`crates/fltk-unparser-core/src/doc.rs:242-244`). The "Port of…" line is the *second* paragraph and carries useful semantics (when `spacing`/`preserved_trivia` are absent, what `required` means). Citing the Python source line for each ported symbol is the deliberate, file-wide parity-maintenance convention (see the module docstrings and every struct/fn doc in `doc.rs`/`accumulator.rs`/`resolve.rs`, and the design's cross-backend-equivalence mandate). Removing this one citation would be inconsistent and would strip maintenance value. Doing so would actively harm the parity-tracking workflow the codebase relies on.

slop-4:
- Disposition: Won't-Do
- Action: no change.
- Severity assessment: Cosmetic / taste; touches "most of the new test functions" per the finding.
- Rationale (Won't-Do): These are *generator* tests that assert on the structure of emitted Rust (e.g. `test_trivia_rule_ws_required_consumes_whitespace`, `tests/test_rust_unparser_generator.py:1662`), so prose describing that structure is describing exactly what the assertions check — not duplication of a black-box outcome. Each docstring's first sentence already states the observable scenario ("A WS_REQUIRED gap in a trivia rule consumes the unlabeled whitespace Span and emits spacing"); the following sentences cite the ported Python source line, which is the codebase-wide parity-maintenance convention. Rewriting most test docstrings to strip the implementation context and Python citations would remove genuine maintenance value across the suite for a style preference, and would actively harm the parity-tracking workflow. The first-sentence summaries already satisfy "state what the test proves."

slop-5:
- Disposition: Fixed
- Action: `fltk/unparse/gsm2unparser_rs.py` — extended the `_gen_non_trivia_rule_processing` docstring to document that when `unparse__trivia` returns `None`, no separator spec is emitted (and `pos` still advances), explicitly noting this is a faithful port of Python's `if_trivia_success` having no `orelse` (`gsm2unparser.py:1321`). The finding's *other* suggested fix — adding an `else` arm that emits default spacing — is rejected: the Python backend (`gsm2unparser.py:1321`) has no `orelse` here, so emitting spacing in the Rust backend would create a Python/Rust rendered-string divergence, which the design's cross-backend parity mandate (design §2.4, CLAUDE.md "cross-backend behavioral equivalence") forbids.
- Severity assessment: The finding's "formatting regression / silent bug" framing is incorrect — the no-output-on-failed-trivia-unparse behavior is intentional, faithful parity with the Python backend, exercised under the same conditions there. The only actionable improvement was making the intent visible to a maintainer auditing the generator, which the docstring now does. No behavioral change.
