# Deep efficiency review — codegen protocol + .pyi outputs

Commit reviewed: 19348b3a8900ae0eaf883f3f7b3531b029d9a814 (base f0edfd75)

No findings.

Scope check: the entire diff is build-time, one-shot codegen — new `generate`/`gen-rust-cst`/
`gen-rust-unparser` CLI flags, the `generate_protocol()` method, the `render_stub_package_init`
helper, and the Bazel/Makefile wiring. None of it runs in an application startup, per-request,
per-render, or polling hot path; it executes once per `make gencode` / Bazel action.

Specifically verified there is no wasteful work introduced:
- `generate_protocol()` (gsm2tree_rs.py) reuses the already-trivia-processed `self.grammar` —
  it does **not** re-parse the grammar file or re-run trivia classification.
- The grammar is parsed once (`_parse_grammar_raw`) per `gen-rust-cst` invocation; the protocol,
  `.pyi`, and `.rs` are each generated once.
- The second `CstGenerator` + `create_default_context()` inside `generate_protocol()` is
  constructed at most once per invocation and only when `--protocol-output` is set; it is required
  by design (§1.2 — needs a non-empty `py_module` for the `kind` Literal discriminant) and cannot
  reuse `self._py_gen`. One-shot cost, negligible.
- `_render_init_pyi` runs validation up front (before grammar parse), so a malformed marker fails
  fast without wasted parsing.
- Sequential file writes (.rs, protocol .py, .pyi, __init__.pyi) are intentional — the
  "generate all text before opening any file" contract preserves atomicity on error; parallelizing
  a handful of writes in a one-shot build action would add no meaningful benefit.
