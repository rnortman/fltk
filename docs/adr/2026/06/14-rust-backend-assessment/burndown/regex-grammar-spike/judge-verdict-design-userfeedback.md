# Judge verdict — regex-grammar-spike (design phase, post-approval user-feedback revisions)

Phase: design. Doc: `burndown/regex-grammar-spike/design.md`. Round 1.
Scope: adjudicate two post-approval revisions made in response to user direction, against the
already-APPROVED design (`judge-verdict-design.md`).
- Directive 1 (general CLI tool; no committed clockwork path/snapshot; in-tree corpora committed;
  clockwork ad hoc) — source `notes-design-user.md`, dispositions `dispositions-design-user.md`.
- Directive 2 (grammars parsed as UTF-8 → adversarial suite must include UTF-8 characters) —
  source/finding `exploration-utf8.md`, dispositions `dispositions-design-utf8.md`.
(Design phase — no added-TODOs walk.)

## Other findings walk

### user-directive-1 (general/reusable tool — nothing clockwork-specific) — Fixed (confirm)
Claim/intent: the tool must extract and test regexes from ANY `.fltkg` file; nothing
clockwork-specific. Consequence (implied): a clockwork-coupled tool can't serve as the general
recognizer the lint will reuse and bakes an out-of-tree dependency into a reusable component.
Design check: core capability is `collect_regexes(grammar)` + accept/reject classifier over any
`gsm.Grammar` (§3.1), enumerated programmatically via the GSM walk (`gsm._for_each_item`,
`gsm.py:291-302`) — not a per-grammar hand-list — wrapped by a grammar-agnostic CLI taking an
arbitrary `.fltkg` path (§3.1, §3.4). §5 Inc 2 states "Nothing clockwork-specific; it operates
on any `gsm.Grammar`." Committed corpus runs the identical logic over in-tree grammars; clockwork
is just another input path (§3.4).
Source check: `gsm.py` `_for_each_item` depth-first item walk including sub-expressions confirmed
in the prior verdict's source check (design-4); the enumeration mechanism is real and reusable.
Assessment: directive honored; the reusability is structural (programmatic GSM walk, one collector
shared by corpus test + CLI), not asserted. Accept.

### user-directive-2 (path via CLI arg, not hard-coded in anything committed) — Fixed
Claim/intent: do not hard-code a path to clockwork.fltkg in anything committed; provide it as a
CLI arg. The design doc is itself committed under `docs/adr/`. Consequence: a committed literal
machine path (`/home/rnortman/tps/...`) violates the directive's literal text and rots the moment
the developer's checkout moves; the prior text even contradicted itself (claimed "nothing committed
references this path" one line above a code block printing the literal path).
Source check (post-edit): `grep` for `tps`, `/home/rnortman`, `~/tps` in `design.md` → **no match**.
The documented command (design.md:329) is now `uv run python -m fltk.fegen.regex_corpus
<path/to/clockwork.fltkg>` — a placeholder, developer-supplied at the CLI. The residual
`clockwork.fltkg:NNN` mentions that remain (lines 185-186, 291, 295-296, 308, 312) are bare
filename:line citations documenting expected dispositions, **not** filesystem paths to the file —
they do not let CI or anyone locate the out-of-tree file, so they do not violate "hard-code a path."
Assessment: the one residual contradiction (literal absolute path in §3.4 prose + code block) is
removed; the documented command is grammar-agnostic with a placeholder; the directive now holds of
the design doc itself. Fix matches the consequence. Accept.

### user-directive-3 (no committed clockwork data or path; clockwork exercised ad hoc) — Fixed
Claim/intent: commit no clockwork data and no clockwork path; exercise clockwork ad hoc. Consequence:
a committed `clockwork_regexes.json` or snapshot helper creates a CI dependency on an out-of-tree
checkout CI does not have (breaking the build for anyone without `~/tps/clockwork`) and vendors
third-party DSL data into FLTK.
Source check: `find` for `*clockwork*` / `*snapshot*` / `*regexes.json*` under the spike dir →
**none**. In `design.md`, every "snapshot / provenance / clockwork_regexes / JSON" mention
(lines 313-315, 337-338, 682, 725, 758-759, 790-791) is a **negation** — explicitly stating the
snapshot-fixture approach is removed and nothing of the kind is committed. §3.1 lists the committed
corpus as in-tree only (`fltk/fegen/fegen.fltkg`, `fltk/fegen/regex.fltkg`); §3.4 routes clockwork
through the ad-hoc general CLI; §5 Inc 3 acceptance says any CLI unit test runs "over an in-tree
grammar — never clockwork"; §8 "NOT created" enumerates no clockwork artifacts.
Supersession note: this directive correctly **overrides** the original approved disposition design-4
(which had mandated a snapshot helper reusing `collect_regexes` + a JSON provenance header). The
snapshot path is gone entirely; the single-source-of-truth `collect_regexes` collector survives and
is now reused by the CLI instead of a snapshot helper (§3.1, §3.4). No stale snapshot language
contradicts the directive.
Assessment: no committed clockwork data or path anywhere in the tree; clockwork is ad hoc via the
general CLI; the former snapshot O5 is retired. Directive honored. Accept.

### utf8-directive (grammars parsed as UTF-8 → adversarial suite must include UTF-8) — Fixed
Claim/finding: FLTK reads grammar files and parser input as Unicode and indexes by codepoint at
every layer; non-ASCII content is legal and structurally reachable, so the adversarial suite MUST
include UTF-8 cases. Consequence: an ASCII-only suite gives **zero** coverage of the codepoint↔byte
off-by-one / span-length / Unicode-category-table divergence bug class — the in-tree corpora are all
pure ASCII, so the adversarial suite is the only place this hazard is probed; omitting it ships the
spike's central "the grammar works" claim with a verified blind spot.
Source check (exploration accurate to source):
- Python: `terminalsrc.py` stores the input `str`, uses `len()` (codepoints) and indexes
  char-by-char (`consume_literal`), and passes a codepoint `pos` to `re.compile(regex).match(...,
  pos=pos)` — verified in source; `parse_text` success predicate is `result.pos !=
  len(terminals.terminals)` (`plumbing.py:323`), confirmed. All grammar-read `open()` calls carry
  **no `encoding=`** argument (`plumbing.py:55-56,206`) — confirmed, so the UTF-8/locale model the
  exploration describes is real.
- Rust: `terminalsrc.rs` builds a `cp_to_byte` table (one entry per codepoint + `text.len()`
  sentinel), declares "All external positions are codepoint indices (i64), matching Python's
  string-indexing semantics," and converts a regex match-end byte offset back to a codepoint via
  `partition_point` binary search — confirmed in source, exactly as exploration §2 states. This is
  the machinery the "multi-byte at non-zero offset" and "astral-plane 4-byte path" cases exercise.
- Empirical: `re` default flags = 32 (`re.UNICODE`); `re.match(..., pos=N)` is a codepoint offset
  (`café monde` matches at pos=5, not pos=6); `𝄞` = U+1D11E, 1 Python codepoint / 4 UTF-8 bytes;
  NFC `é` (1 cp) ≠ NFD `é` (2 cp). Every UTF-8 ACCEPT-pin pattern in §4.2 (`café`, `αβγ`, `中文`,
  `a𝄞b`, `é+`, `中*`, `[é]`, `[中-中]`, `[a-zé]`, `\w+`, ` a`, ` *`) `re.compile`s cleanly — so the
  §4.1 ACCEPT-direction Python `re` cross-check will pass for them, as the design claims.
- Grammar admits the cases: `class_char := /[^\\\]\[\-\n]/` excludes only ASCII metacharacters, so
  `[é]`/`[中-中]`/`[a-zé]`/`[αβγ]` parse as ordinary class members; `assertion := /[bB]/` and
  `class_shorthand := /[dDwWsS]/` admit top-level `\b`/`\w`/`\s` for the Unicode-shorthand cases
  (`regex.fltkg`, verified).
Design check: §4.2 carries a **required** "UTF-8 / non-ASCII probes" category covering exactly the
exploration §6 obligations — multi-byte literals, multi-byte at non-zero offsets, in-class non-ASCII
(incl. range endpoint), Unicode `\w`/`\s`/`\b` shorthands, NFC-vs-NFD combining marks, astral-plane
1-codepoint span, and bidi/RTL — each tied to the specific hazard it stresses. §4.3 ("Why the UTF-8
cases are required (not optional)") grounds the requirement in the verified source facts and states
the directive verbatim. Crucially, the design draws the correct scope boundary: the cases assert
**grammar acceptance** and the `rationale` must *name* the cross-engine match-set parity risk
(Unicode tables, normalization) as owned by the differential-property-harness (lint §9), since the
single-backend Python oracle cannot prove cross-engine match equality (§4.2 Unicode-shorthand bullet,
§4.3 scope boundary). §4.1's ACCEPT-only Python `re` cross-check applies, which is sound here.
Assessment: the directive is honored and the cases are accurate to the exploration, which is itself
accurate to source. The codepoint model, the `cp_to_byte` 4-byte path, the astral-plane / NFC-NFD /
multi-byte-offset claims, and the grammar's admission of each case all verify. The design does not
over-claim — it asserts only grammar acceptance and explicitly flags the out-of-scope match-set
parity rather than silently assuming it. Accept.

## Disputed items

None. Both directives are fully honored; the UTF-8 cases are accurate to the exploration and to
source; no committed clockwork path/data/snapshot remains; the general CLI is grammar-agnostic.

## Approved

4 dispositions (3 user-directive + 1 utf8-directive): all Fixed, all verified.
- No committed clockwork path/data/snapshot anywhere in the tree (`find` + `grep` clean); documented
  command uses a `<path/to/...>` placeholder; general `collect_regexes` collector + grammar-agnostic
  CLI confirmed reusable.
- UTF-8 adversarial category is a hard coverage obligation (§4.2) justified by verified source facts
  (§4.3); every load-bearing claim independently confirmed (codepoint model in `terminalsrc.py` and
  `terminalsrc.rs` `cp_to_byte`; `re.UNICODE` default; `pos=` codepoint offset; `𝄞` U+1D11E 1 cp / 4
  bytes; NFC≠NFD; grammar `class_char`/`assertion`/`class_shorthand` admit the cases).
- The supersession of original disposition design-4 (snapshot helper → removed) is clean: the
  single-source-of-truth collector survives, the snapshot path does not.

---

## Verdict: APPROVED

Both post-approval revisions are acceptable. Directive 1: the design commits no clockwork path,
data, or snapshot (verified by filesystem and grep); the documented command is a CLI-arg placeholder;
the tool is a general, reusable `collect_regexes` + grammar-agnostic CLI operating on any
`gsm.Grammar`; the committed corpus is in-tree only and clockwork is exercised ad hoc. Directive 2:
the adversarial suite carries a required UTF-8 / non-ASCII category whose cases are accurate to
`exploration-utf8.md`, which is itself accurate to source (Python codepoint indexing, Rust
`cp_to_byte`, `re.UNICODE`, U+1D11E 1-codepoint/4-byte, NFC≠NFD, grammar admission), with the
correct grammar-acceptance scope boundary and no over-claiming. No over-claimed fixes, no
hand-wavy deferrals, no residual contradiction with either directive.
