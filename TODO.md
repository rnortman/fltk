# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `rule-preserve-blanks`

Rule-level `preserve_blanks` is parsed and stored but never consumed. `RuleConfig.preserve_blanks`
(`fltk/unparse/fmt_config.py`) and `FormatterConfig.get_preserve_blanks(rule_name)` exist, but both
unparser generators read the *global* `trivia_config.preserve_blanks` as a generation-time constant
rather than calling the rule-aware method, so a per-rule `preserve_blanks` directive has no effect.
Pre-existing feature gap, orthogonal to the blank-line-preservation bug fix. To close it, thread the
rule name to the newline-spacing emission and read `get_preserve_blanks(rule_name)`. Location:
`fltk/unparse/gsm2unparser.py` (both `# Get preserve_blanks from config` sites in
`_gen_trivia_processing`), `fltk/unparse/gsm2unparser_rs.py` (`_get_preserve_blanks`).

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks). Re-open only with profiling evidence.

## `fmt-cli-per-consumer-version`

`fltk-fmt-cli`'s `FmtArgs` carries `#[command(version)]`, which clap expands to `CARGO_PKG_VERSION` where `FmtArgs` is defined — the scaffolding crate — so every consumer binary reports `fltk-fmt-cli`'s version, not its own. This is an observable defect today: `fltkfmt` is `0.1.0` (`crates/fltkfmt/Cargo.toml`; deliberately outside the root workspace with its own `[workspace]`), while `fltk-fmt-cli` is `0.2.0` (`crates/fltk-fmt-cli/Cargo.toml`), so `fltkfmt --version` prints `0.2.0` for a `0.1.0` binary. Fix by threading `version` (and possibly `name`) through `run_main` / `fltk_formatter_main!` the same way `about` is threaded (commit for `fmt-cli-per-consumer-about`), so `<consumer> --version` prints the consumer's own version. Do NOT add a second bare `&'static str` positional argument next to `about` on `run_main`: two adjacent indistinguishable string params can be swapped silently (a version string rendered as the `--help` description). Introduce an identity struct instead (e.g. `FormatterInfo::new(about).version(..)`, keeping `about` required) so this fix — and any later per-consumer knob — is a non-breaking addition rather than another signature break. Location: `crates/fltk-fmt-cli/src/lib.rs` (`#[command(version)]` on `FmtArgs`, and `run_main`).

## `lsp-cst-text-helpers`

`fltk/lsp/lsp_config.py`'s `_span_text` / `_identifier_text` and the inline literal-extraction
sequence in `_parse_anchor` duplicate helpers that already exist for `.fltkfmt`:
`fltk/unparse/fmt_config.py` (`_span_text`, `_extract_identifier_text`, `_extract_literal_text`)
and the more careful `fltk/unparse/pyrt.py:extract_span_text` (which guards against a
source-bearing span whose `text()` returns `None` — a guard the `fmt_config` and `lsp_config`
copies both lack). There is also a fourth single-backend copy at `fltk/fegen/fltk2gsm.py`
(`Cst2Gsm._span_text`). Consolidate into one canonical, `SpanProtocol`-typed helper (dropping
the `hasattr` probe and `type: ignore`s now that `SpanProtocol` includes `text()`), keeping the
pyrt source-bearing guard, and migrate all copies to it. Deferred because it touches out-of-round
modules (`fmt_config`, `unparse.pyrt`). Location: `fltk/lsp/lsp_config.py` (`_span_text`,
`_identifier_text`, `_parse_anchor`).

## `lsp-test-parse-helper`

`fltk/lsp/test_lsp_config.py` (`_load`) and `fltk/lsp/test_lsp_validation.py` (`_parse`) each
hand-roll the same `TerminalSource` → `Parser` → `apply__parse_lsp_spec` → full-consumption
check, diverging only on failure reporting (`_load` renders a caret diagnostic; `_parse`
bare-asserts). The design's `plumbing.parse_lsp_config` wrapper (not yet built) is the intended
home for this sequence; fold both helpers onto it once it lands, rather than building a throwaway
interim shared helper. Location: `fltk/lsp/test_lsp_config.py`, `fltk/lsp/test_lsp_validation.py`.

## `formatter-group-idempotency`

The formatter is not idempotent on grouped alternations at narrow widths: `fltk/fegen/test_data/rust_parser_fixture.fltkg` formatted at width 40 / indent 4 changes between pass 1 and pass 2 (a grouped alternation `( inner:rec_via_sub . "+" | inner:atom ) .` re-breaks into a multi-line `(` … `)` block on the second pass), converging only at pass 2. Single-pass cross-backend parity holds, so this is a shared formatter-layout bug present in both the Python and Rust backends, not a backend divergence. Fixing it is a formatter behavior change to both backends and was out of scope for the pure test addition that discovered it (`fltkfmt` integration tests). The idempotency integration test (`crates/fltkfmt/tests/cli.rs`, `format_format_is_format`) carves this one case out explicitly, pinning current behavior (`out2 != out1`, `out3 == out2`); when the formatter is fixed that carve-out's `assert_ne!` trips, forcing its removal alongside this entry. Location: `crates/fltkfmt/tests/cli.rs` (the `TODO(formatter-group-idempotency)` carve-out in `format_format_is_format`); the layout logic lives in the shared unparser/renderer (`fltk/unparse/` and the generated Rust unparser).

## `resolver-spec-file-recognition`

`fltk/lsp/resolver.py`'s `_looks_like_path` treats a `--resolver` spec head as a file whenever
`pathlib.Path(head).is_file()` — a cwd-relative check — even for a head that reads as a plain
module (no `.py`, no separator). So whether `--resolver mylang.resolvers:create_resolver` imports
the installed module `mylang.resolvers` or `exec`s a file literally named `mylang.resolvers`
depends on the server's cwd contents. Editors commonly spawn LSP servers with cwd = workspace
root, so a hostile project that plants a file matching a known resolver module name could get
arbitrary Python exec'd at startup for a user who configured a bare-module resolver spec. No
shipped config is affected (the gear demo and README use explicit `.py` paths). The fix — drop the
bare `is_file()` recognition, keeping only the unambiguous `.py`/separator signals — contradicts
the frozen step5 design §4.3 ("a path is recognized by an existing file"), so it requires a design
delta before landing; do it there, not by editing the frozen doc. Location: `fltk/lsp/resolver.py`
(`_looks_like_path`).

## `rename-guard-incomplete-scan`

`ProjectNavigator.rename_hazard` (`fltk/lsp/project.py`) decides whether a same-file rename is safe
by scanning the workspace for cross-file references. When that scan is incomplete -- a directory
`os.walk` error (surfaced only as an advisory `window/logMessage` warning), or a neighbor file that
is unreadable/unparseable and therefore dropped by `host.document()` -- the guard still returns
`Hazard.NONE` and permits the rename, so a cross-file reference hiding in the skipped file goes
undetected and the rename can silently break another file. This is the one fail-closed path (frozen
step5 design §4.6) meeting the read path's deliberate silent-degradation policy (§5:
transiently-broken neighbors are the normal state of live editing); the design did not resolve the
tension. Refusing on any imperfect scan would make rename nearly unusable during editing; permitting
weakens the guard. Reconciling requires a design delta (e.g. refuse only on walk/IO errors while
tolerating unparseable neighbors, or track scan completeness explicitly), not a respond-mode patch.
Location: `fltk/lsp/project.py` (`ProjectNavigator.rename_hazard`).

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

## `lsp-classify-hotpath`

`fltk/lsp/classify.py`'s `classify` / `default_tokens` are the per-document hot path the M2
server will sit on. The once-per-grammar table build is now hoisted: `AnalysisEngine` builds a
`_GrammarTables` once in `__init__` and threads it into `classify` via the optional `tables`
parameter, so `highlight` no longer re-walks the grammar and recompiles every terminal regex per
call. Two internal inefficiencies remain, both confined to `classify.py` and neither forcing a
change to the engine seam's signature: (1) `_winner_segments` rescans all intervals per boundary
pair (O(n^2)); a sweep line maintaining the active set reaches the intended O(n log n); (2)
`classify` walks the analysis tree twice (`_explicit_intervals` then `_default_intervals`) — fold
default emission into the explicit walk. Both are the design-stage sweep-line/walk-fusion rewrite
of the interval-resolution core, best batched (shared walk/segment logic). Address before the M2
server ships (it drives `classify` per keystroke), or when profiling on a real grammar shows
`classify` latency dominates. Location: `fltk/lsp/classify.py` (`_winner_segments`, the second
`_default_intervals` loop in `classify`).

## `lsp-rule-surface-index`

`fltk/lsp/lsp_config.py`'s `_index_rule` (`RuleIndex`: labels / literals / invoked rules) and
`fltk/lsp/classify.py`'s `_build_terminal_table` (`_TerminalTable`: literals / regexes,
label-keyed) are two parallel per-rule walks over `rule.alternatives` × `gsm.for_each_item`, each
collecting an overlapping slice of a rule's item surface (literals appear in both). The definition
of "what a rule's items expose to anchors/classification" thus lives in two mirrored walkers in
two modules, and any drift shows up as validation accepting an anchor the classifier can't match.
Unify into one per-rule surface index (labels, literals, regexes, invoked rules; label-keyed views
derived from it) consumed by validation, resolution, and the classifier tables. Deferred rather
than done in respond-mode because it restructures private surfaces across two modules.
Location: `fltk/lsp/lsp_config.py` (`_index_rule`), `fltk/lsp/classify.py`
(`_build_terminal_table`).

The INLINE half of this is already handled and is no longer a reason to do the unification: `!`
dispositions are expanded into sub-expressions at the text→GSM parse boundary, so both walkers
receive a grammar in which an inlined rule's terminals already live in the parent rule's items.
Neither walker needs its own splice, and neither is forced to change by INLINE support. What
remains is the duplication itself.

## `rust-codegen-self-keyword`

The Rust CST backend emits uncompilable Rust for any grammar label or rule name whose
UpperCamelCase form is `Self`. `_rust_variant_name` (`fltk/fegen/gsm2tree_rs.py`) and the rule
class name both route through `naming.snake_to_upper_camel`, which has no keyword handling, and
`Self` is the only Rust keyword that survives camel-casing. Because `snake_to_upper_camel`
lowercases first and collapses underscores, the trigger set is `self`, `Self`, `SELF`, `self_`,
`_self`, `__self__` and friends — not just the literal `self`. A label named `self` emits
`enum {CN}Label { …, Self }` plus every `{CN}Label::Self` match arm; a rule named `self` emits
`pub struct Self`, `impl Self` and `NodeKind::Self`. rustc rejects both with "expected identifier,
found keyword `Self`" pointing into generated code, so a downstream consumer sees a build failure
in a file they did not write rather than a grammar-level error. The Python backend accepts these
names (`Label.SELF`, class `Self`) and parses normally, so this is a Rust-backend-only divergence;
no in-tree grammar uses such a name, which is why nothing catches it today.

`cst_ergonomics.RUST_UNRAWABLE_KEYWORDS` already contains `self` and correctly skips the ergonomic
bare accessor for such a label, so only the variant/class identifiers lack a guard. Two fix shapes:
reject at validation time next to the existing `_RESERVED_LABELS` / `_RESERVED_CLASS_NAMES` checks
in `RustCstGenerator.__init__` (both live in the Rust generator, so a Python-only consumer with a
`self` label is unaffected), or mangle the emitted Rust identifier while leaving the Python-visible
name (`SELF`) unchanged. Mangling would normally be a breaking rename of a generated public symbol,
but no consumer can depend on the current spelling because it does not compile. Whichever is
chosen, cover both the label path and the rule-name path, and add a fixture case — the Rust fixture
grammar has keyword labels (`type`, `match`) but nothing that camels to `Self`. Location:
`fltk/fegen/gsm2tree_rs.py` (`_rust_variant_name`, and the class-name collision check in
`RustCstGenerator.__init__`).

## `ast-terminal-repeat-synthesis`

`to_cst` on a terminal-only AST node rebuilds the CST by matching the node's `text` against one
regex per alternative, with a named capture group per included item
(`fltk/fegen/ast_model.py`, `_terminal_plan`). That construction cannot express an item whose
quantifier admits more than one occurrence — a single group would capture the whole run rather
than each occurrence — so `_terminal_plan` marks such an alternative unsynthesisable
(`pattern=None`), and `astrt.terminal_to_cst` raises `AstError` for it. The parse direction is
unaffected: `from_cst` reads the node's own span, so a rule like `word := c:/[a-z]/+ ;` converts
fine and only fails on the way back out. Closing this means splitting the text per occurrence
(walk the alternative's items left to right, matching each pattern at the current offset with
backtracking) and mirroring the algorithm in the Rust emitter so both backends synthesise the same
children. Location: `fltk/fegen/ast_model.py` (`_terminal_plan`'s `bounds != (1, 1)` return),
`fltk/fegen/pyrt/astrt.py` (`terminal_to_cst`).

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

## `ast-transparent-container-payload`

`transparent;` on a single-field product erases the rule to the type of its one field, but only
when that field occurs exactly once: an optional or repeated field is a generation error
(`_ModelBuilder.erased_product_payload`). Design §5.4 states the payload as "the field's type"
without restricting arity, so `list := "[" , (value , ("," , value)* , ","?)? , "]" ;` marked
`transparent;` should erase to `Vec<Value>` / `list[Value]` rather than being refused. Closing this
means composing two container levels: `FieldType` carries one `Container`, so a use site of an
erased collection payload needs `list[list[T]]` annotations, and `astrt.cursor` — which tells a
single value from a collection by `isinstance(value, list)` — would take a list-valued single field
for several values, so the emitter must construct the cursor explicitly at such positions.  Both
halves have to land in the Rust emitter the same way, or the two ASTs stop being shape-equivalent.
Location: `fltk/fegen/ast_model.py` (`_ModelBuilder.erased_product_payload`'s arity check),
`fltk/fegen/gsm2ast.py` (`field_annotation`, `cursor_expression`).

## `rust-cst-memberless-nodes`

The Rust CST generator refuses any rule whose model has no members (`gsm2tree_rs.py`,
`_rule_info`: "Model class ... would have no members"), while the Python CST generator accepts one.
Two AST-modelable shapes are therefore unreachable on the Rust backend: a marker product spelled
with `.` separators (`marker := $"!" . $"?" ;` — a rule whose included items are all unlabeled
literals, which the AST models as a span-only node) and an unlabeled-unincluded terminal rule. This
is pre-existing CST-generator behavior, not AST-layer debt, and the workaround is to `$`-include a
terminal so the node has one member. Closing it means teaching the Rust CST generator to emit a
memberless node — the node struct, its child and label enums (which have no variants), and the
parser plumbing that appends nothing — which is its own bounded design. Until it is closed, the
Python/Rust AST parity suite must carve these two shapes out as a known divergence rather than
reporting them as a backend bug. Location: `fltk/fegen/gsm2tree_rs.py` (the `if not model.types:`
guard in `_rule_info`).

## `ast-deep-clone-debug`

Generated Rust fold types derive `Clone` and `Debug` (`gsm2ast_rs.py`, `_NODE_DERIVES`), and both
derives recurse once per chain link, so cloning or `{:?}`-formatting a fold chain of some tens of
thousands of operands overflows the stack — the same hazard the emitted iterative `Drop` closes for
teardown and the emitted `eq_walk` closes for comparison. Unlike those two, `Clone` and `Debug` are
explicit consumer calls: they are avoidable, no design law rests on them, and a consumer who needs
neither pays nothing. So v1 documents the limit rather than emitting worklist implementations.
Closing it means emitting a written-out `Clone` (build the new chain bottom-up from a worklist over
the old one) and `Debug` (render iteratively, or bound the depth) for the types the recursion
analysis marks `deep`, in place of the derives. Do it when a consumer actually hits it — the
`PartialEq` walk is the shape to copy. Location: `fltk/fegen/gsm2ast_rs.py` (`_NODE_DERIVES`).


## `ast-select-literal-content`

Kind-aware `to_cst` alternative selection tests a value's *kind*, and a labeled literal's kind is
the same TEXT a regex position contributes (`element_types` maps a literal to SPAN, which
`field_type` coerces to TEXT wherever the label carries anything else). So for a rule whose
alternatives split a label between a literal and something else — `x := v:"lit" | v:item ;` under a
`rule x { product; }` sidecar — the literal alternative's selection guard admits *any* string, and
the literal position then renders the grammar's own text: a hand-built `X(v="xyz")` unparses to
`lit` on both backends, silently replacing the value. Pre-existing (name-only first-fit chose the
same alternative and swapped the same way); the kind test narrowed it to strings but not to the
literal's own string. Closing it means a content test at selection time — `Guard(GuardKind.LITERAL)`
where the accepted TEXT of a label is contributed by literal positions alone, which Python already
spells as `astrt.LiteralText` — *and* the matching content test on the Rust side, whose selection
conjunct is a `matches!` over field enum variants and carries no content today. That second half is
the design work: `AcceptedKind.guard` is currently the untagged backend's test only, so making
selection content-aware changes what the tagged backend reads, and it has to be decided against the
multi-spelling doctrine (`rival_signature` deliberately does not record which literal a value came
from, so alternatives differing only in literal spelling stay first-fit). Location:
`fltk/fegen/ast_model.py` (`_kind_guard`), `fltk/fegen/gsm2ast_rs.py` (`kind_condition`).

## `cst-per-label-mutator-narrow-child-check`

`append_<label>` / `extend_<label>` are annotated with the label's own child type but validate
against the *node-wide* child union, on both backends. On `Items`, `append_item(trivia_node)` is a
pyright error and a runtime success: the `Trivia` is stored under `Items.Label.ITEM`, comes back
out of `children_item()` typed as `Item`, and is silently skipped by the native Rust data-struct
accessors, which do match on the child variant. Deferred rather than fixed because the Python side
alone is not the ceiling: the Rust per-label mutators extract through the node-wide child enum
(`extract_from_pyobject`), so closing this means either a per-label extraction path in the Rust
emitter or a per-label allowed-class tuple threaded through both emitters, plus a decision about
what the two backends' typed readers should do with an off-type child already in a tree. Pinned by
`test_per_label_append_stores_an_off_type_known_child` in `tests/test_cst_mutators_parity.py` —
invert that test when this closes. Location: `fltk/fegen/gsm2tree.py` (`concrete_body_for`'s
`append`/`extend` branches, `_check_child_type_for_mutators`), `fltk/fegen/gsm2tree_rs.py`
(`_per_label_methods`, `extract_from_pyobject`).

## `astrt-fold-roundtrip-span-merge`

`to_cst()` on an AST value from a `fold`-using rule produces a CST that `from_cst()` then refuses:
the round trip raises `AstError` with "the operands of a fold come from different sources, so their
spans cannot merge". Reverse construction synthesises each node's span against its own source text,
one text per node, and `Span.merge` rejects operands from different sources by construction — so
this fires on any real parse of such a rule, not just on a hand-mixed tree. It needs the operands to
carry spans: a sidecar that erases them to plain scalars leaves nothing to merge and round-trips
today, so a fix validated only on that shape proves nothing. Pre-existing, and backend-independent
(`to_cst` is Python-backend-only either way). Closing it means deciding how synthesised spans
compose across sources —
whether reverse construction should share one synthetic source per conversion, whether a fold link's
span should be synthesised rather than merged, and what a consumer reading `.span` off a
round-tripped node is entitled to — which is a design cycle, not a patch. Pinned by
`test_fold_roundtrip_raises_on_span_merge` in `tests/test_ast_fold_roundtrip.py`; invert that test
when this closes. Location: `fltk/fegen/pyrt/astrt.py` (`_merged`).

## `version-bump-0-6-0`

The version fields across the repo still read `0.4.0` even though `v0.5.0` is a tag on `origin`
(pointing at `f33015c`), so any artifact built from that tag self-identifies as `0.4.0`. The
decision is to leave `v0.5.0` exactly as it is — no re-tag, no deletion, no `0.5.1`; it is accepted
as a known-broken release — and to correct the metadata when `0.6.0` is cut. This entry exists
because a forgotten version bump is the defect that made `v0.5.0` broken in the first place, and the
edit spans seven manifests: the root `Cargo.toml` (`[package] version`), and
`crates/fltk-cst-core/Cargo.toml`, `crates/fltk-serde-core/Cargo.toml`,
`crates/fltk-fmt-cli/Cargo.toml`, `crates/fltk-unparser-core/Cargo.toml`,
`crates/fltk-parser-core/Cargo.toml`, `crates/fltk-ast-core/Cargo.toml` (each `[package] version`).
`pyproject.toml` is no longer one of them: it carries no `[project]` table and declares no version.
Done = every one of those fields reads the released version at the `0.6.0` cut, and `v0.5.0` is left
untouched. Location: the root `Cargo.toml` carries the `TODO(version-bump-0-6-0)` comment; the six
crate manifests above are the rest of the edit.

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

## `bazel-generated-native-lib`

`src/lib.rs` — the `fltk._native` module wiring — is generator output (`gen-rust-lib
--module-name _native --register-span-types --unknown-span-static --no-cst --no-parser`) and is
the one generated Rust file still tracked in git. Design §5.1 of the all-Bazel ADR has `//:native`
built from a `generate_rust_lib` output assembled with the hand-written `src/span.rs`, with the
tracked copy deleted; that cannot land while the root `Cargo.toml` declares the `fltk-native`
package, because its `[lib]` target has no crate root without the file and *every* cargo
invocation then fails to parse the workspace manifest — including `cargo metadata --locked`,
`cargo deny`, and the compile-gate tests that build throwaway crates with path deps on the
runtime crates.

`//:native_lib_rs` regenerates it and `//:native_lib_parity` diffs it against the tracked copy,
so the file cannot drift from what the generator produces. Done = either the root manifest stops
being a package (a virtual workspace manifest, which changes what `@fltk_crates` resolves and
needs its own look at `Cargo.lock`), or cargo stops being needed at all — after which `//:native`
takes the generated `lib.rs` and `src/lib.rs` is deleted with the parity genrule.

Location: `BUILD.bazel` (`:native_lib_rs`, `:native_lib_parity`, `:native`), `Cargo.toml`,
`src/lib.rs`.

## `bazel-rustc-gate-tests`

Three pytest files are compile gates: they write a throwaway Cargo crate out of freshly
generated Rust, with path dependencies on this repo's runtime crates, and hand it to `cargo`
(`tests/test_generated_rust_gate.py`, `tests/test_rust_prelude_qualification.py`,
`tests/test_nullable_loop_guard.py`). They run under Bazel as `local` + `requires-cargo`
targets: unsandboxed, inheriting `PATH` / `HOME` / `CARGO_HOME` / `RUSTUP_HOME` so cargo finds
its toolchain and its registry cache, with `//:cargo_workspace_files` supplying the manifests
and sources cargo reads off disk. That is a hole in the hermeticity of `bazel test //...` —
the compiler, its version resolution and the resolved third-party crates come from the
developer's machine rather than the build graph — and it is why CI still installs a Rust
toolchain and needs a warm registry cache for `--offline` resolution.

The hermetic replacement is to compile the generated crates through rules_rust instead: the
grammar shapes become codegen targets, the hand-written `#[test]` modules become `rust_test`s
over them, and the runtime crates come in as Bazel rlibs. What that costs is one target per
shape declared in Starlark instead of a `Case` dataclass in Python, and a way to express the
negative cases (a shape that must *fail* to compile is a test the build graph cannot hold
directly).

The gates also keep their build directories outside the sandbox
(`tests/generated_rust_gate.py`'s `cargo_target_dir`, one persistent directory per gate under
`$XDG_CACHE_HOME`/`$HOME`), because Bazel's per-run scratch space would make each one recompile
the runtime crates every time any of them changes. The rules_rust replacement must not inherit
that: its build outputs belong in bazel-out, and this helper goes away with the cargo lane.

Done = no pytest target carries `requires-cargo`, and `cargo` is not needed to run
`bazel test //...`. Location: `tests/BUILD.bazel` (`_CARGO_GATE`),
`tests/generated_rust_gate.py`, `BUILD.bazel` (`:cargo_workspace_files`) and the
`cargo_gate_files` filegroups in each runtime crate.

## `bazel-consumer-pyo3-seam`

`pyo3_extension_py_library` is exported from `rust.bzl` and published in
`docs/bazel-consumer-guide.md` §4 as the "if you compile the cdylib yourself" recipe, but no
target outside fltk's own module exercises it, and it is not clear one can. A hand-assembled
cdylib needs a direct `pyo3` dependency for the generated `#[pyclass]` code, and it must be the
*same* pyo3 instance that `@fltk//crates/fltk-cst-core` links, or the `Bound<'_, PyModule>` types
in the generated `register_classes` come from two different crates. In-repo the fixtures name
`@fltk_crates//:pyo3` directly; a downstream module cannot — crate-hub repos are module-local,
and there is no injection seam for pyo3 the way `//crates/fltk-serde-core:serde` is one for serde.

So the recipe is either missing a seam (a `label_flag`/alias making fltk's pyo3 nameable
cross-module, mirroring the serde one) or missing a documented constraint. Deciding which is a
consumer-surface design call, not a test to add. Done = the guide's §4 recipe is exercised by a
target in `tests/bazel_consumer/` that loads `pyo3_extension_py_library` through `@fltk//:rust.bzl`
and imports the resulting module from a `py_test`. Location: `tests/bazel_consumer/BUILD.bazel`,
`rust.bzl` (`pyo3_extension_py_library`), `docs/bazel-consumer-guide.md` §4.

## `uv-retired-agent-hook`

`.claude/settings.json`'s `PostToolUse` hook still shells out to uv to format the edited file
(`... ruff format "$file_path" 2>/dev/null || echo "Formatting completed"`) after every Python
edit — spelled out in the file, and deliberately not repeated here, because this doc is one of
the surfaces the retirement gate scans. uv is retired: `pyproject.toml` declares no project and
no `[tool.uv]` table, and the uv lockfile is gone. On a machine
without uv the command fails, stderr is discarded, and the `|| echo` reports success while
formatting nothing; on a machine with uv installed globally it formats with whatever ruff an
ad-hoc environment resolves, which is not the hub-pinned ruff `//:ruff_format_check` and
`tests/test_seed_fixed_point.py` enforce — so the hook can produce bytes the lint lane rejects.

Close it by pointing the hook at the pinned toolchain (`//:ruff_fix` currently formats the whole
workspace and takes no path argument, so this is either a new per-file target or dropping the
hook in favour of `make fix`) and dropping the failure mask, then adding `.claude/settings.json`
to `//:repo_tooling_files` so a regression is red. Deferred rather than fixed in review: the file
configures the repo owner's agent harness, which is the owner's call and not an implementation
detail of this migration. Location: `.claude/settings.json` (the `PostToolUse` command),
`BUILD.bazel` (`:repo_tooling_files`), `tests/test_uv_retirement.py`
(`test_tooling_config_invokes_no_uv`).
