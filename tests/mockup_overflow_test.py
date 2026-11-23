"""溢出检查：干净页通过；框内多出几像素只提示；多得明显或撑破页面算失败。没有 Chrome / Node 22 时跳过。"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "skills/mockup/scripts/check-overflow.py"
PAGE = ('<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<style>body{margin:0;font:16px system-ui}</style></head><body>%s</body></html>')


def node_ok():
    node = shutil.which("node")
    if not node:
        return False
    out = subprocess.run([node, "-p", "process.versions.node.split('.')[0]"], capture_output=True, text=True).stdout.strip()
    return out.isdigit() and int(out) >= 22


HAS_BROWSER = node_ok() and any(shutil.which(n) for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"))


@unittest.skipUnless(HAS_BROWSER, "需要 Chrome 和 Node 22 以上")
class OverflowTest(unittest.TestCase):
    def run_page(self, body):
        d = Path(tempfile.mkdtemp(prefix="wfs-ov-"))
        page = d / "p.html"
        page.write_text(PAGE % body, encoding="utf-8")
        return subprocess.run([sys.executable, str(TOOL), str(page), "--widths=390", "--no-sandbox"], capture_output=True, text=True, timeout=120)

    def test_clean_page_passes(self):
        self.assertEqual(self.run_page("<p>正常</p>").returncode, 0)

    def test_small_inner_overflow_is_only_a_note(self):
        r = self.run_page('<div style="width:100px"><div style="width:105px;height:10px">多出五像素</div></div>')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("note", r.stderr)
        self.assertIn("多出五像素", r.stderr)

    def test_large_inner_overflow_fails_and_names_the_text(self):
        r = self.run_page('<div style="width:100px"><div style="width:140px;height:10px">多出四十像素</div></div>')
        self.assertEqual(r.returncode, 1)
        self.assertIn("多出四十像素", r.stderr)

    def test_page_overflow_fails(self):
        r = self.run_page('<div style="width:3000px">撑破整页</div>')
        self.assertEqual(r.returncode, 1)
        self.assertIn("撑破页面", r.stderr)


if __name__ == "__main__":
    unittest.main()
