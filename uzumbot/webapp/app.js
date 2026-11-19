/* Taobao → Uzum mini ilova. Vanilla JS, yig'ish (build) shart emas. */
(function () {
  "use strict";
  const tg = window.Telegram && window.Telegram.WebApp;
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
  const { calculate, parseNumber } = window.UzCalc;
  const ver = (v) => !!(tg && tg.isVersionAtLeast && tg.isVersionAtLeast(v));

  // ---------- holat ----------
  const S = {
    me: null, settings: {}, meta: [], statuses: {}, cargos: [], products: [], stats: {}, ai: false,
    tab: "home", filter: "all", q: "", aiMode: "tr", aiText: "", aiOut: "",
    calc: emptyCalc(), editingId: null, sheetOpen: false,
  };
  // bot/db.py RATE_FIELDS bilan bir xil
  const RATE_FIELDS = ["cny_rate", "usd_rate", "fx_spread_pct", "buyer_pct", "pack_cost", "logistics_fee", "tax_pct",
    "payout_fee_pct", "ads_pct", "returns_pct", "target_margin_pct", "uzum_trip_cost", "uzum_vat_pct"];
  const VERDICT = {
    KIRAMIZ: { e: "🟢", t: "KIRAMIZ", s: "Foyda yaxshi — sinab ko'rsa bo'ladi" },
    EHTIYOT: { e: "🟡", t: "EHTIYOT", s: "Foyda bor, lekin zaxira kam" },
    KIRMAYMIZ: { e: "🔴", t: "KIRMAYMIZ", s: "Foyda yetarli emas" },
  };
  const WEEKDAYS = ["Yakshanba", "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"];
  const MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];
  const STATUS_ORDER = ["idea", "sample", "batch", "transit", "selling", "stopped"];
  const MOTTO = [
    "Avval kichik sinov, keyin ishlaganini ko'paytiramiz 🌱",
    "Sotuv narxi tannarxdan 3 barobar — oltin qoida ✨",
    "Har bir namunani qo'lda tekshiramiz 🔍",
    "Qutini videoga olib ochamiz — bu dalil 🎥",
    "Har bir sharhga chiroyli javob — reyting o'sadi ⭐",
    "Shoshilmaymiz, hisob-kitob bilan yuramiz 🧮",
  ];

  function emptyCalc() {
    return { name: "", source_link: "", price_cny: "", weight_g: "", qty: "50", cargo_id: null, tariff_usd_kg: "",
      sell_price: "", commission_pct: "", china_ship_cny: "", length_cm: "", width_cm: "", height_cm: "",
      sell_days: "", scheme: "FBO", cat: null, status: "idea", note: "" };
  }

  // ---------- yordamchilar ----------
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (x) => (x == null || !isFinite(x)) ? "∞" : String(Math.round(x)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  const fmtK = (x) => Math.abs(x) >= 1e6 ? (x / 1e6).toFixed(1).replace(".0", "") + " mln" : fmt(x);
  const g = (v) => (Math.round(v * 100) / 100).toString();
  const vcls = (v) => "v-" + v;

  function haptic(kind, style) {
    if (!ver("6.1")) return;
    try {
      const h = tg.HapticFeedback;
      if (kind === "sel") h.selectionChanged();
      else if (kind === "ok" || kind === "err" || kind === "warn") h.notificationOccurred({ ok: "success", err: "error", warn: "warning" }[kind]);
      else h.impactOccurred(style || "light");
    } catch (e) { /* eski klient */ }
  }

  let toastTimer;
  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 2200);
  }

  function ask(msg) {
    return new Promise((res) => {
      if (ver("6.2")) tg.showConfirm(msg, (ok) => res(!!ok));
      else res(window.confirm(msg));
    });
  }

  function alertMsg(msg) {
    if (ver("6.2")) tg.showAlert(msg); else window.alert(msg);
  }

  function confetti() {
    const colors = ["#ffb020", "#ff6b5a", "#ff4f9a", "#7b5cff", "#12c2b0", "#3fa7ff"];
    for (let i = 0; i < 36; i++) {
      const c = document.createElement("i");
      c.className = "confetti";
      c.style.left = Math.random() * 100 + "vw";
      c.style.background = colors[i % colors.length];
      c.style.animationDelay = Math.random() * 0.4 + "s";
      c.style.animationDuration = 1.2 + Math.random() * 0.9 + "s";
      document.body.appendChild(c);
      setTimeout(() => c.remove(), 2600);
    }
  }

  async function api(method, path, body) {
    let r;
    try {
      r = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json", "X-Init-Data": tg ? tg.initData : "" },
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (e) {
      throw new Error("Bot bilan aloqa uzildi (internet yoki bot qayta ishga tushgan). "
        + "Ilovani yopib, «📱 Ilova» tugmasidan qayta oching.");
    }
    if (r.status === 524 || r.status === 502 || r.status === 530)
      throw new Error("Javob juda uzoq kutildi yoki bot vaqtincha o'chiq. Birozdan keyin qayta urinib ko'ring.");
    let data = {};
    try { data = await r.json(); } catch (e) { /* bo'sh javob */ }
    if (!r.ok) throw new Error(data.error || ("Xato " + r.status));
    return data;
  }

  async function reload() {
    const d = await api("GET", "/api/boot");
    Object.assign(S, { me: d.me, settings: d.settings, meta: d.settings_meta, statuses: d.statuses, cargos: d.cargos,
      products: d.products, stats: d.stats, ai: d.ai, tariffs: d.tariffs });
  }

  // ---------- Telegram tugmalari ----------
  let mainFn = null, secFn = null, backFn = null;
  function setMain(opts) {
    if (!tg) return;
    const mb = tg.MainButton;
    if (mainFn) mb.offClick(mainFn);
    mainFn = null;
    if (!opts) { mb.hide(); return; }
    mainFn = opts.onClick;
    mb.onClick(mainFn);
    const p = { text: opts.text, is_visible: true, is_active: opts.enabled !== false,
      color: opts.enabled === false ? "#c9bfd6" : (opts.color || "#ff4f9a"), text_color: "#ffffff" };
    if (ver("7.10")) p.has_shine_effect = !!opts.shine && opts.enabled !== false;
    mb.setParams(p);
  }
  function setSecondary(opts) {
    if (!tg || !ver("7.10") || !tg.SecondaryButton) return;
    const sb = tg.SecondaryButton;
    if (secFn) sb.offClick(secFn);
    secFn = null;
    if (!opts) { sb.hide(); return; }
    secFn = opts.onClick;
    sb.onClick(secFn);
    sb.setParams({ text: opts.text, is_visible: true, position: "left" });
  }
  function setBack(fn) {
    if (!tg || !ver("6.1")) return;
    if (backFn) tg.BackButton.offClick(backFn);
    backFn = fn;
    if (fn) { tg.BackButton.onClick(fn); tg.BackButton.show(); } else tg.BackButton.hide();
  }

  // ---------- tema ----------
  function applyTheme() {
    const dark = tg && tg.colorScheme === "dark";
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    const bg = dark ? "#15122a" : "#fff7ef";
    if (ver("6.1")) { try { tg.setHeaderColor(bg); tg.setBackgroundColor(bg); } catch (e) { /* */ } }
    if (ver("7.10")) { try { tg.setBottomBarColor(bg); } catch (e) { /* */ } }
  }

  // ---------- qoralama (CloudStorage: telefon va kompyuterda bir xil) ----------
  let draftTimer;
  function saveDraft() {
    clearTimeout(draftTimer);
    draftTimer = setTimeout(() => {
      const v = JSON.stringify({ c: S.calc, e: S.editingId });
      if (ver("6.9")) tg.CloudStorage.setItem("calc_draft", v.slice(0, 4000));
      else try { localStorage.setItem("calc_draft", v); } catch (e) { /* */ }
    }, 400);
    updateClosingConfirm();
  }
  function loadDraft() {
    return new Promise((res) => {
      let done = false;
      const apply = (v) => {
        if (done) return;
        done = true;
        try { const d = JSON.parse(v || "null"); if (d && d.c) { S.calc = { ...emptyCalc(), ...d.c }; S.editingId = d.e || null; } } catch (e) { /* */ }
        res();
      };
      setTimeout(() => apply(null), 1500);   // CloudStorage javob bermasa, qoralamasiz davom etamiz
      if (ver("6.9")) tg.CloudStorage.getItem("calc_draft", (err, v) => apply(err ? null : v));
      else { try { apply(localStorage.getItem("calc_draft")); } catch (e) { res(); } }
    });
  }
  function clearDraft() {
    S.calc = emptyCalc(); S.editingId = null;
    if (ver("6.9")) tg.CloudStorage.removeItem("calc_draft");
    else try { localStorage.removeItem("calc_draft"); } catch (e) { /* */ }
    updateClosingConfirm();
  }
  function updateClosingConfirm() {
    if (!ver("6.2")) return;
    const dirty = S.calc.name || S.calc.price_cny || S.calc.sell_price;
    if (dirty) tg.enableClosingConfirmation(); else tg.disableClosingConfirmation();
  }

  // ---------- hisob ----------
  const selectedCargo = (c) => (c.cargo_id ? S.cargos.find((x) => x.id === Number(c.cargo_id)) || null : null);
  const catCommission = (cat, scheme) => (cat ? cat[scheme === "FBS" ? "fbs" : "fbo"] : null);

  // bot/service.py build_input() bilan bir xil ustunlik tartibi:
  // foydalanuvchi kiritgani > kargo/toifa > sozlamadagi standart
  function buildInput(c, cargoArg) {
    const s = S.settings;
    const cargo = cargoArg === undefined ? selectedCargo(c) : cargoArg;
    const cat = c.cat, scheme = c.scheme === "FBS" ? "FBS" : "FBO";
    const inp = {};
    RATE_FIELDS.forEach((k) => (inp[k] = s[k]));
    inp.commission_pct = s.commission_pct;
    const cc = catCommission(cat, scheme);
    if (cc != null) inp.commission_pct = cc;
    inp.china_ship_cny = s.china_ship_cny;
    inp.sell_days = s.sell_days;
    inp.vol_divisor = s.vol_divisor;
    inp.trip_cost = s.trip_cost;
    inp.cargo_usd_m3 = 0;
    if (cargo) {
      inp.tariff_usd_kg = Number(cargo.tariff_usd_kg);
      inp.cargo_usd_m3 = Number(cargo.usd_m3 || 0);
      if (cargo.vol_divisor) inp.vol_divisor = Number(cargo.vol_divisor);
      if (cargo.pickup_cost != null) inp.trip_cost = Number(cargo.pickup_cost);
      else if (cargo.olmaliq) inp.trip_cost = s.olmaliq_pickup_cost;
    }
    inp.fbo = scheme === "FBS" ? 0 : 1;
    inp.storage_special = cat && cat.special ? 1 : 0;
    inp.storage_free_days = cat ? Number(cat.free || 30) : 30;
    const n = (k) => parseNumber(c[k]);
    ["price_cny", "weight_g", "sell_price", "commission_pct", "china_ship_cny", "length_cm", "width_cm", "height_cm", "sell_days"]
      .forEach((k) => { if (!isNaN(n(k))) inp[k] = n(k); });
    if (!cargo && !isNaN(n("tariff_usd_kg"))) inp.tariff_usd_kg = n("tariff_usd_kg");
    ["length_cm", "width_cm", "height_cm"].forEach((k) => { if (inp[k] === undefined) inp[k] = 0; });
    inp.qty = Math.floor(n("qty"));
    const ok = ["price_cny", "weight_g", "tariff_usd_kg", "sell_price"].every((k) => inp[k] !== undefined && !isNaN(inp[k]))
      && inp.qty > 0 && inp.sell_price > 0 && inp.commission_pct < 100;
    return ok ? inp : null;
  }
  function itemPayload(c) {
    const out = {};
    ["price_cny", "weight_g", "qty", "tariff_usd_kg", "sell_price", "commission_pct", "china_ship_cny", "length_cm",
      "width_cm", "height_cm", "sell_days"]
      .forEach((k) => { const v = parseNumber(c[k]); if (!isNaN(v)) out[k] = v; });
    return out;
  }

  // bot/service.py cargo_offers() bilan bir xil:
  // ball = 50% narx + 20% tezlik + 15% sifat + 10% oq hujjat + 5% Olmaliq; mos kelmaganlar alohida
  const SERIES_QTY = 3, DAYS_BUFFER = 4;
  const OFFER_W = { price: 0.5, speed: 0.2, quality: 0.15, docs: 0.1, olmaliq: 0.05 };
  function cargoEligibility(cg, qty, batchKg) {
    if (!(Number(cg.tariff_usd_kg) > 0)) return "tarif kiritilmagan";
    if (qty > SERIES_QTY && cg.series_ok === 0) return "seriya (partiya) olinmaydi — faqat namuna uchun";
    if (cg.min_kg && batchKg < Number(cg.min_kg)) return `minimal ${g(cg.min_kg)} kg (partiya ${batchKg.toFixed(1)} kg)`;
    return null;
  }
  function cargoOffers(c) {
    const rows = [], bad = [];
    S.cargos.forEach((cg) => {
      const inp = buildInput(c, cg);
      if (!inp) return;
      const r = calculate(inp);
      const reason = cargoEligibility(cg, inp.qty, r.charge_kg * inp.qty);
      const days = cg.days_max || cg.days_min || null;
      const x = { cargo: cg, r, ship: r.cargo + r.trip, ok: !reason, reason, badges: [], score: 0, days,
        real_days: days ? days + DAYS_BUFFER : null };
      (x.ok ? rows : bad).push(x);
    });
    if (rows.length) {
      const cheapest = Math.min(...rows.map((x) => x.ship));
      const fastest = Math.min(...rows.map((x) => x.days || 999));
      rows.forEach((x) => {
        const cg = x.cargo, docs = cg.white_docs;
        const p = {
          price: x.ship > 0 ? cheapest / x.ship : 1,
          speed: x.days ? fastest / x.days : 0.5,
          quality: (cg.rating || 3) / 5,
          docs: docs === 1 ? 1 : docs == null ? 0.5 : 0,
          olmaliq: cg.olmaliq ? 1 : 0,
        };
        x.score = Math.round(100 * Object.keys(OFFER_W).reduce((a, k) => a + OFFER_W[k] * p[k], 0));
      });
      rows.sort((a, b) => b.score - a.score || a.ship - b.ship);
      const bp = rows.reduce((a, b) => (b.ship < a.ship ? b : a));
      const bs = rows.reduce((a, b) => ((b.days || 999) < (a.days || 999) ? b : a));
      const bq = rows.reduce((a, b) => ((b.cargo.rating || 3) > (a.cargo.rating || 3) ? b : a));
      rows.forEach((x, i) => {
        if (i === 0) x.badges.push("🏆 Tavsiya");
        if (x === bp) x.badges.push("💰 Eng arzon");
        if (x === bs && x.days) x.badges.push("⚡ Eng tez");
        if (x === bq && (x.cargo.rating || 3) >= 4) x.badges.push("⭐ Ishonchli");
        if (x.cargo.white_docs === 1) x.badges.push("📄 Oq hujjat");
        if (x.cargo.olmaliq) x.badges.push("📍 Olmaliq");
      });
    }
    bad.sort((a, b) => a.ship - b.ship);
    return rows.concat(bad);
  }

  // ================= EKRANLAR =================
  function render() {
    $$(".tab").forEach((b) => b.classList.toggle("on", b.dataset.tab === S.tab));
    const v = $("#view");
    v.onclick = null; v.oninput = null;   // oldingi bo'limning tinglovchilari qolmasin
    if (S.tab === "home") v.innerHTML = homeView();
    else if (S.tab === "calc") { v.innerHTML = calcView(); mountCalc(); }
    else if (S.tab === "products") { v.innerHTML = productsView(); mountProducts(); }
    else if (S.tab === "cargos") v.innerHTML = cargosView();
    else if (S.tab === "ai") { v.innerHTML = aiView(); mountAI(); }
    if (!S.sheetOpen) { tabButtons(); setBack(S.tab === "home" ? null : () => go("home")); }
    window.scrollTo(0, 0);
  }
  function go(tab) {
    if (S.tab === tab) return;
    S.tab = tab; haptic("sel"); render();
  }
  function tabButtons() {
    setSecondary(null);
    if (S.tab === "calc") return calcButtons();
    if (S.tab === "ai") return aiButtons();
    if (S.tab === "cargos") return setMain({ text: "➕ Kargo qo'shish", onClick: () => cargoSheet(null), color: "#3fa7ff" });
    if (S.tab === "products") return setMain({ text: "🧮 Yangi hisob", onClick: () => { clearDraft(); go("calc"); } });
    setMain(null);
  }

  // ---------- 🏠 Bosh ----------
  function homeView() {
    const st = S.stats, s = S.settings, me = S.me;
    const icon = me.name === "Gulim" ? "🌷" : "🚀";
    const dt = new Date();
    const today = `${WEEKDAYS[dt.getDay()]}, ${dt.getDate()}-${MONTHS[dt.getMonth()]}`;
    const motto = MOTTO[new Date().getDate() % MOTTO.length];
    const used = Math.min(st.budget_used_pct || 0, 100);
    const R = 46, C = 2 * Math.PI * R;
    const ringColor = used > 90 ? "#f04b4b" : used > 70 ? "#ffb020" : "url(#rg)";
    const pipe = STATUS_ORDER.map((k) => {
      const [e, ...rest] = (S.statuses[k] || "").split(" ");
      return `<button class="pipe" data-filter="${k}"><div class="e">${e}</div><b>${st.by_status[k] || 0}</b><span>${esc(rest.join(" "))}</span></button>`;
    }).join("");
    const recent = S.products.slice(0, 3).map(productCard).join("") ||
      `<div class="empty"><div class="e">🌱</div>Hali tovar yo'q. Birinchi hisobni qilamizmi?</div>`;
    return `
      <section class="hero">
        <h1>Salom, ${esc(me.name)}! ${icon}</h1>
        <div class="sub">${esc(today)} · ${esc(motto)}</div>
        <div class="rates">
          <button class="rate" data-act="rates">¥ <span class="num">${fmt(s.cny_rate)}</span> <small>so'm</small></button>
          <button class="rate" data-act="rates">$ <span class="num">${fmt(s.usd_rate)}</span> <small>so'm</small></button>
          <button class="rate" data-act="settings">⚙️</button>
        </div>
      </section>

      ${S.calc.name || S.calc.price_cny ? `<button class="card" data-go="calc" style="display:flex;gap:12px;align-items:center;width:100%;text-align:left">
        <span style="font-size:28px">📝</span><div><b>Tugallanmagan hisob${S.calc.name ? ": " + esc(S.calc.name) : ""}</b>
        <div class="small muted">${S.editingId ? "Tahrirlash" : "Qoralama"} saqlangan — davom etish →</div></div></button>` : ""}

      <div class="tiles">
        <button class="tile g" data-filter="all"><b>${st.by_verdict.KIRAMIZ}</b><span>🟢 Kiramiz</span></button>
        <button class="tile y" data-filter="all"><b>${st.by_verdict.EHTIYOT}</b><span>🟡 Ehtiyot</span></button>
        <button class="tile r" data-filter="all"><b>${st.by_verdict.KIRMAYMIZ}</b><span>🔴 Kirmaymiz</span></button>
      </div>

      <div class="card">
        <h2>💰 Byudjet</h2>
        <div class="budget">
          <div class="ring">
            <svg width="108" height="108" viewBox="0 0 108 108">
              <defs><linearGradient id="rg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffb020"/><stop offset=".5" stop-color="#ff4f9a"/><stop offset="1" stop-color="#7b5cff"/></linearGradient></defs>
              <circle cx="54" cy="54" r="${R}" fill="none" stroke="var(--soft)" stroke-width="12"/>
              <circle cx="54" cy="54" r="${R}" fill="none" stroke="${ringColor}" stroke-width="12" stroke-linecap="round"
                stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - used / 100)}" style="transition:stroke-dashoffset .8s"/>
            </svg>
            <div class="lbl"><div><b>${Math.round(st.budget_used_pct || 0)}%</b><br><span>band</span></div></div>
          </div>
          <ul>
            <li><span>Byudjet</span><b class="num">$${fmt(st.budget_usd)}</b></li>
            <li><span>Tovarda turgan</span><b class="num">$${fmt(st.capital_usd)}</b></li>
            <li><span>Bo'sh</span><b class="num">$${fmt(Math.max(st.budget_usd - st.capital_usd, 0))}</b></li>
            <li><span>Kutilgan foyda</span><b class="num" style="color:var(--green)">${fmtK(st.expected_profit)}</b></li>
          </ul>
        </div>
        <p class="small muted" style="margin:10px 0 0">Reja: $350 sinov · $550 yaxshi sotilganiga · $100 zaxira</p>
      </div>

      <div class="section-title">🧭 Tovarlar yo'li</div>
      <div class="pipeline">${pipe}</div>

      <div class="fab-row">
        <button class="big-action" style="background:var(--grad)" data-act="newcalc"><span class="e">🧮</span><div><b>Yangi hisob</b><span>Taobao → Uzum</span></div></button>
        <button class="big-action" style="background:var(--grad-cool)" data-go="ai"><span class="e">✨</span><div><b>AI yordam</b><span>Tarjima, matn</span></div></button>
      </div>

      <div class="section-title">🕒 Oxirgilar <button class="more" data-go="products">Hammasi →</button></div>
      <div class="plist">${recent}</div>
    `;
  }

  // ---------- 🧮 Hisob ----------
  function field(k, label, unit, opts = {}) {
    const v = S.calc[k] ?? "";
    const ph = opts.ph ?? "";
    const steps = opts.step ? `<button class="step" data-step="${k}" data-d="-${opts.step}">−</button><button class="step" data-step="${k}" data-d="${opts.step}">+</button>` : "";
    return `<div class="field"><label>${label}</label><div class="inp">
      <input data-k="${k}" value="${esc(v)}" placeholder="${esc(ph)}" inputmode="${opts.text ? "text" : "decimal"}" autocomplete="off">
      ${unit ? `<span class="unit">${unit}</span>` : ""}${steps}</div></div>`;
  }
  function calcView() {
    const c = S.calc, s = S.settings;
    const cargos = S.cargos.map((x) => `<button class="cpk ${String(c.cargo_id) === String(x.id) ? "on" : ""}" data-cargo="${x.id}">
      <b>${x.mode === "avia" ? "✈️" : "🚛"} ${esc(x.name)}${x.verified ? "" : " ❔"}</b><span>${x.tariff_usd_kg > 0 ? g(x.tariff_usd_kg) + " $/kg" : "⚠️ tarif yo'q"}${x.days_max ? ` · ${x.days_min || "?"}–${x.days_max} kun` : ""}${x.olmaliq ? " · 📍" : ""}</span></button>`).join("");
    const fbo = c.scheme !== "FBS";
    return `
      <section class="hero" style="padding-bottom:16px">
        <h1>${S.editingId ? "✏️ Tahrirlash" : "🧮 Tannarx hisobi"}</h1>
        <div class="sub">Uzum rasmiy tariflari bilan · yozganingiz sari natija o'zgaradi</div>
      </section>
      <div class="card" id="calcForm">
        <h2>🛍 Tovar</h2>
        ${field("name", "Tovar nomi", "", { text: true, ph: "Masalan: Mini zont UPF50+" })}
        ${field("source_link", "Taobao / 1688 linki", "🔗", { text: true, ph: "https://…" })}
        <div class="grid2">
          ${field("price_cny", "1 dona narxi", "¥", { ph: "15" })}
          ${field("weight_g", "Vazni (qadoq bilan)", "g", { ph: "250" })}
        </div>
        <div class="field"><label>Qadog'i bilan o'lchami — Uzum logistikasi va kargo uchun muhim</label>
          <div class="grid3">
            <div class="inp"><input data-k="length_cm" value="${esc(c.length_cm)}" placeholder="Uzun." inputmode="decimal"><span class="unit">sm</span></div>
            <div class="inp"><input data-k="width_cm" value="${esc(c.width_cm)}" placeholder="Eni" inputmode="decimal"><span class="unit">sm</span></div>
            <div class="inp"><input data-k="height_cm" value="${esc(c.height_cm)}" placeholder="Bal." inputmode="decimal"><span class="unit">sm</span></div>
          </div>
          <div class="small muted" id="litersInfo" style="margin:6px 4px 0"></div>
        </div>
        ${field("qty", "Partiyada nechta dona", "dona", { step: 10, ph: "50" })}
      </div>

      <div class="card">
        <h2>🍇 Uzum</h2>
        <div class="seg" id="schemeSeg">
          <button data-scheme="FBO" class="${fbo ? "on" : ""}">🏬 FBO · Uzum ombori</button>
          <button data-scheme="FBS" class="${fbo ? "" : "on"}">🏠 FBS · o'z omborimiz</button>
        </div>
        <div class="field"><label>Toifa — komissiya rasmiy jadvaldan</label>
          <div id="catBox">${catChosenHTML()}</div>
        </div>
        ${field("sell_price", "Uzumdagi sotuv narxi", "so'm", { ph: "129 000" })}
        <div id="fboBox" class="${fbo ? "" : "hidden"}">${field("sell_days", "Partiya necha kunda sotiladi (saqlash uchun)", "kun", { ph: g(s.sell_days) })}</div>
      </div>

      <div class="card" id="cargoCard">
        <h2>🚚 Kargo</h2>
        <div class="cargo-pick">${cargos}<button class="cpk ${!c.cargo_id ? "on" : ""}" data-cargo=""><b>✍️ Qo'lda</b><span>tarifni yozaman</span></button></div>
        <div id="manualTariff" class="${c.cargo_id ? "hidden" : ""}">${field("tariff_usd_kg", "Kargo tarifi", "$/kg", { ph: "6.7" })}</div>
        <div id="offers"></div>
      </div>

      <div class="card">
        <details class="more" style="margin-top:0" ${c.commission_pct || c.china_ship_cny || c.note ? "open" : ""}>
          <summary>➕ Qo'shimcha: komissiyani qo'lda, Xitoy ichki yetkazish, izoh</summary>
          <div class="grid2">
            ${field("commission_pct", "Komissiya (qo'lda)", "%", { ph: "toifadan" })}
            ${field("china_ship_cny", "Xitoy ichki yetkazish", "¥/partiya", { ph: g(s.china_ship_cny) })}
          </div>
          ${field("note", "Izoh", "", { text: true, ph: "Rang, model, sotuvchi…" })}
        </details>
      </div>
      <div class="card result" id="calcResult"></div>
    `;
  }
  function catChosenHTML() {
    const c = S.calc, cat = c.cat;
    if (cat) {
      const cc = catCommission(cat, c.scheme);
      const warn = cc == null ? `<div class="small" style="color:var(--red);font-weight:800">⚠️ Bu toifa ${esc(c.scheme)} sxemasida sotilmaydi</div>` : "";
      return `<div class="srow" style="margin-top:0"><span class="t">${esc(cat.uz)}<br>
        <span class="small muted">${cc != null ? `komissiya <b>${g(cc)}%</b>` : ""}${cat.disc ? " · chegirmali" : ""} · saqlash ${cat.special ? "maxsus" : "standart"} tarif, ${cat.free} kun bepul</span>${warn}</span>
        <button class="chip" data-act="catclear">✕</button></div>`;
    }
    return `<div class="inp"><input id="catQ" placeholder="🔎 soyabon, ryukzak, oshxona…" autocomplete="off"></div>
      <div id="catList" class="plist" style="gap:6px;margin-top:8px"></div>
      <div class="small muted" style="margin:6px 4px 0">Tanlanmasa: ${g(S.settings.commission_pct)}% (taxminiy)</div>`;
  }
  function mountCatSearch() {
    const q = $("#catQ");
    if (!q) return;
    let timer;
    q.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const v = q.value.trim();
        if (v.length < 2) { $("#catList").innerHTML = ""; return; }
        try {
          const d = await api("GET", "/api/categories?q=" + encodeURIComponent(v));
          S._catResults = d.categories;
          $("#catList").innerHTML = d.categories.map((c, i) => {
            const cc = catCommission(c, S.calc.scheme);
            return `<button class="srow" style="margin:0;text-align:left;width:100%" data-catpick="${i}"><span class="t small">${esc(c.uz)}</span>
              <b class="num" style="white-space:nowrap">${cc != null ? g(cc) + "%" : "—"}</b></button>`;
          }).join("") || `<div class="small muted">Topilmadi — boshqa so'z yozing</div>`;
        } catch (e) { /* tarmoq */ }
      }, 250);
    });
  }
  function refreshCalcParts() {
    const c = S.calc;
    const L = parseNumber(c.length_cm), W = parseNumber(c.width_cm), H = parseNumber(c.height_cm);
    const li = window.UzCalc.uzumLiters(L || 0, W || 0, H || 0);
    const info = $("#litersInfo");
    if (info) info.innerHTML = li ? `📦 ${li} litr → Uzum logistikasi <b>${fmt(window.UzCalc.uzumLogistics(li))}</b> so'm/dona`
      : `⚠️ O'lcham kiritilmasa, logistika taxminiy (${fmt(S.settings.logistics_fee)} so'm)`;
    const off = $("#offers");
    if (off) {
      const all = cargoOffers(c);
      const ok = all.filter((x) => x.ok), bad = all.filter((x) => !x.ok);
      const okHTML = ok.map((x) => `<button class="srow offer ${String(c.cargo_id) === String(x.cargo.id) ? "on" : ""}" data-cargo="${x.cargo.id}" style="width:100%;text-align:left;display:block;padding:10px 12px">
          <div style="display:flex;justify-content:space-between;gap:8px"><b>${x.cargo.mode === "avia" ? "✈️" : "🚛"} ${esc(x.cargo.name)}${x.cargo.verified ? "" : " ❔"}</b><b class="num" style="color:${x.r.profit >= 0 ? "var(--green)" : "var(--red)"}">${fmt(x.r.profit)}</b></div>
          <div class="small muted">${x.days ? `${x.cargo.days_min || "?"}–${x.days} kun (real ~${x.real_days})` : "muddat ?"} · ${"★".repeat(x.cargo.rating || 3)} · kargo+olib kelish ${fmt(x.ship)} so'm/dona · ball ${x.score}</div>
          <div class="badges" style="margin-top:4px">${x.badges.map((b) => `<span class="badge">${b}</span>`).join("")}</div>
        </button>`).join("");
      const badHTML = bad.length ? `<details class="more"><summary>✖️ Mos emas (${bad.length})</summary>${bad.map((x) =>
        `<div class="small" style="padding:6px 4px;border-bottom:1px dashed var(--line)"><b>${esc(x.cargo.name)}</b> — <span class="muted">${esc(x.reason)}</span></div>`).join("")}</details>` : "";
      off.innerHTML = all.length
        ? `<div class="small muted" style="margin:10px 4px 6px;font-weight:800">Shu partiya uchun takliflar (narx 50% · tezlik 20% · sifat 15% · oq hujjat 10% · Olmaliq 5%):</div>`
          + (okHTML || `<div class="small muted">Mos kargo yo'q — tarifni qo'lda yozing.</div>`) + badHTML
        : `<div class="small muted" style="margin-top:8px">Kargolar ro'yxati bo'sh — «🚚 Kargo» bo'limida 📥 tugmasini bosing.</div>`;
    }
  }
  function mountCalc() {
    const view = $("#view");
    view.oninput = (e) => {
      const k = e.target.dataset.k;
      if (!k) return;
      S.calc[k] = e.target.value;
      saveDraft(); updateResult(); calcButtons();
    };
    view.onclick = (e) => {
      const st = e.target.closest("[data-step]");
      if (st) {
        const k = st.dataset.step, d = Number(st.dataset.d);
        const cur = parseNumber(S.calc[k]) || 0;
        S.calc[k] = String(Math.max(1, cur + d));
        $(`[data-k="${k}"]`).value = S.calc[k];
        haptic("sel"); saveDraft(); updateResult(); return;
      }
      const sch = e.target.closest("[data-scheme]");
      if (sch) {
        S.calc.scheme = sch.dataset.scheme;
        $$("#schemeSeg button").forEach((b) => b.classList.toggle("on", b === sch));
        $("#fboBox").classList.toggle("hidden", S.calc.scheme === "FBS");
        $("#catBox").innerHTML = catChosenHTML(); mountCatSearch();
        haptic("sel"); saveDraft(); updateResult(); calcButtons(); return;
      }
      const cpick = e.target.closest("[data-catpick]");
      if (cpick) {
        S.calc.cat = S._catResults[Number(cpick.dataset.catpick)];
        $("#catBox").innerHTML = catChosenHTML();
        haptic("ok"); saveDraft(); updateResult(); calcButtons(); return;
      }
      if (e.target.closest('[data-act="catclear"]')) {
        S.calc.cat = null; $("#catBox").innerHTML = catChosenHTML(); mountCatSearch();
        const q = $("#catQ"); if (q) q.focus();
        saveDraft(); updateResult(); return;
      }
      const cp = e.target.closest("[data-cargo]");
      if (cp) {
        const id = cp.dataset.cargo;
        S.calc.cargo_id = id ? Number(id) : null;
        $$(".cpk").forEach((b) => b.classList.toggle("on", b.dataset.cargo === id));
        $("#manualTariff").classList.toggle("hidden", !!id);
        if (!id) { const t = $('[data-k="tariff_usd_kg"]'); if (t) t.focus(); }
        haptic("sel"); saveDraft(); updateResult(); calcButtons();
      }
    };
    mountCatSearch();
    updateResult();
  }
  let lastVerdict = null;
  function updateResult() {
    refreshCalcParts();
    const box = $("#calcResult");
    if (!box) return;
    const inp = buildInput(S.calc);
    if (!inp) {
      lastVerdict = null;
      box.innerHTML = `<div class="empty"><div class="e">🧮</div>Narx, vazn, kargo va sotuv narxini yozing —<br>foyda shu yerda paydo bo'ladi</div>`;
      return;
    }
    const r = calculate(inp);
    if (lastVerdict && lastVerdict !== r.verdict) haptic(r.verdict === "KIRAMIZ" ? "ok" : r.verdict === "KIRMAYMIZ" ? "err" : "warn");
    lastVerdict = r.verdict;
    box.innerHTML = resultHTML(inp, r, true);
    const sl = $("#priceSlider");
    if (sl) sl.addEventListener("input", (e) => {
      S.calc.sell_price = fmt(Number(e.target.value));
      $('[data-k="sell_price"]').value = S.calc.sell_price;
      saveDraft();
      const inp2 = buildInput(S.calc); const r2 = calculate(inp2);
      if (lastVerdict !== r2.verdict) haptic(r2.verdict === "KIRAMIZ" ? "ok" : "warn");
      lastVerdict = r2.verdict;
      // slayderni qayta chizmasdan faqat yuqori qismini yangilaymiz
      $("#resTop").innerHTML = resultTop(inp2, r2);
      $("#resRest").innerHTML = resultRest(inp2, r2);
      $("#slVal").textContent = fmt(inp2.sell_price) + " so'm";
      refreshCalcParts();
    });
  }
  function resultTop(inp, r) {
    const V = VERDICT[r.verdict];
    const mPct = Math.max(0, Math.min(100, r.margin_pct / (inp.target_margin_pct * 1.5) * 100));
    const xPct = Math.max(0, Math.min(100, r.multiple / 4.5 * 100));
    const warn = r.logistics_estimated ? `<div class="small" style="color:var(--amber);font-weight:800;margin-bottom:8px">⚠️ O'lcham kiritilmagan — logistika taxminiy</div>` : "";
    return `
      <div class="verdict ${vcls(r.verdict)}"><span class="em">${V.e}</span><div><b>${V.t}</b><span>${V.s}</span></div></div>
      ${warn}
      <div class="kpis">
        <div class="kpi"><b class="num" style="color:${r.profit >= 0 ? "var(--green)" : "var(--red)"}">${fmt(r.profit)}</b><span>foyda / dona</span></div>
        <div class="kpi"><b class="num">${r.margin_pct.toFixed(1)}%</b><span>sof marja</span></div>
        <div class="kpi"><b class="num">${r.multiple.toFixed(2)}x</b><span>sotuv/tannarx</span></div>
      </div>
      <div class="meter"><div class="row"><span>Marja</span><span>maqsad ${g(inp.target_margin_pct)}%</span></div>
        <div class="bar"><i style="width:${mPct}%"></i><span class="goal" style="left:${100 / 1.5}%"></span></div></div>
      <div class="meter"><div class="row"><span>Sotuv / tannarx</span><span>oltin qoida 3x</span></div>
        <div class="bar"><i style="width:${xPct}%;background:var(--grad-cool)"></i><span class="goal" style="left:${3 / 4.5 * 100}%"></span></div></div>`;
  }
  function resultRest(inp, r) {
    const s = inp.sell_price;
    const other = r.logistics + r.tax + r.payout + r.storage;
    const parts = [
      ["Tannarx", r.landed, "#ff6b5a"], ["Komissiya", r.commission, "#7b5cff"], ["Reklama", r.ads, "#ff4f9a"],
      ["Brak", r.returns, "#ffb020"], ["Logistika, soliq", other, "#3fa7ff"], ["Foyda", Math.max(r.profit, 0), "#1fbf6b"],
    ];
    const total = parts.reduce((a, p) => a + p[1], 0) || 1;
    const bar = parts.map((p) => `<i style="width:${p[1] / total * 100}%;background:${p[2]}"></i>`).join("");
    const legend = parts.map((p) => `<div><span><i class="dot" style="background:${p[2]}"></i>${p[0]}</span><b class="num">${fmt(p[1])}</b></div>`).join("");
    const usd = S.settings.usd_rate || 1;
    const kgNote = r.cargo_by_m3 ? "kub metr bo'yicha" : r.volume_kg > r.actual_kg
      ? `⚠️ hajmiy ${r.volume_kg.toFixed(2)} kg &gt; haqiqiy ${r.actual_kg.toFixed(2)} kg` : `${r.charge_kg.toFixed(2)} kg`;
    const ln = (label, v, minus) => v ? `<div class="ln"><span>${label}</span><b class="num">${minus ? "−" : ""}${fmt(v)}</b></div>` : "";
    const vat = inp.uzum_vat_pct ? ` + QQS ${g(inp.uzum_vat_pct)}%` : "";
    return `
      <div class="small muted" style="margin-top:14px;font-weight:800">${fmt(s)} so'm qayerga ketadi:</div>
      <div class="split">${bar}</div>
      <div class="legend">${legend}</div>
      ${r.profit < 0 ? `<p class="small" style="color:var(--red);font-weight:800">Zarar: ${fmt(r.profit)} so'm / dona</p>` : ""}
      <details class="more" open><summary>🧾 Batafsil hisob (1 dona)</summary>
        <div class="receipt">
          ${ln(`Tovar (${g(inp.price_cny)} ¥ + konvertatsiya ${g(inp.fx_spread_pct)}%)`, r.goods)}
          ${ln(`Bayer xizmati ${g(inp.buyer_pct)}%`, r.buyer)}
          ${ln(`Kargo (${kgNote})`, r.cargo)}
          ${ln("Xitoy ichki yetkazish", r.china_ship)}
          ${ln("Qadoq, shtrix-kod", r.pack)}
          ${ln(`Kargodan olib kelish (${inp.qty} dona)`, r.trip)}
          ${ln("Uzum omboriga topshirish", r.uzum_trip)}
          <div class="ln tot"><span>1 dona tannarx</span><b class="num">${fmt(r.landed)}</b></div>
          ${ln(`Uzum komissiyasi ${g(inp.commission_pct)}%${vat} (ekvayring ichida)`, r.commission, true)}
          ${ln(r.logistics_estimated ? "Logistika (⚠️ taxminiy)" : `Logistika (${r.liters} l)`, r.logistics, true)}
          ${ln("FBO saqlash (taxminiy)", r.storage, true)}
          ${ln(`Aylanma solig'i ${g(inp.tax_pct)}%`, r.tax, true)}
          ${ln(`Pul yechish ${g(inp.payout_fee_pct)}%`, r.payout, true)}
          ${ln(`Reklama ${g(inp.ads_pct)}%`, r.ads, true)}
          ${ln(`Brak va qaytarish ${g(inp.returns_pct)}%`, r.returns, true)}
          <div class="ln tot"><span>Sof foyda</span><b class="num">${fmt(r.profit)}</b></div>
          <div class="ln"><span>Zararsizlik narxi</span><b class="num">${fmt(r.breakeven_price)}</b></div>
        </div>
      </details>
      <div class="kpis" style="margin-top:12px">
        <div class="kpi"><b class="num">${fmtK(r.batch_cost)}</b><span>partiyaga pul ($${fmt(r.batch_cost / usd)})</span></div>
        <div class="kpi"><b class="num" style="color:var(--green)">${fmtK(r.batch_profit)}</b><span>hammasi sotilsa</span></div>
        <div class="kpi"><b class="num">${r.roi_pct.toFixed(0)}%</b><span>pulga foyda</span></div>
      </div>`;
  }
  function resultHTML(inp, r, withSlider) {
    let slider = "";
    if (withSlider && r.breakeven_price) {
      const lo = Math.max(1000, Math.floor(r.breakeven_price * 0.7 / 1000) * 1000);
      const hi = Math.ceil(Math.max(inp.sell_price * 1.6, (r.target_price || inp.sell_price) * 1.4) / 1000) * 1000;
      const val = Math.min(Math.max(inp.sell_price, lo), hi);
      slider = `<div class="slider">
        <div class="row" style="display:flex;justify-content:space-between;font-weight:900"><span>🎚 Narxni sinab ko'ring</span><span id="slVal" class="num">${fmt(inp.sell_price)} so'm</span></div>
        <input type="range" id="priceSlider" min="${lo}" max="${hi}" step="500" value="${val}">
        <div class="ticks"><span>0 foyda: ${fmt(r.breakeven_price)}</span><span>${g(inp.target_margin_pct)}%: ${fmt(r.target_price)}</span></div>
      </div>`;
    }
    return `<div id="resTop">${resultTop(inp, r)}</div>${slider}<div id="resRest">${resultRest(inp, r)}</div>`;
  }
  function calcButtons() {
    const valid = !!buildInput(S.calc);
    setMain({ text: S.editingId ? "💾 O'zgarishni saqlash" : "💾 Saqlash", enabled: valid, shine: valid, onClick: saveCalc });
    setSecondary({ text: "🧹 Tozalash", onClick: async () => {
      if (!(await ask("Formani tozalaymizmi?"))) return;
      clearDraft(); render();
    } });
  }
  let saving = false;
  async function saveCalc() {
    if (saving) return;
    const c = S.calc;
    if (!buildInput(c)) { haptic("err"); return toast("Avval asosiy maydonlarni to'ldiring"); }
    if (!c.name.trim()) { haptic("err"); toast("Tovar nomini yozing ✍️"); const n = $('[data-k="name"]'); if (n) n.focus(); return; }
    saving = true;
    if (tg) tg.MainButton.showProgress();
    try {
      if (c.cat && catCommission(c.cat, c.scheme) == null) { haptic("err"); saving = false; tg && tg.MainButton.hideProgress();
        return toast(`Bu toifa ${c.scheme} da sotilmaydi`); }
      const body = { name: c.name, source_link: c.source_link, cargo_id: c.cargo_id, note: c.note, item: itemPayload(c),
        category_id: c.cat ? c.cat.id : null, scheme: c.scheme || "FBO" };
      let p;
      if (S.editingId) p = (await api("PUT", "/api/products/" + S.editingId, body)).product;
      else p = (await api("POST", "/api/products", { ...body, status: c.status || "idea" })).product;
      haptic("ok");
      if (p.result.verdict === "KIRAMIZ") confetti();
      toast(S.editingId ? "✅ Yangilandi" : "✅ Saqlandi");
      clearDraft();
      await reload();
      S.tab = "products"; render();
      productSheet(p.id);
    } catch (e) { haptic("err"); alertMsg(e.message); }
    finally { saving = false; if (tg) tg.MainButton.hideProgress(); }
  }

  // ---------- 📦 Tovarlar ----------
  function productCard(p) {
    const r = p.today || p.result;
    const d = p.today ? p.today.profit - p.result.profit : 0;
    const delta = Math.abs(d) >= 100 ? `<div class="delta ${d > 0 ? "up" : "down"}">${d > 0 ? "▲" : "▼"} ${fmt(Math.abs(d))} bugungi kurs</div>` : "";
    return `<button class="pcard ${vcls(r.verdict)}" data-pid="${p.id}">
      <div class="top"><div><div class="name">${esc(p.name)}</div>
        <div class="meta">${esc(p.status_label)} · ${esc(p.created_by_name || "")} · ${esc((p.created_at || "").slice(0, 5))}</div></div>
        <div class="profit"><b class="num">${fmt(r.profit)}</b><span>${r.margin_pct.toFixed(0)}% · ${r.multiple.toFixed(1)}x</span>${delta}</div>
      </div></button>`;
  }
  function productsView() {
    const counts = S.stats.by_status;
    const chips = [`<button class="chip ${S.filter === "all" ? "on" : ""}" data-f="all">Hammasi ${S.products.length}</button>`]
      .concat(STATUS_ORDER.map((k) => `<button class="chip ${S.filter === k ? "on" : ""}" data-f="${k}">${esc(S.statuses[k])} ${counts[k] || 0}</button>`)).join("");
    return `<div class="section-title" style="margin-top:4px">📦 Tovarlarim</div>
      <div class="chips">${chips}</div>
      <input class="search" id="q" placeholder="🔎 Qidirish…" value="${esc(S.q)}">
      <div class="plist" id="plist"></div>`;
  }
  function mountProducts() {
    const draw = () => {
      const q = S.q.trim().toLowerCase();
      const list = S.products.filter((p) => (S.filter === "all" || p.status === S.filter) && (!q || p.name.toLowerCase().includes(q)));
      $("#plist").innerHTML = list.map(productCard).join("") ||
        `<div class="empty"><div class="e">🫙</div>Bu yerda hozircha bo'sh</div>`;
    };
    $("#q").addEventListener("input", (e) => { S.q = e.target.value; draw(); });
    draw();
  }
  function productSheet(id) {
    const p = S.products.find((x) => x.id === id);
    if (!p) return;
    const r = p.today || p.result;
    const idx = STATUS_ORDER.indexOf(p.status);
    const steps = STATUS_ORDER.map((k, i) => `<button class="stp ${k === p.status ? "on" : i < idx && p.status !== "stopped" ? "done" : ""}" data-status="${k}">${esc(S.statuses[k])}</button>`).join("");
    const d = p.today ? p.today.profit - p.result.profit : 0;
    const rateNote = Math.abs(d) >= 1
      ? `<p class="small muted">📅 Saqlangan kunda foyda ${fmt(p.result.profit)} edi, bugungi kurs bilan ${fmt(p.today.profit)} (${d > 0 ? "+" : "−"}${fmt(Math.abs(d))}).</p>` : "";
    openSheet(`
      <h2>${esc(p.name)}</h2>
      <div class="small muted">#${p.id} · ${esc(p.created_by_name)} · ${esc(p.created_at)} · 🚚 ${esc(p.cargo_name)}</div>
      <div class="small muted">🏷 ${p.category ? esc(p.category) : "toifa tanlanmagan"} · ${esc(p.scheme || "FBO")}</div>
      <div class="field"><label>Holati</label><div class="steps">${steps}</div></div>
      ${p.source_link ? `<button class="btn" data-act="link" style="margin-top:10px">🔗 Taobao/1688 da ochish</button>` : ""}
      <div class="card result">${resultHTML(Object.assign({}, p.input, rebaseInput(p.input)), r, false)}</div>
      ${rateNote}
      <div class="field"><label>Izoh</label><div class="inp"><textarea id="pnote" placeholder="Sotuvchi, rang, namuna natijasi…" style="min-height:70px">${esc(p.note || "")}</textarea></div></div>
      <div class="btns">
        <button class="btn" data-act="edit">✏️ Tahrirlash</button>
        <button class="btn danger" data-act="del">🗑 O'chirish</button>
      </div>`, (body) => {
      body.addEventListener("click", async (e) => {
        const st = e.target.closest("[data-status]");
        if (st && st.dataset.status !== p.status) {
          haptic("sel");
          try { await api("PUT", "/api/products/" + p.id, { status: st.dataset.status }); await reload(); haptic("ok");
            toast(S.statuses[st.dataset.status]); render(); productSheet(p.id); } catch (er) { alertMsg(er.message); }
          return;
        }
        const a = e.target.closest("[data-act]");
        if (!a) return;
        if (a.dataset.act === "link") { if (tg) tg.openLink(p.source_link); else window.open(p.source_link); }
        if (a.dataset.act === "edit") {
          const i = p.input, n = (v) => (v ? String(v) : "");
          const cat = p.category_obj || null, scheme = p.scheme || "FBO";
          // komissiya toifadan kelgan bo'lsa, "qo'lda" maydoni bo'sh qoladi
          const manualComm = cat && catCommission(cat, scheme) === i.commission_pct ? "" : n(i.commission_pct);
          S.calc = { ...emptyCalc(), name: p.name, source_link: p.source_link || "", price_cny: n(i.price_cny), weight_g: n(i.weight_g),
            qty: n(i.qty), cargo_id: p.cargo_id, tariff_usd_kg: n(i.tariff_usd_kg), sell_price: fmt(i.sell_price),
            commission_pct: manualComm, china_ship_cny: n(i.china_ship_cny), length_cm: n(i.length_cm),
            width_cm: n(i.width_cm), height_cm: n(i.height_cm), sell_days: n(i.sell_days), scheme, cat,
            status: p.status, note: p.note || "" };
          S.editingId = p.id; saveDraft(); closeSheet(); S.tab = "calc"; render();
        }
        if (a.dataset.act === "del") {
          if (!(await ask(`«${p.name}» o'chirilsinmi?`))) return;
          try { await api("DELETE", "/api/products/" + p.id); haptic("ok"); toast("🗑 O'chirildi"); await reload(); closeSheet(); render(); }
          catch (er) { alertMsg(er.message); }
        }
      });
      $("#pnote", body).addEventListener("change", async (e) => {
        try { await api("PUT", "/api/products/" + p.id, { note: e.target.value }); p.note = e.target.value; toast("📝 Izoh saqlandi"); }
        catch (er) { alertMsg(er.message); }
      });
    });
  }
  function rebaseInput(i) {
    const o = {};
    RATE_FIELDS.forEach((k) => (o[k] = S.settings[k]));
    return o;
  }

  // ---------- 🚚 Kargolar ----------
  function cargosView() {
    const list = S.cargos.map((c) => `<button class="ccard" data-cid="${c.id}">
      <div class="top"><div class="name">${c.mode === "avia" ? "✈️" : "🚛"} ${esc(c.name)}</div><div class="tariff num">${g(c.tariff_usd_kg)} $/kg</div></div>
      <div class="badges">
        <span class="badge">⏱ ${c.days_min ? `${c.days_min}–${c.days_max} kun` : "muddat ?"}</span>
        <span class="badge">${"★".repeat(c.rating || 3)}</span>
        <span class="badge ${c.series_ok === 0 ? "no" : c.series_ok === 1 ? "ok" : ""}">${c.series_ok === 0 ? "🧪 faqat namuna" : c.series_ok === 1 ? "📦 partiya ✅" : "📦 partiya ?"}</span>
        ${c.min_kg ? `<span class="badge">min ${g(c.min_kg)} kg</span>` : ""}
        ${c.tariff_usd_kg > 0 ? "" : `<span class="badge no">⚠️ tarif kiritilmagan</span>`}
        <span class="badge ${c.olmaliq ? "ok" : "no"}">${c.olmaliq ? "📍 Olmaliqda bor" : "✖️ Olmaliq"}</span>
        <span class="badge ${c.white_docs ? "ok" : "no"}">${c.white_docs ? "✅" : "✖️"} oq hujjat</span>
        ${c.usd_m3 ? `<span class="badge">${g(c.usd_m3)} $/m³</span>` : ""}
        ${c.verified ? "" : `<span class="badge" style="color:var(--amber)">❔ saytdan${c.checked_at ? " · " + esc(c.checked_at) : ""}</span>`}
      </div>
      ${c.note ? `<div class="small muted" style="margin-top:6px">${esc(c.note)}</div>` : ""}
    </button>`).join("");
    return `<div class="section-title" style="margin-top:4px">🚚 Kargolar <span class="muted small" style="margin-left:auto">arzonidan</span></div>
      <p class="small muted" style="margin:4px 4px 0">Qaysi biri yaxshiroq — 🧮 Hisob bo'limida aniq tovar uchun taqqoslanadi (narx, tezlik, sifat, Olmaliq).</p>
      <div class="plist">${list || `<div class="empty"><div class="e">🚚</div>Hali kargo yo'q.</div>`}</div>
      <button class="btn cool" data-act="suggest" style="margin-top:14px">📥 Kargolar ro'yxatini yangilash (cargos.json)</button>
      <button class="btn" data-act="cargoai" style="margin-top:10px">🚚 Kargo bo'yicha savol (qo'llanma + AI)</button>`;
  }
  function cargoSheet(id) {
    const c = id ? S.cargos.find((x) => x.id === id) : { name: "", mode: "avto", tariff_usd_kg: "", days_min: "", days_max: "",
      white_docs: 0, olmaliq: 0, note: "", rating: 3, verified: 1, usd_m3: "", vol_divisor: "", pickup_cost: "", source: "",
      series_ok: 1, min_kg: "", checked_at: "" };
    if (!c) return;
    const f = { ...c };
    const inp = (idk, val, ph, unit, mode) => `<div class="inp"><input id="${idk}" value="${esc(val ?? "")}" inputmode="${mode || "decimal"}" placeholder="${esc(ph)}">${unit ? `<span class="unit">${unit}</span>` : ""}</div>`;
    const stars = () => [1, 2, 3, 4, 5].map((i) => `<button class="chip ${i <= f.rating ? "on" : ""}" data-star="${i}" style="padding:8px 11px">★</button>`).join("");
    openSheet(`
      <h2>${id ? "✏️ " + esc(c.name) : "➕ Yangi kargo"}</h2>
      ${c.source ? `<button class="btn" data-act="src" style="margin-top:6px">🔗 Manba: narxni tekshirish</button>` : ""}
      <div class="field"><label>Nomi</label>${inp("c_name", f.name, "iPost, MK Express…", "", "text")}</div>
      <div class="field"><label>Turi</label><div class="seg" id="c_mode">
        <button data-m="avia" class="${f.mode === "avia" ? "on" : ""}">✈️ Avia</button><button data-m="avto" class="${f.mode === "avto" ? "on" : ""}">🚛 Avto</button></div></div>
      <div class="grid2">
        <div class="field"><label>Tarif</label>${inp("c_tariff", f.tariff_usd_kg, "6.7", "$/kg")}</div>
        <div class="field"><label>Kub metr narxi (bo'lsa)</label>${inp("c_m3", f.usd_m3, "700", "$/m³")}</div>
      </div>
      <div class="grid2">
        <div class="field"><label>Muddat: kamida</label>${inp("c_dmin", f.days_min, "12", "kun", "numeric")}</div>
        <div class="field"><label>ko'pi bilan</label>${inp("c_dmax", f.days_max, "15", "kun", "numeric")}</div>
      </div>
      <div class="grid2">
        <div class="field"><label>Hajmiy vazn bo'luvchisi</label>${inp("c_vd", f.vol_divisor, g(S.settings.vol_divisor), "")}</div>
        <div class="field"><label>Punktdan uyga olib kelish</label>${inp("c_pick", f.pickup_cost, f.olmaliq ? g(S.settings.olmaliq_pickup_cost) : g(S.settings.trip_cost), "so'm")}</div>
      </div>
      <div class="field"><label>Minimal yuk (bo'lsa)</label>${inp("c_minkg", f.min_kg, "masalan 100", "kg")}</div>
      <div class="field"><label>Sifat / ishonch (brak, yo'qotish, muomala)</label><div class="chips" id="c_stars">${stars()}</div></div>
      <div class="card" style="padding:4px 14px">
        <div class="toggle">📍 Olmaliqda punkti bor<span class="switch ${f.olmaliq ? "on" : ""}" data-t="olmaliq"></span></div>
        <div class="toggle" style="border-top:1px solid var(--line)">«Oq» hujjat (invoys, GTD) beradi<span class="switch ${f.white_docs ? "on" : ""}" data-t="white_docs"></span></div>
        <div class="toggle" style="border-top:1px solid var(--line)">📦 Partiya (3+ bir xil dona) qabul qiladi<span class="switch ${f.series_ok === 0 ? "" : "on"}" data-t="series_ok"></span></div>
        <div class="toggle" style="border-top:1px solid var(--line)">✅ Narxni o'zim tasdiqladim<span class="switch ${f.verified ? "on" : ""}" data-t="verified"></span></div>
      </div>
      <div class="field"><label>Izoh, telefon, manzil</label><div class="inp"><textarea id="c_note" style="min-height:70px">${esc(f.note || "")}</textarea></div></div>
      <p class="small muted">Bo'sh qoldirilgan maydonlar sozlamadagi standart qiymatni oladi. Kargo haqiqiy vazn, hajmiy vazn va kub metr narxidan qaysi biri qimmat bo'lsa, shuni hisoblaydi.</p>
      ${id ? `<button class="btn danger" data-act="cdel" style="margin-top:14px">🗑 O'chirish</button>` : ""}
    `, (body) => {
      body.addEventListener("click", async (e) => {
        const m = e.target.closest("[data-m]");
        if (m) { f.mode = m.dataset.m; $$("#c_mode button", body).forEach((b) => b.classList.toggle("on", b === m)); haptic("sel"); }
        const t = e.target.closest("[data-t]");
        if (t) { f[t.dataset.t] = f[t.dataset.t] ? 0 : 1; t.classList.toggle("on", !!f[t.dataset.t]); haptic("sel"); }
        const st = e.target.closest("[data-star]");
        if (st) { f.rating = Number(st.dataset.star); $("#c_stars").innerHTML = stars(); haptic("sel"); }
        if (e.target.closest('[data-act="src"]')) { if (tg) tg.openLink(c.source); else window.open(c.source); }
        if (e.target.closest('[data-act="cdel"]')) {
          if (!(await ask(`«${c.name}» kargosi o'chirilsinmi?`))) return;
          try { await api("DELETE", "/api/cargos/" + id); haptic("ok"); toast("🗑 O'chirildi"); await reload(); closeSheet(); render(); }
          catch (er) { alertMsg(er.message); }
        }
      });
    }, {
      text: "💾 Saqlash", color: "#3fa7ff", onClick: async () => {
        const num = (sel) => { const v = parseNumber($(sel).value); return isNaN(v) ? null : v; };
        const body = { name: $("#c_name").value, mode: f.mode, tariff_usd_kg: num("#c_tariff"),
          days_min: $("#c_dmin").value || null, days_max: $("#c_dmax").value || null,
          white_docs: f.white_docs, olmaliq: f.olmaliq, verified: f.verified, rating: f.rating,
          usd_m3: num("#c_m3"), vol_divisor: num("#c_vd"), pickup_cost: num("#c_pick"),
          note: $("#c_note").value, source: c.source || null,
          series_ok: f.series_ok === 0 ? 0 : 1, min_kg: num("#c_minkg"), checked_at: c.checked_at || null };
        if (!body.name.trim()) { haptic("err"); return toast("Nomini yozing"); }
        if (!(body.tariff_usd_kg > 0)) { haptic("err"); return toast("Tarifni yozing"); }
        try {
          if (id) await api("PUT", "/api/cargos/" + id, body); else await api("POST", "/api/cargos", body);
          haptic("ok"); toast("✅ Saqlandi"); await reload(); closeSheet(); render();
        } catch (er) { haptic("err"); alertMsg(er.message); }
      },
    });
  }

  // ---------- ✨ AI ----------
  const AI_MODES = {
    tr: { e: "🈶", t: "Xitoycha → o'zbekcha", s: "Tovar tavsifi yoki sotuvchi xabarini tarjima", ph: "Xitoycha matnni shu yerga qo'ying…" },
    seller: { e: "✉️", t: "Sotuvchiga xabar", s: "O'zbekcha yozing — xitoycha xabar tayyor bo'ladi", ph: "Masalan: 50 dona narxi qancha, namuna bormi, qadoq o'lchami?" },
    cargo: { e: "🚚", t: "Kargo bo'yicha savol", s: "Qo'llanma va kargolar ro'yxatiga tayanib javob", ph: "Masalan: 40 kg ryukzak partiyasini qaysi kargo bilan olgan ma'qul?" },
    card: { e: "📝", t: "Uzum kartochkasi", s: "Sarlavha, tavsif, qidiruv so'zlari (uz + ru)", ph: "Nomi, material, o'lcham, rang, kimga mos…" },
  };
  function aiView() {
    if (!S.ai) return `<div class="empty"><div class="e">🔌</div>Gemini kaliti kiritilmagan.<br>.env → GEMINI_API_KEY</div>`;
    const modes = Object.entries(AI_MODES).map(([k, m]) => `<button class="mode ${S.aiMode === k ? "on" : ""}" data-mode="${k}">
      <span class="e">${m.e}</span><div><b>${m.t}</b><span>${m.s}</span></div></button>`).join("");
    return `<section class="hero" style="background:var(--grad-cool)"><h1>✨ AI yordamchi</h1><div class="sub">Gemini · natijani har doim o'zingiz tekshiring</div></section>
      <div class="modes" style="margin-top:14px">${modes}</div>
      <div class="field"><div class="inp"><textarea id="aiText" placeholder="${esc(AI_MODES[S.aiMode].ph)}">${esc(S.aiText)}</textarea></div></div>
      <div id="aiOut">${S.aiOut ? aiOutHTML(S.aiOut) : ""}</div>
      <p class="small muted">🔒 Maxfiy ma'lumot (karta, parol, pasport) yubormang.</p>`;
  }
  function aiOutHTML(t) {
    return `<div class="card"><div class="ai-out">${esc(t)}</div><button class="btn" data-act="copy" style="margin-top:12px">📋 Nusxalash</button></div>`;
  }
  function mountAI() {
    const v = $("#view");
    v.onclick = (e) => {
      const m = e.target.closest("[data-mode]");
      if (m) { S.aiMode = m.dataset.mode; haptic("sel"); S.aiOut = ""; render(); return; }
      if (e.target.closest('[data-act="copy"]')) copyText(S.aiOut);
    };
    const ta = $("#aiText");
    if (ta) ta.addEventListener("input", (e) => (S.aiText = e.target.value));
  }
  function aiButtons() {
    if (!S.ai) return setMain(null);
    setMain({ text: "✨ Yuborish", color: "#7b5cff", onClick: async () => {
      if (!S.aiText.trim()) { haptic("err"); return toast("Matn yozing"); }
      tg && tg.MainButton.showProgress();
      $("#aiOut").innerHTML = `<div class="card"><div class="empty"><div class="e" style="animation:bob 1s infinite">✨</div>O'ylayapman…</div></div>`;
      try {
        S.aiOut = (await api("POST", "/api/ai", { mode: S.aiMode, text: S.aiText })).text;
        $("#aiOut").innerHTML = aiOutHTML(S.aiOut); haptic("ok");
      } catch (er) { $("#aiOut").innerHTML = ""; haptic("err"); alertMsg(er.message); }
      finally { tg && tg.MainButton.hideProgress(); }
    } });
  }
  async function copyText(t) {
    try { await navigator.clipboard.writeText(t); }
    catch (e) {
      const ta = document.createElement("textarea"); ta.value = t; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (er) { /* */ } ta.remove();
    }
    haptic("ok"); toast("📋 Nusxalandi");
  }

  // ---------- ⚙️ Sozlamalar ----------
  const GROUPS = [
    ["💱 Kurslar", ["cny_rate", "usd_rate", "fx_spread_pct"]],
    ["🇨🇳 Xitoy tomoni", ["buyer_pct", "china_ship_cny", "vol_divisor"]],
    ["🚗 Qatnovlar va qadoq", ["trip_cost", "olmaliq_pickup_cost", "uzum_trip_cost", "pack_cost"]],
    ["🍇 Uzum", ["commission_pct", "logistics_fee", "uzum_vat_pct", "payout_fee_pct", "ads_pct", "returns_pct", "sell_days"]],
    ["🧾 Soliq", ["tax_pct"]],
    ["🎯 Maqsad", ["target_margin_pct", "budget_usd"]],
  ];
  function settingsSheet(onlyKeys) {
    const meta = Object.fromEntries(S.meta.map((m) => [m.key, m]));
    const owner = S.me.role === "owner";
    const groups = (onlyKeys ? [["💱 Bugungi kurs", onlyKeys]] : GROUPS).map(([t, keys]) => `<div class="sgroup"><h3>${t}</h3>
      ${keys.filter((k) => meta[k]).map((k) => `<div class="srow"><span class="t">${esc(meta[k].title)}</span>
        <div class="inp"><input data-s="${k}" value="${S.settings[k] >= 1000 ? fmt(S.settings[k]) : g(S.settings[k])}" inputmode="decimal" ${owner ? "" : "disabled"}>
        <span class="unit">${esc(meta[k].unit)}</span></div></div>`).join("")}</div>`).join("");
    const home = !onlyKeys && ver("8.0") && tg.addToHomeScreen
      ? `<button class="btn cool" data-act="home" style="margin-top:18px">📲 Telefon ekraniga qo'shish</button>` : "";
    const t = S.tariffs || {};
    const tariffBox = onlyKeys ? "" : `<div class="sgroup"><h3>📜 Uzum rasmiy tariflari</h3><div class="card" style="margin-top:6px">
      <div class="small">Komissiya jadvali: <b>${t.count || 0}</b> toifa · yangilangan: <b>${esc(t.fetched_at || "—")}</b><br>
      Logistika: 1 l gacha 5 250, har qo'shimcha litr +250, maks 50 000 so'm (01.06.2026 dan).<br>
      Ekvayring komissiya ichida. Saqlash FBO'da aylanma 60 kundan oshsa.</div>
      <div class="btns"><button class="btn" data-act="tref">🔄 Hozir yangilash</button><button class="btn" data-act="manual">📖 Qo'llanma</button></div></div></div>`;
    openSheet(`<h2>${onlyKeys ? "💱 Kurslar" : "⚙️ Sozlamalar"}</h2>
      <div class="small muted">${owner ? "O'zgartirsangiz, darhol saqlanadi va barcha hisoblarga ta'sir qiladi." : "Faqat admin o'zgartiradi."}</div>
      ${groups}${tariffBox}${home}
      ${onlyKeys ? `<button class="btn" data-act="all" style="margin-top:14px">⚙️ Barcha sozlamalar</button>` : ""}`, (body) => {
      body.addEventListener("change", async (e) => {
        const k = e.target.dataset.s;
        if (!k) return;
        const v = parseNumber(e.target.value);
        if (isNaN(v)) { haptic("err"); return toast("Son kiriting"); }
        try { await api("PUT", "/api/settings", { [k]: v }); await reload(); haptic("ok"); toast("✅ " + meta[k].title); }
        catch (er) { haptic("err"); alertMsg(er.message); }
      });
      body.addEventListener("click", (e) => {
        const a = e.target.closest("[data-act]");
        if (!a) return;
        if (a.dataset.act === "home") tg.addToHomeScreen();
        if (a.dataset.act === "manual") { if (tg) tg.openLink(t.manual); else window.open(t.manual); }
        if (a.dataset.act === "tref") {
          a.textContent = "⏳ Yuklanmoqda…";
          api("POST", "/api/tariffs/refresh").then(async (d) => { await reload(); haptic("ok"); toast("✅ " + d.message); closeSheet(true); settingsSheet(); })
            .catch((er) => { haptic("err"); alertMsg(er.message); a.textContent = "🔄 Hozir yangilash"; });
        }
        if (a.dataset.act === "all") { closeSheet(true); settingsSheet(); }
      });
    }, null, () => render());
  }

  // ---------- sheet ----------
  let onSheetClose = null;
  function openSheet(html, mount, mainOpts, onClose) {
    const sh = $("#sheet"), ov = $("#overlay");
    $("#sheetBody").innerHTML = html;
    sh.classList.remove("hidden"); ov.classList.remove("hidden");
    sh.scrollTop = 0;
    requestAnimationFrame(() => { sh.classList.add("show"); ov.classList.add("show"); });
    S.sheetOpen = true;
    onSheetClose = onClose || null;
    haptic("impact", "soft");
    setSecondary(null);
    setMain(mainOpts || null);
    setBack(() => closeSheet());
    if (mount) mount($("#sheetBody"));
  }
  function closeSheet(silent) {
    const sh = $("#sheet"), ov = $("#overlay");
    sh.classList.remove("show"); ov.classList.remove("show");
    setTimeout(() => { if (!S.sheetOpen) { sh.classList.add("hidden"); ov.classList.add("hidden"); } }, 280);
    S.sheetOpen = false;
    if (silent) return;
    tabButtons();
    setBack(S.tab === "home" ? null : () => go("home"));
    const cb = onSheetClose; onSheetClose = null;
    if (cb) cb();
  }

  // ---------- umumiy bosishlar ----------
  document.addEventListener("click", (e) => {
    const tab = e.target.closest(".tab");
    if (tab) return go(tab.dataset.tab);
    if (e.target.closest("#overlay")) return closeSheet();
    if (S.sheetOpen) return;
    const t = e.target.closest("[data-go]");
    if (t) return go(t.dataset.go);
    const f = e.target.closest("[data-filter]");
    if (f) { S.filter = f.dataset.filter; S.tab = "products"; haptic("sel"); return render(); }
    const chip = e.target.closest("[data-f]");
    if (chip) { S.filter = chip.dataset.f; haptic("sel"); return render(); }
    const pc = e.target.closest("[data-pid]");
    if (pc) return productSheet(Number(pc.dataset.pid));
    const cc = e.target.closest("[data-cid]");
    if (cc) return cargoSheet(Number(cc.dataset.cid));
    const a = e.target.closest("[data-act]");
    if (a && a.dataset.act === "rates") return settingsSheet(["cny_rate", "usd_rate"]);
    if (a && a.dataset.act === "settings") return settingsSheet();
    if (a && a.dataset.act === "cargoai") { S.aiMode = "cargo"; S.aiOut = ""; return go("ai"); }
    if (a && a.dataset.act === "suggest") {
      return ask("data_seed/cargos.json dagi kargolar yuklansinmi? Borlari yangilanadi, siz qo'ygan reyting va qo'lda kiritilgan tarif saqlanadi.")
        .then(async (ok) => {
          if (!ok) return;
          try { const d = await api("POST", "/api/cargos/import"); await reload(); haptic("ok"); toast(`📥 ${d.added} yangi, ${d.updated} yangilandi`); render(); }
          catch (er) { alertMsg(er.message); }
        });
    }
    if (a && a.dataset.act === "newcalc") { if (!S.editingId && !S.calc.name) clearDraft(); return go("calc"); }
  });

  // ---------- start ----------
  async function start() {
    if (!tg || !tg.initData) {
      $("#view").innerHTML = `<div class="splash"><div><div class="logo">🔒</div><h2>Telegram orqali oching</h2>
        <p class="muted">Bu ilova faqat bot ichida ishlaydi.</p></div></div>`;
      return;
    }
    tg.ready();
    tg.expand();
    if (ver("7.7")) tg.disableVerticalSwipes();
    applyTheme();
    tg.onEvent("themeChanged", () => { applyTheme(); });
    if (ver("7.0") && tg.SettingsButton) { tg.SettingsButton.show(); tg.SettingsButton.onClick(() => settingsSheet()); }
    try {
      await Promise.all([reload(), loadDraft()]);
    } catch (e) {
      $("#view").innerHTML = `<div class="splash"><div><div class="logo">😕</div><h2>Ulanib bo'lmadi</h2><p class="muted">${esc(e.message)}</p>
        <button class="btn primary" onclick="location.reload()">Qayta urinish</button></div></div>`;
      return;
    }
    $("#tabs").classList.remove("hidden");
    const startParam = tg.initDataUnsafe && tg.initDataUnsafe.start_param;
    const [tabParam, idParam] = String(startParam || "").split("_");
    if (["calc", "products", "cargos", "ai"].includes(tabParam)) S.tab = tabParam;
    render();
    if (tabParam === "products" && idParam) productSheet(Number(idParam));
    updateClosingConfirm();
  }
  start();
})();
