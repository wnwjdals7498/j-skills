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
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


STATUSES_ACTIVE = {"Planned", "In Progress", "Blocked"}
LIST_FILES = ("facts.md", "decisions.md", "backlog.md")
GENERATED = {"RESUME.md", "graph.md", "graph.json", "Doing.md", "index.md"}
STALE_MINUTES = 30


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
        "updated",
        "labels",
        "repositories",
        "next_id",
        "verify",
        "blocks",
        "blocked_by",
        "related_to",
        "list_refs",
        "waiting_on",
        "resolved_blockers",
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


class Context:
    def __init__(self, args: argparse.Namespace) -> None:
        docs_arg = getattr(args, "docs_root", None) or os.environ.get("PMT_DOCS_ROOT")
        self.docs_root = Path(docs_arg).expanduser().resolve() if docs_arg else (Path.home() / "docs").resolve()
        self.projects_root = self.docs_root / "projects"
        self.worklog_root = self.docs_root / "worklog"
        self.times_root = self.docs_root / "times"
        self.session = getattr(args, "session", None) or os.environ.get("PMT_SESSION") or f"session-{os.getpid()}"
        self.project = getattr(args, "project", None) or self.detect_project()

    def detect_project(self) -> Optional[str]:
        try:
            cwd = Path.cwd().resolve()
            root = (self.docs_root / "projects").resolve()
            cwd.relative_to(root)
            rel = cwd.relative_to(root)
            return rel.parts[0] if rel.parts else None
        except Exception:
            return None

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
        if any(part in {"archive", "resources", ".locks", "canceled", ".migration-v1-backup"} for part in path.parts):
            continue
        if path.name in GENERATED or path.name in LIST_FILES:
            continue
        try:
            fm, body = read_doc(path)
        except Exception:
            continue
        item_id = fm.get("id")
        if not item_id:
            continue
        nodes[str(item_id)] = {
            "path": str(path),
            "type": fm.get("type"),
            "kind": fm.get("kind"),
            "status": fm.get("status"),
            "parent": fm.get("parent"),
            "title": title_from_body(body),
            "blocks": as_list(fm.get("blocks")),
            "blocked_by": as_list(fm.get("blocked_by")),
            "related_to": as_list(fm.get("related_to")),
            "waiting_on": fm.get("waiting_on"),
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
        head = "| ID | 상태 | 생성 | 내용 |\n|---|---|---|---|\n"
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
        name = next_work_id(project_dir, class_name)
        item_id = f"{ctx.require_project()}/{class_name}/{name}"
        parent = f"{ctx.require_project()}/{class_name}"
        body = (
            f"# {name}: {args.title}\n## Goal\n- {args.goal or args.title}\n"
            "## 결과\n-\n## 증거\n-\n"
        )
        write_doc(id_to_path(project_dir, item_id), {"type": "work", "id": item_id, "parent": parent, "status": "Planned", "updated": today()}, body)
        sync(ctx, project_dir)
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
        data = {"type": "item", "kind": args.kind, "id": item_id, "parent": parent_id, "status": "Planned", "updated": today()}
        if args.verify:
            data["verify"] = args.verify
        write_doc(id_to_path(project_dir, item_id), data, body)
        sync(ctx, project_dir)
        print(item_id)
        return 0
    return add_list_row(ctx, args)


def add_list_row(ctx: Context, args: argparse.Namespace) -> int:
    project_dir = ctx.project_dir()
    mapping = {"fact": ("facts.md", "F"), "decision": ("decisions.md", "D"), "backlog": ("backlog.md", "B")}
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
        if args.add_kind == "decision":
            text = f"전->후: {args.from_value} -> {args.to_value}. 사유: {args.why}. 결정자: {args.decider or ctx.session}. {args.text}"
            row = f"| {row_id} | Done | {today()} | {escape_cell(text)} |"
        elif args.add_kind == "fact":
            text = args.text + (f" 참조: {args.ref}" if args.ref else "")
            row = f"| {row_id} | Active | {today()} | {escape_cell(text)} |"
        else:
            row = f"| {row_id} | {args.kind} | Active | {today()} | {escape_cell(args.text)} |"
        body = insert_table_row(body, row)
        write_doc(path, fm, body)
        sync(ctx, project_dir)
        print(row_id)
        return 0
    finally:
        release_lock(project_lock_base(project_dir), lock_id, ctx.session)


def escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def insert_table_row(body: str, row: str) -> str:
    lines = body.splitlines()
    insert_at = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("## "):
            insert_at = i
            break
    lines.insert(insert_at, row)
    return "\n".join(lines) + "\n"


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


def require_lock_owner(base: Path, item_id: str, session: str) -> None:
    if not lock_owned(base, item_id, session):
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


def read_locks(base: Path) -> List[Dict[str, Any]]:
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
        hb = parse_time(str(meta.get("heartbeat", "")))
        stale = bool(hb and (now_local() - hb).total_seconds() > STALE_MINUTES * 60)
        meta["path"] = str(lock_dir)
        meta["stale"] = stale
        rows.append(meta)
    return rows


def parse_time(value: str) -> Optional[dt.datetime]:
    try:
        return dt.datetime.fromisoformat(value)
    except Exception:
        return None


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


def set_status(project_dir: Path, item_id: str, status: str) -> None:
    path = id_to_path(project_dir, item_id)
    fm, body = read_doc(path)
    fm["status"] = status
    fm["updated"] = today()
    write_doc(path, fm, body)


def promote_parents(project_dir: Path, item_id: str) -> None:
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
    if not acquire_lock(project_lock_base(project_dir), item_id, ctx.session):
        print(f"lock busy: {item_id}", file=sys.stderr)
        return 1
    backup_docs = {p: p.read_text(encoding="utf-8") for p in project_dir.rglob("*.md") if ".locks" not in p.parts}
    log_path = worklog_path(ctx, item_id)
    old_log = log_path.read_text(encoding="utf-8") if log_path.exists() else None
    try:
        fm["status"] = "In Progress"
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
        release_lock(project_lock_base(project_dir), item_id)
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
    impacts = related_followup_impacts(ctx, item_id)
    if impacts:
        print("\n## 관련 과거 worklog 후속 영향")
        for impact in impacts:
            print(f"- {impact}")


def related_followup_impacts(ctx: Context, item_id: str, limit: int = 10) -> List[str]:
    parts = item_id.split("/")
    component = parts[1] if len(parts) > 1 else "_default"
    hits: List[Tuple[float, str]] = []
    for root in (ctx.worklog_root, ctx.worklog_root / "done"):
        if not root.exists():
            continue
        for log_path in root.glob(f"{parts[0]}__*.md"):
            text = log_path.read_text(encoding="utf-8", errors="ignore")
            front, _ = parse_frontmatter(text)
            if component not in as_list(front.get("components")):
                continue
            for line in text.splitlines():
                if "후속 영향" in line:
                    hits.append((log_path.stat().st_mtime, f"{log_path.name}: {line.strip('- ')}"))
    return [value for _, value in sorted(hits, reverse=True)[:limit]]


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
    require_lock_owner(project_lock_base(project_dir), args.item_id, ctx.session)
    write_resume_block(path, ctx.session, args.did, args.next_step, args.watch, args.wait, args.unverified)
    update_lock(project_lock_base(project_dir), args.item_id, ctx.session)
    append_worklog(ctx, args.item_id, "체크포인트", [f"한 것: {args.did}", f"다음: {args.next_step}", f"주의: {args.watch or '없음'}"])
    sync(ctx, project_dir)
    print(f"noted {args.item_id}")
    return 0


def resume_is_fresh(text: str) -> bool:
    match = re.search(r"갱신:\s*([0-9T:+-]+)", text)
    if not match:
        return False
    when = parse_time(match.group(1))
    return bool(when and (now_local() - when).total_seconds() <= 60 * 60)


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
        require_lock_owner(project_lock_base(project_dir), args.item_id, ctx.session)
        body = replace_section(body, "결과", f"- {args.result}")
        if args.evidence:
            body = replace_section(body, "증거", "\n".join(f"- {x}" for x in args.evidence))
        body = replace_section(body, "재개", "")
        fm["status"] = "Done"
        fm["updated"] = today()
        write_doc(path, fm, body)
        append_worklog(ctx, args.item_id, "결과", [f"결과: {args.result}", f"증거: {', '.join(args.evidence or []) or '없음'}"])
        move_worklog_done(ctx, args.item_id)
        release_lock(project_lock_base(project_dir), args.item_id, ctx.session)
        auto_done_parents(project_dir, args.item_id)
        append_time(ctx, args.item_id, args.result)
        sync(ctx, project_dir)
        doctor(ctx, project_dir, scope=args.item_id.split("/")[1] if "/" in args.item_id else None, quiet=False)
        print(f"done {args.item_id}")
        return 0
    if args.pause:
        require_lock_owner(project_lock_base(project_dir), args.item_id, ctx.session)
        resume = section_text(body, "재개")
        if args.did and args.next_step:
            write_resume_block(path, ctx.session, args.did, args.next_step, args.watch, args.wait, args.unverified)
        elif not resume_is_fresh(resume):
            raise PmtError("--pause requires fresh resume block or --did and --next", 2)
        append_worklog(ctx, args.item_id, "체크포인트", ["pause"])
        release_lock(project_lock_base(project_dir), args.item_id, ctx.session)
        sync(ctx, project_dir)
        print(f"paused {args.item_id}")
        return 0
    if args.fail:
        if not args.cause or not args.fix:
            raise PmtError("--fail requires --cause and --fix", 2)
        require_lock_owner(project_lock_base(project_dir), args.item_id, ctx.session)
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
        require_lock_owner(project_lock_base(project_dir), args.item_id, ctx.session)
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
        new_id = f"{project_dir.name}/canceled/{Path(path).stem}"
        fm["id"] = new_id
        fm["parent"] = f"{project_dir.name}/canceled"
        for key in ("blocks", "blocked_by", "related_to"):
            fm.pop(key, None)
        body = replace_section(body, "결과", f"- skipped: {args.reason}")
        canceled_path = project_dir / "canceled" / path.name
        write_doc(canceled_path, fm, body)
        if path != canceled_path and path.exists():
            path.unlink()
        remove_active_relations(project_dir, old_id)
        append_worklog(ctx, old_id, "스킵", [args.reason])
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


def remove_active_relations(project_dir: Path, removed_id: str) -> None:
    for node in scan_docs(project_dir).values():
        path = Path(node["path"])
        fm, body = read_doc(path)
        changed = False
        for key in ("blocks", "blocked_by", "related_to"):
            values = as_list(fm.get(key))
            if removed_id in values:
                fm[key] = [value for value in values if value != removed_id]
                changed = True
        blockers = as_list(fm.get("resolved_blockers"))
        if changed and removed_id not in blockers:
            fm["resolved_blockers"] = blockers + [removed_id]
        if changed:
            fm["updated"] = today()
            write_doc(path, fm, body)


def append_time(ctx: Context, item_id: str, result: str) -> None:
    ensure_dir(ctx.times_root)
    path = ctx.times_root / f"{today()[:7]}.md"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"- {timestamp()} {item_id}: {result}\n")


def auto_done_parents(project_dir: Path, item_id: str) -> None:
    current = item_id
    while True:
        fm, _ = read_doc(id_to_path(project_dir, current))
        parent = fm.get("parent")
        if not parent or parent == project_dir.name:
            return
        siblings = [node for node in scan_docs(project_dir).values() if node.get("parent") == parent]
        if siblings and all(s.get("status") in {"Done", "Canceled"} for s in siblings):
            try:
                set_status(project_dir, str(parent), "Done")
            except PmtError:
                return
            current = str(parent)
        else:
            return


def build_graph(project_dir: Path) -> Dict[str, Any]:
    nodes = scan_docs(project_dir)
    children: Dict[str, List[str]] = {k: [] for k in nodes}
    for item_id, node in nodes.items():
        parent = node.get("parent")
        if parent in children:
            children[parent].append(item_id)
    return {"nodes": nodes, "children": children}


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
        (project_dir / "graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
        (project_dir / "graph.md").write_text(render_graph_md(project_dir, graph), encoding="utf-8")
        (project_dir / "Doing.md").write_text(render_doing(project_dir), encoding="utf-8")
        (project_dir / "index.md").write_text(render_index(graph), encoding="utf-8")
        (project_dir / "RESUME.md").write_text(render_resume(ctx, project_dir, graph), encoding="utf-8")
        project_indexes(ctx)
    finally:
        release_lock(project_lock_base(project_dir), index_id, ctx.session)


def render_graph_md(project_dir: Path, graph: Dict[str, Any]) -> str:
    lines = ["# Graph", "## Roots"]
    nodes = graph["nodes"]
    children = graph["children"]
    for item_id, node in sorted(nodes.items()):
        if node.get("type") != "project" and node.get("status") in STATUSES_ACTIVE and not node.get("blocked_by"):
            lines.append(f"- {item_id} ({node.get('status')}) {node.get('title')}")
    lines.append("\n## Blocked")
    for item_id, node in sorted(nodes.items()):
        if node.get("blocked_by"):
            lines.append(f"- {item_id} <- {', '.join(node.get('blocked_by') or [])}")
    lines.append("\n## Orphans")
    for item_id, node in sorted(nodes.items()):
        parent = node.get("parent")
        if parent and not parent_exists(project_dir, nodes, parent) and node.get("type") != "project":
            lines.append(f"- {item_id} parent missing: {parent}")
    lines.append("\n## Children")
    for item_id, kids in sorted(children.items()):
        if kids:
            lines.append(f"- {item_id}: {', '.join(sorted(kids))}")
    return "\n".join(lines) + "\n"


def render_doing(project_dir: Path) -> str:
    lines = ["# Doing", "| session | id | heartbeat | stale |", "|---|---|---|---|"]
    for row in read_locks(project_lock_base(project_dir)):
        if str(row.get("id", "")).startswith("__"):
            continue
        lines.append(f"| {row.get('session')} | {row.get('id')} | {row.get('heartbeat')} | {row.get('stale')} |")
    return "\n".join(lines) + "\n"


def render_index(graph: Dict[str, Any]) -> str:
    lines = ["# Index"]
    nodes = graph["nodes"]
    for item_id, node in sorted(nodes.items()):
        if node.get("type") in {"project", "work", "item"}:
            lines.append(f"- {item_id} [{node.get('type')} {node.get('status')}] {node.get('title')}")
    return "\n".join(lines) + "\n"


def render_resume(ctx: Context, project_dir: Path, graph: Dict[str, Any]) -> str:
    nodes = graph["nodes"]
    active_work = sum(1 for n in nodes.values() if n.get("type") == "work" and n.get("status") == "In Progress")
    active_item = sum(1 for n in nodes.values() if n.get("type") == "item" and n.get("status") == "In Progress")
    locks = [row for row in read_locks(project_lock_base(project_dir)) if not str(row.get("id", "")).startswith("__")]
    waiting = [(i, n) for i, n in nodes.items() if n.get("waiting_on")]
    project_goal = ""
    project_path = project_dir / "project.md"
    if project_path.exists():
        _, body = read_doc(project_path)
        goal = section_text(body, "Goal")
        project_goal = next((line.strip("- ").strip() for line in goal.splitlines() if line.strip("- ")), "")
    lines = [
        f"# RESUME - {project_dir.name} 생성 {timestamp()}",
        "## 30초 요약",
        f"- Goal: {project_goal}",
        f"- 활성 Work {active_work} · In Progress Item {active_item} · 점유 중 {len(locks)} · 외부 대기 {len(waiting)} · 미정 필드 0",
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
    lines.append("\n## 외부 대기")
    for item_id, node in waiting:
        lines.append(f"- {item_id}: {node.get('waiting_on')}")
    if not waiting:
        lines.append("- 없음")
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
    lines.extend(recent_list_rows(project_dir / "decisions.md", 5))
    lines.extend(recent_list_rows(project_dir / "facts.md", 5))
    lines.append("\n## 최근 worklog 결과 3")
    lines.extend(recent_worklog(ctx, project_dir.name, 3))
    lines.append("\n## 주의 (doctor warn/fail 요약)")
    warnings, failures = doctor_collect(project_dir)
    for item in (failures + warnings)[:10]:
        lines.append(f"- {item}")
    if not warnings and not failures:
        lines.append("- 없음")
    text = "\n".join(lines) + "\n"
    if len(text) > 6000:
        text = text[:5900] + "\n\n- RESUME length trimmed; inspect graph.md and active item files for detail.\n"
    return text


def recent_list_rows(path: Path, limit: int) -> List[str]:
    if not path.exists():
        return []
    _, body = read_doc(path)
    rows = [line for line in body.splitlines() if line.startswith("| ") and not line.startswith("| ID ") and not line.startswith("|---")]
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
    sync(ctx, project_dir)
    print((project_dir / "RESUME.md").read_text(encoding="utf-8"))
    return 0


def cmd_sync(ctx: Context, args: argparse.Namespace) -> int:
    sync(ctx, ctx.project_dir())
    print("synced")
    return 0


def cmd_graph(ctx: Context, args: argparse.Namespace) -> int:
    project_dir = ctx.project_dir()
    graph = build_graph(project_dir)
    nodes = graph["nodes"]
    children = graph["children"]
    target = args.item_id
    result: List[str] = []
    if args.graph_kind == "roots":
        result = [i for i, n in nodes.items() if n.get("type") != "project" and n.get("status") == "Planned" and not n.get("blocked_by")]
    elif args.graph_kind == "blocked":
        result = [f"{i}: {', '.join(n.get('blocked_by') or [])}" for i, n in nodes.items() if n.get("blocked_by")]
    elif args.graph_kind == "orphans":
        result = [
            i
            for i, n in nodes.items()
            if n.get("parent") and not parent_exists(project_dir, nodes, n.get("parent")) and n.get("type") != "project"
        ]
    elif target:
        if target not in nodes:
            raise PmtError(f"missing id: {target}", 1)
        if args.graph_kind == "children":
            result = sorted(children.get(target, []))
        elif args.graph_kind == "parents":
            parent = nodes[target].get("parent")
            result = [parent] if parent else []
        elif args.graph_kind == "ancestors":
            result = ancestors(nodes, target)
        elif args.graph_kind == "descendants":
            result = descendants(children, target)
    else:
        raise PmtError(f"{args.graph_kind} requires id", 2)
    print("\n".join(result))
    return 0


def ancestors(nodes: Dict[str, Dict[str, Any]], item_id: str) -> List[str]:
    out = []
    seen = set()
    current = item_id
    while True:
        parent = nodes.get(current, {}).get("parent")
        if not parent or parent in seen:
            return out
        out.append(parent)
        seen.add(parent)
        current = parent


def descendants(children: Dict[str, List[str]], item_id: str) -> List[str]:
    out = []
    stack = list(children.get(item_id, []))
    while stack:
        node = stack.pop(0)
        out.append(node)
        stack.extend(children.get(node, []))
    return out


def cmd_lock(ctx: Context, args: argparse.Namespace) -> int:
    base = repo_lock_base(ctx) if args.repo else project_lock_base(ctx.project_dir())
    item_id = str(Path(args.repo).resolve()) if args.repo else args.item_id
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
    if args.lock_kind == "list":
        for row in read_locks(base):
            print(json.dumps(row, ensure_ascii=False))
        return 0
    if args.lock_kind == "reap":
        return reap_locks(ctx, base, project_lock_base(ctx.project_dir()) == base)
    return 0


def reap_locks(ctx: Context, base: Path, project_scoped: bool) -> int:
    count = 0
    for row in read_locks(base):
        if not row.get("stale"):
            continue
        if project_scoped:
            try:
                path = id_to_path(ctx.project_dir(), row["id"])
                fm, body = read_doc(path)
                resume = section_text(body, "재개")
                line = f"- 비정상 종료 추정 (abnormal exit suspected): 마지막 체크포인트 {row.get('heartbeat')}, 이후 작업 미기록"
                body = replace_section(body, "재개", line + "\n" + resume)
                write_doc(path, fm, body)
            except Exception:
                pass
        shutil.rmtree(Path(row["path"]))
        count += 1
    if project_scoped:
        sync(ctx, ctx.project_dir())
    print(f"reaped {count}")
    return 0


def cmd_find(ctx: Context, args: argparse.Namespace) -> int:
    project_dir = ctx.project_dir()
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
            text = path.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(text.splitlines(), 1):
                matched = bool(exact_pattern.search(line)) if exact_id else query in line.lower()
                if matched:
                    hits.append(f"{path}:{line_no}: {line}")
                    break
    if not hits:
        return 1
    print("\n".join(hits))
    return 0


def cmd_compact(ctx: Context, args: argparse.Namespace) -> int:
    project_dir = ctx.project_dir()
    moved = 0
    for name in LIST_FILES:
        path = project_dir / name
        if not path.exists() or path.stat().st_size <= 8000:
            continue
        fm, body = read_doc(path)
        lines = body.splitlines()
        keep, archive = [], []
        for line in lines:
            if line.startswith("| ") and ("| Done |" in line or "| Canceled |" in line):
                archive.append(line)
            else:
                keep.append(line)
        if not archive:
            continue
        arch_path = project_dir / "archive" / name
        ensure_dir(arch_path.parent)
        with arch_path.open("a", encoding="utf-8", newline="\n") as handle:
            if arch_path.stat().st_size == 0:
                handle.write(f"# Archive {name}\n")
            for line in archive:
                handle.write(line + "\n")
        write_doc(path, fm, "\n".join(keep) + "\n")
        moved += len(archive)
    sync(ctx, project_dir)
    print(f"moved {moved}")
    return 0


def doctor_collect(project_dir: Path) -> Tuple[List[str], List[str]]:
    warnings: List[str] = []
    failures: List[str] = []
    nodes = scan_docs(project_dir)
    required = ["type", "id", "status", "updated"]
    for item_id, node in nodes.items():
        path = Path(node["path"])
        fm, body = read_doc(path)
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
        if parent and parent not in nodes:
            if fm.get("type") == "work":
                parent_parts = str(parent).split("/")
                if len(parent_parts) != 2 or parent_parts[0] != project_dir.name or not (project_dir / parent_parts[1]).is_dir():
                    failures.append(f"{item_id}: missing classification parent {parent}")
            else:
                failures.append(f"{item_id}: missing parent {parent}")
        for key in ("blocks", "blocked_by", "related_to"):
            for rel in as_list(fm.get(key)):
                if rel not in nodes:
                    failures.append(f"{item_id}: missing relation {key}={rel}")
        if fm.get("type") == "item":
            depth = len(str(item_id).split("/")[-1].split("-")) - 1
            if depth > 3:
                failures.append(f"{item_id}: depth > 3")
            if fm.get("kind") == "test":
                if any(n.get("parent") == item_id for n in nodes.values()):
                    failures.append(f"{item_id}: test item has child")
        if fm.get("status") == "In Progress":
            resume = section_text(body, "재개")
            if not resume_is_recent_hours(resume, 24):
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


def resume_is_recent_hours(text: str, hours: int) -> bool:
    match = re.search(r"갱신:\s*([0-9T:+-]+)", text)
    if not match:
        return False
    when = parse_time(match.group(1))
    return bool(when and (now_local() - when).total_seconds() <= hours * 3600)


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
    for name in LIST_FILES:
        path = project_dir / name
        if not path.exists():
            failures.append(f"missing list: {name}")
            continue
        fm, body = read_doc(path)
        ids = []
        for line in body.splitlines():
            if line.startswith("| ") and not line.startswith("| ID ") and not line.startswith("|---"):
                ids.append(line.split("|")[1].strip())
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


def cmd_close(ctx: Context, args: argparse.Namespace) -> int:
    if not args.confirm:
        raise PmtError("close requires --confirm", 2)
    project_dir = ctx.project_dir(args.slug or ctx.project)
    fm, body = read_doc(project_dir / "project.md")
    repos = as_list(fm.get("repositories"))
    if repos and not args.remote_synced:
        raise PmtError("remote targets configured; pass --remote-synced after explicit upsert", 2)
    fm["status"] = "Done"
    fm["updated"] = today()
    write_doc(project_dir / "project.md", fm, body)
    sync(ctx, project_dir)
    print(f"closed {project_dir.name}")
    return 0


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
        status = canonical_status(cells[1] if len(cells) > 1 else source_fm.get("status"))
        created = canonical_date(cells[2] if len(cells) > 2 else source_fm.get("updated"))
        content = cells[-1] if len(cells) > 1 else row
        new_id = allocate_list_id(fm, prefix)
        id_map[old_id] = new_id
        body = insert_table_row(body, f"| {new_id} | {status} | {created} | {escape_cell(f'[{old_id}] {content}')} |")
    remainder = non_table_remainder(source_body)
    if remainder:
        new_id = allocate_list_id(fm, prefix)
        body = insert_table_row(body, f"| {new_id} | Active | {today()} | {escape_cell(f'[{old_name}] {remainder}')} |")
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
        status = canonical_status(cells[1] if len(cells) > 1 else source_fm.get("status"))
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
            target_path = worklog_path_for_id(ctx, target_id)
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


def worklog_path_for_id(ctx: Context, item_id: str) -> Path:
    parts = item_id.split("/")
    class_name = parts[1] if len(parts) > 1 else "_default"
    item_name = parts[-1]
    return ctx.worklog_root / f"{parts[0]}__{class_name}__{item_name}.md"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="pmt", description="Project Management Tool v2")
    parser.add_argument("--docs-root")
    parser.add_argument("--session")
    parser.add_argument("--project")
    sub = parser.add_subparsers(dest="command", required=True)

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
    d = add_sub.add_parser("decision")
    d.add_argument("text")
    d.add_argument("--from", dest="from_value", required=True)
    d.add_argument("--to", dest="to_value", required=True)
    d.add_argument("--why", required=True)
    d.add_argument("--decider")
    b = add_sub.add_parser("backlog")
    b.add_argument("text")
    b.add_argument("--kind", choices=["req", "todo", "plan", "issue", "bug"], required=True)

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

    p = sub.add_parser("sync")

    p = sub.add_parser("graph")
    p.add_argument("graph_kind", choices=["roots", "blocked", "children", "parents", "ancestors", "descendants", "orphans"])
    p.add_argument("item_id", nargs="?")

    p = sub.add_parser("lock")
    p.add_argument("lock_kind", choices=["acquire", "beat", "release", "list", "reap"])
    p.add_argument("item_id", nargs="?")
    p.add_argument("--repo")

    p = sub.add_parser("find")
    p.add_argument("query")

    p = sub.add_parser("compact")
    p = sub.add_parser("doctor")
    p.add_argument("--scope")

    p = sub.add_parser("close")
    p.add_argument("slug", nargs="?")
    p.add_argument("--confirm", action="store_true")
    p.add_argument("--remote-synced", action="store_true")

    p = sub.add_parser("migrate")
    p.add_argument("migrate_kind", choices=["v1"])
    p.add_argument("slug", nargs="?")
    p.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] = sys.argv[1:]) -> int:
    try:
        args = parse_args(argv)
        ctx = Context(args)
        handlers = {
            "new": cmd_new,
            "resume": cmd_resume,
            "add": cmd_add,
            "start": cmd_start,
            "note": cmd_note,
            "end": cmd_end,
            "sync": cmd_sync,
            "graph": cmd_graph,
            "lock": cmd_lock,
            "find": cmd_find,
            "compact": cmd_compact,
            "doctor": cmd_doctor,
            "close": cmd_close,
            "migrate": cmd_migrate,
        }
        return handlers[args.command](ctx, args)
    except PmtError as exc:
        print(str(exc), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    raise SystemExit(main())
