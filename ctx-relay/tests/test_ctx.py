import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CTX = ROOT / "scripts" / "ctx.py"

TASKS = """# TASKS
plan: ship login

- [x] T1 Write tests
  files: src/a.test.ts
  do: add tests
  verify: npm test -- a
- [ ] T2 Implement validator
  files: src/a.ts
  do: implement validateEmail.
    Trim input first.
  verify: npm test -- a
"""

NOW = {
    "task": "T2",
    "status": "active",
    "did": "added function",
    "next": "handle empty string",
    "fails": "0",
    "blocked": "-",
}


def state(notes=("use snake_case",), **over):
    now = dict(NOW)
    now.update(over)
    body = "\n".join("%s: %s" % (k, now[k]) for k in NOW if now[k] is not None)
    lines = "\n".join("- " + n for n in notes)
    return "# STATE\ngoal: ship login\nupdated: 2026-09-23 14:10\n\n## now\n%s\n\n## notes\n%s\n" % (body, lines)


class CtxTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_ctx(self, *args, script=CTX, cwd=None):
        proc = subprocess.run([sys.executable, str(script)] + list(args), cwd=str(cwd or self.repo),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        return proc.returncode, proc.stdout + proc.stderr

    def init(self):
        code, out = self.run_ctx("init", "--root", str(self.repo), "--goal", "ship login")
        self.assertEqual(code, 0, out)
        return out

    def write(self, name, text):
        (self.repo / ".ctx" / name).write_text(text, encoding="utf-8")

    def check_fails(self, expected, state_text=None, tasks_text=TASKS):
        if not (self.repo / ".ctx").is_dir():
            self.init()
        self.write("TASKS.md", tasks_text)
        self.write("STATE.md", state_text if state_text is not None else state())
        code, out = self.run_ctx("check", "--root", str(self.repo))
        self.assertEqual(code, 1, out)
        self.assertIn(expected, out)

    def test_init_creates_valid_relay(self):
        out = self.init()
        for name in ("STATE.md", "TASKS.md", "LOG.md", "ctx.py"):
            self.assertTrue((self.repo / ".ctx" / name).is_file(), name)
        self.assertIn("ctx check: OK | status idle | task - | open 0", out)
        agents = (self.repo / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(agents.count("<!-- ctx-relay:start -->"), 1)

    def test_init_is_idempotent_and_keeps_existing_content(self):
        (self.repo / "AGENTS.md").write_text("# Rules\nBe nice.\n", encoding="utf-8")
        self.init()
        self.write("TASKS.md", TASKS)
        out = self.init()
        self.assertIn("kept    .ctx/TASKS.md", out)
        self.assertEqual((self.repo / ".ctx" / "TASKS.md").read_text(encoding="utf-8"), TASKS)
        agents = (self.repo / "AGENTS.md").read_text(encoding="utf-8")
        self.assertTrue(agents.startswith("# Rules\nBe nice.\n"))
        self.assertEqual(agents.count("<!-- ctx-relay:start -->"), 1)

    def test_copied_script_finds_repo_from_any_cwd(self):
        self.init()
        sub = self.repo / "src" / "deep"
        sub.mkdir(parents=True)
        code, out = self.run_ctx("check", script=self.repo / ".ctx" / "ctx.py", cwd=sub)
        self.assertEqual(code, 0, out)
        code, out = self.run_ctx("check", cwd=sub)
        self.assertEqual(code, 0, out)

    def test_active_state_passes(self):
        self.init()
        self.write("TASKS.md", TASKS)
        self.write("STATE.md", state())
        code, out = self.run_ctx("check", "--root", str(self.repo))
        self.assertEqual(code, 0, out)
        self.assertIn("status active | task T2 | open 1 | done 1 | blocked 0", out)

    def test_blocked_state_passes(self):
        self.init()
        self.write("TASKS.md", TASKS.replace("- [ ] T2", "- [!] T2"))
        self.write("STATE.md", state(status="blocked", fails="2", blocked="needs src/b.ts"))
        code, out = self.run_ctx("check", "--root", str(self.repo))
        self.assertEqual(code, 0, out)

    def test_missing_ctx_exits_2(self):
        code, out = self.run_ctx("check", "--root", str(self.repo))
        self.assertEqual(code, 2, out)

    def test_state_errors(self):
        cases = [
            ('status "working" invalid', state(status="working")),
            ("fails reached 2", state(fails="2")),
            ('"fails:" must be a whole number', state(fails="two")),
            ('missing "next:" line', state(next=None)),
            ('"did:" is empty', state(did="")),
            ('"did:" is 301 chars', state(did="x" * 301)),
            ('status is idle, so "task:" must be "-"', state(status="idle")),
            ("task T9 is not in TASKS.md", state(task="T9")),
            ('status is blocked, so "blocked:" must say why', state(status="blocked")),
            ("TASKS must mark it [!]", state(status="blocked", blocked="stuck")),
            ("6 notes, max 5", state(notes=["n"] * 6)),
            ("note is 201 chars", state(notes=["n" * 201])),
            ('unknown heading "## plan"', state() + "\n## plan\n"),
            ('unknown key "owner"', state().replace("fails: 0", "fails: 0\nowner: me")),
            ('use "YYYY-MM-DD HH:MM"', state().replace("2026-09-23 14:10", "today")),
            ("chars, max 3000", state(notes=["n" * 199] * 5) + "x" * 2500),
        ]
        for expected, text in cases:
            with self.subTest(expected=expected):
                self.check_fails(expected, state_text=text)

    def test_active_task_must_be_open(self):
        self.check_fails("TASKS marks it [x]", state_text=state(task="T1"))

    def test_task_errors(self):
        cases = [
            ("duplicate task id T2", TASKS + "- [ ] T2 Again\n  files: a\n  do: b\n  verify: c\n"),
            ('T2 has no "verify:" line', "".join(TASKS.rsplit("  verify: npm test -- a\n", 1))),
            ("malformed task line", TASKS + "- [X] T3 Bad marker\n"),
            ("unexpected top-level text", TASKS + "random note\n"),
            ('missing "plan: <one line>"', TASKS.replace("plan: ship login\n", "")),
            ("chars, max 12000", TASKS + "#" * 12001),
        ]
        for expected, tasks_text in cases:
            with self.subTest(expected=expected):
                self.check_fails(expected, tasks_text=tasks_text)

    def test_blocked_task_without_blocked_state_warns(self):
        self.init()
        self.write("TASKS.md", TASKS + "- [!] T3 Stuck\n  files: a\n  do: b\n  verify: c\n")
        self.write("STATE.md", state())
        code, out = self.run_ctx("check", "--root", str(self.repo))
        self.assertEqual(code, 0, out)
        self.assertIn("WARN .ctx/TASKS.md", out)


if __name__ == "__main__":
    unittest.main()
