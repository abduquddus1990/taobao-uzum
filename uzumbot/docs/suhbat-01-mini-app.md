# Suhbat 01 — Loyihani o'rganish va Mini App (2026-11-18)

## So'rov
- Loyiha fayllarini (PDF taqdimot, 1-bosqich kodi) o'rganish, tushunganini yozish.
- Esdan chiqqan nozik masalalarni topish.
- Botni davom ettirish; "server o'rniga GitHub bo'ladimi?"
- 2 kishilik sodda, yorqin, kreativ Mini App.
- Adminlar: 359795989 (Quddusxon), 660673338 (ayoli — botda "Gulim").

## Qarorlar
- **GitHub server emas.** Actions 24/7 bot uchun mo'ljallanmagan (6 soatlik limit, qoidalarga zid). GitHub — kod va tarix uchun (private repo).
- **Server o'rniga:** uy kompyuteri + cloudflared quick tunnel (bepul HTTPS, domen kerak emas). Bot manzilni menyu tugmasiga o'zi yozadi.
- Ikkala admin teng huquqli (`owner`). Ismlar `.env` → `ADMINS` dan.
- Hisobga qo'shildi: hajmiy vazn, Xitoy ichki yetkazish, qadoq/shtrix-kod, ROI. Eski hisoblar o'zgarmaydi (yangi maydonlar standart 0).
- Tovar holatlari: g'oya → namuna → partiya → yo'lda → sotuvda / to'xtatildi; byudjet ($1000) shu holatlardan hisoblanadi.
- Kunlik zaxira nusxa Telegramga; o'chirishdan oldin tasdiqlash.
- AI: "sotuvchiga xitoycha xabar" rejimi qo'shildi.

## Topilgan xavf
- `.env.example` ichida haqiqiy BOT_TOKEN va GEMINI_API_KEY turgan edi → `.env` ga ko'chirildi, namuna tozalandi. Tokenlarni yangilash tavsiya etildi.

## Ochiq savollar
- Uzum komissiyasi toifalar bo'yicha; logistika yig'imi o'lchamga bog'liq — aniq jadval kerak.
- Aylanma solig'i 1% — buxgalter bilan tasdiqlash.
- Kargo hajmiy vazn bo'luvchisi (5000/6000) va minimal vazn — kargodan so'rash.
