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
        facts = self.docs / "projects" / slug / "facts.md"
        with facts.open("a", encoding="utf-8") as fh:
            for i in range(80):
                fh.write(f"| F{i + 2} | Done | 2026-09-02 | filler {'x' * 120} |\n")

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
        self.run_pmt("--project", slug, "start", parent)
        rejected = self.run_pmt(
            "--project", slug, "end", parent, "--skip", "--reason", "obsolete", ok=False
        )
        self.assertEqual(rejected.returncode, 2)

        self.run_pmt("--project", slug, "start", child)
        self.run_pmt("--project", slug, "end", child, "--skip", "--reason", "obsolete")
        self.assertTrue((self.docs / "projects" / slug / "canceled" / "_default__Work1-1-1.md").exists())
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
