slop-1:
- Disposition: Fixed
- Action: Collapsed the two-step name resolution into a single `.map(...).unwrap_or_else(...)` chain; removed the dead first `.unwrap_or("<unknown>")` and the redundant `if/else` block. errors.rs:153-157.
- Severity assessment: Dead code misleading reviewers into believing `"<unknown>"` was reachable; no runtime impact.

slop-2:
- Disposition: Fixed
- Action: Removed the dead `recursion = ri.clone()` assignment inside the loop body (the local was never read after that point), dropped the now-unnecessary `mut` on the parameter, and deleted the `let _ = recursion; // consumed` suppressor that was masking the compiler warning. memo.rs:322-324, 313.
- Severity assessment: The suppressor was hiding a real unused-assignment compiler warning; the assignment itself was dead. No behavioral change.

slop-3:
- Disposition: Fixed
- Action: Replaced the task-authoring docstring with `"The returned reference is valid for the lifetime of this \`SourceText\`."`. span.rs:75-80 (fltk-cst-core).
- Severity assessment: Cosmetic; the stale caller reference would mislead maintainers adding new uses of the method.
