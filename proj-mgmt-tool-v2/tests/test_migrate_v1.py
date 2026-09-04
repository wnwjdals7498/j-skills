import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PMT = ROOT / "scripts" / "pmt.py"
MIGRATE = ROOT / "scripts" / "migrate_v1.py"
SESSION = "test-session"


class MigrateV1Test(unittest.TestCase):
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

    def run_migrate(self, *args, session=SESSION, ok=True):
        cmd = [
            sys.executable,
            str(MIGRATE),
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

        self.run_migrate(slug)
        self.assertEqual(before, item.read_text(encoding="utf-8"))

        self.run_migrate(slug, "--apply")
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

        result = self.run_migrate(slug, "--apply")
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

        result = self.run_migrate(slug, "--apply")

        self.assertIn("WARN migration: unresolved handoff preserved", result.stdout)
        self.assertTrue(handoff.exists())


if __name__ == "__main__":
    unittest.main()
