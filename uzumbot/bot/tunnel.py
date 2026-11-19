"""Cloudflare "quick tunnel": uy kompyuteridagi Mini App'ga bepul HTTPS manzil.

Akkaunt va domen kerak emas. `cloudflared tunnel --url http://127.0.0.1:PORT` ishga tushadi,
u https://xxxx.trycloudflare.com manzilini beradi. Manzil har ishga tushganda o'zgaradi —
shuning uchun bot uni har safar Telegram menyu tugmasiga o'zi yozib qo'yadi.
Jarayon to'xtab qolsa, qayta ishga tushiriladi va yangi manzil yana o'rnatiladi.
"""
import asyncio
import logging
import os
import re
import shutil
from typing import Awaitable, Callable, Optional

import aiohttp

log = logging.getLogger(__name__)

DNS_WARMUP_SECONDS = 8
WATCHDOG_SECONDS = 60          # manzilni har daqiqada tekshiramiz
WATCHDOG_FAILS = 3             # ketma-ket 3 marta ishlamasa — tunnel qayta yoqiladi
CONTROL_URL = "https://www.cloudflare.com/cdn-cgi/trace"   # internet borligini tekshirish
URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
WINDOWS_PATHS = (
    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
    r"C:\Program Files\cloudflared\cloudflared.exe",
)


def find_cloudflared() -> Optional[str]:
    path = os.getenv("CLOUDFLARED_PATH") or shutil.which("cloudflared")
    if path:
        return path
    for p in WINDOWS_PATHS:
        if os.path.exists(p):
            return p
    return None


class QuickTunnel:
    def __init__(self, port: int, on_url: Callable[[str], Awaitable[None]]):
        self.port = port
        self.on_url = on_url
        self.proc: Optional[asyncio.subprocess.Process] = None
        self.url: Optional[str] = None
        self._stopping = False

    async def _probe(self, session, url: str) -> bool:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                return r.status < 500
        except Exception:
            return False

    async def _watchdog(self) -> None:
        """Internet uzilib qaytganda Cloudflare quick-tunnel manzilini o'chirib yuboradi, cloudflared
        esa buni sezmay ishlab turaveradi. Manzil ishlamay qolsa (internet bor bo'lsa ham) —
        cloudflared qayta ishga tushiriladi va yangi manzil menyu tugmasiga yoziladi."""
        fails = 0
        async with aiohttp.ClientSession() as session:
            while True:
                await asyncio.sleep(WATCHDOG_SECONDS)
                if not self.url or not self.proc or self.proc.returncode is not None:
                    fails = 0
                    continue
                if await self._probe(session, self.url + "/"):
                    fails = 0
                    continue
                if not await self._probe(session, CONTROL_URL):
                    continue                     # internetning o'zi yo'q — kutamiz
                fails += 1
                log.warning("Mini App manzili javob bermayapti (%s/%s): %s", fails, WATCHDOG_FAILS, self.url)
                if fails >= WATCHDOG_FAILS:
                    fails = 0
                    log.warning("Tunnel qayta ishga tushirilmoqda")
                    try:
                        self.proc.kill()
                    except ProcessLookupError:
                        pass

    async def _run_once(self, exe: str) -> None:
        self.proc = await asyncio.create_subprocess_exec(
            exe, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{self.port}",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        )
        assert self.proc.stderr
        async for raw in self.proc.stderr:
            line = raw.decode("utf-8", "replace")
            if not self.url:
                m = URL_RE.search(line)
                if m:
                    self.url = m.group(0)
                    log.info("Mini App manzili: %s", self.url)
                    # Yangi subdomen DNS'da paydo bo'lishini kutamiz: juda erta so'ralsa,
                    # telefon/provayder "topilmadi" javobini keshlab qo'yadi.
                    await asyncio.sleep(DNS_WARMUP_SECONDS)
                    try:
                        await self.on_url(self.url)
                    except Exception:
                        log.exception("Manzilni o'rnatishda xato")
        await self.proc.wait()

    async def run_forever(self) -> None:
        exe = find_cloudflared()
        if not exe:
            log.warning("cloudflared topilmadi — Mini App o'chiq. README, 9-bo'limga qarang.")
            return
        delay = 5
        watchdog = asyncio.create_task(self._watchdog())
        try:
            while not self._stopping:
                self.url = None
                try:
                    await self._run_once(exe)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    log.exception("cloudflared xatosi")
                if self._stopping:
                    break
                delay = 5 if self.url else min(delay * 2, 300)   # ishlagan bo'lsa — tez qayta
                log.warning("cloudflared to'xtadi, %s s dan keyin qayta ishga tushadi", delay)
                await asyncio.sleep(delay)
        finally:
            watchdog.cancel()
            if self.proc and self.proc.returncode is None:
                self.proc.kill()

    async def stop(self) -> None:
        self._stopping = True
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), 10)
            except asyncio.TimeoutError:
                self.proc.kill()
