"""SQLite baza: sozlamalar, foydalanuvchilar, kargolar, tovar hisoblari."""
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

import aiosqlite

# Botda o'zgartiriladigan sozlamalar: kalit -> (nomi, standart qiymat, birligi)
SETTINGS: dict[str, tuple[str, float, str]] = {
    "cny_rate": ("Yuan kursi (1 ¥)", 1750, "so'm"),
    "usd_rate": ("Dollar kursi (1 $)", 12500, "so'm"),
    "fx_spread_pct": ("Konvertatsiya xarajati", 3, "%"),
    "buyer_pct": ("Bayer xizmati", 10, "%"),
    "china_ship_cny": ("Xitoy ichki yetkazish (partiyaga)", 15, "¥"),
    "vol_divisor": ("Kargo hajmiy vazn bo'luvchisi", 6000, "sm³/kg"),
    "trip_cost": ("Toshkent kargosidan olib kelish (Uzum safariga qo'shilsa 0)", 0, "so'm/qatnov"),
    "olmaliq_pickup_cost": ("Olmaliq punktidan olib kelish", 0, "so'm/qatnov"),
    "uzum_trip_cost": ("Uzum omboriga topshirish", 200000, "so'm/qatnov"),
    "pack_cost": ("Qadoq va shtrix-kod", 1500, "so'm/dona"),
    "commission_pct": ("Komissiya (toifa tanlanmasa)", 25, "%"),
    "logistics_fee": ("Logistika (o'lcham kiritilmasa)", 5250, "so'm/dona"),
    "uzum_vat_pct": ("Uzum xizmatlariga QQS ustama", 0, "%"),
    "payout_fee_pct": ("Pul yechish xizmati", 0, "%"),
    "tax_pct": ("Aylanma solig'i", 1, "%"),
    "ads_pct": ("Reklama", 10, "%"),
    "returns_pct": ("Brak va qaytarish", 5, "%"),
    "sell_days": ("Partiya sotilish muddati (taxmin)", 45, "kun"),
    "target_margin_pct": ("Maqsadli sof marja", 20, "%"),
    "budget_usd": ("Boshlang'ich byudjet", 1000, "$"),
}

# Sozlamadan to'g'ridan-to'g'ri CalcInput'ga o'tadigan maydonlar.
# Tovarga/kargoga xos maydonlar (commission_pct, china_ship_cny, trip_cost, vol_divisor,
# sell_days) uchun sozlama faqat standart qiymat beradi.
RATE_FIELDS = (
    "cny_rate", "usd_rate", "fx_spread_pct", "buyer_pct", "pack_cost", "logistics_fee", "tax_pct",
    "payout_fee_pct", "ads_pct", "returns_pct", "target_margin_pct", "uzum_trip_cost", "uzum_vat_pct",
)

# Tovar holatlari (Xarid moduli boshlanishi)
STATUSES: dict[str, str] = {
    "idea": "💡 G'oya",
    "sample": "🧪 Namuna",
    "batch": "📦 Partiya",
    "transit": "🚚 Yo'lda",
    "selling": "🛒 Sotuvda",
    "stopped": "⛔ To'xtatildi",
}
# Pul "bog'langan" holatlar — byudjetdan ishlatilgan hisoblanadi
CAPITAL_STATUSES = ("sample", "batch", "transit", "selling")

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
    tg_id INTEGER PRIMARY KEY,
    name TEXT,
    role TEXT NOT NULL DEFAULT 'member',
    added_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS cargos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mode TEXT NOT NULL,              -- avia / avto
    tariff_usd_kg REAL NOT NULL,
    days_min INTEGER,
    days_max INTEGER,
    white_docs INTEGER DEFAULT 0,    -- "oq" hujjat beradimi
    olmaliq INTEGER DEFAULT 0,       -- Olmaliqda punkti bormi
    note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_link TEXT,
    cargo_id INTEGER,
    input_json TEXT NOT NULL,
    landed REAL,
    sell_price REAL,
    profit REAL,
    margin_pct REAL,
    verdict TEXT,
    created_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

# Eski bazaga qo'shiladigan ustunlar: (jadval, ustun, ta'rif)
MIGRATIONS = [
    ("products", "status", "TEXT NOT NULL DEFAULT 'idea'"),
    ("products", "note", "TEXT"),
    ("products", "batch_cost", "REAL"),
    ("products", "updated_at", "TEXT"),
    ("products", "category_id", "INTEGER"),
    ("products", "scheme", "TEXT NOT NULL DEFAULT 'FBO'"),
    ("cargos", "usd_m3", "REAL"),            # kub metr narxi, $/m³ (zich bo'lmagan yuk uchun)
    ("cargos", "vol_divisor", "REAL"),       # o'z hajmiy vazn bo'luvchisi (bo'sh — sozlamadagi)
    ("cargos", "pickup_cost", "REAL"),       # punktdan uyga olib kelish, so'm/qatnov
    ("cargos", "rating", "INTEGER NOT NULL DEFAULT 3"),   # sifat/ishonch 1–5
    ("cargos", "verified", "INTEGER NOT NULL DEFAULT 1"), # 0 — saytdagi narx, tasdiqlanmagan
    ("cargos", "source", "TEXT"),
    ("cargos", "series_ok", "INTEGER"),      # bir xil tovar partiyasini oladimi (NULL — noma'lum)
    ("cargos", "min_kg", "REAL"),            # minimal yuk vazni, kg
    ("cargos", "checked_at", "TEXT"),        # narx manbadan tekshirilgan sana
]

CARGO_FIELDS = ("name", "mode", "tariff_usd_kg", "days_min", "days_max", "white_docs", "olmaliq", "note",
                "usd_m3", "vol_divisor", "pickup_cost", "rating", "verified", "source", "series_ok", "min_kg",
                "checked_at")

PRODUCT_FIELDS = ("name", "source_link", "cargo_id", "status", "note", "category_id", "scheme")


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.executescript(SCHEMA)
        for table, col, ddl in MIGRATIONS:
            cur = await self.conn.execute(f"PRAGMA table_info({table})")
            cols = {r["name"] for r in await cur.fetchall()}
            if col not in cols:
                await self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        # eskirgan sozlamalar (masalan, ekvayring — u komissiya ichida) o'chiriladi
        await self.conn.execute(
            f"DELETE FROM settings WHERE key NOT IN ({','.join('?' * len(SETTINGS))})", tuple(SETTINGS))
        for key, (_, default, _) in SETTINGS.items():
            await self.conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (key, default)
            )
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    def backup_to(self, dest: str) -> None:
        """Ishlab turgan bazaning izchil nusxasi (sinxron — thread'da chaqiring)."""
        src = sqlite3.connect(self.path)
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

    # --- sozlamalar ---
    async def get_settings(self) -> dict[str, float]:
        cur = await self.conn.execute("SELECT key, value FROM settings")
        return {r["key"]: r["value"] for r in await cur.fetchall()}

    async def set_setting(self, key: str, value: float) -> None:
        if key not in SETTINGS:
            raise KeyError(key)
        await self.conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await self.conn.commit()

    # --- foydalanuvchilar ---
    async def ensure_owner(self, tg_id: int, name: str = "Ega") -> None:
        await self.ensure_admins({tg_id: name})

    async def ensure_admins(self, admins: dict[int, str]) -> None:
        """.env dagi adminlarni 'owner' roli va berilgan ism bilan yozadi (ism yangilanadi).
        .env dan olib tashlangan adminlar bazadan ham o'chiriladi (/adduser a'zolariga tegilmaydi)."""
        if admins:
            marks = ",".join("?" * len(admins))
            await self.conn.execute(
                f"DELETE FROM users WHERE role = 'owner' AND tg_id NOT IN ({marks})", tuple(admins))
        for tg_id, name in admins.items():
            await self.conn.execute(
                "INSERT INTO users(tg_id, name, role) VALUES (?, ?, 'owner') "
                "ON CONFLICT(tg_id) DO UPDATE SET name = excluded.name, role = 'owner'",
                (tg_id, name),
            )
        await self.conn.commit()

    async def is_allowed(self, tg_id: int) -> bool:
        cur = await self.conn.execute("SELECT 1 FROM users WHERE tg_id = ?", (tg_id,))
        return await cur.fetchone() is not None

    async def add_user(self, tg_id: int, name: str, role: str = "member") -> None:
        await self.conn.execute(
            "INSERT OR REPLACE INTO users(tg_id, name, role) VALUES (?, ?, ?)", (tg_id, name, role)
        )
        await self.conn.commit()

    async def list_users(self) -> list[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT * FROM users ORDER BY added_at")
        return await cur.fetchall()

    async def get_user(self, tg_id: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        return await cur.fetchone()

    async def user_role(self, tg_id: int) -> Optional[str]:
        row = await self.get_user(tg_id)
        return row["role"] if row else None

    async def user_names(self) -> dict[int, str]:
        return {r["tg_id"]: r["name"] for r in await self.list_users()}

    # --- kargolar ---
    @staticmethod
    def _cargo_row(data: dict[str, Any]) -> dict[str, Any]:
        row = {k: data.get(k) for k in CARGO_FIELDS}
        row["rating"] = int(row["rating"] or 3)
        row["verified"] = 1 if row["verified"] in (None, "") else int(bool(row["verified"]))
        for k in ("white_docs", "olmaliq", "series_ok"):     # None — noma'lum bo'lib qoladi
            row[k] = None if row[k] is None else int(bool(row[k]))
        if row["olmaliq"] is None:
            row["olmaliq"] = 0
        return row

    async def upsert_cargo(self, data: dict[str, Any]) -> str:
        """Nomi va turi bo'yicha: bor bo'lsa yangilaydi (reyting va olib kelish narxi saqlanadi)."""
        cur = await self.conn.execute("SELECT * FROM cargos WHERE name = ? AND mode = ?",
                                      (data["name"], data["mode"]))
        old = await cur.fetchone()
        if not old:
            await self.add_cargo(data)
            return "yangi"
        keep = {k: old[k] for k in ("rating", "pickup_cost")}
        if data.get("tariff_usd_kg", 0) <= 0 and old["tariff_usd_kg"] > 0:
            keep["tariff_usd_kg"] = old["tariff_usd_kg"]     # qo'lda kiritilgan tarif yo'qolmasin
        await self.update_cargo(old["id"], {**data, **keep})
        return "yangilandi"

    async def set_cargo_tariff(self, cargo_id: int, tariff: float) -> None:
        await self.conn.execute("UPDATE cargos SET tariff_usd_kg = ?, verified = 1 WHERE id = ?",
                                (tariff, cargo_id))
        await self.conn.commit()

    async def add_cargo(self, data: dict[str, Any]) -> int:
        row = self._cargo_row(data)
        cols = ", ".join(CARGO_FIELDS)
        marks = ", ".join(f":{k}" for k in CARGO_FIELDS)
        cur = await self.conn.execute(f"INSERT INTO cargos({cols}) VALUES ({marks})", row)
        await self.conn.commit()
        return cur.lastrowid

    async def update_cargo(self, cargo_id: int, data: dict[str, Any]) -> None:
        row = self._cargo_row(data)
        sets = ", ".join(f"{k}=:{k}" for k in CARGO_FIELDS)
        await self.conn.execute(f"UPDATE cargos SET {sets} WHERE id=:id", {**row, "id": cargo_id})
        await self.conn.commit()

    async def list_cargos(self) -> list[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT * FROM cargos ORDER BY tariff_usd_kg")
        return await cur.fetchall()

    async def get_cargo(self, cargo_id: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT * FROM cargos WHERE id = ?", (cargo_id,))
        return await cur.fetchone()

    async def delete_cargo(self, cargo_id: int) -> None:
        await self.conn.execute("DELETE FROM cargos WHERE id = ?", (cargo_id,))
        await self.conn.commit()

    # --- tovarlar ---
    async def save_product(self, name: str, link: Optional[str], cargo_id: Optional[int], inp: dict,
                           res: dict, user_id: int, status: str = "idea",
                           note: Optional[str] = None, category_id: Optional[int] = None,
                           scheme: str = "FBO") -> int:
        cur = await self.conn.execute(
            "INSERT INTO products(name, source_link, cargo_id, input_json, landed, sell_price, "
            "profit, margin_pct, verdict, created_by, status, note, batch_cost, category_id, scheme) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (name, link, cargo_id, json.dumps(inp, ensure_ascii=False), res["landed"],
             inp["sell_price"], res["profit"], res["margin_pct"], res["verdict"], user_id,
             status if status in STATUSES else "idea", note, res.get("batch_cost"), category_id,
             scheme if scheme in ("FBO", "FBS") else "FBO"),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def update_product(self, pid: int, fields: dict[str, Any],
                             inp: Optional[dict] = None, res: Optional[dict] = None) -> None:
        sets, vals = [], []
        for k in PRODUCT_FIELDS:
            if k in fields:
                if k == "status" and fields[k] not in STATUSES:
                    raise ValueError("Noma'lum holat")
                sets.append(f"{k} = ?")
                vals.append(fields[k])
        if inp is not None and res is not None:
            sets += ["input_json = ?", "landed = ?", "sell_price = ?", "profit = ?",
                     "margin_pct = ?", "verdict = ?", "batch_cost = ?"]
            vals += [json.dumps(inp, ensure_ascii=False), res["landed"], inp["sell_price"],
                     res["profit"], res["margin_pct"], res["verdict"], res.get("batch_cost")]
        if not sets:
            return
        sets.append("updated_at = CURRENT_TIMESTAMP")
        await self.conn.execute(f"UPDATE products SET {', '.join(sets)} WHERE id = ?", (*vals, pid))
        await self.conn.commit()

    async def list_products(self, limit: int = 20) -> list[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM products ORDER BY id DESC LIMIT ?", (limit,)
        )
        return await cur.fetchall()

    async def get_product(self, pid: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT * FROM products WHERE id = ?", (pid,))
        return await cur.fetchone()

    async def delete_product(self, pid: int) -> None:
        await self.conn.execute("DELETE FROM products WHERE id = ?", (pid,))
        await self.conn.commit()
