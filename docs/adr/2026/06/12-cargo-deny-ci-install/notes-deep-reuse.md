## reuse-1

**File:line:** `Makefile:57-65` (the `check:` recipe body)

**What's duplicated:** The mktemp/capture/print-on-failure/cleanup shell pattern is written out inline in `check`'s recipe:

```makefile
@tmpfile=$$(mktemp); \
if ! $(MAKE) cargo-deny >"$$tmpfile" 2>&1; then \
    echo "FAILED: cargo-deny"; \
    cat "$$tmpfile"; \
    rm -f "$$tmpfile"; \
    exit 1; \
fi; \
rm -f "$$tmpfile"; \
```

**Existing equivalent:** The identical pattern appears inside the `for` loop body of `check-common` (`Makefile:42-49`). That loop iterates a list of steps; `check` runs exactly one additional step (`cargo-deny`) after `check-common` completes, so the same pattern is hand-rolled again rather than extracted.

**Consequence:** If the run-and-capture idiom ever changes (e.g., adding a timeout, changing the failure message format, or switching from `mktemp` to a named temp dir), both sites must be updated in sync. Divergence would produce inconsistent output formatting between the `check-common` steps and the `cargo-deny` step when `make check` is run locally.

**Note:** Makefile has no built-in function abstraction; extraction would require a `define`/`call` macro. The duplication is modest (8 lines) and the two sites are adjacent and obviously related, so the maintenance risk is low. Flagged for awareness rather than urgency.
