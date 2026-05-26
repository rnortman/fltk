# Design Review: PyO3 CST Phased Project Plan

Reviewer notes. Concise. Precise. Source-backed. No padding.

Scope: planning ADR, not a software design doc. Reviewed for groundedness, internal consistency,
phase coverage of the stated goal (PyO3-wrapped Rust CST), and scope discipline. Findings below are
ordered roughly by consequence.

---

## design-1: Committed `fltk.fltkg` cannot be regenerated — invalidates Phase 3/4 foundation

**Section:** Phase 3 ("generated Rust code for the FLTK grammar (`fltk.fltkg`, 13 rules ...) should
compile and produce classes with the same API as `fltk_cst.py`"); Phase 4 ("Use `gsm2tree_rs.py`
... to generate the Rust CST module for the FLTK grammar", "verify API equivalence with the existing
Python dataclass CST module"); Phase 4 Done-when ("`genparser.py` can regenerate `fltk_parser.py`
from `fltk.fltkg`").

**What's wrong:** The committed `fltk/fegen/fltk.fltkg` is out of sync with the committed
`fltk_cst.py` / `fltk_parser.py`. Running the current generator on the current grammar **fails
outright**:

```
$ uv run python -m fltk.fegen.genparser -o /tmp/x fltk/fegen/fltk.fltkg fltktest fltktest_cst
ValueError: Identifier rule_options not in grammar
```

`fltk.fltkg:9` references `options:rule_options`, but `rule_options` is never defined
(`grep -nE '^rule_options *:=' fltk/fegen/fltk.fltkg` → no match). The grammar also adds rules
`invocation` (line 43), `expression` (line 46), `var` — none of which appear as classes in the
committed `fltk_cst.py` (`grep -cE '^class ' fltk/fegen/fltk_cst.py` → 14 classes:
Grammar, Rule, Alternatives, Items, Item, Term, Disposition, Quantifier, Identifier, RawString,
Literal, Trivia, LineComment, BlockComment). The committed files were generated from an older
grammar version.

**Why:** Verified by running the generator (above) and by `git log` showing `fltk.fltkg` last
touched in `7914e57` ("Add preserve_blanks directive...") while `fltk_cst.py` last touched in
`29b4dc1` ("Add unparser/formatter support"). No test exercises regeneration:
`grep -rln 'fltk.fltkg' fltk/ --include=*.py` → no matches, so the staleness is invisible to
`uv run pytest`.

**Consequence:** Phase 3's core deliverable ("generate Rust for `fltk.fltkg`, compile, verify API
equivalence with `fltk_cst.py`") is impossible as written — the grammar errors before any CST is
produced, and even if fixed it yields 3 extra classes that `fltk_cst.py` does not have, so
"API equivalence with the existing Python dataclass CST module" is undefined. Phase 4's
"done when: genparser.py can regenerate fltk_parser.py from fltk.fltkg" cannot be satisfied. The
plan assumes a clean regenerate-and-compare baseline that does not exist. This is a Phase 0/1
prerequisite the plan never accounts for.

**Suggested fix:** Add a Phase -1 / Phase 0 prerequisite: fix `fltk.fltkg` (define `rule_options`
or remove the reference) and regenerate the committed Python `fltk_cst.py` / `fltk_parser.py` from
it so the Python pipeline round-trips, before any Rust work. State explicitly which grammar the
Rust generation targets, and add a regression test that regenerates from `fltk.fltkg` (currently
absent) so drift is caught. Correct the "13 rules" figure (the file has 18 rule definitions;
`fltk_cst.py` has 14 classes).

---

## design-2: "Bootstrap pipeline is independent and unaffected" — false for Phase 1

**Section:** Context ("The bootstrap pipeline (`bootstrap_cst.py`) is independent and unaffected.");
Incremental Validation Strategy (Phase 1 row); exploration §7 echoes "Bootstrap CST ... fully
independent; no generated code involved. Not affected by PyO3 changes."

**What's wrong:** `bootstrap_cst.py` and `bootstrap_parser.py` both depend on `terminalsrc.Span`:
`bootstrap_cst.py:5` `import fltk.fegen.pyrt.terminalsrc`, used as
`span: fltk.fegen.pyrt.terminalsrc.Span = ... .UnknownSpan` on every node (lines 13, 58, 133, ...);
`bootstrap_parser.py` has 79 `Span(` occurrences. Phase 1 replaces the `Span` definition in
`terminalsrc.py` with a Rust import. So the bootstrap pipeline **is** affected by Phase 1 — it
relies on the re-export working correctly.

**Why:** `grep -n "Span\|terminalsrc" fltk/fegen/bootstrap_cst.py` and
`grep -c "Span" fltk/fegen/bootstrap_parser.py` (=79). Phase 1 scope explicitly: "Replace the
`Span` dataclass definition in `terminalsrc.py` with an import from the Rust extension."

**Consequence:** Mostly benign — the re-export pattern keeps it working — but the plan understates
Phase 1's blast radius. If the Rust `Span` differs subtly (e.g. positional construction, see
design-3), bootstrap parsing breaks, and the plan's framing would send a debugger looking in the
wrong place. The "Context" and validation-strategy statements are factually wrong and should not
be relied on when scoping Phase 1 risk.

**Suggested fix:** Reword: bootstrap is independent of the *generated* CST classes but shares
`terminalsrc.Span`, so Phase 1 affects it; the full test suite (which covers bootstrap) is the
safety net.

---

## design-3: Rust `Span` must support positional construction, not only keyword args

**Section:** Phase 1 ("`#[new]` accepting keyword args"); Done-when lists only `Span(1,2)` /
`hash` / `==` checks.

**What's wrong:** `terminalsrc.py` itself constructs `Span` positionally:
`Span(pos, pos + len(literal))` (line 38), `Span(pos, match.end())` (line 43),
`Span(0, self.line_ends[0])` (lines 60, 63), and `UnknownSpan = Span(-1, -1)` (line 15). Test code
also: `terminalsrc.Span(0, 42)` (`test_gsm2parser.py:72`), `Span(0, ...)` in
`test_regression_line_col_error.py:22`. The Phase 1 scope text says "`#[new]` accepting keyword
args" only.

**Why:** `grep -rho 'Span([0-9-][^)]*)' fltk/ --include=*.py | grep -v '='` → positional sites in
`terminalsrc.py` and tests. (`fltk_parser.py` uses keyword form, 588 keyword sites total, but the
runtime `consume_literal`/`consume_regex` paths are positional and are on the hot path of every
parse.)

**Consequence:** If the Rust `#[new]` is keyword-only, `terminalsrc.consume_literal` /
`consume_regex` raise at runtime and *every* parse fails — not caught by the Done-when checks
(which only test `Span(1,2)` keyword/positional ambiguously). PyO3 `#[new]` accepts both by default,
so this is likely fine in practice, but the spec text is wrong and the acceptance criteria don't
cover the positional case.

**Suggested fix:** State "`#[new]` accepting both positional and keyword args" and add a positional
construction case to the Done-when list.

---

## design-4: Span replacement blast radius understated — many more consumers than listed

**Section:** Phase 1 ("`Span` is used pervasively: as node fields (40 construction sites in
`fltk_parser.py`), ... and in `fltk2gsm.py:24`"); Context names only `fltk_parser.py`,
`fltk_trivia_parser.py`, `fltk2gsm.py` as static consumers.

**What's wrong:** Two understatements. (a) `Span` construction in `fltk_parser.py` is 80 sites, not
40 (`grep -c 'Span(' fltk/fegen/fltk_parser.py` → 80; the "40 pairs" framing from exploration §1
counts pairs, but the plan says "40 construction sites"). (b) Beyond the three named modules, there
are additional **committed, production** static CST consumers that import `terminalsrc.Span` and a
generated CST module: `fltk/unparse/unparsefmt_cst.py`, `fltk/unparse/toy_cst.py`, consumed by
`fltk/unparse/fmt_config.py:11` (`from fltk.unparse import unparsefmt_cst as fmt_cst`),
`unparsefmt_parser.py:7`, `unparsefmt_trivia_parser.py:7`, `toy_parser.py:7`,
`toy_trivia_parser.py:7`. `fmt_config.FmtParser` is on the production path
(`plumbing.py:28,200`).

**Why:** `grep -c 'Span('` ; `grep -rn 'unparsefmt_cst\|toy_cst' fltk/ --include=*.py | grep import`;
`grep -n 'unparsefmt\|fmt_config\|FmtParser' fltk/plumbing.py`.

**Consequence:** The plan's "three static consumers" framing (used in both Context and Phase 4)
omits the unparsefmt/formatter CST modules and their parsers, all of which depend on `terminalsrc.Span`
(Phase 1) and follow the same generated-CST pattern that Phase 4 wants to migrate. A reader scoping
Phase 4 from this list would miss the formatter pipeline. For Phase 1 specifically the impact is
covered by "run the full test suite," but the enumerated consumer list is incomplete and the
"40 sites" figure is wrong.

**Suggested fix:** Either say "all Span consumers, validated by the full suite" without enumerating,
or complete the list (add `unparsefmt_cst.py`, `toy_cst.py` and their parser/formatter consumers).
Fix the 80-vs-40 count.

---

## design-5: gsm2unparser line references are off; label/enum mechanism is correct

**Section:** Context (`gsm2unparser.py:1882`); R1 (`gsm2unparser.py:303-308`); exploration §6/§3
cite `gsm2unparser.py:983` as an `isinstance(child, Span)` check.

**What's wrong:** Minor citation drift. The generated `from <cst_module> import ...` is emitted
around lines 1875-1894 (the `ast.Import(name=cst_module)` and `ImportFrom`), not pinpoint 1882.
The label-enum string interpolation `f"{class_name}.Label.{expected_label.upper()}"` is at
~303-308 — confirmed correct (`gsm2unparser.py:305-307`). But `gsm2unparser.py:983` is a
`char == "\n"` newline check, not an `isinstance(child, Span)` check as the exploration claims.

**Why:** `sed -n '300,316p'` and `sed -n '980,985p' fltk/unparse/gsm2unparser.py`.

**Consequence:** Low. The load-bearing claim — that the unparser references CST node label enums via
`ClassName.Label.LABELNAME` string interpolation and imports node classes by name from the CST
module — is correct, which is what R1 and the nested-enum workaround depend on. Only the exact line
numbers are stale. A reader trusting line `983` as the Span-isinstance site would be misdirected;
otherwise the risk analysis stands.

**Suggested fix:** Drop or re-verify specific line numbers (they drift as generated code changes);
keep the mechanism description.

---

## design-6: Phase 5 5C ("runtime Rust compilation") is speculative scope

**Section:** Phase 5, sub-option 5C; Open Question 2.

**What's wrong:** 5C (invoke `rustc`/`cargo` at runtime in `plumbing.generate_parser`) is presented
as a real option alongside 5A/5B. The analysis (`analysis-rust-cst-first.md` §9) and the plan's own
Recommendation say start with 5A and "defer 5B/5C until there's a demonstrated need." 5C requires a
Rust toolchain on every end-user's machine for what is currently a pure-Python library
(`pyproject.toml` dependencies: `astor`, `typer`).

**Why:** Plan's own line 183 recommends 5A and deferral; 5C's cons ("fragile", "requires Rust
toolchain", "compilation latency") are listed by the plan itself.

**Consequence:** Minor, but documenting three sub-options at equal depth invites premature design of
a path the plan recommends against. For a planning ADR this is acceptable as enumerated alternatives;
flagged for scope discipline — the detail on 5C exceeds its likelihood of being built.

**Suggested fix:** Compress 5C to a one-line "rejected: requires user Rust toolchain" rather than a
co-equal sub-option, consistent with the stated recommendation.

---

## design-7: Phase 3 "reuse `CstGenerator.model_for_rule`" — constructor side effect not noted

**Section:** Phase 3 ("Reuse the analysis logic (`model_for_rule`, `model_for_items`, etc.) from
`CstGenerator`"); Inputs ("the generator reuses `CstGenerator.model_for_rule`").

**What's wrong:** `CstGenerator.__init__` (`gsm2tree.py:43-44`) eagerly populates
`self.rule_models` by calling `model_for_rule` for every rule at construction time. The analysis
logic is not a set of free functions — it is bound to instance state (`self.rule_models`,
`self.iir_types`, `self.context.python_type_registry`, `self.py_module`). Reuse means
instantiating `CstGenerator` (which requires a `pyreg.Module` and `CompilerContext`) and reading
`self.rule_models`, not calling standalone methods.

**Why:** `gsm2tree.py:34-44`, `:69-78` (`iir_type_for_rule` mutates `self.context.python_type_registry`).

**Consequence:** Low/medium. The plan's framing ("reuse the analysis logic, emit Rust instead of
ast.Module") is achievable but implies cleaner separation than exists. `gsm2tree_rs.py` must either
subclass `CstGenerator` or construct one and consume `rule_models` — and must supply a `py_module`
whose import path matches the Rust module path (the `in_module` annotation logic at `gsm2tree.py:85-93`
depends on it). Underestimating this coupling risks the "~300-400 lines" estimate.

**Suggested fix:** Note that reuse is via instantiating/subclassing `CstGenerator` and consuming
`rule_models`, and that the `py_module` import-path argument drives annotation generation
(relevant only if `.pyi` stubs are generated — Open Question 1).

---

## Coverage check (goal → phases)

The stated goal (PyO3-wrapped Rust CST, phased) maps cleanly: build infra (0), Span (1),
node/enum/children mechanics (2), generator (3), static integration (4), runtime (5). Risk register
covers the exploration's three unvalidated assumptions (nested enum R1, Py<PyList> R2, dynamic
module — partially, see below). Dependency graph is coherent and linear.

Gaps:
- The dynamic-module-registration open question (exploration §3 "Potential issue", §11 Q4) is the
  third unvalidated assumption named in Context, but it is only addressed in Phase 5, not given a
  dedicated PoC like R1/R2. Context promises "PoC work: nested-enum workaround, Py<PyList> mutation
  semantics, and dynamic module registration" — the first two get focused Phase 2 tests; dynamic
  module registration does not. Minor inconsistency between Context's promise and the phase plan.
- No phase validates the formatter/unparsefmt CST pipeline (design-4), though it shares the pattern
  being migrated.

## Things verified correct (not findings)

- `terminalsrc.py:7-15` Span is `@dataclass(frozen=True, eq=True, slots=True)`, fields `start:int`,
  `end:int`, `UnknownSpan = Span(-1,-1)` — matches Phase 1 exactly.
- Span is never mutated in place; only `node.span` is reassigned — so frozen Span + node.span setter
  (Phase 1/Phase 2 line 78) is internally consistent.
- `plumbing.py:101-112` exec()+ModuleType+sys.modules pattern, module name `fltk_grammar_{id}` —
  matches Context and Phase 5.
- `fltk2gsm.py` children access: `children[0][0]`, slice `[start_idx:]`, stride `[::2]`/`[1::2]`,
  `len`, tuple unpack, `isinstance(item, cst.Item)`, label `==`/`in` — all present (lines 36-64),
  confirming the Py<PyList> requirement (R2) and label-enum requirement (R1).
- `fltk_parser.py` 11 `children.extend` sites — confirmed (`grep -c`).
- No existing Cargo/Rust infra; `pyproject.toml:1-3` uses setuptools — Phase 0 premise correct.
- `gsm2tree.py` is 303 lines; trivia insertion at `:296-303`; class-name mapping at `:46-47` —
  all confirmed.
- `fltk_trivia_parser.py:4` statically imports `fltk.fegen.fltk_cst` — confirmed (Phase 4 lists it).
