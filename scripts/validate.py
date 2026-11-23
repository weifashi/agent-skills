#!/usr/bin/env python3
"""检查 skills/ 下每个技能是否符合 AGENTS.md 里的规范。

用法：python3 scripts/validate.py [仓库根目录]
有问题时逐条列出并以 1 退出；CI 跑的是同一个命令。
"""
import json
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME = 64          # Agent Skills 规范
MAX_DESC = 1024        # Agent Skills 规范
MAX_LINES = 500        # 官方建议的 SKILL.md 上限
TEXT_SUFFIXES = {".md", ".py", ".js", ".cjs", ".mjs", ".sh", ".html", ".json", ".yaml", ".yml", ".sql", ".txt"}

# 不该进公开技能的东西：绑定某台机器或某个外部服务的写法、内部项目名、密钥形状
BANNED = [
    (re.compile(r"8008--"), "写死了端口转发域名"),
    (re.compile(r"~/www\b"), "写死了本机原型目录 ~/www"),
    (re.compile(r"ttpos", re.I), "出现内部项目名"),
    (re.compile(r"\b(itn_|ghp_|gho_|sk-)[A-Za-z0-9]{16,}"), "像是密钥"),
]

LINK_RE = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
PATH_RE = re.compile(r"`((?:references|assets|scripts|templates)/[^`\s*<>{}]+)`")


def frontmatter(text):
    """只支持本库约定的写法：--- 之间每行一个 key: value，值写在一行里。"""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fields = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip("\"'")
    return fields


def check_skill(d):
    errors = []
    md = d / "SKILL.md"
    if not md.is_file():
        return [f"{d.name}: 缺少 SKILL.md"]
    text = md.read_text(encoding="utf-8")
    fm = frontmatter(text)
    if fm is None:
        return [f"{d.name}: SKILL.md 开头没有 frontmatter"]

    name, desc = fm.get("name", ""), fm.get("description", "")
    if name != d.name:
        errors.append(f"{d.name}: name「{name}」和目录名不一致")
    if not NAME_RE.match(name) or len(name) > MAX_NAME:
        errors.append(f"{d.name}: name 只能用小写字母、数字、连字符，最长 {MAX_NAME} 字符")
    if not desc or desc in (">", "|", ">-", "|-"):
        errors.append(f"{d.name}: description 要写在一行里，不能为空")
    elif len(desc) > MAX_DESC:
        errors.append(f"{d.name}: description {len(desc)} 字符，超过 {MAX_DESC}")
    lines = text.count("\n") + 1
    if lines > MAX_LINES:
        errors.append(f"{d.name}: SKILL.md {lines} 行，超过 {MAX_LINES}，把细节移到 references/")

    for f in sorted(d.rglob("*")):
        if not f.is_file() or f.suffix not in TEXT_SUFFIXES:
            continue
        body = f.read_text(encoding="utf-8", errors="replace")
        rel = f.relative_to(d.parent)
        for pattern, why in BANNED:
            m = pattern.search(body)
            if m:
                line = body.count("\n", 0, m.start()) + 1
                errors.append(f"{rel}:{line}: {why}")
        if f.suffix != ".md":
            continue
        targets = {t for t in LINK_RE.findall(body) if "://" not in t and not t.startswith("mailto:")}
        missing = {t for t in targets if not (f.parent / t).exists()}
        if f == md:  # 入口里用反引号写的路径也要真的存在
            missing |= {t for t in PATH_RE.findall(body) if not (d / t).exists()}
        errors += [f"{rel}: 指向的文件不存在 {t}" for t in sorted(missing)]
    return errors


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    errors = []
    for manifest in ("marketplace.json", "plugin.json"):
        try:
            json.loads((root / ".claude-plugin" / manifest).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            errors.append(f".claude-plugin/{manifest}: {e}")

    skills = sorted(p for p in (root / "skills").iterdir() if p.is_dir()) if (root / "skills").is_dir() else []
    for d in skills:
        errors += check_skill(d)

    for e in errors:
        print("✗", e)
    print(f"{len(skills)} 个技能，{len(errors)} 个问题")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
