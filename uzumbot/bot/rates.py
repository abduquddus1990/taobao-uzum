"""Markaziy bank (cbu.uz) kurslari: ¥ va $ har kuni avtomatik yangilanadi.

Bu RASMIY kurs. Haqiqatda yuan sotib olish (Alipay, bayer, karta) qimmatroq —
farqni «Konvertatsiya xarajati» (fx_spread_pct) sozlamasi qoplaydi, hisobda u alohida qo'shiladi.
O'chirish: Sozlamalar → «Kursni Markaziy bankdan...» = 0 (qo'lda kiritgan kursingiz saqlanadi).
"""
import asyncio
import datetime as dt
import logging
from typing import Optional

import aiohttp

from .service import TASHKENT

log = logging.getLogger(__name__)

CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
CODES = {"CNY": "cny_rate", "USD": "usd_rate"}
ALERT_PCT = 1.0          # kurs shundan ko'p o'zgarsa — xabar beramiz


def parse_cbu(payload) -> dict[str, float]:
    """cbu.uz JSON ro'yxatidan {"CNY": 1 ¥ so'mda, "USD": 1 $ so'mda} ni ajratadi."""
    out: dict[str, float] = {}
    for row in payload or []:
        code = str(row.get("Ccy", "")).upper()
        if code not in CODES:
            continue
        try:
            rate = float(str(row.get("Rate", "0")).replace(",", "."))
            nominal = float(row.get("Nominal") or 1)
        except ValueError:
            continue
        if rate > 0 and nominal > 0:
            out[code] = round(rate / nominal, 2)
    return out


async def fetch_cbu(session: Optional[aiohttp.ClientSession] = None, timeout: int = 20) -> dict[str, float]:
    own = session is None
    session = session or aiohttp.ClientSession()
    try:
        async with session.get(CBU_URL, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status != 200:
                raise RuntimeError(f"cbu.uz javobi: HTTP {resp.status}")
            data = parse_cbu(await resp.json(content_type=None))
    except aiohttp.ClientError as exc:
        raise RuntimeError(f"cbu.uz ga ulanib bo'lmadi: {exc}") from exc
    finally:
        if own:
            await session.close()
    if set(data) != set(CODES):
        raise RuntimeError("cbu.uz javobida USD yoki CNY topilmadi")
    return data


async def update_rates(db, fetch=None) -> list[tuple[str, float, float]]:
    """Kurslarni yangilaydi. Qaytaradi: [(kod, eski, yangi), ...] — faqat o'zgarganlari."""
    rates = await (fetch or fetch_cbu)()
    old = await db.get_settings()
    changed = []
    for code, key in CODES.items():
        new = rates[code]
        prev = float(old.get(key) or 0)
        if abs(new - prev) >= 0.01:
            await db.set_setting(key, new)
            changed.append((code, prev, new))
    return changed


def rates_text(changed: list[tuple[str, float, float]], settings: dict) -> str:
    sign = {"CNY": "¥", "USD": "$"}
    lines = ["💱 <b>Markaziy bank kursi</b>"]
    for code, key in CODES.items():
        lines.append(f"1 {sign[code]} = {settings.get(key, 0):,.2f} so'm".replace(",", " "))
    for code, prev, new in changed:
        if prev:
            pct = (new - prev) / prev * 100
            lines.append(f"{'📈' if pct > 0 else '📉'} {code}: {pct:+.2f}%")
    lines.append(f"<i>Haqiqiy xarid kursiga +{settings.get('fx_spread_pct', 0):g}% konvertatsiya qo'shiladi.</i>")
    return "\n".join(lines)


def _seconds_until(hour: int, minute: int) -> float:
    now = dt.datetime.now(TASHKENT)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += dt.timedelta(days=1)
    return (target - now).total_seconds()


async def rates_loop(bot, db, chat_ids: list[int], hour: int = 9, minute: int = 15) -> None:
    """Ishga tushganda va har kuni 09:15 da (MB kursi odatda ertalab e'lon qilinadi)."""
    first = True
    while True:
        if not first:
            await asyncio.sleep(_seconds_until(hour, minute))
        first = False
        settings = await db.get_settings()
        if not settings.get("auto_rates", 1):
            await asyncio.sleep(60)
            continue
        try:
            changed = await update_rates(db)
        except Exception as exc:
            log.warning("Kurs yangilanmadi: %s", exc)
            await asyncio.sleep(1800)          # 30 daqiqadan keyin qayta urinamiz
            first = True
            continue
        big = [c for c in changed if c[1] and abs(c[2] - c[1]) / c[1] * 100 >= ALERT_PCT]
        if big:
            text = rates_text(changed, await db.get_settings())
            for cid in chat_ids:
                try:
                    await bot.send_message(cid, text, disable_notification=True)
                except Exception as exc:
                    log.warning("Kurs xabari yuborilmadi (%s): %s", cid, exc)
        await asyncio.sleep(60)
