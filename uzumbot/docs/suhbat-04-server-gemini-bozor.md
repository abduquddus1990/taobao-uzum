# 4-suhbat (2026-11-18/19): noutbuk server, Gemini, Uzum bozor tahlili

## Server (ofis noutbuki)
- "UzumBot" vazifasi (S4U, Windows yoqilganda). Uy kompyuteriga ko'chirish — keyinroq (yo'riqnoma suhbatda berildi).
- Muammo: internet uzilganda Cloudflare quick-tunnel manzili o'ladi, cloudflared sezmaydi -> `bot/tunnel.py` watchdog
  (har 60 s tekshiradi, internet bor-u manzil 3 marta javob bermasa — cloudflared qayta, yangi manzil menyuga).
- Muammo: Stop-ScheduledTask faqat supervisor'ni o'ldirardi, run.py osilib port 8088 ni band qilardi ->
  `supervisor.py` Job Object (KILL_ON_JOB_CLOSE): bolalar ham o'ladi. Sinaldi.
- `server/restart_server.ps1` (admin): osilgan eski nusxalarni tozalab, qayta yoqadi.

## Gemini
- `gemini-2.5-flash` yopildi (404). Asosiy: `gemini-3.5-flash`, zaxira zanjiri `FALLBACK_MODELS`.
- Bepul kalit: 3.8-flash kuniga 20 so'rov; Google Search grounding bepulda YO'Q (limit 0).
- 404 -> keyingi model (doimiy), 503/504/429 -> keyingi model (bir martalik). Umumiy vaqt ~75 s
  (Mini App so'rovini Cloudflare 100 s da uzadi -> "Failed to fetch").
- Tarjima: skrinshot qabul qiladi; faqat link yuborilsa — yo'riqnoma (bot Taobao'ni ocha olmaydi).

## Foydalanuvchining asl g'oyasi
Link -> Taobao'da arzon muqobillar + izohlar -> Uzum'dagi o'xshashlar tahlili.
- Taobao: login/bot-himoya, rasmiy API faqat Xitoy kompaniyalariga. Yo'llar: pullik 3-tomon API yoki skrinshot.
- Uzum: saytning ichki API kalitlarini olish ruxsat etilmadi (xavfsizlik). Hozir — skrinshot;
  keyin: Gemini billing + Google Search, yoki rasmiy/pullik manba.

## 📊 Uzum bozor tahlili (`bot/market.py`, `bot/handlers/market.py`, /bozor)
Saqlangan tovar tanlanadi -> Uzum qidiruv natijalari skrinshotlari -> Gemini JSON o'qiydi ->
narx oralig'i, mediana, sotuv bo'yicha o'rtacha narx, top-3, raqobat darajasi, tovarimizning shu narxlardagi
foydasi (bugungi kurs bilan, `calculate` orqali) va xulosa. Testlar: `tests/test_market.py`.
Navbatda: Taobao skrinshot-taqqoslash; Mini App'da bozor tahlili.
