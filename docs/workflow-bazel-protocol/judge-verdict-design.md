# Judge verdict — design review

Phase: design. Doc: `docs/workflow-bazel-protocol/design.md`. Round 1.
Notes: 1 reviewer file (design-reviewer); 3 findings, all dispositioned Fixed.

## Other findings walk

### design-1 — Fixed
Claim: §2 "Stub exposure" paragraph reads unconditional; adding `<name>/cst.pyi` / `<name>/__init__.pyi` / `cst_protocol.py` labels to `py_library.data` unconditionally references files that are declared only under `if protocol_module:` / `if generate_protocol:` (`rust.bzl:138-164`).
Consequence: the design's own explicitly-valid `python_extension = True`, `protocol_module = ""` case fails at analysis time with a Bazel "no such target" error — real correctness consequence for a listed happy path. Finding stands.
Design as revised: §2 "Output routing" (lines 89-104) introduces `OutputGroupInfo(rust_srcs, stub_srcs)`; `stub_srcs` is an **empty depset** when `protocol_module` is empty, gains `cst.pyi`/`__init__.pyi` when set, and `cst_protocol.py` only when `protocol = True`. "Stub exposure" (lines 158-168) now adds the `stub_srcs` **group** (not enumerated file labels) to `data`, so the `protocol_module = ""` case adds nothing and references no undeclared file — self-gating.
Assessment: fix addresses the consequence. It also correctly notes the reviewer's literal suggestion (cherry-pick `<name>/cst.pyi` by label) is not expressible in a macro, and routes via output groups instead — a stronger fix than the finding proposed, grounded in the Bazel macro/label constraint (lines 99-104). Accept.

### design-2 — Fixed
Claim: the crate-assembly genrule (`rust.bzl:395-397`) copies every file in the internal target's `DefaultInfo`; when `bootstrap_native` sets protocol, `.pyi`/`.py` land in the flat crate root as undeclared genrule outputs — first-exercised path, unnamed in the test plan.
Consequence: reviewer states almost-certainly-harmless (Bazel discards undeclared outputs) but a genuinely new interaction that could fail under a stricter execution strategy — should-fix at most. Finding is honest about its own severity.
Design as revised: §2 macro bullet (lines 146-148) states crate assembly consumes **only the `rust_srcs` output group**, so `.pyi`/`.py` never enter the crate root. Edge-cases adds "Stub/protocol files must not reach crate assembly" (lines 230-238). Test plan asserts the assembled crate root contains exactly `lib.rs`/`cst.rs`/`parser.rs` (lines 260-262).
Assessment: the `rust_srcs`-group routing removes the interaction entirely rather than merely documenting it, and the test plan now names it. Fix exceeds what the finding asked. Accept.

### design-3 — Fixed
Claim: §3 removes `fltk_pyo3_cdylib` from the public surface but the module docstring load example (`rust.bzl:13`) and two doc-string references (`rust.bzl:89`, `rust.bzl:251`) still name it.
Consequence: after the change the file's own documented load example advertises a removed symbol, misleading out-of-tree source readers. Doc hygiene, low severity — but consistent with the design's stated attention to surface changes. Finding valid.
Design as revised: §3 (lines 182-185) now explicitly instructs updating the module docstring load example (`rust.bzl:13`) plus the `rust.bzl:89` and `rust.bzl:251` references alongside the load removal.
Assessment: fix names the exact three sites the finding cited. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified. Each fix is present in the revised design, addresses the reviewer's stated consequence, and (for design-1/design-2) resolves the deeper implementability issue via output groups rather than the finding's literal-but-unimplementable suggestion.

---

## Verdict: APPROVED

All three dispositions acceptable. Fixes verified against the revised design text; no open consequence remains.
