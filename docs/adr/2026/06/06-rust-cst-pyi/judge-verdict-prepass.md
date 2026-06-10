# Judge verdict — prepass

Style: concise, precise, no padding. Audience: smart LLM/human.

Phase: prepass. Base 46a6639..HEAD c78a014. Round 1.
Notes: notes-prepass-slop.md (no findings), notes-prepass-scope.md (3 items). Design ground truth: design.md + notes-design-user.md.

## Added TODOs walk

None. Diff adds no new `TODO(slug)` comments. The only `TODO(` additions in the diff are: an implementation-log sentence recording *removal* of `TODO(rust-cst-pyi)` (comment at `genparser.py` and the `TODO.md` entry, both removed per design §2.1/§2.4 — verified in diff stat: `TODO.md` -4 lines), and a cross-reference to pre-existing `TODO(gencode-poc-fltkg)` in the `fltk/_native/__init__.pyi` header, which design §2.3 explicitly mandates ("Document the omission in the stub header, cross-referencing `TODO(gencode-poc-fltkg)`").

## Other findings walk

### scope-1 — `fegen_cst.pyi` missing `# ruff: noqa: N802` header — Won't-Do
Claim: generator unconditionally emits the noqa header (`gsm2tree_rs.py:123`, verified) but committed `fltk/_native/fegen_cst.pyi` lacks it (verified: file starts `from __future__ import annotations`); consequence stated by reviewer as "benign at the moment", "low operational impact", spurious diff only if a future ruff version/config makes N802 fire.
Mechanism verified: `make fix` runs `ruff check --fix` (`Makefile:29-31`) with `RUF` in the select list (`pyproject.toml` lint.select), so RUF100 deterministically strips the unused noqa. The committed file is therefore exactly the regen → `make fix` output; CLAUDE.md "Generated Code and Formatting" defines that as the canonical flow, and `make check` passes (implementation-log Increment 4; reviewer concurs).
Responder rationale: no regen-diff drift exists under the documented flow; the concern is hypothetical; if N802 ever fires, regen + `make fix` reintroduces the directive naturally.
Assessment: severity nit; consequence is explicitly speculative and the reviewer's own summary line is "No findings." Won't-Do rationale is factually grounded against the documented workflow. Accept.

### scope-2 — `generate_pyi` deviation: `Label = _proto.<Class>.Label`, no module-level `<Class>: type[<Class>]` attrs — Won't-Do
Claim: design §2.1 specified `Label: ClassVar[type[_proto.<Class>.Label]]` and module-level attrs; shipped form deviates. Reviewer's own suggested fix: "None. Accept as-is."
Verified: committed stub uses `Label = _proto.Grammar.Label` (`fegen_cst.pyi:13`) and contains zero module-level `<Class>: type[<Class>]` attrs. Implementation-log Increment 3 records the deviation with the specific pyright failures of the design-specified forms (`reportRedeclaration` in self-check; `"Label" is not defined as a ClassVar in protocol` in conformance) and that the shipped forms pass both — pinned by `TestGeneratePyiSelfCheck` and `TestGeneratePyiConformance` (whole-module + 14 per-class no-cast fixtures, zero errors).
Assessment: the design's stated acceptance target (§2.2/§4: zero-error self-check and no-cast conformance) is met; the design-specified surface forms provably cannot meet it. Logged deviation achieving design intent is the correct outcome; reviewer requested no action. Accept.

### scope-3 — Python CST `span` annotation widened to `terminalsrc.Span | fltk._native.Span` — Won't-Do
Claim: §2.3 blast-radius enumeration did not predict this; four Python CST concrete files regenerated outside the §2.4 list. Reviewer: "the change is necessary and correct"; migration note "good hygiene but is not a scope gap"; suggested fix: none.
Verified in diff: `gsm2tree.py` emits the union; `fltk_cst.py`/`bootstrap_cst.py`/`toy_cst.py`/`unparsefmt_cst.py` regenerated with `span: terminalsrc.Span | fltk._native.Span` (matches the protocol union at `fltk_cst_protocol.py:89` cited in design §3, which mandates "exactly that union" for conformance). Implementation-log Increment 4 records the deviation and the 676-error pyright cascade that forced it once `fltk/_native` became typed — the design's own acceptance gate (§2.3: repo-wide `uv run pyright`) mandated the fix.
CLAUDE.md out-of-tree-consumer check: union widening, not renaming; call sites using `node.span` values unaffected; only downstream re-annotations `s: terminalsrc.Span = node.span` newly error — and those were already runtime-wrong (the `fltk.fegen.pyrt.span` selector prefers `fltk._native.Span`, so parsers assign it at runtime). Deliberate and called out (implementation log + reviewer note + this verdict), satisfying CLAUDE.md's "deliberate, called-out decision" bar.
Assessment: Won't-Do on remediation is sound; reviewer requested no action. Accept.

### §2.1a spot-check (design-mandated public-API removal)
Not a finding, verified as ground truth for the above: `CstModule.Span` property absent from regenerated `fltk_cst_protocol.py` (grep: no `def Span` property), per §2.1a and the user's OQ-A decision.

## Disputed items

None.

## Approved

3 findings: 3 Won't-Do sound (all three were informational/no-action items; the reviewer's own summary was "No findings"). 0 Fixed, 0 TODOs.

---

## Verdict: APPROVED

All dispositions acceptable. No new TODOs introduced; `TODO(rust-cst-pyi)` removed per design. Slop reviewer reported no findings.
