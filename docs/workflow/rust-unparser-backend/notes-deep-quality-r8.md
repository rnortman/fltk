# Quality review — batch 8 (69fa04ef)

## quality-1

**File:** `fltk/unparse/gsm2unparser_rs.py:166`

**Issue:** `_node_param` scans raw Rust code strings that include string-literal content,
so a grammar literal whose text happens to be the word `"node"` produces a false positive.

For a required SUPPRESS literal or an INLINE literal whose value is `"node"`, the body
lines include `fltk_unparser_core::text("node")`.  The pattern `\bnode\b` matches `node`
inside the Rust string literal (`"` is a non-word character, so word boundaries fire on
both sides).  `_node_param` returns `"node"`, the generated method parameter is named
`node`, but the body never references it as a variable.  The resulting code compiles but
emits an `unused_variables` warning that fails `cargo clippy -D warnings`.

Both affected paths (`_gen_suppressed_item_body` at line 1070 and `_gen_literal_term_body`
INLINE branch at line 924) produce exactly this shape of body.

**Consequence:** A downstream grammar with `"node"` as a required-suppressed or INLINE
literal produces a generated unparser that fails the project's clippy gate.  `make check`
runs `clippy -D warnings` over all generated code; failure lands silently at compile time
with no diagnostic at generation time, breaking CI for real downstream consumers without a
clear root-cause pointer.  The pattern will propagate: every grammar that adds a `"node"`
token hits the same defect in every regeneration.

**Fix:** Strip Rust string-literal content before the `\bnode\b` search — e.g., replace
`re.search(r"\bnode\b", line)` with
`re.search(r"\bnode\b", re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '""', line))` — or switch
to a tracked-usage approach: have `_gen_suppressed_item_body` and `_gen_literal_term_body`
return a `(body, uses_node: bool)` pair so callers receive the answer without scanning,
eliminating the string-content ambiguity entirely.
