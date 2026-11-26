import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_post.py"

HEADER = '---\ntitle: "t"\ntags: [a, b]\nsummary: "s"\n---\n\n'
PROSE = "".join(f"문장 {i}입니다.\n" for i in range(60))
CODE = "```bash\necho 10.0.0.1 내부\n```\n"


def run(body: str, *extra: str):
    with tempfile.TemporaryDirectory() as tmp:
        post = Path(tmp) / "post.md"
        post.write_text(body, encoding="utf-8")
        deny = Path(tmp) / "deny.txt"
        deny.write_text("# comment\nAcmeCorp\n", encoding="utf-8")
        args = [a.replace("{deny}", str(deny)) for a in extra]
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(post), *args],
            capture_output=True,
            text=True,
        )


class CheckPostTest(unittest.TestCase):
    def test_clean_post_passes(self):
        r = run(HEADER + PROSE)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("오류 0건", r.stdout)

    def test_hanja_fails(self):
        r = run(HEADER + PROSE + "보안 " + chr(0x6AA2) + chr(0x67FB) + "\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("한자", r.stdout)

    def test_emoji_fails(self):
        r = run(HEADER + PROSE + "완료 \U0001F680\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("이모지", r.stdout)

    def test_ip_in_code_fails(self):
        r = run(HEADER + PROSE + CODE)
        self.assertEqual(r.returncode, 1)
        self.assertIn("IPv4 '10.0.0.1'", r.stdout)

    def test_version_number_is_not_ip(self):
        r = run(HEADER + PROSE + "actionlint 1.7.12 와 v1.0.290\n")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_deny_file_and_flag(self):
        r = run(HEADER + PROSE + "acmecorp 레포\nsecret-host\n", "--deny-file", "{deny}", "--deny", "secret-host")
        self.assertEqual(r.returncode, 1)
        self.assertIn("금지어 'AcmeCorp'", r.stdout)
        self.assertIn("금지어 'secret-host'", r.stdout)

    def test_unbalanced_fence_fails(self):
        r = run(HEADER + PROSE + "```bash\necho hi\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("짝이 맞지 않음", r.stdout)

    def test_missing_front_matter_key_fails(self):
        r = run('---\ntitle: "t"\n---\n' + PROSE)
        self.assertEqual(r.returncode, 1)
        self.assertIn("'tags' 없음", r.stdout)
        self.assertIn("'summary' 없음", r.stdout)

    def test_long_prose_warns_only(self):
        r = run(HEADER + PROSE * 3)
        self.assertEqual(r.returncode, 0)
        self.assertIn("WARN", r.stdout)

    def test_code_lines_not_counted_as_prose(self):
        code = "```text\n" + "x\n" * 500 + "```\n"
        r = run(HEADER + PROSE + code)
        self.assertNotIn("초과", r.stdout)


if __name__ == "__main__":
    unittest.main()
