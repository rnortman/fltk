## errhandling-1

**File:line**: `fltk/unparse/gsm2unparser_rs.py:360` (`_gen_identifier_term_body`)

**The broken error path**: `assert isinstance(item.term, gsm.Identifier)` is used as an internal routing guard. If the dispatch in `_gen_term_body` is ever broken by a refactoring and the wrong term type reaches this method, the `AssertionError` carries no context: no rule name, no item, no type found vs. type expected.

**Why**: `AssertionError` is opaque. Running with `python -O` strips the assert entirely, letting the wrong type silently flow into `item.term.value` on the next line — producing either an `AttributeError` with an equally opaque traceback or, worse, silently using the wrong field value to generate plausible-looking but wrong Rust (e.g., a `Regex` value string used as a rule name in the recursive `unparse_` call).

**Consequence**: A generation-time invariant violation (misrouted term type) either aborts with an `AssertionError` that cannot be mapped to a grammar rule without reading the stack carefully, or — under `-O` — produces silently incorrect generated Rust that fails later at Rust compile time, at which point the Python generator is no longer in scope. On-call diagnosis requires re-running the generator under a debugger to recover the rule name.

**What must change**: Replace with an explicit `RuntimeError` that names the rule and the type found: `raise RuntimeError(f"Internal error: _gen_identifier_term_body reached with {type(item.term).__name__} term in rule {rule_name!r}")`. The same fix applies to the analogous `assert isinstance(item.term, gsm.Literal)` in `_gen_literal_term_body` (next finding).

---

## errhandling-2

**File:line**: `fltk/unparse/gsm2unparser_rs.py:387` (`_gen_literal_term_body`)

**The broken error path**: `assert isinstance(item.term, gsm.Literal)` — same class of problem as errhandling-1.

**Why**: Same mechanism: stripped by `-O`, no context in the `AssertionError` when not stripped. If a `Regex` or `Identifier` term is misrouted here, it has a `.value` attribute too, so `item.term.value` proceeds without error, using the regex pattern or rule name as the literal text to embed in `add_non_trivia(text("..."))`. The generated Rust compiles, produces wrong output, and the mismatch surfaces at unparse time as a formatting artifact with no generation-time signal.

**Consequence**: Silent generation of wrong Rust: the literal re-emission uses the regex pattern or rule name as the literal text. This is worse than a crash because it produces valid, quietly incorrect output. The failure manifests only at unparse parity test time (or not at all if the wrong text happens to match).

**What must change**: Replace with `raise RuntimeError(f"Internal error: _gen_literal_term_body reached with {type(item.term).__name__} term in rule {rule_name!r}")`.

---

## errhandling-3

**File:line**: `fltk/unparse/gsm2unparser_rs.py:462–489` (`_gen_child_prelude`)

**The broken error path**: When `need_tuple=False` and `item.label` is truthy, the function does not bind `child_tuple` (the `if need_tuple:` block is skipped) but then unconditionally emits the label check `if child_tuple.0 != Some(...)` which references `child_tuple`. The Python generator returns this string as the generated output without raising.

**Why**: The invariant "if `item.label`, then `need_tuple` must be `True`" is documented implicitly in the docstring but not enforced by the function. Current callers satisfy it (`_gen_validate_span_child` computes `need_tuple = bool(item.label) or num_variants > 1`; `_gen_identifier_term_body` always passes `need_tuple=True`), but the function itself has no guard. Future callers — or a refactoring that changes the call sites — can violate it without any Python-level signal.

**Consequence**: `generate()` returns a string containing Rust with an undefined variable `child_tuple`. The Python generator reports success. The failure surfaces only when the generated `.rs` file is compiled, as a Rust `error[E0425]: cannot find value child_tuple in this scope`, pointing to generated code. At that point the Python generator is not in scope and the mismatch between the generator's implied invariant and the emitted code is non-obvious.

**What must change**: Add a guard at the top of `_gen_child_prelude`: if `item.label and not need_tuple`, raise `RuntimeError` with the class name and item label. This converts a silent Rust compile failure into a Python generation-time error.
