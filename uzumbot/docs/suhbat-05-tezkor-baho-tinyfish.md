# Suhbat 05 — Tezkor baho (link → narx) va TinyFish

**Qaror:** Taobao'dagi tadqiqotni Quddusxon o'zi qiladi (pullik skreperlarsiz). Bot faqat hisoblaydi.

## Nima qo'shildi
- `bot/quote.py` — linkli matnni tahlil qilish (narx, vazn, o'lcham, partiya, #toifa, nom), `make_quote`, hisobot.
- `bot/handlers/quote.py` — link yuborilganda hisob, yetishmasa so'rash, 💾 saqlash, 📊 Uzum narxlari.
- `bot/tinyfish.py` — TinyFish Fetch mijozi (bepul: 1 000 sahifa/kun).
- `gemini.market_listings_text` — Uzum sahifa matnidan narxlar ro'yxatini JSON qilib ajratish.
- `tests/test_quote.py` — 13 ta test.

## Narx qoidalari
- **Minimal narx** = maqsadli marja (sozlamalar, default 20%) beradigan narx. Undan pastga tushmaymiz.
- **Tavsiya narx** = minimal narx …900 ga yuqoriga yaxlitlangan (psixologik narx).
- 3x qoidasi: Uzum narxi ≥ tannarx × 3 → 🟢; ≥2.2 → 🟡; aks holda 🔴.
- Raqobatchi arzon bo'lsa — narxni tushirmaymiz, boshqa tovar yoki boshqa sotuvchi qidiramiz.
