from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest

import yaml

from glance_linter.linter import expand_config, lint_config


class GlanceLinterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write(self, relative_path: str, contents: str) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        return path

    def test_expands_widget_lists_like_glance(self) -> None:
        entry = self.write(
            "glance.yml",
            "pages:\n"
            "  - name: Home\n"
            "    columns:\n"
            "      - size: full\n"
            "        widgets:\n"
            "          - $include: widgets.yml\n",
        )
        self.write(
            "widgets.yml",
            "- type: weather\n"
            "  location: London\n"
            "- type: clock\n",
        )

        expanded = expand_config(entry)
        parsed = yaml.safe_load(expanded.text)

        self.assertEqual(len(parsed["pages"][0]["columns"][0]["widgets"]), 2)
        self.assertNotIn("$include", expanded.text)

    def test_supports_bang_include_and_nested_relative_paths(self) -> None:
        entry = self.write("glance.yml", "pages:\n  - !include: pages/home.yml\n")
        self.write(
            "pages/home.yml",
            "- name: Home\n"
            "  columns:\n"
            "    - size: full\n"
            "      widgets:\n"
            "        - $include: ../widgets/clock.yml\n",
        )
        self.write("widgets/clock.yml", "type: clock\n")

        expanded, diagnostics = lint_config(entry)

        self.assertEqual(diagnostics, [])
        self.assertIsNotNone(expanded)
        self.assertEqual(len(expanded.files), 3)

    def test_maps_yaml_errors_to_the_included_source(self) -> None:
        entry = self.write(
            "glance.yml",
            "pages:\n"
            "  - name: Home\n"
            "    columns:\n"
            "      - size: full\n"
            "        widgets:\n"
            "          - $include: widgets.yml\n",
        )
        child = self.write(
            "widgets.yml",
            "- type: rss\n"
            " title: News\n",
        )

        _, diagnostics = lint_config(entry)

        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].path, child.resolve())
        self.assertEqual(diagnostics[0].line, 2)

    def test_rejects_duplicate_keys(self) -> None:
        entry = self.write(
            "glance.yml",
            "pages:\n"
            "  - name: Home\n"
            "    name: Duplicate\n",
        )

        _, diagnostics = lint_config(entry)

        self.assertEqual(len(diagnostics), 1)
        self.assertIn("duplicate key (name)", diagnostics[0].message)
        self.assertEqual(diagnostics[0].line, 3)

    def test_distinct_yaml_11_boolean_keys_are_not_duplicates(self) -> None:
        entry = self.write(
            "glance.yml",
            "pages:\n"
            "  - name: Home\n"
            "    headers:\n"
            "      yes: one\n"
            "      true: two\n",
        )

        _, diagnostics = lint_config(entry)

        self.assertEqual(diagnostics, [])

    def test_reports_missing_includes_without_a_traceback(self) -> None:
        entry = self.write(
            "glance.yml",
            "pages:\n"
            "  - $include: missing.yml\n",
        )

        _, diagnostics = lint_config(entry)

        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].path, entry.resolve())
        self.assertEqual(diagnostics[0].line, 2)
        self.assertIn("could not read include", diagnostics[0].message)

    def test_reports_include_cycles(self) -> None:
        entry = self.write("glance.yml", "$include: child.yml\n")
        self.write("child.yml", "$include: glance.yml\n")

        _, diagnostics = lint_config(entry)

        self.assertEqual(len(diagnostics), 1)
        self.assertIn("include cycle detected", diagnostics[0].message)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are not supported")
    def test_nested_includes_are_relative_to_the_symlink_path(self) -> None:
        entry = self.write(
            "glance.yml",
            "pages:\n"
            "  - $include: links/page.yml\n",
        )
        real_page = self.write(
            "real/page.yml",
            "- name: Home\n"
            "  columns:\n"
            "    - $include: column.yml\n",
        )
        self.write("links/column.yml", "- size: full\n  widgets: []\n")
        (self.root / "links").mkdir(exist_ok=True)
        (self.root / "links/page.yml").symlink_to(real_page)

        expanded, diagnostics = lint_config(entry)

        self.assertEqual(diagnostics, [])
        self.assertIsNotNone(expanded)
        self.assertIn("size: full", expanded.text)

    def test_expanded_output_preserves_comments_and_variables(self) -> None:
        entry = self.write(
            "glance.yml",
            "# dashboard\n"
            "pages:\n"
            "  - $include: page.yml\n",
        )
        self.write("page.yml", "name: ${PAGE_NAME}\n")

        expanded = expand_config(entry)

        self.assertIn("# dashboard", expanded.text)
        self.assertIn("${PAGE_NAME}", expanded.text)


if __name__ == "__main__":
    unittest.main()
