# Glance Config

Helper notes for linting / validating the Glance YAML configuration before deploying.

## Setup
- From this directory, create and activate the virtualenv:
  - `python3 -m venv .venv`
  - `source .venv/bin/activate`
- Install dependencies: `pip install -r scripts/requirements.txt`

## Validate the config
- Run the validator (uses `config/glance.yml` as the entrypoint):
  - `python scripts/validate_glance.py`
- Get a fully expanded YAML (after resolving all `$include` files):
  - `python scripts/validate_glance.py -o /tmp/glance-expanded.yml`

## What it checks
- YAML syntax and indentation errors with file, line, and column.
- Missing `$include` targets and include cycles.

## Housekeeping
- `.venv/`, `__pycache__/`, and `*.pyc` are already ignored via `.gitignore`.
- Deactivate the venv when done: `deactivate`.
