# Kargo qo'llanmasi: Xitoy → O'zbekiston (2026-yil noyabr)

> Bu fayl botning "🚚 Kargo bo'yicha savol" funksiyasi uchun bilimlar bazasi. Narxlar tez o'zgaradi: har bir raqam yonida manba va tekshirilgan sana bor. Oyda bir marta yangilab turing.

---

## 1. Kargo qanday ishlaydi

1. Ro'yxatdan o'tasan va shaxsiy kod olasan. Kargo senga **Xitoydagi omborining manzilini** beradi (Guanchjou, Iu, Sian va boshqalar).
2. Taobao/1688 da buyurtma berganda yetkazish manzili sifatida shu omborni yozasan. Ism o'rniga shaxsiy kodingni qo'yasan.
3. Xitoy ichidagi yetkazish 1–4 kun davom etadi. Ombor posilkani qabul qiladi, tortadi va trekni tizimga kiritadi.
4. Kerak bo'lsa ombor qo'shimcha xizmatlarni bajaradi: bir nechta posilkani birlashtirish (konsolidatsiya), qayta qadoqlash, tekshiruv, foto.
5. Yuk reysga (avia) yoki mashinaga (avto) yuklanadi.
6. Yuk O'zbekiston bojxonasidan o'tadi, keyin Toshkentdagi omborga yoki viloyat punktiga keladi.
7. To'lov kargoga qarab oldindan yoki yuk kelganda qilinadi. Shundan keyin yukni olib ketasan.

---

## 2. Narx nimalardan tashkil topadi

**To'liq kargo xarajati** = tarif × hisoblangan vazn + quyidagi qo'shimchalar:

| Xarajat | Odatdagi narx (misollar) |
|---|---|
| Asosiy tarif | $4.5–13/kg (yo'nalish va tovar turiga qarab) |
| Tovar turi ustamasi | brend, seriya, batareya, suyuqlik |
| Qadoqlash | Green Post: $0.4/kg |
| Konsolidatsiya | Green Post: $0.2/kg; Globbing: $2 |
| Tekshiruv | Green Post: $0.5/kg; Yumecs: $5 |
| Foto-hisobot | Green Post: $1/lot; Yumecs: $1; Globbing: $2–5 |
| Sug'urta | Meest: $100 gacha tekin, undan yuqorisi uchun ortiqcha qismning 2.5% |
| Saqlash | Mandarin: Xitoyda 7 kun tekin; Yumecs: 14 kun tekin, keyin $1/kun; Transit Pro: Toshkentda 3 kundan keyin 500 so'm/kg/kun |
| O'zbekiston ichida yetkazish | ko'pincha tarifga kiradi, ayrimlarida alohida |
| Bayer (sotib olish) xizmati | 3–10% (Sellmate 3%, minimal summa $3 000; Transit Pro 10%) |
| To'lov va konvertatsiya | karta va valyuta farqi 1–4% |

**Qoida:** kargoning e'lon qilgan kg narxini emas, **bitta donaga tushadigan to'liq kargo xarajatini** solishtir. Bot buni avtomatik hisoblaydi.

---

## 3. Vazn: haqiqiy va hajmiy

Kargo ikki xil vaznni hisoblaydi va **ulardan kattasini** oladi:

- **Haqiqiy vazn** — tarozida ko'rsatgan vazn.
- **Hajmiy vazn** — qutining o'lchamidan hisoblanadi. Yengil, lekin katta joy egallaydigan tovar (yostiq, plastik idish, o'yinchoq) uchun shu muhim bo'ladi.

**Formulalar:**
- iPost (va ko'p avia kargolar): **Uzunlik × Eni × Balandligi (sm) ÷ 6000**. Hisoblangan vazn — haqiqiy va hajmiy vazndan kattasi.
- Kuryer va ekspress xizmatlari ko'pincha **÷ 5000** ishlatadi (masalan, EMU Express). Bunda hajmiy vazn kattaroq chiqadi.
- Meest'da yumshoqroq qoida: hajmiy vazn haqiqiysidan 2 marta katta bo'lsa, hisoblangan vazn = (hajmiy − haqiqiy) ÷ 2 + haqiqiy.
- Kichik posilkalarda yaxlitlash bor: Jana Post vaznni keyingi 100 grammgacha yaxlitlaydi (85 g → 100 g, 158 g → 200 g).
- Konteyner va katta yuklar kub metr (m³) bilan hisoblanadi: **CBM = U × E × B (sm) ÷ 1 000 000**. Masalan, Green Post Cargo Container — $100/m³ dan.

**Misol: 50 ta mini zont**
- Bitta zont: 250 g, qutisi 18 × 6 × 6 sm.
- 50 tasi bitta qutida taxminan 40 × 30 × 25 sm = 30 000 sm³.
- Hajmiy vazn (÷6000) = 5 kg, haqiqiy vazn = 12.5 kg. Haqiqiy vazn katta, demak **12.5 kg** uchun to'laysan.
- Xuddi shu qutida 50 ta yengil yostiq bo'lsa: haqiqiy vazn 5 kg, hajmiy esa 15 kg bo'lishi mumkin. Bu holda **15 kg** uchun to'laysan.

**Tejash usullari:**
- Sotuvchidan qalin, ammo kichik qadoqlashni so'ra: 请用小一点的箱子 ("kichikroq quti ishlating").
- Bir nechta posilkani bitta qutiga birlashtir (konsolidatsiya).
- Ortiqcha karton va ichki qutilarni olib tashlat. Lekin sinadigan tovarda buni qilma.

---

## 4. Tovar turi bo'yicha tariflar — bu juda muhim

Ko'p kargo **bir xil tovardan 3 donadan ko'p** bo'lsa, uni "seriya" yoki "tijorat" deb hisoblaydi va qimmatroq tarif qo'llaydi:

- **Mandarin:** standart $9.5/kg, brend $11/kg, seriya/tijorat $12/kg. Seriya tarifi 3 tadan ortiq bir xil tovarga, batareyali elektronikaga va kosmetikaga qo'llanadi.
- **Yumecs:** 3 tadan ortiq bir xil tovar tijorat hisoblanadi, $12/kg dan. Ustamalar: dori $3, atir $9.99, batareya yoki simsiz qurilma $20.
- **MK Express avto pochta:** brend buyumlar $6.99/kg. Bu yo'nalishda seriya tovar olinmaydi.
- **Green Post:** Cargo Commerce (tijorat) $8/kg dan. Batareya, suyuqlik yoki kukun bo'lsa +$2/kg.

**Xulosa:** biz partiya olamiz, ya'ni bizning yuk **doim tijorat yuki** bo'ladi. Tannarxni "standart $9.5" tarifida emas, **tijorat tarifida** hisobla. Namuna (1–2 dona) uchungina standart tarif ishlaydi.

**Brend tarifi** asl brendlar uchun (Nike, Apple va boshqalar). Taobao'dagi arzon "brend" ko'pincha kontrafakt bo'ladi. Uni Uzumda sotish taqiqlangan, bunday tovar olmaymiz.

---

## 5. Yo'nalishlar va muddatlar

| Yo'nalish | Muddat | Kimga mos |
|---|---|---|
| Avia (Toshkent aeroporti) | 3–8 kun; ayrim kargolarda haftada 2 reys (seshanba va juma) | namuna, shoshilinch, qimmat va yengil tovar |
| Avto kargo (Qashg'ar–Irkeshtam–O'sh–Andijon yoki Xorgos–Qozog'iston) | 10–30 kun | partiyalar, og'ir tovar |
| Konteyner / temir yo'l | 20–30+ kun | 100 kg dan katta bir turdagi yuk |

**Kechikish sabablari:**
- Xitoy Yangi yili: 2027-yil 6-fevral, uzilish 4–6 hafta.
- Chegaradagi navbat va tekshiruvlar.
- Bojxona so'rovlari: hujjat yetishmasa, yuk to'xtab qoladi.
- 11.11 va 12.12 chegirmalaridan keyin omborlar tirband bo'ladi.

**Muddat bo'yicha qoida:** kargo aytgan muddatning **yuqori chegarasini** ol va ustiga yana 3–5 kun qo'sh.

---

## 6. Sifat, sug'urta va kafolatlar

**Nimani so'rash kerak:**
1. **Sug'urta nimani qoplaydi va qancha?** "Sug'urta tarifga kiritilgan" degan gap hech narsa demaydi. Limit va shartlarini **yozma** so'ra. Yaxshi namuna: Meest'da $100 gacha sug'urta tarifga kiradi, $100–500 uchun ortiqcha qismning 2.5% olinadi. Masalan, $400 lik posilka uchun (400 − 100) × 0.025 = $7.5.
2. **Yo'qolgan yuk uchun kompensatsiya:** tovar qiymati to'liq qaytariladimi yoki faqat kg narxi? Muddati qancha?
3. **Shikastlangan yuk:** da'voni necha kun ichida berish kerak, qanday dalil talab qilinadi?
4. **Vazn bo'yicha nizo:** Xitoydagi omborning tarozi fotosi beriladimi? (Meest'da vaznni tekshirish tekin.)
5. **Tekshiruv (验货):** qanday darajada — qutini ochib sanaydimi yoki faqat tashqi ko'rinish? Narxi qancha?

**O'zingni himoya qilish:**
- Yukni olishda qutini **videoga olib** och, toki video uzilmasin.
- Ombordagi vazn bilan o'zing olgan vaznni solishtir. 5% dan katta farq bo'lsa, da'vo qil.
- Qimmat va sinadigan tovarni qo'shimcha qadoqlat: burchak himoyasi, yog'och karkas.
- Barcha chek, trek va yozishmalarni saqla. Bot ularni xaridga biriktiradi.

---

## 7. Hujjatlar: "oq" va "kulrang" kargo

- **Kulrang kargo:** arzon, lekin hujjatsiz. Tovar shaxsiy posilka sifatida yoki kargoning o'z nomidan o'tadi, senda tovarning kelib chiqishini isbotlovchi hujjat qolmaydi.
- **"Oq" kargo:** tijorat hisob-fakturasi (invoys), bojxona deklaratsiyasi (GTD), kerak bo'lsa sertifikat beriladi. Importchi tomonidan senga EHF (elektron hisob-faktura) chiqariladi.
- **Bizga "oq" kerak.** Sababi:
  - Uzum va soliq tekshiruvida tovarning kelib chiqishini isbotlash;
  - 1% aylanma solig'i rejimini saqlab qolish (importni importchi kompaniya qiladi, biz ichki xarid qilamiz);
  - markirovka talab qilinadigan toifalar uchun.
- "Oq" xizmat beradigan kompaniyalar: TAK! (invoys, GTD, sertifikatlar, import 18 kungacha), Meest (tijorat avto kargo, bojxona rasmiylashtiruvi bilan), Transit Pro ($3–6/kg bojxona rasmiylashtiruvi bilan, YATT uchun tijorat yuklari 10 kg dan). Boshqalardan ham yozma so'ra.

---

## 8. To'lov

- **Oldindan yoki kelganda:**
  - Mandarin'da yuk kelganda to'lanadi. Bu xaridor uchun xavfsizroq.
  - Ba'zi kargolar oldindan to'lovni talab qiladi. Bunday holda kompaniyani tekshir: ofisi, shartnomasi, sharhlari.
- **To'lov usullari:** Click, Payme, Uzum, Uzcard, Humo, NBU, Alipay (Mandarin misolida).
- **Kurs:** tarif $ da, to'lov so'mda. Qaysi kurs ishlatilishini so'ra (MB kursimi yoki kargoning o'z kursimi). Farq 1–3% bo'lishi mumkin.

---

## 9. Taqiqlangan va cheklangan tovarlar

- **Odatda taqiqlangan:** qurol, portlovchi moddalar, giyohvand moddalar, noqonuniy dorilar, radioaktiv materiallar, hayvonlar, tez buziladigan oziq-ovqat. Mandarin bularga qo'shimcha ravishda naqshli matolarni ham sanaydi.
- **Cheklangan (ustama yoki faqat ayrim yo'nalishda):**
  - litiy batareyalar (aviada qattiq cheklangan; Green Post Avto Pochta qabul qiladi);
  - suyuqliklar, kukunlar, atir va lak (yonuvchan);
  - magnitlar, kosmetika.
- **Bojxona tomonidan:** markirovka talab qilinadigan tovarlar (maishiy texnika, akkumulyatorlar va boshqalar), sertifikat kerak bo'lganlar (bolalar tovarlari, kosmetika, elektronika).

**Qoida:** shubha bo'lsa, buyurtmadan **oldin** kargodan yozma so'ra.

---

## 10. Kargo tanlash cheklisti (15 ta savol)

1. Xitoydagi ombor qayerda va manzil qanday yoziladi?
2. Tijorat/seriya tarifi qancha? "Seriya" necha donadan boshlanadi?
3. Hajmiy vazn formulasi qanday (÷5000, ÷6000 yoki boshqa)?
4. Minimal vazn va yaxlitlash qoidasi qanday?
5. Qadoqlash, konsolidatsiya, tekshiruv va foto narxi qancha?
6. Sug'urta: limiti, foizi, yo'qolganda kompensatsiya qanday?
7. "Oq" hujjat (invoys, GTD) va EHF beriladimi? Qancha turadi?
8. Haqiqiy muddat qancha? Oxirgi 3 ta reys qancha vaqtda kelgan?
9. Trek kuzatuvi bormi (sayt, bot)?
10. To'lov oldindanmi yoki kelgandami? Qaysi kurs bo'yicha?
11. Xitoyda va Toshkentda necha kun tekin saqlanadi?
12. Olmaliqda punkt bormi? Viloyatga yetkazish narxi qancha?
13. Batareya, suyuqlik, magnit qabul qilinadimi?
14. Rasmiy shartnoma yoki oferta bormi? Kompaniya ro'yxatdan o'tganmi (STIR)?
15. Da'vo tartibi qanday va javob qancha vaqtda beriladi?

---

## 11. Qizil bayroqlar (firibgarlik belgilari)

- Faqat Telegram akkaunti bor, ofis, sayt, STIR va shartnoma yo'q.
- Bozordan ancha past narx: masalan, "avia $3/kg".
- 100% oldindan to'lov, ayniqsa shaxsiy kartaga.
- Trek raqami yo'q yoki bermaydi.
- Sug'urta va da'vo haqidagi savolga noaniq javob beradi.
- OLX'dagi e'lonlar ("kubi $90" va hokazo) **tekshiriladigan nomzod**, tayyor tanlov emas.

**Birinchi ish:** yangi kargoni avval kichik namuna posilkasi bilan sina. Bot natijani kargo reytingiga yozadi.

---

## 12. Taniqli kargo xizmatlari

To'liq raqamlar `data_seed/cargos.json` faylida. Bot ularni `/import_kargo` buyrug'i bilan yuklaydi.

### Mandarin Cargo (faqat avia)
- **Tarif:** standart $9.5/kg, brend $11/kg, seriya/tijorat $12/kg. Muddat 3–7 kun.
- **Afzalliklari:**
  - to'lov yuk kelganda;
  - to'lov usullari ko'p (Click, Payme, Uzum, Uzcard, Humo, NBU, Alipay);
  - Xitoyda 7 kun tekin saqlash;
  - minimal to'lov yo'q;
  - sug'urta tarifga kiritilgan;
  - Sian (Shensi) shahrida o'z ombori.
- **Kamchiliklari:**
  - avto yo'nalishi yo'q;
  - partiya uchun qimmat ($12/kg);
  - ofis faqat Toshkentda (Chilonzor, Arnasoy 5A), viloyatlarga pochta orqali;
  - sug'urta limiti ko'rsatilmagan.

### MK Express
- **Tarif (2026-11-18):**
  - aviapochta, oddiy mahsulot: 114 000 so'm/kg, 2–7 kun;
  - aviapochta, brend: 156 000 so'm/kg;
  - avto pochta: 65 880 so'm/kg, 15–25 kun;
  - avto kargo: 83 880 so'm/kg, 100 kg dan 78 000 so'm/kg, 10–25 kun.
- **Muhim:** aviapochtada seriya (bir xil tovar partiyasi) **olinmaydi**, partiya uchun avto kargo kerak. Katta yuklar narxi kelishiladi.
- **Olmaliq:** MK037 filiali — Oydin bekati orqasi, uyga yetkazish bilan; tel. +998 88 027 95 15. Yaqin filiallar: Chirchiq (MK010), Yangiyo'l (MK028).
- **Afzalliklari:** 37 ta filial, shu jumladan Olmaliq; Taobao, 1688 va Pinduoduo'ni qo'llab-quvvatlaydi; narxlari va kalkulyatori saytda ochiq; ilovasi bor.
- **Kamchiliklari:**
  - tarif so'mda belgilangan;
  - sug'urta va "oq" hujjat shartlari saytda yozilmagan, so'rash kerak;
  - Olmaliqdagi uyga yetkazishning narxi va muddatini aniqlash kerak.
- **Aloqa:** +998 88 188 95 15, Telegram: @mk_express_admin

### iPost
- **Tarif:** avia 3–7 kun, avto 12–15 kun. Narx saytdagi kalkulyatorda.
- **Afzalliklari:**
  - 800+ olib ketish punkti, 14 hudud (Olmaliq bo'lishi ehtimoli yuqori);
  - bojxona deklaratsiyasini qiladi;
  - ilovasi bor;
  - hajmiy vazn formulasi ochiq (÷6000).
- **Kamchiliklari:** kg narxi saytda ochiq yozilmagan, kalkulyator orqali ko'rish kerak.

### Sellmate
- **Tarif:** standart $4.5/kg, 30 kun; ekspress $6/kg, 12–17 kun (minimal 200 kg).
- **Afzalliklari:** eng arzon avto tarif; xarid, konsolidatsiya va sug'urta xizmati bor.
- **Kamchiliklari:**
  - standart tarifda muddat uzun (30 kun);
  - bayer xizmati (3%) faqat $3 000 dan yuqori xaridga;
  - ekspress uchun 200 kg minimal.

### Meest China
- **Tarif:** avia $10/kg dan, 8 kundan; reys haftada 2 marta (seshanba, juma). Tijorat avto 30 kg dan, bojxona rasmiylashtiruvi bilan.
- **Afzalliklari:**
  - sug'urta qoidasi ochiq ($100 gacha tekin, undan yuqorisi 2.5%);
  - vazn tekshiruvi tekin;
  - hajmiy vazn qoidasi yumshoq;
  - tovar qidirish xizmati;
  - xalqaro tarmoq.
- **Kamchiliklari:** avia sekinroq (8 kundan); konsolidatsiya, qayta qadoqlash, sifat nazorati va foto-hisobot alohida pullik.

### Green Post
- **Tarif:**
  - Avia Pochta: $9.5/kg, 3–7 kun (seshanba, juma), faqat standart tovar;
  - Avia TK/SG: $13/kg, 5–10 kun;
  - Avto Pochta: $5.5/kg, 20–30 kun (shanba), batareya, suyuqlik va kukunni ham qabul qiladi;
  - Cargo Commerce: $8/kg dan, 20–30 kun, tijorat yuklari uchun; batareya, suyuqlik, kukun +$2/kg;
  - Cargo Container: $100/m³ dan, 100 kg dan ortiq bir turdagi yuk.
- **Afzalliklari:**
  - tariflar juda batafsil;
  - tijorat va konteyner yo'nalishlari bor;
  - qo'shimcha xizmatlar narxi ochiq.
- **Kamchiliklari:** avto muddati uzun (20–30 kun); qo'shimcha xizmatlar qo'shilsa, narx sezilarli oshadi.

### Jana Post
- **Tarif:** $0.61 / 100 g, vazn 100 grammgacha yaxlitlanadi. Barcha posilkalar uchun bitta tarif.
- **Afzalliklari:** kichik va yengil namunalar uchun qulay; Pinduoduo, Taobao va 1688 uchun mo'ljallangan.
- **Kamchiliklari:**
  - Qozog'iston kompaniyasi, O'zbekistonda 2024-yildan;
  - Toshkentda 5 ta punkt;
  - partiyalar uchun mos emas: $6.1/kg.

### Yumecs
- **Tarif:** Xitoydan $8.5–10/kg; tijorat yuki (3 tadan ortiq bir xil tovar) $12/kg dan.
- **Afzalliklari:** 14 kun tekin saqlash; ko'p mamlakatlardan yetkazadi.
- **Kamchiliklari:** ustamalar yuqori (batareya yoki simsiz qurilma +$20, atir +$9.99); tekshiruv $5; tezkor bojxona rasmiylashtiruvi $10.

### Express Delivery (expresscargo.uz)
- **Tarif:** 50 kg gacha $8/kg, 50 kg dan $7/kg; 7–12 kun.
- **Afzalligi:** avto, lekin tez (7–12 kun).
- **Kamchiligi:** hujjat va sug'urta shartlari aniqlanishi kerak.

### Transit Pro
- **Tarif:** bojxona rasmiylashtiruvi bilan $3–6/kg (tovar nomi, vazni va zichligiga bog'liq).
- **Afzalliklari:**
  - "oq" rasmiylashtiruv;
  - YATT uchun tijorat yuklari (10 kg dan);
  - o'z hisobidan xarid qiladi (10% komissiya, to'lov yuk kelganda);
  - Asl Belgisi hujjatlari bo'yicha xizmat.
- **Kamchiliklari:** Toshkent omborida 3 kundan keyin saqlash puli (500 so'm/kg/kun); bayer komissiyasi 10%.

### TAK!
- **Xizmat:** "oq" import — invoys, GTD, sertifikatlar, 18 kungacha.
- **Afzalligi:** to'liq qonuniy hujjatlar paketi.
- **Kamchiligi:** narxni so'rov orqali aniqlash kerak; kichik hajmga mos kelmasligi mumkin.

### Tez Kargo & Silk Road Olmaliq (mahalliy)
- **Manzil:** Olmaliq, Metallurglar ko'chasi 5-uy (dehqon bozori yonida). Xitoy va Turkiyadan, 5–15 kun.
- **Muhim:** ma'lumot katalog saytidan olingan. Telefon qilib tarif, hujjat va sug'urtani **tekshirish kerak**.

---

## 13. Bizning strategiyamiz

1. **Namuna (1–3 dona):** avia standart tarif. Mandarin ($9.5, to'lov kelganda) yoki Jana Post (yengil namuna uchun $0.61/100 g).
2. **Birinchi partiya (15–50 dona):** tijorat tarifi, iloji bo'lsa **"oq" hujjat bilan**. Ko'rib chiqiladiganlar: Meest tijorat avto, Green Post Cargo Commerce, Transit Pro, MK Express avto kargo.
3. **Shoshilinch bayram partiyasi:** avia tijorat ($12/kg atrofida). Bot narx farqini hisoblaydi.
4. **Katta partiya (100 kg dan):** MK Express 100 kg+ tarif, Sellmate ekspress (200 kg dan), Green Post konteyner.
5. **Olmaliq:** iPost punkti va mahalliy kargo tekshiriladi. Shunda Toshkentga faqat Uzum omboriga borish qoladi.
6. **Har bir kargo** kichik sinov posilkasidan o'tadi. Natija botdagi reytingga yoziladi.

---

## 14. Ma'lumotni yangilash tartibi

- Har oy (yoki narx o'zgarganini eshitganda) kargoning saytini oching va `data_seed/cargos.json` dagi raqamlarni yangilang: `checked_at` sanasi va `source_url`.
- Keyin botga `/import_kargo` yozing. Bot kargolarni yangilaydi, hisoblaringiz saqlanib qoladi.
- Bu faylga yangi bilim qo'shsangiz (masalan, kargo bilan suhbatdan olingan javoblar), bot "Kargo bo'yicha savol"da undan foydalanadi.

### Manbalar
- Mandarin Cargo: https://www.mandarincargo.uz/uz/
- MK Express: https://mkexpress.uz/kargo-narxlari
- iPost: https://ipost.uz/en
- Sellmate: https://sellmate.uz/uz/services/cargo
- Meest China: https://uz.meest.cn/uz/tarify-i-uslugi/
- Spot.uz — 7 ta yetkazib berish servisi (Green Post, Jana Post, Yumecs va boshqalar): https://www.spot.uz/oz/2026/07/16/delivery
- EMU Express — hajmiy vazn: https://emu.uz/uz/blog/hajmiy-vazn-va-kilogramm-farqi
- Tonlexing — CBM kalkulyatori: https://www.tonlexing.com/uz/Xitoydan-yetkazib-berish-uchun-cbm-kalkulyatori/
- Transit Pro: https://transitpro.uz/uz/
- Express Delivery: https://expresscargo.uz/
- Qog'ozcha katalogi (Olmaliq): https://qogozcha.uz/kargo-logistika
