const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const LABEL = {global: "Global top sites", india_bank: "Indian banks / fintech", india_gov: "Indian government", india_univ: "Indian universities"};
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const f1 = n => Math.round(n * 10) / 10;
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

// Reads data from this folder first, then from ../dashboard/ (so nothing has to be copied).
async function load(name) {
  for (const p of [name, "../dashboard/" + name]) {
    try { const r = await fetch(p); if (r.ok) return await r.json(); } catch (e) {}
  }
  throw new Error("Cannot load " + name);
}

function counter(el, to, suf) {
  if (reduce) { el.textContent = f1(to) + suf; return; }
  let t0;
  (function f(t) {
    t0 = t0 || t;
    const k = Math.min((t - t0) / 1600, 1), e = 1 - Math.pow(1 - k, 3);
    el.textContent = f1(to * e) + suf;
    if (k < 1) requestAnimationFrame(f);
  })(performance.now());
}

function hero(hosts) {
  if (!window.THREE) return;
  const cv = $("#hero"), R = new THREE.WebGLRenderer({canvas: cv, alpha: true, antialias: true});
  const sc = new THREE.Scene(), cam = new THREE.PerspectiveCamera(55, 1, .1, 100), g = new THREE.Group();
  cam.position.z = 7; sc.add(g); R.setPixelRatio(Math.min(devicePixelRatio, 2));
  const t = document.createElement("canvas"); t.width = t.height = 32;
  const x = t.getContext("2d"), gr = x.createRadialGradient(16, 16, 0, 16, 16, 16);
  gr.addColorStop(0, "#fff"); gr.addColorStop(1, "#fff0"); x.fillStyle = gr; x.fillRect(0, 0, 32, 32);
  const tex = new THREE.CanvasTexture(t), n = hosts.length, P = new Float32Array(n * 3), C = new Float32Array(n * 3);
  hosts.forEach((h, i) => {
    const p = Math.acos(1 - 2 * (i + .5) / n), a = i * 2.39996, r = 2.7;
    P.set([r * Math.sin(p) * Math.cos(a), r * Math.cos(p), r * Math.sin(p) * Math.sin(a)], i * 3);
    C.set(h.status === "pqc_hybrid" ? [.5, .9, 1] : [.85, .63, .36], i * 3);
  });
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(P, 3));
  geo.setAttribute("color", new THREE.BufferAttribute(C, 3));
  g.add(new THREE.Points(geo, new THREE.PointsMaterial({size: .38, map: tex, vertexColors: true, transparent: true, depthWrite: false})));
  g.add(new THREE.Mesh(new THREE.IcosahedronGeometry(2.6, 2), new THREE.MeshBasicMaterial({color: 0x6f7dff, wireframe: true, transparent: true, opacity: .13})));
  const S = new Float32Array(900); for (let i = 0; i < 900; i++) S[i] = (Math.random() - .5) * 40;
  const sg = new THREE.BufferGeometry(); sg.setAttribute("position", new THREE.BufferAttribute(S, 3));
  sc.add(new THREE.Points(sg, new THREE.PointsMaterial({size: .05, color: 0x98a2bd})));
  let mx = 0, my = 0, vis = true;
  addEventListener("pointermove", e => { mx = e.clientX / innerWidth - .5; my = e.clientY / innerHeight - .5; });
  new IntersectionObserver(e => { vis = e[0].isIntersecting; }).observe(cv);
  function size() { const w = cv.clientWidth, h = cv.clientHeight; R.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); }
  size(); addEventListener("resize", size);
  (function f() {
    requestAnimationFrame(f);
    if (!vis) return;
    if (!reduce) g.rotation.y += .0025;
    g.rotation.x += (my * .6 - g.rotation.x) * .04;
    g.position.x += (mx * 1.2 - g.position.x) * .04;
    const k = Math.min(scrollY / innerHeight, 1);
    cam.position.z = 7 + k * 3; g.position.y = k * 1.5;
    R.render(sc, cam);
  })();
}

function init(s, b) {
  const o = s.overall;
  let cat = "";
  counter($("#count"), o.pct_of_reachable, "%");
  $("#sub").textContent = o.pqc_hybrid + " of " + o.reachable + " reachable hosts negotiate X25519MLKEM768 (" + o.total + " scanned, snapshot " + s.scanned_at.slice(0, 10) + ")";
  hero(s.hosts);

  // Category bars (click to filter, hover for details)
  $("#bars").innerHTML = Object.entries(s.categories).map(([k, v]) =>
    `<button class="row" data-c="${k}"><span>${esc(LABEL[k] || k)}</span><div class="track"><i class="fill" style="--w:${v.pct_of_reachable}%"></i><i class="ci" style="left:${v.ci95[0]}%;width:${v.ci95[1] - v.ci95[0]}%"></i></div><span class="small">${f1(v.pct_of_reachable)}% (${v.pqc_hybrid}/${v.reachable})</span></button>`).join("");
  const tip = $("#tip");
  $$(".row").forEach(r => {
    const v = s.categories[r.dataset.c];
    r.addEventListener("mousemove", e => {
      tip.style.left = Math.min(e.clientX + 14, innerWidth - 280) + "px"; tip.style.top = e.clientY + 14 + "px";
      tip.innerHTML = "<b>" + esc(LABEL[r.dataset.c] || r.dataset.c) + "</b><br>Hybrid: " + v.pqc_hybrid + " of " + v.reachable + " reachable<br>95% CI: " + v.ci95[0] + "-" + v.ci95[1] + "%<br>Classical only: " + v.classical_only + " | Unreachable: " + v.unreachable;
      tip.style.opacity = 1;
    });
    r.addEventListener("mouseleave", () => { tip.style.opacity = 0; });
    r.addEventListener("click", () => { setCat(cat === r.dataset.c ? "" : r.dataset.c); });
  });

  // Outcomes table
  const cols = ["pqc_hybrid", "classical_only", "pqc_offer_rejected", "no_tls13", "unreachable", "timeout"];
  $("#outcomes").innerHTML = "<tr><th>Category</th>" + cols.map(c => "<th>" + c + "</th>").join("") + "</tr>" +
    Object.entries(s.categories).map(([k, v]) => "<tr><td>" + esc(LABEL[k] || k) + "</td>" + cols.map(c => "<td>" + v[c] + "</td>").join("") + "</tr>").join("");

  // Benchmark bars
  const h = b.handshake_cost_us, mx = Math.max(...Object.values(h));
  const sch = [["X25519", "x25519"], ["ML-KEM-768", "ml_kem_768"], ["Hybrid", "hybrid"]];
  $("#bench").innerHTML = ["client", "server"].map(side => "<h3>" + side + " (microseconds, estimated)</h3>" +
    sch.map(([n, k]) => { const v = h[k + "_" + side]; return `<div class="brow"><span>${n}</span><div class="track"><i class="fill" style="--w:${v / mx * 100}%"></i></div><b>${v} µs</b></div>`; }).join("")).join("");
  $("#benchmeta").textContent = b.meta.openssl + " | " + b.meta.cpu + " | median of " + b.meta.runs + " runs. " + b.meta.note;

  // Handshake size diagram
  const z = b.sizes_bytes;
  const notes = {
    x25519: "Classical key share: 32 bytes each way.",
    ml_kem_768: "ML-KEM-768 alone: about 37 times larger than X25519.",
    hybrid_x25519mlkem768: "Hybrid sends both: roughly 1.1 KB extra per direction, which is why some middleboxes struggle with it."
  };
  function setK(k) {
    $$(".seg button").forEach(x => x.classList.toggle("on", x.dataset.k === k));
    $("#cb").style.setProperty("--w", Math.max(z[k].client_share / 1216 * 100, 1.5) + "%");
    $("#sb").style.setProperty("--w", Math.max(z[k].server_share / 1216 * 100, 1.5) + "%");
    $("#cn").textContent = z[k].client_share + " B"; $("#sn").textContent = z[k].server_share + " B";
    $("#hn").textContent = notes[k];
  }
  $$(".seg button").forEach(x => x.addEventListener("click", () => setK(x.dataset.k)));
  setK("x25519");

  // Host table with category filter
  function draw() {
    const q = $("#q").value.toLowerCase();
    const r = s.hosts.filter(x => (!cat || x.category === cat) && x.domain.toLowerCase().includes(q));
    $("#hc").textContent = r.length + " hosts" + (cat ? " in " + LABEL[cat] : "");
    $("#hosts").innerHTML = "<tr><th>Domain</th><th>Category</th><th>Status</th><th>Group</th></tr>" +
      r.map(x => "<tr><td>" + esc(x.domain) + "</td><td>" + esc(LABEL[x.category] || x.category) + '</td><td class="' + x.status + '">' + x.status + "</td><td>" + esc(x.group) + "</td></tr>").join("");
  }
  function setCat(c) { cat = c; $$(".row").forEach(r => r.classList.toggle("on", r.dataset.c === c)); draw(); }
  $("#q").addEventListener("input", draw);
  $("#clear").addEventListener("click", () => setCat(""));
  draw();

  // Scroll reveals (bars grow when their container gets the "in" class)
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), {threshold: .15});
  $$(".rv").forEach(e => reduce ? e.classList.add("in") : io.observe(e));

  // Nav highlight
  const links = $$("#nav a");
  const so = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) links.forEach(a => a.classList.toggle("on", a.getAttribute("href") === "#" + e.target.id));
  }), {rootMargin: "-45% 0px -50% 0px"});
  $$("header[id],section[id]").forEach(e => so.observe(e));
}

Promise.all([load("summary.json"), load("benchmark.json")]).then(([s, b]) => init(s, b))
  .catch(e => { $("#sub").textContent = "Could not load data: " + e.message; });
