# Suhbat 02 — Uzum rasmiy tariflari, kargo taklifi, uy serveri (2026-11-18)

## Javoblar (foydalanuvchidan)
1. Uzum komissiya va logistikani to'liq o'rganib bazaga kiritish; tovar hajmi/vazni bo'yicha aniqlash — manbalarni o'zim topdim.
2. Aylanma solig'i — 1% (tasdiqlandi).
3. Bot kargo variantlarini taklif qilsin: narx, tezlik, sifat + Olmaliqdagi kargo.
4. "GitHub shartmi?" — yo'q, shart emas (pastda).
5. Uy kompyuterini server qilish; hisob xatosiz bo'lishi kerak.

## Manbalar
- seller.uzum.uz/manual/3.tariffs — logistika (01.06.2026), to'lov jadvali, jarimalar.
- seller.uzum.uz/manual/6.product-preparation — saqlash tariflari.
- Rasmiy Google jadval "Комиссионное вознаграждение" (qo'llanmadan havola) — 5 084 toifa, FBO/FBS/DBS, chegirmalar.

## Topilgan muhim faktlar
- **Ekvayring komissiya ichida** — avval 1.5% alohida (ikki marta) hisoblanardi. Olib tashlandi.
- Komissiyalar ko'pchilik toifada **20–25.5%**, soyabonlar 30.5% (avvalgi standart 20% past edi → 25%).
- Logistika: litr = U×E×B(mm)/1 000 000, yuqoriga yaxlitlanadi; 1 l gacha 5 250, +250/l, maks 50 000; o'lchamsiz 50 000. Faqat sotilgandan, qaytsa qaytariladi.
- Saqlash (FBO): aylanma 0–60 kun bepul; 12/18/24 (maxsus 12/14/18) so'm/l/kun; yangi stok 30 (ba'zi toifa 60) kun bepul.
- Pul yechish: 2 haftada/oyda 0%, haftada 1%, har kuni 1.5%.
- QQS komissiyaga kiradimi — qo'llanmada YOZILMAGAN → `uzum_vat_pct` sozlamasi (standart 0), birinchi komissioner hisobotidan tekshirish kerak.
- PDF'dagi mini zont (129 000 so'm) 30.5% komissiya bilan deyarli foydasiz chiqadi.

## Qilingan ishlar
- `bot/uzum_tariffs.py`: jadvalni yuklash/parse, qidiruv (o'zbek/rus), haftalik yangilash, komissiya o'zgarsa xabar; `/tariflar`.
- `calc.py` + `calc.js` qayta yozildi: hajm bo'yicha logistika, saqlash, $/m³ kargo, Uzum omboriga qatnov, Olmaliq olib kelish, pul yechish, QQS ustama.
- Kargo taklifi (chat va ilova): har kargo bilan foyda, ball = 50% narx + 25% tezlik + 25% sifat; Olmaliq punkti olib kelish narxini kamaytiradi.
- Internetdagi kargolar (MK Express Olmaliq MK015, MyEDS, Meest, Transit Pro, Mandarin) — "❔ tasdiqlanmagan" bilan qo'shish tugmasi.
- Server rejimi: `supervisor.py`, `server/setup_server.ps1` (uyqu o'chadi, Windows yonishi bilan ishga tushadi), `remove_server.ps1`.
- Testlar 21 ta: rasmiy misollar, qo'lda hisoblangan to'liq misol, 500 tasodifiy tekshiruv, JS↔Python 304 holat.

## GitHub
Shart emas. Foydasi: kod tarixi va zaxira. Baza zaxirasi har kuni Telegramga keladi, kod papkasini vaqti-vaqti bilan nusxalash yetarli.

## Ochiq savollar
- Uzum xizmatlariga QQS ustiga qo'shiladimi (komissioner hisobotidan).
- Tez Kargo & Silk Road Olmaliq (Metallurglar ko'ch. 5) narxi; MK Express avia narxi.
- Kargodagi minimal vazn va hajm qoidasi (5000/6000 yoki $/m³) — har biridan so'rash.
