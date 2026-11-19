from html import escape
from typing import Optional

from .calc import CalcInput, CalcResult, fmt

VERDICT_ICON = {"KIRAMIZ": "🟢", "EHTIYOT": "🟡", "KIRMAYMIZ": "🔴"}


def link_line(label: str, url: Optional[str]) -> str:
    if url and url.startswith("http"):
        return f'🔗 <a href="{escape(url, quote=True)}">{escape(label)}</a>'
    return f"🔗 {escape(label)}: kiritilmagan"


def _opt(label: str, value: float, minus: bool = False) -> str:
    return f"• {label}: {'−' if minus else ''}{fmt(value)}\n" if value else ""


def _kg_line(r: CalcResult) -> str:
    if r.cargo_by_m3:
        return "⚠️ kub metr bo'yicha"
    if r.volume_kg > r.actual_kg:
        return f"⚠️ hajmiy {r.volume_kg:.2f} kg > haqiqiy {r.actual_kg:.2f} kg"
    return f"{r.actual_kg * 1000:g} g"


def calc_report(name: str, link: Optional[str], cargo_name: str, inp: CalcInput, r: CalcResult,
                category: Optional[str] = None) -> str:
    icon = VERDICT_ICON.get(r.verdict, "")
    scheme = "FBO (Uzum ombori)" if inp.fbo else "FBS (o'z omborimiz)"
    logi = (f"• Logistika yig'imi ({r.liters} l): −{fmt(r.logistics)}\n" if not r.logistics_estimated
            else f"• Logistika yig'imi (⚠️ o'lcham yo'q, taxminiy): −{fmt(r.logistics)}\n")
    vat = f" + QQS {inp.uzum_vat_pct:g}%" if inp.uzum_vat_pct else ""
    cat = f"🏷 Toifa: {escape(category)}\n" if category else ""
    return (
        f"<b>{escape(name)}</b>\n"
        f"{link_line('Manba (Taobao/1688)', link)}\n"
        f"🚚 Kargo: {escape(cargo_name)} · {inp.tariff_usd_kg:g} $/kg\n"
        f"{cat}📦 Sxema: {scheme}\n\n"
        f"<b>1 dona tannarx: {fmt(r.landed)} so'm</b>\n"
        f"• Tovar ({inp.price_cny:g} ¥ + konvertatsiya {inp.fx_spread_pct:g}%): {fmt(r.goods)}\n"
        f"• Bayer xizmati ({inp.buyer_pct:g}%): {fmt(r.buyer)}\n"
        f"• Kargo ({_kg_line(r)}): {fmt(r.cargo)}\n"
        f"{_opt('Xitoy ichki yetkazish ulushi', r.china_ship)}"
        f"{_opt('Qadoq va shtrix-kod', r.pack)}"
        f"{_opt(f'Kargodan olib kelish ({inp.qty} dona)', r.trip)}"
        f"{_opt('Uzum omboriga topshirish', r.uzum_trip)}\n"
        f"<b>Sotuv: {fmt(inp.sell_price)} so'm</b>\n"
        f"• Uzum komissiyasi ({inp.commission_pct:g}%{vat}, ekvayring ichida): −{fmt(r.commission)}\n"
        f"{logi}"
        f"{_opt('FBO saqlash (taxminiy)', r.storage, True)}"
        f"• Aylanma solig'i ({inp.tax_pct:g}%): −{fmt(r.tax)}\n"
        f"{_opt(f'Pul yechish xizmati ({inp.payout_fee_pct:g}%)', r.payout, True)}"
        f"• Reklama ({inp.ads_pct:g}%): −{fmt(r.ads)}\n"
        f"• Brak/qaytarish ({inp.returns_pct:g}%): −{fmt(r.returns)}\n\n"
        f"<b>Sof foyda: {fmt(r.profit)} so'm ({r.margin_pct:.1f}%)</b>\n"
        f"Sotuv / tannarx: {r.multiple:.2f}x (maqsad ≥ 3x)\n"
        f"Zararsizlik narxi: {fmt(r.breakeven_price)} so'm\n"
        f"{inp.target_margin_pct:g}% marja uchun narx: {fmt(r.target_price)} so'm\n\n"
        f"Qo'yilgan pulga foyda (1 aylanish): {r.roi_pct:.0f}%\n"
        f"Partiya ({inp.qty} dona): pul kerak {fmt(r.batch_cost)} so'm, "
        f"hammasi sotilsa foyda {fmt(r.batch_profit)} so'm\n\n"
        f"{icon} <b>Xulosa: {r.verdict}</b>"
    )


def offers_report(offers: list, limit: int = 6) -> str:
    """Kargo takliflari: har biri bilan tovar tannarxi va foydasi."""
    if not offers:
        return ""
    ok = [x for x in offers if x["ok"]]
    bad = [x for x in offers if not x["ok"]]
    lines = ["<b>🚚 Kargo takliflari</b> (shu partiya uchun)"]
    for x in ok[:limit]:
        c, r = x["cargo"], x["result"]
        days = f"{c['days_min'] or '?'}–{c['days_max']} kun (real ~{x['real_days']})" if x["days"] else "muddat ?"
        unver = " ❔" if not c["verified"] else ""
        lines.append(
            f"{' '.join(x['badges'])} · ball {x['score']}\n"
            f"  <b>{escape(c['name'])}</b> ({c['mode']}){unver} · {days} · {'★' * int(c['rating'])}\n"
            f"  kargo+olib kelish {fmt(x['ship'])} · tannarx {fmt(r.landed)} · foyda "
            f"{fmt(r.profit)} so'm {VERDICT_ICON.get(r.verdict, '')}")
    if not ok:
        lines.append("Mos kargo topilmadi — tarifni qo'lda yozing.")
    if bad:
        lines.append("\n<b>Mos emas:</b>")
        lines += [f"  ✖️ {escape(x['cargo']['name'])} — {escape(x['reason'])}" for x in bad[:8]]
    lines.append("\nBall: narx 50% · tezlik 20% · sifat 15% · oq hujjat 10% · Olmaliq 5%. "
                 "❔ — narx saytdan, qo'ng'iroq qilib tasdiqlang.")
    return "\n".join(lines)


def split_text(text: str, limit: int = 4000) -> list[str]:
    parts, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > limit:
            parts.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        parts.append(cur)
    return parts or [""]
