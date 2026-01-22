#!/usr/bin/env python3
"""
Validate Glance YAML with `$include` support.
- Expands includes starting from an entry file (default: config/glance.yml).
- Reports YAML syntax/indentation errors with file, line, column.
- Flags missing include targets and include cycles.
- Optional: write the fully-expanded YAML via --output.
Requires: PyYAML (`pip install pyyaml`).
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Set, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("PyYAML is required. Install with: pip install pyyaml\n")
    sys.exit(2)


@dataclass
class ValidationError:
    path: Path
    message: str
    line: int | None = None
    column: int | None = None
    context_lines: List[str] | None = None

    def __str__(self) -> str:
        loc = ""
        if self.line is not None and self.column is not None:
            loc = f":{self.line}:{self.column}"
        result = f"{self.path}{loc} - {self.message}"
        
        if self.context_lines and self.line is not None:
            result += "\n\nContext:\n"
            start_line = max(1, self.line - 5)
            for i, line_text in enumerate(self.context_lines, start=start_line):
                prefix = ">>> " if i == self.line else "    "
                result += f"{prefix}{i:4d} | {line_text}"
                if i == self.line and self.column is not None:
                    # Add pointer to the error column
                    pointer_offset = len(f"{prefix}{i:4d} | ") + self.column - 1
                    result += " " * pointer_offset + "^\n"
        
        return result


def _load_yaml(path: Path) -> Tuple[Any, List[ValidationError]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, [ValidationError(path, "file not found")]
    
    lines = text.splitlines(keepends=True)
    
    try:
        return yaml.safe_load(text), []
    except yaml.YAMLError as exc:  # includes indentation/scanner/parser errors
        line = getattr(getattr(exc, "problem_mark", None), "line", None)
        col = getattr(getattr(exc, "problem_mark", None), "column", None)
        # Convert to 1-based
        line = line + 1 if line is not None else None
        col = col + 1 if col is not None else None
        
        # Build a better error message
        problem = getattr(exc, "problem", None)
        context = getattr(exc, "context", None)
        
        msg_parts = []
        if isinstance(exc, yaml.scanner.ScannerError):
            msg_parts.append("YAML Scanner Error")
            if problem:
                msg_parts.append(problem)
            msg_parts.append("(check for tabs, special characters, or malformed structure)")
        elif isinstance(exc, yaml.parser.ParserError):
            msg_parts.append("YAML Parser Error")
            if problem:
                msg_parts.append(problem)
            if "mapping" in str(problem).lower():
                msg_parts.append("(likely indentation issue - check alignment of keys/values)")
            elif "sequence" in str(problem).lower():
                msg_parts.append("(likely indentation issue with list items)")
        else:
            msg_parts.append("YAML Error")
            if problem:
                msg_parts.append(problem)
        
        if context and context not in str(problem or ""):
            msg_parts.append(f"Context: {context}")
        
        msg = " - ".join(msg_parts)
        
        # Extract context lines
        context_lines = None
        if line is not None:
            start_idx = max(0, line - 6)  # -6 because line is 1-based
            end_idx = min(len(lines), line + 5)
            context_lines = lines[start_idx:end_idx]
        
        return None, [ValidationError(path, msg, line, col, context_lines)]


def _expand(node: Any, base_dir: Path, seen: Set[Path], errors: List[ValidationError]) -> Any:
    """Recursively expand $include nodes."""
    if isinstance(node, dict):
        if "$include" in node and len(node) == 1:
            target = Path(node["$include"])
            include_path = (base_dir / target).resolve()
            if include_path in seen:
                errors.append(ValidationError(include_path, "include cycle detected"))
                return None
            included, errs = _load_yaml(include_path)
            errors.extend(errs)
            if errs:
                return None
            seen.add(include_path)
            expanded = _expand(included, include_path.parent, seen, errors)
            seen.remove(include_path)
            return expanded
        # regular mapping: walk values
        return {k: _expand(v, base_dir, seen, errors) for k, v in node.items()}
    if isinstance(node, list):
        return [_expand(item, base_dir, seen, errors) for item in node]
    return node


def validate(entry: Path, output: Path | None = None) -> int:
    errors: List[ValidationError] = []
    data, errs = _load_yaml(entry)
    errors.extend(errs)
    if not errs:
        expanded = _expand(data, entry.parent, {entry.resolve()}, errors)
    else:
        expanded = None

    if errors:
        sys.stderr.write(f"Found {len(errors)} problem(s):\n")
        for err in errors:
            sys.stderr.write(f" - {err}\n")
        return 1

    if output:
        try:
            dumped = yaml.safe_dump(expanded, sort_keys=False, allow_unicode=False)
            output.write_text(dumped, encoding="utf-8")
        except OSError as exc:  # pragma: no cover
            sys.stderr.write(f"Could not write output file: {exc}\n")
            return 2
    sys.stdout.write("OK: YAML parsed and includes expanded successfully.\n")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Glance YAML with $include support.")
    parser.add_argument(
        "--entry",
        "-e",
        default="config/glance.yml",
        type=Path,
        help="entrypoint YAML file",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="optional path to write the fully expanded YAML",
    )
    args = parser.parse_args()

    sys.exit(validate(args.entry, args.output))


if __name__ == "__main__":
    main()
