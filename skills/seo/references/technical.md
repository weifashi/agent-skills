# 技术项：逐条做法

这些都由生成脚本一次写进每个页面（模板见 `assets/build_pages.example.py`），不要手工逐页改。

## 1. title 和 description

- 每页不同，含本页主词。
- 同步改 `og:title`、`og:description`（分享到聊天软件时显示的也是它们）。

## 2. canonical

每页指向自己：

```html
<link rel="canonical" href="/qr-menu/">
```

测试环境可以写相对路径；正式上线时换成带域名的完整地址（见第 7 条的开关）。

## 3. hreflang

同一主题的各语言页面互相标注，再加一条默认版本：

```html
<link rel="alternate" hreflang="tr" href="/qr-menu/">
<link rel="alternate" hreflang="en" href="/en/qr-menu/">
<link rel="alternate" hreflang="ja" href="/ja/mobile-order/">
<link rel="alternate" hreflang="x-default" href="/qr-menu/">
```

- 每一页都要列出**全组**（包括自己）。
- 只有一种语言的页面，只标自己和 x-default。
- **标注指向的每个地址都要打得开**。先 `curl` 一遍：常见的坑是仓库里有某种语言的页面，但发布时没带上，线上是 404。
- 页头的语言切换也改成跳到同主题的那一页，而不是各语言首页。

## 4. sitemap.xml

列出全部页面，带各语言对应关系：

```xml
<url>
  <loc>https://example.com/qr-menu/</loc>
  <xhtml:link rel="alternate" hreflang="tr" href="https://example.com/qr-menu/"/>
  <xhtml:link rel="alternate" hreflang="en" href="https://example.com/en/qr-menu/"/>
  <xhtml:link rel="alternate" hreflang="x-default" href="https://example.com/qr-menu/"/>
</url>
```

网站地图必须用完整地址。域名用一个变量传入，正式域名定下后换掉重跑。

## 5. 结构化数据

每页 `<head>` 里放一段 JSON-LD，页面上不显示：

```html
<script type="application/ld+json" data-seo>
[{"@context":"https://schema.org","@type":"SoftwareApplication","name":"品牌名",
  "description":"本页描述","url":"https://example.com/qr-menu/","inLanguage":"tr",
  "applicationCategory":"BusinessApplication","operatingSystem":"Web",
  "offers":{"@type":"Offer","price":"0","priceCurrency":"TRY"}},
 {"@context":"https://schema.org","@type":"FAQPage","inLanguage":"tr",
  "mainEntity":[{"@type":"Question","name":"问题","acceptedAnswer":{"@type":"Answer","text":"答案"}}]}]
</script>
```

- 常见问题直接从本页的问答里提取，不另写一份，免得两处不一致。
- `operatingSystem`、价格这些只写确实成立的。
- JSON 里的 `</` 要写成 `<\/`，否则可能提前结束 script 标签。
- 给这段加一个标记（如 `data-seo`），脚本重跑时先删旧的再写新的；删的时候连它后面的换行一起删，否则每跑一次多一个空行（重复生成结果就不一样了）。

## 6. 站内链接

- 首页页脚加本语言各分页的链接；分页页脚链回首页和同语言其它分页。
- 没有任何页面链过去的分页，搜索引擎很难发现。

## 7. 测试环境不收录 + 正式上线开关

测试环境每页都带：

```html
<meta name="robots" content="noindex,nofollow">
```

逐页检查有没有漏的（独立做的页面，如下载页，最容易漏）。

正式上线不要去改源文件（那样测试环境也会被收录），而是在构建脚本里加一个只在正式发布时打开的开关，例如环境变量 `SITE_PUBLIC_ORIGIN=https://正式域名`。打开后：

1. 去掉官网各页的 `noindex,nofollow`；
2. canonical、hreflang、sitemap、og 图片、结构化数据里的地址换成正式域名；
3. 生成 `robots.txt`：放开官网，挡住后台、接口等不该收录的路径，并写上 `Sitemap:` 地址。

同时加两道保护：

- 不设这个变量时，构建结果和原来**完全一样**；
- 变量填成测试域名时直接报错。

用一个假域名把「开」和「不开」各构建一次，核对：不开时 noindex 一页不少，开了以后一页不剩，且输出里搜不到测试域名（画在插图里的文字除外）。

## 8. 重复生成必须一致

脚本写完连跑三遍，比对输出文件的校验值。不一致的常见原因：

- 插入内容时多带了换行，删除时没带上；
- 把已经生成过的输出又当成输入，重复套了一层；
- 用到了当前时间、随机数、不稳定的遍历顺序。
