# Glance YAML Linter

[![Tests](https://github.com/M1XZG/glance-linter/actions/workflows/tests.yml/badge.svg)](https://github.com/M1XZG/glance-linter/actions/workflows/tests.yml)
[![CodeQL](https://github.com/M1XZG/glance-linter/actions/workflows/codeql.yml/badge.svg)](https://github.com/M1XZG/glance-linter/actions/workflows/codeql.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![MIT license](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Find the source file and line that broke a modular [Glance](https://github.com/glanceapp/glance) dashboard before the next reload.

Glance YAML Linter follows Glance's real [`$include:` expansion rules](https://github.com/glanceapp/glance/blob/main/docs/configuration.md#including-other-config-files), checks the combined YAML for syntax and duplicate-key errors, then maps failures back to the original source file. It also supports Glance's `!include:` alias. This is useful when a parser error in a large include tree would otherwise point somewhere in the merged configuration.

```text
$ glance-lint ~/glance/config/glance.yml
Found 1 problem(s):
/home/user/glance/config/widgets/weather.yml:7:3 - YAML error: expected <block end>, but found '<block mapping start>'

Context:
       5 | - type: weather
       6 |   location: London
>>>    7 |  units: metric
             ^
```

## Install

Install the command directly from GitHub with [`pipx`](https://pipx.pypa.io/):

```bash
pipx install git+https://github.com/M1XZG/glance-linter.git
```

Python 3.10 or newer is required. A virtual environment also works:

```bash
git clone https://github.com/M1XZG/glance-linter.git
cd glance-linter
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
```

## Use

Pass the main Glance configuration file:

```bash
glance-lint /path/to/config/glance.yml
```

If the file is named `glance.yml` in the current directory, no argument is needed. The linter also falls back to `config/glance.yml`, which matches a common Docker volume layout.

Write the fully expanded configuration for inspection or diffing:

```bash
glance-lint config/glance.yml --output build/glance-expanded.yml
```

The expanded output preserves comments, formatting and `${VARIABLE}` references. Include paths are resolved relative to the file containing each directive, as they are in Glance.

Existing checkouts can keep using the original command:

```bash
python scripts/validate_glance.py --entry config/glance.yml
```

## What it checks

The linter catches malformed YAML, indentation errors, duplicate mapping keys, missing include targets, unreadable files, include cycles and trees deeper than Glance's 20-level limit. Both Glance include forms are supported:

```yaml
pages:
  - $include: home.yml
  - !include: homelab.yml
```

Included files do not need extra indentation:

```yaml
- type: weather
  location: London
- type: clock
```

This is a syntax and include-tree linter. Current Glance releases also provide full application-level validation for widget options, required pages and other schema rules:

```bash
glance --config config/glance.yml config:validate
```

Using both checks gives you source-focused YAML errors from `glance-lint` and Glance's authoritative configuration validation.

## Optional config file

For a frequently checked dashboard, copy [`config-example.txt`](config-example.txt) to `config.txt` and edit the paths:

```ini
entry=config/glance.yml
output=build/glance-expanded.yml
```

Relative paths are resolved from the config file's directory. Explicit command-line arguments take precedence. Use `--no-config-file` when you want to ignore it.

## Development

Install the package in editable mode and run the standard-library test suite:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -v
```

The project is licensed under the [MIT License](LICENSE). Bug reports and focused pull requests are welcome.
