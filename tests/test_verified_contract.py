"""Real Git repositories; only GitHub's transport is replaced in recovery tests."""
import argparse
import contextlib
import io
import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_release import release, run


class VerifiedContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        run("git", "init", "--bare", str(self.root / "origin.git"), cwd=self.root)
        run("git", "init", "-b", "main", cwd=self.repo)
        run("git", "config", "user.name", "Test", cwd=self.repo)
        run("git", "config", "user.email", "test@example.invalid", cwd=self.repo)
        run("git", "remote", "add", "origin", str(self.root / "origin.git"), cwd=self.repo)
        (self.repo / "VERSION").write_text("1.0.0\n")
        self.commit()
        self.head = release.git(self.repo, "rev-parse", "HEAD")

    def commit(self):
        run("git", "add", ".", cwd=self.repo)
        run("git", "commit", "-m", "fixture", cwd=self.repo)

    def args(self, **kwargs):
        defaults = dict(apply=False, version="2026.09.07.0", bump=None,
                        notes_file=None, not_latest=False, expected_head=None,
                        expected_config=None, resume=False, contract=None,
                        dry_run=True, tag_prefix="", branch="main", provider="github",
                        notes_required=False, check=[])
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def config(self, checks=(), **extra):
        config = {"release": {"name": "fixture", "runner": [sys.executable, "-c", "pass"],
                              "dry_run_args": ["--dry-run"], **extra},
                  "checks": {"commands": list(checks)}}
        path = self.repo / "release.toml"
        path.write_text('[release]\nname="fixture"\nrunner=["unused"]\n')
        return path, config

    def test_failed_check_blocks_apply_and_dry_run(self):
        marker = self.root / "published"
        for apply in (False, True):
            path, config = self.config([[sys.executable, "-c", "raise SystemExit(9)"]],
                                       runner=[sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"])
            result = release.execute_run(self.repo, path, config, self.args(apply=apply))
            self.assertFalse(result["ready"])
            self.assertFalse(result["executed"])
            self.assertFalse(marker.exists())

    def test_plan_does_not_claim_readiness(self):
        path, config = self.config([[sys.executable, "-c", "raise SystemExit(9)"]])
        result = release.execute_plan(self.repo, path, config, self.args())
        self.assertIsNone(result["ready"])
        self.assertFalse(result["checks_verified"])
        self.assertEqual(result["target_commit"], self.head)
        self.assertEqual(result["version"], "2026.09.07.0")

    def test_stale_head_and_config_block_run(self):
        path, config = self.config()
        for args in (self.args(expected_head="0" * 40), self.args(expected_config="0" * 64)):
            with self.assertRaises(release.ReleaseError):
                release.execute_run(self.repo, path, config, args)

    def test_consumer_validator_runs_before_execution(self):
        path, config = self.config(validate_version_command=[sys.executable, "-c", "raise SystemExit(8)"])
        with self.assertRaises(release.ReleaseError):
            release.execute_run(self.repo, path, config, self.args())

    def test_publish_false_blocks_apply(self):
        path, config = self.config(publish=False)
        with self.assertRaisesRegex(release.ReleaseError, "publish"):
                release.execute_run(self.repo, path, config, self.args(apply=True))

    def test_provenance_detects_runner_drift(self):
        path = self.repo / "release.toml"
        prefix = ('[release]\nname="fixture"\nrunner=["unused"]\n[runner_source]\n'
                  'repository="https://github.com/iancleary/release-skills"\n'
                  'revision="' + 'a' * 40 + '"\nsha256="')
        path.write_text(prefix + '0' * 64 + '"\n')
        with self.assertRaisesRegex(release.ReleaseError, "checksum"):
            release.load_config(self.repo, "release.toml")
        digest = hashlib.sha256(Path(release.__file__).read_bytes()).hexdigest()
        path.write_text(prefix + digest + '"\n')
        release.load_config(self.repo, "release.toml")

    def test_prepared_protocol_runs_checks_through_public_cli(self):
        (self.repo / "release.py").write_bytes(Path(release.__file__).read_bytes())
        marker = self.root / "public-checks"
        check = [sys.executable, "-c", "from pathlib import Path; "
                 "assert Path('VERSION').read_text() == '1.1.0\\n'; "
                 f"p=Path({str(marker)!r}); p.write_text(p.read_text()+'x' if p.exists() else 'x')"]
        contract = self.repo / "release.toml"
        runner = [sys.executable, "release.py", "version-file-release", "--version-file", "VERSION"]
        contract.write_text('[release]\nname="fixture"\nrunner_protocol="prepared-v1"\nrunner='
                            + json.dumps(runner) + '\ndry_run_args=["--dry-run"]\n'
                            + '[checks]\ncommands=[' + json.dumps(check) + ']\n')
        self.commit()
        result = run(sys.executable, "release.py", "run", "--dry-run", "--version", "1.1.0", "--json", cwd=self.repo)
        self.assertTrue(json.loads(result.stdout)["checks_verified"])
        self.assertEqual(marker.read_text(), "x")
        self.assertEqual((self.repo / "VERSION").read_text(), "1.0.0\n")
        self.assertEqual(release.git(self.repo, "tag", "--list"), "")

    def test_checks_cannot_change_target_commit(self):
        path, config = self.config([["git", "commit", "--allow-empty", "-m", "unexpected"]])
        with self.assertRaisesRegex(release.ReleaseError, "HEAD changed"):
            release.execute_run(self.repo, path, config, self.args(expected_head=self.head))

    def test_unsafe_tag_is_rejected(self):
        for version in ("-bad", "a..b", "a b", "", "a\x00b"):
            with self.subTest(version=version), self.assertRaises(release.ReleaseError):
                release.release_tag(self.repo, version, "")

    def test_prepared_checks_see_new_version_once_and_restore(self):
        marker = self.root / "checks"
        check = [sys.executable, "-c", "from pathlib import Path; "
                 "assert Path('VERSION').read_text() == '1.1.0\\n'; "
                 f"p=Path({str(marker)!r}); p.write_text(p.read_text()+'x' if p.exists() else 'x')"]
        contract = self.repo / "release.toml"
        contract.write_text('[release]\nname="fixture"\nrunner=["unused"]\n'
                            '[checks]\ncommands=[' + json.dumps(check) + ']\n')
        self.commit()
        args = self.args(version="1.1.0", version_file="VERSION", contract=str(contract))
        with contextlib.redirect_stdout(io.StringIO()):
            release.version_file_release(self.repo, args)
        self.assertEqual(marker.read_text(), "x")
        self.assertEqual((self.repo / "VERSION").read_text(), "1.0.0\n")
        self.assertEqual(release.git(self.repo, "status", "--porcelain"), "")

    def test_failed_apply_checks_restore_version_without_tag(self):
        args = self.args(version="1.1.0", version_file="VERSION", dry_run=False,
                         check=[f'{sys.executable} -c "raise SystemExit(7)"'])
        real = release.run_command

        def transport(repo, argv):
            if argv[0] == "gh":
                return release.CommandResult(list(argv), True, 0, "", "")
            return real(repo, argv)

        with patch.object(release, "run_command", side_effect=transport):
            with self.assertRaises(release.ReleaseError):
                release.version_file_release(self.repo, args)
        self.assertEqual((self.repo / "VERSION").read_text(), "1.0.0\n")
        self.assertEqual(release.git(self.repo, "tag", "--list"), "")

    def test_resume_verifies_remote_target_and_is_repeatable(self):
        tag = "2026.09.07.0"
        args = self.args(dry_run=False, expected_head=self.head)
        real = release.run_command
        published = False
        fail_once = True
        creates = []

        def transport(repo, argv):
            nonlocal published, fail_once
            if argv[0] != "gh":
                return real(repo, argv)
            if argv[1] == "auth":
                return release.CommandResult(list(argv), True, 0, "", "")
            if argv[1] == "api":
                body = "HTTP/2 200 OK\n\n" + json.dumps({"tag_name": tag, "draft": False})
                return release.CommandResult(list(argv), published, 0 if published else 1,
                                             body if published else "HTTP/2 404 Not Found\n\n{}", "")
            creates.append(list(argv))
            if fail_once:
                fail_once = False
                return release.CommandResult(list(argv), False, 1, "", "simulated publish failure")
            published = True
            return release.CommandResult(list(argv), True, 0, "", "")

        with patch.object(release, "run_command", side_effect=transport), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(release.ReleaseError, "simulated"):
                release.tag_release(self.repo, args)
            self.assertIn(tag, release.git(self.repo, "ls-remote", "--tags", "origin"))
            args.resume = True
            release.tag_release(self.repo, args)
            release.tag_release(self.repo, args)
        self.assertEqual(len(creates), 2)
        self.assertEqual(release.git(self.repo, "rev-parse", "HEAD"), self.head)

    def test_resume_rejects_conflicting_remote_tag(self):
        run("git", "tag", "release", cwd=self.repo)
        run("git", "push", "origin", "refs/tags/release", cwd=self.repo)
        (self.repo / "VERSION").write_text("2.0.0\n")
        self.commit()
        with self.assertRaisesRegex(release.ReleaseError, "remote release tag"):
            release.verify_resume_tag(self.repo, "release", release.git(self.repo, "rev-parse", "HEAD"))

    def test_resume_stops_on_auth_or_network_error(self):
        args = self.args(resume=True)
        failure = release.CommandResult(["gh"], False, 1, "HTTP/2 403 Forbidden\n\n{}", "denied")
        with patch.object(release, "run_command", return_value=failure) as transport:
            with self.assertRaises(release.ReleaseError):
                release.publish_release(self.repo, args, "release", None)
            self.assertEqual(transport.call_count, 1)


if __name__ == "__main__":
    unittest.main()
