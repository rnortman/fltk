# Dispositions — regex-grammar-spike design vs. user design-gate directive

Source directive (authoritative, verbatim at
`burndown/regex-grammar-spike/notes-design-user.md`):

> One note: We should not hard-code a path to the clockwork.fltkg in anything we commit to
> the repo. We can provide the path as a CLI arg. And really nothing about this is
> clockwork-specific; we should be able to use the same script to extract regexes from any
> grammar file and test against them.

The directive carries three distinct, fact-checkable requirements. Each is dispositioned
separately below. Fact-check basis: the prior design already incorporated most of the
directive (it cites the directive throughout); this pass verified compliance line by line
against the design and the directive, and closed the one residual gap.

---

user-directive-1 (general/reusable tool — nothing clockwork-specific):
- Disposition: Fixed
- Action: Confirmed already honored and verified end-to-end in the design — no change
  needed beyond confirmation. The core capability is a general `collect_regexes(grammar)` +
  accept/reject classifier operating on **any** `gsm.Grammar`, wrapped by a grammar-agnostic
  CLI that takes an arbitrary `.fltkg` path argument (design §3.1, §3.4, §5 Inc 2–3, §8).
  The committed corpus test runs this same logic over in-tree grammars (`fegen.fltkg`,
  `regex.fltkg`); clockwork is just another input path to the identical tool (§3.4). The
  design explicitly states "Nothing clockwork-specific; it operates on any `gsm.Grammar`"
  (§5 Inc 2). The enumeration is programmatic via the GSM walk
  (`gsm._for_each_item`, `gsm.py:291-302`; exploration §6 `:248-304`), not a per-grammar
  hand-list, which is what makes it reusable across arbitrary grammars.
- Severity assessment: This is the substance of the directive's reusability mandate; the
  design satisfies it directly. No latent contradiction found on re-read.

user-directive-2 (path provided as a CLI arg, not hard-coded):
- Disposition: Fixed
- Action: Two residual hard-codings of the literal absolute path
  `/home/rnortman/tps/clockwork/clockwork/dsl/clockwork.fltkg` remained inside the committed
  design doc (§3.4 prose at old line 308, and the "Documented command" code block at old
  lines 326-327). The directive says "do not hard-code a path ... in anything we commit to
  the repo," and the design doc is itself committed under `docs/adr/`. The prior text even
  contained an internal contradiction: it claimed "nothing committed references this path"
  one line above a code block that printed the literal path. Fixed in design §3.4: the
  prose now states clockwork "lives only in the developer's own clockwork checkout" and that
  the directive applies to the design doc too; the documented command is now
  `uv run python -m fltk.fegen.regex_corpus <path/to/clockwork.fltkg>` with the developer
  supplying the path at the CLI. Verified post-edit: `grep` for `/home/rnortman/tps` and
  `~/tps` returns no match anywhere in `design.md`.
- Severity assessment: Without this fix the committed design doc would itself violate the
  directive's literal text and ship a stale machine-specific path that rots the moment the
  developer's checkout moves — exactly the brittleness the directive guards against. Low
  blast radius (doc-only, no code), but it was a real, direct contradiction of the
  authoritative directive.

user-directive-3 (no committed clockwork data or path; clockwork exercised ad hoc):
- Disposition: Fixed
- Action: Confirmed already honored and re-verified. The snapshot-fixture approach is
  removed: design states there is no committed `clockwork_regexes.json`, no snapshot helper,
  and no clockwork data of any kind (§3.4, §6 "Stale corpus enumeration", §7, §8 "NOT
  created", §9 retired O5). Committed corpus tests run only against in-tree grammars
  (`fegen.fltkg`, `regex.fltkg`); clockwork is exercised ad hoc via the general CLI with its
  path on the command line (§3.4, §5 Inc 3 acceptance: "the CLI may carry a small unit test
  that runs it over an in-tree grammar — never clockwork"). Strengthened the §3.4 wording so
  the "no committed clockwork path" claim is now literally true of the design doc as well
  (see user-directive-2). The §3.3 clockwork risk points (UUID `\b`, ` *`, `'?`) are
  retained only as documented expected dispositions for the developer's ad-hoc run, not as
  committed test pins.
- Severity assessment: Committing clockwork data or its path would create a CI dependency on
  an out-of-tree checkout that CI does not have, breaking the build for anyone without
  `~/tps/clockwork`, and would vendor third-party DSL data into FLTK. The design correctly
  avoids all of this.

---

Preserved intact per directive ("Keep the rest of the design intact"): the
codegen/Makefile wiring (§2), the accept/reject oracle (§3.2), the adversarial suite
including the explicitly-assigned Opus increment (§4, §5 Inc 4), and the increment
breakdown (§5). Increments were not re-cut — they were already structured around the general
tool (Inc 2 builds the general collector/classifier; Inc 3 wraps it in the grammar-agnostic
CLI and documents the ad-hoc clockwork run; Inc 4 remains the Opus adversarial increment).
The dependency note (Inc 3 depends on Inc 1 and Inc 2) is unchanged and correct.

Cleanup-editor not re-invoked: the design was already written to the directive; this pass
applied a single targeted contradiction fix in §3.4 (replacing a hard-coded path with a CLI
placeholder), which is a small fix-up, not a substantial structural edit.
