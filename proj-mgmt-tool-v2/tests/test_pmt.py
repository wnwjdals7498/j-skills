import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PMT = ROOT / "scripts" / "pmt.py"
VALIDATE = ROOT / "scripts" / "validate_skill.py"
SESSION = "test-session"


class PmtTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_pmt(self, *args, session=SESSION, ok=True):
        cmd = [
            sys.executable,
            str(PMT),
            "--docs-root",
            str(self.docs),
        ]
        if session is not None:
            cmd.extend(["--session", session])
        cmd.extend(args)
        env = os.environ.copy()
        if session is None:
            env.pop("PMT_SESSION", None)
        proc = subprocess.run(cmd, text=True, capture_output=True, env=env)
        if ok and proc.returncode != 0:
            self.fail(f"{cmd} failed\nstdout={proc.stdout}\nstderr={proc.stderr}")
        return proc

    def set_lock_heartbeat(self, root, item_id, minutes):
        heartbeat = (dt.datetime.now() - dt.timedelta(minutes=minutes)).replace(microsecond=0)
        for meta_path in root.glob("*.lock/lock.json"):
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            if data.get("id") != item_id:
                continue
            data["heartbeat"] = heartbeat.isoformat(timespec="minutes")
            meta_path.write_text(json.dumps(data), encoding="utf-8")
            return
        self.fail(f"missing lock: {item_id}")

    def make_item(self, slug="alpha", title="First item"):
        self.run_pmt("new", slug, "--goal", "ship alpha")
        work = self.run_pmt("--project", slug, "add", "work", "Build core").stdout.strip()
        item = self.run_pmt("--project", slug, "add", "item", work, title).stdout.strip()
        return slug, work, item

    def test_new_add_start_note_resume_supports_cold_start(self):
        slug, _work, item = self.make_item()
        self.run_pmt("--project", slug, "start", item)
        self.run_pmt(
            "--project",
            slug,
            "note",
            item,
            "--did",
            "created command parser",
            "--next",
            "run unit tests",
            "--watch",
            "do not edit user files",
        )

        resume = self.run_pmt("resume", slug).stdout

        self.assertIn("created command parser", resume)
        self.assertIn("run unit tests", resume)
        self.assertIn("do not edit user files", resume)

    def test_same_item_lock_conflicts_but_different_items_can_start(self):
        slug, work, item_one = self.make_item()
        item_two = self.run_pmt("--project", slug, "add", "item", work, "Second item").stdout.strip()

        first = self.run_pmt("--project", slug, "start", item_one, session="s1")
        same = self.run_pmt("--project", slug, "start", item_one, session="s2", ok=False)
        different = self.run_pmt("--project", slug, "start", item_two, session="s2")

        self.assertEqual(first.returncode, 0)
        self.assertEqual(same.returncode, 1)
        self.assertEqual(different.returncode, 0)

    def test_reap_marks_abnormal_exit_and_preserves_last_note(self):
        slug, _work, item = self.make_item()
        self.run_pmt("--project", slug, "start", item, session="lost")
        self.run_pmt(
            "--project",
            slug,
            "note",
            item,
            "--did",
            "last durable checkpoint",
            "--next",
            "continue from checkpoint",
            session="lost",
        )
        missing = f"{slug}/_default/Missing"
        self.run_pmt("--project", slug, "lock", "acquire", missing, session="lost")
        for lock_meta in (self.docs / "projects" / slug / ".locks").glob("*.lock/lock.json"):
            data = json.loads(lock_meta.read_text(encoding="utf-8"))
            data["heartbeat"] = "2000-01-01T00:00:00"
            lock_meta.write_text(json.dumps(data), encoding="utf-8")

        reaped = self.run_pmt("--project", slug, "lock", "reap", item, session="new")
        resume = self.run_pmt("resume", slug, session="new").stdout

        self.assertIn("last durable checkpoint", resume)
        self.assertIn("비정상 종료 추정", resume)
        self.assertIn(missing, reaped.stderr)

    def test_done_requires_result_and_marks_parent_done_when_children_done(self):
        slug, work, item = self.make_item()
        self.run_pmt("--project", slug, "start", item)

        missing = self.run_pmt("--project", slug, "end", item, "--done", ok=False)
        self.assertEqual(missing.returncode, 2)

        self.run_pmt("--project", slug, "end", item, "--done", "--result", "completed parser")
        work_text = (self.docs / "projects" / slug / "_default" / "Work1.md").read_text(encoding="utf-8")
        self.assertIn("status: Done", work_text)
        self.assertRegex(self.run_pmt("--project", slug, "doctor").stdout, r"(0 fail|fail: 0)")

    def test_end_all_pause_releases_session_locks(self):
        slug, work, item_one = self.make_item()
        item_two = self.run_pmt("--project", slug, "add", "item", work, "Second item").stdout.strip()
        self.run_pmt("--project", slug, "start", item_one)
        self.run_pmt("--project", slug, "start", item_two)
        for item in (item_one, item_two):
            self.run_pmt("--project", slug, "note", item, "--did", "paused work", "--next", "resume work")

        self.run_pmt("--project", slug, "end", "--all", "--pause")
        locks = self.run_pmt("--project", slug, "lock", "list").stdout
        doctor = self.run_pmt("--project", slug, "doctor").stdout

        self.assertNotIn(SESSION, locks)
        self.assertRegex(doctor, r"(0 fail|fail: 0)")

    def test_compact_preserves_find_for_archived_rows(self):
        slug, _work, _item = self.make_item()
        target = "archived fact survives"
        self.run_pmt("--project", slug, "add", "fact", target)
        self.run_pmt("--project", slug, "set", "F1", "--status", "Closed")
        facts = self.docs / "projects" / slug / "facts.md"
        with facts.open("a", encoding="utf-8") as fh:
            for i in range(80):
                fh.write(f"| F{i + 2} | Active | 2026-09-02 | filler {'x' * 120} |\n")

        before = self.run_pmt("--project", slug, "find", "F1").stdout
        self.run_pmt("--project", slug, "lock", "acquire", "__list-facts.md", session="other")
        busy = self.run_pmt("--project", slug, "compact", ok=False)
        self.assertEqual(busy.returncode, 1)
        self.run_pmt("--project", slug, "lock", "release", "__list-facts.md", session="other")
        self.run_pmt("--project", slug, "compact")
        after = self.run_pmt("--project", slug, "find", "F1").stdout
        missing = self.run_pmt("--project", slug, "find", "does-not-exist")

        self.assertIn(target, before)
        self.assertIn("F1", before)
        self.assertIn(target, before)
        self.assertIn("F1", after)
        self.assertIn(target, after)
        self.assertIn("archive", after)
        self.assertEqual(missing.returncode, 0)
        self.assertEqual(missing.stdout.strip(), "0건")

    def test_validate_skill_passes_and_can_run_tests(self):
        proc = subprocess.run([sys.executable, str(VALIDATE), str(ROOT)], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        invalid_root = self.docs / "not-a-directory"
        invalid_root.write_text("file", encoding="utf-8")
        unexpected = subprocess.run(
            [sys.executable, str(PMT), "--docs-root", str(invalid_root), "--project", "x", "sync"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(unexpected.returncode, 3)
        self.assertEqual(len(unexpected.stderr.splitlines()), 1)

    def test_terminal_item_cannot_restart_and_end_modes_require_payloads(self):
        slug, _work, item = self.make_item()
        self.run_pmt("--project", slug, "start", item)
        self.run_pmt("--project", slug, "end", item, "--done", "--result", "first result")

        restarted = self.run_pmt("--project", slug, "start", item, ok=False)
        self.assertEqual(restarted.returncode, 2)

        _slug, _work, active = self.make_item(slug="beta")
        self.run_pmt("--project", "beta", "start", active)
        failed = self.run_pmt("--project", "beta", "end", active, "--fail", ok=False)
        skipped = self.run_pmt("--project", "beta", "end", active, "--skip", ok=False)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(skipped.returncode, 2)

    def test_skip_parent_is_rejected_but_leaf_skip_keeps_doctor_clean(self):
        slug, work, parent = self.make_item()
        child = self.run_pmt("--project", slug, "add", "item", parent, "Child").stdout.strip()
        blocked = self.run_pmt("--project", slug, "add", "item", work, "Blocked sibling").stdout.strip()
        self.run_pmt("--project", slug, "set", blocked, "--blocked-by", child)
        self.run_pmt("--project", slug, "start", parent)
        rejected = self.run_pmt(
            "--project", slug, "end", parent, "--skip", "--reason", "obsolete", ok=False
        )
        self.assertEqual(rejected.returncode, 2)

        self.run_pmt("--project", slug, "start", child)
        self.run_pmt("--project", slug, "end", child, "--skip", "--reason", "obsolete")
        self.assertTrue((self.docs / "projects" / slug / "canceled" / "_default__Work1-1-1.md").exists())
        blocked_text = (self.docs / "projects" / slug / "_default" / "Work1-2.md").read_text(encoding="utf-8")
        worklog = self.docs / "worklog" / f"{slug}___default__Work1-1-1.md"
        self.assertNotIn(child, blocked_text)
        self.assertIn(f"차단 해소: {blocked}", worklog.read_text(encoding="utf-8"))
        self.assertEqual(self.run_pmt("--project", slug, "doctor").returncode, 0)

    def test_doctor_fails_on_id_path_mismatch(self):
        slug, _work, item = self.make_item()
        path = self.docs / "projects" / slug / "_default" / "Work1-1.md"
        text = path.read_text(encoding="utf-8").replace(f"id: {item}", f"id: {slug}/_default/Work9-9")
        path.write_text(text, encoding="utf-8")
        invalid = path.with_name("invalid.md")
        invalid.write_bytes(b"\xff")

        result = self.run_pmt("--project", slug, "doctor", ok=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("id/path mismatch", result.stdout)
        self.assertIn(f"경고: {invalid}", result.stderr)

    def test_doctor_fails_on_missing_parent(self):
        slug, work, _item = self.make_item()
        path = self.docs / "projects" / slug / "_default" / "Work1-1.md"
        text = path.read_text(encoding="utf-8").replace(f"parent: {work}", f"parent: {slug}/_default/Work99")
        path.write_text(text, encoding="utf-8")

        result = self.run_pmt("--project", slug, "doctor", ok=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("missing parent", result.stdout)

    def test_doctor_fails_on_cycle(self):
        slug, work, item = self.make_item()
        path = self.docs / "projects" / slug / "_default" / "Work1-1.md"
        text = path.read_text(encoding="utf-8").replace(f"parent: {work}", f"parent: {item}")
        path.write_text(text, encoding="utf-8")

        result = self.run_pmt("--project", slug, "doctor", ok=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("parent cycle", result.stdout)

    def test_doctor_fails_on_duplicate_list_id(self):
        slug, _work, _item = self.make_item()
        self.run_pmt("--project", slug, "add", "fact", "first\\fact|value")
        self.run_pmt("--project", slug, "add", "fact", "second fact")
        path = self.docs / "projects" / slug / "facts.md"
        text = path.read_text(encoding="utf-8").replace("| F2 |", "| F1 |", 1)
        path.write_text(text, encoding="utf-8")

        result = self.run_pmt("--project", slug, "doctor", ok=False)

        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate ids", result.stdout)
        self.assertIn("first\\\\fact\\|value", text)

    def test_done_rejects_incomplete_children(self):
        slug, _work, parent = self.make_item()
        child = self.run_pmt("--project", slug, "add", "item", parent, "Child").stdout.strip()
        self.run_pmt("--project", slug, "start", parent)

        result = self.run_pmt(
            "--project", slug, "end", parent, "--done", "--result", "parent done", ok=False
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn(child, result.stderr)

    def test_skip_two_classes_same_stem_no_overwrite(self):
        slug = "classes"
        self.run_pmt("new", slug, "--goal", "skip safely")
        first_work = self.run_pmt(
            "--project", slug, "add", "work", "First class", "--class", "first"
        ).stdout.strip()
        second_work = self.run_pmt(
            "--project", slug, "add", "work", "Second class", "--class", "second"
        ).stdout.strip()
        first_item = self.run_pmt(
            "--project", slug, "add", "item", first_work, "First item"
        ).stdout.strip()
        second_item = self.run_pmt(
            "--project", slug, "add", "item", second_work, "Second item"
        ).stdout.strip()
        canceled = self.docs / "projects" / slug / "canceled"
        canceled.mkdir()
        existing = canceled / "first__Work1-1.md"
        existing.write_text("sentinel", encoding="utf-8")

        for item in (first_item, second_item):
            self.run_pmt("--project", slug, "start", item)
            self.run_pmt("--project", slug, "end", item, "--skip", "--reason", "obsolete")

        first = canceled / "first__Work1-1-1.md"
        second = canceled / "second__Work1-1.md"
        self.assertEqual(existing.read_text(encoding="utf-8"), "sentinel")
        self.assertTrue(first.exists())
        self.assertTrue(second.exists())
        self.assertIn("First item", first.read_text(encoding="utf-8"))
        self.assertIn("Second item", second.read_text(encoding="utf-8"))

    def test_compact_threshold_counts_chars_not_bytes(self):
        slug, _work, _item = self.make_item()
        path = self.docs / "projects" / slug / "facts.md"
        text = path.read_text(encoding="utf-8").replace("next_id: 1", "next_id: 2")
        text += f"| F1 | Done | 2026-09-04 | {'가' * 3000} |\n"
        self.assertLess(len(text), 8000)
        self.assertGreater(len(text.encode("utf-8")), 8000)
        path.write_text(text, encoding="utf-8")

        self.run_pmt("--project", slug, "compact")

        self.assertIn("| F1 | Done |", path.read_text(encoding="utf-8"))
        self.assertFalse((self.docs / "projects" / slug / "archive" / "facts.md").exists())

    def test_add_work_rejects_reserved_class(self):
        slug = "reserved"
        self.run_pmt("new", slug, "--goal", "guard namespaces")
        invalid = ["archive", "canceled", "resources", "decisions", ".locks", ".", ".hidden", "_hidden"]
        for class_name in invalid:
            with self.subTest(class_name=class_name):
                result = self.run_pmt(
                    "--project", slug, "add", "work", "Invalid", "--class", class_name, ok=False
                )
                self.assertEqual(result.returncode, 2)
        allowed = self.run_pmt(
            "--project", slug, "add", "work", "Default", "--class", "_default"
        )
        self.assertEqual(allowed.returncode, 0)

    def test_project_status_becomes_in_progress_on_start(self):
        slug, _work, item = self.make_item()
        project = self.docs / "projects" / slug / "project.md"
        resume = self.docs / "projects" / slug / "RESUME.md"
        (self.docs / "projects" / slug / "resources" / "evidence" / "binary.md").write_bytes(b"\xff")
        self.assertIn("status: Planned", project.read_text(encoding="utf-8"))
        self.assertNotIn(item, resume.read_text(encoding="utf-8"))

        self.run_pmt("--project", slug, "start", item)

        self.assertIn("status: In Progress", project.read_text(encoding="utf-8"))
        self.assertIn(item, resume.read_text(encoding="utf-8"))

    def test_default_session_is_stable_across_calls(self):
        slug, _work, item = self.make_item(slug="stable-session")

        self.run_pmt("--project", slug, "start", item, session=None)
        noted = self.run_pmt(
            "--project",
            slug,
            "note",
            item,
            "--did",
            "started without explicit session",
            "--next",
            "continue with derived session",
            session=None,
        )

        self.assertEqual(noted.returncode, 0)
        self.assertIn("noted", noted.stdout)
        lock_data = next(
            json.loads(path.read_text(encoding="utf-8"))
            for path in (self.docs / "projects" / slug / ".locks").glob("*.lock/lock.json")
        )
        self.assertEqual(lock_data["session"], f"pid-{os.getppid()}")

    def test_start_reaps_stale_lock_and_marks_abnormal_exit(self):
        slug, work, item = self.make_item(slug="stale-start")
        other = self.run_pmt("--project", slug, "add", "item", work, "Other").stdout.strip()
        self.run_pmt("--project", slug, "start", item, session="lost")
        self.run_pmt("--project", slug, "start", other, session="other-owner")
        locks = self.docs / "projects" / slug / ".locks"
        self.set_lock_heartbeat(locks, item, 40)
        self.set_lock_heartbeat(locks, other, 40)

        restarted = self.run_pmt("--project", slug, "start", item, session="new")
        item_path = self.docs / "projects" / slug / "_default" / "Work1-1.md"
        lock_data = {
            data["id"]: data
            for path in locks.glob("*.lock/lock.json")
            for data in [json.loads(path.read_text(encoding="utf-8"))]
        }

        self.assertEqual(restarted.returncode, 0)
        self.assertIn("비정상 종료 추정", item_path.read_text(encoding="utf-8"))
        self.assertEqual(lock_data[item]["session"], "new")
        self.assertEqual(lock_data[other]["session"], "other-owner")

    def test_stale_warning_printed_on_any_command(self):
        slug, _work, item = self.make_item(slug="warning")
        self.run_pmt("--project", slug, "start", item)
        locks = self.docs / "projects" / slug / ".locks"
        self.set_lock_heartbeat(locks, item, 25)

        result = self.run_pmt("--project", slug, "doctor")

        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stderr.splitlines()[0].startswith(f"주의: {item} 체크포인트"))

    def test_start_gate_blocks_when_other_item_stale_then_passes_after_note(self):
        slug, work, first = self.make_item(slug="start-gate")
        second = self.run_pmt("--project", slug, "add", "item", work, "Second").stdout.strip()
        self.run_pmt("--project", slug, "start", first, session="gate")
        locks = self.docs / "projects" / slug / ".locks"
        self.set_lock_heartbeat(locks, first, 40)

        blocked = self.run_pmt("--project", slug, "start", second, session="gate", ok=False)
        self.assertEqual(blocked.returncode, 2)
        self.assertIn(
            f"먼저 pmt note {first} --did --next 또는 pmt end {first} --pause",
            blocked.stderr,
        )

        self.run_pmt(
            "--project",
            slug,
            "note",
            first,
            "--did",
            "checkpoint refreshed",
            "--next",
            "start second item",
            session="gate",
        )
        started = self.run_pmt("--project", slug, "start", second, session="gate")
        self.assertEqual(started.returncode, 0)

    def test_repo_lock_conflict_release_reap(self):
        slug, _work, item = self.make_item(slug="repo-lock")
        self.run_pmt("--project", slug, "start", item, session="owner")
        repo = self.docs / "repos" / "one"
        repo.mkdir(parents=True)
        repo_id = str(repo.resolve())

        self.run_pmt("lock", "acquire", "--repo", str(repo), session="owner")
        conflict = self.run_pmt("lock", "acquire", "--repo", str(repo), session="other", ok=False)
        listed = self.run_pmt("--project", slug, "lock", "list", session="viewer")
        wrong_release = self.run_pmt(
            "lock", "release", "--repo", str(repo), session="other", ok=False
        )

        self.assertEqual(conflict.returncode, 1)
        self.assertEqual(wrong_release.returncode, 1)
        self.assertIn(item, listed.stdout)
        self.assertIn(repo_id, listed.stdout)

        self.run_pmt("lock", "release", "--repo", str(repo), session="owner")
        self.run_pmt("lock", "acquire", "--repo", str(repo), session="owner")
        self.set_lock_heartbeat(self.docs / ".repo-locks", repo_id, 40)
        reaped = self.run_pmt("lock", "reap", "--repo", str(repo), session="other")
        reacquired = self.run_pmt("lock", "acquire", "--repo", str(repo), session="other")

        self.assertIn("reaped 1", reaped.stdout)
        self.assertEqual(reacquired.returncode, 0)

    def test_repo_lock_multi_sorted_acquire_and_rollback(self):
        repo_a = self.docs / "repos" / "a"
        repo_b = self.docs / "repos" / "b"
        repo_a.mkdir(parents=True)
        repo_b.mkdir(parents=True)
        repo_ids = sorted([str(repo_a.resolve()), str(repo_b.resolve())])

        acquired = self.run_pmt(
            "lock",
            "acquire",
            "--repo",
            str(repo_b),
            "--repo",
            str(repo_a),
            session="multi",
        )
        self.assertEqual(acquired.stdout.splitlines(), [f"acquired {item}" for item in repo_ids])

        beaten = self.run_pmt(
            "lock", "beat", "--repo", str(repo_b), "--repo", str(repo_a), session="multi"
        )
        self.assertEqual(beaten.stdout.splitlines(), [f"beat {item}" for item in repo_ids])

        released = self.run_pmt(
            "lock", "release", "--repo", str(repo_a), "--repo", str(repo_b), session="multi"
        )
        self.assertEqual(released.stdout.splitlines(), [f"released {item}" for item in reversed(repo_ids)])

        self.run_pmt("lock", "acquire", "--repo", str(repo_b), session="blocker")
        failed = self.run_pmt(
            "lock",
            "acquire",
            "--repo",
            str(repo_b),
            "--repo",
            str(repo_a),
            session="contender",
            ok=False,
        )
        listed = self.run_pmt("lock", "list", session="viewer")
        locked_ids = {json.loads(line)["id"] for line in listed.stdout.splitlines()}

        self.assertEqual(failed.returncode, 1)
        self.assertNotIn(repo_ids[0], locked_ids)
        self.assertIn(repo_ids[1], locked_ids)

    def test_decide_supersedes_marks_old_row_replaced(self):
        slug = "decisions"
        self.run_pmt("new", slug, "--goal", "track decisions")
        first = self.run_pmt(
            "--project",
            slug,
            "decide",
            "Original choice",
            "--context",
            "x" * 301,
            "--decision",
            "use the first option",
        ).stdout.strip()
        second = self.run_pmt(
            "--project",
            slug,
            "decide",
            "Replacement choice",
            "--context",
            "new evidence",
            "--decision",
            "use the replacement",
            "--supersedes",
            first,
        ).stdout.strip()

        path = self.docs / "projects" / slug / "decisions.md"
        text = path.read_text(encoding="utf-8")
        resume = self.run_pmt("resume", slug).stdout
        old_detail = (self.docs / "projects" / slug / "decisions" / "D1.md").read_text(encoding="utf-8")
        rejected = self.run_pmt(
            "--project",
            slug,
            "decide",
            "Invalid replacement",
            "--context",
            "too late",
            "--decision",
            "cannot replace twice",
            "--supersedes",
            first,
            ok=False,
        )

        self.assertEqual(second, "D2")
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("| ID | 상태 | 생성 | 제목 | 내용 | 대체 |", text)
        self.assertRegex(text, r"\| D1 \| 대체 \| .* \| Original choice \|")
        self.assertRegex(text, r"\| D2 \| 승인 \| .* \| Replacement choice \| .* \| D1 \|")
        self.assertIn("status: 대체", old_detail)
        self.assertIn("Replacement choice", resume)
        self.assertNotIn("Original choice", resume)

    def test_decide_long_content_writes_file_and_links(self):
        slug = "long-decision"
        self.run_pmt("new", slug, "--goal", "store long decisions")
        decision_id = self.run_pmt(
            "--project",
            slug,
            "decide",
            "Long choice",
            "--context",
            "x" * 301,
            "--decision",
            "Keep the durable detail. Additional explanation follows.",
            "--alt",
            "use a short record",
            "--result",
            "full context remains available",
            "--decider",
            "reviewer",
        ).stdout.strip()

        project = self.docs / "projects" / slug
        row_text = (project / "decisions.md").read_text(encoding="utf-8")
        file_text = (project / "decisions" / f"{decision_id}.md").read_text(encoding="utf-8")

        self.assertIn(f"(전문: decisions/{decision_id}.md)", row_text)
        self.assertIn("status: 승인", file_text)
        self.assertIn("decider: reviewer", file_text)
        self.assertIn("## 문맥", file_text)
        self.assertIn("## 결정", file_text)
        self.assertIn("## 대안", file_text)
        self.assertIn("## 결과", file_text)

    def test_set_decision_revoked_and_file_synced(self):
        slug = "revoke-decision"
        self.run_pmt("new", slug, "--goal", "revoke decisions")
        decision_id = self.run_pmt(
            "--project",
            slug,
            "decide",
            "Revocable choice",
            "--context",
            "x" * 301,
            "--decision",
            "use the temporary choice",
        ).stdout.strip()

        self.run_pmt(
            "--project", slug, "set", decision_id, "--status", "폐기", "--why", "no longer valid"
        )
        project = self.docs / "projects" / slug
        rows = (project / "decisions.md").read_text(encoding="utf-8")
        detail = (project / "decisions" / f"{decision_id}.md").read_text(encoding="utf-8")

        self.assertRegex(rows, rf"\| {decision_id} \| 폐기 \|")
        self.assertIn("사유: no longer valid", rows)
        self.assertIn("status: 폐기", detail)

    def test_set_rejects_invalid_transition(self):
        slug, work, item = self.make_item(slug="invalid-transition")
        self.run_pmt("--project", slug, "add", "fact", "fact")
        self.run_pmt("--project", slug, "add", "backlog", "backlog", "--kind", "req")
        self.run_pmt(
            "--project",
            slug,
            "decide",
            "Decision",
            "--context",
            "context",
            "--decision",
            "choice",
        )

        invalid = self.run_pmt("--project", slug, "set", "F1", "--status", "Done", ok=False)
        missing = self.run_pmt("--project", slug, "set", "F99", "--status", "Closed", ok=False)
        mixed = self.run_pmt(
            "--project", slug, "set", item, "--status", "Done", "--blocked-by", "ext:vendor", ok=False
        )
        non_item = self.run_pmt(
            "--project", slug, "set", item, "--blocked-by", work, ok=False
        )
        missing_relation = self.run_pmt(
            "--project", slug, "set", item, "--blocked-by", f"{slug}/_default/Work99-1", ok=False
        )

        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(mixed.returncode, 2)
        self.assertEqual(non_item.returncode, 2)
        self.assertEqual(missing_relation.returncode, 2)

        project = self.docs / "projects" / slug
        facts = project / "facts.md"
        backlog = project / "backlog.md"
        decisions = project / "decisions.md"
        facts.write_text(facts.read_text(encoding="utf-8").replace("| F1 | Active |", "| F1 | Invalid |"), encoding="utf-8")
        backlog.write_text(backlog.read_text(encoding="utf-8").replace("| B1 | req | Active |", "| B1 | req | Invalid |"), encoding="utf-8")
        decisions.write_text(decisions.read_text(encoding="utf-8").replace("| D1 | 승인 |", "| D1 | Invalid |"), encoding="utf-8")
        doctor = self.run_pmt("--project", slug, "doctor", ok=False)

        self.assertEqual(doctor.returncode, 1)
        self.assertIn("facts.md: invalid status F1=Invalid", doctor.stdout)
        self.assertIn("backlog.md: invalid status B1=Invalid", doctor.stdout)
        self.assertIn("decisions.md: invalid status D1=Invalid", doctor.stdout)

    def test_set_blocked_by_hides_from_startable_and_done_unblocks(self):
        slug, work, first = self.make_item(slug="blocked-by")
        second = self.run_pmt("--project", slug, "add", "item", work, "Second").stdout.strip()
        self.run_pmt("--project", slug, "set", second, "--blocked-by", first)
        self.run_pmt("--project", slug, "set", second, "--blocked-by", first)
        before = self.run_pmt("resume", slug).stdout

        second_path = self.docs / "projects" / slug / "_default" / "Work1-2.md"
        self.assertEqual(second_path.read_text(encoding="utf-8").count(first), 1)
        self.assertNotIn(second, before)

        self.run_pmt("--project", slug, "start", first)
        self.run_pmt("--project", slug, "end", first, "--done", "--result", "unblock second")
        after = self.run_pmt("resume", slug).stdout
        worklog = self.docs / "worklog" / "done" / f"{slug}___default__Work1-1.md"

        self.assertIn("blocked_by: []", second_path.read_text(encoding="utf-8"))
        self.assertIn(second, after)
        self.assertIn(f"차단 해소: {second}", worklog.read_text(encoding="utf-8"))

        self.run_pmt("--project", slug, "set", second, "--blocked-by", "ext:vendor")
        self.assertEqual(self.run_pmt("--project", slug, "doctor").returncode, 0)
        self.run_pmt("--project", slug, "set", second, "--unblock", "ext:vendor")

    def test_find_chain_prints_supersede_sequence(self):
        slug = "decision-chain"
        self.run_pmt("new", slug, "--goal", "trace decisions")
        previous = None
        for title in ("First", "Second", "Third"):
            args = [
                "--project",
                slug,
                "decide",
                title,
                "--context",
                "context",
                "--decision",
                f"choose {title.lower()}",
            ]
            if previous:
                args.extend(["--supersedes", previous])
            previous = self.run_pmt(*args).stdout.strip()
        self.run_pmt("--project", slug, "set", "D3", "--status", "폐기")
        decisions = self.docs / "projects" / slug / "decisions.md"
        decisions.write_text(decisions.read_text(encoding="utf-8") + "x" * 8100, encoding="utf-8")
        self.run_pmt("--project", slug, "compact")

        result = self.run_pmt("--project", slug, "find", "D2", "--chain", "D2")
        date = dt.date.today().isoformat()

        self.assertEqual(
            result.stdout.strip(),
            f"D1(대체, {date}) First → D2(대체, {date}) Second → D3(폐기, {date}) Third",
        )
        self.assertIn("| D1 |", (self.docs / "projects" / slug / "archive" / "decisions.md").read_text(encoding="utf-8"))

    def test_auto_compact_on_done_moves_only_terminal_rows(self):
        slug, _work, item = self.make_item(slug="auto-compact")
        self.run_pmt("--project", slug, "add", "fact", "terminal fact")
        self.run_pmt("--project", slug, "set", "F1", "--status", "Closed")
        self.run_pmt("--project", slug, "add", "fact", "active fact")
        project = self.docs / "projects" / slug
        facts = project / "facts.md"
        facts.write_text(
            facts.read_text(encoding="utf-8").replace("active fact", "x" * 8200),
            encoding="utf-8",
        )

        self.run_pmt("--project", slug, "start", item)
        self.run_pmt("--project", slug, "end", item, "--done", "--result", "trigger compact")

        active_facts = facts.read_text(encoding="utf-8")
        archived_facts = (project / "archive" / "facts.md").read_text(encoding="utf-8")
        self.assertNotIn("| F1 |", active_facts)
        self.assertIn("| F2 | Active |", active_facts)
        self.assertIn("| ID | 상태 | 생성 | 내용 |", archived_facts)
        self.assertIn("| F1 | Closed |", archived_facts)
        self.assertNotIn("| F2 |", archived_facts)

        self.run_pmt("--project", slug, "add", "backlog", "terminal backlog", "--kind", "todo")
        self.run_pmt("--project", slug, "set", "B1", "--status", "Done")
        self.run_pmt("--project", slug, "add", "backlog", "active backlog", "--kind", "todo")
        backlog = project / "backlog.md"
        backlog.write_text(
            backlog.read_text(encoding="utf-8").replace("active backlog", "y" * 8200),
            encoding="utf-8",
        )
        self.run_pmt("--project", slug, "lock", "acquire", "__list-backlog.md", session="other")
        skipped = self.run_pmt("resume", slug)
        self.assertIn("목록 압축 건너뜀", skipped.stderr)
        self.assertIn("| B1 | todo | Done |", backlog.read_text(encoding="utf-8"))
        self.run_pmt("--project", slug, "lock", "release", "__list-backlog.md", session="other")
        self.run_pmt("resume", slug)
        self.assertIn(
            "| B1 | todo | Done |",
            (project / "archive" / "backlog.md").read_text(encoding="utf-8"),
        )

    def test_parallel_sync_writes_resume_and_doctor_passes(self):
        slug, _work, _item = self.make_item()
        barrier = threading.Barrier(4)
        results = []

        def run_sync(index):
            barrier.wait()
            results.append(self.run_pmt("--project", slug, "sync", session=f"sync-{index}", ok=False))

        threads = [threading.Thread(target=run_sync, args=(index,)) for index in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual([proc.returncode for proc in results], [0, 0, 0, 0])
        self.assertTrue((self.docs / "projects" / slug / "RESUME.md").exists())
        self.assertEqual(self.run_pmt("--project", slug, "doctor").returncode, 0)


if __name__ == "__main__":
    unittest.main()
