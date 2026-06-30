# Dispositions: user design decisions (respond round)

Design: `design.md` (this directory). Inputs: `notes-design-user.md` (user decisions, authoritative —
these resolve the design's two open questions).

The two user directives were fact-checked against source before applying, then folded into `design.md`
and the prior Open Questions (§6) were converted to a recorded "Resolved decisions" section.

---

user-decision-1 (notes-design-user.md item 1: "Yes we should generate the `__init__.pyi`"):
- Disposition: Fixed
- Action: Resolves prior Open Question 1 (Bazel stub-package `__init__.pyi`). Edited `design.md`:
  §2.5 `protocol_module` attr now generates and declares `{name}/__init__.pyi` (alongside `cst.pyi`)
  whenever `protocol_module` is set, emitted via `ctx.actions.write` with a fixed comment body; §2.5
  outputs table updated (`__init__.pyi` added to both `set/False` and `set/True` rows); §2.6 retitled
  and its second paragraph rewritten from "out of scope" to "generated and declared (resolved)", first
  paragraph generalized so both `.pyi` files flow benignly into the `fltk_pyo3_cdylib` genrule; header
  Change-2 bullet, §3 `rust.bzl` bullet, §4 sandbox-resolution bullet, and §5 Bazel test-plan paragraph
  updated to match; §2.7 gained a note that the in-tree `fltk/_stubs/*/__init__.pyi` markers stay
  hand-authored (the decision is Bazel-scoped); §6 records the resolution.
- Severity assessment: Without this, pyright stub-package resolution would fail in a Bazel sandbox —
  `cst.pyi` would be declared but the directory would lack the `__init__.pyi` marker pyright needs to
  treat `{name}/` as a stub package, so the exposed `.pyi` would be unresolvable for downstream consumers.
- Grounding: Both committed `__init__.pyi` files are comment-only stub-package markers with no
  grammar-derived content (`fltk/_stubs/fegen_rust_cst/__init__.pyi`,
  `fltk/_stubs/rust_parser_fixture/__init__.pyi`), so a static `ctx.actions.write` is the correct
  mechanism — no CLI/generator surface is warranted.

user-decision-2 (notes-design-user.md item 2: "yes it's fine to switch to requiring the protocol import
path to be specified separately"):
- Disposition: Fixed
- Action: Resolves prior Open Question 2 (two-flag coupling vs single opt-in) in favor of option (a):
  the protocol import path is required input, supplied explicitly via `--protocol-module` (Bazel
  `protocol_module`), never auto-derived from co-generating the protocol. Edited `design.md`: header
  Change-2 bullet reworded to "supplied explicitly (via `--protocol-module`) — a required input, never
  auto-derived"; §2.2 deviation paragraph retitled "(user-confirmed)" and its closing sentence changed
  from "recorded as Open Question 2 ... written assuming the user accepts" to a "User-confirmed
  resolution" statement; §6 records the resolution. The CLI/Bazel behavior in §2.2/§2.5 was already
  written assuming (a), so this directive confirmed the existing surface rather than changing it.
- Severity assessment: Low behaviorally (the design already implemented (a)); the edit removes a hedge
  and the open question, so an implementer no longer ships a surface marked "pending user confirmation."
- Grounding: The `.pyi`'s `import {protocol_module} as _proto` line (`gsm2tree_rs.py:345`) needs the
  dotted import path, which is independent of any output file path; the existing CLI already couples
  `--pyi-output` to `--protocol-module` (`genparser.py:382-384`), so requiring the import path
  separately is structurally necessary and consistent with the established pattern.
