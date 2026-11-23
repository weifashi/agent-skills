"""高保真组件库自检：写入页面、只带用到的图标、重复跑不变、缺图标报错、没有外部资源；可点原型的脚本写入和规矩检查。"""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIFI = ROOT / "skills/mockup/assets/hifi"
GALLERY = ROOT / "skills/mockup/assets/hifi.html"

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>t</title></head>
<body>
<div class="hf-phone"><svg class="hf-i"><use href="#i-printer"/></svg><svg viewBox="0 0 29 29"><use href="#qr-a"/></svg></div>
<div class="mmd"><svg viewBox="0 0 10 10"><path d="M0 0"/></svg></div>
</body></html>
"""


def inline(path, *extra):
    return subprocess.run([sys.executable, str(HIFI / "inline.py"), str(path), *extra],
                          capture_output=True, text=True, timeout=60)


class InlineTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="wfs-hifi-"))
        self.page = self.dir / "index.html"
        self.page.write_text(PAGE, encoding="utf-8")

    def test_inline_only_used_and_idempotent(self):
        r = inline(self.page)
        self.assertEqual(r.returncode, 0, r.stderr)
        first = self.page.read_text(encoding="utf-8")
        self.assertEqual(first.count("<style data-hifi>"), 1)
        self.assertEqual(first.count("<svg data-hifi-icons"), 1)
        icons = re.search(r"<svg data-hifi-icons.*?</svg>", first, re.S).group(0)
        self.assertEqual(sorted(re.findall(r'<symbol id="([\w-]+)"', icons)), ["i-printer", "qr-a"])
        self.assertIn('<div class="mmd"><svg viewBox="0 0 10 10"><path d="M0 0"/></svg></div>', first)
        inline(self.page)
        self.assertEqual(self.page.read_text(encoding="utf-8"), first)

    def test_page_own_icons_are_kept_not_missing(self):
        own = '<svg style="display:none"><symbol id="i-own" viewBox="0 0 24 24"><path d="M1 1h2"/></symbol></svg>'
        self.page.write_text(PAGE.replace("<body>", "<body>\n" + own).replace("#i-printer", "#i-own"), encoding="utf-8")
        r = inline(self.page)
        self.assertEqual(r.returncode, 0, r.stderr)
        html = self.page.read_text(encoding="utf-8")
        icons = re.search(r"<svg data-hifi-icons.*?</svg>", html, re.S).group(0)
        self.assertEqual(re.findall(r'<symbol id="([\w-]+)"', icons), ["qr-a"])  # 页面自己有的 i-own 不再补
        self.assertIn(own, html)
        inline(self.page)
        self.assertEqual(self.page.read_text(encoding="utf-8"), html)

    def test_missing_icon_fails_without_change(self):
        self.page.write_text(PAGE.replace("#i-printer", "#i-not-there"), encoding="utf-8")
        before = self.page.read_text(encoding="utf-8")
        r = inline(self.page)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("i-not-there", r.stderr + r.stdout)
        self.assertEqual(self.page.read_text(encoding="utf-8"), before)


PROTO = """<!doctype html><html><head><meta charset="utf-8"><title>p</title></head><body>
<div class="hf-proto">
<section class="hf-ps" data-screen="a" data-end="收银机" data-entry data-title="收银台"><div class="hf-phone"><span class="hf-btn" data-go="b">扫码</span></div><div class="hf-pnote"><p>收银员选收款方式</p></div></section>
<section class="hf-ps" data-screen="b" data-end="收银机" data-title="扫码"><div class="hf-phone"><span class="hf-btn" data-go="a">取消</span><span data-go="c">去老板手机</span></div><div class="hf-pnote"><p>顾客扫码付款</p></div></section>
<section class="hf-ps" data-screen="c" data-end="老板手机" data-entry data-title="首页"><div class="hf-phone"><span data-go="a">回收银台</span></div><div class="hf-pnote"><p>老板看今天卖了多少</p></div></section>
</div>
</body></html>
"""


class ProtoTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="wfs-proto-"))
        self.page = self.dir / "index.html"

    def test_script_written_once_only_when_used(self):
        self.page.write_text(PROTO, encoding="utf-8")
        self.assertEqual(inline(self.page).returncode, 0)
        first = self.page.read_text(encoding="utf-8")
        self.assertEqual(first.count("<script data-hifi-proto>"), 1)
        self.assertLess(first.index("<script data-hifi-proto>"), first.index("</body>"))
        inline(self.page)
        self.assertEqual(self.page.read_text(encoding="utf-8"), first)
        self.page.write_text(PAGE, encoding="utf-8")
        inline(self.page)
        self.assertNotIn("data-hifi-proto", self.page.read_text(encoding="utf-8"))

    def test_script_lands_before_body_end_with_dotted_i(self):
        # 土耳其文的 İ 转小写后变成两个字符：不能拿转小写后的位置去切原文
        html = PROTO.replace("<p>老板看今天卖了多少</p>", "<p>İstanbul İzmir 老板看今天卖了多少</p>")
        self.page.write_text(html, encoding="utf-8")
        self.assertEqual(inline(self.page).returncode, 0)
        out = self.page.read_text(encoding="utf-8")
        self.assertIn("</script>\n</body>", out)
        self.assertRegex(out, r"</script>\n</body></html>\n?$")

    def test_bad_prototypes_fail_without_change(self):
        unreachable = PROTO.replace("</div>\n</body>", '<section class="hf-ps" data-screen="d" data-end="老板手机" data-title="日报"><div class="hf-phone"></div><div class="hf-pnote"><p>没有地方连过来</p></div></section>\n</div>\n</body>')
        cases = {
            "缺说明": (PROTO.replace('<div class="hf-pnote"><p>顾客扫码付款</p></div>', ""), "缺说明"),
            "缺标题": (PROTO.replace(' data-title="扫码"', ""), "缺 data-title"),
            "跳转目标不存在": (PROTO.replace('data-go="c"', 'data-go="zz"'), "指向不存在的屏"),
            "端没有入口": (PROTO.replace(' data-entry data-title="首页"', ' data-title="首页"'), "恰好一个入口"),
            "端有两个入口": (PROTO.replace('data-end="收银机" data-title="扫码"', 'data-end="收银机" data-entry data-title="扫码"'), "恰好一个入口"),
            "点不到的屏": (unreachable, "从入口点不到"),
            "屏重复": (PROTO.replace('data-screen="b"', 'data-screen="a"').replace('data-go="b"', 'data-go="a"'), "重复了"),
        }
        for name, (html, why) in cases.items():
            with self.subTest(name):
                self.page.write_text(html, encoding="utf-8")
                r = inline(self.page)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(why, r.stderr + r.stdout)
                self.assertEqual(self.page.read_text(encoding="utf-8"), html)


class GalleryTest(unittest.TestCase):
    def test_gallery_inline_blocks_are_current(self):
        # 改了 kit.css / proto.js / icons.svg 却没对展示页重跑 inline.py，这里会失败
        tmp = Path(tempfile.mkdtemp(prefix="wfs-gallery-")) / "hifi.html"
        tmp.write_text(GALLERY.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertEqual(inline(tmp).returncode, 0)
        self.assertEqual(tmp.read_text(encoding="utf-8"), GALLERY.read_text(encoding="utf-8"))

    def test_gallery_self_contained(self):
        html = GALLERY.read_text(encoding="utf-8")
        # 资源加载一律内联：不许外链样式、脚本、图片、字体（<a href> 是导航，不算）
        bad = re.findall(r'<(?:link|script|img|iframe|source)\b[^>]*(?:src|href)="https?://', html)
        self.assertEqual(bad, [])
        self.assertNotRegex((HIFI / "kit.css").read_text(encoding="utf-8"), r"url\(\s*['\"]?https?:")
        defined = set(re.findall(r'<symbol id="([\w-]+)"', html))
        used = set(re.findall(r'href="#((?:i|qr)-[\w-]+)"', html))
        self.assertTrue(used)
        self.assertEqual(sorted(used - defined), [])

    def test_sprite_is_shapes_only(self):
        sprite = (HIFI / "icons.svg").read_text(encoding="utf-8")
        tags = set(re.findall(r"<([a-z]+)\b", sprite))
        self.assertTrue(tags <= {"svg", "symbol", "path", "circle", "rect", "line", "polyline", "polygon", "ellipse"}, tags)
        self.assertNotIn("<script", sprite)
        self.assertNotRegex(sprite, r"\son\w+=")


if __name__ == "__main__":
    unittest.main()
