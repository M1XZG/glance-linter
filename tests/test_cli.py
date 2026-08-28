from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from glance_linter.cli import main


class CliTests(unittest.TestCase):
    def test_cli_writes_expanded_output(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "glance.yml"
            child = root / "page.yml"
            output = root / "build" / "expanded.yml"
            entry.write_text("pages:\n  - $include: page.yml\n", encoding="utf-8")
            child.write_text("name: Home\n", encoding="utf-8")
            stdout = StringIO()

            with redirect_stdout(stdout):
                code = main(
                    [
                        str(entry),
                        "--output",
                        str(output),
                        "--no-config-file",
                    ]
                )

            self.assertEqual(code, 0)
            self.assertIn("2 files", stdout.getvalue())
            self.assertEqual(output.read_text(encoding="utf-8"), "pages:\n  name: Home\n  \n")

    def test_cli_reports_source_context(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "glance.yml"
            child = root / "page.yml"
            entry.write_text("pages:\n  - $include: page.yml\n", encoding="utf-8")
            child.write_text("name: Home\n bad: value\n", encoding="utf-8")
            stderr = StringIO()

            with redirect_stderr(stderr):
                code = main([str(entry), "--no-config-file"])

            self.assertEqual(code, 1)
            self.assertIn(f"{child.resolve()}:2:", stderr.getvalue())
            self.assertIn(">>>", stderr.getvalue())

    def test_explicit_arguments_override_config_file(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            configured = root / "configured.yml"
            explicit = root / "explicit.yml"
            settings = root / "config.txt"
            configured.write_text("broken: [\n", encoding="utf-8")
            explicit.write_text("pages: []\n", encoding="utf-8")
            settings.write_text("entry=configured.yml\n", encoding="utf-8")

            code = main(
                [
                    str(explicit),
                    "--config-file",
                    str(settings),
                ]
            )

            self.assertEqual(code, 0)

    def test_malformed_config_file_is_an_error(self) -> None:
        with TemporaryDirectory() as directory:
            settings = Path(directory) / "config.txt"
            settings.write_text("entry\n", encoding="utf-8")
            stderr = StringIO()

            with redirect_stderr(stderr):
                code = main(["--config-file", str(settings)])

            self.assertEqual(code, 2)
            self.assertIn("expected key=value", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
