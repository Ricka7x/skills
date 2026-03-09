#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml"]
# ///
"""
package.py — Package a skill folder into a .skill file.

Usage:
    python package.py <skill-folder>
    python package.py ricka7x/better-auth-plugin

The .skill file will be saved next to the skill folder.
"""

import fnmatch
import re
import sys
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ Missing dependency: pyyaml")
    print("   Run: pip install pyyaml")
    sys.exit(1)

EXCLUDE_DIRS  = {"__pycache__", "node_modules", ".git"}
EXCLUDE_FILES = {".DS_Store"}
EXCLUDE_GLOBS = {"*.pyc"}
ROOT_EXCLUDE_DIRS = {"evals"}


def should_exclude(rel_path: Path) -> bool:
    parts = rel_path.parts
    if any(part in EXCLUDE_DIRS for part in parts):
        return True
    if len(parts) > 1 and parts[1] in ROOT_EXCLUDE_DIRS:
        return True
    name = rel_path.name
    if name in EXCLUDE_FILES:
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in EXCLUDE_GLOBS)


def validate(skill_path: Path) -> tuple[bool, str]:
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    content = skill_md.read_text()
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    try:
        fm = yaml.safe_load(match.group(1))
    except yaml.YAMLError as e:
        return False, f"Invalid YAML: {e}"

    if not isinstance(fm, dict):
        return False, "Frontmatter must be a YAML dictionary"

    allowed = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
    unexpected = set(fm.keys()) - allowed
    if unexpected:
        return False, f"Unexpected frontmatter key(s): {', '.join(sorted(unexpected))}"

    if "name" not in fm:
        return False, "Missing 'name' in frontmatter"
    if "description" not in fm:
        return False, "Missing 'description' in frontmatter"

    name = str(fm["name"]).strip()
    if not re.match(r"^[a-z0-9-]+$", name):
        return False, f"Name '{name}' must be kebab-case"
    if len(name) > 64:
        return False, f"Name too long ({len(name)} chars, max 64)"

    desc = str(fm["description"]).strip()
    if len(desc) > 1024:
        return False, f"Description too long ({len(desc)} chars, max 1024)"

    return True, "Skill is valid!"


def package(skill_path: Path) -> Path | None:
    skill_path = skill_path.resolve()

    if not skill_path.exists() or not skill_path.is_dir():
        print(f"❌ Not a directory: {skill_path}")
        return None

    print("🔍 Validating...")
    ok, msg = validate(skill_path)
    if not ok:
        print(f"❌ {msg}")
        return None
    print(f"✅ {msg}\n")

    out_file = skill_path.parent / f"{skill_path.name}.skill"

    with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in skill_path.rglob("*"):
            if not file.is_file():
                continue
            arcname = file.relative_to(skill_path.parent)
            if should_exclude(arcname):
                print(f"  Skipped: {arcname}")
                continue
            zf.write(file, arcname)
            print(f"  Added:   {arcname}")

    print(f"\n✅ Packaged → {out_file}")
    return out_file


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    result = package(Path(sys.argv[1]))
    sys.exit(0 if result else 1)