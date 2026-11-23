/* 可点原型：每个端一个入口，点界面上带 data-go 的地方切到那一屏，每屏旁边是说明。
   只切换屏幕：不发请求、不存数据。由 inline.py 在页面用到 .hf-proto 时写进页面。 */
(function () {
  function text(el) { return (el.getAttribute('aria-label') || el.textContent || '').replace(/\s+/g, ' ').trim(); }
  function button(label, onClick) {
    var b = document.createElement('button');
    b.type = 'button'; b.textContent = label; b.addEventListener('click', onClick);
    return b;
  }
  document.querySelectorAll('.hf-proto').forEach(function (root) {
    var screens = [].slice.call(root.querySelectorAll('[data-screen]'));
    if (!screens.length) return;
    var byId = {}, ends = [], entry = {}, cur = null, hist = [];
    function endOf(s) { return s.getAttribute('data-end') || '界面'; }
    function titleOf(s) { return s.getAttribute('data-title') || s.getAttribute('data-screen'); }
    function sameEnd(s) { return screens.filter(function (x) { return endOf(x) === endOf(s); }); }
    screens.forEach(function (s) {
      byId[s.getAttribute('data-screen')] = s;
      if (ends.indexOf(endOf(s)) < 0) ends.push(endOf(s));
      if (s.hasAttribute('data-entry') && !entry[endOf(s)]) entry[endOf(s)] = s.getAttribute('data-screen');
    });
    ends.forEach(function (e) { if (!entry[e]) entry[e] = screens.filter(function (s) { return endOf(s) === e; })[0].getAttribute('data-screen'); });

    // 顶栏：每个端一个入口；右边是当前位置、上一屏、从头开始、看全部屏
    var bar = document.createElement('div'); bar.className = 'hf-proto-bar';
    var tabs = document.createElement('div'); tabs.className = 'hf-proto-ends';
    ends.forEach(function (e) { var b = button(e, function () { go(entry[e], true); }); b.setAttribute('data-end', e); tabs.appendChild(b); });
    var pos = document.createElement('span'); pos.className = 'hf-proto-pos';
    var back = button('← 上一屏', function () { if (hist.length > 1) { hist.pop(); setAll(false); show(hist[hist.length - 1]); } });
    var restart = button('从头开始', function () { go(entry[endOf(cur)], true); });
    var all = button('看全部屏', function () { setAll(!root.classList.contains('all')); });
    var tools = document.createElement('div'); tools.className = 'hf-proto-tools';
    [pos, back, restart, all].forEach(function (x) { tools.appendChild(x); });
    bar.appendChild(tabs); bar.appendChild(tools);
    root.insertBefore(bar, root.firstChild);

    // 每屏的说明栏：前面加标题和第几屏，后面列出「这一屏能点」
    screens.forEach(function (s) {
      var note = s.querySelector('.hf-pnote');
      if (!note) { note = document.createElement('div'); note.className = 'hf-pnote'; s.appendChild(note); }
      var n = sameEnd(s).indexOf(s) + 1, h = document.createElement('div'), step = document.createElement('span'), t = document.createElement('b'), where = document.createElement('small');
      h.className = 'hf-pnote-h'; step.className = 'hf-step'; step.textContent = n; t.textContent = titleOf(s);
      where.textContent = endOf(s) + ' · 第 ' + n + ' / ' + sameEnd(s).length + ' 屏';
      h.appendChild(step); h.appendChild(t); h.appendChild(where);
      note.insertBefore(h, note.firstChild);
      var gos = [].slice.call(s.querySelectorAll('[data-go]')).filter(function (g) { return !note.contains(g); });
      if (!gos.length) return;
      var list = document.createElement('div'), lb = document.createElement('b');
      list.className = 'hf-pgo'; lb.textContent = '这一屏能点'; list.appendChild(lb);
      gos.forEach(function (g) {
        var to = byId[g.getAttribute('data-go')];
        list.appendChild(button((text(g) || '点这里') + ' → ' + (to ? titleOf(to) : g.getAttribute('data-go')), function () { go(g.getAttribute('data-go')); }));
        if (!/^(A|BUTTON)$/.test(g.tagName)) { g.setAttribute('tabindex', '0'); g.setAttribute('role', 'button'); }
      });
      note.appendChild(list);
    });

    function setAll(on) { root.classList.toggle('all', on); all.textContent = on ? '回到可点' : '看全部屏'; }
    function show(id) {
      var s = byId[id]; if (!s) return;
      cur = s;
      screens.forEach(function (x) { x.classList.toggle('on', x === s); });
      [].forEach.call(tabs.children, function (b) { b.classList.toggle('on', b.getAttribute('data-end') === endOf(s)); });
      pos.textContent = endOf(s) + ' · 第 ' + (sameEnd(s).indexOf(s) + 1) + ' / ' + sameEnd(s).length + ' 屏';
      back.disabled = hist.length < 2;
      try {  // 网址里的 # 是别的锚点（例如章节 #s7）就不动它
        var h = decodeURIComponent(location.hash.slice(1));
        if (h !== id && (h === '' || byId[h])) history.replaceState(null, '', '#' + encodeURIComponent(id));
      } catch (e) {}
    }
    function go(id, reset) {
      if (!byId[id]) return;
      if (reset) hist = [];
      if (hist[hist.length - 1] !== id) hist.push(id);
      setAll(false); show(id);
      if (root.getBoundingClientRect().top < 0) root.scrollIntoView({block: 'start'});
    }
    root.addEventListener('click', function (e) {
      var g = e.target.closest('[data-go]');
      if (g && root.contains(g) && !g.closest('.hf-pgo')) { e.preventDefault(); go(g.getAttribute('data-go')); return; }
      if (!root.classList.contains('all') && cur && cur.contains(e.target) && !e.target.closest('.hf-pnote')) {
        root.classList.add('hint'); setTimeout(function () { root.classList.remove('hint'); }, 800);  // 点了不能点的地方：把能点的闪一下
      }
    });
    root.addEventListener('keydown', function (e) {
      var g = e.target.closest && e.target.closest('[data-go]');
      if (g && !g.closest('.hf-pgo') && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); go(g.getAttribute('data-go')); }
    });
    addEventListener('hashchange', function () {
      var id = ''; try { id = decodeURIComponent(location.hash.slice(1)); } catch (e) {}
      if (byId[id] && (!cur || cur.getAttribute('data-screen') !== id)) go(id, true);
    });
    var first = ''; try { first = decodeURIComponent(location.hash.slice(1)); } catch (e) {}
    root.classList.add('live');
    go(byId[first] ? first : entry[ends[0]], true);
  });
})();
