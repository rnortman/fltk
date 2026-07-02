### 24. `bazel-neg-test-harness` — DO

- **Problem:** the public Bazel macro's misconfiguration guards (7 conditions protecting
  downstream users from confusing failures) have no automated test — verified once by
  hand; a future edit disabling a guard goes unnoticed.
- **Ground truth:** guards confirmed live post-unification (now 1 shared helper + 1
  templated loop, which makes testing *cheaper* than when the TODO was written);
  `bazel_skylib` confirmed absent from `MODULE.bazel`; `analysistest` is the standard,
  purpose-built mechanism for asserting analysis-time failures without breaking
  `bazel build //...`.
- **What the work looks like:** add `bazel_skylib` dep; one `analysistest` negative target
  per guard condition asserting failure with the expected message.
- **The case for skipping:** guards are simple and rarely edited; this adds a dep and
  Bazel boilerplate for a low-probability regression.
- **Recommendation: Do** — now that the Bazel Rust surface is confirmed working and public,
  its misconfiguration UX is API; cheap insurance.
