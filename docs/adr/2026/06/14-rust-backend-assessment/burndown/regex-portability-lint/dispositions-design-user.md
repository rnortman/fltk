# Dispositions — user design-gate directive (`regex-portability-lint`)

Mode: respond to authoritative user directive. The user reviewed the prior design (which
recommended Option A: an ad-hoc, generation-time, regex-based **denylist** detector) and
redirected:

> Why not create an FLTK *grammar* of the supported regexes, and actually parse the regex
> using a generated FLTK parser. Otherwise we're basically building a janky (and probably
> unreliable) regex-based parser inside a parser generation library, which seems like we
> don't trust our own product.
> — `notes-design-user.md`

The directive is authoritative. The task: seriously evaluate the grammar-based approach
against the actual codebase; adopt it in `design.md`, or push back only with a concrete,
demonstrated blocker. The finding below is the disposition of that directive.

---

## `design-user:regex-grammar-validator`

- **Disposition:** Fixed (design rewritten to adopt the user's approach)
- **Action:** `design.md` rewritten end to end. The recommended approach is now: author an
  FLTK grammar describing the portable (supported) regex subset (`regex_subset.fltkg`),
  generate and commit a Python parser + CST from it via the existing `genparser generate`
  pipeline (exactly as `unparsefmt`/`toy` parsers are generated and committed today), and
  validate each grammar regex by parsing it with that generated FLTK parser at Rust-parser
  generation time. A pattern that the regex-subset parser does not fully consume is
  non-portable and is rejected with a clear, located error. The old denylist detector
  (`scan_regex_portability` + `regex_portability.py`) is removed from the design. New
  §2 (approach), §3 (feasibility / why no blocker), §4 (the grammar), §5 (wiring), §6
  (edge cases), §7 (tests), §8 (files), §9 (non-goals), §10 (open questions).
- **Severity assessment:** This is the core design pivot the directive demands. Adopting it
  replaces a hand-rolled, fail-open denylist (which can only reject constructs someone
  remembered to enumerate) with a fail-closed allowlist (accepts only what the documented
  subset grammar admits), and dogfoods FLTK's own product to do it — directly answering the
  "we don't trust our own product" objection.

### Feasibility verdict: feasible, no blocker

Investigated against the actual codebase. Every load-bearing precondition holds:

1. **A committed generated FLTK parser is pure Python and is exactly the supported reuse
   pattern.** `fltk/unparse/unparsefmt_parser.py` is a committed, generator-produced parser
   that the production path imports and instantiates (`fltk/plumbing.py:29,350`;
   `fltk/unparse/genunparser.py:15,65`). Its only imports are `fltk.fegen.pyrt.*` and its
   sibling CST module (verified: `unparsefmt_parser.py:1-8`) — **no Rust extension, no
   build step, no bootstrapping cycle at lint time.** A `regex_subset_parser.py` would have
   the identical shape and be importable the same way.

2. **FLTK already self-hosts grammars-of-grammars.** `fltk/fegen/fegen.fltkg` and
   `bootstrap.fltkg` are FLTK grammars whose subject language is *FLTK grammar syntax*; the
   committed `fltk_parser.py` is generated from `fegen.fltkg` (`Makefile:250-252`). A
   grammar whose subject language is *regex syntax* is the same move one level over. The
   self-hosting precedent removes any "can the format describe this?" doubt.

3. **Regex syntax is comfortably expressible in the `.fltkg` format.** Regex is a textbook
   PEG/CFG language: concatenation, alternation (`|`), quantifiers (`?`/`+`/`*`), grouping
   (`(...)`), character classes (`[...]`), escapes (`\\.`), anchors. The `.fltkg` format
   supplies all of these (`fegen.fltkg:1-21`): alternatives, the three quantifiers,
   sub-expressions, labels, literals, and regex terminals. The grammar is not
   left-recursive in any required construction (it can be written right-recursive /
   iterative), so the packrat backend handles it without issue. The grammar's *terminals*
   (the leaf character/escape matchers) are themselves FLTK regexes that run on Python `re`
   — but those are simple, fixed, hand-audited classes (`[a-z]`, `\\.`, etc.), not
   user-supplied, so the regex-engine-divergence problem does not recurse into the
   validator. (Documented in design §3.)

4. **The wiring/error path already exists.** The Rust generator's `gsm.Regex` term site
   (`gsm2parser_rs.py`) raises `ValueError`, which `genparser gen-rust-parser`
   converts to `typer.Exit(1)` with the message (`genparser.py:386-391`). The new validator
   plugs into the exact same site and reuses that path unchanged — same as the old design
   intended, only the *detector* changes.

### The one refinement surfaced (not a blocker, a correctness point)

A grammar validates **syntactic membership** in the portable subset; it cannot detect
**same-syntax / different-semantics** divergence. The divergent constructs the assessment
verified (`[[:alpha:]]`, `\p{...}`, nested set ops, lookaround, backreferences —
`a2-parity.md:75-122`) are all *syntactically* distinguishable, so the subset grammar
excludes them by construction and the parser rejects them — this is the entire job and it
is fully covered. What a grammar (or any static checker, including the old denylist) cannot
catch is divergence driven by *Unicode-DB version* on *identical syntax* — `\d`/`\w`/`\s`
and `(?i)` over non-ASCII (`exploration.md:320-328`). That residual is unchanged from the
prior design and remains documented-only (design §6, §10 O3). This is presented in the
design as an honest limit of *all* static approaches, not a reason to prefer the denylist.

### Why this is strictly better than the rejected denylist (recorded for the design record)

- **Failure posture inverts from fail-open to fail-closed.** A denylist accepts anything it
  did not explicitly enumerate as bad; a future divergent construct nobody listed sails
  through silently — re-opening the exact hole this item exists to close. The subset grammar
  accepts only what it explicitly admits; an unrecognized construct is rejected by default.
  For the project's stated stakes (out-of-tree consumers' grammars are public API,
  `CLAUDE.md`), fail-closed is the correct default.
- **The supported subset becomes a single, readable, version-controlled artifact**
  (`regex_subset.fltkg`) instead of a scatter of denylist regexes with hand-tuned escaping
  caveats. It doubles as the executable definition the `document-scope-boundary` item can
  point at.
- **It dogfoods FLTK.** The validator *is* an FLTK-generated parser. This is the directive's
  core point and it is sound.

### Costs accepted (called out in the design, none disqualifying)

- **Adds to the gencode regen surface.** `regex_subset.fltkg` and its committed
  `regex_subset_cst.py` / `regex_subset_parser.py` (+ protocol) join the `make gencode`
  fan-out (`Makefile:247-297`). This is the same maintenance shape as the four grammars
  already regenerated there; design §5/§8 add the `gencode` lines.
- **An allowlist must be deliberately complete enough** not to reject portable patterns
  real grammars use (the `latin_word := /[À-ÿ]+/`, `val := /[!@#$]+/` style in
  `rust_parser_fixture.fltkg`). The design scopes the subset to the constructs the existing
  fixtures and parity corpus exercise, plus the common portable set, and §7 pins this with
  tests (every in-tree committed grammar's regexes must parse clean). Under-admission is a
  loud, fixable build error, never a silent mis-parse — the same safe-direction tradeoff the
  prior design relied on.

No genuine blocker was found. The directive is adopted.
