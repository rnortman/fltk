# Deep-Quality Review Notes

Commit reviewed: edb782c (base: 604dab1)

---

quality-1

**File:line**: `Makefile:36-38` (check-common recipe comment)

**Issue**: The comment on `check-common` says "DO NOT ADD STEPS HERE DIRECTLY — add them to the `steps` variable so both `check` and `check-ci` inherit them automatically via check-common." The `steps` variable is not a Make variable — it is a shell variable local to the recipe's shell script. The phrasing "add them to the `steps` variable" is accurate at the shell level, but "DO NOT ADD STEPS HERE DIRECTLY" is confusing: a reader could interpret "here" as "to the `check-common` recipe body" (which is exactly where they should add the new step, inside the `@steps="…"` string). The block comment above (lines 27–32) states the rule correctly ("must be added to check-common"); the recipe-level comment contradicts it by telling readers not to add to `check-common`. The block comment is the authoritative statement; the recipe comment should be removed or rewritten to say "add the step name to the \`steps\` string inside this recipe."

**Consequence**: Anti-drift is the stated key quality concern. A future developer reading only the recipe comment (the closest guidance at the point of edit) will be told "do not add here" and may add the step directly to `check` or `check-ci`, which is exactly the violation the rule prohibits. The structural protection provided by `check-common` is undermined by the most local documentation.

**Fix**: Replace `Makefile:36-38` with:

```makefile
# Shared base: all checks except cargo-deny.
# ADD new steps here by appending the target name to the `steps` string below.
# DO NOT add new steps directly to `check` or `check-ci` — they inherit via this target.
```

---

No other findings.
