Answer to the open question:

I disagree with the conclusion; we should run `bazel test --config lint //...`. And we should *also* run `bazel build --config lint //...`.  Running with the same `--config` will eliminate the analysis cache discard that's currently costing us time. Just run everything with `--config lint`. The argument that you won't know what failed is a bug justifying a bad decision: If something fails, we must know what failed. Make sure that we do -- bazel will definitely tell us what failed. If we don't pass that on to the user, that's our fault.
