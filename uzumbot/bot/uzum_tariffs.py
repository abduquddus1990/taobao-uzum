"""Uzum Market rasmiy tariflari: toifalar bo'yicha komissiya, logistika yig'imi, saqlash.

Manba — Uzum sotuvchi qo'llanmasi (seller.uzum.uz/manual/3.tariffs) havola qilgan rasmiy
Google jadval "Комиссионное вознаграждение". Bot uni haftada bir marta o'zi yangilaydi
(/tariflar buyrug'i bilan qo'lda ham). Yuklab bo'lmasa — oxirgi saqlangan nusxa ishlatiladi.

Logistika va saqlash tariflari (01.06.2026 dan):
  * Hajm, litr = U(mm)×E(mm)×B(mm) / 1 000 000, BUTUNGA YUQORIGA yaxlitlanadi.
  * Logistika: 1 litrgacha 5 250 so'm, har qo'shimcha litr +250 so'm, maksimum 50 000 so'm.
    O'lcham kiritilmagan tovar — 50 000 so'm. Faqat sotilgan donadan olinadi, qaytsa qaytariladi.
  * Saqlash (faqat FBO): aylanma 0–60 kun bepul; 61–180: 12; 181–360: 18 (maxsus 14);
    361+: 24 (maxsus 18) so'm/litr/kun; maksimum 5 000 (maxsus 3 000) so'm/dona/kun.
    Yangi stok 30 kun bepul (ba'zi toifalar 60 kun).
  * Ekvayring komissiya ICHIDA — alohida hisoblanmaydi.
"""
import asyncio
import csv
import datetime as dt
import io
import json
import logging
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

SHEET_ID = "1J9EQEJqZcF3eRS4nLLAjR0M8jcb0QabZGFpfIP_mpRU"
GID_COMM_RU = "1248630206"
GID_COMM_UZ = "298331907"
GID_FREE60_RU = "243870179"
SOURCE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
MANUAL_URL = "https://seller.uzum.uz/manual/3.tariffs/"
DATA_FILE = Path(__file__).resolve().parent / "uzum_data" / "uzum_tariffs.json"

# Logistika va saqlash (seller.uzum.uz/manual, 01.06.2026)
LOGISTICS_BASE = 5250
LOGISTICS_PER_LITER = 250
LOGISTICS_MAX = 50000
LOGISTICS_NO_DIMS = 50000
STORAGE_STANDARD = ((60, 0), (180, 12), (360, 18), (10**9, 24))
STORAGE_SPECIAL = ((60, 0), (180, 12), (360, 14), (10**9, 18))
STORAGE_MAX_STANDARD = 5000
STORAGE_MAX_SPECIAL = 3000
FREE_DAYS_DEFAULT = 30

# Maxsus saqlash tarifi qo'llanadigan toifalar (qo'llanma, 1-ilova): 1-daraja -> 2-daraja (bo'sh = hammasi)
SPECIAL_STORAGE = {
    "Аксессуары": (),
    "Обувь": (),
    "Одежда": (),
    "Автотовары": ("Аксессуары и принадлежности",),
    "Строительство и ремонт": ("Отделочные материалы",),
    "Товары для дома": ("Текстиль", "Товары для кухни"),
    "Электроника": ("Аксессуары для электроники",),
}


def _pct(v: str) -> Optional[float]:
    v = (v or "").strip().replace("%", "").replace(",", ".").replace(" ", "")
    if not v or v == "-":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _path(row: list[str], a: int = 2, b: int = 8) -> list[str]:
    return [c.strip() for c in row[a:b] if c and c.strip()]


def parse(comm_ru: str, comm_uz: str, free60_ru: str) -> dict[str, Any]:
    """Jadval CSV'laridan ixcham ma'lumot: [{id, uz, ru, fbo, fbs, dbs, disc, special, free}]"""
    free60 = set()
    for r in list(csv.reader(io.StringIO(free60_ru)))[3:]:
        if len(r) >= 3 and r[0].strip() and r[2].strip().isdigit() and int(r[2]) >= 60:
            free60.add((r[0].strip(), r[1].strip()))
    uz_rows = {}
    for r in csv.reader(io.StringIO(comm_uz)):
        if r and r[0].strip().isdigit():
            uz_rows[r[0].strip()] = _path(r)
    cats = []
    for r in csv.reader(io.StringIO(comm_ru)):
        if len(r) < 17 or not r[0].strip().isdigit():
            continue
        ru = _path(r)
        if not ru:
            continue
        l1, l2 = ru[0], ru[1] if len(ru) > 1 else ""
        special_l2 = SPECIAL_STORAGE.get(l1)
        special = special_l2 is not None and (not special_l2 or l2 in special_l2)
        cats.append({
            "id": int(r[0]),
            "ru": " › ".join(ru),
            "uz": " › ".join(uz_rows.get(r[0].strip(), ru)),
            "fbo": _pct(r[14]), "fbs": _pct(r[15]), "dbs": _pct(r[16]),
            "disc": any((_pct(x) or 0) > 0 for x in r[11:14]),
            "special": special,
            "free": 60 if (l1, l2) in free60 else FREE_DAYS_DEFAULT,
        })
    return {"categories": cats}


_APOS = str.maketrans({"ʻ": "'", "ʼ": "'", "’": "'", "‘": "'", "`": "'", "ё": "е"})


def norm(text: str) -> str:
    return (text or "").lower().translate(_APOS)


class Tariffs:
    def __init__(self, path: Path = DATA_FILE):
        self.path = path
        self.data: dict[str, Any] = {"categories": [], "fetched_at": None}
        self.by_id: dict[int, dict] = {}

    def load(self) -> None:
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        self.by_id = {c["id"]: c for c in self.data.get("categories", [])}
        log.info("Uzum tariflari: %s toifa (%s)", len(self.by_id), self.data.get("fetched_at"))

    def get(self, cid: Optional[int]) -> Optional[dict]:
        return self.by_id.get(int(cid)) if cid else None

    def search(self, q: str, limit: int = 30) -> list[dict]:
        words = [w for w in norm(q).split() if w]
        if not words:
            return []
        out = []
        for c in self.data.get("categories", []):
            hay = norm(c["uz"] + " " + c["ru"])
            if all(w in hay for w in words):
                # aniqroq (chuqurroq) toifa va nomning oxiriga mos kelganlar oldinda
                leaf = norm(c["uz"].split(" › ")[-1] + " " + c["ru"].split(" › ")[-1])
                out.append((0 if any(w in leaf for w in words) else 1, len(c["uz"]), c))
        out.sort(key=lambda t: (t[0], t[1]))
        return [c for _, _, c in out[:limit]]

    @property
    def fetched_at(self) -> Optional[str]:
        return self.data.get("fetched_at")

    async def refresh(self, session=None) -> tuple[bool, str, list[tuple[dict, dict]]]:
        """Rasmiy jadvalni yuklab, faylga yozadi. (ok, xabar, o'zgargan toifalar[(eski, yangi)])"""
        import aiohttp
        own = session is None
        session = session or aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))
        try:
            async def get(gid: str) -> str:
                url = f"{SOURCE_URL}/export?format=csv&gid={gid}"
                async with session.get(url) as r:
                    if r.status != 200:
                        raise RuntimeError(f"HTTP {r.status}")
                    return await r.text(encoding="utf-8")
            ru, uz, free = await asyncio.gather(get(GID_COMM_RU), get(GID_COMM_UZ), get(GID_FREE60_RU))
        except Exception as exc:
            return False, f"Yuklab bo'lmadi: {exc}", []
        finally:
            if own:
                await session.close()
        new = parse(ru, uz, free)
        if len(new["categories"]) < 1000:
            return False, f"Jadval kutilganidan kichik ({len(new['categories'])} qator) — eski nusxa qoldi", []
        changed = []
        for c in new["categories"]:
            old = self.by_id.get(c["id"])
            if old and (old["fbo"], old["fbs"]) != (c["fbo"], c["fbs"]):
                changed.append((old, c))
        new["fetched_at"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        new["source"] = SOURCE_URL
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(new, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        self.data = new
        self.by_id = {c["id"]: c for c in new["categories"]}
        return True, f"{len(new['categories'])} toifa yangilandi, {len(changed)} tasida komissiya o'zgargan", changed


TARIFFS = Tariffs()


async def refresh_loop(bot, db, chat_ids: list[int], every_hours: int = 24 * 7) -> None:
    """Haftada bir marta rasmiy jadvalni yangilaydi; saqlangan tovarlar toifasida komissiya
    o'zgarsa, adminlarga xabar beradi."""
    await asyncio.sleep(60)
    while True:
        ok, msg, changed = await TARIFFS.refresh()
        log.info("Tariflar: %s", msg)
        if ok and changed:
            await notify_changes(bot, db, chat_ids, changed)
        await asyncio.sleep(every_hours * 3600)


async def notify_changes(bot, db, chat_ids: list[int], changed: list[tuple[dict, dict]]) -> None:
    by_id = {new["id"]: (old, new) for old, new in changed}
    lines = []
    for p in await db.list_products(limit=1000):
        cid = p["category_id"]
        if cid in by_id:
            old, new = by_id[cid]
            lines.append(f"• {p['name']}: {old['fbo']}% → {new['fbo']}%")
    if not lines:
        return
    text = ("📢 <b>Uzum komissiyasi o'zgardi</b> — tovarlaringiz toifasida:\n" + "\n".join(lines[:30])
            + "\n\nIlovada tovarni ochsangiz, bugungi foyda yangi komissiya bilan ko'rinadi.")
    for cid in chat_ids:
        try:
            await bot.send_message(cid, text)
        except Exception as exc:
            log.warning("Xabar yuborilmadi: %s", exc)
