Style: concise, precise, no padding. Audience: smart LLM/human.

# Dispositions — rust-cst-pyi prepass

## scope-1 — `fegen_cst.pyi` missing `# ruff: noqa: N802` header

Disposition: Won't-Do

Action: no change

Severity assessment: Benign. `make check` passes; the committed file is the canonical post-`make fix` output. The "discrepancy" is that ruff strips a directive it considers redundant, which is expected and correct behavior in the regen → `make fix` → commit flow documented in CLAUDE.md. No operational impact now or in foreseeable future unless ruff config changes to trigger N802 on this file, at which point regen + make fix would naturally reintroduce the directive.

Rationale: The CLAUDE.md "Generated Code and Formatting" section explicitly defines the intended workflow as: run generator → run `make fix` → commit the result. The committed file is exactly what that workflow produces. The generator emitting the header and ruff stripping it are both correct behaviors. There is no discrepancy worth fixing; the reviewer's "regen-and-diff discipline" concern is speculative and the suggested fix (removing the unconditional emission or adding a per-file-ignore) would be an optimization for a non-problem. Won't-Do because acting on it would change correct behavior to address a hypothetical future concern.

---

## scope-2 — Deviation in `generate_pyi`: `Label = _proto.Class.Label` and no module-level `<Class>: type[<Class>]` attrs

Disposition: Won't-Do

Action: no change

Severity assessment: Zero negative consequence. The shipped forms produce zero pyright errors in both self-check and conformance; the design-specified forms provably do not (implementation log Increment 3 documents the specific pyright errors). The deviation achieves the design intent better than the design specification. Implementation log entry at Increment 3 is the complete, accurate record.

Rationale: The design-specified forms (`Label: typing.ClassVar[type[_proto.<Class>.Label]]` and module-level `<Class>: type[<Class>]`) cause pyright `reportRedeclaration` errors in self-check and `"Label" is not defined as a ClassVar in protocol` errors in conformance. The shipped alternatives pass both. This is a case where the design's stated goal (zero-error self-check and conformance) is achieved by a technically superior alternative to the design's specified form. Fixing this would mean introducing pyright errors. Won't-Do.

---

## scope-3 — Deviation in §2.3: Python CST `span` annotation widening

Disposition: Won't-Do

Action: no change

Severity assessment: The annotation widening is a conservative, correct public-API change. Parsers have always assigned `fltk._native.Span` objects to `span` fields at runtime; the prior `terminalsrc.Span`-only annotation was already inaccurate. Downstream callers using narrowed local type annotations (`s: terminalsrc.Span = node.span`) gain a pyright error that flags their previously-incorrect annotation; callers using `node.span` directly are unaffected. The change is necessary: without it the repo pyright gate produces 676 errors once `fltk._native` is typed. Implementation log entry at Increment 4 is the complete, accurate record.

Rationale: The blast-radius enumeration in §2.3 did not predict this change, but the change was required and correct. The design's overall goal (repo-wide `uv run pyright` passes) mandated it. The out-of-tree consumer impact is the weakest possible breaking case: callers who wrote `s: terminalsrc.Span = node.span` had an annotation that was always wrong at runtime (parsers assign `fltk._native.Span`); pyright was just not catching it before. Won't-Do on any remediation.
