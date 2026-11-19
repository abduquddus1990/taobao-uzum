"""🔗 Tezkor baho: Taobao/1688 linki yuborilsa — narx, kargo, xarajatlar va minimal narx.
📊 Uzum narxlari: TinyFish orqali Uzum qidiruv sahifasi -> raqobatchilar -> bozor tahlili."""
from dataclasses import asdict
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..calc import input_from_dict
from ..keyboards import ChoiceCb, cancel_menu, main_menu
from ..market import parse_listings, report
from ..quote import CJK_RE, HELP, LINK_RE, QuoteRequest, make_quote, parse_request, quote_report
from ..render import split_text
from ..service import result_dict
from ..tinyfish import uzum_search_url
from ..uzum_tariffs import TARIFFS

router = Router(name="quote")


class QuoteFlow(StatesGroup):
    details = State()      # narx/vazn kutilmoqda
    uzum_query = State()   # Uzum'da qidirish so'zi kutilmoqda


def quote_buttons():
    kb = InlineKeyboardBuilder()
    kb.button(text="💾 Saqlash", callback_data=ChoiceCb(field="q", value="save"))
    kb.button(text="📊 Uzum narxlari", callback_data=ChoiceCb(field="q", value="uzum"))
    kb.adjust(2)
    return kb.as_markup()


async def _edit(message: Message, wait: Message, text: str) -> None:
    try:
        await message.bot.edit_message_text(text, chat_id=message.chat.id, message_id=wait.message_id)
    except Exception:
        await message.answer(text)


@router.message(Command("baho"))
async def baho_cmd(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(HELP)


@router.message(StateFilter(None), F.text.regexp(LINK_RE))
async def got_link(message: Message, state: FSMContext, db) -> None:
    await _handle(message, state, db, parse_request(message.text))


@router.message(QuoteFlow.details, F.text)
async def got_details(message: Message, state: FSMContext, db) -> None:
    old = QuoteRequest.from_dict((await state.get_data()).get("q_req"))
    await _handle(message, state, db, old.merge(parse_request(message.text)))


async def _handle(message: Message, state: FSMContext, db, req: QuoteRequest) -> None:
    if req.missing():
        await state.set_state(QuoteFlow.details)
        await state.update_data(q_req=req.to_dict())
        await message.answer(
            f"🔗 Link qabul qilindi. Yetishmaydi: <b>{', '.join(req.missing())}</b>.\n"
            "Yozing, masalan: <code>15 250</code> (¥15, 250 g)\n"
            "Qo'shimcha: <code>18x6x6</code> o'lcham, <code>50ta</code> partiya, <code>#soyabon</code> toifa.",
            reply_markup=cancel_menu())
        return
    settings = await db.get_settings()
    cargos = await db.list_cargos()
    category = None
    if req.category_query:
        found = TARIFFS.search(req.category_query, limit=1)
        category = found[0] if found else None
    try:
        q = make_quote(settings, req, cargos, category)
    except ValueError as exc:
        await message.answer(f"Hisoblab bo'lmadi: {escape(str(exc))}", reply_markup=main_menu())
        await state.clear()
        return
    await state.clear()
    await state.update_data(q_req=req.to_dict(), q_inp=asdict(q.inp), q_res=result_dict(q.inp),
                            q_cargo=q.offer["cargo"]["id"] if q.offer else None,
                            q_cat=category["id"] if category else None, q_user=message.from_user.id)
    for part in split_text(quote_report(q)):
        await message.answer(part, reply_markup=quote_buttons())
    await message.answer("Yana link yuborishingiz mumkin.", reply_markup=main_menu())


@router.callback_query(ChoiceCb.filter((F.field == "q") & (F.value == "save")))
async def save(cb: CallbackQuery, state: FSMContext, db) -> None:
    d = await state.get_data()
    if "q_inp" not in d:
        await cb.answer("Hisob eskirgan — linkni qayta yuboring", show_alert=True)
        return
    req = QuoteRequest.from_dict(d["q_req"])
    pid = await db.save_product(req.name, req.link, d.get("q_cargo"), d["q_inp"], d["q_res"],
                                d.get("q_user") or cb.from_user.id, note="🔗 tezkor baho",
                                category_id=d.get("q_cat"), scheme="FBO")
    await cb.answer("Saqlandi")
    await cb.message.answer(f"✅ «{escape(req.name)}» #{pid} — 💡 G'oya holatida saqlandi.")


@router.callback_query(ChoiceCb.filter((F.field == "q") & (F.value == "uzum")))
async def uzum_start(cb: CallbackQuery, state: FSMContext, tinyfish) -> None:
    d = await state.get_data()
    if "q_inp" not in d:
        await cb.answer("Hisob eskirgan — linkni qayta yuboring", show_alert=True)
        return
    await cb.answer()
    if not tinyfish.enabled:
        await cb.message.answer(
            "📊 Uzum narxlarini avtomatik o'qish uchun TinyFish kaliti kerak (bepul, kuniga 1000 sahifa):\n"
            "1) agent.tinyfish.ai da ro'yxatdan o'ting → API key\n"
            "2) .env ga <code>TINYFISH_API_KEY=...</code> yozing va botni qayta yoqing.\n\n"
            "Hozircha: /bozor — Uzum qidiruv skrinshotlari orqali.")
        return
    name = QuoteRequest.from_dict(d["q_req"]).name
    await state.set_state(QuoteFlow.uzum_query)
    hint = ("" if CJK_RE.search(name) or name.startswith("Taobao") else
            f"\nYoki shu nom bilan: <code>{escape(name)}</code>")
    await cb.message.answer("Uzum'da qanday so'z bilan qidiramiz? Xaridor yozadigan so'zni yozing "
                            "(masalan: <i>mini zont</i> yoki <i>зонт мини</i>)." + hint,
                            reply_markup=cancel_menu())


@router.message(QuoteFlow.uzum_query, F.text)
async def uzum_search(message: Message, state: FSMContext, tinyfish, gemini) -> None:
    query = (message.text or "").strip()[:80]
    d = await state.get_data()
    url = uzum_search_url(query)
    wait = await message.answer(f"⏳ Uzum o'qilmoqda: {escape(query)}")
    try:
        page = await tinyfish.fetch(url)
    except RuntimeError as exc:
        await _edit(message, wait, f"❌ {escape(str(exc))}")
        await state.set_state(None)
        return
    if not gemini.enabled:
        await _edit(message, wait, "Sahifa o'qildi, lekin narxlarni ajratish uchun Gemini kaliti kerak (.env).")
        await state.set_state(None)
        return
    items = parse_listings(await gemini.market_listings_text(page))
    await state.set_state(None)
    if not items:
        await _edit(message, wait, "Uzum sahifasidan tovar narxlarini ajrata olmadim. Boshqa so'z bilan urinib "
                             "ko'ring yoki /bozor orqali skrinshot yuboring.")
        return
    inp = input_from_dict(d["q_inp"]) if d.get("q_inp") else None
    try:
        await message.bot.delete_message(message.chat.id, wait.message_id)
    except Exception:
        pass
    text = report(items, query, inp) + f'\n\n🔗 <a href="{escape(url, quote=True)}">Uzum qidiruvini ochish</a>'
    for part in split_text(text):
        await message.answer(part)
    await message.answer("Tayyor.", reply_markup=main_menu())
