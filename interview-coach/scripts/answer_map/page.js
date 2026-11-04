(function () {
  var qs = Array.prototype.slice.call(document.querySelectorAll('details.q'));
  var groups = Array.prototype.slice.call(document.querySelectorAll('.group'));
  var input = document.getElementById('q');
  var level = document.getElementById('lvl');
  var count = document.getElementById('count');
  var empty = document.getElementById('empty');
  var chips = document.getElementById('topics');
  var topic = '';

  // Per-viewer convenience only; the page works the same when storage is blocked.
  function load(key) { try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch (e) { return null; } }
  function save(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* storage unavailable */ } }

  var topics = [];
  qs.forEach(function (q) { var t = q.dataset.topic; if (topics.indexOf(t) < 0) topics.push(t); });
  [''].concat(topics).forEach(function (t) {
    var b = document.createElement('button');
    b.type = 'button';
    b.textContent = t || 'All topics';
    if (!t) b.className = 'on';
    b.addEventListener('click', function () {
      topic = t;
      Array.prototype.forEach.call(chips.children, function (c) { c.classList.toggle('on', c === b); });
      apply();
    });
    chips.appendChild(b);
  });

  function apply() {
    var words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
    var lv = level.value, shown = 0;
    qs.forEach(function (q) {
      var hit = (!topic || q.dataset.topic === topic) && (!lv || q.dataset.level === lv) &&
        words.every(function (w) { return q.dataset.text.indexOf(w) >= 0; });
      q.hidden = !hit;
      if (hit) shown++;
    });
    groups.forEach(function (g) { g.hidden = !g.querySelector('details.q:not([hidden])'); });
    empty.hidden = shown > 0;
    count.textContent = shown + (shown === 1 ? ' answer' : ' answers');
  }
  var timer;
  input.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(apply, 120); });
  level.addEventListener('change', apply);

  function mode(short) {
    document.body.classList.toggle('short', short);
    document.getElementById('m-short').classList.toggle('on', short);
    document.getElementById('m-full').classList.toggle('on', !short);
    save('iam-short', short);
  }
  document.getElementById('m-full').addEventListener('click', function () { mode(false); });
  document.getElementById('m-short').addEventListener('click', function () { mode(true); });
  if (load('iam-short')) mode(true);

  var done = load('iam-done') || {};
  document.querySelectorAll('input[data-done]').forEach(function (c) {
    var q = c.closest('details.q');
    c.checked = !!done[c.dataset.done];
    q.classList.toggle('is-done', c.checked);
    c.addEventListener('change', function () {
      if (c.checked) done[c.dataset.done] = 1; else delete done[c.dataset.done];
      q.classList.toggle('is-done', c.checked);
      save('iam-done', done);
      var row = document.querySelector('input[data-k="' + c.dataset.done + '"]');
      if (row) row.checked = c.checked;
    });
  });

  // A link to an answer must work even if filters currently hide it.
  function reveal(id) {
    var el = document.getElementById(id);
    if (!el) return;
    input.value = ''; level.value = ''; topic = '';
    Array.prototype.forEach.call(chips.children, function (c, i) { c.classList.toggle('on', i === 0); });
    apply();
    if (el.tagName === 'DETAILS') el.open = true;
    el.scrollIntoView();
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href^="#"]');
    if (!a) return;
    var id = a.getAttribute('href').slice(1);
    if (/^(q-|bank-)/.test(id)) { e.preventDefault(); reveal(id); }
  });
  if (/^#(q-|bank-)/.test(location.hash)) reveal(location.hash.slice(1));

  document.querySelectorAll('[data-copy]').forEach(function (b) {
    b.addEventListener('click', function () {
      var code = b.parentNode.querySelector('pre code');
      function selectIt() {
        var r = document.createRange(); r.selectNodeContents(code);
        var s = getSelection(); s.removeAllRanges(); s.addRange(r);
        b.textContent = 'Press Ctrl+C to copy';
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(code.textContent).then(function () { b.textContent = 'Copied'; }, selectIt);
      } else { selectIt(); }
    });
  });

  // ---- plans by experience
  var plans = JSON.parse(document.getElementById('plan-data').textContent);
  var GROUPS = [['core', 'Focus first', 'These topics decide the interview at this level. Spend most of your time here.'],
    ['also', 'Also prepare', 'Expect questions here, with less depth. Cover the key answers.'],
    ['aware', 'Know the basics', 'A short list, so a question here doesn\'t catch you out.']];
  var pick = document.getElementById('tp'), body = document.getElementById('tp-body');
  var chosen = load('iam-track') || 'experienced', onlyAnswers = false;
  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  function key(r) { return r.a ? r.a.slice(2) : 'x-' + r.id; }
  function renderPlan() {
    var p = plans.filter(function (x) { return x.id === chosen; })[0] || plans[0];
    pick.innerHTML = plans.map(function (x) {
      return '<button type="button" data-t="' + x.id + '" aria-pressed="' + (x === p) + '" class="' + (x === p ? 'on' : '') + '"><b>' + esc(x.label) + '</b><span>' + esc(x.range) + '</span></button>';
    }).join('');
    var all = p.topics.reduce(function (a, t) { return a.concat(t.rows); }, []);
    var withAns = all.filter(function (r) { return r.a; }).length, dn = all.filter(function (r) { return done[key(r)]; }).length;
    var html = '<div class="tp-sum"><h3>' + esc(p.title) + '</h3><p>' + esc(p.expect) + '</p><p><strong>How to prepare:</strong> ' + esc(p.advice) + '</p>' +
      '<div class="tp-stats"><span>' + p.total + ' questions</span><span>about ' + p.hours + ' hours at 5 minutes each</span>' +
      p.stage_order.filter(function (s) { return p.stages[s]; }).map(function (s) { return '<span>' + p.stages[s] + ' ' + p.stage_label[s].toLowerCase() + '</span>'; }).join('') + '</div>' +
      '<div class="bar"><i style="width:' + (100 * dn / all.length) + '%"></i></div><p class="note">' + dn + ' of ' + all.length + ' ticked. Your ticks are saved in this browser only.</p>' +
      '<p class="note">' + withAns + ' of these ' + all.length + ' questions have a full answer on this page. The rest are listed so you can practise them or look them up.</p>' +
      '<label class="tp-opt"><input type="checkbox" id="tp-only"' + (onlyAnswers ? ' checked' : '') + '> Only show questions with an answer here</label></div>';
    GROUPS.forEach(function (g) {
      var ts = p.topics.filter(function (t) { return t.weight === g[0]; });
      if (!ts.length) return;
      html += '<h3 class="tp-group">' + g[1] + '</h3><p>' + g[2] + '</p>';
      ts.forEach(function (t, i) {
        var rows = onlyAnswers ? t.rows.filter(function (r) { return r.a; }) : t.rows;
        html += '<details class="tp-topic"' + (g[0] === 'core' && i === 0 ? ' open' : '') + '><summary><b>' + esc(t.title) + '</b><span class="n">' + rows.length + ' questions</span><span class="why">' + esc(t.why) + '</span></summary>';
        var last = null;
        rows.forEach(function (r) {
          if (r.l !== last) { last = r.l; html += '<div class="tp-stage">' + p.stage_label[r.l] + '</div>'; }
          html += '<div class="tp-row"><input type="checkbox" data-k="' + key(r) + '" aria-label="I can say this aloud"' + (done[key(r)] ? ' checked' : '') + '>' +
            (r.a ? '<button type="button" class="t" data-a="' + r.a + '" aria-expanded="false">' + r.h + '</button>' : '<span class="q0">' + r.h + '</span>') +
            '<span class="tag' + (r.r ? ' rep' : '') + '">' + (r.r ? 'reported' : (r.a ? '' : 'question only')) + '</span></div>';
        });
        html += '</details>';
      });
    });
    body.innerHTML = html;
    document.getElementById('tp-only').onchange = function (e) { onlyAnswers = e.target.checked; renderPlan(); };
  }
  pick.addEventListener('click', function (e) {
    var b = e.target.closest('[data-t]');
    if (b) { chosen = b.dataset.t; save('iam-track', chosen); renderPlan(); }
  });
  body.addEventListener('click', function (e) {
    var b = e.target.closest('button.t');
    if (!b) return;
    var row = b.parentNode, open = row.querySelector('.tp-ans');
    b.setAttribute('aria-expanded', String(!open));
    if (open) { open.remove(); return; }
    var box = document.createElement('div'); box.className = 'tp-ans';
    document.getElementById(b.dataset.a).querySelectorAll('.ans > .sec').forEach(function (s) { box.appendChild(s.cloneNode(true)); });
    row.appendChild(box);
  });
  body.addEventListener('change', function (e) {
    var k = e.target.dataset && e.target.dataset.k;
    if (!k) return;
    if (e.target.checked) done[k] = 1; else delete done[k];
    save('iam-done', done);
    var c = document.querySelector('input[data-done="' + k + '"]');
    if (c && c.checked !== e.target.checked) { c.checked = e.target.checked; c.dispatchEvent(new Event('change', { bubbles: true })); }
  });
  renderPlan();

  apply();
})();
