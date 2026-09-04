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
