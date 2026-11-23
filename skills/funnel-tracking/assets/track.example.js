'use strict';
// 官网 / 落地页的自有统计脚本模板。复制到项目里，改 CONFIG。不加载任何第三方脚本。
// 1) 数据只发到自己的后端。不记 IP、浏览器型号、邮箱、地址栏参数。
// 2) 不经同意也记：每打开一次页面一个随机编号（只在内存里）。能算每页被看几次、看到哪、点了什么。
//    访客点「同意」后：本机存一个随机的访客编号，才能把同一个人的几次访问和之后的注册连起来。
//    拒绝 / 撤回：删掉访客编号和来源记录；浏览器开了全局隐私控制（GPC）时当作拒绝。
// 3) 来源参数（utm_* 等）接到站内链接和注册链接上，带进产品。
// 地址带 ?track=off 这一次不统计；?internal=1 让这台设备以后都不统计（自己人用），?internal=0 取消。
//
// 页面里的约定：
//   <body data-page="lp-a">                         页面编号
//   <section data-sec="pricing">                    要统计「看到这一屏」的段落
//   <a data-cta="start" href="/signup">             主按钮；data-cta 是按钮名
//   <details data-faq="price">                      常见问题
//   同意框的两个按钮调用 window.siteTrack.consent(true / false)
(() => {
  const CONFIG = Object.assign({
    endpoint: '/api/v1/events',
    app: 'site',
    consentKey: 'site-consent',     // 值：granted / denied
    visitorKey: 'site-vid',
    attrKey: 'site-attr',
    forward: ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'lp', 'ref'],
    signupPath: /^\/(signup|admin)\b/,   // 来源参数要带过去的站内路径
  }, window.SITE_TRACK || {});

  const store = { get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* 隐私模式 */ } },
    del: (k) => { try { localStorage.removeItem(k); } catch { /* 隐私模式 */ } } };
  const qs = new URLSearchParams(location.search);
  if (qs.get('internal') === '1') store.set('site-internal', '1');
  if (qs.get('internal') === '0') store.del('site-internal');
  const OFF = qs.get('track') === 'off' || store.get('site-internal') === '1';

  const uuid = () => crypto.randomUUID();
  const VIEW = uuid();
  const gpc = navigator.globalPrivacyControl === true;
  const consented = () => !gpc && store.get(CONFIG.consentKey) === 'granted';

  // ---------- 来源：没同意时只放内存，同意后才写本机 ----------
  let attr = {};
  CONFIG.forward.forEach((k) => { const v = qs.get(k); if (v) attr[k.replace(/^utm_/, '')] = v.slice(0, 120); });
  if (!Object.keys(attr).length && consented()) { try { attr = JSON.parse(store.get(CONFIG.attrKey) || '{}'); } catch { attr = {}; } }
  const saveAttr = () => { if (consented() && Object.keys(attr).length) store.set(CONFIG.attrKey, JSON.stringify(attr)); };
  if (!consented()) { store.del(CONFIG.attrKey); store.del(CONFIG.visitorKey); } else saveAttr();
  const visitor = () => { if (!consented()) return null; let v = store.get(CONFIG.visitorKey); if (!v) { v = uuid(); store.set(CONFIG.visitorKey, v); } return v; };

  // 把来源参数接到去注册 / 去产品的站内链接上
  const carry = new URLSearchParams();
  CONFIG.forward.forEach((k) => { const v = qs.get(k); if (v) carry.set(k, v.slice(0, 120)); });
  if ([...carry].length) document.querySelectorAll('a[href^="/"]').forEach((a) => {
    const u = new URL(a.getAttribute('href'), location.origin);
    if (!CONFIG.signupPath.test(u.pathname)) return;
    carry.forEach((v, k) => { if (!u.searchParams.has(k)) u.searchParams.set(k, v); });
    a.setAttribute('href', u.pathname + u.search + u.hash);
  });

  // ---------- 发送：攒一小批，页面隐藏时一定发出去 ----------
  let queue = [];
  const flush = () => {
    if (!queue.length) return;
    const body = JSON.stringify({ events: queue.splice(0, 25) });
    try { if (!(navigator.sendBeacon && navigator.sendBeacon(CONFIG.endpoint, new Blob([body], { type: 'application/json' })))) fetch(CONFIG.endpoint, { method: 'POST', headers: { 'content-type': 'application/json' }, body, keepalive: true }).catch(() => {}); } catch { /* 统计失败不影响页面 */ }
  };
  const push = (event, props) => {
    if (OFF) return;
    queue.push({ id: uuid(), at: Date.now(), event, app: CONFIG.app, view: VIEW, visitor: visitor(), path: location.pathname,
      page: document.body.dataset.page || '', lang: (document.documentElement.lang || '').slice(0, 2),
      referrer: (() => { try { return document.referrer ? new URL(document.referrer).hostname : ''; } catch { return ''; } })(), attr, props: props || {} });
    if (queue.length >= 10) flush(); else setTimeout(flush, 2000);
  };

  // ---------- 事件 ----------
  push('page_view');

  // 停留时间：切到别的标签页不算
  let visibleMs = 0, since = document.visibilityState === 'visible' ? Date.now() : 0, maxScroll = 0, left = false;
  const leave = () => {
    if (left) return; left = true;
    if (since) visibleMs += Date.now() - since;
    push('page_leave', { seconds: Math.round(visibleMs / 1000), percent: maxScroll }); flush();
  };
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') { if (since) { visibleMs += Date.now() - since; since = 0; } flush(); } else since = Date.now();
  });
  addEventListener('pagehide', leave);

  // 滚动深度：25 / 50 / 75 / 90，各记一次
  const marks = [25, 50, 75, 90], seen = new Set();
  addEventListener('scroll', () => {
    const h = document.documentElement.scrollHeight - innerHeight; if (h <= 0) return;
    const p = Math.min(100, Math.round(scrollY / h * 100)); maxScroll = Math.max(maxScroll, p);
    marks.forEach((m) => { if (p >= m && !seen.has(m)) { seen.add(m); push('scroll_depth', { percent: m }); } });
  }, { passive: true });

  // 看到第几屏：带顺序号，用来画「每一屏还剩多少人」
  const secs = [...document.querySelectorAll('[data-sec]')];
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((es) => es.forEach((e) => {
      if (!e.isIntersecting) return; io.unobserve(e.target);
      push('section_view', { sec: e.target.dataset.sec, order: secs.indexOf(e.target) + 1 });
    }), { threshold: 0.4 });
    secs.forEach((s) => io.observe(s));
  }

  // 点击：按钮名 + 在页面的哪一块
  document.addEventListener('click', (e) => {
    const a = e.target.closest('[data-cta]'); if (!a) return;
    push('cta_click', { cta: a.dataset.cta, place: a.closest('[data-sec]')?.dataset.sec || 'other' }); flush();
  });

  // 展开的常见问题
  document.querySelectorAll('details[data-faq]').forEach((d) => d.addEventListener('toggle', () => { if (d.open) push('faq_open', { faq: d.dataset.faq }); }));

  // ---------- 同意：只在亲手点选时记一次 ----------
  window.siteTrack = {
    consent(granted) {
      store.set(CONFIG.consentKey, granted ? 'granted' : 'denied');
      if (granted) saveAttr(); else { store.del(CONFIG.visitorKey); store.del(CONFIG.attrKey); }
      push('consent_set', { granted: !!granted && !gpc });
    },
    needsChoice: () => !gpc && !store.get(CONFIG.consentKey),
  };
})();
