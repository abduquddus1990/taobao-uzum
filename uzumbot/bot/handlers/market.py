"""📊 Uzum bozor tahlili: Uzum qidiruv natijalari skrinshotlari -> narx, sotuv, raqobat, foydamiz."""
import json
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..calc import input_from_dict
from ..keyboards import ChoiceCb, cancel_menu, main_menu
from ..market import from_dicts, merge, parse_listings, report, to_dicts
from ..render import split_text
from ..service import rebase

router = Router(name="market")

MAX_ITEMS = 60

HOW_TO = (
    "📸 <b>Uzum ilovasida</b> shu tovarni qidiring (masalan: <i>qo'l oynasi sovg'a to'plami</i>), "
    "saralashni <b>«Ommabop»</b> qiling va natijalar ro'yxatining <b>1–4 ta skrinshotini</b> yuboring "
    "(pastga surib, har ekranni alohida).\n\n"
    "Har bir skrinshotdan narx, reyting, izoh va buyurtmalar sonini o'qiyman. "
    "Tugatgach — <b>«✅ Tahlil qilish»</b>."
)


class Market(StatesGroup):
    shots = State()


def go_button():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tahlil qilish", callback_data=ChoiceCb(field="mkt", value="go"))
    return kb.as_markup()


@router.message(Command("bozor"))
async def market_cmd(message: Message, state: FSMContext, db) -> None:
    await start_market(message, state, db)


async def start_market(message: Message, state: FSMContext, db) -> None:
    await state.clear()
    rows = await db.list_products(limit=10)
    kb = InlineKeyboardBuilder()
    for r in rows:
        kb.button(text=f"#{r['id']} {r['name'][:28]}", callback_data=ChoiceCb(field="mkt", value=f"p{r['id']}"))
    kb.button(text="➖ Tovarsiz (faqat bozor narxi)", callback_data=ChoiceCb(field="mkt", value="p0"))
    kb.adjust(1)
    await message.answer("📊 <b>Uzum bozor tahlili</b>\n\nQaysi tovaringiz uchun? Saqlangan tovarni tanlasangiz, "
                         "Uzum narxlarida qancha foyda qilishingizni ham hisoblayman.",
                         reply_markup=kb.as_markup())


@router.callback_query(ChoiceCb.filter((F.field == "mkt") & (F.value == "start")))
async def start_cb(cb: CallbackQuery, state: FSMContext, db) -> None:
    await cb.answer()
    await start_market(cb.message, state, db)


@router.callback_query(ChoiceCb.filter((F.field == "mkt") & F.value.startswith("p")))
async def pick_product(cb: CallbackQuery, callback_data: ChoiceCb, state: FSMContext) -> None:
    pid = int(callback_data.value[1:] or 0)
    await state.set_state(Market.shots)
    await state.update_data(mkt_pid=pid, mkt_items=[])
    await cb.message.answer(HOW_TO, reply_markup=cancel_menu())
    await cb.answer()


@router.message(Market.shots, F.photo)
async def got_shot(message: Message, state: FSMContext, gemini) -> None:
    data = await state.get_data()
    items = from_dicts(data.get("mkt_items"))
    if len(items) >= MAX_ITEMS:
        await message.answer("Yetarli — «✅ Tahlil qilish» ni bosing.", reply_markup=go_button())
        return
    wait = await message.answer("⏳ Skrinshot o'qilmoqda...")
    buf = await message.bot.download(message.photo[-1])
    raw = await gemini.market_listings(buf.read())
    new = parse_listings(raw)
    if not new:
        hint = raw if raw.startswith(("⏳", "Gemini")) else \
            "Bu rasmdan tovar narxlarini o'qiy olmadim. Uzum qidiruv natijalari ko'ringan skrinshot yuboring."
        await wait.edit_text(hint)
        return
    items = merge(items, new)[:MAX_ITEMS]
    await state.update_data(mkt_items=to_dicts(items))
    await wait.edit_text(f"✅ {len(new)} ta tovar o'qildi (jami {len(items)} ta). "
                         "Yana skrinshot yuboring yoki tahlil qiling.", reply_markup=go_button())


@router.message(Market.shots)
async def shots_text(message: Message) -> None:
    await message.answer("Uzum qidiruv natijalarining <b>skrinshotini</b> (rasm) yuboring, "
                         "yoki «✅ Tahlil qilish» ni bosing.", reply_markup=go_button())


@router.callback_query(ChoiceCb.filter((F.field == "mkt") & (F.value == "go")))
async def analyze(cb: CallbackQuery, state: FSMContext, db) -> None:
    data = await state.get_data()
    items = from_dicts(data.get("mkt_items"))
    if not items:
        await cb.answer("Avval skrinshot yuboring", show_alert=True)
        return
    await cb.answer()
    name, inp = "", None
    pid = data.get("mkt_pid") or 0
    if pid:
        row = await db.get_product(pid)
        if row:
            name = row["name"]
            inp = rebase(input_from_dict(json.loads(row["input_json"])), await db.get_settings())
    text = report(items, name, inp)
    for part in split_text(text):
        await cb.message.answer(part)
    await state.clear()
    await cb.message.answer("Tayyor. Boshqa tovar uchun: /bozor", reply_markup=main_menu())
