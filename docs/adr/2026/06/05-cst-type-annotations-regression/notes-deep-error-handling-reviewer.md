# Error-handling review notes — errhandling
## Commit reviewed: 0903a36

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

### errhandling-1

**File:line:** `fltk/fegen/gsm2tree.py:304`

**Broken path:** `protocol_annotation_for_model_types` contains `assert len(parts) > 0`.

**Why:** This assertion fires — as `AssertionError` with no message — when a node's model has zero child types (`model.types` is empty). The caller `_protocol_class_for_model` passes `model.types` directly; no caller guards against the empty-types case before calling. The `assert` is not a `# S101`-suppressed invariant with a diagnostic message; it carries no context about which rule triggered it, which grammar file was being processed, or what `model.types` contained.

**Consequence:** An empty-types node in a user grammar (legitimate for certain grammar patterns) crashes `gen_protocol_module` with a bare `AssertionError` during `genparser generate`. No file path, no rule name, no model state in the traceback. On-call cannot distinguish "generator bug" from "unsupported grammar shape". The partially-written `_cst_protocol.py` may or may not exist depending on timing; no cleanup is performed.

**Fix:** Replace the bare assert with `raise ValueError(f"Rule {class_name!r} has no child types in its model; cannot generate annotation")` (convert to a proper error with context). If the empty-types case is genuinely impossible given the GSM invariants, document that and add the context message anyway — a bare assert is never sufficient for a generator that processes user-supplied grammars.

---

### errhandling-2

**File:line:** `fltk/fegen/genparser.py:202` (protocol write block)

**Broken path:** `f.write(ast.unparse(protocol_mod))` — `ast.unparse` is called inside the `try` block that only catches `OSError`, but `ast.unparse` can raise `ValueError` (malformed AST) or any other exception if the generated AST is internally inconsistent.

**Why:** The existing CST write at line 187 (`f.write(ast.unparse(cst_mod))`) has the same pattern, but the protocol generator constructs `ast.ClassDef` nodes via `pygen.function` / `pygen.stmt` with dynamically-assembled argument strings. If `pygen.function` constructs an invalid AST node (e.g., from a malformed annotation string containing unbalanced brackets from `protocol_annotation_for_model_types`), `ast.unparse` raises. This exception is not caught, propagates through the Typer command handler, and surfaces as an unhandled traceback rather than a clean error message — inconsistent with the OSError handling immediately adjacent.

**Consequence:** Generator crashes with a raw Python traceback instead of a user-readable error message. The partially-opened file is left empty or truncated. No indication which grammar rule or annotation triggered the failure.

**Fix:** Expand the `try` to wrap both `gen_protocol_module()` and the `f.write(ast.unparse(...))` call, catching at minimum `ValueError` alongside `OSError`, with a message that names the output file and suggests checking the grammar. Alternatively, call `gen_protocol_module()` before opening the file so a generation failure does not leave a partially-written artifact.

---

### errhandling-3

**File:line:** `fltk/fegen/fltk2gsm.py:18` and `fltk/plumbing.py:148, 175–176`; `fltk/fegen/genparser.py:62`

**Broken path:** `cast("cstp.GrammarNode", result.result)` — `result.result` is the raw parse output, typed as an opaque object. The cast is a static-only no-op at runtime; it performs no structural check.

**Why:** This is the documented boundary cast for the nested-Label nominal mismatch, and the design explicitly accepts it. The error-handling concern is narrower: if `result.result` is `None` (parse failure slipped through the guard) or is a node of an entirely wrong type (e.g. the parser returned a different rule's node), the cast silently succeeds, and the first `AttributeError` surfaces deep inside `visit_grammar` / `children_rule()` with no indication that the cast was the source of the unsoundness. The `parse_grammar` guards (`if not result or result.pos != len(terminals.terminals)`) cover the `None`/incomplete-parse case, so this is a narrow residual gap rather than a live bug — but it is invisible to on-call.

**Consequence:** An internal parser bug returning a wrong-type node (not a user-input bug) would produce an `AttributeError` with a traceback pointing into `visit_grammar`, with no log entry explaining that the upstream parse result was unexpectedly typed. The existing guards reduce the probability; the gap is the absence of any logged diagnostic at the cast site if the node is structurally wrong.

**Fix:** Low priority given the guards. The mitigation is an `assert result.result is not None` with a message before each cast (the guards already enforce this by raising `ValueError`; make it explicit). A structured log line at the cast site naming the grammar source and backend in use would let on-call distinguish frontend/backend misroutes. Not blocking.

---

No other findings. The `OSError` handling on the protocol write (errhandling-2's `try/except OSError`) and the existing `ValueError` raises in `visit_disposition`, `visit_quantifier`, `visit_term` are correctly structured. The `cast` on `_DEFAULT_CST` at module level is correctly documented and bounded. Error propagation from `Cst2Gsm.visit_*` up through `parse_grammar` is clean — `NotImplementedError` and `ValueError` propagate without swallowing.
