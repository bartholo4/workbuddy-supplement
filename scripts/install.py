#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-platform installer/verifier/uninstaller for the workbuddy-supplement skill."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SKILL_NAME = "workbuddy-supplement"
TARGET_DIRS = {
    "antigravity": Path.home() / ".gemini" / "config" / "skills" / SKILL_NAME,
    "codex": Path.home() / ".codex" / "skills" / SKILL_NAME,
    "claude": Path.home() / ".claude" / "skills" / SKILL_NAME,
}
REQUIRED_REL_FILES = (
    Path("SKILL.md"),
    Path("scripts") / "wb_supplement.py",
    Path("references") / "free-sources-guide.md",
)


def _repo_skill_src() -> Path:
    return Path(__file__).resolve().parent.parent / "skills" / SKILL_NAME


def resolve_dest(target: str, custom_dest: str | None) -> Path:
    if target == "custom":
        if not custom_dest or not custom_dest.strip():
            raise ValueError("--dest is required when --target is 'custom'")
        return Path(custom_dest).expanduser().resolve()
    return TARGET_DIRS[target]


def install_skill(dest: Path) -> int:
    src = _repo_skill_src()
    for rel in REQUIRED_REL_FILES:
        if not (src / rel).is_file():
            print(f"Error: missing source file {src / rel}", file=sys.stderr)
            return 1
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"Installed {SKILL_NAME} -> {dest}")
    return 0


def check_skill(dest: Path, run_doctor: bool = True) -> int:
    missing = [str(rel) for rel in REQUIRED_REL_FILES if not (dest / rel).is_file()]
    if missing:
        print(f"Check failed at {dest}: missing {missing}", file=sys.stderr)
        return 1
    script = dest / "scripts" / "wb_supplement.py"
    if not run_doctor:
        print(f"Verified files present at {dest}")
        return 0
    proc = subprocess.run([sys.executable, str(script), "doctor"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode
    # Validate JSON structure cleanly
    data = json.loads(proc.stdout)
    print(f"Check OK at {dest}; workbuddy_home={data.get('workbuddy_home')}, westock_installed={data.get('westock', {}).get('installed')}")
    return 0


def uninstall_skill(dest: Path) -> int:
    if not dest.exists():
        print(f"Not installed at {dest} (nothing to remove)")
        return 0
    shutil.rmtree(dest)
    print(f"Removed {SKILL_NAME} from {dest}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install or manage the workbuddy-supplement skill.")
    parser.add_argument("--target", choices=(*TARGET_DIRS.keys(), "custom"), default="antigravity")
    parser.add_argument("--dest", help="Destination skill directory when --target custom is used")
    parser.add_argument("--check", action="store_true", help="Verify installation and run doctor")
    parser.add_argument("--uninstall", action="store_true", help="Remove installed skill directory")
    args = parser.parse_args()

    try:
        dest = resolve_dest(args.target, args.dest)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.uninstall:
        return uninstall_skill(dest)
    if args.check:
        return check_skill(dest)
    rc = install_skill(dest)
    if rc != 0:
        return rc
    return check_skill(dest)


if __name__ == "__main__":
    raise SystemExit(main())
