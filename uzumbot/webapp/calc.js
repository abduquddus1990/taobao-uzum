// bot/calc.py ning aynan nusxasi — ilovada jonli hisob uchun.
// O'zgartirsangiz, ikkalasini birga o'zgartiring: tests/test_webapp.py ularni solishtiradi.
(function (root) {
  const LOGISTICS_BASE = 5250, LOGISTICS_PER_LITER = 250, LOGISTICS_MAX = 50000;
  const STORAGE_STANDARD = [[60, 0], [180, 12], [360, 18], [1e9, 24]];
  const STORAGE_SPECIAL = [[60, 0], [180, 12], [360, 14], [1e9, 18]];
  const CAP_STANDARD = 5000, CAP_SPECIAL = 3000;
  const pct = (x) => x / 100;
  const round6 = (x) => Math.round(x * 1e6) / 1e6;

  function uzumLiters(l, w, h) {
    if (!(l > 0 && w > 0 && h > 0)) return 0;
    return Math.ceil(round6(l * w * h / 1000));
  }
  function uzumLogistics(liters) {
    if (liters <= 0) return 0;
    return Math.min(LOGISTICS_BASE + Math.max(liters - 1, 0) * LOGISTICS_PER_LITER, LOGISTICS_MAX);
  }
  function storagePerUnit(liters, days, freeDays, special) {
    if (liters <= 0 || days <= 0) return 0;
    const grid = special ? STORAGE_SPECIAL : STORAGE_STANDARD;
    const cap = special ? CAP_SPECIAL : CAP_STANDARD;
    let total = 0;
    const n = Math.ceil(days);
    for (let t = 0; t < n; t++) {
      if (t < freeDays) continue;
      const turnover = Math.ceil(days - t);
      const rate = grid.find(([limit]) => turnover <= limit)[1];
      total += (1 - t / days) * Math.min(rate * liters, cap);
    }
    return total;
  }
  function priceForMargin(inp, landed, logistics, storage, margin) {
    const vat = 1 + pct(inp.uzum_vat_pct || 0);
    const c = pct(inp.commission_pct) * vat;
    const t = pct(inp.tax_pct), p = pct(inp.payout_fee_pct || 0);
    const ads = pct(inp.ads_pct), ret = pct(inp.returns_pct);
    const denom = 1 - c - t - ads - ret - p * (1 - c) - margin;
    if (denom <= 0) return null;
    return (landed + logistics * (1 - p) + storage) / denom;
  }

  function calculate(inp) {
    if (!(inp.qty > 0)) throw new Error("Partiya soni 0 dan katta bo'lishi kerak");
    const fx = 1 + pct(inp.fx_spread_pct);
    const goods = inp.price_cny * inp.cny_rate * fx;
    const buyer = goods * pct(inp.buyer_pct);

    const actual_kg = inp.weight_g / 1000;
    const L = inp.length_cm || 0, W = inp.width_cm || 0, H = inp.height_cm || 0;
    const cm3 = (L > 0 && W > 0 && H > 0) ? L * W * H : 0;
    const vd = inp.vol_divisor || 0;
    const volume_kg = (cm3 && vd > 0) ? cm3 / vd : 0;
    const charge_kg = Math.max(actual_kg, volume_kg);
    let cargo = charge_kg * inp.tariff_usd_kg * inp.usd_rate;
    let cargo_by_m3 = false;
    if (cm3 && (inp.cargo_usd_m3 || 0) > 0) {
      const byM3 = cm3 / 1e6 * inp.cargo_usd_m3 * inp.usd_rate;
      if (byM3 > cargo) { cargo = byM3; cargo_by_m3 = true; }
    }

    const trip = inp.trip_cost / inp.qty;
    const uzum_trip = (inp.uzum_trip_cost || 0) / inp.qty;
    const china_ship = (inp.china_ship_cny || 0) * inp.cny_rate * fx / inp.qty;
    const pack = inp.pack_cost || 0;
    const landed = goods + buyer + cargo + trip + uzum_trip + china_ship + pack;

    const vat = 1 + pct(inp.uzum_vat_pct || 0);
    const liters = uzumLiters(L, W, H);
    const logistics_estimated = liters === 0;
    const logistics = (logistics_estimated ? inp.logistics_fee : uzumLogistics(liters)) * vat;
    const fbo = inp.fbo === undefined ? 1 : inp.fbo;
    const storage = fbo ? storagePerUnit(liters, inp.sell_days || 0,
      inp.storage_free_days === undefined ? 30 : inp.storage_free_days, !!inp.storage_special) : 0;

    const s = inp.sell_price;
    const commission = s * pct(inp.commission_pct) * vat;
    const tax = s * pct(inp.tax_pct);
    const payout = Math.max(s - commission - logistics, 0) * pct(inp.payout_fee_pct || 0);
    const ads = s * pct(inp.ads_pct);
    const returns = s * pct(inp.returns_pct);
    const fees = commission + logistics + tax + payout + ads + returns + storage;

    const profit = s - landed - fees;
    const margin_pct = s ? profit / s * 100 : 0;
    const multiple = landed ? s / landed : 0;
    let verdict = "KIRMAYMIZ";
    if (margin_pct >= 15 && multiple >= 3) verdict = "KIRAMIZ";
    else if (margin_pct >= 8) verdict = "EHTIYOT";

    return {
      goods, buyer, cargo, trip, uzum_trip, china_ship, pack, actual_kg, volume_kg, charge_kg, cargo_by_m3,
      liters, landed, commission, logistics, logistics_estimated, tax, payout, ads, returns, storage, fees,
      profit, margin_pct, multiple,
      breakeven_price: priceForMargin(inp, landed, logistics, storage, 0),
      target_price: priceForMargin(inp, landed, logistics, storage, pct(inp.target_margin_pct)),
      batch_cost: landed * inp.qty,
      batch_profit: profit * inp.qty,
      roi_pct: landed ? profit / landed * 100 : 0,
      verdict,
    };
  }

  function parseNumber(text) {
    let t = String(text ?? "").trim().replace(/[\s ]/g, "").replace(/%/g, "");
    t = t.replace(/so'm|som|¥|\$/g, "");
    if ((t.match(/,/g) || []).length === 1 && !t.includes(".")) t = t.replace(",", ".");
    t = t.replace(/,/g, "");
    if (t === "") return NaN;
    const v = Number(t);
    return v < 0 ? NaN : v;
  }

  const api = { calculate, parseNumber, uzumLiters, uzumLogistics };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.UzCalc = api;
})(this);
