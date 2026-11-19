"""Mini App: JS kalkulyator = Python kalkulyator, API imzo tekshiruvi va CRUD."""
import hashlib
import hmac
import json
import shutil
import subprocess
import tempfile
import time
import unittest
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlencode

from aiogram import Bot
from aiohttp.test_utils import TestClient, TestServer

from bot.calc import CalcInput, calculate
from bot.db import Database
from bot.gemini import GeminiClient
from bot.webapp import create_app
from tests.test_flow import FakeSession

TOKEN = "123456:TEST-TOKEN"
ROOT = Path(__file__).resolve().parent.parent
ADMIN, GULIM, STRANGER = 359795989, 660673338, 999


def init_data(user_id: int, name: str = "Q", token: str = TOKEN, age: int = 0) -> str:
    fields = {
        "auth_date": str(int(time.time()) - age),
        "query_id": "AAH",
        "user": json.dumps({"id": user_id, "first_name": name}, separators=(",", ":")),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


CASES = [
    dict(price_cny=15, weight_g=250, qty=50, tariff_usd_kg=6.7, sell_price=129_000, cny_rate=1750, usd_rate=12500),
    dict(price_cny=5, weight_g=50, qty=200, tariff_usd_kg=6.7, sell_price=28_000, cny_rate=1750, usd_rate=12500),
    dict(price_cny=38.5, weight_g=420, qty=30, tariff_usd_kg=8, sell_price=199_000, cny_rate=1760, usd_rate=12650,
         china_ship_cny=20, pack_cost=1500, length_cm=30, width_cm=20, height_cm=15, commission_pct=15),
    dict(price_cny=2, weight_g=900, qty=7, tariff_usd_kg=4.2, sell_price=15_000, cny_rate=1750, usd_rate=12500,
         ads_pct=0, returns_pct=0, commission_pct=99),
]


def _random_cases(n=300):
    import random
    rnd = random.Random(7)
    out = []
    for _ in range(n):
        out.append(dict(
            price_cny=rnd.uniform(1, 200), weight_g=rnd.uniform(10, 3000), qty=rnd.randint(1, 500),
            tariff_usd_kg=rnd.uniform(3, 12), sell_price=rnd.uniform(10000, 900000),
            cny_rate=rnd.uniform(1600, 1900), usd_rate=rnd.uniform(11500, 13500),
            commission_pct=rnd.uniform(5, 35), payout_fee_pct=rnd.choice([0, 1, 1.5]),
            uzum_vat_pct=rnd.choice([0, 12]), length_cm=rnd.choice([0, round(rnd.uniform(5, 80), 1)]),
            width_cm=round(rnd.uniform(5, 60), 1), height_cm=round(rnd.uniform(1, 50), 1),
            sell_days=rnd.choice([0, 45, rnd.uniform(1, 400)]), storage_special=rnd.randint(0, 1),
            storage_free_days=rnd.choice([30, 60]), cargo_usd_m3=rnd.choice([0, 700]),
            vol_divisor=rnd.choice([0, 5000, 6000]), fbo=rnd.randint(0, 1),
            china_ship_cny=rnd.uniform(0, 50), pack_cost=rnd.uniform(0, 3000),
            uzum_trip_cost=rnd.uniform(0, 300000)))
    return out


@unittest.skipUnless(shutil.which("node"), "node o'rnatilmagan")
class JsParityTest(unittest.TestCase):
    def test_js_matches_python(self):
        script = (
            "const c=require(process.argv[1]);const cases=JSON.parse(process.argv[2]);"
            "console.log(JSON.stringify(cases.map(x=>c.calculate(x))));"
        )
        full = [asdict(CalcInput(**c)) for c in CASES + _random_cases()]
        tmp = Path(tempfile.mkdtemp()) / "cases.json"
        tmp.write_text(json.dumps(full), encoding="utf-8")
        script = script.replace("JSON.parse(process.argv[2])",
                                "JSON.parse(require('fs').readFileSync(process.argv[2],'utf8'))")
        out = subprocess.run(["node", "-e", script, str(ROOT / "webapp" / "calc.js"), str(tmp)],
                             capture_output=True, text=True, check=True).stdout
        js = json.loads(out)
        for case, jr in zip(full, js):
            py = asdict(calculate(CalcInput(**case)))
            for k, v in py.items():
                if isinstance(v, float) and v == float("inf"):
                    self.assertIsNone(jr[k], k)
                elif isinstance(v, bool):
                    self.assertEqual(v, jr[k], k)
                elif isinstance(v, (int, float)):
                    self.assertAlmostEqual(v, jr[k], places=6, msg=k)
                else:
                    self.assertEqual(v, jr[k], k)


class ApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(f"{self.tmp.name}/t.db")
        await self.db.connect()
        await self.db.ensure_admins({ADMIN: "Quddusxon", GULIM: "Gulim"})
        self.session = FakeSession()
        self.bot = Bot(TOKEN, session=self.session)
        app = create_app(self.db, self.bot, GeminiClient("", "x"), TOKEN)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        await self.db.close()
        self.tmp.cleanup()

    async def call(self, method, path, body=None, user=ADMIN, raw=None):
        headers = {"X-Init-Data": raw if raw is not None else init_data(user)}
        resp = await self.client.request(method, path, json=body, headers=headers)
        return resp.status, await resp.json()

    async def test_auth(self):
        st, _ = await self.call("GET", "/api/boot", raw="")
        self.assertEqual(st, 401)
        st, _ = await self.call("GET", "/api/boot", raw=init_data(ADMIN, token="999:WRONG"))
        self.assertEqual(st, 401)
        st, _ = await self.call("GET", "/api/boot", raw=init_data(ADMIN, age=8 * 24 * 3600))
        self.assertEqual(st, 401)
        st, _ = await self.call("GET", "/api/boot", user=STRANGER)
        self.assertEqual(st, 403)
        st, d = await self.call("GET", "/api/boot", user=GULIM)
        self.assertEqual(st, 200)
        self.assertEqual(d["me"]["name"], "Gulim")
        self.assertEqual(d["me"]["role"], "owner")

    async def test_static(self):
        resp = await self.client.get("/")
        self.assertEqual(resp.status, 200)
        self.assertIn("telegram-web-app.js", await resp.text())
        for f in ("app.js", "calc.js", "style.css"):
            self.assertEqual((await self.client.get(f"/static/{f}")).status, 200, f)

    async def test_crud_flow(self):
        st, d = await self.call("PUT", "/api/settings", {"cny_rate": 1760})
        self.assertEqual(st, 200)
        self.assertEqual(d["settings"]["cny_rate"], 1760)
        st, _ = await self.call("PUT", "/api/settings", {"hack": 1})
        self.assertEqual(st, 400)

        st, d = await self.call("POST", "/api/cargos", {"name": "iPost", "mode": "avto", "tariff_usd_kg": 6.7,
                                                        "days_min": 12, "days_max": 15, "white_docs": True})
        self.assertEqual(st, 201)
        cid = d["cargo"]["id"]
        st, d = await self.call("PUT", f"/api/cargos/{cid}", {"name": "iPost", "mode": "avia", "tariff_usd_kg": 9})
        self.assertEqual(d["cargo"]["mode"], "avia")
        st, _ = await self.call("POST", "/api/cargos", {"name": "", "tariff_usd_kg": 1})
        self.assertEqual(st, 400)

        item = {"price_cny": 15, "weight_g": 250, "qty": 50, "tariff_usd_kg": 6.7, "sell_price": 129000}
        st, d = await self.call("POST", "/api/products", {"name": "Mini zont", "source_link": "https://item.taobao.com/x",
                                                          "cargo_id": cid, "item": item}, user=GULIM)
        self.assertEqual(st, 201, d)
        p = d["product"]
        self.assertEqual(p["created_by_name"], "Gulim")
        self.assertEqual(p["status"], "idea")
        self.assertIn("today", p)
        # boshqa adminga xabar ketdi (Gulim saqladi -> Quddusxon oladi)
        notes = [m for m in self.session.sent if getattr(m, "chat_id", None) == ADMIN]
        self.assertTrue(notes and "Gulim" in notes[-1].text)

        st, _ = await self.call("POST", "/api/products", {"name": "X", "source_link": "javascript:alert(1)", "item": item})
        self.assertEqual(st, 400)
        st, _ = await self.call("POST", "/api/products", {"name": "X", "item": {**item, "sell_price": 0}})
        self.assertEqual(st, 400)

        st, d = await self.call("PUT", f"/api/products/{p['id']}", {"status": "sample", "note": "qizil"})
        self.assertEqual(d["product"]["status"], "sample")
        self.assertEqual(d["product"]["note"], "qizil")
        st, _ = await self.call("PUT", f"/api/products/{p['id']}", {"status": "nope"})
        self.assertEqual(st, 400)
        st, d = await self.call("PUT", f"/api/products/{p['id']}", {"item": {**item, "sell_price": 150000}})
        self.assertEqual(d["product"]["input"]["sell_price"], 150000)

        st, d = await self.call("GET", "/api/boot")
        self.assertEqual(d["stats"]["by_status"]["sample"], 1)
        self.assertGreater(d["stats"]["capital_usd"], 0)

        st, _ = await self.call("DELETE", f"/api/products/{p['id']}")
        self.assertEqual(st, 200)
        st, _ = await self.call("DELETE", f"/api/cargos/{cid}")
        st, d = await self.call("GET", "/api/boot")
        self.assertEqual((len(d["products"]), len(d["cargos"])), (0, 0))

    async def test_categories_cargo_offers_flow(self):
        from bot.uzum_tariffs import TARIFFS
        TARIFFS.load()
        st, d = await self.call("GET", "/api/categories?q=soyabon")
        self.assertEqual(st, 200)
        self.assertTrue(any(c["id"] == 13841 for c in d["categories"]))

        st, d = await self.call("POST", "/api/cargos/import")
        self.assertEqual(d["added"], 18)
        st, d = await self.call("GET", "/api/boot")
        mk = next(c for c in d["cargos"] if c["name"] == "MK Express avto")
        self.assertEqual((mk["olmaliq"], mk["verified"], mk["series_ok"]), (1, 0, 1))
        self.assertAlmostEqual(mk["tariff_usd_kg"], round(83880 / 12500, 2))
        ipost = next(c for c in d["cargos"] if c["name"] == "iPost avto")
        self.assertEqual(ipost["olmaliq"], 0)              # null -> noma'lum, Olmaliq yo'q deb olinadi
        # reyting va qo'lda kiritilgan tarif qayta importda saqlanadi
        await self.call("PUT", f"/api/cargos/{ipost['id']}", {**ipost, "tariff_usd_kg": 7.2, "rating": 5})
        st, d = await self.call("POST", "/api/cargos/import")
        self.assertEqual((d["added"], d["updated"]), (0, 18))   # takrorlanmaydi
        st, d = await self.call("GET", "/api/boot")
        ipost = next(c for c in d["cargos"] if c["name"] == "iPost avto")
        self.assertEqual((ipost["tariff_usd_kg"], ipost["rating"]), (7.2, 5))

        item = {"price_cny": 15, "weight_g": 250, "qty": 50, "sell_price": 129000,
                "length_cm": 30, "width_cm": 20, "height_cm": 15}
        st, d = await self.call("POST", "/api/products", {"name": "Zont", "item": item, "cargo_id": mk["id"],
                                                          "category_id": 13841, "scheme": "FBO"})
        self.assertEqual(st, 201, d)
        p = d["product"]
        self.assertEqual(p["input"]["commission_pct"], 30.5)    # rasmiy jadvaldan
        self.assertEqual(p["input"]["trip_cost"], 0)            # Olmaliq punkti (sozlama: 0)
        self.assertEqual(p["input"]["uzum_trip_cost"], 200000)  # Uzum omboriga qatnov
        self.assertEqual(p["result"]["liters"], 9)
        self.assertEqual(p["result"]["logistics"], 7250)
        self.assertEqual(p["category_obj"]["id"], 13841)
        st, d = await self.call("POST", "/api/products", {"name": "X", "item": item, "category_id": 99999999})
        self.assertEqual(st, 400)

    async def test_member_cannot_change_settings(self):
        await self.db.add_user(555, "Yordamchi", "member")
        st, _ = await self.call("PUT", "/api/settings", {"cny_rate": 1}, user=555)
        self.assertEqual(st, 403)


if __name__ == "__main__":
    unittest.main()
