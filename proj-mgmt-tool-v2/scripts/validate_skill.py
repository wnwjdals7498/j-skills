#!/usr/bin/env python3
"""Validate the proj-mgmt-tool-v2 skill package."""

from __future__ import annotations

import argparse
import ast
import py_compile
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", nargs="?", default=str(ROOT))
    parser.add_argument("--run-tests", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.skill_dir).resolve()
    required = [
        "SKILL.md",
        "agents/openai.yaml",
        "scripts/pmt.py",
        "scripts/migrate_v1.py",
        "references/pmt-v2-contract.md",
        "references/migration-v1.md",
        "references/acceptance-tests.md",
    ]
    for rel in required:
        if not (root / rel).exists():
            fail(f"missing {rel}")

    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    if len(skill) > 4000:
        fail(f"SKILL.md too large: {len(skill)} chars")
    if not skill.startswith("---\n"):
        fail("SKILL.md missing frontmatter")
    unfinished_marker = "TO" + "DO:"
    scaffold_marker = "place" + "holder"
    if unfinished_marker in skill or scaffold_marker in skill.lower():
        fail("SKILL.md contains unfinished scaffold text")
    if not re.search(r"^name:\s*proj-mgmt-tool-v2\s*$", skill, re.M):
        fail("SKILL.md frontmatter name mismatch")
    description = re.search(r"^description:\s*(.+)$", skill, re.M)
    if not description or len(description.group(1).strip()) > 200:
        fail("SKILL.md description missing or too large")
    if "Codex" not in skill or "Claude Code" not in skill:
        fail("SKILL.md does not state cross-agent usage")
    if "hook" in skill:
        fail("SKILL.md contains forbidden hook text")

    pmt_path = root / "scripts/pmt.py"
    pmt = pmt_path.read_text(encoding="utf-8")
    if unfinished_marker in pmt or scaffold_marker in pmt.lower():
        fail("pmt.py contains unfinished scaffold text")
    if len(pmt.splitlines()) > 2000:
        fail(f"pmt.py too large: {len(pmt.splitlines())} lines")
    tree = ast.parse(pmt)
    command_count = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        if any(isinstance(target, ast.Name) and target.id == "command_specs" for target in node.targets):
            command_count = len(node.value.keys)
            break
    if command_count is None:
        fail("pmt.py command_specs not found")
    if command_count > 14:
        fail(f"too many subcommands: {command_count}")
    for rel in ("scripts/pmt.py", "scripts/migrate_v1.py", "scripts/validate_skill.py", "tests/test_pmt.py"):
        if (root / rel).exists():
            py_compile.compile(str(root / rel), doraise=True)

    print("PASS: skill package validates")
    if args.run_tests:
        proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=str(root))
        return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
