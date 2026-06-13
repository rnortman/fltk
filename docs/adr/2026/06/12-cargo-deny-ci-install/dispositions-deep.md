## Dispositions — cargo-deny CI split (deep review, round 1)

---

security-1:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: CI no longer independently enforces the cargo-deny supply-chain gate; a PR introducing a crate with a known RustSec advisory, disallowed license, or unknown source will pass CI green. The local precommit hook provides partial but bypassable coverage.
- Rationale (Won't-Do): This is the explicitly accepted trade-off recorded in the ADR (Consequences section). The ADR evaluated all three options for running cargo-deny in CI (cargo install, binstall action, binary caching) and decided the cost is not worthwhile. Undoing or mitigating this in respond mode would contradict a deliberate user-authorized architectural decision. The mode instructions explicitly direct Won't-Do disposition for security findings that restate this trade-off.

---

security-2:
- Disposition: Fixed
- Action: Makefile:61 — changed `check: check-common` to `check: check-ci`. The one-sanctioned-divergence relationship is now enforced structurally by Make: `check` → `check-ci` → `check-common`. A future developer adding a step directly to `check` would have to bypass a structurally visible dependency chain, not just ignore a comment. Removed both TODO comments (antidrift-structural and check-capture-macro) from the Makefile header; the reuse-1 macro extraction was not implemented (see reuse-1 disposition). Updated the recipe comment to document the structural intent.
- Severity assessment: Was low immediate risk; now structurally enforced. No behavioral change to existing targets.

---

reuse-1:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: 8-line duplication at two adjacent sites; no correctness risk. The judge flagged this as borderline ("nit-level") and said it was not independently load-bearing. A Make `define`/`call` macro is viable but the shell idiom is already clear and the sites are immediately adjacent in the file. The structural fix for security-2 was the priority; the macro extraction adds cosmetic value at the cost of Make-macro indirection that makes the recipe harder to read.
- Rationale (Won't-Do): The judge explicitly marked this as nit-level and "not independently load-bearing," stating only to fold in if convenient at the same time as security-2. The duplication is cosmetic; the two sites differ only in the step name string, are immediately adjacent, and a reader can see both in one screen. Make `define`/`call` macros reduce line count but add an indirection layer that obscures what each recipe actually does. The cost (readability) exceeds the benefit (deduplication of a 2-site, never-diverged idiom).

---

quality-1:
- Disposition: Fixed
- Action: Makefile:36-38 — replaced the contradictory comment ("DO NOT ADD STEPS HERE DIRECTLY") with "ADD new steps here by appending the target name to the `steps` string below. / DO NOT add new steps directly to `check` or `check-ci` — they inherit via this target."
- Severity assessment: The old comment told readers not to add steps to `check-common`, which is exactly where they should add them. A developer reading only the recipe-level comment (the most local guidance) would be directed to add steps directly to `check` or `check-ci`, the exact violation the anti-drift rule prohibits.
