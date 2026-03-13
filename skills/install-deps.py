#!/usr/bin/env python3
"""Install dependencies declared in skills/*/deps.json."""

import json
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


def main() -> int:
    """Entry point."""
    skills_dir = Path(__file__).resolve().parent
    deps_files = find_deps_files(skills_dir)

    if not deps_files:
        print("  no skill deps found")
        return 0

    installed: list[str] = []
    failed: list[str] = []

    for deps_file in deps_files:
        skill_name = deps_file.parent.name
        data = json.loads(deps_file.read_text())

        for dep in data.get("deps", []):
            result = install_dep(dep, skill_name)
            if result:
                installed.append(f"{skill_name}/{dep['command']}")
            elif not check_command(dep["command"]):
                failed.append(f"{skill_name}/{dep['command']}")

    if installed:
        print(f"  installed: {', '.join(installed)}")
    if failed:
        print(f"  failed: {', '.join(failed)}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
