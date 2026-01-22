# Glance YAML Linter

Purpose: catch broken Glance dashboard configs _before_ the container starts. This tool mirrors the `$include` layout style from the official [glanceapp/glance](https://github.com/glanceapp/glance) repo: it expands every `$include` under `config/glance.yml`, checks YAML structure/indentation, and reports exactly where things fail (file, line, column) with 5 lines of context and a caret pointing to the offending column.

## Quick start
1) Create and activate a virtualenv (local, ignored by git):
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
2) Install deps: `pip install -r scripts/requirements.txt`

## Running the linter
- Validate using the default entrypoint (`config/glance.yml`):
  - `python scripts/validate_glance.py`
- Write the fully expanded YAML (handy for debugging or diffing):
  - `python scripts/validate_glance.py -o /tmp/glance-expanded.yml`

## What it flags
- YAML scanner/parser errors (indentation, bad lists/mappings, tabs, malformed tokens)
- Missing `$include` targets
- Include cycles
- Offending line/column highlighted with 5 lines of surrounding context

## Notes
- `.venv/`, `__pycache__/`, `*.pyc`, and `.env` are ignored by `.gitignore`.
- Deactivate the venv when done: `deactivate`.
