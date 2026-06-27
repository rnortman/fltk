## slop-1

**File:** `fltk/unparse/gsm2unparser_rs.py` — `generate_pyi` docstring

**Quote:**
```
design OQ-3, user answer "Yes, emit .pyi"
design §2.4 settles it as purely additive
```

**What's wrong:** The `generate_pyi` docstring is 25+ lines of design-rationale narrative peppered with design-document cross-references ("OQ-3", "§2.4", "§2.3"). These are internal workflow breadcrumbs that mean nothing to a future reader who wasn't in the room. The actual method contract (inputs, outputs, side effects) is buried under process history.

**Consequence:** Code reads like an LLM filing a design-doc update rather than documenting a callable. Reviewers outside the immediate workflow will find the docstring actively misleading — the design refs are authoritative-sounding but point nowhere accessible.

**Fix:** Replace the docstring body with the method's actual contract: what `protocol_module` must be, what the returned string contains, and any invariants (e.g., callable independent of `generate()`). Strip every "design §N" / "OQ-N" / "user answer" phrase.

---

## slop-2

**File:** `fltk/unparse/gsm2unparser_rs.py` — `_gen_python_bindings` updated docstring

**Quote:**
```
Additively (design OQ-2, user answer "Please expose the intermediate Doc"), each rule
also gets an ``unparse_{rule}_doc(node) -> Option<PyDoc>`` method …
```

**What's wrong:** "user answer 'Please expose the intermediate Doc'" is a transcript of a design conversation, not documentation. Same pattern as slop-1.

**Consequence:** The docstring reads as an implementation diary rather than a spec for the generator method. Future maintainers learn nothing about invariants or calling conventions from the design-process prose.

**Fix:** Keep the behavioral description (what the `_doc` methods do, why `unsendable`). Drop the "user answer" attribution and design-document section numbers.

---

## slop-3

**File:** `fltk/fegen/genparser.py` — `gen_rust_unparser` docstring

**Quote:**
```
When --protocol-module is given, also emits a .pyi stub describing the
Unparser/Doc Python surface (design OQ-3) so downstream code is type-checked;
```

**What's wrong:** "(design OQ-3)" is a reference to an internal design document section embedded in a CLI help string / docstring that downstream users and tooling will see. It is noise outside the design-review workflow.

**Consequence:** CLI `--help` or generated docs will expose a meaningless parenthetical. Minor but visibly unpolished.

**Fix:** Drop "(design OQ-3)" — the sentence reads correctly without it.

---

## slop-4

**File:** `tests/test_rust_unparser_generator.py` — multiple test-body comments

**Quotes:**
```python
# `unsendable` is load-bearing: the core `Doc` uses `Rc` (the unparser-core crate is
# single-threaded by design §2.1), so a plain `#[pyclass]` would fail to compile …
# The field uses the fully-qualified path so no extra import is needed and it never collides
# with the header's `_uses_doc_type`-gated `use fltk_unparser_core::Doc;`.
# The string methods coexist (purely additive — design §2.4).
# An inspection affordance for the "or to inspect formatting" motivation (OQ-2).
```

**What's wrong:** Test-body comments reference design document sections ("§2.1", "§2.4", "OQ-2"). These are process breadcrumbs: the comments explain the *why-we-made-this-decision*, not *what-this-assertion-is-checking*. Some are also over-verbose restatements of what the assertion immediately below them already shows.

**Consequence:** Four tests read like annotated meeting notes. The signal-to-noise ratio for someone diagnosing a future failure is low; they must mentally filter process archaeology from test intent.

**Fix:** Replace design-doc references with the testable reason inline (e.g., "unsendable required because core Doc uses Rc" without "by design §2.1"). Delete or sharply trim comments that merely restate the assertion.
