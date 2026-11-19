"""Elektr/internet o'chganini bilish uchun tashqi "yurak urishi".

Bot har N soniyada healthchecks.io manziliga signal yuboradi. Signal kelmay qolsa,
healthchecks.io o'zi Telegramga xabar yuboradi (kompyuter o'chgan bo'lsa ham).
"""
import asyncio
import logging

import aiohttp

log = logging.getLogger(__name__)


async def heartbeat_loop(url: str, every_seconds: int) -> None:
    if not url:
        log.info("HEALTHCHECK_URL berilmagan — heartbeat o'chiq")
        return
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        log.warning("Heartbeat javobi: %s", resp.status)
            except Exception as exc:  # internet yo'q bo'lsa ham bot ishlashda davom etadi
                log.warning("Heartbeat yuborilmadi: %s", exc)
            await asyncio.sleep(every_seconds)
