"""Chat va Mini App uchun umumiy mantiq: sozlamadan hisob kiritmasi, tovar/kargo ko'rinishi, statistika."""
import datetime as dt
import json
from dataclasses import asdict
from typing import Any, Optional

from .calc import CalcInput, calculate, input_from_dict
from .db import CAPITAL_STATUSES, RATE_FIELDS, STATUSES

TASHKENT = dt.timezone(dt.timedelta(hours=5))

# Tovarga xos (foydalanuvchi kiritadigan) maydonlar
ITEM_FIELDS = ("price_cny", "weight_g", "qty", "tariff_usd_kg", "sell_price", "commission_pct",
               "china_ship_cny", "length_cm", "width_cm", "height_cm", "sell_days")


def _get(row, key, default=None):
    """sqlite Row yoki dict'dan xavfsiz o'qish."""
    if row is None:
        return default
    try:
        v = row[key]
    except (KeyError, IndexError):
        return default
    return default if v is None else v


def scheme_commission(category: Optional[dict], scheme: str) -> Optional[float]:
    if not category:
        return None
    return category.get("fbs" if scheme == "FBS" else "fbo")


def build_input(settings: dict[str, float], item: dict[str, Any], cargo=None,
                category: Optional[dict] = None, scheme: str = "FBO") -> CalcInput:
    """Sozlamalar + kargo + Uzum toifasi + tovar maydonlari -> CalcInput.

    Ustunlik tartibi: foydalanuvchi kiritgani > kargo/toifa ma'lumoti > sozlamadagi standart.
    webapp/app.js dagi buildInput() aynan shu tartibda ishlaydi.
    """
    data: dict[str, Any] = {k: settings[k] for k in RATE_FIELDS if k in settings}
    data["commission_pct"] = settings.get("commission_pct", 25)
    cat_comm = scheme_commission(category, scheme)
    if cat_comm is not None:
        data["commission_pct"] = cat_comm
    data["china_ship_cny"] = settings.get("china_ship_cny", 0)
    data["sell_days"] = settings.get("sell_days", 0)
    data["vol_divisor"] = settings.get("vol_divisor", 6000)
    data["trip_cost"] = settings.get("trip_cost", 0)
    if cargo is not None:
        data["tariff_usd_kg"] = float(cargo["tariff_usd_kg"])
        data["cargo_usd_m3"] = float(_get(cargo, "usd_m3", 0) or 0)
        if _get(cargo, "vol_divisor"):
            data["vol_divisor"] = float(cargo["vol_divisor"])
        if _get(cargo, "pickup_cost") is not None:
            data["trip_cost"] = float(cargo["pickup_cost"])
        elif _get(cargo, "olmaliq", 0):
            data["trip_cost"] = settings.get("olmaliq_pickup_cost", data["trip_cost"])
    data["fbo"] = 0 if scheme == "FBS" else 1
    if category:
        data["storage_special"] = 1 if category.get("special") else 0
        data["storage_free_days"] = float(category.get("free", 30))
    for k in ITEM_FIELDS:
        v = item.get(k)
        if v is None or v == "":
            continue
        if k == "tariff_usd_kg" and cargo is not None:
            continue   # kargo tanlangan bo'lsa, uning tarifi
        data[k] = float(v)
    data["qty"] = int(data.get("qty", 0))
    for k in ("price_cny", "weight_g", "tariff_usd_kg", "sell_price"):
        if k not in data:
            raise ValueError(f"{k} kiritilmagan")
        if data[k] < 0:
            raise ValueError(f"{k} manfiy bo'lmaydi")
    if data["qty"] < 1:
        raise ValueError("Partiyada kamida 1 dona bo'lsin")
    if data["sell_price"] <= 0:
        raise ValueError("Sotuv narxi 0 dan katta bo'lishi kerak")
    if not 0 <= data["commission_pct"] < 100:
        raise ValueError("Komissiya 0–99% oralig'ida bo'lsin")
    return CalcInput(**data)


SERIES_QTY = 3          # qo'llanma: 3 donadan ko'p bir xil tovar — "seriya/tijorat"
DAYS_BUFFER = 4         # qo'llanma: e'lon qilingan muddatning yuqori chegarasi + 3–5 kun
OFFER_WEIGHTS = {"price": 0.50, "speed": 0.20, "quality": 0.15, "docs": 0.10, "olmaliq": 0.05}


def cargo_eligibility(cargo, qty: int, batch_kg: float) -> Optional[str]:
    """Kargo shu partiyaga mos kelmasa — sababi, mos kelsa None."""
    if float(_get(cargo, "tariff_usd_kg", 0) or 0) <= 0:
        return "tarif kiritilmagan"
    if qty > SERIES_QTY and _get(cargo, "series_ok") == 0:
        return "seriya (partiya) olinmaydi — faqat namuna uchun"
    min_kg = _get(cargo, "min_kg")
    if min_kg and batch_kg < float(min_kg):
        return f"minimal {float(min_kg):g} kg (partiya {batch_kg:.1f} kg)"
    return None


def cargo_offers(settings: dict[str, float], item: dict[str, Any], cargos: list,
                 category: Optional[dict] = None, scheme: str = "FBO") -> list[dict[str, Any]]:
    """Har bir kargo bilan shu tovarni hisoblab, taklif ro'yxati: mos kelganlar (ball bo'yicha), keyin mos emaslar.

    Ball = 50% narx (kargo + olib kelish, 1 donaga) + 20% tezlik + 15% sifat (reyting)
           + 10% "oq" hujjat + 5% Olmaliq punkti.
    webapp/app.js dagi cargoOffers() bilan bir xil.
    """
    rows, bad = [], []
    for c in cargos:
        try:
            inp = build_input(settings, item, c, category, scheme)
            r = calculate(inp)
        except (ValueError, KeyError):
            continue
        reason = cargo_eligibility(c, inp.qty, r.charge_kg * inp.qty)
        x = {"cargo": c, "result": r, "ship": r.cargo + r.trip, "ok": reason is None, "reason": reason,
             "badges": [], "score": 0, "days": _get(c, "days_max") or _get(c, "days_min")}
        x["real_days"] = x["days"] + DAYS_BUFFER if x["days"] else None
        (rows if x["ok"] else bad).append(x)
    if rows:
        w = OFFER_WEIGHTS
        cheapest = min(x["ship"] for x in rows)
        fastest = min((x["days"] or 999) for x in rows)
        for x in rows:
            c = x["cargo"]
            docs = _get(c, "white_docs")
            parts = {
                "price": (cheapest / x["ship"]) if x["ship"] > 0 else 1,
                "speed": (fastest / x["days"]) if x["days"] else 0.5,
                "quality": int(_get(c, "rating", 3)) / 5,
                "docs": 1.0 if docs == 1 else 0.5 if docs is None else 0.0,
                "olmaliq": 1.0 if _get(c, "olmaliq", 0) else 0.0,
            }
            x["score"] = round(100 * sum(w[k] * parts[k] for k in w))
        rows.sort(key=lambda x: (-x["score"], x["ship"]))
        best_price = min(rows, key=lambda x: x["ship"])
        best_speed = min(rows, key=lambda x: x["days"] or 999)
        best_q = max(rows, key=lambda x: int(_get(x["cargo"], "rating", 3)))
        for i, x in enumerate(rows):
            b = x["badges"]
            if i == 0:
                b.append("🏆 Tavsiya")
            if x is best_price:
                b.append("💰 Eng arzon")
            if x is best_speed and x["days"]:
                b.append("⚡ Eng tez")
            if x is best_q and int(_get(x["cargo"], "rating", 3)) >= 4:   # faqat o'zingiz baholagan
                b.append("⭐ Ishonchli")
            if _get(x["cargo"], "white_docs") == 1:
                b.append("📄 Oq hujjat")
            if _get(x["cargo"], "olmaliq", 0):
                b.append("📍 Olmaliq")
    bad.sort(key=lambda x: x["ship"])
    return rows + bad


def local_time(ts: Optional[str]) -> str:
    """SQLite UTC vaqtini Toshkent vaqtiga: '2026-11-18 04:00:00' -> '18.11.2026 09:00'"""
    if not ts:
        return ""
    try:
        t = dt.datetime.fromisoformat(ts).replace(tzinfo=dt.timezone.utc).astimezone(TASHKENT)
        return t.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return ts


def rebase(inp: CalcInput, settings: dict[str, float]) -> CalcInput:
    """Saqlangan hisobni bugungi kurs va foizlar bilan qayta qurish (tovar maydonlari saqlanadi)."""
    d = asdict(inp)
    for k in RATE_FIELDS:
        if k in settings:
            d[k] = settings[k]
    return CalcInput(**d)


def result_dict(inp: CalcInput) -> dict[str, Any]:
    r = asdict(calculate(inp))
    for k in ("breakeven_price", "target_price"):
        if r[k] == float("inf"):
            r[k] = None
    return r


def cargo_dict(c) -> dict[str, Any]:
    return {k: c[k] for k in c.keys()}


def product_dict(row, settings: Optional[dict[str, float]] = None,
                 names: Optional[dict[int, str]] = None, cargo_name: str = "",
                 category: Optional[dict] = None) -> dict[str, Any]:
    inp = input_from_dict(json.loads(row["input_json"]))
    out = {
        "id": row["id"],
        "name": row["name"],
        "source_link": row["source_link"],
        "cargo_id": row["cargo_id"],
        "cargo_name": cargo_name,
        "status": row["status"] or "idea",
        "status_label": STATUSES.get(row["status"] or "idea", ""),
        "note": row["note"],
        "category_id": _get(row, "category_id"),
        "category": category["uz"] if category else None,
        "category_obj": category,
        "scheme": _get(row, "scheme", "FBO"),
        "created_by": row["created_by"],
        "created_by_name": (names or {}).get(row["created_by"], ""),
        "created_at": local_time(row["created_at"]),
        "input": asdict(inp),
        "result": result_dict(inp),
    }
    if settings is not None:
        out["today"] = result_dict(rebase(inp, settings))
    return out


def stats(products: list[dict[str, Any]], settings: dict[str, float]) -> dict[str, Any]:
    by_verdict = {"KIRAMIZ": 0, "EHTIYOT": 0, "KIRMAYMIZ": 0}
    by_status = {k: 0 for k in STATUSES}
    capital = 0.0
    expected = 0.0
    margins = []
    for p in products:
        r = p.get("today") or p["result"]
        by_verdict[r["verdict"]] = by_verdict.get(r["verdict"], 0) + 1
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1
        if p["status"] in CAPITAL_STATUSES:
            capital += r["batch_cost"]
            expected += r["batch_profit"]
        if p["status"] != "stopped":
            margins.append(r["margin_pct"])
    usd = settings.get("usd_rate") or 1
    budget = settings.get("budget_usd", 1000)
    return {
        "count": len(products),
        "by_verdict": by_verdict,
        "by_status": by_status,
        "capital_sum": capital,
        "capital_usd": capital / usd,
        "budget_usd": budget,
        "budget_used_pct": (capital / usd / budget * 100) if budget else 0,
        "expected_profit": expected,
        "avg_margin": (sum(margins) / len(margins)) if margins else 0,
    }
