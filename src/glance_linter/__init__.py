"""Source-aware YAML linting for Glance dashboard configuration."""

from .linter import Diagnostic, ExpandedConfig, expand_config, lint_config

__all__ = [
    "Diagnostic",
    "ExpandedConfig",
    "expand_config",
    "lint_config",
]

__version__ = "0.1.0"
