"""🔗 Tezkor baho va 📊 Uzum narxlari (TinyFish) testlari."""
import datetime as dt
import json
import tempfile
import unittest

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from bot.calc import calculate
from bot.cargo_import import import_cargos
from bot.db import Database
from bot.handlers import all_routers
from bot.middlewares import AccessMiddleware
from bot.quote import QuoteRequest, make_quote, nice_price, parse_request, quote_report
from bot.tinyfish import extract_text, uzum_search_url
from bot.uzum_tariffs import TARIFFS
from tests.test_flow import FakeSession, texts

TARIFFS.load()
OWNER = 111
LINK = "https://item.taobao.com/item.htm?id=123456789012"


class ParseTest(unittest.TestCase):
    def test_plain_numbers(self):
        r = parse_request(f"{LINK} 15 250")
        self.assertEqual((r.link, r.price_cny, r.weight_g, r.qty), (LINK, 15, 250, None))
        self.assertEqual(r.name, "Taobao #123456789012")

    def test_units_dims_qty_cat_name(self):
        r = parse_request(f"Mini zont {LINK} ¥15,5 0.3kg 18x6x6 50ta #soyabon")
        self.assertEqual(r.price_cny, 15.5)
        self.assertEqual(r.weight_g, 300)
        self.assertEqual(r.dims, (18, 6, 6))
        self.assertEqual(r.qty, 50)
        self.assertEqual(r.category_query, "soyabon")
        self.assertEqual(r.name, "Mini zont")

    def test_any_order_and_yuan_word(self):
        r = parse_request(f"{LINK} 250g 12 yuan")
        self.assertEqual((r.price_cny, r.weight_g), (12, 250))

    def test_taobao_share_text_ignores_stray_numbers(self):
        share = ("【淘宝】7天无理由退货 https://m.tb.cn/h.TU4iKGX?tk=abc CZ057 「迷你折叠伞防晒防紫外线」"
                 "点击链接直接打开")
        r = parse_request(share)
        self.assertTrue(r.link.startswith("https://m.tb.cn/"))
        self.assertIsNone(r.price_cny)          # "7天" narx deb olinmadi
        self.assertEqual(r.name, "迷你折叠伞防晒防紫外线")
        self.assertEqual(r.missing(), ["narx (¥)", "vazn (g)"])
        r2 = r.merge(parse_request("15 250"))
        self.assertEqual((r2.price_cny, r2.weight_g, r2.link), (15, 250, r.link))

    def test_1688_link(self):
        r = parse_request("https://detail.1688.com/offer/6543.html 3.2 80 100")
        self.assertEqual((r.price_cny, r.weight_g, r.qty), (3.2, 80, 100))

    def test_nice_price(self):
        self.assertEqual(nice_price(58743), 58900)
        self.assertEqual(nice_price(58950), 59900)
        self.assertEqual(nice_price(129000), 129900)
        self.assertEqual(nice_price(128900), 128900)


SETTINGS = {"cny_rate": 1750, "usd_rate": 12500, "fx_spread_pct": 3, "buyer_pct": 10, "china_ship_cny": 15,
            "vol_divisor": 6000, "trip_cost": 0, "olmaliq_pickup_cost": 0, "uzum_trip_cost": 200000,
            "pack_cost": 1500, "commission_pct": 25, "logistics_fee": 5250, "uzum_vat_pct": 0,
            "payout_fee_pct": 0, "tax_pct": 1, "ads_pct": 10, "returns_pct": 5, "sell_days": 45,
            "target_margin_pct": 20, "budget_usd": 1000}

CARGOS = [
    {"id": 1, "name": "Arzon avto", "mode": "avto", "tariff_usd_kg": 5, "days_min": 20, "days_max": 25,
     "white_docs": 1, "olmaliq": 0, "rating": 3, "series_ok": 1, "min_kg": None, "vol_divisor": 6000},
    {"id": 2, "name": "Faqat namuna", "mode": "avia", "tariff_usd_kg": 9, "days_min": 3, "days_max": 7,
     "white_docs": None, "olmaliq": 1, "rating": 3, "series_ok": 0, "min_kg": None, "vol_divisor": 6000},
]


class QuoteMathTest(unittest.TestCase):
    def test_recommended_price_meets_target_margin(self):
        q = make_quote(SETTINGS, parse_request(f"{LINK} 15 250 18x6x6"), CARGOS)
        self.assertEqual(q.offer["cargo"]["name"], "Arzon avto")   # namuna-kargo partiyaga mos emas
        self.assertEqual(q.inp.qty, 20)
        self.assertGreaterEqual(q.rec_price, q.result.target_price)
        self.assertGreaterEqual(q.result.margin_pct, 19.99)
        self.assertEqual(q.rec_price % 1000, 900)
        # zararsizlik narxida foyda 0
        r0 = calculate(q.inp.__class__(**{**q.inp.__dict__, "sell_price": q.result.breakeven_price}))
        self.assertAlmostEqual(r0.profit, 0, delta=1)
        text = quote_report(q)
        for s in ("¥15", "Tavsiya narx", "Minimal narx", "Zararsizlik", "Arzon avto", LINK):
            self.assertIn(s, text)

    def test_no_cargo_still_quotes(self):
        q = make_quote(SETTINGS, parse_request(f"{LINK} 15 250"), [])
        self.assertIsNone(q.offer)
        self.assertTrue(any("kargo" in n.lower() for n in q.notes))

    def test_missing_raises(self):
        with self.assertRaises(ValueError):
            make_quote(SETTINGS, QuoteRequest(link=LINK, price_cny=15), CARGOS)


class TinyFishTest(unittest.TestCase):
    def test_extract_text_any_shape(self):
        self.assertEqual(extract_text({"results": [{"url": "u", "markdown": "abc"}]}), "abc")
        self.assertEqual(extract_text([{"data": {"content": "x" * 10, "text": "y"}}]), "x" * 10)

    def test_search_url(self):
        self.assertEqual(uzum_search_url("mini zont"), "https://uzum.uz/uz/search?query=mini+zont")


class FakeGemini:
    enabled = True

    async def market_listings_text(self, page):
        assert "Mini zont" in page
        return json.dumps([
            {"title": "Mini zont A", "price": "129 000", "old_price": 189000, "rating": 4.9, "reviews": 30,
             "orders": 120},
            {"title": "Mini zont B", "price": 89000, "rating": 4.7, "reviews": 212, "orders": 728},
            {"title": "Mini zont C", "price": 59900, "orders": 10},
        ])


class FakeTinyFish:
    enabled = True

    def __init__(self):
        self.urls = []

    async def fetch(self, url, timeout=60):
        self.urls.append(url)
        return "Mini zont ... " * 50


class QuoteFlowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(f"{self.tmp.name}/t.db")
        await self.db.connect()
        await self.db.ensure_owner(OWNER)
        await import_cargos(self.db)
        self.session = FakeSession()
        self.bot = Bot("123:ABC", session=self.session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self.dp = Dispatcher(storage=MemoryStorage())
        self.tiny = FakeTinyFish()
        self.dp["db"], self.dp["gemini"], self.dp["tinyfish"] = self.db, FakeGemini(), self.tiny
        self.dp.message.outer_middleware(AccessMiddleware())
        self.dp.callback_query.outer_middleware(AccessMiddleware())
        for r in all_routers():
            r._parent_router = None          # boshqa testdagi dispetcherdan ajratamiz
            self.dp.include_router(r)
        self.uid = 0

    async def asyncTearDown(self):
        for r in all_routers():
            r._parent_router = None
        await self.db.close()       # Windows: fayl yopilmasa, papkani o'chirib bo'lmaydi
        self.tmp.cleanup()

    async def msg(self, text):
        self.uid += 1
        m = Message(message_id=self.uid, date=dt.datetime.now(), chat=Chat(id=OWNER, type="private"),
                    from_user=User(id=OWNER, is_bot=False, first_name="Q"), text=text)
        await self.dp.feed_update(self.bot, Update(update_id=self.uid, message=m))

    async def cb(self, data):
        self.uid += 1
        m = Message(message_id=1, date=dt.datetime.now(), chat=Chat(id=OWNER, type="private"), text="x")
        q = CallbackQuery(id=str(self.uid), from_user=User(id=OWNER, is_bot=False, first_name="Q"),
                          chat_instance="c", message=m, data=data)
        await self.dp.feed_update(self.bot, Update(update_id=self.uid, callback_query=q))

    async def test_link_then_details_save_and_uzum(self):
        await self.msg(LINK)
        self.assertIn("Yetishmaydi", texts(self.session)[-1])
        await self.msg("15 250 18x6x6 #soyabon")
        report = [t for t in texts(self.session) if "Tavsiya narx" in t][-1]
        self.assertIn("Minimal narx", report)
        self.assertIn("🏷", report)                    # toifa topildi

        await self.cb("ch:q:save")
        rows = await self.db.list_products()
        self.assertEqual(rows[0]["source_link"], LINK)
        self.assertEqual(rows[0]["status"], "idea")

        await self.cb("ch:q:uzum")
        await self.msg("Mini zont")
        self.assertEqual(self.tiny.urls, ["https://uzum.uz/uz/search?query=Mini+zont"])
        market = [t for t in texts(self.session) if "Uzum bozor tahlili" in t][-1]
        self.assertIn("Sizning tovaringiz", market)
        self.assertIn("uzum.uz/uz/search", market)

    async def test_full_link_in_one_message(self):
        await self.msg(f"{LINK} ¥15 250g 30ta Mini zont")
        report = [t for t in texts(self.session) if "Tavsiya narx" in t][-1]
        self.assertIn("30 dona", report)
        self.assertIn("Mini zont", report)


if __name__ == "__main__":
    unittest.main()
