"""Exercise the shipped wrapper at the real just -> shell -> uv boundary."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "skills/create-release-process/templates/release/release.just"


class ReleaseWrapperTests(unittest.TestCase):
    def setUp(self):
        self.just = shutil.which("just")
        self.assertIsNotNone(self.just, "just is required; do not skip boundary proof")
        self.temp = tempfile.TemporaryDirectory(prefix="release wrapper ")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.bin = self.repo / "bin"
        self.bin.mkdir()
        uv = self.bin / "uv"
        uv.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['ARGV_CAPTURE']).write_text(json.dumps(sys.argv[1:]))\n"
        )
        uv.chmod(0o755)
        self.capture = self.repo / "argv.json"
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        ARGV_CAPTURE=str(self.capture))

    def invoke(self, recipe, args):
        (self.repo / "justfile").write_text(recipe)
        return subprocess.run([self.just, "--justfile", str(self.repo / "justfile"),
                               "release", *args], cwd=self.repo, env=self.env,
                              capture_output=True, text=True)

    def test_literal_arguments_and_no_execution(self):
        cases = [[], ["check", "--json"],
                 ["run", "--dry-run", "--notes-file", "notes with spaces.md"],
                 ["single'quote", 'double"quote', "", "line\nbreak", "*"],
                 ["$(touch injected-dollar)", "`touch injected-backtick`",
                  "; touch injected-semicolon", "a && touch injected-and",
                  "a | touch injected-pipe", "$HOME", "\\", "--apply"]]
        for args in cases:
            with self.subTest(args=args):
                result = self.invoke(WRAPPER.read_text(), args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(self.capture.read_text()),
                                 ["run", "scripts/release.py", *args])
                self.assertEqual(list(self.repo.glob("injected-*")), [])

    def test_fixture_detects_old_interpolation_failure(self):
        # Negative control: interpolation places caller text into shell source.
        unsafe = 'release *args:\n    uv run scripts/release.py {{args}}\n'
        args = ["$(touch injected-dollar)", "notes with spaces.md"]
        result = self.invoke(unsafe, args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.repo / "injected-dollar").exists())
        self.assertNotEqual(json.loads(self.capture.read_text()),
                            ["run", "scripts/release.py", *args])
