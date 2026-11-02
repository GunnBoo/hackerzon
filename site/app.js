'use strict';
/* Hackerzon: an Amazon-style store of products Hacker News keeps recommending.
   Plain JS, no build step. Data comes from data/products.json (+ data/m/<asin>.json per product). */

const DEPTS = [
  ['Programming', 'book'], ['Computer Science & Math', 'book'], ['Science & Engineering', 'book'],
  ['Business & Startups', 'book'], ['Economics & Finance', 'book'], ['History & Biography', 'book'],
  ['Psychology & Self-Help', 'book'], ['Philosophy & Society', 'book'], ['Fiction & Sci-Fi', 'book'],
  ['Design, Writing & Art', 'book'], ['Food, Health & Home', 'book'],
  ['Computers & Accessories', 'gear'], ['Electronics & Gadgets', 'gear'], ['Maker & Tools', 'gear'],
  ['Home & Kitchen', 'gear'], ['Health & Personal Care', 'gear'], ['Outdoors & Travel', 'gear'],
  ['Office & School', 'gear'], ['Toys, Games & Kids', 'gear'], ['Movies, Music & Games', 'gear'],
];
const HUES = {};
DEPTS.forEach(([d], i) => { HUES[d] = Math.round((i * 360) / DEPTS.length + 200) % 360; });

const S = { prods: [], by: {}, stats: {}, deptCount: {}, maxSc: 1, mcache: {} };
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmtMonth = (m) => { if (!m) return ''; const [y, mo] = m.split('-'); return new Date(+y, +mo - 1, 1).toLocaleString('en-US', { month: 'short', year: 'numeric' }); };
const plural = (n, w) => `${n} ${w}${n === 1 ? '' : 's'}`;
// Items found only by name (Ask HN) or via other stores have no Amazon ID: link to a plain Amazon search instead.
const amazonUrl = (p) => (p.amz ? `https://www.amazon.com/dp/${p.amz}` : `https://www.amazon.com/s?k=${encodeURIComponent(p.t + (p.by ? ' ' + p.by : ''))}`);
const amazonLabel = (p) => (p.amz ? 'View on Amazon' : 'Search on Amazon');
const SRC_NAME = { amazon: 'Amazon links', askhn: 'Ask HN threads', goodreads: 'Goodreads links', oreilly: "O'Reilly links", pragprog: 'Pragmatic Bookshelf links', manning: 'Manning links', nostarch: 'No Starch links', mitpress: 'MIT Press links', bookshop: 'Bookshop.org links', press: 'Princeton UP links', cambridge: 'Cambridge UP links', springer: 'Springer links', abebooks: 'AbeBooks links', bhphotovideo: 'B&H links', etsy: 'Etsy links' };

/* ---------- local state (no accounts) ---------- */
const store = {
  get(k, d) { try { const v = localStorage.getItem('hz:' + k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem('hz:' + k, JSON.stringify(v)); } catch { /* private mode */ } },
};
const U = {
  list: store.get('list', []),
  liked: store.get('liked', []),
  hist: store.get('hist', []),
  save() { store.set('list', this.list); store.set('liked', this.liked); store.set('hist', this.hist); updateCount(); },
};
function toggle(arr, a) { const i = arr.indexOf(a); if (i >= 0) arr.splice(i, 1); else arr.unshift(a); return i < 0; }
function updateCount() { $('#listCount').textContent = U.list.length; }
function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('show'), 1800); }

/* ---------- images: Amazon by ASIN -> other editions -> Open Library cover -> drawn placeholder ---------- */
function imgSrcs(p) {
  const out = p.amz ? [p.amz, ...(p.ed || [])].slice(0, 3).map((a) => `https://m.media-amazon.com/images/P/${a}.01._SCLZZZZZZZ_.jpg`) : [];
  if (p.im) out.unshift(p.im);  // picture we found and host ourselves (Wikimedia Commons, Open Library, ...)
  if (p.isbn) out.push(`https://covers.openlibrary.org/b/isbn/${p.amz}-L.jpg?default=false`);
  if (p.oc) out.push(`https://covers.openlibrary.org/b/id/${p.oc}-L.jpg?default=false`);
  if (!out.length) out.push('data:,');
  return out;
}
function placeholder(p, big) {
  const h = HUES[p.d] ?? 210;
  return `<div class="ph${big ? ' big' : ''}" style="background:linear-gradient(150deg,hsl(${h} 45% 34%),hsl(${(h + 40) % 360} 50% 22%))">
    <div class="pt">${esc(p.t)}</div><div class="pb">${esc(p.by)}</div></div>`;
}
// Published build: covers ship as data: URIs in shard files (the artifact sandbox blocks outside images).
const BUNDLE = !!window.HZ_BUNDLE;
const shardCache = {};
const shard = (kind, k) => (shardCache[kind + k] ||= fetch(`data/${kind}/${k}.json`).then((r) => r.json()).catch(() => ({})));
function hydrate() {
  document.querySelectorAll('.im[data-a]:not([data-h])').forEach((el) => {
    el.dataset.h = '1';
    const p = S.by[el.dataset.a]; if (!p) return;
    shard('img', p.sh).then((m) => { el.innerHTML = m[p.a] ? `<img alt="" src="${m[p.a]}">` : placeholder(p, el.dataset.big === '1'); });
  });
}
function img(p, big = false) {
  if (BUNDLE) return `<div class="im" data-a="${p.a}" data-big="${big ? 1 : 0}"></div>`;
  return `<div class="im"><img alt="" loading="lazy" referrerpolicy="no-referrer" data-a="${p.a}" data-i="0" data-big="${big ? 1 : 0}" src="${imgSrcs(p)[0]}"></div>`;
}
function onImgLoad(el) { if (el.naturalWidth < 5) onImgFail(el); }
function onImgFail(el) {
  const p = S.by[el.dataset.a]; if (!p) return;
  const srcs = imgSrcs(p); const i = +el.dataset.i + 1;
  if (i < srcs.length) { el.dataset.i = i; el.src = srcs[i]; return; }
  el.parentElement.innerHTML = placeholder(p, el.dataset.big === '1');
}
document.addEventListener('load', (e) => { if (e.target.tagName === 'IMG' && e.target.dataset.a) onImgLoad(e.target); }, true);
document.addEventListener('error', (e) => { if (e.target.tagName === 'IMG' && e.target.dataset.a) onImgFail(e.target); }, true);
// Some image requests hang; if an on-screen image hasn't loaded after 25s, move to the next source.
const seenAt = new WeakMap();
setInterval(() => {
  const now = Date.now();
  document.querySelectorAll('.im img').forEach((el) => {
    if (el.complete) return;
    const r = el.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight + 200) return;
    const key = el.src;
    const s = seenAt.get(el);
    if (!s || s.src !== key) { seenAt.set(el, { src: key, t: now }); return; }
    if (now - s.t > 25000) onImgFail(el);  // uncached Open Library covers can take 15s+ via archive.org
  });
}, 1500);

/* ---------- small renderers ---------- */
const up = (p, unit = true) => `<span class="up"><span class="tr">▲</span><span class="n">${Math.round(p.sc)}</span>${unit ? '<span class="u">HN score</span>' : ''}</span>`;
function meter(p) {
  const lvl = Math.max(1, Math.min(5, Math.ceil((Math.log(1 + p.sc) / Math.log(1 + S.maxSc)) * 5)));
  return `<span class="meter" title="${esc(`Recommended in ~${Math.round(p.sc)} different months`)}"><span class="bars">${[1, 2, 3, 4, 5].map((i) => `<i class="${i <= lvl ? 'on' : ''}"></i>`).join('')}</span>${p.na.toLocaleString()} HNers</span>`;
}
function imgCredit(p) {
  const c = p.ic;
  if (c && c.src === 'Wikimedia Commons') return `Photo${c.artist ? ' by ' + esc(c.artist) : ''}, <a href="${esc(c.url)}" target="_blank" rel="noopener noreferrer">${esc(c.license || 'free license')}, via Wikimedia Commons</a>`;
  if (c) return `Cover via <a href="${esc(c.url)}" target="_blank" rel="noopener noreferrer">${esc(c.src)}</a>, not an A/B-tested hero shot.`;
  return `${p.amz ? 'Image from Amazon' : p.oc ? 'Cover from Open Library' : 'No product photo'}, not an A/B-tested hero shot.`;
}
const byline = (p) => (p.k === 'book' ? `by ${esc(p.by)}` : esc(p.by));
const choice = (p) => (p.hc ? `<span class="choice"><b>HN's</b> Choice</span>` : '');
const gem = (p) => (p.gem ? `<span class="gemb">Hidden gem</span>` : '');
const years = (p) => `${p.f.slice(0, 4)}–${p.l.slice(0, 4)}`;

function stripItem(p, sub) {
  return `<a class="it" href="#/p/${p.a}">${img(p)}<div class="t">${esc(p.t)}</div><div class="t2">${sub ?? `${meter(p)}`}</div></a>`;
}
function strip(title, items, more) {
  if (!items.length) return '';
  return `<section class="row"><div class="row-h"><h2>${esc(title)}</h2>${more ? `<a href="${more}">See more</a>` : ''}</div>
    <div class="strip">${items.map((p) => stripItem(p)).join('')}</div></section>`;
}
function card(title, items, more, moreLabel = 'See more', why = '') {
  if (!items.length) return '';
  return `<div class="card"><h2>${esc(title)}</h2>${why ? `<div class="why">${esc(why)}</div>` : ''}<div class="grid4">${items.slice(0, 4).map((p) => `<a href="#/p/${p.a}">${img(p)}<div class="t">${esc(p.t)}</div></a>`).join('')}</div>
    ${more ? `<a class="more" href="${more}">${esc(moreLabel)}</a>` : ''}</div>`;
}

/* ---------- recommendations from likes / list / history ---------- */
function recsFor(seeds, n = 20) {
  const sc = {}; const seen = new Set([...U.list, ...U.liked, ...U.hist.slice(0, 30)]);
  seeds.forEach(([a, w]) => {
    const p = S.by[a]; if (!p) return;
    (p.rel || []).forEach((b, i) => { if (!seen.has(b) && S.by[b]) sc[b] = (sc[b] || 0) + w * (1 - i / 14); });
    S.prods.filter((q) => q.sub === p.sub && q.d === p.d && !seen.has(q.a)).slice(0, 6).forEach((q) => { sc[q.a] = (sc[q.a] || 0) + w * 0.35; });
  });
  return Object.entries(sc).sort((x, y) => y[1] - x[1]).slice(0, n).map(([a]) => S.by[a]);
}
function seeds() {
  return [...U.liked.map((a) => [a, 3]), ...U.list.map((a) => [a, 2]), ...U.hist.slice(0, 12).map((a, i) => [a, 1.2 - i * 0.07])];
}

/* ---------- pages ---------- */
function home() {
  const P = S.prods; const st = S.stats;
  // home cards look best with real photos: items with an Amazon image or a cover go first (ranking order kept within each group)
  const withPic = (arr) => [...arr.filter((p) => p.amz || p.oc), ...arr.filter((p) => !(p.amz || p.oc))];
  const books = withPic(P.filter((p) => p.k === 'book')); const gear = withPic(P.filter((p) => p.k !== 'book'));
  const gems = withPic(P.filter((p) => p.gem));
  const recent = [...P].filter((p) => p.l >= '2025-01').sort((a, b) => (b.y['2026'] || 0) + (b.y['2025'] || 0) - ((a.y['2026'] || 0) + (a.y['2025'] || 0)) || b.sc - a.sc);
  const timeless = withPic(P.filter((p) => p.f <= '2011-12' && p.l >= '2023-01'));
  const histP = U.hist.map((a) => S.by[a]).filter(Boolean);
  const recs = seeds().length ? recsFor(seeds(), 24) : [];
  const deptRows = DEPTS.map(([d]) => d).filter((d) => (S.deptCount[d] || 0) >= 6);
  const pick = (arr, k) => { const out = []; const used = new Set(); for (const p of arr) { if (used.has(p.a)) continue; used.add(p.a); out.push(p); if (out.length >= k) break; } return out; };

  $('#app').innerHTML = `
  <div class="hero">
    <h1>Only the stuff Hacker News keeps telling each other to buy.</h1>
    <p>We read ${(st.scanned + (st.scanned_stores || 0)).toLocaleString()} HN comments that link Amazon and other stores, plus ${(st.askhn_answers || 0).toLocaleString()} answers in ${(st.askhn_threads || 0).toLocaleString()} "Ask HN" recommendation threads, from ${st.from.slice(0, 4)} to ${st.to.slice(0, 4)}. We kept the products different people recommended again and again, and threw out everything else.</p>
    <div class="stats">
      <div><b>${st.products.toLocaleString()}</b>products</div>
      <div><b>${st.people.toLocaleString()}</b>HN recommenders</div>
      <div><b>${st.mentions.toLocaleString()}</b>comments as reviews</div>
      <div><b>0</b>sponsored results</div>
    </div>
    <div class="nope"><span><s>Sponsored</s></span><span><s>Ads</s></span><span><s>Upsells</s></span><span><s>Subscribe &amp; Save</s></span><span><s>Affiliate tags</s></span><span><s>AI slop books</s></span><span><s>Sign in</s></span></div>
  </div>
  <div class="cards">
    ${histP.length ? card('Pick up where you left off', histP, '#/history', 'View your history') : card('The HN canon', books, '#/s?sort=score&k=book', 'Shop the most recommended books', 'Recommended in the most different months')}
    ${card('Hardware HN swears by', gear, '#/s?k=gear', 'See all gear')}
    ${card('Hidden gems', gems, '#/s?gem=1', 'See all hidden gems', 'Loved on HN, little known elsewhere')}
    ${card('Still recommended after 15 years', timeless, '#/s?sort=span', 'See long-runners')}
  </div>
  ${recs.length ? strip('Recommended for you, based on what you looked at', recs, '#/foryou') : ''}
  ${strip('Recommended on HN lately', pick(recent, 20), '#/s?sort=recent')}
  ${deptRows.map((d) => strip(`Most recommended in ${d}`, P.filter((p) => p.d === d).slice(0, 18), `#/s?d=${encodeURIComponent(d)}`)).join('')}
  `;
}

function parseQuery(qs) { const o = {}; new URLSearchParams(qs).forEach((v, k) => { o[k] = v; }); return o; }
function toQuery(o) { const u = new URLSearchParams(); Object.entries(o).forEach(([k, v]) => { if (v !== '' && v != null) u.set(k, v); }); return u.toString(); }

function searchScore(p, terms) {
  let s = 0;
  const t = p.t.toLowerCase(); const by = p.by.toLowerCase();
  const tg = p.tg.join(' ').toLowerCase(); const cat = (p.d + ' ' + p.sub).toLowerCase();
  const body = (p.s + ' ' + p.w + ' ' + p.ab.join(' ')).toLowerCase();
  for (const w of terms) {
    let hit = 0;
    if (t.includes(w)) hit += new RegExp(`\\b${w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`).test(t) ? 6 : 3;
    if (by.includes(w)) hit += 5;
    if (tg.includes(w)) hit += 3;
    if (cat.includes(w)) hit += 2;
    if (body.includes(w)) hit += 1;
    if (!hit) return 0;
    s += hit;
  }
  return s * (1 + Math.log(1 + p.sc) / 3);
}

const SORTS = { score: 'Most recommended', people: 'Most recommenders', span: 'Longest-running on HN', recent: 'Recently recommended', oldest: 'Oldest classics', gems: 'Hidden gems first' };
function search(qs) {
  const o = parseQuery(qs);
  const q = (o.q || '').trim();
  const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
  let rows = S.prods.map((p) => [p, terms.length ? searchScore(p, terms) : p.sc]);
  rows = rows.filter(([, s]) => s > 0);
  const base = rows.map(([p]) => p);
  const f = (p) => (!o.d || p.d === o.d) && (!o.sub || p.sub === o.sub)
    && (!o.k || (o.k === 'book' ? p.k === 'book' : o.k === 'gear' ? p.k === 'product' : p.k === o.k))
    && (!o.gem || p.gem) && (!o.aged || p.aged === o.aged) && (!o.min || p.sc >= +o.min)
    && (!o.era || p.f.slice(0, 4) >= o.era.split('-')[0] && p.f.slice(0, 4) <= o.era.split('-')[1]);
  rows = rows.filter(([p]) => f(p));
  const sort = o.sort || (terms.length ? 'relevance' : 'score');
  const span = (p) => +p.l.slice(0, 4) - +p.f.slice(0, 4);
  const cmp = {
    relevance: (a, b) => b[1] - a[1], score: (a, b) => b[0].sc - a[0].sc, people: (a, b) => b[0].na - a[0].na,
    span: (a, b) => span(b[0]) - span(a[0]) || b[0].sc - a[0].sc, recent: (a, b) => b[0].l.localeCompare(a[0].l) || b[0].sc - a[0].sc,
    oldest: (a, b) => a[0].f.localeCompare(b[0].f) || b[0].sc - a[0].sc, gems: (a, b) => (b[0].gem - a[0].gem) || b[0].sc - a[0].sc,
  }[sort] || ((a, b) => b[0].sc - a[0].sc);
  rows.sort(cmp);
  const page = +(o.p || 1); const per = 24; const total = rows.length; const pages = Math.max(1, Math.ceil(total / per));
  const shown = rows.slice((page - 1) * per, page * per).map(([p]) => p);
  const link = (patch) => '#/s?' + toQuery({ ...o, p: '', ...patch });

  // facet counts (computed against the other filters)
  const cnt = (pred) => base.filter((p) => pred(p) && (!o.k || f({ ...p, d: o.d || p.d, sub: o.sub || p.sub }))).length;
  const deptList = DEPTS.map(([d]) => [d, base.filter((p) => p.d === d && (!o.k || (o.k === 'book' ? p.k === 'book' : p.k !== 'book'))).length]).filter(([, n]) => n);
  const subs = o.d ? Object.entries(base.filter((p) => p.d === o.d).reduce((m, p) => { m[p.sub] = (m[p.sub] || 0) + 1; return m; }, {})).sort((a, b) => b[1] - a[1]) : [];
  const title = q ? `"${esc(q)}"` : o.sub ? esc(o.sub) : o.d ? esc(o.d) : o.gem ? 'Hidden gems' : o.k === 'book' ? 'Books' : o.k === 'gear' ? 'Gear' : 'Everything';

  $('#app').innerHTML = `
  <div class="res-bar">
    <button class="btn gh sm filters-toggle" onclick="document.querySelector('.side').classList.toggle('open')">Filters</button>
    <div class="q">${total ? `${(page - 1) * per + 1}-${Math.min(page * per, total)} of ${total.toLocaleString()}` : 'No'} results for <b>${title}</b>${o.d && q ? ` in ${esc(o.d)}` : ''}</div>
    <select aria-label="Sort by" onchange="go('${link({ sort: '' }).replace(/'/g, "\\'")}&sort='+this.value)">
      ${terms.length ? `<option value="relevance" ${sort === 'relevance' ? 'selected' : ''}>Sort by: Relevance</option>` : ''}
      ${Object.entries(SORTS).map(([k, v]) => `<option value="${k}" ${sort === k ? 'selected' : ''}>Sort by: ${v}</option>`).join('')}
    </select>
  </div>
  <div class="res">
    <aside class="side">
      <h4>Type</h4>
      <a class="${!o.k ? 'on' : ''}" href="${link({ k: '' })}">Everything</a>
      <a class="${o.k === 'book' ? 'on' : ''}" href="${link({ k: 'book', d: '', sub: '' })}">Books</a>
      <a class="${o.k === 'gear' ? 'on' : ''}" href="${link({ k: 'gear', d: '', sub: '' })}">Products &amp; gear</a>
      <a class="${o.k === 'media' ? 'on' : ''}" href="${link({ k: 'media', d: '', sub: '' })}">Movies, music &amp; courses</a>
      <h4>Department</h4>
      ${o.d ? `<a class="clear" href="${link({ d: '', sub: '' })}">‹ Any department</a><a class="on" href="${link({ sub: '' })}">${esc(o.d)}</a>
        ${subs.map(([s, n]) => `<a class="sub ${o.sub === s ? 'on' : ''}" href="${link({ sub: s })}">${esc(s)} <span style="color:#888">(${n})</span></a>`).join('')}`
    : deptList.map(([d, n]) => `<a href="${link({ d, sub: '' })}">${esc(d)} <span style="color:#888">(${n})</span></a>`).join('')}
      <h4>HN score</h4>
      ${[['', 'Any'], ['20', '▲20 & up'], ['10', '▲10 & up'], ['5', '▲5 & up']].map(([v, l]) => `<a class="${(o.min || '') === v ? 'on' : ''}" href="${link({ min: v })}">${l}</a>`).join('')}
      <h4>First recommended on HN</h4>
      ${[['', 'Any time'], ['2007-2011', '2007–2011'], ['2012-2016', '2012–2016'], ['2017-2021', '2017–2021'], ['2022-2026', '2022–2026']].map(([v, l]) => `<a class="${(o.era || '') === v ? 'on' : ''}" href="${link({ era: v })}">${l}</a>`).join('')}
      <h4>How it holds up</h4>
      ${[['', 'Any'], ['timeless', 'Timeless'], ['still useful', 'Still useful'], ['dated', 'Dated'], ['historical', 'Historical']].map(([v, l]) => `<a class="${(o.aged || '') === v ? 'on' : ''}" href="${link({ aged: v })}">${l}</a>`).join('')}
      <h4>Popularity</h4>
      <a class="${o.gem ? 'on' : ''}" href="${link({ gem: o.gem ? '' : '1' })}">${o.gem ? '✓ ' : ''}Hidden gems only</a>
    </aside>
    <div>
      <div class="rlist">
        ${shown.length ? shown.map(resultRow).join('') : `<div class="empty">Nothing HN recommends matches that. Try fewer words, or <a href="#/s">browse everything</a>.</div>`}
      </div>
      ${pages > 1 ? `<div class="pager">
        <button ${page <= 1 ? 'disabled' : ''} onclick="go('${link({ p: page - 1 })}')">‹ Previous</button>
        ${pageNums(page, pages).map((n) => (n === '…' ? '<span>…</span>' : `<button class="${n === page ? 'on' : ''}" onclick="go('${link({ p: n })}')">${n}</button>`)).join('')}
        <button ${page >= pages ? 'disabled' : ''} onclick="go('${link({ p: page + 1 })}')">Next ›</button></div>` : ''}
    </div>
  </div>`;
}
function pageNums(p, n) { const s = new Set([1, n, p - 1, p, p + 1].filter((x) => x >= 1 && x <= n)); const a = [...s].sort((x, y) => x - y); const out = []; a.forEach((x, i) => { if (i && x - a[i - 1] > 1) out.push('…'); out.push(x); }); return out; }

function resultRow(p) {
  const inList = U.list.includes(p.a);
  return `<div class="ritem">
    <a href="#/p/${p.a}">${img(p)}</a>
    <div style="min-width:0">
      <div style="display:flex;gap:6px;margin-bottom:4px">${choice(p)}${gem(p)}</div>
      <h3><a href="#/p/${p.a}">${esc(p.t)}</a></h3>
      <div class="by">${byline(p)} · ${esc(p.sub || p.d)}</div>
      <div>${meter(p)}</div>
      <div style="margin-top:6px">${up(p)} <span class="u" style="color:var(--muted);font-size:13px">· on HN ${years(p)}</span></div>
      <div class="sum">${esc(p.w || p.s)}</div>
      ${p.q && p.q.t ? `<div class="q">“${esc(p.q.t)}”</div>` : ''}
      <div class="acts"><button class="btn sm" onclick="addList('${p.a}', this)">${inList ? 'In your list ✓' : 'Add to List'}</button>
      <a class="btn gh sm" href="${amazonUrl(p)}" target="_blank" rel="noopener noreferrer">${amazonLabel(p)}</a></div>
    </div></div>`;
}

async function loadMentions(a) {
  if (S.mcache[a]) return S.mcache[a];
  if (BUNDLE) { const m = await shard('ms', S.by[a].sh); S.mcache[a] = m[a] || []; return S.mcache[a]; }
  const r = await fetch(`data/m/${a}.json`); const j = await r.json(); S.mcache[a] = j; return j;
}

function product(a) {
  const p = S.by[a];
  if (!p) { $('#app').innerHTML = `<div class="empty">That product isn't one HN keeps recommending. <a href="#/">Back to the store</a></div>`; return; }
  U.hist = [a, ...U.hist.filter((x) => x !== a)].slice(0, 200); U.save();
  const inList = U.list.includes(a); const liked = U.liked.includes(a);
  const deptRank = S.prods.filter((q) => q.d === p.d).findIndex((q) => q.a === a) + 1;
  const subRank = S.prods.filter((q) => q.d === p.d && q.sub === p.sub).findIndex((q) => q.a === a) + 1;
  const rel = (p.rel || []).map((b) => S.by[b]).filter(Boolean);
  const same = S.prods.filter((q) => q.sub === p.sub && q.d === p.d && q.a !== a && !p.rel.includes(q.a)).slice(0, 18);
  const span = +p.l.slice(0, 4) - +p.f.slice(0, 4) + 1;
  document.title = `${p.t} · Hackerzon`;

  $('#app').innerHTML = `
  <div class="crumbs white"><a href="#/s?d=${encodeURIComponent(p.d)}">${esc(p.d)}</a> › <a href="#/s?d=${encodeURIComponent(p.d)}&sub=${encodeURIComponent(p.sub)}">${esc(p.sub)}</a></div>
  <div class="pdp">
    <div class="gallery">${img(p, true)}<div class="note">${imgCredit(p)}</div></div>
    <div style="min-width:0">
      <h1>${esc(p.t)}</h1>
      <div class="by">${p.k === 'book' ? `by <a href="#/s?q=${encodeURIComponent(p.by.split(/,| et al/)[0])}">${esc(p.by)}</a> (Author)` : `Brand: <a href="#/s?q=${encodeURIComponent(p.by)}">${esc(p.by)}</a>`}</div>
      <div class="rate">${meter(p)} <a href="#reviews" onclick="document.getElementById('reviews').scrollIntoView({behavior:'smooth'});return false;">${plural(p.n, 'HN comment')}</a> ${choice(p)} ${gem(p)}</div>
      ${p.hc ? `<div style="font-size:13px;margin-top:-2px">HN's Choice in <a href="#/s?d=${encodeURIComponent(p.d)}&sub=${encodeURIComponent(p.sub)}">${esc(p.sub)}</a>: the most recommended item in its category.</div>` : ''}
      <hr>
      <div class="bigup">${up(p, false)} <span style="font-size:14px">months with an HN recommendation</span></div>
      <div style="font-size:13px;color:var(--muted);margin-top:4px">#${deptRank} in ${esc(p.d)} · #${subRank} in ${esc(p.sub)} · recommended over ${plural(span, 'year')}</div>
      <hr>
      <div class="about">
        <h3>Why Hacker News recommends it</h3>
        <p style="margin:0">${esc(p.w)}</p>
        ${p.q && p.q.t ? `<blockquote style="margin:10px 0 0;padding:6px 12px;border-left:3px solid var(--hn);background:#fff8f2;font-style:italic">“${esc(p.q.t)}”</blockquote>` : ''}
        <h3>About this item</h3>
        <ul>${[p.s, ...p.ab].filter(Boolean).map((b) => `<li>${esc(b)}</li>`).join('')}</ul>
        <h3>Details</h3>
        <table class="facts">
          <tr><td>First recommended on HN</td><td>${fmtMonth(p.f)}</td></tr>
          <tr><td>Most recently</td><td>${fmtMonth(p.l)}</td></tr>
          <tr><td>Recommenders</td><td>${p.na.toLocaleString()} different HN users, ${p.nm} different months</td></tr>
          <tr><td>How it holds up</td><td>${esc(p.aged ? p.aged[0].toUpperCase() + p.aged.slice(1) : '')}</td></tr>
          ${p.pub ? `<tr><td>Published</td><td>${esc(p.pub)}${p.pg ? ` · ${p.pg} pages` : ''}</td></tr>` : ''}
          <tr><td>Found on HN via</td><td>${(p.src || ['amazon']).map((k) => SRC_NAME[k] || k).join(', ')}</td></tr>
          ${p.amz ? `<tr><td>ASIN</td><td>${p.amz}${p.ed.length ? ` <span style="color:var(--muted)">(+${plural(p.ed.length, 'other edition')} merged)</span>` : ''}</td></tr>` : ''}
        </table>
        <div class="tags">${p.tg.map((t) => `<a href="#/s?q=${encodeURIComponent(t)}">${esc(t)}</a>`).join('')}</div>
      </div>
    </div>
    <div class="buybox">
      ${up(p)}
      <div class="instock">Recommended on HN</div>
      <div class="clean">
        <div>✓ No sponsored placement</div><div>✓ No affiliate tag in our link</div>
        <div>✓ No Subscribe &amp; Save upsell</div><div>✓ Ranked only by HN recommendations</div>
      </div>
      <button class="btn wide" id="listBtn" onclick="addList('${a}', this)">${inList ? 'In your list ✓' : 'Add to List'}</button>
      <a class="btn or wide" href="${amazonUrl(p)}" target="_blank" rel="noopener noreferrer">${amazonLabel(p)}</a>
      ${Object.entries(p.lk || {}).map(([n, u]) => `<a class="btn gh wide" href="${esc(u)}" target="_blank" rel="noopener noreferrer">View at ${esc(n)}</a>`).join('')}
      <button class="btn gh wide" onclick="likeIt('${a}', this)">${liked ? '♥ Liked' : '♡ Like'}</button>
      <div class="small">Prices change by the minute on Amazon, so we don't show them. Your list, likes and history stay in this browser only.</div>
    </div>
  </div>
  ${strip('HNers who recommended this also recommended', rel)}
  ${strip(`More in ${p.sub}`, same, `#/s?d=${encodeURIComponent(p.d)}&sub=${encodeURIComponent(p.sub)}`)}
  <section class="section" id="reviews">
    <h2>What Hacker News said</h2>
    <div class="sub">Every comment that linked this product, oldest to newest. Labels are Claude's reading of each comment.</div>
    <div class="reviews"><div class="histo" id="histo"></div><div id="rvlist"><div class="empty">Loading comments…</div></div></div>
  </section>`;
  window.scrollTo(0, 0);
  loadMentions(a).then((ms) => renderReviews(p, ms, 'all')).catch(() => { $('#rvlist').innerHTML = '<div class="empty">Couldn\'t load comments.</div>'; });
}

const STANCE = { rec: ['✓ Recommends', 'rec'], cite: ['Cites it', 'cite'], neg: ['Criticizes', 'neg'], joke: ['Joke', 'cite'], self: ['Author', 'cite'], other: ['Mentions', 'cite'] };
function avatarColor(u) { let h = 0; for (const c of u) h = (h * 31 + c.charCodeAt(0)) % 360; return `hsl(${h} 45% 45%)`; }
function linkify(s) { return esc(s).replace(/https?:\/\/[^\s<]+[^\s<.,;:)'"]/g, (u) => `<a href="${u}" target="_blank" rel="noopener noreferrer nofollow">${u.length > 70 ? u.slice(0, 67) + '…' : u}</a>`); }

function renderReviews(p, ms, mode) {
  const lab = ms.filter((m) => m.s);
  const c = (k) => lab.filter((m) => m.s === k).length;
  const rows = [['Recommends', c('rec')], ['Cites it', c('cite')], ['Criticizes', c('neg')], ['Other', lab.length - c('rec') - c('cite') - c('neg')]];
  const yrs = []; for (let y = 2007; y <= 2026; y++) yrs.push(y);
  const ycount = yrs.map((y) => ms.filter((m) => +m.mo.slice(0, 4) === y).length); const ymax = Math.max(1, ...ycount);
  $('#histo').innerHTML = `
    <div style="display:flex;align-items:baseline;gap:8px">${up(p, false)}<span>HN score</span></div>
    <div style="color:var(--muted);font-size:13px;margin:4px 0 10px">${plural(ms.length, 'comment')} from ${plural(p.na, 'person', 'people').replace('persons', 'people')}</div>
    ${lab.length ? rows.map(([l, n]) => `<div class="r"><span>${l}</span><div class="bar"><i style="width:${(100 * n) / lab.length}%"></i></div><span>${Math.round((100 * n) / lab.length)}%</span></div>`).join('') : ''}
    <div style="color:var(--muted);font-size:12px">${lab.length < ms.length ? `Based on ${lab.length} labeled comments.` : ''}</div>
    <h4 style="margin:18px 0 0">Mentions per year</h4>
    <div class="timeline">${ycount.map((n, i) => `<i class="${n ? '' : 'z'}" style="height:${n ? 8 + (92 * n) / ymax : 3}%" title="${yrs[i]}: ${n}"></i>`).join('')}</div>
    <div class="tl-ax"><span>2007</span><span>2016</span><span>2026</span></div>`;
  let list = ms.slice();
  if (mode === 'rec') list = list.filter((m) => m.s === 'rec');
  if (mode === 'neg') list = list.filter((m) => m.s === 'neg');
  if (mode === 'new') list.reverse();
  const btn = (m, l) => `<button class="${mode === m ? 'on' : ''}" data-mode="${m}">${l}</button>`;
  $('#rvlist').innerHTML = `<div class="rvfilter">${btn('all', 'Oldest first')}${btn('new', 'Newest first')}${btn('rec', `Recommendations (${c('rec')})`)}${c('neg') ? btn('neg', `Criticism (${c('neg')})`) : ''}</div>
    ${list.map((m) => {
    const [lbl, cls] = STANCE[m.s] || ['', 'cite'];
    return `<div class="rv"><div class="who"><span class="av" style="background:${avatarColor(m.u)}">${esc(m.u[0].toUpperCase())}</span>
        <a href="https://news.ycombinator.com/user?id=${encodeURIComponent(m.u)}" target="_blank" rel="noopener noreferrer">${esc(m.u)}</a></div>
        ${lbl ? `<div class="st ${cls}">${lbl}</div>` : ''}
        <div class="meta">${m.v && m.v !== 'amazon' ? `<span style="background:var(--chip);border-radius:3px;padding:0 5px;margin-right:4px">via ${esc((SRC_NAME[m.v] || m.v).replace(/ links?$/, '').replace(' threads', ''))}</span>` : ''}${fmtMonth(m.mo)}${m.stt ? ` · on <a href="https://news.ycombinator.com/item?id=${m.sid}" target="_blank" rel="noopener noreferrer">${esc(m.stt)}</a>` : ''} · <a href="https://news.ycombinator.com/item?id=${m.id}" target="_blank" rel="noopener noreferrer">view on HN</a></div>
        <div class="body${m.x.length > 600 ? ' clip' : ''}">${linkify(m.x)}</div>
        ${m.x.length > 600 ? '<button class="more" onclick="this.previousElementSibling.classList.remove(\'clip\');this.remove()">Read more</button>' : ''}</div>`;
  }).join('') || '<div class="empty">No comments in this view.</div>'}`;
  $('#rvlist').querySelectorAll('.rvfilter button').forEach((b) => { b.onclick = () => renderReviews(p, ms, b.dataset.mode); });
}

function addList(a, el) {
  const added = toggle(U.list, a); U.save();
  if (el) el.textContent = added ? 'In your list ✓' : 'Add to List';
  toast(added ? 'Added to your list' : 'Removed from your list');
}
function likeIt(a, el) {
  const added = toggle(U.liked, a); U.save();
  if (el) el.textContent = added ? '♥ Liked' : '♡ Like';
  toast(added ? 'Liked. Your home page recs will use this.' : 'Unliked');
}

function listPage() {
  const items = U.list.map((a) => S.by[a]).filter(Boolean);
  const recs = items.length ? recsFor(items.map((p) => [p.a, 2]), 18) : [];
  $('#app').innerHTML = `
  <div class="cartpage">
    <div class="main">
      <h1>Your List</h1>
      <div style="color:var(--muted);font-size:14px;margin-bottom:10px">Things you want to remember. Nothing here is sold by us. Each item links to its Amazon page without an affiliate tag.</div>
      ${items.length ? items.map((p) => `<div class="citem">
        <a href="#/p/${p.a}">${img(p)}</a>
        <div style="min-width:0"><h3><a href="#/p/${p.a}" style="color:var(--text)">${esc(p.t)}</a></h3>
          <div class="by" style="font-size:13px;color:var(--muted)">${byline(p)}</div>
          <div style="color:var(--green);font-size:12px;margin:4px 0">Recommended on HN ${years(p)}</div>
          ${meter(p)}
          <div class="ops"><button onclick="addList('${p.a}');listPage()">Delete</button>|<a href="${amazonUrl(p)}" target="_blank" rel="noopener noreferrer">${amazonLabel(p)}</a>|<button onclick="likeIt('${p.a}')">Like</button></div></div>
        <div>${up(p, false)}</div></div>`).join('') : '<div class="empty">Your list is empty. Add things HN recommends and they\'ll wait here, stored only in this browser.</div>'}
      ${items.length ? `<div style="text-align:right;font-size:18px;border-top:1px solid #ddd;padding-top:10px">List (${plural(items.length, 'item')}): <b>${up({ sc: items.reduce((s, p) => s + p.sc, 0) }, false)}</b> combined HN score</div>` : ''}
    </div>
    <div class="cartside">
      <div style="font-size:18px">List (${plural(items.length, 'item')})</div>
      <div style="color:var(--green);font-size:13px;margin:8px 0">✓ Nothing to pay here. No account, no checkout.</div>
      <button class="btn wide" onclick="copyList()" ${items.length ? '' : 'disabled'}>Copy list as text</button>
      <button class="btn gh wide" onclick="if(this.dataset.sure){U.list=[];U.save();listPage()}else{this.dataset.sure=1;this.textContent='Click again to clear'}" ${items.length ? '' : 'disabled'}>Clear list</button>
    </div>
  </div>
  ${strip('Pairs well with your list, per HN', recs)}`;
}
function copyList() {
  const txt = U.list.map((a) => S.by[a]).filter(Boolean).map((p) => `${p.t} (${p.by}): ${amazonUrl(p)}`).join('\n');
  navigator.clipboard?.writeText(txt).then(() => toast('Copied your list'), () => toast('Copy failed'));
}

function gridPage(title, asins, empty, clearKey) {
  const items = asins.map((a) => S.by[a]).filter(Boolean);
  $('#app').innerHTML = `<div class="wrap white" style="margin-top:0">
    <div class="row-h"><h2 style="font-size:24px;margin:0">${esc(title)}</h2>${clearKey && items.length ? `<button class="btn gh sm" onclick="U['${clearKey}']=[];U.save();route()">Clear</button>` : ''}</div>
    <div class="rlist" style="margin-top:12px">${items.length ? items.map(resultRow).join('') : `<div class="empty">${empty}</div>`}</div></div>`;
}

function deptsPage() {
  const sec = (k) => DEPTS.filter(([, t]) => t === k).map(([d]) => {
    const subs = Object.entries(S.prods.filter((p) => p.d === d).reduce((m, p) => { m[p.sub] = (m[p.sub] || 0) + 1; return m; }, {})).sort((a, b) => b[1] - a[1]);
    if (!subs.length) return '';
    return `<div class="card"><h2><a href="#/s?d=${encodeURIComponent(d)}" style="color:var(--text)">${esc(d)}</a></h2><ul>${subs.map(([s, n]) => `<li><a href="#/s?d=${encodeURIComponent(d)}&sub=${encodeURIComponent(s)}">${esc(s)}</a><span>${n}</span></li>`).join('')}</ul></div>`;
  }).join('');
  $('#app').innerHTML = `<div class="wrap"><h1 style="font-size:24px;margin:8px 0 0">Books</h1></div><div class="depts">${sec('book')}</div>
    <div class="wrap"><h1 style="font-size:24px;margin:8px 0 0">Products &amp; media</h1></div><div class="depts">${sec('gear')}</div>`;
}

function about() {
  const st = S.stats;
  $('#app').innerHTML = `<article class="doc">
  <h1>About Hackerzon</h1>
  <p>Hackerzon is an Amazon-style store that only carries things Hacker News commenters have recommended to each other, again and again, over twenty years.</p>
  <p>It started as a reply to Andrej Karpathy's <a href="https://hackertube.org">HackerTube</a> post:</p>
  <blockquote>now do Amazon and remove sponsored posts, ads, upsells, and subscribe and save for everything<br><small>— @tylerpalmer, replying to <a href="https://x.com/karpathy/status/2116957135661945283">@karpathy</a></small></blockquote>
  <h2>How it was built</h2>
  <ol>
    <li><b>Find every product link on HN.</b> ${st.scanned.toLocaleString()} comments from ${fmtMonth(st.from)} to ${fmtMonth(st.to)} contained an Amazon link (via the public HN Algolia API), and ${(st.scanned_stores || 0).toLocaleString()} more linked Goodreads, O'Reilly, MIT Press, Manning, Pragmatic Bookshelf, No Starch and other stores. Regexes pulled out the product IDs; books with an ISBN were matched to their Amazon listing.</li>
    <li><b>Find products named without a link.</b> Many recommendations are just a name: "the AeroPress changed my mornings". Claude Haiku read ${(st.askhn_answers || 0).toLocaleString()} top-level answers in ${(st.askhn_threads || 0).toLocaleString()} "Ask HN" recommendation threads (best purchases, books that changed your thinking, desk setups) and listed every book and product each answer recommends. Those were matched to known items by title and author, or became new items.</li>
    <li><b>Keep what HN keeps coming back to.</b> Like HackerTube, a product makes the cut only if at least 3 different people recommended it in at least 3 different months, counting links and named mentions together. Different editions of the same book are merged using Open Library.</li>
    <li><b>Read the comments.</b> A link isn't always a recommendation. Claude read a sample of comments for each product and labeled each one: recommending it, citing it, criticizing it, joking, or the author promoting their own work. Self-promotion, mockery and unidentifiable items were dropped. Claude also wrote the short summaries, the "why HN recommends it" notes and the category.</li>
    <li><b>Rank by lasting recommendations.</b> The ▲ HN score estimates how many different months someone recommended the product, with each person counting for at most two months so one enthusiast can't carry an item. Being recommended steadily for a decade beats one viral thread.</li>
  </ol>
  <h2>What's not here</h2>
  <p>No sponsored results, ads, upsells, "frequently bought together" bundles or Subscribe &amp; Save. No affiliate tags: "View on Amazon" goes to the plain product page. No prices, since they change constantly and we don't sell anything. AI slop books never get recommended by thousands of different people over a decade, so they aren't here either.</p>
  <h2>Get the data</h2>
  <p>Everything behind this store is yours to reuse. <a href="https://github.com/Boo-Geonhyeok/hackerzon/releases/latest/download/hackerzon-data.zip">Download the data</a> (one zip: every product, every HN comment with its stance, and a DATA.md written for agents). Point your Claude at it and ask for your own version. The pipeline code is on <a href="https://github.com/Boo-Geonhyeok/hackerzon">GitHub</a>. Released under ODC-By 1.0, like the Hacker News archive it comes from.</p>
  <h2>Privacy</h2>
  <p>No accounts. Your list, likes and history are stored in this browser's local storage and never leave it. Likes and history steer the "Recommended for you" row.</p>
  <h2>Caveats</h2>
  <p>Images load from Amazon (or Open Library for books) by product ID; some are missing, so you'll see a drawn cover instead. Labels and summaries were written by an AI model from a sample of comments and can be wrong. The full comments are on every product page, linked back to HN.</p>
  <p style="color:var(--muted);font-size:13px">Not affiliated with Amazon, Hacker News or Y Combinator. Comments belong to their authors.</p>
  </article>`;
}

/* ---------- routing ---------- */
function route() {
  const h = curPath();
  const [path, qs = ''] = h.split('?');
  document.title = 'Hackerzon: what Hacker News keeps recommending';
  $('#subnav').querySelectorAll('a').forEach((a) => a.classList.toggle('on', a.getAttribute('href') === '#' + h));
  if (path === '/' || path === '') home();
  else if (path === '/s') search(qs);
  else if (path.startsWith('/p/')) product(path.slice(3));
  else if (path === '/list') listPage();
  else if (path === '/history') gridPage('Your browsing history', U.hist, 'Nothing yet. Products you open show up here (only in this browser).', 'hist');
  else if (path === '/liked') gridPage('Things you liked', U.liked, 'Like products to steer your recommendations.', 'liked');
  else if (path === '/foryou') gridPage('Recommended for you', recsFor(seeds(), 48).map((p) => p.a), 'Open, like or list a few products and recommendations will appear.');
  else if (path === '/depts') deptsPage();
  else if (path === '/about') about();
  else home();
  if (!path.startsWith('/p/')) window.scrollTo(0, 0);
  const o = parseQuery(qs); $('#q').value = path === '/s' ? (o.q || '') : ''; $('#searchDept').value = path === '/s' ? (o.d || '') : '';
}

async function init() {
  const [prods, stats] = await Promise.all([fetch('data/products.json').then((r) => r.json()), fetch('data/stats.json').then((r) => r.json())]);
  S.prods = prods; S.stats = stats; S.by = Object.fromEntries(prods.map((p) => [p.a, p]));
  S.maxSc = Math.max(...prods.map((p) => p.sc));
  prods.forEach((p) => { S.deptCount[p.d] = (S.deptCount[p.d] || 0) + 1; });
  const present = DEPTS.filter(([d]) => S.deptCount[d]);
  $('#searchDept').innerHTML = '<option value="">All</option>' + present.map(([d]) => `<option>${esc(d)}</option>`).join('');
  const nav = [['#/depts', '☰ All'], ['#/s?k=book', 'Books'], ['#/s?k=gear', 'Gear'], ['#/s?gem=1', 'Hidden gems'], ['#/s?sort=recent', 'Lately on HN'],
    ...present.filter(([, t]) => t === 'gear').slice(0, 5).map(([d]) => [`#/s?d=${encodeURIComponent(d)}`, d]),
    ['#/foryou', 'For you'], ['#/about', 'How it works']];
  $('#subnav').innerHTML = nav.map(([h, l]) => `<a href="${h}">${esc(l)}</a>`).join('') + '<span class="promise subnav-a" style="padding:7px 8px">0 sponsored results. Ever.</span>';
  updateCount();
  route();
}

$('#searchForm').addEventListener('submit', (e) => {
  e.preventDefault();
  const q = $('#q').value.trim(); const d = $('#searchDept').value;
  go('#/s?' + toQuery({ q, d }));
});
window.addEventListener('hashchange', route);
// In the published artifact, the sandbox blocks #-links, so route clicks in-page instead.
let CUR = '/';
function curPath() { return BUNDLE ? CUR : (location.hash.slice(1) || '/'); }
function go(h) { if (BUNDLE) { CUR = h.replace(/^#/, '') || '/'; route(); } else location.hash = h; }
// claude.ai intercepts real links, so in-site links become data-go elements there.
function delink(root = document) {
  root.querySelectorAll('a[href^="#/"]').forEach((a) => {
    a.dataset.go = a.getAttribute('href'); a.removeAttribute('href');
    a.setAttribute('role', 'link'); a.tabIndex = 0;
  });
}
if (BUNDLE) {
  document.addEventListener('click', (e) => {
    const a = e.target.closest('[data-go]');
    if (!a) return;
    e.preventDefault();
    go(a.dataset.go);
  }, true);
  document.addEventListener('keydown', (e) => {
    const a = e.target.closest && e.target.closest('[data-go]');
    if (a && e.key === 'Enter') go(a.dataset.go);
  });
  new MutationObserver(() => delink()).observe(document.body, { childList: true, subtree: true });
}
if (BUNDLE) new MutationObserver(hydrate).observe(document.getElementById('app'), { childList: true, subtree: true });
document.addEventListener('keydown', (e) => {
  if (e.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { e.preventDefault(); $('#q').focus(); }
});
init().catch((e) => { $('#app').innerHTML = `<div class="empty">Couldn't load the store data. (${esc(e.message)})</div>`; });
