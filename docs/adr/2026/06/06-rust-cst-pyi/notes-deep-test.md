Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

Commit reviewed: c78a014.

---

test-1. `tests/test_fltk_native_stub.py:57-64` — `_stub_class_names()` is dead code and broken.

The function calls `_parse_stub()` (which does NOT annotate parent attrs on AST nodes) then
filters `isinstance(node.parent, ast.Module)`. `node.parent` is never set, so calling it raises
`AttributeError`. No test calls it — it's dead. The comment on line 74 says "annotate parents
for _stub_class_names() above" but that annotation happens only inside
`_stub_classes_with_members()`, in a different call to `_parse_stub()`.

Consequence: If anyone calls this function it silently does nothing useful (AttributeError
propagates through `isinstance`, which raises rather than returning False). No test exercises the
top-level-class-name filter for `_stub_class_names`, so it can drift without detection.

Fix: delete `_stub_class_names()` entirely (nothing uses it); or, if it's meant to be used in a
test assertion, fix it by annotating parents before the walk (as `_stub_classes_with_members`
does) and add a test that calls it.

---

test-2. `tests/test_fltk_native_stub.py:205-211` — `test_stub_members_exist_at_runtime` calls
`runtime_cls()` with no args as a fallback path.

The code is `hasattr(runtime_cls, member) or hasattr(runtime_cls(), member)`. PyO3 node classes
require at minimum a `span` argument to construct; calling `runtime_cls()` with no args raises
`TypeError`. The comment says this handles `Label` as a classattr, but `Label` is accessible via
`hasattr(runtime_cls, "Label")` (it is a classattr, accessible on the class object) — the
fallback `runtime_cls()` branch is never actually reached for any member in the current stub.
However, the code is written as though `runtime_cls()` can succeed, creating a latent failure if
the stub ever declares a member (e.g., an instance-only attribute) that is not on the class
object: the test would then raise `TypeError` from PyO3's constructor instead of asserting the
expected failure.

Consequence: If a future stub member genuinely requires an instance to observe, the test crashes
with `TypeError` rather than producing a useful assertion failure. The latent path gives false
confidence that instance-level member checking is covered.

Fix: remove the `or hasattr(runtime_cls(), member)` branch; instance construction with no args
is not valid for these PyO3 classes. Add an explicit check for `Label` as a classattr
(`isinstance(getattr(runtime_cls, "Label", None), type)`) if that specific case warrants
verification.

---

test-3. `fltk/fegen/test_genparser.py:181-202` — CLI test `test_gen_rust_cst_protocol_module_emits_pyi` uses a mismatched grammar/protocol pair and does not verify the emitted `.pyi` is valid.

The test invokes `gen-rust-cst` on `simple_grammar_file` (the `word := value:/[a-z]+/` grammar,
one rule named "Word") with `--protocol-module fltk.fegen.fltk_cst_protocol`. The generated stub
references `_proto.NodeKind.WORD`, `_proto.Word`, etc., which do not exist in
`fltk_cst_protocol.py`. The test asserts `result.exit_code == 0` and `"class Word:" in pyi_text`
— it never runs pyright on the output, so the stub's type validity is not verified.

Consequence: a bug in the emitter that generates syntactically correct but type-incorrect content
(e.g., wrong `_proto.` qualification, wrong member shape) passes this test. The matched-pair
pyright tests in `TestGeneratePyiConformance` only run for the fegen grammar, so the CLI wiring
is tested only via the malformed-but-file-exists path.

Fix: either (a) use a matched grammar+protocol pair (fegen grammar + `fltk_cst_protocol`) in
this CLI test, or (b) explicitly note in the docstring that this test only verifies file emission
plumbing and add a separate CLI test with the correct pair that also checks `.pyi` parsability
(`ast.parse()`) as a lightweight validity guard without requiring pyright.

---

test-4. `fltk/fegen/test_genparser.py:231-254` — `test_gen_rust_cst_rs_unchanged_with_protocol_module` does not check the exit code of the second `runner.invoke` call (the one with `--protocol-module`).

If the second invocation fails (e.g., `generate_pyi` raises), the output `.rs` file may not be
written or may be empty, and the assertion `output_rs_no_pyi.read_text() == output_rs_with_pyi.read_text()` would pass vacuously on empty-vs-empty strings or fail with an unhelpful message.

Consequence: An exception inside `.pyi` generation that also corrupts `.rs` output goes
undetected; the test passes if both writes fail identically.

Fix: add `assert result2.exit_code == 0` after the second invoke (mirror the pattern of the
other CLI tests), capturing `result2 = runner.invoke(...)`.

---

test-5. `tests/test_gsm2tree_rs.py` — no determinism test for `generate_pyi`.

`TestDeterministicOutput` covers `generate()` (the `.rs` emitter) but has no parallel test for
`generate_pyi()`. The `.pyi` emitter iterates `_rule_info()` which in turn iterates
`self.grammar.rules` (a tuple — deterministic) and `sorted(model.labels.keys())` (sorted —
deterministic). However there is no explicit guard, so any future introduction of a set/dict
iteration into `generate_pyi` would silently produce non-deterministic output.

Consequence: No test catches a regression to non-deterministic `.pyi` emission, which would cause
noisy committed-file diffs and flaky pyright checks.

Fix: Add a test in `TestDeterministicOutput` (or alongside it) that calls
`gen.generate_pyi(protocol_module)` twice on the same instance and asserts identical strings, and
a second call using two generator instances on the same grammar — matching the pattern of
`test_two_calls_produce_identical_strings` and `test_two_generator_instances_produce_identical_strings`.

---

test-6. `tests/test_gsm2tree_rs.py:TestGeneratePyiConformance` — no per-class conformance test for the PoC grammar; only fegen grammar is covered.

`test_fegen_per_class_no_cast_zero_errors` runs per-class no-cast checks on 14 fegen-grammar
classes. No parallel test runs the same check on the PoC grammar (Identifier, Items, Trivia).
The PoC grammar exercises exactly the same emitter code paths; if a conformance bug affects only
smaller grammars (e.g., missing accessor for a single-label rule), the fegen test would still
pass because the relevant class is present there too but the PoC-only code path is untested.

Consequence: A per-class conformance regression on a small grammar (single-label, no-Trivia
child types) would not be caught until a downstream consumer uses a small grammar.

Fix: Add `test_poc_per_class_no_cast_zero_errors` in `TestGeneratePyiConformance` using the PoC
grammar's classes (Identifier, Items, Trivia) — these exist in `fltk_cst_protocol` since they
share class names with the fegen grammar's `Identifier`, `Items`, `Trivia`.

---

test-7. `tests/test_gsm2tree_rs.py:TestGeneratePyiClasses:test_no_stub_local_class_names_in_annotations` — covers only the quoted-string form of forward references, not the unqualified bare name form.

The test `assert not re.search(r'"[A-Z][A-Za-z0-9_]*"', poc_pyi)` catches `"Grammar"` (as a
`from __future__ import annotations` string annotation using a stub-local name). But a bare
unqualified `Grammar` in an annotation (e.g., `def foo(self, other: Grammar) -> None`) would
also be stub-local and fail conformance, yet not be caught by this pattern.

Consequence: If the emitter accidentally emits `def extend_children(self, other: Identifier)` (bare, stub-local) instead of `_proto.Identifier`, the test does not flag it. The pyright
conformance tests would catch it, but only when pyright is available.

Fix: Supplement with a check that no annotation in the `.pyi` body (outside class definitions)
references an uppercase identifier without a `_proto.` prefix — e.g., check that the word-
boundary pattern `r'\b([A-Z][A-Za-z0-9_]*)\b'` in annotation contexts is always preceded by
`_proto.` or is one of the known non-proto names (`typing`, `None`, `fltk`, `Iterator`, `list`,
`tuple`, `Optional`, `Literal`, `Iterable`). Alternatively, rely on the pyright conformance
tests as the authoritative guard and document that this test is a fast pre-pyright lint only.
