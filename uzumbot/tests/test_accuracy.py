"""Hisob aniqligi: rasmiy Uzum misollari, qo'lda hisoblangan misol, tasodifiy tekshiruvlar."""
import random
import unittest

from bot.calc import CalcInput, calculate, storage_per_unit, uzum_liters, uzum_logistics
from bot.service import build_input, cargo_offers
from bot.uzum_tariffs import TARIFFS

TARIFFS.load()


class UzumOfficialRulesTest(unittest.TestCase):
    def test_liters_rounding_from_manual(self):
        # qo'llanma: 500×380×300 mm = 57 l; 1,6 -> 2; 5,2 -> 6; 104,3 -> 105
        self.assertEqual(uzum_liters(50, 38, 30), 57)
        self.assertEqual(uzum_liters(10, 10, 16), 2)      # 1.6 l
        self.assertEqual(uzum_liters(10, 10, 52), 6)      # 5.2 l
        self.assertEqual(uzum_liters(10, 10, 1043), 105)  # 104.3 l
        self.assertEqual(uzum_liters(10, 10, 10), 1)      # aniq 1 l — 2 emas
        self.assertEqual(uzum_liters(30, 20, 15), 9)      # aniq 9 l (suzuvchi nuqta xatosi yo'q)
        self.assertEqual(uzum_liters(0, 20, 15), 0)

    def test_logistics_grid_from_manual(self):
        self.assertEqual(uzum_logistics(1), 5250)
        self.assertEqual(uzum_logistics(2), 5500)
        self.assertEqual(uzum_logistics(57), 19250)       # qo'llanmadagi misol
        self.assertEqual(uzum_logistics(180), 50000)
        self.assertEqual(uzum_logistics(500), 50000)      # maksimum

    def test_storage(self):
        # 90 kunda sotilsa: aylanma hech qachon 60 dan oshmaydi (30-kundan keyin <=60) -> 0
        self.assertEqual(storage_per_unit(9, 90, 30, False), 0)
        self.assertEqual(storage_per_unit(9, 45, 30, False), 0)
        # 120 kun: 30..59-kunlar aylanma 90..61 -> 12 so'm/l/kun × qoldiq ulushi
        expected = sum((1 - t / 120) * 12 * 9 for t in range(30, 60))
        self.assertAlmostEqual(storage_per_unit(9, 120, 30, False), expected)
        # maxsus tarif 181+ kunda arzonroq
        self.assertLess(storage_per_unit(9, 400, 30, True), storage_per_unit(9, 400, 30, False))
        # FBS da saqlash yo'q
        base = dict(price_cny=10, weight_g=200, qty=10, tariff_usd_kg=6, sell_price=100000, cny_rate=1750,
                    usd_rate=12500, length_cm=30, width_cm=20, height_cm=15, sell_days=200)
        self.assertGreater(calculate(CalcInput(**base, fbo=1)).storage, 0)
        self.assertEqual(calculate(CalcInput(**base, fbo=0)).storage, 0)

    def test_no_separate_acquiring(self):
        r = calculate(CalcInput(price_cny=10, weight_g=100, qty=10, tariff_usd_kg=6, sell_price=100000,
                                cny_rate=1750, usd_rate=12500, commission_pct=20, ads_pct=0, returns_pct=0,
                                tax_pct=0, length_cm=10, width_cm=10, height_cm=10))
        # komissiya (ekvayring ichida) + logistika — boshqa hech narsa
        self.assertAlmostEqual(r.fees, 20000 + 5250)


class HandCalculatedTest(unittest.TestCase):
    def test_full_example_by_hand(self):
        """Har bir qator qo'lda hisoblangan:

        Tovar: 20 ¥ × 1750 × 1.03 = 36 050
        Bayer 10%: 3 605
        Kargo: 30×20×15 = 9000 sm³ / 6000 = 1.5 kg > 0.4 kg -> 1.5 × 6 $ × 12 500 = 112 500
        Xitoy ichki: 30 ¥ × 1750 × 1.03 / 40 = 1 351.875
        Qadoq: 1 500
        Olib kelish: 200 000 / 40 = 5 000; Uzumga topshirish: 200 000 / 40 = 5 000
        Tannarx = 36 050 + 3 605 + 112 500 + 1 351.875 + 1 500 + 5 000 + 5 000 = 165 006.875

        Sotuv 399 000: komissiya 30.5% = 121 695; logistika 9 l = 5 250 + 8×250 = 7 250;
        soliq 1% = 3 990; reklama 10% = 39 900; brak 5% = 19 950; pul yechish 0; saqlash 0 (45 kun)
        Xarajatlar = 192 785; Foyda = 399 000 − 165 006.875 − 192 785 = 41 208.125
        """
        inp = CalcInput(price_cny=20, weight_g=400, qty=40, tariff_usd_kg=6, sell_price=399000,
                        cny_rate=1750, usd_rate=12500, buyer_pct=10, fx_spread_pct=3, trip_cost=200000,
                        commission_pct=30.5, tax_pct=1, payout_fee_pct=0, ads_pct=10, returns_pct=5,
                        china_ship_cny=30, pack_cost=1500, length_cm=30, width_cm=20, height_cm=15,
                        vol_divisor=6000, uzum_trip_cost=200000, sell_days=45)
        r = calculate(inp)
        self.assertAlmostEqual(r.goods, 36050)
        self.assertAlmostEqual(r.cargo, 112500)
        self.assertAlmostEqual(r.landed, 165006.875)
        self.assertEqual(r.liters, 9)
        self.assertAlmostEqual(r.logistics, 7250)
        self.assertAlmostEqual(r.commission, 121695)
        self.assertAlmostEqual(r.fees, 192785)
        self.assertAlmostEqual(r.profit, 41208.125)
        self.assertEqual(r.storage, 0)

    def test_cargo_by_cubic_meter(self):
        # 40×30×30 = 36 000 sm³ = 0.036 m³ × 700 $ = 25.2 $ > 0.5 kg × 6 $ = 3 $
        r = calculate(CalcInput(price_cny=10, weight_g=500, qty=10, tariff_usd_kg=6, sell_price=200000,
                                cny_rate=1750, usd_rate=12500, length_cm=40, width_cm=30, height_cm=30,
                                vol_divisor=0, cargo_usd_m3=700))
        self.assertTrue(r.cargo_by_m3)
        self.assertAlmostEqual(r.cargo, 0.036 * 700 * 12500)


class RandomizedConsistencyTest(unittest.TestCase):
    def test_breakeven_and_target_are_exact(self):
        rnd = random.Random(42)
        for _ in range(500):
            inp = CalcInput(
                price_cny=rnd.uniform(1, 200), weight_g=rnd.uniform(10, 3000), qty=rnd.randint(1, 500),
                tariff_usd_kg=rnd.uniform(3, 12), sell_price=rnd.uniform(10000, 900000),
                cny_rate=rnd.uniform(1600, 1900), usd_rate=rnd.uniform(11500, 13500),
                commission_pct=rnd.uniform(5, 35), payout_fee_pct=rnd.choice([0, 1, 1.5]),
                uzum_vat_pct=rnd.choice([0, 12]), length_cm=rnd.choice([0, rnd.uniform(5, 80)]),
                width_cm=rnd.uniform(5, 60), height_cm=rnd.uniform(1, 50), sell_days=rnd.uniform(0, 400),
                storage_special=rnd.randint(0, 1), cargo_usd_m3=rnd.choice([0, 700]),
                china_ship_cny=rnd.uniform(0, 50), pack_cost=rnd.uniform(0, 3000),
                uzum_trip_cost=rnd.uniform(0, 300000))
            r = calculate(inp)
            # foyda = sotuv − tannarx − xarajatlar (qismlar yig'indisi)
            parts = (r.goods + r.buyer + r.cargo + r.trip + r.uzum_trip + r.china_ship + r.pack)
            self.assertAlmostEqual(parts, r.landed, places=6)
            fees = r.commission + r.logistics + r.tax + r.payout + r.ads + r.returns + r.storage
            self.assertAlmostEqual(fees, r.fees, places=6)
            self.assertAlmostEqual(inp.sell_price - r.landed - r.fees, r.profit, places=6)
            if r.breakeven_price != float("inf"):
                r0 = calculate(CalcInput(**{**inp.__dict__, "sell_price": r.breakeven_price}))
                self.assertAlmostEqual(r0.profit, 0, delta=0.01)
            if r.target_price != float("inf"):
                rt = calculate(CalcInput(**{**inp.__dict__, "sell_price": r.target_price}))
                self.assertAlmostEqual(rt.margin_pct, inp.target_margin_pct, delta=1e-6)


class BuildInputTest(unittest.TestCase):
    SETTINGS = {"cny_rate": 1750, "usd_rate": 12500, "fx_spread_pct": 3, "buyer_pct": 10, "china_ship_cny": 15,
                "vol_divisor": 6000, "trip_cost": 200000, "olmaliq_pickup_cost": 20000, "uzum_trip_cost": 200000,
                "pack_cost": 1500, "commission_pct": 25, "logistics_fee": 5250, "uzum_vat_pct": 0,
                "payout_fee_pct": 0, "tax_pct": 1, "ads_pct": 10, "returns_pct": 5, "sell_days": 45,
                "target_margin_pct": 20}
    ITEM = {"price_cny": 15, "weight_g": 250, "qty": 50, "sell_price": 129000,
            "length_cm": 30, "width_cm": 20, "height_cm": 15}

    def test_category_commission_and_storage(self):
        cat = TARIFFS.get(13841)  # Soyabonlar
        self.assertEqual(cat["fbo"], 30.5)
        inp = build_input(self.SETTINGS, {**self.ITEM, "tariff_usd_kg": 6}, None, cat, "FBO")
        self.assertEqual(inp.commission_pct, 30.5)
        self.assertEqual(inp.storage_special, 1)
        self.assertEqual(inp.storage_free_days, 60)
        # foydalanuvchi o'zi yozsa — u ustun
        inp2 = build_input(self.SETTINGS, {**self.ITEM, "tariff_usd_kg": 6, "commission_pct": 18}, None, cat)
        self.assertEqual(inp2.commission_pct, 18)

    def test_olmaliq_cargo_cheaper_pickup(self):
        tash = {"id": 1, "name": "T", "mode": "avto", "tariff_usd_kg": 6.0, "days_min": 12, "days_max": 15,
                "olmaliq": 0, "rating": 3, "usd_m3": None, "vol_divisor": None, "pickup_cost": None, "verified": 1}
        olm = {**tash, "id": 2, "name": "O", "olmaliq": 1}
        a = build_input(self.SETTINGS, self.ITEM, tash)
        b = build_input(self.SETTINGS, self.ITEM, olm)
        self.assertEqual(a.trip_cost, 200000)
        self.assertEqual(b.trip_cost, 20000)
        offers = cargo_offers(self.SETTINGS, self.ITEM, [tash, olm])
        self.assertEqual(offers[0]["cargo"]["name"], "O")
        self.assertIn("📍 Olmaliq", offers[0]["badges"])
        self.assertIn("💰 Eng arzon", offers[0]["badges"])


class CargoEligibilityTest(unittest.TestCase):
    """Qo'llanma qoidalari: seriya, minimal vazn, tarifsiz kargo."""
    S = BuildInputTest.SETTINGS
    ITEM = {"price_cny": 15, "weight_g": 250, "qty": 50, "sell_price": 129000,
            "length_cm": 18, "width_cm": 6, "height_cm": 6}

    def cargo(self, **kw):
        base = {"id": 1, "name": "C", "mode": "avto", "tariff_usd_kg": 6.0, "days_min": 10, "days_max": 20,
                "olmaliq": 0, "white_docs": None, "rating": 3, "usd_m3": None, "vol_divisor": None,
                "pickup_cost": None, "verified": 1, "series_ok": 1, "min_kg": None}
        return {**base, **kw}

    def test_rules(self):
        cargos = [
            self.cargo(id=1, name="Avia namuna", mode="avia", tariff_usd_kg=9.1, days_max=7, series_ok=0),
            self.cargo(id=2, name="100kg+", tariff_usd_kg=6.2, min_kg=100),
            self.cargo(id=3, name="Tarifsiz", tariff_usd_kg=0),
            self.cargo(id=4, name="Olmaliq avto", tariff_usd_kg=6.71, olmaliq=1, days_max=25),
            self.cargo(id=5, name="Oq hujjat", tariff_usd_kg=6.0, white_docs=1, days_max=30),
        ]
        offers = cargo_offers(self.S, self.ITEM, cargos)
        ok = {x["cargo"]["name"] for x in offers if x["ok"]}
        bad = {x["cargo"]["name"]: x["reason"] for x in offers if not x["ok"]}
        self.assertEqual(ok, {"Olmaliq avto", "Oq hujjat"})
        self.assertIn("seriya", bad["Avia namuna"])
        self.assertIn("minimal 100 kg (partiya 12.5 kg)", bad["100kg+"])
        self.assertEqual(bad["Tarifsiz"], "tarif kiritilmagan")
        # mos kelganlar oldinda, ball va sabab to'g'ri
        self.assertTrue(offers[0]["ok"] and offers[1]["ok"])
        self.assertEqual(offers[0]["real_days"], offers[0]["days"] + 4)
        # 3 donagacha (namuna) — avia ham mos
        sample = cargo_offers(self.S, {**self.ITEM, "qty": 2}, cargos)
        self.assertTrue(next(x for x in sample if x["cargo"]["name"] == "Avia namuna")["ok"])

    def test_seed_file_is_valid(self):
        from bot.cargo_import import guide_text, load_seed, to_row
        items = load_seed()
        self.assertGreaterEqual(len(items), 18)
        for it in items:
            row = to_row(it, 12500)
            self.assertIn(row["mode"], ("avia", "avto"))
            self.assertGreaterEqual(row["tariff_usd_kg"], 0)
            self.assertIn("series_ok", it)
        mk = next(to_row(i, 12500) for i in items if i["name"] == "MK Express avia")
        self.assertEqual((mk["olmaliq"], mk["series_ok"]), (True, False))
        self.assertIn("MK037", guide_text())


if __name__ == "__main__":
    unittest.main()
