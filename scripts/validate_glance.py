#!/usr/bin/env python3
"""Backward-compatible entry point for the glance-lint command."""

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from glance_linter.cli import main  # noqa: E402


if __name__ == "__main__":
    arguments = sys.argv[1:]
    has_config_choice = any(
        argument == "--no-config-file"
        or argument == "--config-file"
        or argument.startswith("--config-file=")
        for argument in arguments
    )
    if not has_config_choice:
        arguments.extend(["--config-file", str(REPOSITORY_ROOT / "config.txt")])
    sys.exit(main(arguments))
