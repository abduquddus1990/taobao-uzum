"""Telegramga ulanmasdan botning to'liq dialogini sinash (soxta sessiya bilan)."""
import asyncio
import datetime as dt
import tempfile
import unittest

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from bot.db import Database
from bot.gemini import GeminiClient
from bot.handlers import all_routers
from bot.middlewares import AccessMiddleware
from bot.uzum_tariffs import TARIFFS

TARIFFS.load()

OWNER = 111
STRANGER = 999


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.sent = []

    async def make_request(self, bot, method, timeout=None):
        self.sent.append(method)
        ret = method.__returning__
        if ret is Message:
            return Message(message_id=len(self.sent), date=dt.datetime.now(),
                           chat=Chat(id=getattr(method, "chat_id", OWNER), type="private"),
                           text=getattr(method, "text", None))
        return True

    async def stream_content(self, *a, **k):
        yield b""

    async def close(self):
        pass


def texts(session):
    return [m.text for m in session.sent if getattr(m, "text", None)]


class FlowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(f"{self.tmp.name}/t.db")
        await self.db.connect()
        await self.db.ensure_owner(OWNER)
        self.session = FakeSession()
        self.bot = Bot("123:ABC", session=self.session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self.dp = Dispatcher(storage=MemoryStorage())
        self.dp["db"] = self.db
        self.dp["gemini"] = GeminiClient("", "x")
        self.dp.message.outer_middleware(AccessMiddleware())
        self.dp.callback_query.outer_middleware(AccessMiddleware())
        for r in all_routers():
            self.dp.include_router(r)
        self.uid = 0

    async def asyncTearDown(self):
        await self.db.close()
        self.tmp.cleanup()

    async def msg(self, text, user=OWNER):
        self.uid += 1
        m = Message(message_id=self.uid, date=dt.datetime.now(), chat=Chat(id=user, type="private"),
                    from_user=User(id=user, is_bot=False, first_name="Q"), text=text)
        await self.dp.feed_update(self.bot, Update(update_id=self.uid, message=m))

    async def cb(self, data, user=OWNER):
        self.uid += 1
        m = Message(message_id=1, date=dt.datetime.now(), chat=Chat(id=user, type="private"), text="x")
        q = CallbackQuery(id=str(self.uid), from_user=User(id=user, is_bot=False, first_name="Q"),
                          chat_instance="c", message=m, data=data)
        await self.dp.feed_update(self.bot, Update(update_id=self.uid, callback_query=q))

    async def test_full_flow(self):
        await self.msg(STRANGER and "/start", user=STRANGER)
        self.assertIn("yopiq bot", texts(self.session)[-1])

        await self.msg("/start")
        self.assertIn("Assalomu alaykum", texts(self.session)[-1])

        # kargo qo'shish
        await self.cb("cargo:add:0")
        await self.msg("iPost")
        await self.cb("ch:mode:avto")
        await self.msg("6,7")
        await self.msg("12-15")
        await self.cb("ch:white_docs:1")
        await self.cb("ch:olmaliq:1")
        await self.msg("-")
        cargos = await self.db.list_cargos()
        self.assertEqual(cargos[0]["name"], "iPost")
        self.assertEqual(cargos[0]["tariff_usd_kg"], 6.7)

        # sozlama o'zgartirish
        await self.cb("set:cny_rate")
        await self.msg("1 760")
        self.assertEqual((await self.db.get_settings())["cny_rate"], 1760)

        # tannarx hisoblash
        await self.msg("🧮 Tannarx hisoblash")
        await self.msg("Mini zont")
        await self.msg("https://item.taobao.com/item.htm?id=1")
        await self.msg("15")
        await self.msg("250")
        await self.msg("30 x 20 x 15")          # o'lcham -> 9 litr
        await self.msg("50")
        await self.msg("soyabon")                # Uzum toifasi qidiruvi
        self.assertIn("Qaysi biri", texts(self.session)[-1])
        await self.cb("ch:cat:13841")            # Aksessuarlar › Erkaklar › Soyabonlar (30.5%)
        await self.msg("129000")
        self.assertIn("Kargo takliflari", texts(self.session)[-1])
        await self.cb(f"cargo:pick:{cargos[0]['id']}")
        report = [t for t in texts(self.session) if "Sof foyda" in t][-1]
        self.assertIn("taobao.com", report)
        self.assertIn("Soyabon", report)
        self.assertIn("(9 l)", report)
        self.assertIn("30.5%", report)
        self.assertIn("Xulosa", report)
        await self.cb("prod:save:0")
        prods = await self.db.list_products()
        self.assertEqual(prods[0]["name"], "Mini zont")
        self.assertEqual(prods[0]["category_id"], 13841)

        await self.msg("📦 Tovarlarim")
        self.assertIn("Mini zont", texts(self.session)[-1])
        await self.cb(f"prod:view:{prods[0]['id']}")
        self.assertIn("Sof foyda", texts(self.session)[-1])

        # bekor qilish
        await self.msg("🧮 Tannarx hisoblash")
        await self.msg("❌ Bekor qilish")
        self.assertEqual(texts(self.session)[-1], "Bekor qilindi.")

        # foydalanuvchi qo'shish
        await self.msg("/adduser 222 Ayolim")
        self.assertTrue(await self.db.is_allowed(222))
        await self.msg("⚙️ Sozlamalar", user=222)
        self.assertIn("Sozlamalar", texts(self.session)[-1])
        await self.cb("set:cny_rate", user=222)  # a'zo sozlamani o'zgartira olmaydi
        self.assertEqual((await self.db.get_settings())["cny_rate"], 1760)

        # AI kaliti yo'q
        await self.msg("🤖 AI yordamchi")
        self.assertIn("Gemini kaliti", texts(self.session)[-1])


if __name__ == "__main__":
    unittest.main()
