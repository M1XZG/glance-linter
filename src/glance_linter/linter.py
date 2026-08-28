from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Any

import yaml


INCLUDE_PATTERN = re.compile(
    r"^([ \t]*)(?:-[ \t]*)?(?:!|\$)include:[ \t]*(.+)$"
)
MAX_INCLUDE_DEPTH = 20


@dataclass(frozen=True)
class SourceLocation:
    path: Path
    line: int
    added_indent: int = 0


@dataclass(frozen=True)
class ExpandedConfig:
    text: str
    sources: tuple[SourceLocation, ...]
    files: frozenset[Path]


@dataclass(frozen=True)
class Diagnostic:
    path: Path
    message: str
    line: int | None = None
    column: int | None = None


class ExpansionError(Exception):
    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    source_keys: set[tuple[str, str]] = set()
    for key_node, value_node in node.value:
        source_key = (key_node.tag, key_node.value)
        if source_key in source_keys:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key ({key_node.value})",
                key_node.start_mark,
            )
        source_keys.add(source_key)

        key = loader.construct_object(key_node, deep=deep)
        try:
            key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable key",
                key_node.start_mark,
            ) from exc
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _read_text(path: Path, location: SourceLocation | None = None) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        if location is None:
            diagnostic = Diagnostic(path, f"could not read file: {exc}")
        else:
            diagnostic = Diagnostic(
                location.path,
                f"could not read include {path}: {exc}",
                location.line,
                1,
            )
        raise ExpansionError(diagnostic) from exc


def _expand_file(
    path: Path,
    stack: tuple[Path, ...],
    depth: int,
    include_location: SourceLocation | None = None,
) -> ExpandedConfig:
    absolute_path = Path(os.path.abspath(path.expanduser()))
    identity = absolute_path.resolve()
    if identity in stack:
        cycle = " -> ".join(item.name for item in (*stack, identity))
        location = include_location or SourceLocation(absolute_path, 1)
        raise ExpansionError(
            Diagnostic(
                location.path,
                f"include cycle detected: {cycle}",
                location.line,
                1,
            )
        )
    if depth > MAX_INCLUDE_DEPTH:
        location = include_location or SourceLocation(absolute_path, 1)
        raise ExpansionError(
            Diagnostic(
                location.path,
                f"include depth exceeds Glance's limit of {MAX_INCLUDE_DEPTH}",
                location.line,
                1,
            )
        )

    text = _read_text(absolute_path, include_location)
    output_lines: list[str] = []
    source_map: list[SourceLocation] = []
    files = {absolute_path}

    for line_number, line in enumerate(text.split("\n"), start=1):
        match = INCLUDE_PATTERN.fullmatch(line)
        if match is None:
            output_lines.append(line)
            source_map.append(SourceLocation(absolute_path, line_number))
            continue

        indent, include_value = match.groups()
        include_path = Path(include_value.strip()).expanduser()
        if not include_path.is_absolute():
            include_path = absolute_path.parent / include_path

        directive_location = SourceLocation(absolute_path, line_number)
        included = _expand_file(
            include_path,
            (*stack, identity),
            depth + 1,
            directive_location,
        )
        included_lines = included.text.split("\n")
        output_lines.extend(indent + item for item in included_lines)
        source_map.extend(
            SourceLocation(source.path, source.line, source.added_indent + len(indent))
            for source in included.sources
        )
        files.update(included.files)

    return ExpandedConfig(
        "\n".join(output_lines),
        tuple(source_map),
        frozenset(files),
    )


def expand_config(entry: Path) -> ExpandedConfig:
    return _expand_file(entry, (), 0)


def _yaml_message(exc: yaml.YAMLError) -> str:
    problem = getattr(exc, "problem", None)
    context = getattr(exc, "context", None)
    parts = ["YAML error"]
    if problem:
        parts.append(str(problem))
    if context and context != problem:
        parts.append(str(context))
    return ": ".join(parts)


def lint_config(entry: Path) -> tuple[ExpandedConfig | None, list[Diagnostic]]:
    try:
        expanded = expand_config(entry)
    except ExpansionError as exc:
        return None, [exc.diagnostic]

    try:
        yaml.load(expanded.text, Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        if mark is None or not expanded.sources:
            return expanded, [Diagnostic(entry, _yaml_message(exc))]

        index = min(mark.line, len(expanded.sources) - 1)
        source = expanded.sources[index]
        column = max(1, mark.column + 1 - source.added_indent)
        return expanded, [
            Diagnostic(
                source.path,
                _yaml_message(exc),
                source.line,
                column,
            )
        ]

    return expanded, []
