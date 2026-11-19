"""Uzum bozor tahlili: o'xshash tovarlar narxi, sotuvi, raqobati va bizning foydamiz.

Ma'lumot manbai hozircha — Uzum qidiruv natijalari skrinshotlari (Gemini o'qiydi). Manba
almashsa ham (API, qidiruv) shu modul o'zgarmaydi: unga `Listing` ro'yxati beriladi.
"""
from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass, replace
from html import escape
from typing import Any, Optional

from .calc import CalcInput, calculate, fmt

VERDICT_ICON = {"KIRAMIZ": "🟢", "EHTIYOT": "🟡", "KIRMAYMIZ": "🔴"}


@dataclass
class Listing:
    title: str
    price: float                 # hozirgi (chegirmali) narx, so'm
    old_price: float = 0         # chizilgan eski narx
    rating: float = 0
    reviews: int = 0             # izohlar/baholar soni
    orders: int = 0              # "N ta buyurtma" / "N+ sotildi"

    def key(self) -> tuple:
        return (re.sub(r"\W+", "", self.title.lower())[:40], round(self.price))


def _num(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).lower().replace(" ", " ")
    mult = 1000 if re.search(r"\d\s*(k|ming|тыс)", s) else 1
    s = re.sub(r"[^\d.,]", "", s).replace(",", ".")
    if s.count(".") > 1 or re.fullmatch(r"\d{1,3}(\.\d{3})+", s):   # 1.250.000 -> 1250000
        s = s.replace(".", "")
    try:
        return float(s) * mult if s else 0.0
    except ValueError:
        return 0.0


def parse_listings(text: str) -> list[Listing]:
    """Gemini javobidan JSON massivni ajratib oladi (```json ... ``` bo'lsa ham)."""
    m = re.search(r"\[.*\]", text or "", re.S)
    if not m:
        return []
    try:
        raw = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out = []
    for d in raw if isinstance(raw, list) else []:
        if not isinstance(d, dict):
            continue
        price = _num(d.get("price"))
        title = str(d.get("title") or "").strip()
        if price < 1000 or not title:          # so'mda 1000 dan arzon — o'qish xatosi
            continue
        out.append(Listing(title=title[:120], price=price, old_price=_num(d.get("old_price")),
                           rating=min(_num(d.get("rating")), 5.0), reviews=int(_num(d.get("reviews"))),
                           orders=int(_num(d.get("orders")))))
    return out


def merge(old: list[Listing], new: list[Listing]) -> list[Listing]:
    seen = {x.key() for x in old}
    return old + [x for x in new if x.key() not in seen and not seen.add(x.key())]


def to_dicts(items: list[Listing]) -> list[dict]:
    return [x.__dict__.copy() for x in items]


def from_dicts(items: list[dict]) -> list[Listing]:
    return [Listing(**d) for d in items or []]


@dataclass
class MarketSummary:
    count: int
    min: float
    p25: float
    median: float
    p75: float
    max: float
    top: list[Listing]            # eng ko'p sotilganlar
    top_price: float              # sotuv bo'yicha o'rtacha (vaznli) narx — bozor "haqiqiy" narxi
    total_orders: int
    avg_rating: float
    discounted_share: float       # chegirmadagilar ulushi, %


def _quantiles(prices: list[float]) -> tuple[float, float, float]:
    if len(prices) == 1:
        return prices[0], prices[0], prices[0]
    q = statistics.quantiles(prices, n=4, method="inclusive")
    return q[0], q[1], q[2]


def summarize(items: list[Listing]) -> Optional[MarketSummary]:
    if not items:
        return None
    prices = sorted(x.price for x in items)
    p25, med, p75 = _quantiles(prices)
    top = sorted(items, key=lambda x: (x.orders, x.reviews), reverse=True)[:3]
    total_orders = sum(x.orders for x in items)
    if total_orders:
        top_price = sum(x.price * x.orders for x in items) / total_orders
    else:
        top_price = med
    rated = [x.rating for x in items if x.rating > 0]
    disc = sum(1 for x in items if x.old_price > x.price) / len(items) * 100
    return MarketSummary(count=len(items), min=prices[0], p25=p25, median=med, p75=p75, max=prices[-1],
                         top=top, top_price=top_price, total_orders=total_orders,
                         avg_rating=sum(rated) / len(rated) if rated else 0.0, discounted_share=disc)


def profit_at(inp: CalcInput, price: float):
    return calculate(replace(inp, sell_price=price))


def competition_level(s: MarketSummary) -> str:
    big = sum(1 for x in s.top if x.orders >= 1000)
    if s.count >= 15 and big >= 2:
        return "🔴 yuqori — kuchli sotuvchilar bor, narx/rasm/izoh bilan ajralib turish kerak"
    if s.count >= 8 or big >= 1:
        return "🟡 o'rtacha"
    return "🟢 past — bo'sh joy bor (lekin talab ham kamroq bo'lishi mumkin)"


def report(items: list[Listing], name: str = "", inp: Optional[CalcInput] = None) -> str:
    s = summarize(items)
    if not s:
        return "Tahlil uchun tovar o'qilmadi."
    head = f"📊 <b>Uzum bozor tahlili</b>{(' — ' + escape(name)) if name else ''}\n"
    lines = [head,
             f"O'qilgan o'xshash tovarlar: <b>{s.count}</b> ta",
             f"Narx: {fmt(s.min)} – {fmt(s.max)} so'm",
             f"O'rtacha (mediana): <b>{fmt(s.median)}</b> · ko'pchilik {fmt(s.p25)}–{fmt(s.p75)}"]
    if s.total_orders:
        lines.append(f"Sotuv bo'yicha o'rtacha narx: <b>{fmt(s.top_price)}</b> so'm "
                     f"(jami ~{fmt(s.total_orders)} buyurtma)")
    if s.avg_rating:
        lines.append(f"O'rtacha reyting: {s.avg_rating:.1f}★ · chegirmada: {s.discounted_share:.0f}%")
    lines.append(f"Raqobat: {competition_level(s)}")

    if any(x.orders or x.reviews for x in s.top):
        lines.append("\n<b>Eng ko'p sotilganlar:</b>")
        for i, x in enumerate(s.top, 1):
            extra = []
            if x.orders:
                extra.append(f"{fmt(x.orders)} buyurtma")
            if x.rating:
                extra.append(f"{x.rating:.1f}★")
            if x.reviews:
                extra.append(f"{fmt(x.reviews)} izoh")
            lines.append(f"{i}. {escape(x.title[:60])} — <b>{fmt(x.price)}</b>"
                         + (f" ({', '.join(extra)})" if extra else ""))

    if inp is not None:
        lines.append("\n<b>Sizning tovaringiz shu narxlarda:</b>")
        r0 = calculate(inp)
        lines.append(f"Tannarx (1 dona, uygacha): {fmt(r0.landed)} so'm")
        points = [("eng arzon", s.min), ("arzonlar (25%)", s.p25), ("mediana", s.median)]
        if s.total_orders:
            points.append(("sotuv o'rtachasi", s.top_price))
        for label, price in points:
            r = profit_at(inp, price)
            lines.append(f"{VERDICT_ICON.get(r.verdict, '')} {label} {fmt(price)} → foyda "
                         f"<b>{fmt(r.profit)}</b> ({r.margin_pct:.0f}%)")
        be, tp = r0.breakeven_price, r0.target_price
        if be != float("inf"):
            lines.append(f"Zararsizlik narxi: {fmt(be)} · maqsadli marja narxi: "
                         f"{'—' if tp == float('inf') else fmt(tp)}")
        lines.append("\n<b>Xulosa:</b> " + advice(s, r0))
    else:
        lines.append("\n💡 Tovarni avval «🧮 Tannarx hisoblash»da saqlasangiz, shu narxlardagi "
                     "foydangizni ham ko'rsataman.")
    lines.append("\n<i>Ma'lumot skrinshotlardan o'qildi — muhim raqamlarni Uzum'da tekshiring.</i>")
    return "\n".join(lines)


def advice(s: MarketSummary, r0) -> str:
    tp, be = r0.target_price, r0.breakeven_price
    ref = s.top_price if s.total_orders else s.median
    if be == float("inf") or be > s.p75:
        return ("🔴 Bozor narxi sizning zararsizlik narxingizdan past. Arzonroq ta'minotchi, "
                "boshqa kargo yoki kattaroq partiya kerak — aks holda kirmaymiz.")
    if tp != float("inf") and tp <= s.p25:
        return (f"🟢 Kuchli: maqsadli marjaga {fmt(tp)} da ham chiqasiz — bu bozorning arzon qismi. "
                f"Narxni {fmt(min(ref, s.median))} atrofida qo'yib, raqobatda ustun bo'lish mumkin.")
    if tp != float("inf") and tp <= ref:
        return (f"🟢 Kirsa bo'ladi: tavsiya narx {fmt(tp)}–{fmt(ref)} so'm. "
                f"Rasm va kartochka sifati bilan eng ko'p sotilganlardan ajralib turing.")
    return (f"🟡 Ehtiyot: foyda bor, lekin maqsadli marja uchun {fmt(tp)} so'm kerak — bu bozor "
            f"o'rtachasidan ({fmt(ref)}) yuqori. Tannarxni kamaytirish yo'lini qidiring.")
