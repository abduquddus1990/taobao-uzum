"""Botni ishga tushirish: python run.py"""
import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, LinkPreviewOptions, MenuButtonWebApp, WebAppInfo

from bot.backup import backup_loop
from bot.cargo_import import import_cargos
from bot.config import load_config
from bot.db import Database
from bot.gemini import GeminiClient
from bot.tinyfish import TinyFishClient
from bot.handlers import all_routers
from bot.heartbeat import heartbeat_loop
from bot.keyboards import WEBAPP, main_menu
from bot.middlewares import AccessMiddleware
from bot.rates import rates_loop
from bot.tunnel import QuickTunnel
from bot.uzum_tariffs import TARIFFS, refresh_loop
from bot.webapp import create_app, start_server

log = logging.getLogger("run")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config()

    TARIFFS.load()
    db = Database(cfg.db_path)
    await db.connect()
    await db.ensure_admins(cfg.admins)
    if not await db.list_cargos():          # birinchi ishga tushish: tayyor kargolar ro'yxati
        try:
            logging.info("Kargolar import qilindi: %s ta", len(await import_cargos(db)))
        except Exception as exc:
            logging.warning("data_seed/cargos.json import qilinmadi: %s", exc)

    bot = Bot(
        cfg.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview=LinkPreviewOptions(is_disabled=True),
        ),
    )
    gemini = GeminiClient(cfg.gemini_api_key, cfg.gemini_model)
    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db
    dp["gemini"] = gemini
    dp["tinyfish"] = TinyFishClient(cfg.tinyfish_api_key)

    dp.message.outer_middleware(AccessMiddleware())
    dp.callback_query.outer_middleware(AccessMiddleware())
    for r in all_routers():
        dp.include_router(r)

    await bot.set_my_commands([
        BotCommand(command="start", description="Bosh menyu"),
        BotCommand(command="app", description="Ilovani ochish"),
        BotCommand(command="cancel", description="Bekor qilish"),
        BotCommand(command="backup", description="Zaxira nusxa"),
        BotCommand(command="baho", description="Taobao linki -> tezkor baho"),
        BotCommand(command="foto", description="Foto studiya: fonni olib tashlash"),
        BotCommand(command="kurs", description="Markaziy bank kursini yangilash"),
        BotCommand(command="bozor", description="Uzum bozor tahlili (skrinshotlar)"),
        BotCommand(command="tariflar", description="Uzum tariflarini yangilash"),
        BotCommand(command="import_kargo", description="Kargolarni cargos.json dan yangilash"),
        BotCommand(command="help", description="Yordam"),
    ])

    # --- Mini App ---
    runner = await start_server(create_app(db, bot, gemini, cfg.bot_token), cfg.webapp_port)

    async def set_webapp_url(url: str) -> None:
        WEBAPP["url"] = url
        button = MenuButtonWebApp(text="📱 Ilova", web_app=WebAppInfo(url=url))
        for admin_id, name in cfg.admins.items():
            try:
                await bot.set_chat_menu_button(chat_id=admin_id, menu_button=button)
            except Exception as exc:
                log.warning("%s uchun menyu tugmasi o'rnatilmadi: %s", name, exc)

    tunnel = None
    tunnel_task = None
    if cfg.webapp_url:
        await set_webapp_url(cfg.webapp_url)
    elif cfg.tunnel == "cloudflared":
        tunnel = QuickTunnel(cfg.webapp_port, set_webapp_url)
        tunnel_task = asyncio.create_task(tunnel.run_forever())
        for _ in range(80):          # manzil chiqishini 40 s gacha kutamiz
            if WEBAPP["url"]:
                break
            await asyncio.sleep(0.5)

    tasks = [
        asyncio.create_task(heartbeat_loop(cfg.healthcheck_url, cfg.heartbeat_seconds)),
        asyncio.create_task(backup_loop(bot, db, [cfg.owner_id], cfg.backup_hour)),
        asyncio.create_task(refresh_loop(bot, db, list(cfg.admins))),
        asyncio.create_task(rates_loop(bot, db, list(cfg.admins))),
    ]

    app_note = "📱 Ilova tayyor — chap pastdagi «Ilova» tugmasi." if WEBAPP["url"] else \
        "⚠️ Ilova manzili hali yo'q (cloudflared?). Chat menyusi ishlayveradi."
    try:
        await bot.send_message(cfg.owner_id, f"✅ Bot ishga tushdi.\n{app_note}", reply_markup=main_menu(),
                               disable_notification=True)
    except Exception:
        log.warning("Egaga xabar yuborilmadi — avval botga /start yozing")
    try:
        await dp.start_polling(bot)
    finally:
        for t in tasks:
            t.cancel()
        if tunnel:
            await tunnel.stop()
        if tunnel_task:
            tunnel_task.cancel()
        await runner.cleanup()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except BaseException:
        # Xato bilan to'xtasa, jarayon albatta yopilsin (ba'zi kutubxona oqimlari uni osiltirib
        # qo'yishi mumkin) — supervisor.py botni qayta ishga tushiradi.
        logging.exception("Bot xato bilan to'xtadi")
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
