.PHONY: check lint typecheck test cargo-check cargo-test cargo-clippy

# Run all checks: lint, type-check, tests, and Rust checks. This is the canonical
# entry point used by CI.
check: lint typecheck test cargo-check cargo-clippy cargo-test

lint:
	uv run --group lint --group test ruff check .

typecheck:
	uv run --group lint --group test pyright

test:
	uv run --group lint --group test pytest

cargo-check:
	cargo check

cargo-test:
	cargo test

cargo-clippy:
	cargo clippy -- -D warnings
