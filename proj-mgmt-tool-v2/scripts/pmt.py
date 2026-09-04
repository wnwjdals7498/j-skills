#!/usr/bin/env python3
"""Local-first Project Management Tool v2 CLI.

The engine is intentionally dependency-free so the same skill directory can be
linked from Codex and Claude Code.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


LIST_FILES = ("facts.md", "decisions.md", "backlog.md")
GENERATED = {"RESUME.md"}
SKIP_DIRS = {"archive", "canceled", "resources", ".locks", ".migration-v1-backup", "decisions"}
STALE_MINUTES = 30
WARN_MINUTES = 20


class PmtError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def now_local() -> dt.datetime:
    return dt.datetime.now().replace(microsecond=0)


def today() -> str:
    return dt.date.today().isoformat()


def timestamp() -> str:
    return now_local().isoformat(timespec="minutes")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def slug_safe(text: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip()).strip("-")
    return safe or "default"


def lock_name(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    return f"{slug_safe(value.replace('/', '__').replace(chr(92), '__'))}-{digest}.lock"


def parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if value in {"", "null", "None", "~"}:
        return None
    if value in {"[]", "{}"}:
        return [] if value == "[]" else {}
    if value.startswith("[") and value.endswith("]"):
        try:
            return ast.literal_eval(value)
        except Exception:
            body = value[1:-1].strip()
            return [x.strip().strip("\"'") for x in body.split(",") if x.strip()]
    if value in {"true", "false"}:
        return value == "true"
    return value.strip("\"'")


def format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, list):
        return "[" + ", ".join(str(x) for x in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    block = text[4:end].strip("\n")
    body = text[text.find("\n", end + 1) + 1 :]
    data: Dict[str, Any] = {}
    current: Optional[str] = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current:
            data.setdefault(current, []).append(parse_scalar(line[4:]))
            continue
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        current = key.strip()
        data[current] = parse_scalar(raw)
    return data, body


def render_frontmatter(data: Dict[str, Any], body: str) -> str:
    lines = ["---"]
    order = [
        "type",
        "kind",
        "id",
        "parent",
        "status",
        "supersedes",
        "created",
        "decider",
        "updated",
        "labels",
        "repositories",
        "next_id",
        "verify",
        "blocked_by",
        "linear_id",
    ]
    emitted = set()
    for key in order:
        if key in data and data[key] is not None:
            lines.append(f"{key}: {format_scalar(data[key])}")
            emitted.add(key)
    for key in sorted(k for k in data if k not in emitted and data[k] is not None):
        lines.append(f"{key}: {format_scalar(data[key])}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body.lstrip("\n")


def read_doc(path: Path) -> Tuple[Dict[str, Any], str]:
    if not path.exists():
        raise PmtError(f"missing file: {path}")
    return parse_frontmatter(path.read_text(encoding="utf-8"))


def write_doc(path: Path, data: Dict[str, Any], body: str) -> None:
    ensure_dir(path.parent)
    path.write_text(render_frontmatter(data, body), encoding="utf-8")


def replace_section(body: str, heading: str, replacement: str) -> str:
    pattern = re.compile(rf"(^## {re.escape(heading)}\n)(.*?)(?=^## |\Z)", re.M | re.S)
    repl = f"## {heading}\n{replacement.rstrip()}\n"
    if pattern.search(body):
        return pattern.sub(repl, body, count=1)
    if not body.endswith("\n"):
        body += "\n"
    return body + "\n" + repl


def section_text(body: str, heading: str) -> str:
    pattern = re.compile(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", re.M | re.S)
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def title_from_body(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "(untitled)"


def derive_session() -> Tuple[str, bool]:
    env = os.environ.get("PMT_SESSION")
    if env:
        return env, True
    try:
        ppid = os.getppid()
        stat = Path(f"/proc/{ppid}/stat").read_text(encoding="utf-8")
        rest = stat[stat.rindex(")") + 2 :].split()
        return f"pid-{rest[1]}", True
    except Exception:
        return f"session-{os.getppid()}", False


class Context:
    def __init__(self, args: argparse.Namespace) -> None:
        docs_arg = getattr(args, "docs_root", None) or os.environ.get("PMT_DOCS_ROOT")
        self.docs_root = Path(docs_arg).expanduser().resolve() if docs_arg else (Path.home() / "docs").resolve()
        self.projects_root = self.docs_root / "projects"
        self.worklog_root = self.docs_root / "worklog"
        self.times_root = self.docs_root / "times"
        session = getattr(args, "session", None)
        if session:
            self.session, self.session_stable = session, True
        else:
            self.session, self.session_stable = derive_session()
        self.session_warning_emitted = False
        self.project = getattr(args, "project", None) or self.detect_project()

    def detect_project(self) -> Optional[str]:
        try:
            cwd = Path.cwd().resolve()
            root = (self.docs_root / "projects").resolve()
        except Exception as exc:
            print(f"경고: {self.docs_root / 'projects'} {exc}", file=sys.stderr)
            return None
        try:
            rel = cwd.relative_to(root)
        except ValueError:
            return None
        return rel.parts[0] if rel.parts else None

    def require_project(self) -> str:
        if not self.project:
            raise PmtError("project is required; pass --project or run inside a project directory", 2)
        return self.project

    def project_dir(self, slug: Optional[str] = None) -> Path:
        return self.projects_root / (slug or self.require_project())


def id_to_path(project_dir: Path, item_id: str) -> Path:
    slug = project_dir.name
    if item_id == slug:
        return project_dir / "project.md"
    if not item_id.startswith(slug + "/"):
        raise PmtError(f"id is outside project {slug}: {item_id}", 2)
    parts = item_id.split("/")[1:]
    if len(parts) == 1:
        return project_dir / parts[0] / "index.md"
    return project_dir.joinpath(*parts).with_suffix(".md")


def scan_docs(project_dir: Path) -> Dict[str, Dict[str, Any]]:
    nodes: Dict[str, Dict[str, Any]] = {}
    for path in project_dir.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.relative_to(project_dir).parts):
            continue
        if path.name in GENERATED or path.name in LIST_FILES:
            continue
        try:
            fm, body = read_doc(path)
        except Exception as exc:
            print(f"경고: {path} {exc}", file=sys.stderr)
            continue
        item_id = fm.get("id")
        if not item_id:
            continue
        nodes[str(item_id)] = {
            "path": str(path),
            "body": body,
            "frontmatter": fm,
            "id": fm.get("id"),
            "type": fm.get("type"),
            "kind": fm.get("kind"),
            "status": fm.get("status"),
            "parent": fm.get("parent"),
            "title": title_from_body(body),
            "blocked_by": as_list(fm.get("blocked_by")),
            "updated": fm.get("updated"),
            "resume": section_text(body, "재개"),
        }
    return nodes


def as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value if str(x)]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def project_indexes(ctx: Context) -> None:
    ensure_dir(ctx.projects_root)
    rows = ["# Projects", "| slug | status | updated | labels |", "|---|---|---|---|"]
    for project in sorted(p for p in ctx.projects_root.iterdir() if p.is_dir()):
        path = project / "project.md"
        if not path.exists():
            continue
        fm, _ = read_doc(path)
        rows.append(
            f"| {project.name} | {fm.get('status', '')} | {fm.get('updated', '')} | {', '.join(as_list(fm.get('labels')))} |"
        )
    (ctx.projects_root / "projects.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def list_template(kind: str, slug: str) -> str:
    if kind == "facts":
        head = "| ID | 상태 | 생성 | 내용 |\n|---|---|---|---|\n"
    elif kind == "decisions":
        head = "| ID | 상태 | 생성 | 제목 | 내용 | 대체 |\n|---|---|---|---|---|---|\n"
    else:
        head = "| ID | kind | 상태 | 생성 | 내용 |\n|---|---|---|---|---|\n\n## 점검 특징\n-\n"
    return (
        "---\n"
        f"type: list\nid: {slug}/{kind}\nparent: {slug}\nstatus: Active\nupdated: {today()}\nnext_id: 1\n"
        "---\n"
        f"# {kind.title()}\n{head}"
    )


def cmd_new(ctx: Context, args: argparse.Namespace) -> int:
    slug = slug_safe(args.slug)
    ctx.project = slug
    project_dir = ctx.project_dir(slug)
    if project_dir.exists():
        raise PmtError(f"project already exists: {slug}", 1)
    ensure_dir(project_dir / "_default")
    ensure_dir(project_dir / "archive")
    ensure_dir(project_dir / ".locks")
    for sub in ("originals", "derived", "evidence"):
        ensure_dir(project_dir / "resources" / sub)
    labels = "[" + ", ".join(args.label or []) + "]"
    body = (
        f"---\ntype: project\nid: {slug}\nstatus: Planned\nupdated: {today()}\n"
        f"labels: {labels}\nrepositories: []\n---\n"
        f"# {slug}\n## Goal\n- {args.goal}\n## Non-Goal\n-\n## 결과\n-\n"
    )
    (project_dir / "project.md").write_text(body, encoding="utf-8")
    for name in LIST_FILES:
        (project_dir / name).write_text(list_template(name[:-3], slug), encoding="utf-8")
    sync(ctx, project_dir)
    project_indexes(ctx)
    print(f"created {slug}")
    return 0


def next_work_id(project_dir: Path, class_name: str) -> str:
    class_dir = project_dir / class_name
    ensure_dir(class_dir)
    nums = []
    for path in class_dir.glob("Work*.md"):
        match = re.fullmatch(r"Work(\d+)", path.stem)
        if match:
            nums.append(int(match.group(1)))
    return f"Work{max(nums or [0]) + 1}"


def next_item_id(project_dir: Path, parent_id: str) -> str:
    parent_path = id_to_path(project_dir, parent_id)
    prefix = parent_path.stem
    class_dir = parent_path.parent
    nums = []
    for path in class_dir.glob(f"{prefix}-*.md"):
        tail = path.stem[len(prefix) + 1 :]
        if re.fullmatch(r"\d+", tail):
            nums.append(int(tail))
    return f"{prefix}-{max(nums or [0]) + 1}"


def cmd_add(ctx: Context, args: argparse.Namespace) -> int:
    project_dir = ctx.project_dir()
    if args.add_kind == "work":
        class_name = args.class_name or "_default"
        reserved = {"archive", "canceled", "resources", "decisions", ".locks"}
        if class_name in reserved or class_name.startswith(".") or (class_name.startswith("_") and class_name != "_default"):
            raise PmtError(f"reserved classification: {class_name}", 2)
        name = next_work_id(project_dir, class_name)
        item_id = f"{ctx.require_project()}/{class_name}/{name}"
        parent = f"{ctx.require_project()}/{class_name}"
        body = (
            f"# {name}: {args.title}\n## Goal\n- {args.goal or args.title}\n"
            "## 결과\n-\n## 증거\n-\n"
        )
        write_doc(id_to_path(project_dir, item_id), {"type": "work", "id": item_id, "parent": parent, "status": "Planned", "updated": today()}, body)
        print(item_id)
        return 0
    if args.add_kind == "item":
        parent_id = args.parent_id
        parent_path = id_to_path(project_dir, parent_id)
        if not parent_path.exists():
            raise PmtError(f"missing parent: {parent_id}", 1)
        fm, _ = read_doc(parent_path)
        if fm.get("kind") == "test":
            raise PmtError("test items cannot have children", 2)
        name = next_item_id(project_dir, parent_id)
        if len(name.split("-")) - 1 > 3:
            raise PmtError("item depth cannot exceed 3 below Work", 2)
        class_name = parent_id.split("/")[1]
        item_id = f"{ctx.require_project()}/{class_name}/{name}"
        body = (
            f"# [{args.kind}] {args.title}\n## 기본 내용\n-\n## 범위\n- [ ]\n"
            "## 완료 기준\n-\n## 재개\n<start 이후 note가 채움>\n## 결과\n-\n## 증거\n-\n"
        )
        data = {"type": "item", "kind": args.kind, "id": item_id, "parent": parent_id, "status": "Planned", "blocked_by": [], "base_commit": "-", "updated": today()}
        if args.verify:
            data["verify"] = args.verify
        write_doc(id_to_path(project_dir, item_id), data, body)
        print(item_id)
        return 0
    return add_list_row(ctx, args)


def add_list_row(ctx: Context, args: argparse.Namespace) -> int:
    project_dir = ctx.project_dir()
    mapping = {"fact": ("facts.md", "F"), "backlog": ("backlog.md", "B")}
    file_name, prefix = mapping[args.add_kind]
    path = project_dir / file_name
    lock_id = f"__list-{file_name}"
    if not acquire_lock(project_lock_base(project_dir), lock_id, ctx.session):
        raise PmtError(f"list lock busy: {file_name}", 1)
    try:
        fm, body = read_doc(path)
        num = int(fm.get("next_id") or 1)
        row_id = f"{prefix}{num}"
        fm["next_id"] = num + 1
        fm["updated"] = today()
        if args.add_kind == "fact":
            text = args.text + (f" 참조: {args.ref}" if args.ref else "")
            row = f"| {row_id} | Active | {today()} | {escape_cell(text)} |"
        else:
            row = f"| {row_id} | {args.kind} | Active | {today()} | {escape_cell(args.text)} |"
        body = insert_table_row(body, row)
        write_doc(path, fm, body)
        print(row_id)
        return 0
    finally:
        release_lock(project_lock_base(project_dir), lock_id, ctx.session)


def escape_cell(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def insert_table_row(body: str, row: str) -> str:
    header = table_header(body)
    cells = split_table_row(row)
    if header == ["ID", "상태", "생성", "내용"] and len(cells) == 4:
        cells[1] = {"Done": "Closed", "Canceled": "Closed", "Planned": "Active", "In Progress": "Active"}.get(cells[1], cells[1])
        row = join_table_row(cells)
    elif header == ["ID", "상태", "생성", "제목", "내용", "대체"] and len(cells) == 4:
        cells[1] = {"Done": "승인", "Canceled": "폐기", "Planned": "승인", "In Progress": "승인", "Active": "승인"}.get(cells[1], cells[1])
        cells = [cells[0], cells[1], cells[2], cells[3], cells[3], ""]
        row = join_table_row(cells)
    elif header == ["ID", "kind", "상태", "생성", "내용"] and len(cells) == 5:
        cells[2] = {"Planned": "Active", "In Progress": "Active", "Canceled": "Dropped"}.get(cells[2], cells[2])
        row = join_table_row(cells)
    lines = body.splitlines()
    insert_at = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("## "):
            insert_at = i
            break
    lines.insert(insert_at, row)
    return "\n".join(lines) + "\n"


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


def join_table_row(cells: Sequence[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def table_header(body: str) -> List[str]:
    return next((split_table_row(line) for line in body.splitlines() if line.strip().startswith("| ID ")), [])


def find_table_row(body: str, row_id: str) -> Optional[List[str]]:
    return next((split_table_row(line) for line in body.splitlines() if line.strip().startswith(f"| {row_id} |")), None)


def replace_table_row(body: str, row_id: str, cells: Sequence[str]) -> str:
    lines = body.splitlines()
    for index, line in enumerate(lines):
        current = split_table_row(line) if line.strip().startswith("|") else []
        if current and current[0] == row_id:
            lines[index] = join_table_row(cells)
            return "\n".join(lines) + "\n"
    return body


def sync_decision_file_status(project_dir: Path, decision_id: str, status: str) -> None:
    path = project_dir / "decisions" / f"{decision_id}.md"
    if not path.exists():
        return
    fm, body = read_doc(path)
    fm["status"] = status
    write_doc(path, fm, body)


def cmd_decide(ctx: Context, args: argparse.Namespace) -> int:
    project_dir = ctx.project_dir()
    path = project_dir / "decisions.md"
    lock_id = "__list-decisions.md"
    if not acquire_lock(project_lock_base(project_dir), lock_id, ctx.session):
        raise PmtError("list lock busy: decisions.md", 1)
    try:
        fm, body = read_doc(path)
        status_index = table_header(body).index("상태")
        previous = find_table_row(body, args.supersedes) if args.supersedes else None
        if args.supersedes and (not re.fullmatch(r"D\d+", args.supersedes) or not previous or previous[status_index] != "승인"):
            raise PmtError(f"supersedes target must be approved: {args.supersedes}", 2)
        number = int(fm.get("next_id") or 1)
        decision_id = f"D{number}"
        values = (("문맥", args.context), ("결정", args.decision), ("대안", args.alt), ("결과", args.result))
        content = " / ".join(f"{name}: {value}" for name, value in values if value)
        if len(content) > 300:
            decision_body = "\n".join([f"# {args.title}"] + [f"## {name}\n{value or '-'}" for name, value in values]) + "\n"
            write_doc(project_dir / "decisions" / f"{decision_id}.md", {"type": "decision", "id": f"{project_dir.name}/{decision_id}", "status": "승인", "supersedes": args.supersedes, "created": today(), "decider": args.decider or ctx.session}, decision_body)
            summary = re.split(r"(?<=[.!?])\s+|\n+", args.decision.strip(), maxsplit=1)[0]
            content = f"결정: {summary} (전문: decisions/{decision_id}.md)"
        row = [decision_id, "승인", today(), escape_cell(args.title), escape_cell(content), args.supersedes or ""]
        body = insert_table_row(body, join_table_row(row))
        if previous:
            previous[status_index] = "대체"
            body = replace_table_row(body, args.supersedes, previous)
        fm.update({"next_id": number + 1, "updated": today()})
        write_doc(path, fm, body)
        if args.supersedes:
            sync_decision_file_status(project_dir, args.supersedes, "대체")
        print(decision_id)
        return 0
    finally:
        release_lock(project_lock_base(project_dir), lock_id, ctx.session)


def set_list_status(ctx: Context, args: argparse.Namespace, prefix: str) -> int:
    file_name, transitions = {"F": ("facts.md", {"Active": {"Closed"}}), "B": ("backlog.md", {"Active": {"Done", "Dropped"}}), "D": ("decisions.md", {"승인": {"폐기"}})}[prefix]
    project_dir = ctx.project_dir()
    path = project_dir / file_name
    lock_id = f"__list-{file_name}"
    if not acquire_lock(project_lock_base(project_dir), lock_id, ctx.session):
        raise PmtError(f"list lock busy: {file_name}", 1)
    try:
        fm, body = read_doc(path)
        header = table_header(body)
        cells = find_table_row(body, args.target)
        if not cells:
            raise PmtError(f"missing list id: {args.target}", 2)
        status_index, content_index = header.index("상태"), header.index("내용")
        current = cells[status_index]
        if args.status not in transitions.get(current, set()):
            raise PmtError(f"invalid transition: {current} -> {args.status}", 2)
        cells[status_index] = args.status
        if args.why:
            cells[content_index] += f" / 사유: {escape_cell(args.why)}"
        body = replace_table_row(body, args.target, cells)
        fm["updated"] = today()
        write_doc(path, fm, body)
        if prefix == "D":
            sync_decision_file_status(project_dir, args.target, args.status)
        print(args.target)
        return 0
    finally:
        release_lock(project_lock_base(project_dir), lock_id, ctx.session)


def cmd_set(ctx: Context, args: argparse.Namespace) -> int:
    relation_modes = sum(value is not None for value in (args.blocked_by, args.unblock))
    if args.status is not None and relation_modes:
        raise PmtError("--status cannot be combined with --blocked-by or --unblock", 2)
    match = re.fullmatch(r"([FDB])\d+", args.target)
    if match:
        if args.status is None or relation_modes:
            raise PmtError("list status update requires --status", 2)
        return set_list_status(ctx, args, match.group(1))
    if args.status is not None or args.why is not None or relation_modes != 1:
        raise PmtError("item relation update requires exactly one of --blocked-by or --unblock", 2)
    project_dir = ctx.project_dir()
    path = id_to_path(project_dir, args.target)
    fm, body = read_doc(path)
    if fm.get("type") != "item":
        raise PmtError(f"target is not an item: {args.target}", 2)
    relation = args.blocked_by if args.blocked_by is not None else args.unblock
    if not relation.startswith("ext:"):
        relation_path = id_to_path(project_dir, relation)
        if not relation_path.exists():
            raise PmtError(f"missing blocked_by item: {relation}", 2)
        relation_fm, _ = read_doc(relation_path)
        if relation_fm.get("type") != "item":
            raise PmtError(f"blocked_by target is not an item: {relation}", 2)
    blocked_by = as_list(fm.get("blocked_by"))
    if args.blocked_by is not None and relation not in blocked_by:
        blocked_by.append(relation)
    elif args.unblock is not None:
        blocked_by = [value for value in blocked_by if value != relation]
    fm.update({"blocked_by": blocked_by, "updated": today()})
    write_doc(path, fm, body)
    print(args.target)
    return 0


def acquire_lock(base: Path, item_id: str, session: str) -> bool:
    ensure_dir(base)
    target = base / lock_name(item_id)
    meta = {"id": item_id, "session": session, "created": timestamp(), "heartbeat": timestamp()}
    try:
        target.mkdir()
        (target / "lock.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except FileExistsError:
        return False


def acquire_lock_wait(base: Path, item_id: str, session: str, timeout_seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while True:
        if acquire_lock(base, item_id, session):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.02)


def lock_meta(base: Path, item_id: str) -> Optional[Dict[str, Any]]:
    path = base / lock_name(item_id) / "lock.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def lock_owned(base: Path, item_id: str, session: str) -> bool:
    meta = lock_meta(base, item_id)
    return bool(meta and meta.get("session") == session)


def require_lock_owner(base: Path, item_id: str, ctx: Context) -> None:
    if not ctx.session_stable:
        if not ctx.session_warning_emitted:
            print("주의: 세션 식별 불안정 — PMT_SESSION 설정 권장", file=sys.stderr)
            ctx.session_warning_emitted = True
        if (base / lock_name(item_id)).exists():
            return
    if not lock_owned(base, item_id, ctx.session):
        raise PmtError(f"lock not owned by session: {item_id}", 1)


def update_lock(base: Path, item_id: str, session: str) -> bool:
    path = base / lock_name(item_id) / "lock.json"
    meta = lock_meta(base, item_id)
    if not meta or meta.get("session") != session:
        return False
    meta["heartbeat"] = timestamp()
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def release_lock(base: Path, item_id: str, session: Optional[str] = None) -> bool:
    path = base / lock_name(item_id)
    if not path.exists():
        return False
    meta_path = path / "lock.json"
    if session and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("session") != session:
            return False
    shutil.rmtree(path)
    return True


def read_locks(base: Path, stale_minutes: int = STALE_MINUTES) -> List[Dict[str, Any]]:
    rows = []
    if not base.exists():
        return rows
    for lock_dir in base.glob("*.lock"):
        meta_path = lock_dir / "lock.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        meta["path"] = str(lock_dir)
        meta["stale"] = lock_age_minutes(meta) >= stale_minutes
        rows.append(meta)
    return rows


def parse_time(value: str) -> Optional[dt.datetime]:
    try:
        return dt.datetime.fromisoformat(value)
    except Exception:
        return None


def lock_age_minutes(meta: Dict[str, Any]) -> float:
    heartbeat = parse_time(str(meta.get("heartbeat", "")))
    if not heartbeat:
        return 0.0
    return (now_local() - heartbeat).total_seconds() / 60


def resume_age_minutes(body: str) -> Optional[float]:
    match = re.search(r"^- 갱신:\s*([0-9T:+-]+)", body, re.M)
    if not match:
        return None
    when = parse_time(match.group(1))
    if not when:
        return None
    return (now_local() - when).total_seconds() / 60


def criteria_hash(body: str) -> str:
    criteria = section_text(body, "완료 기준").strip()
    return hashlib.sha1(criteria.encode()).hexdigest()[:8] if criteria.strip("- \t\n") else ""


def git_head(cwd: Optional[Path]) -> str:
    if cwd is None: return "-"
    try:
        proc = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--short", "HEAD"], text=True, capture_output=True, timeout=10)
        return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else "-"
    except Exception:
        return "-"


def verify_cwd(ctx: Context, project_dir: Path, arg: Optional[str]) -> Path:
    value = arg or next(iter(as_list(read_doc(project_dir / "project.md")[0].get("repositories"))), None)
    return Path(value).expanduser().resolve() if value else Path.cwd()


def verification_rows(body: str) -> List[List[str]]:
    return [split_table_row(line) for line in section_text(body, "검증").splitlines() if line.startswith("| ") and not line.startswith("| at ") and not line.startswith("|---")]


def append_verification(body: str, row: str) -> str:
    current = section_text(body, "검증")
    if current: return replace_section(body, "검증", f"{current}\n{row}")
    block = f"## 검증\n| at | commit | criteria | command | exit | limits |\n|---|---|---|---|---|---|\n{row}\n"
    return body.replace("## 결과\n", block + "## 결과\n", 1) if "## 결과\n" in body else body.rstrip() + "\n\n" + block


def project_lock_base(project_dir: Path) -> Path:
    return project_dir / ".locks"


def repo_lock_base(ctx: Context) -> Path:
    return ctx.docs_root / ".repo-locks"


def worklog_path(ctx: Context, item_id: str) -> Path:
    parts = item_id.split("/")
    slug = parts[0]
    class_name = parts[1] if len(parts) > 1 else "_default"
    name = parts[-1]
    return ctx.worklog_root / f"{slug}__{class_name}__{name}.md"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for number in range(1, 1000):
        candidate = path.with_name(f"{stem}-{number}{suffix}")
        if not candidate.exists():
            return candidate
    raise PmtError(f"cannot allocate archive path for {path}", 1)


def append_worklog(ctx: Context, item_id: str, heading: str, lines: Sequence[str]) -> None:
    ensure_dir(ctx.worklog_root)
    path = worklog_path(ctx, item_id)
    if not path.exists():
        text = (
            "---\n"
            f"title: {item_id}\nstatus: Active\nissues: [{item_id}]\ncomponents: [{item_id.split('/')[1] if '/' in item_id else '_default'}]\n"
            f"created: {today()}\n---\n"
            f"# {item_id}\n"
        )
        path.write_text(text, encoding="utf-8")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"\n## {heading} {timestamp()}\n")
        for line in lines:
            handle.write(f"- {line}\n")


def promote_parents(project_dir: Path, item_id: str) -> None:
    project_path = project_dir / "project.md"
    project_fm, project_body = read_doc(project_path)
    if project_fm.get("status") == "Planned":
        project_fm["status"] = "In Progress"
        project_fm["updated"] = today()
        write_doc(project_path, project_fm, project_body)
    current = item_id
    while True:
        path = id_to_path(project_dir, current)
        fm, _ = read_doc(path)
        parent = fm.get("parent")
        if not parent or parent == project_dir.name:
            return
        try:
            parent_path = id_to_path(project_dir, str(parent))
            pfm, pbody = read_doc(parent_path)
        except PmtError:
            return
        if pfm.get("status") == "Planned":
            pfm["status"] = "In Progress"
            pfm["updated"] = today()
            write_doc(parent_path, pfm, pbody)
        current = str(parent)


def cmd_start(ctx: Context, args: argparse.Namespace) -> int:
    project_dir = ctx.project_dir()
    item_id = args.item_id
    lock_base = project_lock_base(project_dir)
    path = id_to_path(project_dir, item_id)
    if not path.exists():
        raise PmtError(f"missing item: {item_id}", 1)
    fm, body = read_doc(path)
    if fm.get("status") in {"Done", "Canceled"}:
        raise PmtError(f"cannot start terminal item {item_id}: {fm.get('status')}", 2)
    if args.delegate:
        missing = []
        if not section_text(body, "범위").replace("- [ ]", "").strip():
            missing.append("범위")
        if not section_text(body, "완료 기준").strip("- \n"):
            missing.append("완료 기준")
        if not fm.get("verify"):
            missing.append("verify")
        if missing:
            raise PmtError("delegate gate failed: " + ", ".join(missing), 2)
    stale_owned = sorted(
        str(row.get("id"))
        for row in read_locks(lock_base)
        if row.get("session") == ctx.session
        and not str(row.get("id", "")).startswith("__")
        and row.get("id") != item_id
        and lock_age_minutes(row) >= STALE_MINUTES
    )
    if stale_owned:
        stale_id = stale_owned[0]
        raise PmtError(
            f"먼저 pmt note {stale_id} --did --next 또는 pmt end {stale_id} --pause",
            2,
        )
    acquired = acquire_lock(lock_base, item_id, ctx.session)
    if not acquired:
        existing = lock_meta(lock_base, item_id)
        if existing and lock_age_minutes(existing) >= STALE_MINUTES:
            if reap_lock(ctx, lock_base, item_id, project_scoped=True):
                fm, body = read_doc(path)
                acquired = acquire_lock(lock_base, item_id, ctx.session)
    if not acquired:
        print(f"lock busy: {item_id}", file=sys.stderr)
        return 1
    backup_docs = {
        p: p.read_text(encoding="utf-8")
        for p in project_dir.rglob("*.md")
        if not any(part in SKIP_DIRS for part in p.relative_to(project_dir).parts)
    }
    log_path = worklog_path(ctx, item_id)
    old_log = log_path.read_text(encoding="utf-8") if log_path.exists() else None
    try:
        fm["status"] = "In Progress"
        fm["base_commit"] = git_head(verify_cwd(ctx, project_dir, None))
        fm["updated"] = today()
        write_doc(path, fm, body)
        promote_parents(project_dir, item_id)
        append_worklog(ctx, item_id, "착수", [f"session: {ctx.session}", f"note: {args.note or ''}", f"worktree: {args.worktree or ''}"])
        sync(ctx, project_dir)
    except Exception:
        for doc_path, original in backup_docs.items():
            ensure_dir(doc_path.parent)
            doc_path.write_text(original, encoding="utf-8")
        if old_log is None and log_path.exists():
            log_path.unlink()
        elif old_log is not None:
            log_path.write_text(old_log, encoding="utf-8")
        release_lock(lock_base, item_id)
        raise
    print_context(ctx, path, item_id)
    return 0


def print_context(ctx: Context, path: Path, item_id: str) -> None:
    fm, body = read_doc(path)
    print(f"# {fm.get('id')}")
    for heading in ("기본 내용", "범위", "완료 기준", "재개"):
        text = section_text(body, heading)
        if text:
            print(f"\n## {heading}\n{text}")
    resume, rows = section_text(body, "재개"), verification_rows(body)
    age = resume_age_minutes(resume)
    match = re.search(r"- 갱신:\s*([0-9T:+-]+)", resume)
    print("체크포인트: 없음" if age is None else f"체크포인트: 마지막 note {match.group(1)[11:16]} ({int(age)}분 전)")
    head, criteria = git_head(verify_cwd(ctx, ctx.project_dir(), None)), criteria_hash(body)
    success = next((row for row in reversed(rows) if len(row) >= 5 and row[4] == "0"), None)
    last = f"마지막 {rows[-1][1]}/{rows[-1][2]} exit {rows[-1][4]} @{rows[-1][0]}" if rows else "없음"
    print(f"검증: {last} → 현재 HEAD {head} / criteria {criteria} → 재검증 {'불필요' if success and success[1:3] == [head, criteria] else '필요'}")


def write_resume_block(path: Path, session: str, did: str, next_step: str, watch: Optional[str], wait: Optional[str], unverified: Optional[str]) -> None:
    fm, body = read_doc(path)
    block = [
        f"- 갱신: {timestamp()} (session {session})",
        f"- 한 것: {did}",
        f"- 다음: {next_step}",
        f"- 주의: {watch or '없음'}",
        f"- 대기: {wait or '없음'}",
        f"- 검증 못 한 것: {unverified or '없음'}",
    ]
    fm["updated"] = today()
    write_doc(path, fm, replace_section(body, "재개", "\n".join(block)))


def cmd_note(ctx: Context, args: argparse.Namespace) -> int:
    project_dir = ctx.project_dir()
    path = id_to_path(project_dir, args.item_id)
    require_lock_owner(project_lock_base(project_dir), args.item_id, ctx)
    write_resume_block(path, ctx.session, args.did, args.next_step, args.watch, args.wait, args.unverified)
    update_lock(project_lock_base(project_dir), args.item_id, ctx.session)
    append_worklog(ctx, args.item_id, "체크포인트", [f"한 것: {args.did}", f"다음: {args.next_step}", f"주의: {args.watch or '없음'}"])
    sync(ctx, project_dir)
    print(f"noted {args.item_id}")
    return 0


def cmd_verify(ctx: Context, args: argparse.Namespace) -> int:
    project_dir = ctx.project_dir()
    path = id_to_path(project_dir, args.item_id)
    fm, body = read_doc(path)
    if fm.get("type") != "item": raise PmtError("verify target must be an item", 2)
    require_lock_owner(project_lock_base(project_dir), args.item_id, ctx)
    criteria = criteria_hash(body)
    if not criteria: raise PmtError("완료 기준 비어 있음", 2)
    if bool(args.run) == (args.exit_code is not None): raise PmtError("choose exactly one of --run or --exit", 2)
    cwd = verify_cwd(ctx, project_dir, args.cwd)
    exit_code = args.exit_code
    if args.run:
        try:
            exit_code = subprocess.run(args.cmd, shell=True, cwd=str(cwd), capture_output=True, timeout=600).returncode
        except subprocess.TimeoutExpired:
            exit_code = 124
    commit = git_head(cwd)
    row = join_table_row([timestamp(), commit, criteria, escape_cell(args.cmd), str(exit_code), escape_cell(args.limit or "")])
    fm["updated"] = today()
    write_doc(path, fm, append_verification(body, row))
    append_worklog(ctx, args.item_id, "검증", [f"{args.cmd} exit {exit_code} @{commit}{f' {args.limit}' if args.limit else ''}"])
    update_lock(project_lock_base(project_dir), args.item_id, ctx.session)
    sync(ctx, project_dir)
    print(row)
    return 0


def cmd_end(ctx: Context, args: argparse.Namespace) -> int:
    project_dir = ctx.project_dir()
    if args.all:
        if not args.pause:
            raise PmtError("end --all requires --pause", 2)
        code = 0
        for row in read_locks(project_lock_base(project_dir)):
            if row.get("session") == ctx.session and not str(row.get("id", "")).startswith("__"):
                sub = argparse.Namespace(**vars(args))
                sub.all = False
                sub.item_id = row["id"]
                try:
                    code = max(code, cmd_end(ctx, sub))
                except PmtError as exc:
                    print(str(exc), file=sys.stderr)
                    code = max(code, exc.code)
        return code
    if not args.item_id:
        raise PmtError("item id is required", 2)
    modes = [args.done, args.pause, args.fail, args.skip]
    if sum(bool(x) for x in modes) != 1:
        raise PmtError("choose exactly one end mode", 2)
    path = id_to_path(project_dir, args.item_id)
    fm, body = read_doc(path)
    if args.done:
        if not args.result:
            raise PmtError("--done requires --result", 2)
        require_lock_owner(project_lock_base(project_dir), args.item_id, ctx)
        incomplete = sorted(
            item_id
            for item_id, node in scan_docs(project_dir).items()
            if node.get("parent") == args.item_id and node.get("status") in {"Planned", "In Progress"}
        )
        if incomplete:
            raise PmtError("cannot complete with unfinished children: " + ", ".join(incomplete), 2)
        criteria, head = criteria_hash(body), git_head(verify_cwd(ctx, project_dir, None))
        if fm.get("type") == "item" and not criteria: print("경고: 완료 기준 비어 있음", file=sys.stderr)
        elif fm.get("type") == "item" and not any(len(row) >= 5 and row[1:3] == [head, criteria] and row[4] == "0" for row in verification_rows(body)):
            if not args.unverified: raise PmtError(f"pmt verify {args.item_id} --cmd ... 또는 --unverified <사유>", 2)
            row = join_table_row([timestamp(), head, criteria, "-", "-", escape_cell(f"미검증: {args.unverified}")])
            body = append_verification(body, row)
        for evidence in args.evidence or []:
            if not Path(evidence).exists(): print(f"경고: evidence 없음: {evidence}", file=sys.stderr)
        body = replace_section(body, "결과", f"- {args.result}")
        if args.evidence:
            body = replace_section(body, "증거", "\n".join(f"- {x}" for x in args.evidence))
        body = replace_section(body, "재개", "")
        fm["status"] = "Done"
        fm["updated"] = today()
        write_doc(path, fm, body)
        unblocked = remove_active_relations(project_dir, args.item_id)
        result_lines = [f"결과: {args.result}", f"증거: {', '.join(args.evidence or []) or '없음'}"]
        if unblocked:
            result_lines.append(f"차단 해소: {', '.join(unblocked)}")
        append_worklog(ctx, args.item_id, "결과", result_lines)
        move_worklog_done(ctx, args.item_id)
        release_lock(project_lock_base(project_dir), args.item_id, ctx.session)
        auto_done_parents(project_dir, args.item_id)
        append_time(ctx, args.item_id, args.result)
        compact_lists(ctx, project_dir, skip_busy=True)
        sync(ctx, project_dir)
        doctor(ctx, project_dir, scope=args.item_id.split("/")[1] if "/" in args.item_id else None, quiet=False)
        print(f"done {args.item_id}")
        return 0
    if args.pause:
        require_lock_owner(project_lock_base(project_dir), args.item_id, ctx)
        resume = section_text(body, "재개")
        resume_age = resume_age_minutes(resume)
        if args.did and args.next_step:
            write_resume_block(path, ctx.session, args.did, args.next_step, args.watch, args.wait, args.unverified)
        elif resume_age is None or resume_age > 60:
            raise PmtError("--pause requires fresh resume block or --did and --next", 2)
        append_worklog(ctx, args.item_id, "체크포인트", ["pause"])
        release_lock(project_lock_base(project_dir), args.item_id, ctx.session)
        sync(ctx, project_dir)
        print(f"paused {args.item_id}")
        return 0
    if args.fail:
        if not args.cause or not args.fix:
            raise PmtError("--fail requires --cause and --fix", 2)
        require_lock_owner(project_lock_base(project_dir), args.item_id, ctx)
        text = f"실패 원인: {args.cause}; 처방: {args.fix}"
        write_resume_block(path, ctx.session, text, args.fix, text, args.wait, args.unverified)
        append_worklog(ctx, args.item_id, "실패", [text])
        release_lock(project_lock_base(project_dir), args.item_id, ctx.session)
        sync(ctx, project_dir)
        print(f"failed {args.item_id}")
        return 0
    if args.skip:
        if not args.reason:
            raise PmtError("--skip requires --reason", 2)
        require_lock_owner(project_lock_base(project_dir), args.item_id, ctx)
        children = sorted(
            item_id
            for item_id, node in scan_docs(project_dir).items()
            if node.get("parent") == args.item_id
        )
        if children:
            raise PmtError(
                "cannot skip an item with children; finish or skip children first: " + ", ".join(children),
                2,
            )
        old_id = args.item_id
        fm["status"] = "Canceled"
        fm["updated"] = today()
        fm["canceled_from_id"] = old_id
        class_name = old_id.split("/")[1]
        canceled_path = unique_path(project_dir / "canceled" / f"{class_name}__{path.stem}.md")
        new_id = f"{project_dir.name}/canceled/{canceled_path.stem}"
        fm["id"] = new_id
        fm["parent"] = f"{project_dir.name}/canceled"
        fm.pop("blocked_by", None)
        body = replace_section(body, "결과", f"- skipped: {args.reason}")
        write_doc(canceled_path, fm, body)
        if path != canceled_path and path.exists():
            path.unlink()
        unblocked = remove_active_relations(project_dir, old_id)
        skip_lines = [args.reason]
        if unblocked:
            skip_lines.append(f"차단 해소: {', '.join(unblocked)}")
        append_worklog(ctx, old_id, "스킵", skip_lines)
        release_lock(project_lock_base(project_dir), old_id, ctx.session)
        sync(ctx, project_dir)
        print(f"skipped {old_id}")
        return 0
    return 0


def move_worklog_done(ctx: Context, item_id: str) -> None:
    src = worklog_path(ctx, item_id)
    if not src.exists():
        return
    dst = ctx.worklog_root / "done" / src.name
    ensure_dir(dst.parent)
    if dst.exists():
        suffix = 2
        while True:
            candidate = dst.with_name(f"{dst.stem}__{suffix}{dst.suffix}")
            if not candidate.exists():
                dst = candidate
                break
            suffix += 1
    src.replace(dst)


def remove_active_relations(project_dir: Path, removed_id: str) -> List[str]:
    unblocked = []
    for item_id, node in scan_docs(project_dir).items():
        if node.get("type") != "item" or item_id == removed_id:
            continue
        path = Path(node["path"])
        fm = node["frontmatter"]
        blocked_by = as_list(fm.get("blocked_by"))
        if removed_id in blocked_by:
            fm["blocked_by"] = [value for value in blocked_by if value != removed_id]
            fm["updated"] = today()
            write_doc(path, fm, node["body"])
            unblocked.append(item_id)
    return sorted(unblocked)


def append_time(ctx: Context, item_id: str, result: str) -> None:
    ensure_dir(ctx.times_root)
    path = ctx.times_root / f"{today()[:7]}.md"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"- {timestamp()} {item_id}: {result}\n")


def auto_done_parents(project_dir: Path, item_id: str) -> None:
    nodes = scan_docs(project_dir)
    current = item_id
    while True:
        node = nodes.get(current)
        if not node:
            return
        fm = node["frontmatter"]
        parent = fm.get("parent")
        if not parent or parent == project_dir.name:
            return
        siblings = [candidate for candidate in nodes.values() if candidate.get("parent") == parent]
        if siblings and all(s.get("status") in {"Done", "Canceled"} for s in siblings):
            parent_node = nodes.get(str(parent))
            if not parent_node:
                return
            parent_fm = parent_node["frontmatter"]
            parent_fm["status"] = "Done"
            parent_fm["updated"] = today()
            write_doc(Path(parent_node["path"]), parent_fm, parent_node["body"])
            parent_node["status"] = "Done"
            current = str(parent)
        else:
            return


def build_graph(project_dir: Path) -> Dict[str, Any]:
    return {"nodes": scan_docs(project_dir)}


def parent_exists(project_dir: Path, nodes: Dict[str, Dict[str, Any]], parent: Any) -> bool:
    if not parent:
        return True
    parent_id = str(parent)
    if parent_id in nodes:
        return True
    parts = parent_id.split("/")
    return len(parts) == 2 and parts[0] == project_dir.name and (project_dir / parts[1]).is_dir()


def sync(ctx: Context, project_dir: Path) -> None:
    ensure_dir(project_lock_base(project_dir))
    index_id = "__index"
    if not acquire_lock_wait(project_lock_base(project_dir), index_id, ctx.session):
        raise PmtError("index lock busy", 1)
    try:
        graph = build_graph(project_dir)
        (project_dir / "RESUME.md").write_text(render_resume(ctx, project_dir, graph), encoding="utf-8")
        project_indexes(ctx)
    finally:
        release_lock(project_lock_base(project_dir), index_id, ctx.session)

def render_resume(ctx: Context, project_dir: Path, graph: Dict[str, Any]) -> str:
    nodes = graph["nodes"]
    active_work = sum(1 for n in nodes.values() if n.get("type") == "work" and n.get("status") == "In Progress")
    active_item = sum(1 for n in nodes.values() if n.get("type") == "item" and n.get("status") == "In Progress")
    locks = [row for row in read_locks(project_lock_base(project_dir)) if not str(row.get("id", "")).startswith("__")]
    project_goal = ""
    project = nodes.get(project_dir.name)
    if project:
        goal = section_text(project["body"], "Goal")
        project_goal = next((line.strip("- ").strip() for line in goal.splitlines() if line.strip("- ")), "")
    lines = [
        f"# RESUME - {project_dir.name} 생성 {timestamp()}",
        "## 30초 요약",
        f"- Goal: {project_goal}",
        f"- 활성 Work {active_work} · In Progress Item {active_item} · 점유 중 {len(locks)} · 미정 필드 0",
        "",
        "## 지금 점유 중 (Doing)",
        "| 세션 | 대상 | 경과 | 메모 |",
        "|---|---|---|---|",
    ]
    for row in locks:
        lines.append(f"| {row.get('session')} | {row.get('id')} | {row.get('heartbeat')} | {'stale' if row.get('stale') else ''} |")
    lines.append("\n## 이어받을 항목 (In Progress, 재개 블록 최신순)")
    for item_id, node in sorted(nodes.items(), key=lambda kv: str(kv[1].get("updated") or ""), reverse=True):
        if node.get("status") == "In Progress":
            lines.append(f"### {item_id} - {node.get('title')}")
            lines.append(node.get("resume") or "- 재개 정보 없음")
    lines.append("\n## 착수 가능 (선행 없음, 최대 10)")
    roots = 0
    for item_id, node in sorted(nodes.items()):
        if roots >= 10:
            break
        if node.get("type") != "project" and node.get("status") == "Planned" and not node.get("blocked_by"):
            lines.append(f"- {item_id} ({node.get('kind') or node.get('type')} {node.get('status')}) - {node.get('title')}")
            roots += 1
    if roots == 0:
        lines.append("- 없음")
    lines.append("\n## 최근 결정 5 / 최근 사실 5")
    lines.extend(recent_list_rows(project_dir / "decisions.md", 5, status="승인"))
    lines.extend(recent_list_rows(project_dir / "facts.md", 5))
    lines.append("\n## 최근 worklog 결과 3")
    lines.extend(recent_worklog(ctx, project_dir.name, 3))
    lines.append("\n## 주의 (doctor warn/fail 요약)")
    warnings, failures = doctor_collect(project_dir, nodes)
    for item in (failures + warnings)[:10]:
        lines.append(f"- {item}")
    if not warnings and not failures:
        lines.append("- 없음")
    text = "\n".join(lines) + "\n"
    if len(text) > 6000:
        text = text[:5900] + "\n\n- RESUME length trimmed; inspect graph.md and active item files for detail.\n"
    return text


def recent_list_rows(path: Path, limit: int, status: Optional[str] = None) -> List[str]:
    if not path.exists():
        return []
    _, body = read_doc(path)
    rows = [line for line in body.splitlines() if line.startswith("| ") and not line.startswith("| ID ") and not line.startswith("|---")]
    if status:
        status_index = table_header(body).index("상태")
        rows = [line for line in rows if split_table_row(line)[status_index] == status]
    return [f"- {row.strip('| ')}" for row in rows[-limit:]]


def recent_worklog(ctx: Context, slug: str, limit: int) -> List[str]:
    roots = [ctx.worklog_root, ctx.worklog_root / "done"]
    hits: List[Tuple[float, str]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob(f"{slug}__*.md"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "## 결과" in text:
                hits.append((path.stat().st_mtime, f"- {path.name}: 결과 기록 있음"))
    return [x for _, x in sorted(hits, reverse=True)[:limit]] or ["- 없음"]


def cmd_resume(ctx: Context, args: argparse.Namespace) -> int:
    ctx.project = args.slug
    project_dir = ctx.project_dir(args.slug)
    compact_lists(ctx, project_dir, skip_busy=True)
    sync(ctx, project_dir)
    print((project_dir / "RESUME.md").read_text(encoding="utf-8"))
    return 0


def cmd_sync(ctx: Context, args: argparse.Namespace) -> int:
    sync(ctx, ctx.project_dir())
    print("synced")
    return 0


def cmd_lock(ctx: Context, args: argparse.Namespace) -> int:
    repo_ids = sorted(str(Path(path).resolve()) for path in (args.repo or []))
    if args.lock_kind == "list":
        bases = []
        if ctx.project and ctx.project_dir().is_dir():
            bases.append(project_lock_base(ctx.project_dir()))
        bases.append(repo_lock_base(ctx))
        for base in bases:
            for row in read_locks(base):
                print(json.dumps(row, ensure_ascii=False))
        return 0
    if args.lock_kind == "reap":
        if repo_ids:
            return reap_locks(ctx, repo_lock_base(ctx), project_scoped=False)
        return reap_locks(ctx, project_lock_base(ctx.project_dir()), project_scoped=True)
    if repo_ids:
        base = repo_lock_base(ctx)
        if args.lock_kind == "acquire":
            acquired = []
            for item_id in repo_ids:
                if not acquire_lock(base, item_id, ctx.session):
                    for held in reversed(acquired):
                        release_lock(base, held, ctx.session)
                    print(f"busy {item_id}")
                    return 1
                acquired.append(item_id)
            for item_id in acquired:
                print(f"acquired {item_id}")
            return 0
        targets = list(reversed(repo_ids)) if args.lock_kind == "release" else repo_ids
        results = []
        for item_id in targets:
            if args.lock_kind == "beat":
                ok = update_lock(base, item_id, ctx.session)
                print(f"{'beat' if ok else 'not-owned'} {item_id}")
            else:
                ok = release_lock(base, item_id, ctx.session)
                print(f"{'released' if ok else 'not-owned'} {item_id}")
            results.append(ok)
        return 0 if all(results) else 1
    base = project_lock_base(ctx.project_dir())
    item_id = args.item_id
    if args.lock_kind in {"acquire", "beat", "release"} and not item_id:
        raise PmtError("lock id or --repo is required", 2)
    if args.lock_kind == "acquire":
        ok = acquire_lock(base, item_id, ctx.session)
        print("acquired" if ok else "busy")
        return 0 if ok else 1
    if args.lock_kind == "beat":
        ok = update_lock(base, item_id, ctx.session)
        print("beat" if ok else "not-owned")
        return 0 if ok else 1
    if args.lock_kind == "release":
        ok = release_lock(base, item_id, ctx.session)
        print("released" if ok else "not-owned")
        return 0 if ok else 1
    return 0


def reap_lock(ctx: Context, base: Path, item_id: str, project_scoped: bool) -> bool:
    meta = lock_meta(base, item_id)
    if not meta or lock_age_minutes(meta) < STALE_MINUTES:
        return False
    if project_scoped:
        path = ctx.project_dir() / item_id
        try:
            path = id_to_path(ctx.project_dir(), item_id)
            fm, body = read_doc(path)
            resume = section_text(body, "재개")
            line = f"- 비정상 종료 추정 (abnormal exit suspected): 마지막 체크포인트 {meta.get('heartbeat')}, 이후 작업 미기록"
            body = replace_section(body, "재개", line + "\n" + resume)
            write_doc(path, fm, body)
        except Exception as exc:
            print(f"경고: {path} {exc}", file=sys.stderr)
    return release_lock(base, item_id)


def reap_locks(ctx: Context, base: Path, project_scoped: bool) -> int:
    count = 0
    for row in read_locks(base):
        if row.get("stale") and reap_lock(ctx, base, str(row.get("id")), project_scoped):
            count += 1
    if project_scoped:
        sync(ctx, ctx.project_dir())
    print(f"reaped {count}")
    return 0


def decision_rows(project_dir: Path) -> Dict[str, Tuple[str, str, str, str]]:
    rows = {}
    for path in (project_dir / "decisions.md", project_dir / "archive" / "decisions.md"):
        if not path.exists():
            continue
        _, body = read_doc(path)
        for line in body.splitlines():
            cells = split_table_row(line) if line.strip().startswith("|") else []
            if len(cells) < 6 or not re.fullmatch(r"D\d+", cells[0]):
                continue
            rows[cells[0]] = (cells[1], cells[2], cells[3], cells[5])
    return rows


def cmd_find_chain(project_dir: Path, start_id: str) -> int:
    if not re.fullmatch(r"D\d+", start_id):
        raise PmtError(f"invalid decision id: {start_id}", 2)
    rows = decision_rows(project_dir)
    if start_id not in rows:
        print("0건")
        return 0
    chain, seen = [start_id], {start_id}
    while True:
        previous = rows[chain[0]][3]
        if previous not in rows or previous in seen:
            break
        chain.insert(0, previous)
        seen.add(previous)
    following = {}
    for decision_id in sorted(rows, key=lambda value: int(value[1:])):
        following.setdefault(rows[decision_id][3], decision_id)
    current = start_id
    while current in following and following[current] not in seen:
        current = following[current]
        chain.append(current)
        seen.add(current)
    print(" → ".join(f"{decision_id}({rows[decision_id][0]}, {rows[decision_id][1]}) {rows[decision_id][2]}"
                     for decision_id in chain))
    return 0


def cmd_find(ctx: Context, args: argparse.Namespace) -> int:
    project_dir = ctx.project_dir()
    if args.chain:
        return cmd_find_chain(project_dir, args.chain)
    if not args.query: raise PmtError("find requires query or --chain", 2)
    raw_query = args.query
    query = raw_query.lower()
    exact_id = bool(re.fullmatch(r"[A-Za-z]\d+|[A-Za-z0-9._-]+/.+", raw_query))
    exact_pattern = re.compile(rf"(^|\|\s|- )({re.escape(raw_query)})(\s*\||\b)")
    roots = [project_dir, project_dir / "archive", ctx.worklog_root, ctx.worklog_root / "done"]
    hits = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(text.splitlines(), 1):
                matched = bool(exact_pattern.search(line)) if exact_id else query in line.lower()
                if matched:
                    hits.append(f"{path}:{line_no}: {line}")
                    break
    if not hits:
        print("0건")
        return 0
    print("\n".join(hits))
    return 0


def compact_lists(ctx: Context, project_dir: Path, skip_busy: bool = False) -> int:
    moved, terminal = 0, {"Closed", "Done", "Dropped", "대체", "폐기"}
    for name in LIST_FILES:
        path = project_dir / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if len(text) <= 8000:
            continue
        lock_id = f"__list-{name}"
        if not acquire_lock(project_lock_base(project_dir), lock_id, ctx.session):
            if skip_busy:
                print(f"경고: 목록 압축 건너뜀: {name} lock busy", file=sys.stderr)
                continue
            raise PmtError(f"list lock busy: {name}", 1)
        try:
            text = path.read_text(encoding="utf-8")
            if len(text) <= 8000:
                continue
            fm, body = parse_frontmatter(text)
            lines = body.splitlines()
            header = table_header(body)
            if "상태" not in header:
                raise PmtError(f"missing 상태 column: {name}", 2)
            status_index = header.index("상태")
            keep, archive = [], []
            for line in lines:
                cells = split_table_row(line) if line.strip().startswith("|") else []
                if len(cells) > status_index and cells[0] != "ID" and cells[status_index] in terminal:
                    archive.append(line)
                else:
                    keep.append(line)
            if not archive:
                continue
            arch_path = project_dir / "archive" / name
            ensure_dir(arch_path.parent)
            if not arch_path.exists():
                table_lines = [line for line in lines if line.strip().startswith("|")]
                arch_path.write_text(f"# Archive {name}\n" + "\n".join(table_lines[:2]) + "\n", encoding="utf-8")
            with arch_path.open("a", encoding="utf-8", newline="\n") as handle:
                for line in archive:
                    handle.write(line + "\n")
            write_doc(path, fm, "\n".join(keep) + "\n")
            moved += len(archive)
        finally:
            release_lock(project_lock_base(project_dir), lock_id, ctx.session)
    return moved


def cmd_compact(ctx: Context, args: argparse.Namespace) -> int:
    moved = compact_lists(ctx, ctx.project_dir())
    sync(ctx, ctx.project_dir())
    print(f"moved {moved}")
    return 0


def doctor_collect(
    project_dir: Path, nodes: Optional[Dict[str, Dict[str, Any]]] = None
) -> Tuple[List[str], List[str]]:
    warnings: List[str] = []
    failures: List[str] = []
    nodes = nodes if nodes is not None else scan_docs(project_dir)
    required = ["type", "id", "status", "updated"]
    for item_id, node in nodes.items():
        path = Path(node["path"])
        fm = node["frontmatter"]
        body = node["body"]
        req = list(required)
        if fm.get("type") != "project":
            req.append("parent")
        missing = [key for key in req if not fm.get(key)]
        if missing:
            failures.append(f"{item_id}: missing {', '.join(missing)}")
        if item_id != fm.get("id"):
            failures.append(f"{path}: id mismatch")
        try:
            expected_path = id_to_path(project_dir, item_id)
            if fm.get("type") == "project":
                expected_path = project_dir / "project.md"
            if expected_path.resolve() != path.resolve():
                failures.append(f"{item_id}: id/path mismatch")
        except PmtError as exc:
            failures.append(f"{item_id}: {exc}")
        parent = fm.get("parent")
        if not parent_exists(project_dir, nodes, parent):
            if fm.get("type") == "work":
                failures.append(f"{item_id}: missing classification parent {parent}")
            else:
                failures.append(f"{item_id}: missing parent {parent}")
        for rel in as_list(fm.get("blocked_by")):
            if rel.startswith("ext:"):
                continue
            if rel not in nodes:
                failures.append(f"{item_id}: missing relation blocked_by={rel}")
        if fm.get("type") == "item":
            depth = len(str(item_id).split("/")[-1].split("-")) - 1
            if depth > 3:
                failures.append(f"{item_id}: depth > 3")
            if fm.get("kind") == "test":
                if any(n.get("parent") == item_id for n in nodes.values()):
                    failures.append(f"{item_id}: test item has child")
        if fm.get("status") == "In Progress":
            age = resume_age_minutes(body)
            if age is None or age > 24 * 60:
                warnings.append(f"{item_id}: resume block older than 24h or missing")
    for row in read_locks(project_lock_base(project_dir)):
        if row.get("stale"):
            warnings.append(f"stale lock: {row.get('id')}")
    for path in project_dir.rglob("handoff-*.md"):
        warnings.append(f"handoff file exists: {path}")
    failures.extend(check_cycles(nodes))
    failures.extend(check_lists(project_dir))
    for name in GENERATED:
        if not (project_dir / name).exists():
            warnings.append(f"missing generated file: {name}")
    return warnings, failures


def check_cycles(nodes: Dict[str, Dict[str, Any]]) -> List[str]:
    failures = []
    for item_id in nodes:
        seen = set()
        current = item_id
        while current in nodes:
            if current in seen:
                failures.append(f"{item_id}: parent cycle")
                break
            seen.add(current)
            parent = nodes[current].get("parent")
            if not parent:
                break
            current = parent
    return failures


def check_lists(project_dir: Path) -> List[str]:
    failures = []
    allowed_statuses = {"facts.md": {"Active", "Closed"}, "decisions.md": {"승인", "대체", "폐기"}, "backlog.md": {"Active", "Done", "Dropped"}}
    for name in LIST_FILES:
        path = project_dir / name
        if not path.exists():
            failures.append(f"missing list: {name}")
            continue
        fm, body = read_doc(path)
        header = table_header(body)
        if "상태" not in header:
            failures.append(f"{name}: missing 상태 column")
            continue
        status_index = header.index("상태")
        ids = []
        for line in body.splitlines():
            cells = split_table_row(line) if line.strip().startswith("|") else []
            if not cells or cells[0] == "ID" or set(cells[0]) <= {"-"}:
                continue
            ids.append(cells[0])
            if len(cells) <= status_index or cells[status_index] not in allowed_statuses[name]:
                status = cells[status_index] if len(cells) > status_index else ""
                failures.append(f"{name}: invalid status {cells[0]}={status}")
        if len(ids) != len(set(ids)):
            failures.append(f"{name}: duplicate ids")
        nums = [int(x[1:]) for x in ids if len(x) > 1 and x[1:].isdigit()]
        if nums and int(fm.get("next_id") or 1) <= max(nums):
            failures.append(f"{name}: next_id not ahead")
    return failures


def doctor(ctx: Context, project_dir: Path, scope: Optional[str] = None, quiet: bool = False) -> int:
    warnings, failures = doctor_collect(project_dir)
    if scope:
        warnings = [w for w in warnings if f"/{scope}/" in w or not w.startswith(project_dir.name + "/")]
        failures = [f for f in failures if f"/{scope}/" in f or not f.startswith(project_dir.name + "/")]
    if not quiet:
        print(f"doctor: {0 if failures else 1} pass, {len(warnings)} warn, fail: {len(failures)}")
        for item in failures:
            print(f"FAIL {item}")
        for item in warnings:
            print(f"WARN {item}")
    return 1 if failures else 0


def cmd_doctor(ctx: Context, args: argparse.Namespace) -> int:
    return doctor(ctx, ctx.project_dir(), scope=args.scope)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="pmt", description="Project Management Tool v2")
    parser.add_argument("--docs-root")
    parser.add_argument("--session")
    parser.add_argument("--project")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    p = sub.add_parser("new")
    p.add_argument("slug")
    p.add_argument("--goal", required=True)
    p.add_argument("--label", action="append")

    p = sub.add_parser("resume")
    p.add_argument("slug")

    p = sub.add_parser("add")
    add_sub = p.add_subparsers(dest="add_kind", required=True)
    w = add_sub.add_parser("work")
    w.add_argument("title")
    w.add_argument("--class", dest="class_name")
    w.add_argument("--goal")
    i = add_sub.add_parser("item")
    i.add_argument("parent_id")
    i.add_argument("title")
    i.add_argument("--kind", choices=["job", "view", "test", "hotfix"], default="job")
    i.add_argument("--verify")
    f = add_sub.add_parser("fact")
    f.add_argument("text")
    f.add_argument("--ref")
    b = add_sub.add_parser("backlog")
    b.add_argument("text")
    b.add_argument("--kind", choices=["req", "todo", "plan", "issue", "bug"], required=True)

    p = sub.add_parser("decide")
    p.add_argument("title")
    p.add_argument("--context", required=True)
    p.add_argument("--decision", required=True)
    p.add_argument("--alt")
    p.add_argument("--result")
    p.add_argument("--supersedes")
    p.add_argument("--decider")

    p = sub.add_parser("set")
    p.add_argument("target")
    p.add_argument("--status")
    p.add_argument("--why")
    p.add_argument("--blocked-by")
    p.add_argument("--unblock")

    p = sub.add_parser("start")
    p.add_argument("item_id")
    p.add_argument("--note")
    p.add_argument("--delegate", action="store_true")
    p.add_argument("--worktree")

    p = sub.add_parser("note")
    p.add_argument("item_id")
    p.add_argument("--did", required=True)
    p.add_argument("--next", dest="next_step", required=True)
    p.add_argument("--watch")
    p.add_argument("--wait")
    p.add_argument("--unverified")

    p = sub.add_parser("verify")
    p.add_argument("item_id")
    p.add_argument("--cmd", required=True)
    p.add_argument("--run", action="store_true")
    p.add_argument("--exit", dest="exit_code", type=int)
    for option in ("--cwd", "--limit"): p.add_argument(option)

    p = sub.add_parser("end")
    p.add_argument("item_id", nargs="?")
    p.add_argument("--all", action="store_true")
    p.add_argument("--done", action="store_true")
    p.add_argument("--pause", action="store_true")
    p.add_argument("--fail", action="store_true")
    p.add_argument("--skip", action="store_true")
    p.add_argument("--result")
    p.add_argument("--evidence", action="append")
    p.add_argument("--did")
    p.add_argument("--next", dest="next_step")
    p.add_argument("--watch")
    p.add_argument("--wait")
    p.add_argument("--unverified")
    p.add_argument("--cause")
    p.add_argument("--fix")
    p.add_argument("--reason")

    p = sub.add_parser("sync", help=argparse.SUPPRESS)

    p = sub.add_parser("lock")
    p.add_argument("lock_kind", choices=["acquire", "beat", "release", "list", "reap"])
    p.add_argument("item_id", nargs="?")
    p.add_argument("--repo", action="append")

    p = sub.add_parser("find")
    p.add_argument("query", nargs="?")
    p.add_argument("--chain")

    p = sub.add_parser("compact", help=argparse.SUPPRESS)
    p = sub.add_parser("doctor")
    p.add_argument("--scope")
    return parser.parse_args(argv)


def main(argv: Sequence[str] = sys.argv[1:]) -> int:
    try:
        args = parse_args(argv)
        ctx = Context(args)
        if not ctx.project and args.command == "resume":
            ctx.project = args.slug
        if ctx.project and ctx.project_dir().is_dir():
            rows = sorted(read_locks(project_lock_base(ctx.project_dir())), key=lambda row: str(row.get("id")))
            for row in rows:
                item_id = str(row.get("id", ""))
                age = lock_age_minutes(row)
                if row.get("session") == ctx.session and not item_id.startswith("__") and age >= WARN_MINUTES:
                    print(
                        f"주의: {item_id} 체크포인트 {int(age)}분 경과 — pmt note {item_id} --did ... --next ...",
                        file=sys.stderr,
                    )
        handlers = {
            "new": cmd_new,
            "resume": cmd_resume,
            "add": cmd_add,
            "decide": cmd_decide,
            "set": cmd_set,
            "start": cmd_start,
            "note": cmd_note,
            "verify": cmd_verify,
            "end": cmd_end,
            "sync": cmd_sync,
            "lock": cmd_lock,
            "find": cmd_find,
            "compact": cmd_compact,
            "doctor": cmd_doctor,
        }
        return handlers[args.command](ctx, args)
    except PmtError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code
    except Exception as exc:
        print(str(exc).replace("\n", " "), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
