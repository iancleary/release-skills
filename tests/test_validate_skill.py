from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_skill.py"
SPEC = importlib.util.spec_from_file_location("validate_skill", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


class SkillValidatorTests(unittest.TestCase):
    def write_skill(self, root: Path, name: str, frontmatter: str) -> Path:
        skill = root / name
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            f"---\n{frontmatter}---\n\n# Skill\n\nUse this skill.\n"
        )
        return skill

    def test_accepts_required_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = self.write_skill(
                Path(directory),
                "example-skill",
                'name: example-skill\ndescription: "Use for an example task."\n',
            )
            validator.validate(skill)

    def test_rejects_extra_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = self.write_skill(
                Path(directory),
                "example-skill",
                "name: example-skill\ndescription: Example.\nmetadata: extra\n",
            )
            with self.assertRaisesRegex(ValueError, "only name and description"):
                validator.validate(skill)

    def test_rejects_directory_name_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill = self.write_skill(
                Path(directory),
                "example-skill",
                "name: another-skill\ndescription: Example.\n",
            )
            with self.assertRaisesRegex(ValueError, "must match directory"):
                validator.validate(skill)


if __name__ == "__main__":
    unittest.main()
