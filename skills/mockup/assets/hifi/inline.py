#!/usr/bin/env python3
"""把高保真组件库塞进页面：<style data-hifi> 放样式，<svg data-hifi-icons> 只放页面用到的图标；
页面用了可点原型（.hf-proto）时，再加一块 <script data-hifi-proto>（proto.js）。

用法：python3 inline.py <page.html> [<page2.html> ...] [--all-icons]
- 重复跑结果不变：已有这几块就整块替换，没有就插入（样式放 </head> 前，图标放 <body> 后，脚本放 </body> 前）。
- 只动这几块，不碰页面其它内容（包括已渲染的 Mermaid SVG）。
- 页面自己的图标表里已经有的图标（<symbol id="i-…">）照用页面的，不从组件库补。
- 页面引用了两边都没有的图标、或可点原型不合规矩（见 proto_problems）：报错退出 1，页面不改。
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STYLE_RE = re.compile(r"<style data-hifi>.*?</style>\n?", re.S)
ICONS_RE = re.compile(r"<svg data-hifi-icons\b.*?</svg>\n?", re.S)
PROTO_RE = re.compile(r"<script data-hifi-proto>.*?</script>\n?", re.S)
SCREEN_RE = re.compile(r"<section\b([^>]*\bdata-screen=\"([^\"]+)\"[^>]*)>(.*?)</section>", re.S)
GO_RE = re.compile(r'\bdata-go="([^"]+)"')
BODY_END = re.compile(r"</body\s*>", re.I)  # 不能用 lower() 后的位置：土耳其文 İ 转小写会变成两个字符
SYMBOL_RE = re.compile(r'<symbol id="([\w-]+)".*?</symbol>', re.S)
USE_RE = re.compile(r'(?:xlink:)?href="#((?:i|qr)-[\w-]+)"')


def proto_problems(body: str) -> list:
    """可点原型的规矩：每屏有标题和说明、跳转目标都存在、每个端恰好一个入口、每屏都能从入口点到。"""
    screens = [(m.group(2), m.group(1), m.group(3)) for m in SCREEN_RE.finditer(body)]
    if not screens:
        return ['用了 .hf-proto，但没有 <section data-screen="…"> 屏']
    out, attrs_of, ends, edges = [], {}, {}, {}
    for sid, attrs, inner in screens:
        if sid in attrs_of:
            out.append(f"屏 {sid} 重复了")
        attrs_of[sid] = attrs
        end = (re.search(r'\bdata-end="([^"]*)"', attrs) or [None, "界面"])[1]
        ends.setdefault(end, []).append(sid)
        if not re.search(r'\bdata-title="[^"]+"', attrs):
            out.append(f"屏 {sid} 缺 data-title（说明栏的标题）")
        i = inner.find("hf-pnote")
        if i < 0 or len(re.sub(r"<[^>]+>", "", inner[i:]).strip()) < 4:
            out.append(f'屏 {sid} 缺说明：加 <div class="hf-pnote">…</div>，写这一屏做什么、看到什么、有什么规则')
        edges[sid] = GO_RE.findall(inner)
    for sid, targets in edges.items():
        out += [f'屏 {sid} 里 data-go="{to}" 指向不存在的屏' for to in targets if to not in attrs_of]
    entries = []
    for end, members in ends.items():
        mark = [s for s in members if re.search(r"\bdata-entry\b", attrs_of[s])]
        if len(mark) != 1:
            out.append(f"端「{end}」要恰好一个入口屏（data-entry），现在有 {len(mark)} 个")
        entries += mark
    seen, todo = set(entries), list(entries)
    while todo:
        for to in edges.get(todo.pop(), []):
            if to in attrs_of and to not in seen:
                seen.add(to)
                todo.append(to)
    lost = [s for s in attrs_of if entries and s not in seen]
    if lost:
        out.append("从入口点不到这些屏：" + "、".join(lost) + "（在前面的屏上加 data-go 连过来）")
    return out


def build(page: str, all_icons: bool) -> str:
    css = (HERE / "kit.css").read_text(encoding="utf-8").rstrip("\n")
    sprite = (HERE / "icons.svg").read_text(encoding="utf-8")
    symbols = {m.group(1): m.group(0) for m in SYMBOL_RE.finditer(sprite)}

    body = PROTO_RE.sub("", ICONS_RE.sub("", STYLE_RE.sub("", page)))
    own = set(SYMBOL_RE.findall(body))  # 页面自己图标表里已经有的，不用组件库补，也不算缺
    used = sorted(set(USE_RE.findall(body)))
    missing = [u for u in used if u not in symbols and u not in own]
    if missing:
        raise SystemExit("图标表里没有：" + ", ".join(missing))
    keep = [k for k in symbols if k not in own] if all_icons else [u for u in used if u in symbols and u not in own]

    style_block = "<style data-hifi>\n" + css + "\n</style>\n"
    icons_block = ('<svg data-hifi-icons xmlns="http://www.w3.org/2000/svg" style="display:none" aria-hidden="true">\n'
                   + "\n".join(symbols[k] for k in keep) + "\n</svg>\n")

    if STYLE_RE.search(page):
        page = STYLE_RE.sub(lambda _: style_block, page, count=1)
    else:
        if "</head>" not in page:
            raise SystemExit("页面没有 </head>")
        page = page.replace("</head>", style_block + "</head>", 1)

    if ICONS_RE.search(page):
        page = ICONS_RE.sub(lambda _: icons_block, page, count=1)
    else:
        m = re.search(r"<body\b[^>]*>\n?", page)
        if not m:
            raise SystemExit("页面没有 <body>")
        page = page[:m.end()] + icons_block + page[m.end():]

    page = PROTO_RE.sub("", page)
    if re.search(r'class="[^"]*\bhf-proto\b', body):
        problems = proto_problems(body)
        if problems:
            raise SystemExit("可点原型有问题：\n  " + "\n  ".join(problems))
        js = (HERE / "proto.js").read_text(encoding="utf-8").rstrip("\n")
        block = "<script data-hifi-proto>\n" + js + "\n</script>\n"
        ends = list(BODY_END.finditer(page))
        page = page[:ends[-1].start()] + block + page[ends[-1].start():] if ends else page + block
    return page


def main(argv):
    all_icons = "--all-icons" in argv
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    for f in files:
        p = Path(f)
        if not p.is_file():
            print(f"没有这个文件：{f}", file=sys.stderr)
            return 2
        old = p.read_text(encoding="utf-8")
        new = build(old, all_icons)
        if new != old:
            p.write_text(new, encoding="utf-8")
        n = len(USE_RE.findall(ICONS_RE.sub("", STYLE_RE.sub("", new))))
        print(f"{f}: 组件库已写入（引用图标 {n} 处）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
