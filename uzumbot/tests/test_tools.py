"""💱 Kurs (cbu.uz) va 📸 Foto studiya testlari."""
import io
import tempfile
import unittest

from PIL import Image

from bot.db import Database
from bot.photo import CARD_SIZE, make_card
from bot.rates import parse_cbu, rates_text, update_rates

CBU = [
    {"id": 69, "Code": "840", "Ccy": "USD", "CcyNm_UZ": "AQSH dollari", "Nominal": "1", "Rate": "12034.56",
     "Diff": "-5.1", "Date": "20.11.2026"},
    {"id": 14, "Code": "156", "Ccy": "CNY", "Nominal": "1", "Rate": "1688.12", "Date": "20.11.2026"},
    {"id": 1, "Ccy": "JPY", "Nominal": "10", "Rate": "780.1"},
]


class RatesTest(unittest.IsolatedAsyncioTestCase):
    def test_parse(self):
        self.assertEqual(parse_cbu(CBU), {"USD": 12034.56, "CNY": 1688.12})
        self.assertEqual(parse_cbu([{"Ccy": "CNY", "Nominal": "10", "Rate": "16881,2"}]), {"CNY": 1688.12})
        self.assertEqual(parse_cbu(None), {})

    async def test_update_and_kurs_text(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Database(f"{tmp.name}/t.db")
        await db.connect()
        self.addAsyncCleanup(db.close)

        async def fake():
            return parse_cbu(CBU)

        changed = await update_rates(db, fake)
        s = await db.get_settings()
        self.assertEqual((s["cny_rate"], s["usd_rate"]), (1688.12, 12034.56))
        self.assertEqual({c[0] for c in changed}, {"CNY", "USD"})
        self.assertEqual(await update_rates(db, fake), [])          # ikkinchi marta — o'zgarish yo'q
        text = rates_text(changed, s)
        self.assertIn("1 ¥ = 1 688.12 so'm", text)
        self.assertIn("+3% konvertatsiya", text)
        self.assertEqual(s["auto_rates"], 1)

    async def test_bad_response(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Database(f"{tmp.name}/t.db")
        await db.connect()
        self.addAsyncCleanup(db.close)

        async def broken():
            raise RuntimeError("cbu.uz ga ulanib bo'lmadi")

        with self.assertRaises(RuntimeError):
            await update_rates(db, broken)
        self.assertEqual((await db.get_settings())["cny_rate"], 1750)   # eski kurs saqlanadi


def _jpeg(w=900, h=600) -> bytes:
    img = Image.new("RGB", (w, h), (200, 30, 30))          # qizil fon
    img.paste((20, 20, 220), (300, 150, 600, 450))          # o'rtada ko'k "tovar"
    b = io.BytesIO()
    img.save(b, "JPEG")
    return b.getvalue()


def fake_remover(img: Image.Image) -> Image.Image:
    """Ko'k qismni qoldirib, qolganini shaffof qiladi (rembg o'rniga)."""
    out = img.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if not (b > 150 and r < 100):
                px[x, y] = (0, 0, 0, 0)
    return out


class PhotoTest(unittest.TestCase):
    def test_card_with_bg_removal(self):
        res = make_card(_jpeg(), remover=fake_remover)
        self.assertTrue(res.bg_removed)
        card = Image.open(io.BytesIO(res.jpg))
        self.assertEqual(card.size, CARD_SIZE)
        self.assertEqual(card.format, "JPEG")
        self.assertGreater(min(card.getpixel((5, 5))), 245)               # burchak — oq
        r, g, b = card.getpixel((CARD_SIZE[0] // 2, CARD_SIZE[1] // 2))
        self.assertTrue(b > 150 and r < 100)                              # markazda tovar
        png = Image.open(io.BytesIO(res.png))
        self.assertEqual(png.mode, "RGBA")
        self.assertEqual(png.size, (300, 300))                            # tovar aniq kesilgan

    def test_card_without_rembg(self):
        res = make_card(_jpeg(), remove_bg=False)
        self.assertFalse(res.bg_removed)
        self.assertIsNone(res.png)
        self.assertEqual(Image.open(io.BytesIO(res.jpg)).size, CARD_SIZE)

    def test_remover_finds_nothing(self):
        res = make_card(_jpeg(), remover=lambda im: Image.new("RGBA", im.size, (0, 0, 0, 0)))
        self.assertFalse(res.bg_removed)


if __name__ == "__main__":
    unittest.main()
