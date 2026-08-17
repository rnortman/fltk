"""Emit the compile-gate crate's sources into a directory named on the command line.

The crate is a build output. `//tests:rust_gate_srcs` writes it, `//tests:rust_gate_lib` compiles
its modules and `//tests:rust_gate_runtime_test` runs their `#[test]`s; the file set is
`tests/rust_gate_cases.py`'s `CASES`, and `tests/test_rust_gate_manifest.py` holds the BUILD
file's declared outputs to it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tests.rust_gate_cases import CASES, write_crate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path, help="the crate's src directory")
    arguments = parser.parse_args()
    write_crate(arguments.out_dir, CASES)


if __name__ == "__main__":
    main()
