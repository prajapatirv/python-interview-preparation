(function () {
  var nav = document.getElementById('side-nav');
  var body = document.body;
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function slug(s) { return s.toLowerCase().replace(/\(.*?\)/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40); }
  function link(href, text, cls) { var a = el('a', cls, text); a.href = '#' + href; return a; }
  var load = function (k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } };
  var save = function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };

  var root = el('ul'), spyTargets = [], qLinks = [], grpRows = [];
  var openGroups = load('iam-side-open') || {};

  document.querySelectorAll('main > section.panel').forEach(function (sec) {
    var li = el('li', 'side-sec');
    var h2 = sec.querySelector('h2');
    var a = link(sec.id, h2 ? h2.textContent : sec.id);
    li.appendChild(a); spyTargets.push({ el: sec, a: a, top: true });

    if (sec.id === 'answers') {
      var sub = el('ul', 'side-sub');
      sec.querySelectorAll('section.group').forEach(function (g) {
        var h3 = g.querySelector('h3');
        var name = h3.firstChild.textContent.trim();
        var qs = g.querySelectorAll('details.q');
        var row = el('li', 'side-grp' + (openGroups[g.id] ? ' open' : ''));
        var tog = el('button'); tog.type = 'button'; tog.innerHTML = '&#9654;';
        tog.setAttribute('aria-label', 'Show questions in ' + name);
        tog.setAttribute('aria-expanded', openGroups[g.id] ? 'true' : 'false');
        var ga = link(g.id, ''); ga.appendChild(el('span', null, name)); var cnt = el('small'); ga.appendChild(cnt);
        var list = el('ul', 'side-qs');
        qs.forEach(function (q, i) {
          var t = q.querySelector('.qt');
          var qa = link(q.id, '', 'l-' + (q.dataset.level || ''));
          qa.appendChild(el('span', null, 'Q' + (i + 1) + '. ' + (t ? t.textContent : q.id)));
          qa.title = (q.dataset.level || '') + ' level';
          var qli = el('li'); qli.appendChild(qa); list.appendChild(qli);
          qLinks.push({ a: qa, li: qli, q: q, text: (t ? t.textContent : '').toLowerCase() + ' ' + (q.dataset.tags || '') });
        });
        tog.addEventListener('click', function () {
          var o = row.classList.toggle('open');
          tog.setAttribute('aria-expanded', o ? 'true' : 'false');
          if (o) openGroups[g.id] = 1; else delete openGroups[g.id];
          save('iam-side-open', openGroups);
        });
        row.appendChild(tog); row.appendChild(ga); row.appendChild(list); sub.appendChild(row);
        grpRows.push({ row: row, g: g, cnt: cnt, qs: qs, name: name.toLowerCase() });
        spyTargets.push({ el: g, a: ga });
      });
      li.appendChild(sub);
      var leg = el('div', 'side-legend');
      ['fresher', 'mid', 'senior', 'architect'].forEach(function (l) {
        var s = el('span'); var b = el('b'); b.style.background = 'var(--' + l + ')'; s.appendChild(b); s.appendChild(document.createTextNode(l)); leg.appendChild(s);
      });
      li.appendChild(leg);
    } else {
      var h3s = sec.querySelectorAll(':scope > h3');
      if (h3s.length > 1) {
        var sub2 = el('ul', 'side-sub');
        h3s.forEach(function (h) {
          if (!h.id) { var base = sec.id + '-' + slug(h.textContent), id = base, n = 2; while (document.getElementById(id)) id = base + '-' + n++; h.id = id; }
          h.style.scrollMarginTop = '60px';
          var sa = link(h.id, h.textContent.replace(/\s*\(.*\)\s*$/, ''));
          sa.title = h.textContent;
          var sli = el('li'); sli.appendChild(sa); sub2.appendChild(sli);
          spyTargets.push({ el: h, a: sa });
        });
        li.appendChild(sub2);
      }
    }
    root.appendChild(li);
  });
  var none = el('p', 'side-none', 'No questions match.'); none.hidden = true;
  nav.appendChild(root); nav.appendChild(none);

  // Progress: reads the same checkboxes the page already saves.
  var pct = document.getElementById('side-pct'), bar = document.getElementById('side-bar');
  function progress() {
    var total = 0, done = 0;
    grpRows.forEach(function (r) {
      var d = 0;
      r.qs.forEach(function (q) { if (q.classList.contains('is-done')) d++; });
      r.cnt.textContent = d + '/' + r.qs.length;
      r.cnt.classList.toggle('full', d === r.qs.length);
      total += r.qs.length; done += d;
    });
    qLinks.forEach(function (x) { x.a.classList.toggle('ok', x.q.classList.contains('is-done')); });
    pct.textContent = done + ' of ' + total + ' practised';
    bar.style.width = (total ? (done / total * 100) : 0) + '%';
  }
  document.addEventListener('change', function (e) { if (e.target.matches && e.target.matches('input[data-done]')) setTimeout(progress, 0); });
  progress();

  // Index filter: narrows the question list, opening groups with matches.
  var find = document.getElementById('side-find');
  find.addEventListener('input', function () {
    var w = find.value.toLowerCase().split(/\s+/).filter(Boolean), any = false;
    qLinks.forEach(function (x) { x.li.hidden = w.length && !w.every(function (k) { return x.text.indexOf(k) >= 0; }); });
    grpRows.forEach(function (r) {
      var vis = !w.length || r.row.querySelector('.side-qs li:not([hidden])');
      r.row.hidden = !vis;
      r.row.classList.toggle('open', w.length ? !!vis : !!openGroups[r.g.id]);
      if (vis) any = true;
    });
    root.querySelectorAll(':scope > li').forEach(function (li) { li.hidden = w.length && !li.querySelector('.side-grp'); });
    none.hidden = !w.length || any;
  });
  find.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { var first = qLinks.filter(function (x) { return !x.li.hidden; })[0]; if (first) first.a.click(); }
  });

  // Drawer on small screens.
  var openBtn = document.getElementById('side-open');
  function setOpen(o) { body.classList.toggle('nav-open', o); openBtn.setAttribute('aria-expanded', o ? 'true' : 'false'); if (o) setTimeout(function () { find.focus(); }, 50); }
  openBtn.addEventListener('click', function () { setOpen(true); });
  document.getElementById('side-close').addEventListener('click', function () { setOpen(false); });
  document.getElementById('side-scrim').addEventListener('click', function () { setOpen(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && body.classList.contains('nav-open')) setOpen(false); });
  nav.addEventListener('click', function (e) {
    var a = e.target.closest('a');
    if (!a) return;
    var id = a.getAttribute('href').slice(1), t = document.getElementById(id);
    if (t && t.tagName === 'DETAILS') t.open = true;
    if (t && !/^(q-|bank-)/.test(id)) { e.preventDefault(); t.scrollIntoView(); history.replaceState(null, '', '#' + id); }
    setOpen(false);
  });

  // Highlight where the reader is, and keep that entry visible in the index.
  var current = null, ticking = false, toTop = document.getElementById('to-top');
  function spy() {
    ticking = false;
    var line = window.innerHeight * 0.25, best = null;
    for (var i = 0; i < spyTargets.length; i++) {
      var s = spyTargets[i];
      if (s.el.hidden || !s.el.offsetParent) continue;
      if (s.el.getBoundingClientRect().top <= line) best = s;
    }
    var activeA = best ? best.a : spyTargets[0].a;
    var topA = null;
    for (var j = 0; j < spyTargets.length; j++) { var t = spyTargets[j]; if (t.top && t.el.getBoundingClientRect().top <= line) topA = t.a; }
    if (activeA !== current) {
      nav.querySelectorAll('a.active').forEach(function (x) { x.classList.remove('active'); });
      activeA.classList.add('active');
      if (topA && topA !== activeA) topA.classList.add('active');
      current = activeA;
      var r = activeA.getBoundingClientRect(), nr = nav.getBoundingClientRect();
      if (r.top < nr.top || r.bottom > nr.bottom) nav.scrollTop += r.top - nr.top - nr.height / 3;
    }
    toTop.classList.toggle('show', window.scrollY > 800);
  }
  window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(spy); } }, { passive: true });
  window.addEventListener('resize', spy);
  toTop.addEventListener('click', function () { window.scrollTo(0, 0); });
  spy();
})();
