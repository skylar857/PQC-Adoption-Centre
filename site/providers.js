// Extra layer: adds a "Providers" section to the site. Reads providers.json
// (from this folder, or ../dashboard/). Does not modify app.js behaviour.
(async function () {
  const $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  const LABEL = {global: "Global top sites", india_bank: "Indian banks / fintech", india_gov: "Indian government", india_univ: "Indian universities"};
  const NAME = {"other/unidentified": "Unidentified", "no_http_response": "No HTTP response"};
  const EDGE = ["Cloudflare", "CloudFront", "Akamai", "Google", "Meta", "Fastly"];
  const UNK = ["other/unidentified", "no_http_response"];
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  let d = null;
  for (const p of ["providers.json", "../dashboard/providers.json"]) {
    try { const r = await fetch(p); if (r.ok) { d = await r.json(); break; } } catch (e) {}
  }
  if (!d || !$("#hosts-sec")) return;

  const sum = (o, ks) => ks.reduce((a, k) => a + (o[k] || 0), 0);
  const pct = (a, b) => b ? Math.round(a / b * 1000) / 10 : 0;
  const o = d.overall;
  const edgeAll = sum(o.all_by_provider, EDGE), edgeHy = sum(o.hybrid_by_provider, EDGE);
  const restN = o.reachable - edgeAll, restHy = o.hybrid - edgeHy;

  const seg = (n, tot, cls, t) => n ? `<i class="seg ${cls}" style="--w:${n / tot * 100}%" title="${t}: ${n}"></i>` : "";
  const cats = Object.entries(d.categories).map(([k, v]) => {
    const e = sum(v.hybrid_by_provider, EDGE), u = sum(v.hybrid_by_provider, UNK), m = v.hybrid - e - u;
    return `<div class="brow"><span>${esc(LABEL[k] || k)}</span><div class="stack">${seg(e, v.hybrid, "s1", "Major edge provider")}${seg(m, v.hybrid, "s2", "Other identified")}${seg(u, v.hybrid, "s3", "Unidentified")}</div><b>${v.hybrid} hybrid</b></div>`;
  }).join("");

  const prov = Object.entries(o.all_by_provider).sort((a, b) => b[1] - a[1]).map(([p, n]) => {
    const hy = o.hybrid_by_provider[p] || 0;
    return `<div class="brow"><span>${esc(NAME[p] || p)}</span><div class="track"><i class="fill" style="--w:${pct(hy, n)}%"></i></div><b>${hy}/${n}</b></div>`;
  }).join("");

  const st = document.createElement("style");
  st.textContent = ".stack{display:flex;height:16px;border-radius:8px;overflow:hidden;background:var(--line)}" +
    ".seg{display:block;height:100%;width:0;transition:width 1.1s cubic-bezier(.2,.8,.2,1)}.in .seg{width:var(--w)}" +
    ".s1{background:var(--acc)}.s2{background:var(--acc2)}.s3{background:#5b6785}" +
    ".lg{display:inline-block;width:10px;height:10px;border-radius:3px;margin:0 4px 0 12px;vertical-align:middle}";
  document.head.append(st);

  const sec = document.createElement("section");
  sec.id = "providers";
  sec.innerHTML = `<h2>Who serves the hybrid hosts?</h2>
    <p class="sub">Provider attribution comes from HTTP response headers. It is a lower bound: hosts that hide identifying headers show as unidentified.</p>
    <div class="card"><p><b>${edgeAll}</b> hosts sit behind one of six major edge providers (Cloudflare, CloudFront, Akamai, Google, Meta, Fastly), and <b>${edgeHy}</b> of them (${pct(edgeHy, edgeAll)}%) negotiate hybrid PQC. That is ${pct(edgeHy, o.hybrid)}% of all hybrid hosts. Everywhere else, hybrid adoption is ${pct(restHy, restN)}% (${restHy} of ${restN}).</p></div>
    <h3>Hybrid hosts by category</h3>
    <div class="card" id="pv1">${cats}<p class="small"><span class="lg s1"></span>Major edge provider<span class="lg s2"></span>Other identified<span class="lg s3"></span>Unidentified. Bars show composition within each category.</p></div>
    <h3>Hybrid rate by provider</h3>
    <div class="card" id="pv2">${prov}<p class="small">Hybrid hosts / reachable hosts per provider. Small counts (Sucuri, AWS) should not be over-read.</p></div>`;
  $("#hosts-sec").before(sec);

  const link = $('#nav a[href="#hosts-sec"]');
  if (link) { const a = document.createElement("a"); a.href = "#providers"; a.textContent = "Providers"; link.before(a); }

  const cards = [$("#pv1"), $("#pv2")];
  if (reduce) cards.forEach(c => c.classList.add("in"));
  else {
    const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), {threshold: .2});
    cards.forEach(c => io.observe(c));
  }
  const links = [...document.querySelectorAll("#nav a")];
  new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) links.forEach(a => a.classList.toggle("on", a.getAttribute("href") === "#" + e.target.id));
  }), {rootMargin: "-45% 0px -50% 0px"}).observe(sec);
})();
