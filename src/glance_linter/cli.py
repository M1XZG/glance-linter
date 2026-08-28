from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from . import __version__
from .linter import Diagnostic, lint_config


def _settings(path: Path) -> dict[str, Path]:
    if not path.exists():
        return {}

    values: dict[str, Path] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"could not read {path}: {exc}") from exc

    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_number}: expected key=value")
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in {"entry", "output"}:
            raise ValueError(f"{path}:{line_number}: unknown setting {key!r}")
        if not value:
            raise ValueError(f"{path}:{line_number}: {key} cannot be empty")
        configured_path = Path(value).expanduser()
        if not configured_path.is_absolute():
            configured_path = path.parent / configured_path
        values[key] = configured_path
    return values


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="glance-lint",
        description=(
            "Check Glance YAML syntax and $include/!include trees with "
            "source-aware error messages."
        ),
    )
    parser.add_argument("entry", nargs="?", type=Path, help="path to glance.yml")
    parser.add_argument(
        "-e",
        "--entry",
        dest="entry_option",
        type=Path,
        help="path to glance.yml (legacy form)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="write the Glance-compatible expanded YAML to this path",
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        default=Path("config.txt"),
        help="optional key=value settings file (default: ./config.txt)",
    )
    parser.add_argument(
        "--no-config-file",
        action="store_true",
        help="do not read config.txt",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def _context(diagnostic: Diagnostic, radius: int = 5) -> str:
    if diagnostic.line is None:
        return ""
    try:
        lines = diagnostic.path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return ""

    start = max(1, diagnostic.line - radius)
    end = min(len(lines), diagnostic.line + radius)
    rendered = ["", "Context:"]
    for number in range(start, end + 1):
        prefix = ">>> " if number == diagnostic.line else "    "
        rendered.append(f"{prefix}{number:4d} | {lines[number - 1]}")
        if number == diagnostic.line and diagnostic.column is not None:
            gutter = len(f"{prefix}{number:4d} | ")
            rendered.append(" " * (gutter + diagnostic.column - 1) + "^")
    return "\n".join(rendered)


def _print_diagnostic(diagnostic: Diagnostic) -> None:
    location = str(diagnostic.path)
    if diagnostic.line is not None:
        location += f":{diagnostic.line}"
        if diagnostic.column is not None:
            location += f":{diagnostic.column}"
    sys.stderr.write(f"{location} - {diagnostic.message}\n")
    context = _context(diagnostic)
    if context:
        sys.stderr.write(f"{context}\n")


def _default_entry() -> Path:
    if Path("glance.yml").exists():
        return Path("glance.yml")
    return Path("config/glance.yml")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.entry is not None and args.entry_option is not None:
        parser.error("provide the entry path either positionally or with --entry, not both")

    try:
        settings = {} if args.no_config_file else _settings(args.config_file)
    except ValueError as exc:
        sys.stderr.write(f"glance-lint: {exc}\n")
        return 2

    entry = args.entry_option or args.entry or settings.get("entry") or _default_entry()
    output = args.output or settings.get("output")
    expanded, diagnostics = lint_config(entry)

    if diagnostics:
        sys.stderr.write(f"Found {len(diagnostics)} problem(s):\n")
        for diagnostic in diagnostics:
            _print_diagnostic(diagnostic)
        return 1

    if output is not None and expanded is not None:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(expanded.text, encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"glance-lint: could not write {output}: {exc}\n")
            return 2

    file_count = len(expanded.files) if expanded is not None else 0
    noun = "file" if file_count == 1 else "files"
    sys.stdout.write(
        f"OK: YAML parsed and includes expanded successfully ({file_count} {noun}).\n"
    )
    return 0
