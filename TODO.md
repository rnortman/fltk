# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks). Re-open only with profiling evidence.

## `multi-position-spec`

The `.fltkfmt` grammar allows multiple `position_spec_statement*` inside an `after`/`before` anchor block, but `_position_spec_spacing` assumes exactly one spacing statement per block. Supporting multiple spacings (e.g. combining directives) would require defining how they compose. Deferred because single-spacing blocks cover all current use cases. Location: `fltk/unparse/fmt_config.py` (`_position_spec_spacing`).

## `position-preserve-blanks`

The `.fltkfmt` grammar admits a `preserve_blanks` directive inside an `after`/`before` anchor block (`fltk/unparse/unparsefmt.fltkg`'s `position_spec_statement`), but there is no per-anchor blank policy in the config model or either unparser generator, so the directive was silently ignored. `parse_format_config` now rejects it with an error rather than swallowing it. Implementing per-anchor blank policy — the next granularity after global and rule-level, for languages that want blanks preserved only at specific positions (e.g. between struct fields but not inside an expression) — means an `AnchorConfig` operation carrying the count and threading it through both generators' anchor-spacing paths. Location: `fltk/unparse/fmt_config.py` (`_position_spec_spacing`).

## `lsp-analysis-watchdog`

`fltk/lsp/server.py`'s analysis runs on a single-worker `ThreadPoolExecutor`, and Python worker
threads cannot be preempted. The engine already catches `RecursionError` and reports it as a normal
parse-failure diagnostic, but a truly non-terminating parse — catastrophic regex backtracking or an
unbounded grammar recursion that never hits the interpreter's recursion limit — starves every later
analysis for that server process: the protocol loop stays responsive (it is never blocked on the
worker) but that document, and every document analyzed after it, stops updating. Honoring the
engine's wall-clock promise fully needs either process isolation (run each analysis in a killable
subprocess) or a parser-level step/time budget threaded down into the generated parser — real design
work that would dominate this round. Deferred with the stale-token policy covering the degraded mode
meanwhile. Location: `fltk/lsp/server.py` (`FltkLanguageServer._analyze_blocking`).

## `ast-dispatch-order`

`alternatives_are_disjoint` (`fltk/fegen/grammar_shape.py`) decides whether two alternatives of a
rule can be told apart in the CST from their labeled children's occurrence counts and kinds alone.
It cannot use child *order*, so `x := a:num , b:name | b:name , a:num ;` reads as non-disjoint even
though the child order distinguishes the two, and the rule classifies as a merged product where a
sum would be sound. Closing this means an order-sensitive signature (the sequence of labeled item
positions per alternative, matched against the children in source order) in both the classifier and
the generated dispatch, on both backends. It must ship opt-in or with a major version: rules that
default to a merged product today would silently become sums, which is a breaking change to
generated public API for every downstream consumer of such a grammar. Location:
`fltk/fegen/grammar_shape.py` (`alternatives_are_disjoint`, and `alternatives_are_sum` /
`AltSignature` with it), `fltk/fegen/pyrt/astrt.py` (`AltSignature.accepts`).

## `ast-select-count-blind`

`to_cst` alternative selection on a merged product tests which labels are populated
(`astrt.alternative_fits`, `required <= present <= labels`; `alternative_fits` in
`fltk-ast-core`), the kinds they carry and, for a literal-only text position, its spelling — but
never how *many* values a label holds against how many positions the alternative has for it. The
trial returns the first fitting alternative's body result without trying the next, so a value
that fits an earlier alternative by name and kind but is too short for it is refused instead of
reaching a later alternative that would take it. `x := v:"gray" . v:/[0-9]+/ | v:"grey" | v:word ;`
under `rule x { product; }`: parsed `grey` gives `v=["grey"]`; alternative 0 passes the name and
`TEXT` kind tests, its literal position takes `"grey"`, its required regex position has nothing,
and `filled` raises on a value the parser itself produced, on both backends. It predates
literal-content selection (the older own-text body guard refused `"grey"` one position earlier),
and it is not `ast-dispatch-order`, which is the `from_cst` sum/product classifier. Closing it
means a count-aware selection conjunct — per label, the alternative's minimum and maximum
position counts tested against the field's value count — on both backends, decided against how it
composes with optional and repeated positions and with hoisted groups. Location:
`fltk/fegen/gsm2ast.py` and `fltk/fegen/gsm2ast_rs.py` (`trial_lines`).

## `ast-select-untagged-erased-text`

`to_cst` alternative selection on Python cannot tell a `transparent;` rule's erased text from a
literal spelling or from another erased text: the Python field is a bare `str`, while Rust keeps a
payload enum whose variant records the alternative that produced the value. `_distinguishable`
skips the runtime-type overlap check for `LITERAL` and `CONVERTIBLE` guards, so the two backends
part on parsed input wherever the admitting alternative needs more than the label and the parse
went through an erased alternative instead. `LITERAL`: `ltail := v:"lit" . ";" | v:tword ;` with
`tword` transparent, parsed `lit` renders `lit` on Rust and `lit;` on Python (which reads back as
the same value); pinned at `fltk/fegen/test_gsm2ast.py`
(`test_an_untagged_spelling_takes_the_literal_alternative`) and `tests/rust_gate_cases.py`
(`an_untagged_spelling_keeps_its_own_alternative`). `CONVERTIBLE`, which needs two erased rules
with overlapping languages: `x := v:word . ";" | v:other ;` with `word := w:/[a-z]+/ ;`,
`other := o:/[a-z]+/ ;`, both transparent, parsed `abc` renders `abc;` on Python; not pinned.
Dropping the guards instead would send every value of the label to the first alternative on both
backends. Closing it means the Python backend carrying a tag on erased text, which is a
generated-type change for every `transparent;` rule that erases to text and has to be decided
against that break for out-of-tree consumers. Location: `fltk/fegen/ast_model.py`
(`_distinguishable`).

## `ast-synthesised-literal-spans`

`to_cst()` on a terminal-shaped rule replays the parser over the node's text item by item and
hands each regex occurrence its own span, but a literal occurrence — a labeled literal above all,
and the sibling literals of a `text_from:` rule — gets the sentinel span `(-1, -1)`. The generated `*_text()` accessors panic on such a child
(`fltk/fegen/gsm2tree_rs.py`, `_native_ergonomic_methods`, whose required- and optional-arity
branches both `unwrap_or_else(|e| panic!(...))` on an unusable span), so a consumer reading a
literal-valued label off a round-tripped tree panics inside generated code it did not write and
cannot edit — generated accessors are public API for out-of-tree consumers. For
`line := text:/[a-z]+/ . bang:"!" ;`, `Line::to_cst()` gives `bang` no source and `bang_text()`
panics while `text_text()` and the node's own `text()` work. Closing this means deciding what a
synthesised literal child carries: either attach the statically-known text during synthesis
(a literal's text is in the grammar, and every walked occurrence is already a known slice of the
node's text) on both backends — `fltk/fegen/pyrt/astrt.py` (`terminal_to_cst`) and
the Rust runtime's `crates/fltk-ast-core/src/synth.rs` (`TerminalShape::split`), as driven by
`fltk/fegen/gsm2ast_rs.py` (`terminal_to_cst_body`) — or change the accessor contract, which is a
breaking change to generated public API and is disfavoured. Check Python-backend parity (what the
Python generated accessor does on the same synthesised child) as part of closing, so both backends
land the same contract. The contract for a synthesised tree is already fixed and this inherits it:
leaves carry a token-local source with readable text, composites carry unknown spans, and nothing in
a synthesised tree is a file position. Pinned by
`the_synthesised_cst_splits_the_text_back_into_its_two_children` in `tests/rust_gate_cases.py`
(the span-only case's runtime module); that assertion inverts when this closes. Location:
`fltk/fegen/pyrt/astrt.py` (`terminal_to_cst`), `crates/fltk-ast-core/src/synth.rs`
(`TerminalShape::split`).

## `ast-terminal-subexpression-walk`

`to_cst` on a terminal-only rule replays the parser over the node's text item by item, but only for
alternatives made of flat literal and regex items: an alternative holding a sub-expression is passed
over, and a rule whose every alternative holds one is refused with the shape error. Closing this
means walking sub-expression alternatives the way the parser does — a sub-expression is a nested
ordered choice of flat-item sequences, with its own quantifier, consumed at the current offset with
the same commitment and progress rules as the top-level walk — on both backends (the plan, the
Python runtime, the Rust runtime and both emitters), so that `_terminal_plan` never returns
`steps=None`, the `Unsupported` / `TerminalAlt(None)` arms and the shape error go, and the skip and
its residual go with them. The residual has two halves, both shown by
`t := ( "a" | "b" ) . x:/[0-9]/ | y:/[a-z0-9]+/ ;`: on a text the parser gives to the sub-expression
alternative (`a1`) the walk skips it and a later flat alternative emits a different child list under
an equal AST — a wrong split; on a text the parser refuses after committing to the sub-expression
alternative (`a1z`) the walk accepts it through a later flat alternative, against the AST layer's
rule that `to_cst` accepts only text that re-parses. Sub-expressions were a non-goal of the
per-item walk on purpose; the refusal variant (fail at the first sub-expression alternative the walk
reaches) was considered and rejected as scaffolding that over-refuses texts the parser handles and is
discarded by this fix. Location: `fltk/fegen/ast_model.py` (`_terminal_plan`'s `steps=None` return),
`fltk/fegen/pyrt/astrt.py` (`terminal_to_cst`'s unsupported-alternative `continue`),
`crates/fltk-ast-core/src/synth.rs` (`TerminalShape::split`'s `Unsupported` arm).

## `version-bump-0-6-0`

The version fields across the repo still read `0.4.0` even though `v0.5.0` is a tag on `origin`
(pointing at `f33015c`), so any artifact built from that tag self-identifies as `0.4.0`. The
decision is to leave `v0.5.0` exactly as it is — no re-tag, no deletion, no `0.5.1`; it is accepted
as a known-broken release — and to correct the metadata when `0.6.0` is cut. This entry exists
because a forgotten version bump is the defect that made `v0.5.0` broken in the first place. There
are no Cargo manifests anymore, so the fields are Bazel `version` attributes — and they all read
one constant, `FLTK_CRATE_VERSION` in `bzl/version.bzl`, so the edit is one line rather than a list
of sites that goes stale as crates are added. `pyproject.toml` is not part of it: it carries no
`[project]` table and declares no version. Done = that constant reads the released version at the
`0.6.0` cut, and `v0.5.0` is left untouched. Location: `bzl/version.bzl` carries the
`TODO(version-bump-0-6-0)` comment.

## `bazel-lint-consumer-module`

`tests/bazel_consumer/`'s three Python files (`consumer_python_test.py`, `consumer_rust_test.py`,
`consumer_unparser_test.py`) are no longer ruff-checked. They used to be swept up by `ruff check .`
from the repo root; the Bazel `//:ruff_check` / `//:ruff_format_check` targets glob the source tree
instead, and that directory is `.bazelignore`d (it is its own Bazel module, so the root
`bazel test //...` must not treat its packages as its own). An ignored directory has no package, so
no root-module target can name its files. Closing this means giving the consumer module its own
lint targets and running them from `make bazel-consumer-check`, which requires the lint flag and the
ruff config to be reachable cross-module (`@fltk//bzl:lint` is not currently consumer-visible for
this purpose, and the module would need its own pip hub entry for ruff). Small, but it is a real
gap: a style or import-order regression in those files now passes `make check`. Location:
`BUILD.bazel` (the `_LINT_PY_SRCS` glob), `tests/bazel_consumer/BUILD.bazel`.

## `bootstrap-fegen-chain`

The four self-hosting seed files (`fltk/fegen/{fltk_cst,fltk_cst_protocol,fltk_parser,
fltk_trivia_parser}.py`) are the one generated artifact that stays committed, because the
generator needs `fltk_parser` to read any grammar file — including `fegen.fltkg`, which is where
those files come from. The bootstrap system was meant to break that cycle and cannot today:
`bootstrap.fltkg` is a strict subset grammar (15 rules, no regex terms), `runbs.py
fltk/fegen/fegen.fltkg` fails at its `assert result`, and no code path goes bootstrap-parse → GSM
→ full parser. Resurrecting it means designing a staged grammar chain — bootstrap syntax, an
intermediate grammar expressible in it, then full fegen syntax — which is a language project, not
a build-system change, so it was deferred rather than attempted. Meanwhile the staleness hole the
committed seed used to leave open is closed: `tests/test_seed_fixed_point.py` regenerates the seed
and byte-compares, so a generator change with no regeneration is a red test. Done = the seed is
generated from `bootstrap.fltkg` through a staged chain and stops being committed, or the
resurrection is formally abandoned and this entry is closed as won't-do. Location:
`tests/test_seed_fixed_point.py`, `fltk/fegen/bootstrap.fltkg`, `runbs.py`.

## `bazel-consumer-pyo3-seam`

Self-compiled cdylibs are unsupported, and the constraint is now documented rather than
apologized for: a hand-assembled cdylib needs a direct `pyo3` dependency for the generated
`#[pyclass]` code, and it must be the *same* pyo3 instance that `@fltk//crates/fltk-cst-core`
links, or the `Bound<'_, PyModule>` types in the generated `register_classes` come from two
different crates. In-repo the fixtures name `@fltk_crates//:pyo3` directly; a downstream module
cannot — crate-hub repos are module-local, and there is no injection seam for pyo3 the way
`//crates/fltk-serde-core:serde` is one for serde. So `pyo3_extension_py_library` left the
consumer surface (it lives in `bzl/pyo3_ext.bzl` and serves `fltk_pyo3_cdylib` and the in-tree
fixtures), and the guide says to use `fltk_pyo3_cdylib`.

Add the seam and republish the recipe when a consumer needs to compile its own cdylib: a
`label_flag`/alias making fltk's pyo3 nameable cross-module, mirroring the serde one. Done = the
recipe is back in `docs/bazel-consumer-guide.md` §4 and exercised by a target in
`tests/bazel_consumer/` that loads the packaging macro through `@fltk//:rust.bzl` and imports the
resulting module from a `py_test`. Location: `tests/bazel_consumer/BUILD.bazel`,
`bzl/pyo3_ext.bzl`, `rust.bzl`, `docs/bazel-consumer-guide.md` §4.

## `cargo-guides-bazel-rewrite`

`docs/rust-cst-extension-guide.md` and `docs/rust-formatter-guide.md` are written around a
consumer crate with its own `Cargo.toml` pinning FLTK's runtime crates by path or git rev
(`fltk-cst-core = { path = "../fltk/crates/fltk-cst-core" }` and friends). Those pins name
manifests that no longer exist — every FLTK crate is a Bazel target now — and consuming FLTK from
Cargo never actually worked even when they did, so the recipes were dead before they were stale.
Each guide carries a note at the top saying so and pointing at `docs/bazel-consumer-guide.md`,
which is the recipe book that does work (§4 for a Python extension, §5.3 for a formatter binary).
The concepts in both guides are still accurate: what the generated code needs at runtime, the
`pub mod parser/unparser` requirement, the `fltk_formatter_main!` invocation, the cfg-gated
`python` feature. Closing this means rewriting the build mechanics of both onto `bazel_dep` +
`generate_rust_parser` / `fltk_pyo3_cdylib`, or folding what survives into the consumer guide and
deleting them — a call about how many guides this project wants, not a mechanical edit, which is
why it is deferred rather than done alongside the cargo retirement. Done = no guide instructs a
Cargo pin into this repo, and the notes come out with the recipes they warn about. Location:
`docs/rust-cst-extension-guide.md`, `docs/rust-formatter-guide.md`.

## `rust-supply-chain-audit`

There is no advisory, license or yanked-crate gate over the Rust dependencies anymore.
`cargo-deny` was that gate (RustSec advisories, the license allow-list, banned and duplicate
crates, source allow-listing), it ran in the local pre-commit lane only — never in CI — and it
needed both the tool and a manifest for it to read. Cargo retirement removed both, deliberately:
the directive was that no repo workflow may run cargo, and keeping a vestigial manifest pair
solely to feed an auditor keeps cargo runnable. Two smaller losses ride along: Dependabot no
longer opens PRs for Rust dependency bumps or for the Rust toolchain, because neither the
`crate.spec` list in `MODULE.bazel` nor the `rust.toolchain` tag is an ecosystem it understands.
Both are manual now (edit, `CARGO_BAZEL_REPIN=1 bazel test //...`, `make check`), the same
workflow the Bazel version pin already uses.

The successor is one tool over `cargo-bazel-lock.json`, which names every resolved crate, its
version and its checksum: read it, check the names and versions against an advisory database and
a license allow-list, and fail on a hit. That is a hermetic `py_binary` plus a test target, with
no cargo and no manifest, and it covers the consumer module's hub as well by pointing at its
lockfile too. Done = a target in the `bazel test //...` set that reds on a known-vulnerable or
disallowed crate, and CI covers it — which is strictly more than the retired gate did.
Location: new tooling; the inputs are `cargo-bazel-lock.json` and
`tests/bazel_consumer/cargo-bazel-lock.json`, and the policy the retired `deny.toml` held is in
git history at the commit that deleted it.

## `consumer-serde-single-traversal`

`bazel-consumer-check` walks `//:consumer_serde`'s graph twice per run: once inside the union
`deps(set(//:consumer_ast //:consumer_fmt_bin //:consumer_serde))` that carries the pyo3
assertion, and once in the `deps(//:consumer_serde)` cquery the two serde assertions need on
that target's own graph. Dropping `//:consumer_serde` from the union and moving its pyo3
assertion into the second cquery's block would give the same two invocations, the same three
targets covered, and no redundant traversal of the lane's largest graph. It is deferred rather
than done because the union's membership is a stated part of the design this recipe was built
from — the double traversal was weighed there and accepted on the grounds that invocation count,
not graph size, is what the lane pays — so changing the member list is a design revision, not a
cleanup. Done = each consumer target's graph is traversed once per gate run with every current
assertion intact. Location: `Makefile`, the `bazel-consumer-check` recipe.

## `unparse-cursor-fallback-signal`

When the source cursor goes unknown — a hand-built or mutated CST, a foreign-source child, an
optional suppressed non-literal, or a literal alternation whose emitted spelling differs from the
source's — both unparser backends silently revert to consuming trivia in child order *and* skip the
`raise_dropped_trivia` / `_check_dropped_trivia_*` guard. So the one path on which a comment can
still vanish is the one path that emits no diagnostic, and a caller has no way to ask whether a
document was unparsed with exact ownership. The `literal_canonicalization` gate case pins the
mangled layout as expected output, which is honest but gives a real user no explanation. Fixing it
means deciding what the signal is and where it surfaces — a flag or count on the top-level unparse
result, threaded to `fltkfmt`/consumer CLIs as a verbose or warning mode — which is public surface
on `fltk-unparser-core` and on every consumer binary, so it wants a design pass rather than a patch.
The same signal question covers a second bypass: the guard runs on the rule entry's success path,
so a rule that returns `None` for any reason — including an alternative that fails on a child a gap
left unconsumed — never reaches it, and the caller sees only "unparser returned None".
A known instance: with the cursor unknown, an absent optional item between two trivia children —
the shape a mutation that deletes the optional child leaves — loses the second child. The gap
before the item takes the first and sets the accumulator's trivia flag, the gap after it then takes
nothing, and no later gap does either; `x // c\na // d\nz` with `a` removed renders `x\n// c\nz`.
A `before a` spacing used to clear that flag and so masked the loss for configured rules; it no
longer does, and the `optional_before_spec` gate case and its Python twin in
`fltk/unparse/test_unparser.py` pin the lossy text.
Location: `fltk/unparse/pyrt.py` (the `TODO(unparse-cursor-fallback-signal)` comment in the source
cursor section), with the generated counterparts in `fltk/unparse/gsm2unparser.py` and
`fltk/unparse/gsm2unparser_rs.py`.

## `test-missing-zero-run-after-spacing-on-repetition`

An `after X` spacing on an included repetition `X*` fires on a zero-occurrence run, where no `X`
was printed: the repetition method always succeeds, and both generators emit the after-spacing on
the success path. It is the after-side twin of the phantom `before X` that an optional item no
longer emits, and it reaches the resolver the same way — an `AfterSpec` is what boundary extraction
peels. `before X` on the same item is committed only when the run advanced the child position; the
after side was left unchanged deliberately, so the two sides are now asymmetric on an empty run and
no test states what an empty run's after-spacing should be. Deciding it is a formatter-semantics
change for every downstream spec with `after X` on `X*`; once decided, the guard (if any) goes in
both generators beside the before-side one and a rendered witness over `xz` / `xaz` with
`after a { … }` on `a:"a"*` pins it in both backends. Location: the optional-item success branch of
`gen_alternative_unparser` in `fltk/unparse/gsm2unparser.py` and of `_gen_alternative_body` in
`fltk/unparse/gsm2unparser_rs.py`.

## `preserved-trivia-ws-bytes`

A preserved trivia node renders its non-preserved whitespace-token children as `Text` bytes
(gear's `ws := chars:/\s+/`), on both sides of a comment. The whitespace token *before* an
own-line comment carries the newline and the source indent as bytes, so the comment line keeps its
source column instead of taking the nest indent; the whitespace token *after* the comment
terminator starts a layout line and takes the nest indent before its own bytes, one indent more per
pass: when the next line follows directly, that line's text drifts (a trailing comment,
`let r = w.hub; // t`, drifts the same way); when a blank line follows the comment, the token
begins with its newline, so the indent lands on the blank line as trailing whitespace that grows
every pass while the next line sits stably at its source column.
The block-opening gap behaves the same way since `nest-boundary-trivia-indent` kept a boundary
comment inside its nest. Before that the comment was extracted to the enclosing level and the
following token rendered at the enclosing indent + its bytes — the next line at its source column
at any `indent_width`, idempotent every pass but correctly indented only where the source indent
equalled `indent_width`; keeping the comment inside the nest made that gap drift like the interior
one.
Deciding whether such children are dropped, normalised, or left to the grammar is a
formatting-policy design. Done = a gear block with a comment — opening the block or mid-block,
own-line or trailing, with or without a blank line after it — formats to a fixed point in both
backends. Location: `fltk/lsp/test_gear_demo.py` (`test_mid_block_comment_drifts`, including its
`block_start_next_line_drifts` param), the pin that a fix trips. The whitespace token is a rule child
of the trivia node, rendered through ordinary rule-child emission, so no code site is the fix's
until the policy is chosen: dropping or normalising lands in both generators' trivia-node child
emission (`fltk/unparse/gsm2unparser.py`, `fltk/unparse/gsm2unparser_rs.py`); leaving it to the
grammar lands in `docs/format-specs.md` and gear's grammar.


## `join-nest-same-anchor`

Range statements (`group`, `nest`, `join`) that share both anchors in one rule nest in statement
order: the first declared wraps the rest. A `join` declared before a `nest` over the same anchors
therefore wraps a single `Nest` child and inserts no separator, with no diagnostic. Repro: grammar
`array := "[" , elem , ("," , elem)* , "]" ; elem := val:/[0-9]+/ ;`, rule spec
`join from after "[" to before "]" concat([text(","), hard]); nest from after "[" to before "]";`,
input `[1,2,3]` renders `[ 1 , 2, 3 ]`. With the two statements swapped, the join applies inside
the nest. This was observed while adding a join guard test and reproduces with the pre-change
`fltk/unparse/` sources, so this change did not introduce it. `group` and `nest` over the same
anchors show the same order dependence through a boundary comment, since
`nest-boundary-trivia-indent` keeps such a comment inside the `Nest`: `group …; nest …;` builds
`Group(Nest(…))`, the comment's `HardLine` is inside the group and breaks it; `nest …; group …;`
builds `Nest(Group(…))`, the `Group` arm of `_extract_all_boundary_specs` lifts the comment to the
`Nest`'s level and the body stays flat. Repro: `tests/rust_gate_cases.py`
`NEST_BOUNDARY_TRIVIA_GRAMMAR`'s `gn` / `ng` rules on `{\n// c\ny;y;}` —
`{\n    // c\n    y;\n    y;\n}` against `{\n    // c\n    y; y;\n}`. An interior comment breaks
the group in both orders. Choosing between a canonical nesting order for coincident ranges, a
diagnostic, and documented statement-order semantics is a design question for the `.fltkfmt`
language. Done = that rule is chosen, documented in `docs/format-specs.md`, the repro either
formats with the join applied or is rejected with an error, and the `gn` / `ng` rows render the
same text or one order is rejected. Location: `_process_range_operation` in
`fltk/unparse/fmt_config.py`, which builds the anchor operation lists both backends' generators
consume.

## `quality-fit-cursor-hand-mirrors-output-state-machine`

The group fit-check simulates the renderer's output position with its own copy of the cursor
state machine — `column`, the layout line-start flag, "non-empty content at a line start pays the
indent first", "a line break re-arms the flag and zeroes the column" — rather than driving the
renderer's own: `FitCursor` against `Output::append_content` / `Output::break_line` in Rust, and
`_fits`'s `pay_indent` / `charge` against `render`'s `append_content` / `break_line` in Python.
Every change to how output advances (tab-width indent, display width instead of code points,
trailing-whitespace handling) must be made at both sites in both backends, and a miss makes the
formatter non-idempotent again — which the parity suite cannot catch when both backends drift
together. Pull the position state into one type both the renderer and the simulation drive, in
each backend. Needs a design pass: the renderer's cursor is `usize` and writes bytes while the
simulation's is `isize` and only compares, and the simulation's item traversal (one
`append_content` per `Text`, one per `Comment` line, `Nest` threading, `HardLine`
short-circuit) stays hand-mirrored either way, so the shape of the shared type is the open
question. The design approval for the indent-charging fix set the trigger: the next
fit-check correction of this kind should do this instead of adding mirrored state. Location:
`crates/fltk-unparser-core/src/render.rs` (`FitCursor`, `Output`), `fltk/unparse/renderer.py`
(`_fits`, `render`).

## `correctness-persistently-broken-project-files-disable-rename-permanently`

The LSP rename guard (under a resolver) refuses whenever any file in its scan universe — every
file with a resolver suffix under the workspace root, outside dot-directories — fails to read or
parse. A consumer project that commits intentionally-invalid files of its own language (parse-error
test fixtures, an error-recovery corpus) therefore has cross-file-aware rename refused in every file
for as long as those fixtures exist; the only workaround is moving them under a dot-directory or out
of the root (documented in `fltk/lsp/resolver.py`'s module docstring). Fixing it means an exclusion
mechanism that the directory walk and the open-buffer term of the universe both honour, and that
find-references honours too (one project boundary, not two) — e.g. an optional `Resolver`
attribute, an ignore file, or a server flag. Each is a new configuration surface on the provisional
resolver protocol or the server CLI and needs a design cycle. Location: `fltk/lsp/project.py`
(`_is_project_dir`, `ProjectHost.workspace_files`, `ProjectHost.open_documents`).
