import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Config:
    bot_token: str
    admins: dict[int, str]          # tg_id -> ism (tartib saqlanadi, birinchisi — asosiy ega)
    db_path: str
    gemini_api_key: str
    gemini_model: str
    healthcheck_url: str
    heartbeat_seconds: int
    webapp_port: int = 8088
    webapp_url: str = ""            # qat'iy manzil (masalan, o'z domeningiz). Bo'sh — tunnel
    tunnel: str = "cloudflared"     # cloudflared / none
    backup_hour: int = 23
    tinyfish_api_key: str = ""      # Uzum sahifalarini o'qish (TinyFish Fetch, bepul)

    @property
    def owner_id(self) -> int:
        return next(iter(self.admins))


def parse_admins(raw: str) -> dict[int, str]:
    """'359795989:Quddusxon,660673338:Gulim' -> {359795989: 'Quddusxon', 660673338: 'Gulim'}"""
    out: dict[int, str] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        tid, _, name = part.partition(":")
        tid = tid.strip()
        if tid.isdigit():
            out[int(tid)] = name.strip() or "Admin"
    return out


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    admins = parse_admins(os.getenv("ADMINS", ""))
    owner = os.getenv("OWNER_ID", "").strip()   # eski format bilan moslik
    if owner.isdigit() and int(owner) not in admins:
        admins = {int(owner): "Ega", **admins}
    if not token or not admins:
        raise SystemExit(".env faylida BOT_TOKEN va ADMINS to'ldirilmagan. README.md ga qarang.")
    return Config(
        bot_token=token,
        admins=admins,
        db_path=os.getenv("DB_PATH", str(BASE_DIR / "data" / "bot.db")),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip(),
        healthcheck_url=os.getenv("HEALTHCHECK_URL", "").strip(),
        heartbeat_seconds=int(os.getenv("HEARTBEAT_SECONDS", "300")),
        webapp_port=int(os.getenv("WEBAPP_PORT", "8088")),
        webapp_url=os.getenv("WEBAPP_URL", "").strip().rstrip("/"),
        tunnel=os.getenv("TUNNEL", "cloudflared").strip().lower(),
        backup_hour=int(os.getenv("BACKUP_HOUR", "23")),
        tinyfish_api_key=os.getenv("TINYFISH_API_KEY", "").strip(),
    )
