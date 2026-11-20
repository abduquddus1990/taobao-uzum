from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..cargo_import import cargos_context, guide_text
from ..keyboards import BTN_AI, ChoiceCb, cancel_menu, main_menu
from ..render import split_text

router = Router(name="ai")


from ..quote import LINK_RE, parse_request


class AiTask(StatesGroup):
    translate = State()
    card = State()
    seller = State()
    cargo = State()


@router.message(F.text == BTN_AI)
async def ai_menu(message: Message, gemini) -> None:
    if not gemini.enabled:
        await message.answer("Gemini kaliti hali kiritilmagan. .env faylida GEMINI_API_KEY ni to'ldiring.")
        return
    kb = InlineKeyboardBuilder()
    kb.button(text="🈶 Xitoycha → o'zbekcha tarjima", callback_data=ChoiceCb(field="ai", value="tr"))
    kb.button(text="✉️ Sotuvchiga xitoycha xabar", callback_data=ChoiceCb(field="ai", value="seller"))
    kb.button(text="📝 Uzum kartochka matni", callback_data=ChoiceCb(field="ai", value="card"))
    kb.button(text="🚚 Kargo bo'yicha savol", callback_data=ChoiceCb(field="ai", value="cargo"))
    kb.button(text="📊 Uzum bozor tahlili", callback_data=ChoiceCb(field="mkt", value="start"))
    kb.adjust(1)
    await message.answer("Nima qilamiz?", reply_markup=kb.as_markup())


@router.callback_query(ChoiceCb.filter(F.field == "ai"))
async def ai_pick(cb: CallbackQuery, callback_data: ChoiceCb, state: FSMContext) -> None:
    if callback_data.value == "tr":
        await state.set_state(AiTask.translate)
        await cb.message.answer("Xitoycha matn yoki 📸 <b>skrinshot</b> yuboring (Taobao tovar sahifasi, "
                                "tavsif rasmi, sotuvchi xabari). Link yuborsangiz — bot uni ocha olmaydi.",
                                reply_markup=cancel_menu())
    elif callback_data.value == "cargo":
        await state.set_state(AiTask.cargo)
        await cb.message.answer("Kargo haqida savolingizni yozing. Masalan: <i>40 kg ryukzak partiyasini "
                                "Olmaliqqa qaysi kargo bilan olgan arzon?</i>", reply_markup=cancel_menu())
    elif callback_data.value == "seller":
        await state.set_state(AiTask.seller)
        await cb.message.answer("Sotuvchidan nima so'raymiz? O'zbekcha yozing (masalan: 50 dona narxi, "
                                "namuna, qadoq o'lchami).", reply_markup=cancel_menu())
    else:
        await state.set_state(AiTask.card)
        await cb.message.answer(
            "Tovar haqida yozing: nomi, material, o'lchami, rangi, kimga mos, narxi, Uzum linki.",
            reply_markup=cancel_menu())
    await cb.answer()


async def _reply_long(message: Message, text: str) -> None:
    for part in split_text(text):
        await message.answer(part, parse_mode=None)


LINK_ONLY_HELP = (
    "🔗 Bot Taobao sahifasini o'zi ocha olmaydi (Taobao login va bot-himoya talab qiladi).\n\n"
    "Buning o'rniga:\n"
    "📸 <b>Skrinshot</b> yuboring — tovar sahifasi, narx/variantlar, tavsif rasmi yoki sotuvchi "
    "yozishmasi. Bir nechta bo'lsa, bittadan yuboring.\n"
    "📋 yoki tovar nomi/tavsifini nusxalab, <b>matn</b> qilib yuboring.\n\n"
    "Linkning o'zi esa «🧮 Tannarx hisoblash»da saqlanadi — tovar bilan birga."
)


def _has_cjk_body(text: str) -> bool:
    """Linkdan tashqari 20+ xitoycha belgi bo'lsa — bu tarjima qilinadigan matn."""
    body = " ".join(w for w in text.split() if not w.startswith("http"))
    return sum(1 for ch in body if "一" <= ch <= "鿿") >= 20


@router.message(AiTask.translate, F.photo)
async def do_translate_photo(message: Message, state: FSMContext, gemini) -> None:
    await message.answer("⏳ Rasm o'qilmoqda va tarjima qilinmoqda...")
    buf = await message.bot.download(message.photo[-1])
    await _reply_long(message, await gemini.translate_photo(buf.read(), message.caption or ""))
    await message.answer("Yana skrinshot yuborsangiz — uni ham tarjima qilaman. Tugatish: «Bekor qilish».")


@router.message(AiTask.translate)
async def do_translate(message: Message, state: FSMContext, gemini, db) -> None:
    text = message.text or message.caption or ""
    if not text.strip():
        await message.answer("Xitoycha matn yoki skrinshot yuboring.")
        return
    if LINK_RE.search(text):
        # Taobao/1688 linki (ulashish matni bilan ham) — bu tarjima emas, tezkor baho
        from .quote import _handle
        await state.clear()
        await message.answer("🔗 Link keldi — bu tarjima emas, <b>tezkor baho</b> bo'limiga o'tkazdim.")
        await _handle(message, state, db, parse_request(text))
        return
    if ("http" in text or "tb.cn" in text) and not _has_cjk_body(text):
        await message.answer(LINK_ONLY_HELP)
        return
    await message.answer("⏳ Tarjima qilinmoqda...")
    await _reply_long(message, await gemini.translate(text))
    await state.clear()
    await message.answer("Tayyor.", reply_markup=main_menu())


@router.message(AiTask.card)
async def do_card(message: Message, state: FSMContext, gemini) -> None:
    await message.answer("⏳ Matn tayyorlanmoqda...")
    await _reply_long(message, await gemini.card_text(message.text or ""))
    await state.clear()
    await message.answer("Tekshirib, [TEKSHIRING] belgilangan joylarni to'g'rilang.", reply_markup=main_menu())


@router.message(AiTask.seller)
async def do_seller(message: Message, state: FSMContext, gemini) -> None:
    await message.answer("⏳ Xabar tayyorlanmoqda...")
    await _reply_long(message, await gemini.seller_message(message.text or ""))
    await state.clear()
    await message.answer("Xitoycha qismini nusxalab, sotuvchiga yuboring.", reply_markup=main_menu())


@router.message(AiTask.cargo)
async def do_cargo(message: Message, state: FSMContext, gemini, db) -> None:
    await message.answer("⏳ Qo'llanma va kargolar ro'yxatidan javob tayyorlanmoqda...")
    ctx = cargos_context(await db.list_cargos())
    await _reply_long(message, await gemini.cargo_answer(message.text or "", guide_text(), ctx))
    await state.clear()
    await message.answer("Narxlarni kargoning o'zidan tasdiqlang.", reply_markup=main_menu())
