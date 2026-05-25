.PHONY: check lint typecheck test

# Run all checks: lint, type-check, and tests. This is the canonical
# entry point used by CI.
check: lint typecheck test

lint:
	uv run --group lint --group test ruff check .

typecheck:
	uv run --group lint --group test pyright

test:
	uv run --group lint --group test pytest
