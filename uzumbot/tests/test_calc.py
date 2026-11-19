import unittest

from bot.calc import CalcInput, calculate, fmt, parse_number


class CalcTest(unittest.TestCase):
    def test_mini_zont_example(self):
        # Taqdimotdagi misol: tannarx ~54 000, sotuv 129 000 -> foyda ~22 000
        inp = CalcInput(price_cny=15, weight_g=250, qty=50, tariff_usd_kg=6.7, sell_price=129_000,
                        cny_rate=1750, usd_rate=12500, fx_spread_pct=0)
        r = calculate(inp)
        self.assertAlmostEqual(r.landed, 26250 + 2625 + 20937.5 + 4000, delta=1)
        self.assertAlmostEqual(r.fees, 51690, delta=2)  # ekvayring komissiya ichida
        self.assertGreater(r.profit, 21000)
        self.assertEqual(r.verdict, "EHTIYOT")  # marja ~17%, lekin 3x emas
        # zararsizlik narxida foyda ~0
        r0 = calculate(CalcInput(**{**inp.__dict__, "sell_price": r.breakeven_price}))
        self.assertAlmostEqual(r0.profit, 0, delta=1)
        # maqsadli narxda marja ~20%
        rt = calculate(CalcInput(**{**inp.__dict__, "sell_price": r.target_price}))
        self.assertAlmostEqual(rt.margin_pct, 20, delta=0.05)

    def test_phone_case_loses(self):
        inp = CalcInput(price_cny=5, weight_g=50, qty=200, tariff_usd_kg=6.7, sell_price=28_000,
                        cny_rate=1750, usd_rate=12500)
        self.assertEqual(calculate(inp).verdict, "KIRMAYMIZ")

    def test_volume_weight_and_extras(self):
        base = dict(price_cny=15, weight_g=250, qty=50, tariff_usd_kg=6.7, sell_price=129_000,
                    cny_rate=1750, usd_rate=12500, fx_spread_pct=0)
        r0 = calculate(CalcInput(**base))
        # 30x20x15 sm / 6000 = 1.5 kg > 0.25 kg — kargo hajm bo'yicha olinadi
        r = calculate(CalcInput(**base, length_cm=30, width_cm=20, height_cm=15))
        self.assertAlmostEqual(r.charge_kg, 1.5)
        self.assertAlmostEqual(r.cargo, 1.5 * 6.7 * 12500)
        self.assertLess(r.profit, r0.profit)
        # Xitoy ichki yetkazish partiyaga bo'linadi, qadoq har donaga
        r2 = calculate(CalcInput(**base, china_ship_cny=50, pack_cost=1500))
        self.assertAlmostEqual(r2.landed - r0.landed, 50 * 1750 / 50 + 1500)
        self.assertAlmostEqual(r2.roi_pct, r2.profit / r2.landed * 100)

    def test_old_saved_json_loads(self):
        from bot.calc import input_from_dict
        old = dict(price_cny=15, weight_g=250, qty=50, tariff_usd_kg=6.7, sell_price=129_000,
                   cny_rate=1750, usd_rate=12500, unknown_future_key=1)
        self.assertEqual(input_from_dict(old).pack_cost, 0)

    def test_parse_and_fmt(self):
        self.assertEqual(parse_number("129 000"), 129000)
        self.assertEqual(parse_number("12,5"), 12.5)
        self.assertEqual(parse_number("1.5%"), 1.5)
        self.assertEqual(parse_number("1,234,567"), 1234567)
        with self.assertRaises(ValueError):
            parse_number("abc")
        self.assertEqual(fmt(1234567.4), "1 234 567")


if __name__ == "__main__":
    unittest.main()
