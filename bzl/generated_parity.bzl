"""`generated_parity` — assert a Bazel-generated file equals its committed counterpart.

Interim scaffolding.  While a generated module is produced by a Bazel action *and* still
tracked in git, two copies of it exist and nothing forces them to agree: `bazel test //...`
runs against the action's output while a source-tree pytest imports the tracked file.  This
rule is the missing link — a build target whose stamp only materializes when every pair is
byte-identical, so a hand-edit to a tracked copy, or a generator change that was never
regenerated into the tree, fails the build instead of splitting the two lanes apart.

Pairing is by `short_path`: a file declared under `out_dir = "fltk/fegen"` in the root package
has short_path `fltk/fegen/<name>.py`, which is exactly the tracked file's short_path.  The
two `File`s therefore differ only in root (source tree vs bazel-out), which is what makes the
comparison meaningful and what keeps them out of each other's way as action inputs.
"""

_COMMAND = """
set -euo pipefail
stamp="$1"; params="${2#@}"
status=0
while IFS='|' read -r generated committed; do
    if ! diff -u "$committed" "$generated" >&2; then
        echo "generated_parity: $committed differs from the generated copy (above)" >&2
        status=1
    fi
done < "$params"
test "$status" -eq 0
: > "$stamp"
"""

def _pair_lines(generated, committed):
    """`(lines, violation)`: one `<generated path>|<committed path>` line per short_path.

    `violation` is the message for an unmatched short_path on either side, or None.  An
    unmatched path means the rule is comparing a set it was not given — a target that gained or
    lost an output, or a `committed` list that drifted.  Silently skipping it would make the
    gate pass while covering less than it claims, so the caller fails on the message.

    The message is returned rather than raised so it can be asserted in a Starlark unit test;
    `fail` cannot be caught.
    """
    by_short = {f.short_path: f for f in committed}
    lines = []
    for f in generated:
        match = by_short.pop(f.short_path, None)
        if match == None:
            return lines, ("generated_parity: generated file %s has no committed counterpart in `committed`." %
                           f.short_path)
        lines.append(f.path + "|" + match.path)
    if by_short:
        return lines, ("generated_parity: committed files with no generated counterpart: %s." %
                       ", ".join(sorted(by_short.keys())))
    return lines, None

def _generated_parity_impl(ctx):
    generated = ctx.files.generated
    committed = ctx.files.committed

    lines, violation = _pair_lines(generated, committed)
    if violation != None:
        fail(violation)

    stamp = ctx.actions.declare_file(ctx.label.name + ".stamp")
    params = ctx.actions.declare_file(ctx.label.name + ".pairs")
    ctx.actions.write(params, "".join([l + "\n" for l in lines]))

    args = ctx.actions.args()
    args.add(stamp)
    args.add("@" + params.path)

    ctx.actions.run_shell(
        outputs = [stamp],
        inputs = generated + committed + [params],
        arguments = [args],
        command = _COMMAND,
        mnemonic = "GeneratedParity",
        progress_message = "checking generated/committed parity for %{label}",
    )
    return [DefaultInfo(files = depset([stamp]))]

generated_parity = rule(
    implementation = _generated_parity_impl,
    doc = "Fails the build when a generated file differs from its committed counterpart.",
    attrs = {
        "committed": attr.label_list(
            allow_files = True,
            mandatory = True,
            doc = "The tracked source files, one per generated file.",
        ),
        "generated": attr.label_list(
            allow_files = True,
            mandatory = True,
            doc = "Targets whose output files are compared against `committed`, by short_path.",
        ),
    },
)

# Not public API. Exported solely for //tests/bazel_rules; may change without notice.
generated_parity_internals = struct(
    pair_lines = _pair_lines,
)
