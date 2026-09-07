from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "skills"
    / "create-release-process"
    / "templates"
    / "release"
    / "scripts"
    / "release.py"
)
SPEC = importlib.util.spec_from_file_location("release_script", SCRIPT)
assert SPEC and SPEC.loader
release = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release
SPEC.loader.exec_module(release)


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True)


class ReleaseScriptTests(unittest.TestCase):
    def test_semver_bumps(self) -> None:
        self.assertEqual(release.bump_semver("1.2.3", "patch"), "1.2.4")
        self.assertEqual(release.bump_semver("1.2.3", "minor"), "1.3.0")
        self.assertEqual(release.bump_semver("1.2.3", "major"), "2.0.0")

    def test_repo_file_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory).resolve()
            with self.assertRaisesRegex(release.ReleaseError, "inside the repository"):
                release.repo_file(repo, "../notes.md", "notes file")

    def test_config_rejects_legacy_builtin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory).resolve()
            (repo / "release.toml").write_text(
                '[release]\nname = "demo"\nrunner = ["builtin:cargo-release"]\n'
            )
            with self.assertRaisesRegex(release.ReleaseError, "unsupported legacy"):
                release.load_config(repo, "release.toml")

    def test_config_allows_empty_argument_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory).resolve()
            (repo / "release.toml").write_text(
                '[release]\nname = "demo"\nrunner = ["tool", "--tag-prefix", ""]\n'
            )
            _, config = release.load_config(repo, "release.toml")
            self.assertEqual(config["release"]["runner"][-1], "")

    def test_check_reports_each_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory).resolve()
            config_path = repo / "release.toml"
            config_path.write_text(
                """
[release]
name = "demo"
runner = ["python3", "-c", "pass"]
dry_run_args = ["--dry-run"]

[checks]
commands = [
  ["python3", "-c", "print('ok')"],
  ["python3", "-c", "raise SystemExit(7)"],
]
""".lstrip()
            )
            path, config = release.load_config(repo, "release.toml")
            result = release.execute_check(repo, path, config)
            self.assertFalse(result["ready"])
            self.assertEqual([item["exit_status"] for item in result["checks"]], [0, 7])

    def test_run_defaults_to_configured_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory).resolve()
            config_path = repo / "release.toml"
            config_path.write_text(
                f"""
[release]
name = "demo"
runner = ["{sys.executable}", "-c", "import sys; assert sys.argv[1:] == ['--dry-run', '--bump', 'patch']"]
dry_run_args = ["--dry-run"]
""".lstrip()
            )
            path, config = release.load_config(repo, "release.toml")
            args = argparse.Namespace(
                apply=False,
                version=None,
                bump="patch",
                notes_file=None,
                not_latest=False,
            )
            result = release.execute_run(repo, path, config, args)
            self.assertEqual(result["mode"], "dry_run")
            self.assertTrue(result["executed"])

    def test_cargo_dry_run_restores_version_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            test_root = Path(directory).resolve()
            repo = test_root / "repo"
            remote = test_root / "remote.git"
            repo.mkdir()
            run("git", "init", "--bare", str(remote), cwd=test_root)
            run("git", "init", "-b", "main", cwd=repo)
            run("git", "config", "user.name", "Release Test", cwd=repo)
            run("git", "config", "user.email", "release@example.invalid", cwd=repo)
            run("git", "remote", "add", "origin", str(remote), cwd=repo)
            manifest = '[package]\nname = "demo"\nversion = "1.2.3"\n'
            lockfile = 'version = 4\n\n[[package]]\nname = "demo"\nversion = "1.2.3"\n'
            (repo / "Cargo.toml").write_text(manifest)
            (repo / "Cargo.lock").write_text(lockfile)
            run("git", "add", "Cargo.toml", "Cargo.lock", cwd=repo)
            run("git", "commit", "-m", "test fixture", cwd=repo)

            args = argparse.Namespace(
                version_source="Cargo.toml",
                version_target=["Cargo.toml"],
                lockfile=["Cargo.lock"],
                version=None,
                bump="patch",
                tag_prefix="v",
                notes_file=None,
                notes_required=False,
                dry_run=True,
                branch="main",
                provider="github",
                check=[f"{sys.executable} -c pass"],
                not_latest=False,
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(release.cargo_release(repo, args), 0)

            self.assertIn("Dry run succeeded for demo v1.2.4", output.getvalue())
            self.assertEqual((repo / "Cargo.toml").read_text(), manifest)
            self.assertEqual((repo / "Cargo.lock").read_text(), lockfile)
            self.assertEqual(run("git", "status", "--short", cwd=repo).stdout, "")
            self.assertEqual(run("git", "tag", "--list", cwd=repo).stdout, "")

    def test_version_file_dry_run_restores_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            test_root = Path(directory).resolve()
            repo = test_root / "repo"
            remote = test_root / "remote.git"
            repo.mkdir()
            run("git", "init", "--bare", str(remote), cwd=test_root)
            run("git", "init", "-b", "main", cwd=repo)
            run("git", "config", "user.name", "Release Test", cwd=repo)
            run("git", "config", "user.email", "release@example.invalid", cwd=repo)
            run("git", "remote", "add", "origin", str(remote), cwd=repo)
            (repo / "VERSION").write_text("0.1.0\n")
            run("git", "add", "VERSION", cwd=repo)
            run("git", "commit", "-m", "test fixture", cwd=repo)

            args = argparse.Namespace(
                version_file="VERSION",
                version=None,
                bump="minor",
                tag_prefix="v",
                notes_file=None,
                notes_required=False,
                dry_run=True,
                branch="main",
                provider="github",
                check=[f"{sys.executable} -c pass"],
                not_latest=False,
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(release.version_file_release(repo, args), 0)

            self.assertIn("Dry run succeeded for v0.2.0", output.getvalue())
            self.assertEqual((repo / "VERSION").read_text(), "0.1.0\n")
            self.assertEqual(run("git", "status", "--short", cwd=repo).stdout, "")
            self.assertEqual(run("git", "tag", "--list", cwd=repo).stdout, "")

    def test_release_toml_runs_tag_only_non_semver_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            test_root = Path(directory).resolve()
            repo = test_root / "repo"
            remote = test_root / "remote.git"
            repo.mkdir()
            run("git", "init", "--bare", str(remote), cwd=test_root)
            run("git", "init", "-b", "main", cwd=repo)
            run("git", "config", "user.name", "Release Test", cwd=repo)
            run("git", "config", "user.email", "release@example.invalid", cwd=repo)
            run("git", "remote", "add", "origin", str(remote), cwd=repo)
            (repo / "scripts").mkdir()
            (repo / "scripts" / "release.py").write_bytes(SCRIPT.read_bytes())
            (repo / "README.md").write_text("test\n")
            (repo / "release.toml").write_text(
                f"""
[release]
name = "calendar-project"
runner = [
  "{sys.executable}", "scripts/release.py", "tag-release",
  "--provider", "github",
  "--tag-prefix", "",
]
dry_run_args = ["--dry-run"]
""".lstrip()
            )
            run("git", "add", ".", cwd=repo)
            run("git", "commit", "-m", "test fixture", cwd=repo)

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/release.py",
                    "run",
                    "--dry-run",
                    "--version",
                    "2026.09.07.0",
                    "--json",
                ],
                cwd=repo,
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            result = json.loads(completed.stdout)
            self.assertEqual(result["mode"], "dry_run")
            self.assertIn("Dry run succeeded for 2026.09.07.0", result["runner_stdout"])
            self.assertEqual(run("git", "tag", "--list", cwd=repo).stdout, "")

    def test_tag_release_rejects_invalid_git_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory).resolve()
            run("git", "init", "-b", "main", cwd=repo)
            with self.assertRaisesRegex(release.ReleaseError, "invalid Git tag"):
                release.release_tag(repo, "release~candidate", "")

    def test_release_toml_runs_bundled_cargo_runner_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            test_root = Path(directory).resolve()
            repo = test_root / "repo"
            remote = test_root / "remote.git"
            repo.mkdir()
            (repo / "scripts").mkdir()
            (repo / "scripts" / "release.py").write_bytes(SCRIPT.read_bytes())
            run("git", "init", "--bare", str(remote), cwd=test_root)
            run("git", "init", "-b", "main", cwd=repo)
            run("git", "config", "user.name", "Release Test", cwd=repo)
            run("git", "config", "user.email", "release@example.invalid", cwd=repo)
            run("git", "remote", "add", "origin", str(remote), cwd=repo)
            manifest = '[package]\nname = "demo"\nversion = "1.2.3"\n'
            lockfile = 'version = 4\n\n[[package]]\nname = "demo"\nversion = "1.2.3"\n'
            (repo / "Cargo.toml").write_text(manifest)
            (repo / "Cargo.lock").write_text(lockfile)
            (repo / "release.toml").write_text(
                f"""
[release]
name = "demo"
version_source = "Cargo.toml"
runner = [
  "{sys.executable}", "scripts/release.py", "cargo-release",
  "--version-source", "Cargo.toml",
  "--version-target", "Cargo.toml",
  "--lockfile", "Cargo.lock",
  "--tag-prefix", "v",
]
dry_run_args = ["--dry-run"]
""".lstrip()
            )
            run("git", "add", ".", cwd=repo)
            run("git", "commit", "-m", "test fixture", cwd=repo)

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/release.py",
                    "run",
                    "--dry-run",
                    "--bump",
                    "patch",
                    "--json",
                ],
                cwd=repo,
                check=False,
                text=True,
                capture_output=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            result = json.loads(completed.stdout)
            self.assertEqual(result["mode"], "dry_run")
            self.assertTrue(result["executed"])
            self.assertIn("Dry run succeeded for demo v1.2.4", result["runner_stdout"])
            self.assertEqual((repo / "Cargo.toml").read_text(), manifest)
            self.assertEqual((repo / "Cargo.lock").read_text(), lockfile)
            self.assertEqual(run("git", "status", "--short", cwd=repo).stdout, "")

    def test_json_error_is_machine_readable(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "plan", "--repo-path", "/missing", "--json"],
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn("error", json.loads(completed.stdout))


if __name__ == "__main__":
    unittest.main()
