# Suhbat 06 — Foto studiya (rembg) va Markaziy bank kursi

- `bot/photo.py` — rembg (isnet-general-use) bilan fon olish, 1080×1440 oq kartochka, yumshoq soya, shaffof PNG.
  rembg yo'q bo'lsa — faqat kartochkaga moslash. Navbat: bir vaqtda bitta rasm (CPU).
- `bot/rates.py` — cbu.uz JSON (Ccy, Rate, Nominal), har kuni 09:15 + ishga tushganda; 1%+ o'zgarishda xabar.
  Sozlama `auto_rates` (1/0). Rasmiy kursga fx_spread_pct (default 3%) hisobda qo'shiladi.
- `bot/handlers/tools.py` — «📸 Foto studiya» tugmasi, /foto, /kurs.
- Testlar: `tests/test_tools.py` + flow testi. Jami 53 ta.
