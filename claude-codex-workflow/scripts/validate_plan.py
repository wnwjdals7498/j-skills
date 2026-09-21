#!/usr/bin/env python3
"""Validate a claude-codex-workflow Markdown plan without model calls."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


TASK_RE = re.compile(r"^\s*-\s+\[[ xX]\]\s+(T\d+):\s*(.+?)\s*$")
FIELD_RE = re.compile(r"^\s+-\s+([A-Za-z_가-힣]+):\s*(.*?)\s*$")
ALIASES = {"대상": "write_set", "검증": "verify"}
REQUIRED_FIELDS = {
    "wave",
    "depends_on",
    "model",
    "risk",
    "verification_tier",
    "write_set",
    "resource_set",
    "acceptance",
    "verify",
}
ALLOWED_MODELS = {"gpt-5.6-sol", "gpt-5.6-terra"}
ALLOWED_RISKS = {"low", "medium", "high"}
ALLOWED_TIERS = {"V1", "V2", "V3", "V4"}


@dataclass
class Task:
    task_id: str
    title: str
    line: int
    fields: dict[str, str]
    wave: int = 0
    dependencies: tuple[str, ...] = ()
    write_set: tuple[str, ...] = ()
    resource_set: tuple[str, ...] = ()


def strip_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"`":
        return value[1:-1].strip()
    return value


def parse_list(value: str) -> tuple[str, ...]:
    value = value.strip()
    if value == "[]" or not value:
        return ()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return tuple(strip_scalar(item) for item in value.split(",") if strip_scalar(item))


def parse_plan(text: str) -> tuple[list[Task], list[str]]:
    tasks: list[Task] = []
    errors: list[str] = []
    current: Task | None = None

    for line_number, line in enumerate(text.splitlines(), start=1):
        task_match = TASK_RE.match(line)
        if task_match:
            current = Task(task_match.group(1), task_match.group(2), line_number, {})
            tasks.append(current)
            continue

        if current is None:
            continue
        field_match = FIELD_RE.match(line)
        if not field_match:
            continue
        key = ALIASES.get(field_match.group(1), field_match.group(1))
        if key in current.fields:
            errors.append(f"line {line_number}: {current.task_id} duplicates field '{key}'")
        current.fields[key] = field_match.group(2).strip()

    if not tasks:
        return [], ["no tasks found"]
    return tasks, errors


def normalize_write_path(raw: str, task: Task, errors: list[str]) -> str | None:
    value = raw.replace("\\", "/").strip().removeprefix("./")
    if not value:
        return None
    if any(token in value for token in ("*", "?", "[", "]")):
        errors.append(f"line {task.line}: {task.task_id} write_set must not use globs: {raw}")
        return None
    if value.startswith("/") or re.match(r"^[A-Za-z]:/", value):
        errors.append(f"line {task.line}: {task.task_id} write_set must be repo-relative: {raw}")
        return None
    path = PurePosixPath(value)
    if ".." in path.parts:
        errors.append(f"line {task.line}: {task.task_id} write_set escapes the repo: {raw}")
        return None
    return path.as_posix().rstrip("/").casefold()


def paths_overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def validate_tasks(tasks: list[Task], initial_errors: list[str]) -> list[str]:
    errors = list(initial_errors)
    by_id: dict[str, Task] = {}

    for task in tasks:
        if task.task_id in by_id:
            errors.append(f"line {task.line}: duplicate task id {task.task_id}")
        by_id[task.task_id] = task

        missing = sorted(REQUIRED_FIELDS - task.fields.keys())
        if missing:
            errors.append(f"line {task.line}: {task.task_id} missing fields: {', '.join(missing)}")

        try:
            task.wave = int(strip_scalar(task.fields.get("wave", "")))
            if task.wave < 1:
                raise ValueError
        except ValueError:
            errors.append(f"line {task.line}: {task.task_id} wave must be a positive integer")

        task.dependencies = parse_list(task.fields.get("depends_on", ""))
        task.write_set = tuple(
            normalized
            for item in parse_list(task.fields.get("write_set", ""))
            if (normalized := normalize_write_path(item, task, errors)) is not None
        )
        task.resource_set = tuple(item.casefold() for item in parse_list(task.fields.get("resource_set", "")))

        if not task.write_set:
            errors.append(f"line {task.line}: {task.task_id} write_set must not be empty")
        model = strip_scalar(task.fields.get("model", ""))
        if model not in ALLOWED_MODELS:
            errors.append(f"line {task.line}: {task.task_id} unsupported model '{model}'")
        risk = strip_scalar(task.fields.get("risk", "")).casefold()
        if risk not in ALLOWED_RISKS:
            errors.append(f"line {task.line}: {task.task_id} risk must be low, medium, or high")
        tier = strip_scalar(task.fields.get("verification_tier", "")).upper()
        if tier not in ALLOWED_TIERS:
            errors.append(f"line {task.line}: {task.task_id} verification_tier must be V1-V4")
        if not strip_scalar(task.fields.get("acceptance", "")):
            errors.append(f"line {task.line}: {task.task_id} acceptance must not be empty")
        if not strip_scalar(task.fields.get("verify", "")):
            errors.append(f"line {task.line}: {task.task_id} verify must not be empty")

    for task in tasks:
        for dependency in task.dependencies:
            if dependency not in by_id:
                errors.append(f"line {task.line}: {task.task_id} has unknown dependency {dependency}")
            elif dependency == task.task_id:
                errors.append(f"line {task.line}: {task.task_id} depends on itself")
            elif by_id[dependency].wave >= task.wave:
                errors.append(
                    f"line {task.line}: {task.task_id} dependency {dependency} must be in an earlier wave"
                )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, chain: tuple[str, ...]) -> None:
        if task_id in visiting:
            errors.append("dependency cycle: " + " -> ".join((*chain, task_id)))
            return
        if task_id in visited or task_id not in by_id:
            return
        visiting.add(task_id)
        for dependency in by_id[task_id].dependencies:
            visit(dependency, (*chain, task_id))
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in by_id:
        visit(task_id, ())

    for index, left in enumerate(tasks):
        for right in tasks[index + 1 :]:
            if left.wave != right.wave:
                continue
            for left_path in left.write_set:
                for right_path in right.write_set:
                    if paths_overlap(left_path, right_path):
                        errors.append(
                            f"wave {left.wave}: {left.task_id} and {right.task_id} overlap write_set at "
                            f"'{left_path}' / '{right_path}'"
                        )
            shared_resources = sorted(set(left.resource_set) & set(right.resource_set))
            if shared_resources:
                errors.append(
                    f"wave {left.wave}: {left.task_id} and {right.task_id} share resources: "
                    + ", ".join(shared_resources)
                )

    return errors


def validate_text(text: str) -> tuple[list[Task], list[str]]:
    tasks, parse_errors = parse_plan(text)
    return tasks, validate_tasks(tasks, parse_errors) if tasks else parse_errors


def self_test() -> int:
    valid = """
- [ ] T1: core
  - wave: 1
  - depends_on: []
  - model: gpt-5.6-sol
  - risk: low
  - verification_tier: V1
  - write_set: [src/core.ts]
  - resource_set: []
  - acceptance: core works
  - verify: `test core` -> pass
- [ ] T2: api
  - wave: 2
  - depends_on: [T1]
  - model: gpt-5.6-terra
  - risk: high
  - verification_tier: V4
  - write_set: [src/api.ts]
  - resource_set: [test-db]
  - acceptance: api works
  - verify: `test api` -> pass
"""
    invalid = """
- [ ] T1: first
  - wave: 1
  - depends_on: []
  - model: gpt-5.6-sol
  - risk: low
  - verification_tier: V1
  - write_set: [src]
  - resource_set: [test-db]
  - acceptance: done
  - verify: test
- [ ] T2: second
  - wave: 1
  - depends_on: []
  - model: gpt-5.6-sol
  - risk: low
  - verification_tier: V1
  - write_set: [src/api.ts]
  - resource_set: [test-db]
  - acceptance: done
  - verify: test
"""
    _, valid_errors = validate_text(valid)
    _, invalid_errors = validate_text(invalid)
    if valid_errors or not any("overlap write_set" in error for error in invalid_errors):
        print("self-test failed", file=sys.stderr)
        for error in valid_errors + invalid_errors:
            print(error, file=sys.stderr)
        return 1
    print("self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", nargs="?", type=Path, help="Markdown plan file")
    parser.add_argument("--self-test", action="store_true", help="run built-in checks")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.plan is None:
        parser.error("plan is required unless --self-test is used")

    try:
        text = args.plan.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"cannot read plan: {exc}", file=sys.stderr)
        return 2

    tasks, errors = validate_text(text)
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        return 1

    waves = len({task.wave for task in tasks})
    print(f"VALID plan: {len(tasks)} tasks, {waves} waves")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
