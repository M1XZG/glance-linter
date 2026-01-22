# Glance YAML Linter

 Purpose: catch broken Glance dashboard configs _before_ the container starts and after any edit that might break the dashboard. This tool mirrors the `$include` layout style from the official [glanceapp/glance](https://github.com/glanceapp/glance) repo: it expands every `$include` under `config/glance.yml`, checks YAML structure/indentation, and reports exactly where things fail (file, line, column) with 5 lines of context and a caret pointing to the offending column.

## Quick start
1) Create and activate a virtualenv (local, ignored by git):
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
2) Install deps: `pip install -r scripts/requirements.txt`

## Running the linter
- Configure once via `config.txt` (preferred) or via CLI:
  - `entry=/full/path/to/glance.yml`
  - `output=/full/path/to/output.yml` (defaults to `/tmp/glance-expanded.yml` if set in config)

- If `config.txt` exists, its values are used and override CLI flags.
- If `config.txt` is missing, CLI flags are honored (falling back to defaults).

- Validate using the configured entry:
  - `python scripts/validate_glance.py`
- Write the fully expanded YAML (handy for debugging or diffing):
  - `python scripts/validate_glance.py -o /tmp/glance-expanded.yml` (when no config file) or rely on `output` in `config.txt`.

## What it flags
- YAML scanner/parser errors (indentation, bad lists/mappings, tabs, malformed tokens)
- Missing `$include` targets
- Include cycles
- Offending line/column highlighted with 5 lines of surrounding context

## Notes
- `.venv/`, `__pycache__/`, `*.pyc`, and `.env` are ignored by `.gitignore`.
- Deactivate the venv when done: `deactivate`.

## Examples

### Successful validation
```
(.venv) user@host:glance-linter/ (main) $ python scripts/validate_glance.py
OK: YAML parsed and includes expanded successfully.
```

### Failed validation (missing indentation in list item)
```
(.venv) user@host:glance-linter/ (main) $ python scripts/validate_glance.py
Found 1 problem(s):
 - /path/to/config/home.yml:10:11 - YAML Parser Error - expected <block end>, but found '?' - Context: while parsing a block collection

Context:
       5 |         - $include: widgets/left-column.yml
       6 |
       7 |     - size: full
       8 |       widgets:
       9 |           - type: rss
>>>   10 |           title: Met Office SW England Warnings
                     ^
      11 |           limit: 30
      12 |           collapse-after: 10
      13 |           cache: 1h
      14 |           style: detailed-list
      15 |           feeds:
```
The `title:` should be indented level with `type:` (line 9). The parser expected the block to end but found another key at the wrong indentation level.
