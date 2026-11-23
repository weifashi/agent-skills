# agent-skills

wfs 的 Agent 技能库。一个仓库、一个插件（`wfs`），装一次全都有，Claude Code 和 Codex 都能用。

| 技能 | 做什么 | 你怎么说 |
|---|---|---|
| [project](skills/project/SKILL.md) | 起项目 / 接手项目：把需求背景原文、决策、AI 规则存进项目 | 「开个新项目」「接手这个项目」「把这次需求存下来」 |
| [mockup](skills/mockup/SKILL.md) | 一页 HTML 讲清一件事：需求原型、高保真效果图、改动汇报 | 「出个原型」「给老板看做出来的样子」「这次改了什么」 |
| [bug-hunt](skills/bug-hunt/SKILL.md) | 提测检查：对照需求查六类问题，50 条一批，给出能不能提测 | 「找 bug」「能不能提测」 |
| [promo-page](skills/promo-page/SKILL.md) | 推广页 / 官网 / 落地页 | 「做个官网」「官网看着不高级」 |
| [site-seo](skills/site-seo/SKILL.md) | 官网 SEO：从查词到上线 | 「做 SEO」「让谷歌搜到我们」 |
| [funnel-tracking](skills/funnel-tracking/SKILL.md) | 埋点和推广漏斗统计 | 「埋点」「看用户在哪流失」 |

## 安装

Claude Code：

```
/plugin marketplace add weifashi/agent-skills
/plugin install wfs@wfs
```

装好后自动触发，也可以手动调用：`/wfs:mockup`、`/wfs:bug-hunt`、`/wfs:project` ……

Codex：

```bash
codex plugin marketplace add weifashi/agent-skills
codex plugin add wfs@wfs
```

其他工具（Cursor、Gemini CLI 等）：

```bash
npx skills add weifashi/agent-skills
```

## 更新

仓库不写版本号，推送一次就是一次更新。

```
/plugin marketplace update wfs        # Claude Code
codex plugin marketplace upgrade      # Codex
```

## 这套技能的共同约定

资料跟着项目走，不放外部服务，不放只在本机的目录：

```text
项目/
├─ AGENTS.md              AI 规则（CLAUDE.md 只写一行 @AGENTS.md）
└─ docs/
   ├─ background/         需求背景原文，一次需求一个文件
   ├─ decisions.md        决策记录，一行一条
   ├─ architecture.md     架构的最终总结（用到才建）
   ├─ mockups/            原型、改动汇报（用到才建）
   └─ bugs.md             提测问题清单（用到才建）
```

约定由 `project` 技能定，其余技能都往这里写。本仓库自己也按这套来，见 [docs/](docs/)。

## 维护

写技能的规矩在 [AGENTS.md](AGENTS.md)。改完跑：

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests -p "*_test.py"
```

## License

MIT。`skills/mockup/assets/hifi/` 里的图标来自 [Lucide](https://lucide.dev)（ISC）。
