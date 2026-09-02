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
            "--session",
            session,
            *args,
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True)
        if ok and proc.returncode != 0:
            self.fail(f"{cmd} failed\nstdout={proc.stdout}\nstderr={proc.stderr}")
        return proc

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
        lock_meta = next((self.docs / "projects" / slug / ".locks").glob("*.lock/lock.json"))
        data = json.loads(lock_meta.read_text(encoding="utf-8"))
        data["heartbeat"] = "2000-01-01T00:00:00"
        lock_meta.write_text(json.dumps(data), encoding="utf-8")

        self.run_pmt("--project", slug, "lock", "reap", item, session="new")
        resume = self.run_pmt("resume", slug, session="new").stdout

        self.assertIn("last durable checkpoint", resume)
        self.assertIn("비정상 종료 추정", resume)

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
        facts = self.docs / "projects" / slug / "facts.md"
        with facts.open("a", encoding="utf-8") as fh:
            for i in range(80):
                fh.write(f"| F{i + 2} | Done | 2026-09-02 | filler {'x' * 120} |\n")

        before = self.run_pmt("--project", slug, "find", "F1").stdout
        self.run_pmt("--project", slug, "compact")
        after = self.run_pmt("--project", slug, "find", "F1").stdout

        self.assertIn(target, before)
        self.assertIn("F1", before)
        self.assertIn(target, before)
        self.assertIn("F1", after)
        self.assertIn(target, after)
        self.assertIn("archive", after)

    def test_migrate_v1_dry_run_is_read_only_and_apply_maps_progress_notes(self):
        slug = "legacy"
        project = self.docs / "projects" / slug
        item_dir = project / "_default"
        item_dir.mkdir(parents=True)
        work = item_dir / "Work1.md"
        work.write_text(
            "---\n"
            "type: work\n"
            "id: legacy/_default/Work1\n"
            "parent: legacy/_default\n"
            "status: In Progress\n"
            "updated: 2026-09-02\n"
            "---\n"
            "# Work1 legacy\n"
            "## Goal\n"
            "- migrate\n",
            encoding="utf-8",
        )
        item = item_dir / "Work1-J1.md"
        item.write_text(
            "---\n"
            "type: item\n"
            "id: legacy/_default/Work1-J1\n"
            "parent: legacy/_default/Work1\n"
            "status: In Progress\n"
            "updated: 2026-09-02\n"
            "---\n"
            "# J1 legacy\n"
            "## 진행 메모\n"
            "- 한 것: old did\n"
            "- 다음: old next\n",
            encoding="utf-8",
        )
        before = item.read_text(encoding="utf-8")

        self.run_pmt("migrate", "v1", slug)
        self.assertEqual(before, item.read_text(encoding="utf-8"))

        self.run_pmt("migrate", "v1", slug, "--apply")
        migrated = item.read_text(encoding="utf-8")
        self.assertIn("kind: job", migrated)
        self.assertIn("## 재개", migrated)
        self.assertIn("old did", migrated)

    def test_migrate_v1_merges_lists_handoffs_worklogs_and_refs_losslessly(self):
        slug = "legacyfull"
        project = self.docs / "projects" / slug
        item_dir = project / "_default"
        item_dir.mkdir(parents=True)
        (project / "project.md").write_text(
            "---\ntype: project\nid: legacyfull\nstatus: Planned\nupdated: 2026-09-02\n---\n"
            "# legacyfull\n## Goal\n- migrate all v1 data\n## Non-Goal\n-\n## 결과\n-\n",
            encoding="utf-8",
        )
        (item_dir / "Work1.md").write_text(
            "---\ntype: work\nid: legacyfull/_default/Work1\nparent: legacyfull/_default\n"
            "status: In Progress\nupdated: 2026-09-02\n---\n# Work1\n## Goal\n- migrate\n",
            encoding="utf-8",
        )
        item = item_dir / "Work1-J1.md"
        item.write_text(
            "---\ntype: item\nid: legacyfull/_default/Work1-J1\n"
            "parent: legacyfull/_default/Work1\nstatus: In Progress\nupdated: 2026-09-02\n"
            "list_refs: [requirements.md#R7, Information.md#IF2]\n---\n"
            "# J1\n## 진행 메모\n- 한 것: legacy work\n- 다음: migrate\n",
            encoding="utf-8",
        )
        legacy_lists = {
            "Information.md": "# Information\n| ID | 상태 | 생성 | 내용 |\n|---|---|---|---|\n| IF2 | Done | 2026-08-01 | durable fact |\n",
            "histories.md": "# Histories\n| ID | 상태 | 생성 | 내용 |\n|---|---|---|---|\n| H4 | Done | 2026-08-02 | durable decision |\n",
            "requirements.md": "# Requirements\n| ID | 상태 | 생성 | 내용 |\n|---|---|---|---|\n| R7 | In Progress | 2026-08-03 | required behavior |\n",
            "todos.md": "# Todos\n| ID | 상태 | 생성 | 내용 |\n|---|---|---|---|\n| T3 | Planned | 2026-08-04 | follow-up work |\n",
            "plans.md": "# Plans\n| ID | 상태 | 생성 | 내용 |\n|---|---|---|---|\n| P2 | Done | 2026-08-05 | rollout plan |\n",
            "issues.md": "# Issues\n| ID | 상태 | 생성 | 내용 |\n|---|---|---|---|\n| I8 | Active | 2026-08-06 | open issue |\n",
            "Bugs.md": "# Bugs\n| ID | 상태 | 생성 | 내용 |\n|---|---|---|---|\n| BG9 | Active | 2026-08-07 | bad edge |\n\n## 점검 특징\n- restart-sensitive\n",
        }
        for name, content in legacy_lists.items():
            (project / name).write_text(content, encoding="utf-8")
        (project / "works.md").write_text("legacy generated index", encoding="utf-8")
        (project / "classifications.md").write_text("legacy class index", encoding="utf-8")

        handoff = self.docs / "handoff-legacyfull-Work1-J1.md"
        handoff.write_text(
            "target legacyfull/_default/Work1-J1\ncritical handoff warning",
            encoding="utf-8",
        )
        worklog = self.docs / "worklog" / "legacyfull_Work1-J1.md"
        worklog.parent.mkdir(parents=True)
        worklog.write_text("# log\nlegacyfull/_default/Work1-J1\n- work happened\n", encoding="utf-8")

        result = self.run_pmt("migrate", "v1", slug, "--apply")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in legacy_lists:
            self.assertFalse((project / name).exists(), name)
        backlog = (project / "backlog.md").read_text(encoding="utf-8")
        self.assertIn("[R7] required behavior", backlog)
        self.assertIn("[T3] follow-up work", backlog)
        self.assertIn("[BG9] bad edge", backlog)
        self.assertIn("restart-sensitive", backlog)
        self.assertIn("[IF2] durable fact", (project / "facts.md").read_text(encoding="utf-8"))
        self.assertIn("[H4] durable decision", (project / "decisions.md").read_text(encoding="utf-8"))
        migrated_item = item.read_text(encoding="utf-8")
        self.assertRegex(migrated_item, r"list_refs: \[backlog\.md#B\d+, facts\.md#F\d+\]")
        self.assertIn("critical handoff warning", migrated_item)
        self.assertTrue((project / "resources" / "derived" / "handoff-archive" / handoff.name).exists())
        self.assertTrue((self.docs / "worklog" / "legacyfull___default__Work1-J1.md").exists())
        self.assertFalse((project / "works.md").exists())
        self.assertFalse((project / "classifications.md").exists())
        self.assertEqual(self.run_pmt("--project", slug, "doctor").returncode, 0)

    def test_migrate_v1_warns_and_preserves_unresolved_handoff(self):
        slug, _work, _item = self.make_item(slug="ambiguous")
        handoff = self.docs / "handoff-ambiguous-unknown.md"
        handoff.write_text("ambiguous project handoff with no item id", encoding="utf-8")

        result = self.run_pmt("migrate", "v1", slug, "--apply")

        self.assertIn("WARN migration: unresolved handoff preserved", result.stdout)
        self.assertTrue(handoff.exists())

    def test_validate_skill_passes_and_can_run_tests(self):
        proc = subprocess.run([sys.executable, str(VALIDATE), str(ROOT)], text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

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
        self.run_pmt("--project", slug, "start", parent)
        rejected = self.run_pmt(
            "--project", slug, "end", parent, "--skip", "--reason", "obsolete", ok=False
        )
        self.assertEqual(rejected.returncode, 2)

        self.run_pmt("--project", slug, "start", child)
        self.run_pmt("--project", slug, "end", child, "--skip", "--reason", "obsolete")
        self.assertTrue((self.docs / "projects" / slug / "canceled" / "Work1-1-1.md").exists())
        self.assertEqual(self.run_pmt("--project", slug, "doctor").returncode, 0)

    def test_start_prints_related_worklog_followup_impacts(self):
        slug, work, first = self.make_item()
        second = self.run_pmt("--project", slug, "add", "item", work, "Second").stdout.strip()
        self.run_pmt("--project", slug, "start", first)
        log = self.docs / "worklog" / "alpha___default__Work1-1.md"
        with log.open("a", encoding="utf-8") as handle:
            handle.write("- 후속 영향: parser API changed\n")
        self.run_pmt("--project", slug, "end", first, "--done", "--result", "done")

        started = self.run_pmt("--project", slug, "start", second)
        self.assertIn("parser API changed", started.stdout)

    def test_parallel_sync_waits_and_graph_has_no_virtual_class_orphan(self):
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
        graph = json.loads((self.docs / "projects" / slug / "graph.json").read_text(encoding="utf-8"))
        self.assertIn(f"{slug}/_default/Work1", graph["nodes"])
        self.assertNotIn(f"{slug}/_default/Work1", self.run_pmt("--project", slug, "graph", "orphans").stdout)


if __name__ == "__main__":
    unittest.main()
