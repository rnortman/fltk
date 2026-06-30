# Dispositions — prepass review (round 1)

Base: f0edfd757571310a83ac08a361c5af8ec4028001
Reviewed HEAD: 7682e2fa5461dbac03a7184911042944f97613bc
New HEAD (fixes): 19348b3a8900ae0eaf883f3f7b3531b029d9a814

Scope notes (`notes-prepass-scope.md`): "No findings." Nothing to disposition.

---

slop-1:
- Disposition: Won't-Do
- Action: no change (`docs/adr/2026/06/30-codegen-protocol-pyi-outputs/implementation-log.md` left in place)
- Severity assessment: Cosmetic. A non-code markdown doc; affects no build, runtime, or public-API surface. Worst case it is repo clutter.
- Rationale (Won't-Do): The slop reviewer operates "diff only, no surrounding-context investigation" and so flagged the log as a stray agent scratchpad. Fact-check refutes the premise: the file lives in a directory that is, by design, the review-chain working record for this change — alongside ~15 sibling process artifacts already committed there (`exploration.md`, `requirements.md`, `dispositions-design*.md`, `judge-verdict-design*.md`, `notes-design-*.md`, `notes-requirements-*.md`). Within that directory's established convention the incremental implementation log is one more such artifact, not an anomaly. Deleting it would discard the implementer audit trail the user's workflow deliberately commits and single out one artifact from a directory full of peers. Converting the frozen `design.md` into a final "context/decision/consequences" ADR is a separate, later step (CLAUDE.md ADR convention), not respond-mode work, and is not what the reviewer's suggested fix would accomplish.

slop-2:
- Disposition: Won't-Do
- Action: no change (design-section citations in `rust.bzl:119,141-143`, `genparser.py:480,546`, `gsm2tree_rs.py:434,436` left in place)
- Severity assessment: Cosmetic. Comment text only; no effect on behavior, types, or generated output.
- Rationale (Won't-Do): The reviewer's suggested fix is to "expand the sentence to say what the constraint actually is in plain English." That plain-English explanation is already present in every flagged comment — e.g. `rust.bzl:118-119` already reads "Mirror the CLI's `--protocol-output requires --protocol-module` check, surfacing the misconfiguration at analysis time" before the trailing `(§2.5)`; the § is a supplementary pointer, not a substitute for the explanation. The remaining ask — strip the bare § pointers — is contradicted by established house style: citing design sections in code comments is a pre-existing, pervasive convention in this codebase (`gsm2tree_rs.py:328` "§1 of the design", `:333` "design §2.8", `:410` "§3 of design", and `:1613/1621/1692/1716/1742/1751` "§2.3 lock discipline" all pre-date this change in the base commit). Per CLAUDE.md these design docs are committed as permanent ADRs at a stable path, so the references are durable and resolvable, not transient task context. Stripping the pointers from only this change's comments would make them stylistically inconsistent with the surrounding codebase while removing nothing the reader needs.

slop-3:
- Disposition: Fixed
- Action: `genparser.py:501-505` and `:752-756` (both `gen_rust_cst` and `gen_rust_unparser`) — replaced the misleading `if init_pyi_output is not None and init_pyi_text is not None:` double-None guard with `if init_pyi_output is not None:` + `assert init_pyi_text is not None` (the project's documented narrowing-assert idiom; S101 is ignored in non-test code per `pyproject.toml:100-101` precisely for this pattern). Verified: ruff + pyright clean, 27 marker/protocol tests pass.
- Severity assessment: Low in practice (the None branch was unreachable, so no real silent data loss could occur), but the guard genuinely misled: it implied `_render_init_pyi` could return None when `init_pyi_output` is set, which it cannot, and the silent-skip shape hid that invariant. The assert makes the impossible case loud and documents the contract.

slop-4:
- Disposition: Won't-Do
- Action: no change (local `import ast  # noqa: PLC0415` in `test_genparser.py` and `import ast as _ast  # noqa: PLC0415` in `tests/test_gsm2tree_rs.py` left in place)
- Severity assessment: Cosmetic. Test-only import placement; no effect on what the tests assert.
- Rationale (Won't-Do): The reviewer's argument is consistency — but fact-check shows the local-import-with-`# noqa: PLC0415` pattern *is* the established convention in both affected files, verified against the base commit: `test_genparser.py:185` already carried `import ast  # noqa: PLC0415` before this change (also `:370`, `:679`), and `tests/test_gsm2tree_rs.py` has 17 such local imports in the base commit (`re`, `pathlib`, `fltk.*`, etc.). The new tests copy the file's own pre-existing idiom. "Fixing" them to top-level would do the opposite of what the reviewer wants — it would introduce inconsistency, making `ast` the lone top-level import in files that deliberately import inside test bodies. `test_gsm2lib_rs.py` (the file the reviewer cites as the "correct" counter-example) is a different, smaller module with a different established style; it is not the convention `test_genparser.py`/`test_gsm2tree_rs.py` follow.
