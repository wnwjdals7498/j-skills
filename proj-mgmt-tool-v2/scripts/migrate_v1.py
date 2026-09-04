#!/usr/bin/env python3
"""Migrate proj-mgmt-tool v1 data to the v2 layout."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
import pmt
from pmt import (
    Context,
    GENERATED,
    LIST_FILES,
    PmtError,
    as_list,
    doctor,
    ensure_dir,
    escape_cell,
    id_to_path,
    insert_table_row,
    list_template,
    parse_frontmatter,
    read_doc,
    render_frontmatter,
    replace_section,
    scan_docs,
    section_text,
    sync,
    timestamp,
    today,
    unique_path,
    worklog_path,
    write_doc,
)


def cmd_migrate(ctx: Context, args: argparse.Namespace) -> int:
    if args.migrate_kind != "v1":
        raise PmtError("only migrate v1 is supported", 2)
    project_dir = ctx.project_dir(args.slug or ctx.project)
    actions = collect_migration_actions(project_dir)
    if not args.apply:
        print("dry-run")
        for item in actions:
            print(item)
        return 0
    backup = project_dir / ".migration-v1-backup" / timestamp().replace(":", "")
    ensure_dir(backup.parent)
    shutil.copytree(project_dir, backup, ignore=shutil.ignore_patterns(".migration-v1-backup"))
    migration_warnings = apply_migration(ctx, project_dir)
    sync(ctx, project_dir)
    code = doctor(ctx, project_dir)
    for warning in migration_warnings:
        print(f"WARN migration: {warning}")
    print(f"backup: {backup}")
    return code


def collect_migration_actions(project_dir: Path) -> List[str]:
    actions = []
    for old, new in [("Information.md", "facts.md"), ("histories.md", "decisions.md")]:
        if (project_dir / old).exists():
            actions.append(f"merge {old} -> {new}")
    for old in ["requirements.md", "todos.md", "plans.md", "issues.md", "Bugs.md"]:
        if (project_dir / old).exists():
            actions.append(f"merge {old} -> backlog.md")
    for old in ["works.md", "classifications.md"]:
        if (project_dir / old).exists():
            actions.append(f"remove generated v1 index {old}")
    for path in project_dir.rglob("*.md"):
        if path.name in GENERATED:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "## 진행 메모" in text:
            actions.append(f"convert resume block {path}")
        if re.search(r"^kind:\s*(V|J|TE|HF)\s*$", text, re.M):
            actions.append(f"convert item kind {path}")
        if "list_refs:" in text:
            actions.append(f"rewrite list_refs {path}")
    if not actions:
        actions.append("no v1-only structures detected")
    return actions


def apply_migration(ctx: Context, project_dir: Path) -> List[str]:
    for name in LIST_FILES:
        if not (project_dir / name).exists():
            (project_dir / name).write_text(list_template(name[:-3], project_dir.name), encoding="utf-8")
    id_map: Dict[str, str] = {}
    id_map.update(merge_v1_list(project_dir, "Information.md", "facts.md", "F"))
    id_map.update(merge_v1_list(project_dir, "histories.md", "decisions.md", "D"))
    for old_name, kind in [
        ("requirements.md", "req"),
        ("todos.md", "todo"),
        ("plans.md", "plan"),
        ("issues.md", "issue"),
        ("Bugs.md", "bug"),
    ]:
        id_map.update(merge_v1_backlog(project_dir, old_name, kind))
    mapping = {"V": "view", "J": "job", "TE": "test", "HF": "hotfix"}
    for path in project_dir.rglob("*.md"):
        if ".migration-v1-backup" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        text = text.replace("## 진행 메모", "## 재개")
        for old, new in mapping.items():
            text = re.sub(rf"^kind:\s*{old}\s*$", f"kind: {new}", text, flags=re.M)
        fm, _body = parse_frontmatter(text)
        if fm.get("type") == "item" and "kind" not in fm:
            inferred = None
            for old, new in mapping.items():
                if re.search(rf"(^|-){old}\d*($|-)", path.stem):
                    inferred = new
                    break
            if inferred:
                text = text.replace("type: item\n", f"type: item\nkind: {inferred}\n", 1)
        text = re.sub(r"^[A-Za-z_]+:\s*null\s*\n", "", text, flags=re.M)
        text = rewrite_v1_refs(text, id_map)
        path.write_text(text, encoding="utf-8")
    ensure_missing_v1_parents(project_dir)
    warnings = absorb_v1_handoffs(ctx, project_dir)
    normalize_v1_worklogs(ctx, project_dir)
    for old in ["works.md", "classifications.md"]:
        path = project_dir / old
        if path.exists():
            path.unlink()
    return warnings


def ensure_missing_v1_parents(project_dir: Path) -> None:
    nodes = scan_docs(project_dir)
    for node in list(nodes.values()):
        parent = node.get("parent")
        if not parent or parent == project_dir.name or parent in nodes:
            continue
        parent_id = str(parent)
        try:
            parent_path = id_to_path(project_dir, parent_id)
        except PmtError:
            continue
        parts = parent_id.split("/")
        if len(parts) < 3:
            continue
        class_name = parts[1]
        title = parts[-1]
        data = {
            "type": "work",
            "id": parent_id,
            "parent": f"{project_dir.name}/{class_name}",
            "status": "In Progress",
            "updated": today(),
        }
        body = f"# {title}: migrated parent\n## Goal\n- migrated parent for v1 items\n## 결과\n-\n## 증거\n-\n"
        write_doc(parent_path, data, body)


def merge_v1_list(project_dir: Path, old_name: str, new_name: str, prefix: str) -> Dict[str, str]:
    src = project_dir / old_name
    if not src.exists():
        return {}
    dst = project_dir / new_name
    fm, body = read_doc(dst)
    source_fm, source_body = read_doc(src)
    id_map: Dict[str, str] = {}
    for row in extract_table_rows(source_body):
        cells = split_table_row(row)
        if not cells:
            continue
        old_id = cells[0]
        if old_id.lower() == "id":
            continue
        status = migration_status(prefix, canonical_status(cells[1] if len(cells) > 1 else source_fm.get("status")))
        created = canonical_date(cells[2] if len(cells) > 2 else source_fm.get("updated"))
        content = cells[-1] if len(cells) > 1 else row
        new_id = allocate_list_id(fm, prefix)
        id_map[old_id] = new_id
        escaped = escape_cell(f"[{old_id}] {content}")
        if prefix == "D":
            row = f"| {new_id} | {status} | {created} | {escaped} | {escaped} | |"
        else:
            row = f"| {new_id} | {status} | {created} | {escaped} |"
        body = insert_table_row(body, row)
    remainder = non_table_remainder(source_body)
    if remainder:
        new_id = allocate_list_id(fm, prefix)
        escaped = escape_cell(f"[{old_name}] {remainder}")
        if prefix == "D":
            row = f"| {new_id} | 승인 | {today()} | {escaped} | {escaped} | |"
        else:
            row = f"| {new_id} | Active | {today()} | {escaped} |"
        body = insert_table_row(body, row)
    if id_map or remainder:
        fm["updated"] = today()
        write_doc(dst, fm, body)
    src.unlink()
    return id_map


def merge_v1_backlog(project_dir: Path, old_name: str, kind: str) -> Dict[str, str]:
    src = project_dir / old_name
    if not src.exists():
        return {}
    dst = project_dir / "backlog.md"
    fm, body = read_doc(dst)
    source_fm, source_body = read_doc(src)
    id_map: Dict[str, str] = {}
    for row in extract_table_rows(source_body):
        cells = split_table_row(row)
        if not cells:
            continue
        old_id = cells[0]
        if old_id.lower() == "id":
            continue
        status = migration_status("B", canonical_status(cells[1] if len(cells) > 1 else source_fm.get("status")))
        created = canonical_date(cells[2] if len(cells) > 2 else source_fm.get("updated"))
        content = cells[-1] if len(cells) > 1 else row
        new_id = allocate_list_id(fm, "B")
        id_map[old_id] = new_id
        body = insert_table_row(body, f"| {new_id} | {kind} | {status} | {created} | {escape_cell(f'[{old_id}] {content}')} |")
    remainder = non_table_remainder(source_body, skip_section="점검 특징" if old_name == "Bugs.md" else None)
    if remainder:
        new_id = allocate_list_id(fm, "B")
        body = insert_table_row(body, f"| {new_id} | {kind} | Active | {today()} | {escape_cell(f'[{old_name}] {remainder}')} |")
    if old_name == "Bugs.md":
        bug_features = section_text(source_body, "점검 특징")
        if bug_features:
            current = section_text(body, "점검 특징")
            merged = (current + "\n" + bug_features).strip()
            body = replace_section(body, "점검 특징", merged)
    if id_map or remainder or old_name == "Bugs.md":
        fm["updated"] = today()
        write_doc(dst, fm, body)
    src.unlink()
    return id_map


def extract_table_rows(body: str) -> List[str]:
    rows = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = split_table_row(stripped)
        if not cells or cells[0].lower() == "id" or set(stripped.replace("|", "").strip()) <= {"-"}:
            continue
        rows.append(stripped)
    return rows


def split_table_row(row: str) -> List[str]:
    raw = row.strip().strip("|")
    cells: List[str] = []
    current = []
    escaped = False
    for char in raw:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            current.append(char)
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    cells.append("".join(current).strip())
    return cells


def non_table_remainder(body: str, skip_section: Optional[str] = None) -> str:
    if skip_section:
        pattern = re.compile(rf"^## {re.escape(skip_section)}\n.*?(?=^## |\Z)", re.M | re.S)
        body = pattern.sub("", body)
    kept = []
    in_table = False
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            in_table = True
            continue
        if in_table and not stripped:
            in_table = False
            continue
        if stripped.startswith("# ") and not kept:
            continue
        if stripped:
            kept.append(stripped)
    return " / ".join(kept)


def allocate_list_id(frontmatter: Dict[str, Any], prefix: str) -> str:
    number = int(frontmatter.get("next_id") or 1)
    frontmatter["next_id"] = number + 1
    return f"{prefix}{number}"


def canonical_status(value: Any) -> str:
    text = str(value or "Active").strip()
    known = {"done": "Done", "canceled": "Canceled", "cancelled": "Canceled", "in progress": "In Progress", "planned": "Planned", "active": "Active"}
    return known.get(text.lower(), text or "Active")


def migration_status(prefix: str, status: str) -> str:
    mappings = {
        "F": {"Done": "Closed", "Canceled": "Closed", "Planned": "Active", "In Progress": "Active"},
        "D": {"Done": "승인", "Canceled": "폐기", "Planned": "승인", "In Progress": "승인", "Active": "승인"},
        "B": {"Planned": "Active", "In Progress": "Active", "Canceled": "Dropped"},
    }
    return mappings[prefix].get(status, status)


def canonical_date(value: Any) -> str:
    text = str(value or "").strip()
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    return match.group(0) if match else today()


def rewrite_v1_refs(text: str, id_map: Dict[str, str]) -> str:
    if not id_map:
        return text
    fm, body = parse_frontmatter(text)
    refs = as_list(fm.get("list_refs"))
    if not refs:
        return text
    rewritten = []
    for ref in refs:
        new_id = id_map.get(ref.split("#")[-1])
        if not new_id:
            rewritten.append(ref)
        elif new_id.startswith("F"):
            rewritten.append(f"facts.md#{new_id}")
        elif new_id.startswith("D"):
            rewritten.append(f"decisions.md#{new_id}")
        else:
            rewritten.append(f"backlog.md#{new_id}")
    fm["list_refs"] = rewritten
    return render_frontmatter(fm, body)


def absorb_v1_handoffs(ctx: Context, project_dir: Path) -> List[str]:
    archive = project_dir / "resources" / "derived" / "handoff-archive"
    warnings: List[str] = []
    item_ids = sorted(
        (item_id for item_id, node in scan_docs(project_dir).items() if node.get("type") == "item"),
        key=len,
        reverse=True,
    )
    candidates: List[Path] = []
    candidates.extend(ctx.docs_root.glob("handoff-*.md"))
    if ctx.worklog_root.exists():
        candidates.extend(ctx.worklog_root.glob(f"{project_dir.name}__*-handoff.md"))
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        target = match_handoff_target(path, text, project_dir.name, item_ids)
        if not target:
            if project_dir.name in path.name or project_dir.name in text or path.parent == ctx.worklog_root:
                warnings.append(f"unresolved handoff preserved: {path}")
            continue
        item_path = id_to_path(project_dir, target)
        fm, body = read_doc(item_path)
        resume = section_text(body, "재개")
        imported = (
            f"- 갱신: {timestamp()} (session migration-v1)\n"
            f"- 한 것: v1 handoff imported from {path.name}\n"
            f"- 다음: imported handoff 검토\n"
            f"- 주의: 원문은 resources/derived/handoff-archive/{path.name}\n"
            "- 대기: 없음\n"
            "- 검증 못 한 것: handoff 자동 이관 내용 수동 검토\n\n"
            "### v1 handoff 원문\n"
            f"{text.strip()}"
        )
        body = replace_section(body, "재개", (resume + "\n\n" + imported).strip() if resume else imported)
        fm["updated"] = today()
        write_doc(item_path, fm, body)
        ensure_dir(archive)
        destination = unique_path(archive / path.name)
        shutil.move(str(path), str(destination))
    return warnings


def match_handoff_target(path: Path, text: str, slug: str, item_ids: List[str]) -> Optional[str]:
    matches = {item_id for item_id in item_ids if item_id in text}
    if len(matches) == 1:
        return next(iter(matches))
    name_match = re.match(rf"{re.escape(slug)}__(.+)__([A-Za-z0-9_.-]+)-handoff\.md$", path.name)
    if name_match:
        candidate = f"{slug}/{name_match.group(1)}/{name_match.group(2)}"
        if candidate in item_ids:
            return candidate
    return None


def normalize_v1_worklogs(ctx: Context, project_dir: Path) -> None:
    if not ctx.worklog_root.exists():
        return
    for path in list(ctx.worklog_root.glob(f"{project_dir.name}*.md")):
        if path.parent.name == "done" or path.name.endswith("-handoff.md"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        fm, body = parse_frontmatter(text)
        if not fm:
            inferred_id = infer_worklog_issue(project_dir.name, path, body)
            fm = {
                "title": inferred_id or path.stem,
                "status": "Active",
                "issues": [inferred_id] if inferred_id else [],
                "components": [inferred_id.split("/")[1]] if inferred_id and "/" in inferred_id else [],
                "created": today(),
            }
            text = render_frontmatter(fm, body)
        target_id = as_list(fm.get("issues"))[0] if as_list(fm.get("issues")) else infer_worklog_issue(project_dir.name, path, body)
        target_path = path
        if target_id and target_id.startswith(project_dir.name + "/"):
            target_path = worklog_path(ctx, target_id)
        if target_path != path:
            ensure_dir(target_path.parent)
            target_path = unique_path(target_path)
            path.write_text(text, encoding="utf-8")
            shutil.move(str(path), str(target_path))
        else:
            path.write_text(text, encoding="utf-8")


def infer_worklog_issue(slug: str, path: Path, body: str) -> Optional[str]:
    match = re.search(rf"{re.escape(slug)}/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", body)
    if match:
        return match.group(0)
    name_match = re.match(rf"{re.escape(slug)}__(.+)__([A-Za-z0-9_.-]+)\.md$", path.name)
    if name_match:
        return f"{slug}/{name_match.group(1)}/{name_match.group(2)}"
    return None


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate proj-mgmt-tool v1 data")
    parser.add_argument("--docs-root")
    parser.add_argument("--session")
    parser.add_argument("--project")
    parser.add_argument("slug", nargs="?")
    parser.add_argument("--apply", action="store_true")
    parser.set_defaults(migrate_kind="v1")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = parse_args(argv)
        ctx = pmt.Context(args)
        return cmd_migrate(ctx, args)
    except PmtError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
