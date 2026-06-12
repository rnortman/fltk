# Security review notes — rust-naming-shared (deep)

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Reviewed: cf3c54c..6893aa9 (`git diff cf3c54c..6893aa9`)
Scope: TODO.md, fltk/fegen/gsm2parser_rs.py, fltk/fegen/gsm2tree_rs.py

No findings.

Basis: pure generation-time naming refactor. New `RustCstGenerator.child_enum_name(class_name)` static method returns the identical string (`f"{class_name}Child"`) previously constructed inline at four sites; call sites delegate to it; TODO comment/entry removed. No change to escaping, input handling, trust boundaries, emitted code content, filesystem/network/auth/crypto surfaces, or secrets. Inputs to the helper (`class_name`) derive from grammar identifiers already constrained by existing validation; this diff neither widens nor relies on that constraint differently than before.

Adjacent pre-existing concern (out of diff, already tracked, not a finding here): `rust-str-lit-shared` TODO in TODO.md notes `gsm2tree_rs.py` embeds Rust string literals without an escaping helper; unchanged by this diff and unreachable per the identifier constraint cited in the design.
