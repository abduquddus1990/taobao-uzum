"""🔗 Tezkor baho: Taobao/1688 linki + narx + vazn -> so'm/$ qiymati, kargo, xarajatlar, minimal narx.

Taobao'ni bot o'qimaydi (xarajat va bot-himoya) — narx va vaznni foydalanuvchi linkka qo'shib yozadi:
    https://item.taobao.com/item.htm?id=123 15 250
    https://m.tb.cn/h.xxx ¥15 250g 18x6x6 50ta #soyabon Mini zont
Sof funksiyalar — test qilish oson. Handler: bot/handlers/quote.py
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace
from html import escape
from typing import Any, Optional

from .calc import CalcInput, CalcResult, calculate, fmt
from .service import build_input, cargo_offers

DEFAULT_QTY = 20            # sinov partiyasi (qo'llanma: 15–20 dona)

LINK_RE = re.compile(
    r"https?://[^\s<>\"']*(?:taobao|tmall|1688|tb\.cn|yangkeduo|pinduoduo|alibaba)[^\s<>\"']*", re.I)
_NUM = r"(\d+(?:[.,]\d+)?)"
DIMS_RE = re.compile(_NUM + r"\s*[x×*хХ]\s*" + _NUM + r"\s*[x×*хХ]\s*" + _NUM + r"\s*(?:sm|cm|см)?", re.I)
PRICE_RE = re.compile(r"(?:¥|￥)\s*" + _NUM + r"|" + _NUM + r"\s*(?:¥|￥|yuan|yuan\b|юан\w*|元|cny)", re.I)
WEIGHT_RE = re.compile(_NUM + r"\s*(kg|кг|gr|гр|g|г)(?![a-zа-я'])", re.I)
QTY_RE = re.compile(r"(\d+)\s*(?:ta|dona|шт|pcs)(?![a-zа-я'])", re.I)
CAT_RE = re.compile(r"#([^\s#]+)")
CJK_RE = re.compile(r"[一-鿿]")
TITLE_CN_RE = re.compile(r"[「『【]([^」』】]{4,})[」』】]")
ITEM_ID_RE = re.compile(r"[?&]id=(\d+)")


def _f(s: str) -> float:
    return float(s.replace(",", "."))


@dataclass
class QuoteRequest:
    link: Optional[str] = None
    price_cny: Optional[float] = None
    weight_g: Optional[float] = None
    qty: Optional[int] = None
    dims: tuple[float, float, float] = (0, 0, 0)
    category_query: str = ""
    name: str = ""

    def missing(self) -> list[str]:
        out = []
        if not self.price_cny:
            out.append("narx (¥)")
        if not self.weight_g:
            out.append("vazn (g)")
        return out

    def merge(self, other: "QuoteRequest") -> "QuoteRequest":
        """Keyingi xabardagi ma'lumot bilan to'ldirish (yangi qiymat ustun)."""
        return QuoteRequest(
            link=other.link or self.link,
            price_cny=other.price_cny or self.price_cny,
            weight_g=other.weight_g or self.weight_g,
            qty=other.qty or self.qty,
            dims=other.dims if any(other.dims) else self.dims,
            category_query=other.category_query or self.category_query,
            name=other.name or self.name,
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "dims": list(self.dims)}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "QuoteRequest":
        d = dict(d or {})
        d["dims"] = tuple(d.get("dims") or (0, 0, 0))
        return cls(**d)


def parse_request(text: str) -> QuoteRequest:
    """Xabardan link, narx, vazn, o'lcham, partiya, toifa va nomni ajratadi.

    Birliksiz sonlar tartib bo'yicha: narx (¥), vazn (g), partiya (dona).
    Taobao ilovasining "ulashish" matnida (xitoycha) birliksiz sonlar olinmaydi — u yerda
    "7天无理由" kabi sonlar bor.
    """
    text = text or ""
    req = QuoteRequest()
    m = LINK_RE.search(text)
    if m:
        req.link = m.group(0).rstrip(".,;)」】")
        text = text.replace(m.group(0), " ")
    cn_title = TITLE_CN_RE.search(text)
    share_text = bool(CJK_RE.search(text))

    cats = CAT_RE.findall(text)
    if cats:
        req.category_query = " ".join(cats)
        text = CAT_RE.sub(" ", text)
    d = DIMS_RE.search(text)
    if d:
        req.dims = (_f(d.group(1)), _f(d.group(2)), _f(d.group(3)))
        text = text.replace(d.group(0), " ")
    p = PRICE_RE.search(text)
    if p:
        req.price_cny = _f(p.group(1) or p.group(2))
        text = text.replace(p.group(0), " ")
    w = WEIGHT_RE.search(text)
    if w:
        v = _f(w.group(1))
        req.weight_g = v * 1000 if w.group(2).lower() in ("kg", "кг") else v
        text = text.replace(w.group(0), " ")
    q = QTY_RE.search(text)
    if q:
        req.qty = int(q.group(1))
        text = text.replace(q.group(0), " ")

    if not share_text:
        nums = re.findall(r"(?<![\w.,])" + _NUM + r"(?![\w.,])", text)
        for raw in nums:
            v = _f(raw)
            if req.price_cny is None:
                req.price_cny = v
            elif req.weight_g is None:
                req.weight_g = v
            elif req.qty is None and v == int(v):
                req.qty = int(v)
        text = re.sub(r"(?<![\w.,])" + _NUM + r"(?![\w.,])", " ", text)
        words = re.findall(r"[A-Za-zА-Яа-яЁёЎўҚқҒғҲҳʻʼ'’`-]{2,}", text)
        req.name = " ".join(words)[:80].strip(" -'")
    elif cn_title:
        req.name = cn_title.group(1).strip()[:80]
    if not req.name:
        mid = ITEM_ID_RE.search(req.link or "")
        req.name = f"Taobao #{mid.group(1)}" if mid else "Taobao tovar"
    return req


def nice_price(x: float) -> float:
    """Psixologik narx: 58 743 -> 58 900; 58 950 -> 59 900. Har doim x dan kichik emas."""
    if x == float("inf") or x <= 0:
        return x
    p = math.ceil(x / 1000) * 1000 - 100
    return p if p >= x else p + 1000


@dataclass
class Quote:
    req: QuoteRequest
    inp: CalcInput                    # tavsiya narxdagi kiritma (saqlash uchun)
    result: CalcResult                # tavsiya narxdagi natija
    offer: Optional[dict]             # tanlangan (🏆) kargo taklifi
    offers: list[dict] = field(default_factory=list)
    category: Optional[dict] = None
    rec_price: float = 0.0
    notes: list[str] = field(default_factory=list)


def make_quote(settings: dict[str, float], req: QuoteRequest, cargos: list,
               category: Optional[dict] = None, scheme: str = "FBO") -> Quote:
    if req.missing():
        raise ValueError("Yetishmaydi: " + ", ".join(req.missing()))
    item = {"price_cny": req.price_cny, "weight_g": req.weight_g, "qty": req.qty or DEFAULT_QTY,
            "sell_price": 1.0, "length_cm": req.dims[0], "width_cm": req.dims[1], "height_cm": req.dims[2]}
    offers = cargo_offers(settings, item, cargos, category, scheme)
    ok = [o for o in offers if o["ok"]]
    notes = []
    if ok:
        best = ok[0]
        inp = build_input(settings, item, best["cargo"], category, scheme)
    else:
        best = None
        item["tariff_usd_kg"] = 0
        inp = build_input(settings, item, None, category, scheme)
        notes.append("Mos kargo topilmadi — kargo xarajatisiz hisoblandi. «🚚 Kargolar»da tarif kiriting.")
    base = calculate(inp)
    rec = nice_price(base.target_price)
    if rec == float("inf"):
        notes.append("Bu xarajatlar bilan maqsadli marjaga chiqib bo'lmaydi (foizlar yig'indisi juda katta).")
        rec = nice_price(base.breakeven_price) if base.breakeven_price != float("inf") else 0
    final_inp = replace(inp, sell_price=rec or 1.0)
    result = calculate(final_inp)
    if not category:
        notes.append(f"Toifa tanlanmagan — komissiya standart {inp.commission_pct:g}%. "
                     "Aniqroq bo'lishi uchun xabarga #toifa qo'shing (masalan, #soyabon).")
    if not any(req.dims):
        notes.append("O'lcham yo'q — Uzum logistikasi taxminiy, hajmiy vazn tekshirilmadi. "
                     "Qadog'i o'lchamini qo'shing: 18x6x6.")
    return Quote(req=req, inp=final_inp, result=result, offer=best, offers=offers,
                 category=category, rec_price=rec, notes=notes)


def _usd(x: float, usd_rate: float) -> str:
    return f"${x / usd_rate:,.2f}" if usd_rate else ""


def quote_report(q: Quote) -> str:
    inp, r, req = q.inp, q.result, q.req
    usd = inp.usd_rate
    head = f"🔗 <b>{escape(req.name)}</b>"
    if req.link:
        head = f'🔗 <a href="{escape(req.link, quote=True)}"><b>{escape(req.name)}</b></a>'
    cat = f"\n🏷 {escape(q.category['uz'].split(' › ')[-1])} — komissiya {inp.commission_pct:g}%" if q.category else ""
    lines = [
        head + cat,
        f"Partiya: <b>{inp.qty} dona</b>" + (" (seriya tarifi)" if inp.qty > 3 else ""),
        "",
        f"💴 <b>Narx:</b> ¥{inp.price_cny:g} = {_usd(inp.price_cny * inp.cny_rate, usd)} = "
        f"{fmt(inp.price_cny * inp.cny_rate)} so'm",
        f"   karta/konvertatsiya bilan: {fmt(r.goods)} so'm",
    ]
    ok = [o for o in q.offers if o["ok"]][:3]
    if ok:
        lines.append("\n🚚 <b>Kargo (1 donaga, olib kelish bilan):</b>")
        for o in ok:
            c = o["cargo"]
            mark = " ".join(b.split()[0] for b in o["badges"][:2]) or "•"
            days = f", ~{o['real_days']} kun" if o.get("real_days") else ""
            lines.append(f"{mark} {escape(c['name'])} ({c['mode']}) — {fmt(o['ship'])} so'm{days}")
    kg = (f"hajmiy {r.volume_kg:.2f} kg ⚠️" if r.volume_kg > r.actual_kg else f"{r.actual_kg * 1000:g} g")
    lines += [
        f"\n📦 <b>1 dona tannarx: {fmt(r.landed)} so'm</b> ({_usd(r.landed, usd)})",
        f"• Tovar: {fmt(r.goods)} · bayer {inp.buyer_pct:g}%: {fmt(r.buyer)}",
        f"• Kargo ({kg}): {fmt(r.cargo)}",
    ]
    extra = r.china_ship + r.pack + r.trip + r.uzum_trip
    if extra:
        lines.append(f"• Xitoy ichki + qadoq + qatnovlar: {fmt(extra)}")
    rec = q.rec_price
    lines += [
        f"\n🧾 <b>Uzum xarajatlari ({fmt(rec)} so'm narxda):</b>",
        f"• Komissiya {inp.commission_pct:g}%: {fmt(r.commission)} · logistika: {fmt(r.logistics)}"
        + (" (taxminiy)" if r.logistics_estimated else ""),
        f"• Reklama {inp.ads_pct:g}%: {fmt(r.ads)} · brak {inp.returns_pct:g}%: {fmt(r.returns)} · "
        f"soliq {inp.tax_pct:g}%: {fmt(r.tax)}" + (f" · saqlash: {fmt(r.storage)}" if r.storage else ""),
        "",
        "💰 <b>Narxlar:</b>",
        f"• Zararsizlik (0 foyda): {fmt(r.breakeven_price)} so'm",
        f"• Minimal narx ({inp.target_margin_pct:g}% marja): <b>{fmt(r.target_price)}</b> so'm",
        f"• ✅ Tavsiya narx: <b>{fmt(rec)} so'm</b> → foyda {fmt(r.profit)} ({r.margin_pct:.0f}%), "
        f"ROI {r.roi_pct:.0f}%",
        f"• 3x qoidasi (tannarx × 3): {fmt(r.landed * 3)} so'm",
        "",
        f"Partiyaga kerak: <b>{fmt(r.batch_cost)} so'm</b> ({_usd(r.batch_cost, usd)}) · "
        f"hammasi sotilsa foyda: {fmt(r.batch_profit)} so'm",
        f"\n{verdict_line(q)}",
    ]
    if q.notes:
        lines.append("\n<i>" + "\n".join("ℹ️ " + escape(n) for n in q.notes) + "</i>")
    return "\n".join(lines)


def verdict_line(q: Quote) -> str:
    r = q.result
    if r.multiple >= 3:
        return ("🟢 <b>Yaxshi nomzod.</b> Tannarx past — narx raqobatiga chidaydi. Keyingi qadam: "
                "Uzum'dagi raqobatchilar narxini tekshiring (📊).")
    if r.multiple >= 2.2:
        return ("🟡 <b>Ehtiyot.</b> Foyda bor, lekin tovarni chegirma va reklamasiz sotish kerak bo'ladi. "
                "Uzum narxi tavsiya narxdan yuqori bo'lsagina kiring.")
    return ("🔴 <b>Kuchsiz.</b> Tannarx sotuv narxiga nisbatan yuqori — kichik xato (brak, kurs, reklama) "
            "foydani yeydi. Arzonroq sotuvchi (1688) yoki boshqa tovar qidiring.")


HELP = (
    "🔗 <b>Tezkor baho</b>\n\n"
    "Taobao/1688 linkini narx va vazn bilan yuboring:\n"
    "<code>LINK 15 250</code> — ¥15, 250 g\n"
    "<code>LINK ¥15 250g 18x6x6 50ta #soyabon Mini zont</code>\n\n"
    "• o'lcham (sm, qadog'i bilan) — Uzum logistikasi va hajmiy vazn uchun\n"
    "• 50ta — partiya (yo'q bo'lsa 20)\n"
    "• #so'z — Uzum toifasi (komissiya uchun)\n"
    "• qolgan so'zlar — tovar nomi"
)
