# Security review — Phase 4 runtime integration

Commit reviewed: cdffac4 (base f8a2fe1).
Note: Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Scope: changed code in `fltk/plumbing.py`, `fltk/fegen/fltk2gsm.py`, `fltk/fegen/genparser.py`,
`fltk/fegen/gsm2tree_rs.py`, generated `src/*.rs`, test fixture crates.

## Trust model

FLTK is a developer-facing parser-generator toolkit. The untrusted input across this diff is
**grammar text** (`.fltkg`) fed to `parse_grammar` / `parse_grammar_file`. The
backend-selection parameters (`rust_cst_module`, `rust_fegen_cst_module`, `gen-rust-cst`
output path) are **operator/developer-supplied**, same trust level as the calling code — not
an external/network boundary. Findings are weighted accordingly.

## Findings

security-1. `fltk/plumbing.py:78` — dynamic import of caller-supplied module name.
`_load_rust_cst_classes` calls `importlib.import_module(module_name)`, executing the named
module's top-level init code. Data flow: `module_name` originates from the application
developer's call to `generate_parser(..., rust_cst_module=...)` /
`parse_grammar(..., rust_fegen_cst_module=...)`. Consequence: if an application ever forwards
an *untrusted* string into this parameter (e.g. backend name from a config file, HTTP request,
or grammar-embedded directive), an attacker controls which installed module gets imported and
its import-time code runs — arbitrary code execution scoped to importable modules. No such
untrusted flow exists in this diff; the parameter is developer-controlled throughout. This is
a latent footgun, not an active vuln. Suggested: document in the function docstring that
`rust_cst_module` must be a trusted/static value, never derived from untrusted input;
optionally validate against an application-maintained allowlist of expected backend names.

security-2. `fltk/plumbing.py:214,240,384` — `exec()` of generated code (pre-existing,
unchanged trust). The Python backend still `exec`s AST compiled from the grammar
(`gen_py_module`) and the generated parser/unparser. The grammar is untrusted input that flows
into generated Python source which is then executed. This path predates the diff (the
`# noqa: S102` markers are not new) and the diff does not widen it — the Rust branch actually
*avoids* exec'ing CST code. Consequence: a malicious grammar that induces the generator to
emit attacker-chosen Python could achieve RCE at parser-generation time. Out of scope as a
*new* finding (no new code path), but flagged: the toolkit's core assumes grammars are trusted
developer artifacts. Suggested: none for this diff; record as a standing assumption if not
already documented.

security-3. `fltk/fegen/gsm2tree_rs.py:240` (and regenerated `src/cst_fegen.rs`,
`src/cst_generated.rs`) — runtime import target is a hardcoded literal, not interpolated.
The emitted Rust fetches the span sentinel via `py.import("fltk._native").getattr("UnknownSpan")`.
The module/attr names are fixed string literals in the generator, not derived from grammar
content, so no injection into the generated Rust import. The `GILOnceCell` is initialized via
`get_or_try_init` under the GIL — no data race, errors propagate as `PyErr` rather than the
prior `.expect()` panic (a robustness improvement). No finding; recorded to show the new
runtime-import seam was checked.

security-4. `fltk/fegen/genparser.py:268` — `gen-rust-cst` writes generated source to an
operator-supplied `output_file` path. Data flow: `output_file` is a CLI argument supplied by
the operator running the dev tool. No untrusted boundary crossed; path traversal is not
meaningful when the operator already controls the process and filesystem. No finding.

## Other checks (no findings)

- No hardcoded secrets/credentials/tokens in the diff (Python, Rust, Cargo.lock fixtures).
- No `unsafe`, no `std::process`/`Command`, no `env!` in the generated or fixture Rust.
- No SQL/command/template injection surfaces; no network fetch (SSRF n/a); no deserialization
  of untrusted data; no crypto; no redirects; no auth/authz surface (library code, no
  endpoints).
- `fltk2gsm.py` change is a mechanical `cst.X` → `self.cst.X` DI refactor plus a None-label
  filter; no new trust boundary.
- `sys.modules[module_name]` registration uses `fltk_grammar_{id(grammar)}` for both backends,
  unchanged from prior behavior; no new pollution vector.
