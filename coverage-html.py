#!/usr/bin/env python3
"""Run pytest with coverage and generate HTML report."""
# ruff: noqa: T201, S603

import shutil
import subprocess
import sys


def main():
    """Run pytest with coverage and generate HTML report."""
    # Check if uv is available
    uv_path = shutil.which("uv")
    if not uv_path:
        print("✗ Error: 'uv' command not found. Please install uv.", file=sys.stderr)
        sys.exit(1)

    try:
        # Run pytest with coverage
        print("Running pytest with coverage...")
        subprocess.run([uv_path, "run", "coverage", "run", "--source=fltk", "-m", "pytest"], check=True)

        # Generate HTML report
        print("Generating HTML coverage report...")
        subprocess.run([uv_path, "run", "coverage", "html"], check=True)

        print("✓ HTML coverage report generated at htmlcov/index.html")

    except subprocess.CalledProcessError as e:
        print(f"✗ Error running coverage: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
