#!/usr/bin/env python3
"""Lint skills for security issues. Runs as a pre-commit check."""

import json
import re
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent

REQUIRED_DEP_KEYS = {"command", "manager", "package"}
VALID_MANAGERS = {"brew", "npm", "pipx", "pip", "go", "cargo"}
PACKAGE_NAME_PATTERN = re.compile(r"^[@a-zA-Z0-9_./:=-]+$")

DANGEROUS_PATTERNS = [
    (re.compile(r"\beval\s*\("), "eval() usage"),
    (re.compile(r"\bexec\s*\("), "exec() usage"),
    (re.compile(r"\bos\.system\s*\("), "os.system() usage"),
    (re.compile(r"shell\s*=\s*True"), "subprocess shell=True"),
    (re.compile(r"\bexcept\s*:"), "bare except clause"),
    (
        re.compile(
            r"(password|secret|token|api_key)\s*=\s*['\"][^'\"]+['\"]",
            re.IGNORECASE,
        ),
        "possible hardcoded secret",
    ),
]


def lint_deps_json(path: Path) -> list[str]:
    """Validate a deps.json file."""
    errors: list[str] = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]

    if not isinstance(data, dict) or "deps" not in data:
        return [f"{path}: missing 'deps' key"]

    for idx, dep in enumerate(data["deps"]):
        prefix = f"{path}: deps[{idx}]"

        if not isinstance(dep, dict):
            errors.append(f"{prefix}: must be an object")
            continue

        missing = REQUIRED_DEP_KEYS - dep.keys()
        if missing:
            errors.append(f"{prefix}: missing keys: {missing}")
            continue

        for key in REQUIRED_DEP_KEYS:
            if not isinstance(dep[key], str) or not dep[key].strip():
                errors.append(f"{prefix}: {key!r} must be a non-empty string")

        if dep.get("manager") not in VALID_MANAGERS:
            errors.append(
                f"{prefix}: unknown manager {dep.get('manager')!r}, "
                f"must be one of {VALID_MANAGERS}"
            )

        pkg = dep.get("package", "")
        if pkg and not PACKAGE_NAME_PATTERN.match(pkg):
            errors.append(
                f"{prefix}: suspicious package name {pkg!r} "
                f"— must match {PACKAGE_NAME_PATTERN.pattern}"
            )

    return errors


def lint_scripts(skill_dir: Path) -> list[str]:
    """Scan scripts for dangerous patterns."""
    errors: list[str] = []
    for script in skill_dir.rglob("*.py"):
        content = script.read_text()
        for line_num, line in enumerate(content.splitlines(), 1):
            for pattern, description in DANGEROUS_PATTERNS:
                if pattern.search(line):
                    errors.append(f"{script}:{line_num}: {description}")
    return errors


def lint_skill(skill_dir: Path) -> list[str]:
    """Lint a single skill directory."""
    errors: list[str] = []

    if not (skill_dir / "SKILL.md").exists():
        errors.append(f"{skill_dir}: missing SKILL.md")

    deps_file = skill_dir / "deps.json"
    if deps_file.exists():
        errors.extend(lint_deps_json(deps_file))

    errors.extend(lint_scripts(skill_dir))
    return errors


def main() -> int:
    """Entry point."""
    all_errors: list[str] = []

    skill_dirs = [
        d for d in SKILLS_DIR.iterdir()
        if d.is_dir()
        and not d.name.startswith(".")
        and d.name != "__pycache__"
    ]

    for skill_dir in sorted(skill_dirs):
        all_errors.extend(lint_skill(skill_dir))

    if all_errors:
        print("Skills security lint failed:", file=sys.stderr)
        for error in all_errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    print("Skills security lint passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
