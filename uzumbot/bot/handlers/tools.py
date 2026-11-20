"""📸 Foto studiya va 💱 /kurs."""
import asyncio
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, Message

from ..keyboards import BTN_PHOTO, cancel_menu, main_menu
from ..photo import make_card, rembg_available
from ..rates import rates_text, update_rates

router = Router(name="tools")
_busy = asyncio.Semaphore(1)


class PhotoFlow(StatesGroup):
    waiting = State()


PHOTO_HELP = (
    "📸 <b>Foto studiya</b>\n\n"
    "Taobao'dagi tovar rasmini yuboring — fonni olib tashlab, oq fonli <b>3:4 (1080×1440)</b> "
    "Uzum kartochkasini qaytaraman (+ shaffof PNG Canva uchun).\n\n"
    "💡 Sifat uchun rasmni <b>fayl</b> qilib yuboring (📎 → Fayl), oddiy rasm Telegramda siqiladi.\n"
    "💡 Faqat bitta tovar ko'ringan, xitoycha yozuvsiz rasm tanlang. Matnli rasmlarni ishlatmang.\n"
    "Bir nechta rasmni ketma-ket yuborsangiz bo'ladi. Tugatish: «Bekor qilish»."
)


@router.message(F.text == BTN_PHOTO)
@router.message(Command("foto"))
async def photo_start(message: Message, state: FSMContext) -> None:
    await state.set_state(PhotoFlow.waiting)
    note = "" if rembg_available() else (
        "\n\n⚠️ <b>rembg o'rnatilmagan</b> — fon olinmaydi, faqat kartochkaga moslanadi.\n"
        "O'rnatish: <code>pip install \"rembg[cpu]\"</code> va botni qayta ishga tushiring.")
    await message.answer(PHOTO_HELP + note, reply_markup=cancel_menu())


@router.message(PhotoFlow.waiting, F.photo | F.document)
async def photo_process(message: Message) -> None:
    if message.document and not (message.document.mime_type or "").startswith("image/"):
        await message.answer("Bu rasm emas. JPG/PNG/WEBP yuboring.")
        return
    file = message.document or message.photo[-1]
    if (file.file_size or 0) > 20 * 1024 * 1024:
        await message.answer("Fayl 20 MB dan katta — Telegram bot uni yuklay olmaydi.")
        return
    wait = await message.answer("⏳ Ishlanmoqda... (birinchi marta model yuklanadi, 1–2 daqiqa)")
    data = (await message.bot.download(file)).read()
    async with _busy:
        try:
            res = await asyncio.to_thread(make_card, data)
        except Exception as exc:
            await message.answer(f"❌ Rasmni o'qib bo'lmadi: {escape(str(exc))}")
            return
        finally:
            try:
                await message.bot.delete_message(message.chat.id, wait.message_id)
            except Exception:
                pass
    n = message.message_id
    w, h = res.src_size
    cap = (f"✅ Uzum kartochkasi 1080×1440 (asl rasm {w}×{h})"
           + ("" if res.bg_removed else "\n⚠️ Fon olinmadi — oq kartochkaga moslandi."))
    if w < 800 or h < 800:
        cap += "\n⚠️ Asl rasm kichik — kartochka xira chiqishi mumkin. Sotuvchidan katta rasm so'rang."
    await message.answer_document(BufferedInputFile(res.jpg, f"uzum_{n}.jpg"), caption=cap)
    if res.png:
        await message.answer_document(BufferedInputFile(res.png, f"tovar_{n}_shaffof.png"),
                                      caption="Shaffof fonli tovar — Canva/banner uchun.")


@router.message(PhotoFlow.waiting)
async def photo_wrong(message: Message) -> None:
    await message.answer("Rasm yoki rasm-fayl yuboring. Tugatish: «Bekor qilish».")


@router.message(StateFilter(None), Command("kurs"))
async def kurs(message: Message, db) -> None:
    try:
        changed = await update_rates(db)
    except Exception as exc:
        await message.answer(f"❌ {escape(str(exc))}\nKursni qo'lda: ⚙️ Sozlamalar.", reply_markup=main_menu())
        return
    text = rates_text(changed, await db.get_settings())
    await message.answer(text + ("" if changed else "\n(o'zgarish yo'q)"), reply_markup=main_menu())
