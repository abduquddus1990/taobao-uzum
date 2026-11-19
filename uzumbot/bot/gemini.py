"""Gemini bilan ishlash. Kalit .env faylida (GEMINI_API_KEY)."""
import logging
import time

from google import genai
from google.genai import types

log = logging.getLogger(__name__)

TRANSLATE_PROMPT = (
    "Sen Xitoy elektron savdosi bo'yicha tarjimonsan. Quyidagi matnni o'zbek tiliga "
    "(lotin yozuvida) aniq tarjima qil. Agar bu Taobao/1688 tovar tavsifi yoki sotuvchi "
    "xabari bo'lsa, oxirida 'Muhim:' deb o'lcham, material, vazn, kafolat va qaytarish "
    "shartlarini alohida sanab ber. Hech narsa qo'shib to'qima.\n\nMatn:\n"
)

CARD_PROMPT = (
    "Sen Uzum Market uchun tajribali marketolog va kopirayterisan. Berilgan tovar "
    "ma'lumotidan quyidagilarni tayyorla:\n"
    "1) O'zbekcha sarlavha (80 belgigacha, kalit so'zlar bilan)\n"
    "2) Ruscha sarlavha\n"
    "3) O'zbekcha tavsif: 3 ta asosiy foyda, o'lcham/material, kimga mos\n"
    "4) Ruscha tavsif\n"
    "5) 10 ta qidiruv so'zi (o'zbek va rus)\n"
    "Qoidalar: faqat berilgan faktlardan foydalan, yolg'on va'da va 'распродажа' kabi "
    "taqiqlangan so'zlarsiz; noaniq joyni [TEKSHIRING] deb belgila.\n\nTovar:\n"
)


SELLER_PROMPT = (
    "Sen Taobao/1688 sotuvchisi bilan yozishadigan xaridorsan. Quyida o'zbekcha nima so'rash "
    "kerakligi yozilgan. Undan sotuvchiga yuborish uchun qisqa, xushmuomala, aniq xitoycha "
    "(soddalashtirilgan) xabar tuz. Javob formati:\n"
    "1) Xitoycha xabar (nusxalash uchun alohida)\n"
    "2) Uning o'zbekcha ma'nosi (tekshirish uchun)\n"
    "Narx so'rasang — ulgurji (批发) va namuna narxini, minimal partiyani (起订量), "
    "qadoq o'lchami va vaznini so'ra.\n\nSo'rov:\n"
)


PHOTO_PROMPT = (
    "Bu Taobao/1688 tovar sahifasi yoki sotuvchi yozishmasining skrinshoti. Undagi barcha "
    "xitoycha yozuvlarni o'qib, o'zbek tiliga (lotin yozuvida) tarjima qil. Keyin 'Muhim:' deb "
    "alohida sanab ber: tovar nomi, narx(lar) yuanda, variantlar (rang/o'lcham), material, "
    "vazn va o'lcham, yetkazish/qaytarish shartlari. Rasmda ko'rinmagan narsani to'qima — "
    "o'qib bo'lmasa '[o'qilmadi]' de.\n"
)

MARKET_PROMPT = (
    "Bu Uzum Market (uzum.uz) ilovasi yoki saytidagi qidiruv natijalari / tovar sahifasi skrinshoti. "
    "Rasmda ko'ringan HAR BIR tovar kartochkasini o'qi va FAQAT JSON massiv qaytar, boshqa hech narsa "
    "yozma. Har element:\n"
    '{"title": "tovar nomi", "price": hozirgi narx so\'mda (son), "old_price": chizilgan eski narx '
    'yoki 0, "rating": reyting (masalan 4.8) yoki 0, "reviews": baholar/izohlar soni yoki 0, '
    '"orders": buyurtmalar/sotilganlar soni ("1000+ buyurtma" -> 1000) yoki 0}\n'
    "Qoidalar: narxdagi bo'shliq va \"so'm\"ni olib tashla (89 000 so'm -> 89000). Oylik to'lov "
    "(\"... so'mdan/oyiga\", muddatli to'lov) narx EMAS — uni olma. Qisman ko'ringan, narxi o'qilmaydigan "
    "kartochkani tashla. Hech narsa to'qima. Tovar yo'q bo'lsa: []"
)

# Google eski modellarni yopib boradi: sozlangani ishlamasa, keyingisiga o'tamiz.
FALLBACK_MODELS = ("gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-3.5-flash-lite",
                   "gemini-flash-lite-latest")


def _model_gone(exc: Exception) -> bool:
    s = str(exc)
    return "404" in s or "NOT_FOUND" in s or "no longer available" in s


def _model_busy(exc: Exception) -> bool:
    s = str(exc)
    return any(k in s for k in ("503", "504", "UNAVAILABLE", "DEADLINE_EXCEEDED", "overloaded", "high demand",
                                "429", "RESOURCE_EXHAUSTED"))   # 429 = bepul kunlik kvota tugadi


TOTAL_BUDGET = 75     # s: ilova so'rovini Cloudflare 100 s da uzadi — undan oldin javob qaytaramiz


class GeminiClient:
    def __init__(self, api_key: str, model: str):
        self.model = model
        # SDK o'zi 503 da uzoq qayta urinadi — qisqa qilamiz, keyin keyingi modelga o'tamiz
        opts = types.HttpOptions(timeout=30_000, retry_options=types.HttpRetryOptions(attempts=1))
        self.client = genai.Client(api_key=api_key, http_options=opts) if api_key else None

    @property
    def enabled(self) -> bool:
        return self.client is not None

    async def ask(self, prompt: str, image: bytes | None = None, mime: str = "image/jpeg") -> str:
        if not self.client:
            return "Gemini kaliti kiritilmagan (.env → GEMINI_API_KEY)."
        contents = [types.Part.from_bytes(data=image, mime_type=mime), prompt] if image else prompt
        models = list(dict.fromkeys([self.model, *FALLBACK_MODELS]))
        last: Exception | None = None
        gone = set()
        started = time.monotonic()
        for model in models:
            if time.monotonic() - started > TOTAL_BUDGET - 30:
                break                        # keyingi urinishga vaqt yetmaydi
            try:
                resp = await self.client.aio.models.generate_content(model=model, contents=contents)
            except Exception as exc:
                last = exc
                if _model_gone(exc):
                    gone.add(model)
                    log.warning("Gemini modeli %s yopilgan, keyingisi sinanadi", model)
                    continue
                if _model_busy(exc):
                    log.warning("Gemini modeli %s band, keyingisi sinanadi", model)
                    continue
                break
            if self.model in gone:          # yopilgan bo'lsa — butunlay shunga o'tamiz (band bo'lsa — yo'q)
                log.warning("Gemini modeli %s -> %s ga o'tkazildi (.env GEMINI_MODEL ni yangilang)",
                            self.model, model)
                self.model = model
            return (resp.text or "").strip() or "Javob bo'sh keldi."
        log.error("Gemini xatosi: %s", last)
        if last is not None and _model_busy(last):
            return ("⏳ Gemini hozir javob bermadi: Google serverlari band yoki bepul kunlik limit tugagan. "
                    "Birozdan keyin qayta urinib ko'ring.")
        return f"Gemini xatosi: {last}"

    async def translate(self, text: str) -> str:
        return await self.ask(TRANSLATE_PROMPT + text)

    async def market_listings_text(self, page_text: str) -> str:
        """TinyFish o'qigan Uzum qidiruv sahifasi matnidan JSON ro'yxat."""
        prompt = (MARKET_PROMPT.replace("skrinshoti", "matni").replace("Rasmda", "Matnda")
                  + "\n\nSahifa matni:\n" + (page_text or "")[:30000])
        return await self.ask(prompt)

    async def market_listings(self, image: bytes) -> str:
        return await self.ask(MARKET_PROMPT, image=image)

    async def translate_photo(self, image: bytes, caption: str = "") -> str:
        extra = f"\nFoydalanuvchi izohi: {caption}\n" if caption else ""
        return await self.ask(PHOTO_PROMPT + extra, image=image)

    async def card_text(self, info: str) -> str:
        return await self.ask(CARD_PROMPT + info)

    async def seller_message(self, request: str) -> str:
        return await self.ask(SELLER_PROMPT + request)

    async def cargo_answer(self, question: str, guide: str, cargos: str) -> str:
        return await self.ask(CARGO_PROMPT.format(guide=guide, cargos=cargos, question=question))


CARGO_PROMPT = """Sen Xitoy→O'zbekiston kargo bo'yicha maslahatchisan. Oilaviy biznes: Taobao/1688 dan
partiya olib, Uzum Market'da sotadi, Olmaliqda yashaydi. Faqat quyidagi QO'LLANMA va KARGOLAR
ro'yxatiga tayan. Unda yo'q narsani to'qima — "qo'llanmada yo'q, kargodan so'rang" de.
Narx aytsang, manbadagi sanasini ham ayt. Partiya (3+ bir xil dona) uchun seriya/tijorat
tarifini hisobga ol. O'zbek tilida (lotin), qisqa va aniq javob ber.

=== QO'LLANMA ===
{guide}

=== BOTDAGI KARGOLAR (joriy) ===
{cargos}

=== SAVOL ===
{question}
"""
