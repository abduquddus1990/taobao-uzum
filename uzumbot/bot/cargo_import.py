"""data_seed/cargos.json dan kargo tariflarini bazaga yuklash (/import_kargo, ilovadagi 📥 tugma).

Faylni o'zingiz tahrirlaysiz (narx o'zgarganda) — keyin qayta import qilasiz. Bir xil nomli
kargo ikki marta qo'shilmaydi, yangilanadi; siz qo'ygan reyting va qo'lda kiritilgan tarif saqlanadi.
"""
import json
from pathlib import Path
from typing import Any

SEED_FILE = Path(__file__).resolve().parent.parent / "data_seed" / "cargos.json"
GUIDE_FILE = Path(__file__).resolve().parent.parent / "docs" / "kargo_qollanma.md"


def load_seed(path: Path = SEED_FILE) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["cargos"]


def to_row(it: dict[str, Any], usd_rate: float) -> dict[str, Any]:
    tariff = it.get("tariff_usd_kg")
    if not tariff and it.get("tariff_uzs_kg"):
        tariff = round(float(it["tariff_uzs_kg"]) / usd_rate, 2)
    note = (it.get("note") or "").strip()
    if it.get("tariff_uzs_kg"):
        note = f"{int(it['tariff_uzs_kg']):,} so'm/kg. ".replace(",", " ") + note
    return {
        "name": str(it["name"])[:60], "mode": it.get("mode") if it.get("mode") in ("avia", "avto") else "avto",
        "tariff_usd_kg": float(tariff or 0), "days_min": it.get("days_min"), "days_max": it.get("days_max"),
        "white_docs": it.get("white_docs"), "olmaliq": it.get("olmaliq"), "note": note[:300] or None,
        "vol_divisor": it.get("vol_divisor"), "usd_m3": it.get("usd_m3"), "pickup_cost": None,
        "rating": 3, "verified": 0, "source": it.get("source_url"), "series_ok": it.get("series_ok"),
        "min_kg": it.get("min_kg"), "checked_at": it.get("checked_at"),
    }


async def import_cargos(db) -> list[tuple[str, str]]:
    """[(nomi, 'yangi' | 'yangilandi')]"""
    usd = (await db.get_settings())["usd_rate"]
    out = []
    for it in load_seed():
        row = to_row(it, usd)
        out.append((row["name"], await db.upsert_cargo(row)))
    return out


def guide_text(limit: int = 30000) -> str:
    try:
        return GUIDE_FILE.read_text(encoding="utf-8")[:limit]
    except OSError:
        return ""


def cargos_context(rows) -> str:
    """AI uchun kargolar ro'yxati (bitta qatordan)."""
    def yn(v):
        return "?" if v is None else ("ha" if v else "yo'q")
    out = []
    for c in rows:
        out.append(
            f"- {c['name']} ({c['mode']}): {c['tariff_usd_kg']:g} $/kg, muddat {c['days_min'] or '?'}–"
            f"{c['days_max'] or '?'} kun, Olmaliq: {yn(c['olmaliq'])}, oq hujjat: {yn(c['white_docs'])}, "
            f"partiya: {yn(c['series_ok'])}, min kg: {c['min_kg'] or '-'}, reyting {c['rating']}/5, "
            f"tasdiqlangan: {yn(c['verified'])}, tekshirilgan {c['checked_at'] or '?'}. {c['note'] or ''}")
    return "\n".join(out) or "(ro'yxat bo'sh)"
