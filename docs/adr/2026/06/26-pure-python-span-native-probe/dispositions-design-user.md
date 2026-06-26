# Dispositions: user notes on design

Source: `./notes-design-user.md` (authoritative — the user's own words; overrides prior design
decisions). Design revised in place: `./design.md`.

The note is a single directive: the "Python parser produces Rust CST" hybrid is a dead
intermediate development artifact with no use case and must be **removed**, not preserved. The
only two valid configurations are (1) Python parser ⇒ Python span ⇒ Python CST, and (2) Rust
parser ⇒ Rust span ⇒ Rust CST. Existing unit tests that enforce the hybrid path must be removed.
CLAUDE.md public-API constraints (backend-agnostic CST-consumer code; no forced downstream
annotation churn) stay intact.

Below: how it was applied, finding-style, with where each change landed.

---

design-user-1 (hybrid path removed from the design, not preserved):
- Disposition: Fixed
- Action: Rewrote §1.3 ("Two configurations only — the hybrid path is removed"). It now states the
  two valid configs explicitly, names the hybrid path
  (`generate_parser(rust_cst_module=...)` / `parse_grammar(rust_fegen_cst_module=...)`,
  `plumbing.py:120-183,212-297`), cites the user directive, and says the design deletes it.
  Added §2.3 ("Remove the hybrid plumbing") specifying deletion of the `rust_cst_module` /
  `rust_fegen_cst_module` parameters and the support code (`_load_rust_cst_classes`,
  `RustBackendUnavailableError`, `_fegen_rust_parser_cache`, `_load_fegen_grammar`, and the now-dead
  `importlib` import). Title changed to "Two backends only — Python parser ⇒ Python span + Python
  CST; Rust parser ⇒ Rust span + Rust CST."
- Severity assessment: This is the core of the user note; preserving the hybrid path would directly
  contradict an authoritative directive and leave dead, use-case-less code paths in shipped FLTK.

design-user-2 (codegen-time `native_span` selector removed — its only purpose was the hybrid path):
- Disposition: Fixed
- Action: Deleted the prior §2.1 "Codegen-time backend selection" section and the
  `CompilerContext.native_span` field / `create_default_context(native_span=...)` proposal and the
  selector table. §2.1 now states the Python parser constructs `terminalsrc` types
  **unconditionally** (both `_make_span_expr` and the `_source_text` initializer target
  `fltk.fegen.pyrt.terminalsrc`). §2.3 wiring no longer threads any selector; the in-memory exec'd
  parser still gets `from __future__ import annotations`. The `extract_span` "Rust CST ⇒ native
  span" forcing argument is retained only as the explanation (in §1.3) for *why* no selector is
  needed now, scoped out as internal to the all-Rust path.
- Severity assessment: Leaving a selector whose only consumer (the hybrid path) is gone would be
  dead configuration surface and a latent footgun (a way to make a "pure-Python" parser emit native
  spans again), reopening the exact bug this design fixes.

design-user-3 (identify hybrid-enforcing tests for removal by the implementer):
- Disposition: Fixed
- Action: Added §4.1 ("Hybrid-enforcing tests to be REMOVED by the implementer"), enumerating
  located sites with line refs: `fltk/test_plumbing.py` (`:20-21` imports;
  `TestRustBackendUnavailableError` `:386`; `_load_rust_cst_classes` tests `:406-452`, `:589`;
  `TestGenerateParserRustBackend` `:454`; `TestParseGrammarRustBackend` `:522`),
  `tests/test_phase4_fegen_rust_backend.py::TestAC8RealCst2GsmRustBackend` (`:59-108`),
  `tests/test_phase4_rust_fixture.py` (`_rust_pr` at `:54` and all tests consuming it),
  `tests/test_clean_protocol_consumer_api.py` (`:163`, `:360`). Distinguished kept tests: those
  that drive the **Rust parser** (config 2) or exercise Rust CST classes directly never used the
  hybrid plumbing (`TestRustParserSelfHosting`, `test_rust_parser_parity_*`,
  `test_rust_parser_*_bindings`, `test_cst_mutators_parity`) and stay green (§4).
- Severity assessment: Without this list the implementer would either leave failing tests that pin
  the deleted API or over-delete tests that legitimately cover config 2; the enumeration makes the
  cut precise.

design-user-4 (preserve CLAUDE.md public-API constraints — agnostic consumer code, no annotation
churn):
- Disposition: Fixed (constraint affirmed, not relaxed)
- Action: Kept §1.4 (dual role of `span.py`) and §2.4 ("What does NOT change — frozen public
  surface"): the `Span`/`SourceText` type-registry entries stay pointed at
  `("fltk","fegen","pyrt","span")`, so span-typed CST/protocol/`.pyi` annotations remain the
  agnostic `fltk.fegen.pyrt.span.Span` and are not churned. Reframed the rationale around the
  requirement that a consumer can *swap* config 1 ↔ config 2 without editing CST-consuming code.
  This is why §2.1 retargets construction via registry-independent module-qualified calls rather
  than by re-pointing the registry. §5 records the rejected "honest per-backend annotations"
  alternative on the same grounds.
- Severity assessment: Re-pointing the registry to `terminalsrc` would have been a simpler
  implementation but would rename a public annotation symbol on every span-typed child across all
  generated CST/protocol files — a breaking change for out-of-tree consumers, exactly what CLAUDE.md
  and the user note forbid.

---

Cleanup-editor pass run after the rewrite (substantial revision). No open questions remain that
are answerable by investigation; the one recorded decision (agnostic annotation surface kept) is a
design-rationale call, not a user-judgment question.
