#!/usr/bin/env python3
"""Install dependencies declared in skills/*/deps.json."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

MANAGER_INSTALL: dict[str, list[str]] = {
    "brew": ["brew", "install"],
    "npm": ["npm", "install", "-g"],
    "pipx": ["pipx", "install"],
    "pip": ["pip3", "install", "--user"],
    "go": ["go", "install"],
    "cargo": ["cargo", "install"],
}


def find_deps_files(skills_dir: Path) -> list[Path]:
    """Find all deps.json files in skill directories."""
    return sorted(skills_dir.glob("*/deps.json"))


def check_command(command: str) -> bool:
    """Check if a command is available on PATH."""
    return shutil.which(command) is not None


REQUIRED_KEYS = {"command", "manager", "package"}
PACKAGE_NAME_PATTERN = re.compile(r"^[@a-zA-Z0-9_./:=-]+$")


def validate_dep(dep: dict, skill_name: str) -> str | None:
    """Validate a dependency entry. Returns error message or None."""
    if not isinstance(dep, dict):
        return f"{skill_name}: dep must be an object"

    missing = REQUIRED_KEYS - dep.keys()
    if missing:
        return f"{skill_name}: missing keys {missing}"

    for key in REQUIRED_KEYS:
        if not isinstance(dep.get(key), str) or not dep[key].strip():
            return f"{skill_name}: {key!r} must be a non-empty string"

    if dep["manager"] not in MANAGER_INSTALL:
        return f"{skill_name}: unknown manager {dep['manager']!r}"

    if not PACKAGE_NAME_PATTERN.match(dep["package"]):
        return f"{skill_name}: suspicious package name {dep['package']!r}"

    return None


def install_dep(dep: dict, skill_name: str) -> bool:
    """Install a single dependency. Returns True if installed."""
    command = dep["command"]
    manager = dep["manager"]
    package = dep["package"]

    if check_command(command):
        print(f"  skip: {command} (already installed)")
        return False

    if manager not in MANAGER_INSTALL:
        print(
            f"  error: unknown manager {manager!r} for {command}",
            file=sys.stderr,
        )
        return False

    manager_bin = MANAGER_INSTALL[manager][0]
    if not check_command(manager_bin):
        print(
            f"  error: {manager_bin} not found, cannot install {command}",
            file=sys.stderr,
        )
        return False

    cmd = [*MANAGER_INSTALL[manager], package]
    print(f"  install: {command} via {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(
            f"  error: failed to install {command}: exit {exc.returncode}",
            file=sys.stderr,
        )
        return False

    return True


def install_skill_deps(deps_file: Path) -> int:
    """Install deps for a single skill. Returns 0 on success, 1 on failure."""
    skill_name = deps_file.parent.name

    try:
        data = json.loads(deps_file.read_text())
    except json.JSONDecodeError as exc:
        print(f"  error: {skill_name}/deps.json: {exc}", file=sys.stderr)
        return 1

    installed: list[str] = []
    failed: list[str] = []

    for dep in data.get("deps", []):
        error = validate_dep(dep, skill_name)
        if error:
            print(f"  error: {error}", file=sys.stderr)
            failed.append(dep.get("command", "unknown"))
            continue

        result = install_dep(dep, skill_name)
        if result:
            installed.append(dep["command"])
        elif not check_command(dep["command"]):
            failed.append(dep["command"])

    if installed:
        print(f"  installed: {', '.join(installed)}")
    if failed:
        print(f"  failed: {', '.join(failed)}", file=sys.stderr)
        return 1

    return 0


def main() -> int:
    """Entry point.

    Usage:
        install-deps.py              # install deps for all skills
        install-deps.py <skill>      # install deps for one skill
    """
    skills_dir = Path(__file__).resolve().parent

    if len(sys.argv) > 1:
        skill_name = sys.argv[1]
        skill_dir = skills_dir / skill_name
        deps_file = skill_dir / "deps.json"
        if not deps_file.exists():
            print(f"  no deps.json for skill {skill_name!r}")
            return 0
        return install_skill_deps(deps_file)

    deps_files = find_deps_files(skills_dir)
    if not deps_files:
        print("  no skill deps found")
        return 0

    rc = 0
    for deps_file in deps_files:
        if install_skill_deps(deps_file) != 0:
            rc = 1

    return rc


if __name__ == "__main__":
    sys.exit(main())
