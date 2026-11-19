# Uzum–Taobao yordamchi bot — 1.6-bosqich

Bot quyidagilarni qiladi:

- **📱 Mini ilova.** Hammasi bitta chiroyli oynada: jonli kalkulyator, tovarlar, kargolar, AI, sozlamalar. Chap pastdagi «📱 Ilova» tugmasi orqali ochiladi.
- **Tannarx hisoblash — Uzum rasmiy tariflari bilan.** Komissiya 5 084 toifali rasmiy jadvaldan (FBO/FBS), logistika qadoq hajmi (litr) bo'yicha, FBO saqlash, aylanma solig'i 1%, ekvayring komissiya ichida. Xitoy tomoni: narx, konvertatsiya, bayer, ichki yetkazish, kargo (haqiqiy / hajmiy vazn / $ m³ — qaysi biri qimmat), qadoq, qatnovlar. Natija: zararsizlik narxi, maqsadli narx, ROI va xulosa: 🟢 KIRAMIZ, 🟡 EHTIYOT yoki 🔴 KIRMAYMIZ.
- **Kargo taklifi.** Har bir partiya uchun barcha kargolar bilan hisoblab, eng yaxshisini taklif qiladi: 🏆 tavsiya (narx 50% + tezlik 20% + sifat 15% + "oq" hujjat 10% + Olmaliq 5%), 💰 eng arzon, ⚡ eng tez, ⭐ ishonchli (siz 4★+ baholagan), 📄 oq hujjat, 📍 Olmaliq. Mos kelmaganlar sababi bilan alohida: partiya (3+ dona) olmaydigan (masalan, MK Express avia), minimal vazndan kam (MK 100 kg+, Sellmate ekspress 200 kg), tarifi kiritilmagan. Muddat qo'llanma bo'yicha +4 kun zaxira bilan ("real ~").
- **Kargo bilimlari.** `data_seed/cargos.json` — 18 ta tarif (manba va sana bilan), `docs/kargo_qollanma.md` — batafsil qo'llanma. AI → «🚚 Kargo bo'yicha savol» shu ikkisiga tayanib javob beradi.
- **Tariflar o'zi yangilanadi.** Haftada bir marta Uzum jadvali yuklanadi; tovarlaringiz toifasida komissiya o'zgarsa, xabar keladi. Qo'lda: `/tariflar`.
- **Tovarlarim.** Saqlangan hisoblar linklari bilan. Har biri holatga ega: 💡 G'oya → 🧪 Namuna → 📦 Partiya → 🚚 Yo'lda → 🛒 Sotuvda (yoki ⛔ To'xtatildi). Bugungi kurs bilan foyda qanchaga o'zgarganini ham ko'rsatadi.
- **Byudjet.** $1 000 dan qanchasi tovarda turganini ko'rsatadi.
- **Kargolar.** Tarif, muddat, "oq" hujjat, Olmaliqda punkti bormi.
- **Sozlamalar.** Kurslar, komissiya, qatnov, qadoq, reklama, brak va boshqa foizlar.
- **AI yordamchi (Gemini).** Xitoycha → o'zbekcha tarjima, sotuvchiga xitoycha xabar, Uzum kartochka matni.
- **Bir-biringizga xabar.** Gulim yangi tovar saqlasa yoki holatini o'zgartirsa, Quddusxonga xabar keladi (va aksincha).
- **Kunlik zaxira nusxa.** Har kuni 23:00 da baza fayli Telegramga yuboriladi.
- **Elektr nazorati.** Kompyuter o'chsa, healthchecks.io orqali xabar keladi.
- **Yopiq kirish.** Botdan faqat ikki admin foydalanadi.

---

## 1. Kerakli dasturlar (bir marta o'rnatiladi)

1. **Python 3.11+** — https://www.python.org/downloads/ (o'rnatishda **"Add Python to PATH"**).
2. **VS Code** + **Python** kengaytmasi.
3. **cloudflared** — Mini ilova uchun (bu kompyuterda allaqachon o'rnatilgan). Boshqa kompyuterda:
   ```
   winget install --id Cloudflare.cloudflared
   ```

## 2. Loyihani ochish

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

## 3. `.env` fayli

`.env.example` ni nusxalab, nomini `.env` qiling va to'ldiring:

```
BOT_TOKEN=...                                   # @BotFather dan
ADMINS=359795989:Quddusxon,660673338:Gulim      # birinchisi — asosiy ega
GEMINI_API_KEY=...                              # ixtiyoriy
```

**`.env` ni hech kimga yubormang va GitHub'ga yuklamang.** `.gitignore` uni chiqarib tashlaydi.

Adminlar ismi har ishga tushganda `.env` dan olinadi — ismni o'zgartirmoqchi bo'lsangiz, shu yerda o'zgartiring.

## 4. Ishga tushirish

```bash
python run.py
```

Bot ishga tushgach:
1. Mini ilova uchun HTTPS manzil oladi (cloudflared, ~10–20 soniya).
2. Ikkalangizning chatingizda chap pastdagi tugmani «📱 Ilova» ga aylantiradi.
3. Quddusxonga «✅ Bot ishga tushdi» xabarini yuboradi.

To'xtatish: terminalda `Ctrl + C`.

## 5. Birinchi sozlash

1. Ilovani oching → ⚙️ (yoki yuqoridagi ¥/$ kursiga bosing) → bugungi kursni kiriting.
2. **🚚 Kargo** bo'limi → «➕ Kargo qo'shish».
3. **🧮 Hisob** — birinchi tovarni hisoblang.

Gulim botga birinchi marta `/start` yozishi kerak — shundan keyin unga ham xabarlar va «Ilova» tugmasi keladi.

## 5a. Kargolar ro'yxati (cargos.json)

- Bot birinchi ishga tushganda `data_seed/cargos.json` dagi 18 ta tarifni o'zi yuklaydi.
- Narx o'zgarsa: faylni VS Code'da tahrirlang (`checked_at` sanasini ham), keyin botga `/import_kargo` yozing yoki ilovada 🚚 Kargo → «📥 Kargolar ro'yxatini yangilash». Bir xil nomli kargo takrorlanmaydi; siz qo'ygan ★ reyting va qo'lda kiritilgan tarif saqlanadi.
- So'mdagi tarif (`tariff_uzs_kg`) import paytida sozlamadagi dollar kursi bo'yicha $/kg ga o'giriladi.
- ⚠️ tarifi 0 bo'lganlar (iPost, Tez Kargo Olmaliq) — kargodan narx olib, chatda ✏️ yoki ilovada kiriting.
- Maydonlar: `series_ok` — partiya (3+ bir xil dona) oladimi; `min_kg` — minimal yuk; `white_docs`/`olmaliq` — `true`/`false`/`null` (noma'lum).

**Qatnovlar:** Toshkent kargosidan olish Uzum omboriga topshirish safari bilan birga qilinadi — shuning uchun "Toshkent kargosidan olib kelish" = 0, "Uzum omboriga topshirish" = 200 000 so'm. MK Express Olmaliq filiali (MK037) uyga yetkazadi — "Olmaliq punktidan olib kelish" = 0 (pullik bo'lsa, sozlamada o'zgartiring).

## 6. Gemini (AI yordamchi)

1. https://aistudio.google.com/apikey dan kalit oling, `.env` ga `GEMINI_API_KEY=...` yozing.
2. Botni qayta ishga tushiring.

Bepul tarifdagi so'rovlarni Google o'z modellarini yaxshilash uchun ishlatishi mumkin — AI'ga maxfiy ma'lumot yubormang.

## 7. Elektr o'chganda xabar (healthchecks.io)

1. https://healthchecks.io → **Add Check**: Period 5 daqiqa, Grace 5 daqiqa.
2. **Integrations** → Telegram.
3. Ping manzilini `.env` ga: `HEALTHCHECK_URL=https://hc-ping.com/...`

**Muhim:** bitta tokenda bir vaqtda faqat bitta bot ishlashi kerak (zaxira noutbukni asosiysi o'chganda yoqing).

## 8. Zaxira nusxa va tiklash

- Har kuni `BACKUP_HOUR` (standart 23:00, Toshkent) da `uzumbot_YYYY-MM-DD.db` fayli asosiy egaga keladi. Qo'lda: `/backup`.
- **Tiklash:** botni to'xtating → faylni `data\bot.db` nomi bilan joyiga qo'ying → `python run.py`.

## 9. Mini ilova qanday ishlaydi

```
Telefon (Telegram) ──HTTPS──> xxxx.trycloudflare.com ──tunnel──> sizning kompyuter :8088 ──> bot + baza
```

- Server kerak emas: kompyuter o'zi server, cloudflared bepul HTTPS beradi (akkaunt/domen shart emas).
- Manzil har ishga tushganda o'zgaradi — bot uni menyu tugmasiga **o'zi** yozadi. Eski xabarlardagi «Ilova» tugmasi ishlamay qolsa, pastdagi menyu tugmasidan yoki `/app` dan oching.
- Xavfsizlik: har bir so'rov Telegram imzosi bilan tekshiriladi. Manzilni bilgan begona odam hech narsa ko'ra olmaydi.
- O'z domeningiz bo'lsa (yoki keyin VPS'ga ko'chsangiz): `.env` ga `WEBAPP_URL=https://...` yozing — tunnel ishlatilmaydi.

## 10. Uy kompyuterini server qilish

1. `.env` to'ldirilgan va `python run.py` bir marta qo'lda ishlab ko'rilgan bo'lsin (keyin `Ctrl + C`).
2. PowerShell'ni **Administrator** sifatida oching:
   ```
   cd C:\Users\Surface\Taobao-Uzum\uzumbot
   powershell -ExecutionPolicy Bypass -File server\setup_server.ps1
   ```
   Bu: kompyuter rozetkada uxlamaydigan qiladi va "UzumBot" vazifasini yaratadi — Windows yonishi bilan (hech kim kirmasa ham) bot yashirin ishga tushadi, qulasa `supervisor.py` qayta yoqadi.
3. Qo'lda (bir marta):
   - **BIOS/UEFI** → "Restore on AC Power Loss" = **Power On** — elektr kelganda kompyuter o'zi yonadi.
   - **Windows Update** → faol soatlar: qayta yuklash tunda bo'lsin (bot o'zi qayta yonadi).
   - **UPS (ИБП)** router va kompyuterga — qisqa o'chishlarda bot to'xtamaydi.
   - **healthchecks.io** (7-bo'lim) — uzoq o'chsa, telefoningizga xabar keladi.
4. Loglar: `data\bot.log`, `data\supervisor.log`. Bekor qilish: `server\remove_server.ps1`.

Muhim: noutbuk qopqog'i yopilganda uxlamasligi uchun — Boshqaruv paneli → Quvvat → "Qopqoq yopilganda: hech narsa qilmaslik".

## 11. Testlar

```bash
python -m unittest discover -s tests -t .
```

Kalkulyator, botning to'liq dialogi, Mini App API (imzo, ruxsatlar) va JS kalkulyatori Python bilan bir xil natija berishi tekshiriladi (oxirgisi uchun Node.js kerak).

## Papka tuzilishi

```
uzumbot/
├── run.py              # ishga tushirish
├── supervisor.py       # qulasa qayta yoqadi (server rejimi)
├── server/             # Windows avtomatik ishga tushirish skriptlari
├── .env                # maxfiy kalitlar (GitHub'ga yuklanmaydi)
├── bot/
│   ├── calc.py         # tannarx formulalari (Uzum qoidalari izohlarda)
│   ├── uzum_tariffs.py # Uzum rasmiy komissiya jadvali, yangilash
│   ├── uzum_data/      # jadvalning saqlangan nusxasi (5 084 toifa)
│   ├── cargo_import.py # cargos.json -> baza, AI uchun kargo konteksti
│   ├── service.py      # chat va ilova uchun umumiy mantiq
│   ├── db.py           # SQLite baza, sozlamalar, holatlar
│   ├── webapp.py       # Mini ilova serveri (API)
│   ├── tunnel.py       # cloudflared HTTPS tunnel
│   ├── backup.py       # kunlik zaxira
│   ├── render.py       # chatdagi hisobot ko'rinishi
│   ├── gemini.py       # AI
│   ├── heartbeat.py    # elektr/internet nazorati
│   └── handlers/       # chat menyulari
├── webapp/             # Mini ilova (HTML, CSS, JS)
├── data_seed/cargos.json # kargo tariflari (o'zingiz yangilaysiz)
├── docs/kargo_qollanma.md # kargo qo'llanmasi (AI shunga tayanadi)
├── data/bot.db         # baza (avtomatik yaratiladi)
└── tests/
```

## Keyingi bosqichlar

2. Xarid moduli (davomi): sotuvchilar, namunalar natijasi, trek raqamlari, kargo kechikishi signali.
3. Raqobatchi monitoringi, Uzum Seller API: qoldiq kam, pul tushdi signallari.
4. Foto studiya: fonni olib tashlash va shablon fonlar.
5. Instagram/Telegram kontent rejasi.
