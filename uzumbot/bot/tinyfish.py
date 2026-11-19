"""TinyFish Fetch: ochiq veb-sahifani (JS bilan) o'qib, matn qaytaradi. Bepul: kuniga 1000 URL.

Uzum qidiruv sahifasini o'qish uchun ishlatamiz: https://uzum.uz/uz/search?query=...
Kalit: https://agent.tinyfish.ai -> API key -> .env: TINYFISH_API_KEY=...
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional
from urllib.parse import quote_plus

import aiohttp

log = logging.getLogger(__name__)

FETCH_URL = "https://api.fetch.tinyfish.ai"
UZUM_SEARCH = "https://uzum.uz/uz/search?query={q}"
TEXT_KEYS = ("markdown", "content", "text", "html", "body")


def uzum_search_url(query: str) -> str:
    return UZUM_SEARCH.format(q=quote_plus((query or "").strip()))


def extract_text(payload: Any) -> str:
    """Javob tuzilmasi o'zgarsa ham ishlashi uchun: ichidan eng uzun matn maydonini topadi."""
    best = ""

    def walk(x: Any) -> None:
        nonlocal best
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str) and k.lower() in TEXT_KEYS and len(v) > len(best):
                    best = v
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(payload)
    return best


class TinyFishClient:
    def __init__(self, api_key: str, session: Optional[aiohttp.ClientSession] = None):
        self.api_key = (api_key or "").strip()
        self._session = session

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def fetch(self, url: str, timeout: int = 60) -> str:
        """Sahifa matnini qaytaradi. Xato bo'lsa RuntimeError (sababi bilan)."""
        if not self.enabled:
            raise RuntimeError("TINYFISH_API_KEY kiritilmagan")
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        body = {"urls": [url]}
        own = self._session is None
        session = self._session or aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout))
        try:
            async with session.post(FETCH_URL, headers=headers, json=body) as resp:
                raw = await resp.text()
                if resp.status == 401 or resp.status == 403:
                    raise RuntimeError("TinyFish kaliti noto'g'ri yoki faol emas")
                if resp.status == 429:
                    raise RuntimeError("TinyFish limiti tugadi (kuniga 1000 URL) — ertaga qayta urinib ko'ring")
                if resp.status >= 400:
                    raise RuntimeError(f"TinyFish xatosi HTTP {resp.status}: {raw[:200]}")
        except aiohttp.ClientError as exc:
            raise RuntimeError(f"TinyFish bilan aloqa yo'q: {exc}") from exc
        finally:
            if own:
                await session.close()
        try:
            text = extract_text(json.loads(raw))
        except json.JSONDecodeError:
            text = raw
        if len(text.strip()) < 200:
            raise RuntimeError("Sahifa bo'sh qaytdi (Uzum sahifani bermadi). Keyinroq urinib ko'ring "
                               "yoki /bozor orqali skrinshot yuboring.")
        return text
