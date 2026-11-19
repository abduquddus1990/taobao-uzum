# Suhbat 03 — Kargo ma'lumotlari va takliflar (2026-11-18)

## So'rov
- `Downloads\uzumbot` dagi loyihamizda yo'q fayllarni ko'chirish; asosiy papkaga kargo qo'llanmasi qo'shilgan.
- Kargo ma'lumotlarini botga kiritish, kargo hisoblari bo'yicha taklif.

## Javoblar (foydalanuvchidan)
1. Uzum xizmatlariga QQS — hozircha 0%. Komissioner hisobotida alohida chiqsa — 12%. YATT uchun QQS to'liq xarajat.
2. Qatnovlar: MK Express Olmaliq filiali MK037 (Oydin bekati orqasi, uyga yetkazish, +998880279515) —
   kargodan olish 0, Uzumga topshirish 200 000. Toshkent kargosida ikkalasi bitta safarda (biri 200 000, biri 0).
3. MK Express narxlari: avia oddiy 114 000 so'm/kg (2–7 kun), brend 156 000; avto pochta 65 880 (15–25 kun);
   avto kargo 83 880, 100 kg dan 78 000 (10–25 kun). Aviada seriya olinmaydi — partiya avto kargoda.

## Topilganlar
- `Downloads\uzumbot` — eski 1-bosqich kodining boshqa nusxasi (boshqa AI qilgan). Undan o'tkazildi:
  `/import_kargo` g'oyasi (nomi bo'yicha yangilash), ⚠️ tarifsiz kargo + chatda ✏️ tarif, "250 18x6x6" kiritish,
  "Kargo bo'yicha savol" AI rejimi. Qolgani bizda ilg'orroq versiyada bor. Papkaning o'zi o'zgartirilmadi.
- `cargos.json` va `kargo_qollanma.md` ning eng yangisi asosiy papkada edi (10:45) → loyihaga ko'chirildi:
  `uzumbot/data_seed/cargos.json`, `uzumbot/docs/kargo_qollanma.md`.

## Qilingan ishlar
- cargos.json ga `series_ok` va `min_kg` qo'shildi (qo'llanmaning 4- va 12-bo'limlaridan), "MK Express avto pochta" qatori qo'shildi (jami 18).
- Kargo takliflari: mos kelmaganlar ajratiladi (partiya olmaydi / minimal kg / tarif yo'q);
  ball = narx 50% + tezlik 20% + sifat 15% + oq hujjat 10% + Olmaliq 5%; muddat +4 kun "real".
- Sozlama standartlari: Toshkent kargosidan olib kelish 0, Olmaliqdan 0, Uzumga topshirish 200 000.
- `/import_kargo`, ilovada 📥; birinchi ishga tushishda avtomatik import.
- AI: «🚚 Kargo bo'yicha savol» — qo'llanma + joriy kargolar ro'yxati.
- Testlar: 23 ta (kargo qoidalari, cargos.json to'g'riligi, import takrorlanmasligi).

## Ochiq
- iPost va Tez Kargo Olmaliq tarifi (0 — kiritilmagan).
- MK037 uyga yetkazish pulli-yo'qligi.
- Kargolarga ★ reyting — birinchi sinov posilkasidan keyin.
