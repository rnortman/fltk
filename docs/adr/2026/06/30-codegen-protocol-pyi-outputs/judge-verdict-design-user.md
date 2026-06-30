# Judge verdict — design gate (user decisions)

Phase: design. Doc: `docs/adr/2026/06/30-codegen-protocol-pyi-outputs/design.md`. Round 1.
Authoritative input: `notes-design-user.md` (2 verbatim directives). Dispositions: `dispositions-design-user.md` (2 items, both Fixed).
Ground truth: the user's two decisions; the design is the artifact being adjudicated for fidelity.

## Findings walk

### user-decision-1 — "Yes we should generate the `__init__.pyi`" — Fixed
User directive (verbatim): "Yes we should generate the `__init__.pyi`". Context: resolves prior Open Question 1 (Bazel stub-package `__init__.pyi` needed for pyright stub-package resolution in the sandbox).

Disposition: generate and declare `{name}/__init__.pyi` in `generate_rust_parser` whenever `protocol_module` is set, via `ctx.actions.write` with a fixed comment body.

Evidence in design:
- Header Change-2 bullet: ".pyi stub ... together with a generated stub-package `__init__.pyi`, through `generate_rust_parser`." Present.
- §2.5: "It **also** generates and declares the stub-package marker `{name}/__init__.pyi` ... emits it directly via `ctx.actions.write` with a fixed comment body." Outputs table rows `set/False` and `set/True` both list `__init__.pyi`. Present.
- §2.6 retitled "Stub-package `__init__.pyi` is generated and declared (resolved)"; second paragraph rewritten from out-of-scope to generated/declared. Present.
- §3 (rust.bzl), §4 (sandbox-resolution bullet, now "Resolved"), §5 (Bazel test-plan), §6 item 1 (Resolved decisions) all updated consistently. Present.
- §2.7 / §6 correctly scope the decision to the Bazel rule and keep in-tree `fltk/_stubs/*/__init__.pyi` hand-authored.

Source-back on mechanism: both committed markers — `fltk/_stubs/fegen_rust_cst/__init__.pyi` and `fltk/_stubs/rust_parser_fixture/__init__.pyi` — are comment-only, no grammar-derived content (read in full). A static `ctx.actions.write` is the correct mechanism; routing through the CLI/generator would be unwarranted. The directive's "generate" means "have the build produce it" (vs. out-of-scope / consumer-supplied), which the design does at build time. Scoping to Bazel is faithful: Open Question 1 was Bazel-sandbox-specific.

Assessment: design faithfully incorporates the directive; mechanism is grounded. Accept.

### user-decision-2 — "yes it's fine to switch to requiring the protocol import path to be specified separately" — Fixed
User directive (verbatim): "yes it's fine to switch to requiring the protocol import path to be specified separately". Context: resolves prior Open Question 2 (requirement Change-2's "single opt-in" vs. the two-flag coupling), in favor of option (a) — import path is a required, explicitly-supplied input, never auto-derived from co-generating the protocol.

Disposition: confirm `--protocol-module` (Bazel `protocol_module`) as required input; remove the hedge / open question.

Evidence in design:
- Header Change-2 bullet: "whenever the protocol module's dotted import path is supplied explicitly (via `--protocol-module`) — a required input, never auto-derived from co-generating the protocol (resolved per `notes-design-user.md`; see §6)." Present.
- §2.2 deviation paragraph retitled "(user-confirmed)" and closes with "**User-confirmed resolution (`notes-design-user.md`):** the protocol import path is required input, specified separately via `--protocol-module` ... the two-flag coupling is the accepted design, not provisional." Hedge removed. Present.
- §6 item 2 records the resolution. Present.
- No lingering "Open Questions" section remains (§6 converted to "Resolved decisions"); no residual "pending user confirmation" wording.

Source-back on rationale: `gsm2tree_rs.py:345` is `import {protocol_module} as _proto` — the `.pyi` interpolates the dotted import path, which is independent of any output file path, so it cannot be auto-derived from a protocol-output file path. `genparser.py:381-383` already couples `--pyi-output` to `--protocol-module`. Requiring the import path separately is structurally necessary and consistent with the established pattern.

Assessment: design faithfully incorporates the directive; rationale is grounded. Accept.

## Disputed items

None.

## Approved

2 dispositions: both Fixed, both faithfully fold the user's verbatim directive into the design with grounded mechanism/rationale and no lingering hedges or open questions.

---

## Verdict: APPROVED

Both user decisions are faithfully incorporated. Decision 1 (generate `__init__.pyi`) is reflected across the header, §2.5–§2.6, §3–§5, §2.7, and §6, with a grounded static-`ctx.actions.write` mechanism (the committed markers are comment-only). Decision 2 (require the protocol import path separately) is reflected in the header, §2.2 (hedge removed, user-confirmed), and §6, grounded in the `.pyi`'s structural dependence on the dotted import path. No contradictions; no open questions remain.
