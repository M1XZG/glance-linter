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

### Failed validation (indentation error)
```
(.venv) user@host:glance-linter/ (main) $ python scripts/validate_glance.py
Found 1 problem(s):
 - /path/to/config/widgets/port-docktopus.yml:25:3 - YAML Parser Error - mapping values are not allowed here - (likely indentation issue - check alignment of keys/values)

Context:
    21 |             <li data-popover-type="text" data-popover-text="Containers: {{ .JSON.Int "Snapshots.0.ContainerCount" }}">
    22 |               <p style="display:inline-flex;align-items:center;">
    23 |                 <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="height:1em;vertical-align:middle;margin-right:0.5em;" class="size-6 lucide lucide-box icon inline-flex" aria-hidden="true" role="img"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"></path><path d="m3.3 7 8.7 5 8.7-5"></path><path d="M12 22V12"></path></svg>
>>> 25 |   {{ .JSON.Int "Snapshots.0.ContainerCount" }}
                  ^
    26 |               </p>
    27 |             </li>
    28 |             <li data-popover-type="text" data-popover-text="Volumes: {{ .JSON.Int "Snapshots.0.VolumeCount" }}">
    29 |               <p style="display:inline-flex;align-items:center;">
```
The caret (`^`) points to column 19 where the parser detected the issue. Fix indentation in the YAML file.
