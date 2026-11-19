import unittest

from bot.calc import CalcInput, calculate
from bot.market import Listing, _num, merge, parse_listings, profit_at, report, summarize


def inp(**kw):
    base = dict(price_cny=20, weight_g=300, qty=50, tariff_usd_kg=8, sell_price=99_000,
                cny_rate=1750, usd_rate=12_800)
    base.update(kw)
    return CalcInput(**base)


class TestParse(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(_num("89 000 so'm"), 89000)
        self.assertEqual(_num("1.250.000"), 1250000)
        self.assertEqual(_num("4,8"), 4.8)
        self.assertEqual(_num("1000+ buyurtma"), 1000)
        self.assertEqual(_num("2k"), 2000)
        self.assertEqual(_num(None), 0)
        self.assertEqual(_num(35000), 35000)

    def test_json_in_fence(self):
        text = 'Mana:\n```json\n[{"title":"Oyna","price":"89 000 so\'m","old_price":120000,' \
               '"rating":"4.9","reviews":"312","orders":"1000+"},' \
               '{"title":"Bad","price":"12"},{"title":"","price":50000}]\n```'
        items = parse_listings(text)
        self.assertEqual(len(items), 1)                  # 12 so'm va nomsiz tashlanadi
        x = items[0]
        self.assertEqual((x.price, x.old_price, x.rating, x.reviews, x.orders), (89000, 120000, 4.9, 312, 1000))

    def test_garbage(self):
        self.assertEqual(parse_listings("Gemini xatosi: 503"), [])
        self.assertEqual(parse_listings("[not json"), [])
        self.assertEqual(parse_listings('{"a":1}'), [])

    def test_merge_dedup(self):
        a = [Listing("Qo'l oynasi", 89000)]
        b = [Listing("qo'l  oynasi!", 89000), Listing("Taroq", 25000), Listing("Taroq", 25000)]
        self.assertEqual([x.title for x in merge(a, b)], ["Qo'l oynasi", "Taroq"])


class TestSummary(unittest.TestCase):
    def setUp(self):
        self.items = [Listing("A", 50_000, orders=100), Listing("B", 80_000, orders=1000, rating=4.8),
                      Listing("C", 100_000, old_price=150_000), Listing("D", 120_000, orders=0),
                      Listing("E", 200_000, orders=10)]

    def test_stats(self):
        s = summarize(self.items)
        self.assertEqual((s.count, s.min, s.max, s.median), (5, 50_000, 200_000, 100_000))
        self.assertEqual((s.p25, s.p75), (80_000, 120_000))
        self.assertEqual(s.top[0].title, "B")
        self.assertAlmostEqual(s.top_price, (50_000 * 100 + 80_000 * 1000 + 200_000 * 10) / 1110)
        self.assertEqual(s.discounted_share, 20)

    def test_single_and_empty(self):
        s = summarize([Listing("X", 70_000)])
        self.assertEqual((s.p25, s.median, s.p75, s.top_price), (70_000,) * 4)
        self.assertIsNone(summarize([]))

    def test_profit_at_matches_calculate(self):
        i = inp()
        for p in (50_000, 99_000, 150_000):
            self.assertAlmostEqual(profit_at(i, p).profit, calculate(inp(sell_price=p)).profit)
        self.assertEqual(i.sell_price, 99_000)            # asl kiritma o'zgarmaydi

    def test_report_renders(self):
        text = report(self.items, "Oyna <to'plam>", inp())
        self.assertIn("Uzum bozor tahlili", text)
        self.assertIn("&lt;to", text)              # HTML xavfsiz
        self.assertIn("Xulosa", text)
        self.assertIn("Tovarni avval", report(self.items))
        self.assertIn("o'qilmadi", report([]))

    def test_advice_branches(self):
        cheap = inp(price_cny=2, weight_g=60)                        # arzon tannarx — kuchli
        dear = inp(price_cny=400)                         # bozordan qimmat — kirmaymiz
        self.assertIn("🟢", report(self.items, "", cheap).split("Xulosa")[1])
        self.assertIn("🔴", report(self.items, "", dear).split("Xulosa")[1])


if __name__ == "__main__":
    unittest.main()
