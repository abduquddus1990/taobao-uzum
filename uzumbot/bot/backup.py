"""Bazaning zaxira nusxasi: har kuni belgilangan soatda egaga Telegram orqali yuboriladi.

Kompyuter buzilsa yoki disk ishdan chiqsa ham, oxirgi nusxa Telegram chatida turadi.
Tiklash: faylni data/bot.db nomi bilan joyiga qo'yib, botni qayta ishga tushirish.
"""
import asyncio
import datetime as dt
import logging
import tempfile
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

from .service import TASHKENT

log = logging.getLogger(__name__)


async def send_backup(bot: Bot, db, chat_ids: list[int], caption: str = "Kunlik zaxira") -> None:
    stamp = dt.datetime.now(TASHKENT).strftime("%Y-%m-%d_%H%M")
    with tempfile.TemporaryDirectory() as tmp:
        dest = str(Path(tmp) / f"uzumbot_{stamp}.db")
        await asyncio.to_thread(db.backup_to, dest)
        for cid in chat_ids:
            try:
                await bot.send_document(cid, FSInputFile(dest), caption=f"💾 {caption} · {stamp}",
                                        disable_notification=True)
            except Exception as exc:
                log.warning("Zaxira yuborilmadi (%s): %s", cid, exc)


def _seconds_until(hour: int) -> float:
    now = dt.datetime.now(TASHKENT)
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += dt.timedelta(days=1)
    return (target - now).total_seconds()


async def backup_loop(bot: Bot, db, chat_ids: list[int], hour: int) -> None:
    if hour < 0 or hour > 23:
        log.info("BACKUP_HOUR noto'g'ri — kunlik zaxira o'chiq")
        return
    while True:
        await asyncio.sleep(_seconds_until(hour))
        await send_backup(bot, db, chat_ids)
        await asyncio.sleep(60)
