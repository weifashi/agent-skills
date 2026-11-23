"""从各语言首页生成搜索分页 + 站点地图的模板。复制到项目里改 CONFIG 和 customize()。

用法：python3 build_pages.py <官网目录>      # 目录下是 index.html、en/index.html …
     SITE_ORIGIN=https://example.com python3 build_pages.py <官网目录>   # 网站地图用的域名

它做的事：
- 各语言首页：只换 <title> / description / og，补 hreflang（含 x-default）、页脚分页链接、结构化数据；画面不动。
- 每个分页：从同语言首页复制，换标题、描述、首屏文字，canonical 指向自己，同主题的各语言页互相标 hreflang。
- sitemap.xml：全部页面，带各语言对应关系。
重复运行结果必须一模一样（改完连跑三遍比对）。首页改了以后重跑，分页跟着更新。
"""
import json, os, pathlib, re, sys

ROOT = pathlib.Path(sys.argv[1]).resolve()
ORIGIN = os.environ.get('SITE_ORIGIN', 'https://example.com').rstrip('/')
BASE = '/'  # 官网在域名下的路径前缀

# ---------------------------------------------------------------- CONFIG：按项目改
# 语言：键 → (hreflang 代码, 子目录)。根目录放主市场语言。
LANGS = {'tr': ('tr', ''), 'en': ('en', 'en/')}
DEFAULT_LANG = 'tr'  # x-default 指向哪种语言
BRAND = 'Brand'

HOME = {  # 各语言首页的标题和描述：放当地人会搜的品类词
    'tr': dict(title='Brand Adisyon Programı — Telefon ve Tablette Kasa, QR Menü',
               desc='…', link='Adisyon programı', rel='Ayrıca'),
    'en': dict(title='Brand — Restaurant POS and QR Menu Ordering',
               desc='…', link='Restaurant POS', rel='See also'),
}

# 分页。group 相同的页面是同一主题的不同语言版本，互相标 hreflang。
PAGES = [
    dict(lang='tr', slug='qr-menu', group='qr', link='QR menü oluştur',
         title='QR Menü Oluştur — Masadan Sipariş | Brand', desc='…',
         kicker='QR MENÜ', h1='QR menü oluştur: misafir masadan sipariş versin.', sub='…'),
    dict(lang='en', slug='qr-menu', group='qr', link='QR menu ordering',
         title='QR Code Menu and Table Ordering | Brand', desc='…',
         kicker='QR MENU', h1='QR code menu: guests order from the table.', sub='…'),
]
# ----------------------------------------------------------------


def home_url(lang):
    return BASE + LANGS[lang][1]


def page_url(p):
    return home_url(p['lang']) + p['slug'] + '/'


def sub1(pattern, repl, t):
    """必须正好替换一处；模板结构变了就立刻报错，而不是悄悄漏改。"""
    t2, n = re.subn(pattern, lambda m: repl(m) if callable(repl) else repl, t, count=1, flags=re.S)
    assert n == 1, pattern
    return t2


def set_meta(t, title, desc):
    t = sub1(r'<title>.*?</title>', f'<title>{title}</title>', t)
    for k, v in (('name="description"', desc), ('property="og:title"', title), ('property="og:description"', desc)):
        if re.search(r'<meta ' + re.escape(k), t):
            t = sub1(r'<meta ' + re.escape(k) + r' content="[^"]*"', f'<meta {k} content="{v}"', t)
    return t


def set_canonical_hreflang(t, self_url, urls):
    """urls: {lang: url}。先删旧的再写，重复跑不会叠加。"""
    t = re.sub(r'<link rel="(?:canonical|alternate)"[^>]*>\n?', '', t)
    links = [f'<link rel="canonical" href="{self_url}">']
    links += [f'<link rel="alternate" hreflang="{LANGS[l][0]}" href="{u}">' for l, u in urls.items()]
    links.append(f'<link rel="alternate" hreflang="x-default" href="{urls.get(DEFAULT_LANG) or next(iter(urls.values()))}">')
    return sub1(r'(<meta name="description"[^>]*>)', lambda m: m.group(1) + '\n' + '\n'.join(links), t)


REL_RE = re.compile(r'<span class="seo-rel">.*?</span>', re.S)


def set_rel(t, lang, items):
    """页脚里同语言其它页面的链接。首页模板的 </footer> 前要能放下一个 <span>。"""
    span = f'<span class="seo-rel">{HOME[lang]["rel"]}: ' + ' · '.join(f'<a href="{u}">{n}</a>' for u, n in items) + '</span>'
    if REL_RE.search(t):
        return REL_RE.sub(lambda m: span, t, count=1)
    return sub1(r'(</footer>)', lambda m: span + m.group(1), t)


LD_RE = re.compile(r'<script type="application/ld\+json" data-seo>.*?</script>\n?', re.S)


def strip_tags(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s)).strip()


def set_ld(t, lang, url, name, desc):
    """结构化数据：软件 + 本页常见问题（直接从页面的 <details> 里取，不另写一份）。"""
    qa = re.findall(r'<details><summary>(.*?)</summary><p>(.*?)</p></details>', t, re.S)
    data = [{'@context': 'https://schema.org', '@type': 'SoftwareApplication', 'name': BRAND, 'headline': name,
             'description': desc, 'url': ORIGIN + url, 'inLanguage': LANGS[lang][0],
             'applicationCategory': 'BusinessApplication', 'operatingSystem': 'Web'}]
    if qa:
        data.append({'@context': 'https://schema.org', '@type': 'FAQPage', 'inLanguage': LANGS[lang][0],
                     'mainEntity': [{'@type': 'Question', 'name': strip_tags(q),
                                     'acceptedAnswer': {'@type': 'Answer', 'text': strip_tags(a)}} for q, a in qa]})
    js = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    t = LD_RE.sub('', t)  # 连同后面的换行一起删，否则每跑一次多一个空行
    return t.replace('</head>', f'<script type="application/ld+json" data-seo>{js}</script>\n</head>', 1)


def customize(t, p):
    """按项目的首页结构改这里：换首屏文字、导航、去掉无关段落、挑常见问题。
    下面是最小的例子：只换第一个 <h1> 和它后面的第一段。"""
    t = sub1(r'<h1[^>]*>.*?</h1>', lambda m: re.sub(r'>.*<', lambda _: '>' + p['h1'] + '<', m.group(0), count=1, flags=re.S), t)
    return t


def write(path, s):
    """先写临时文件再改名：中途出错不会留下半个文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(s, encoding='utf-8')
    os.replace(tmp, path)
    print(path.relative_to(ROOT), len(s))


def by_lang(lang):
    return [p for p in PAGES if p['lang'] == lang]


homes, home_alts = {}, {l: home_url(l) for l in LANGS}
for lang, (_, sub) in LANGS.items():
    f = ROOT / sub / 'index.html'
    t = f.read_text(encoding='utf-8')
    t = set_meta(t, HOME[lang]['title'], HOME[lang]['desc'])
    t = set_canonical_hreflang(t, home_url(lang), home_alts)
    t = set_rel(t, lang, [(page_url(q), q['link']) for q in by_lang(lang)])
    t = set_ld(t, lang, home_url(lang), HOME[lang]['title'], HOME[lang]['desc'])
    write(f, t)
    homes[lang] = t

for p in PAGES:
    lang, url = p['lang'], page_url(p)
    group = {q['lang']: page_url(q) for q in PAGES if q['group'] == p['group']}
    t = customize(homes[lang], p)
    t = set_meta(t, p['title'], p['desc'])
    t = set_canonical_hreflang(t, url, group)
    # 页头 / 页脚的语言切换：有同主题页的语言直接跳过去
    for l, u in group.items():
        t = t.replace(f'href="{home_url(l)}" lang="{LANGS[l][0]}"', f'href="{u}" lang="{LANGS[l][0]}"')
    t = set_rel(t, lang, [(home_url(lang), HOME[lang]['link'])] + [(page_url(q), q['link']) for q in by_lang(lang) if q is not p])
    t = set_ld(t, lang, url, p['title'], p['desc'])
    write(ROOT / LANGS[lang][1] / p['slug'] / 'index.html', t)


def sm_entry(url, alts):
    x = ''.join(f'<xhtml:link rel="alternate" hreflang="{LANGS[l][0]}" href="{ORIGIN}{u}"/>' for l, u in alts.items())
    x += f'<xhtml:link rel="alternate" hreflang="x-default" href="{ORIGIN}{alts.get(DEFAULT_LANG) or next(iter(alts.values()))}"/>'
    return f'<url><loc>{ORIGIN}{url}</loc>{x}</url>\n'


sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
for l in LANGS:
    sm += sm_entry(home_url(l), home_alts)
for p in PAGES:
    sm += sm_entry(page_url(p), {q['lang']: page_url(q) for q in PAGES if q['group'] == p['group']})
write(ROOT / 'sitemap.xml', sm + '</urlset>\n')
