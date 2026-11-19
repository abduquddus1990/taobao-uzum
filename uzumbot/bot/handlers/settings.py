from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..calc import fmt, parse_number
from ..db import SETTINGS
from ..keyboards import BTN_SETTINGS, SettingCb, cancel_menu, main_menu

router = Router(name="settings")


class EditSetting(StatesGroup):
    value = State()


def _val(v: float) -> str:
    return fmt(v) if v >= 1000 else f"{v:g}"


async def _settings_view(db):
    s = await db.get_settings()
    lines = ["<b>⚙️ Sozlamalar</b> (o'zgartirish uchun tugmani bosing)\n"]
    kb = InlineKeyboardBuilder()
    for key, (title, _, unit) in SETTINGS.items():
        lines.append(f"• {title}: <b>{_val(s[key])}</b> {unit}")
        kb.button(text=title, callback_data=SettingCb(key=key))
    kb.adjust(2)
    return "\n".join(lines), kb.as_markup()


@router.message(F.text == BTN_SETTINGS)
async def show_settings(message: Message, db) -> None:
    text, markup = await _settings_view(db)
    await message.answer(text, reply_markup=markup)


@router.callback_query(SettingCb.filter())
async def ask_value(cb: CallbackQuery, callback_data: SettingCb, state: FSMContext, role: str) -> None:
    if role != "owner":
        await cb.answer("Sozlamani faqat ega o'zgartiradi", show_alert=True)
        return
    title, _, unit = SETTINGS[callback_data.key]
    await state.set_state(EditSetting.value)
    await state.update_data(key=callback_data.key)
    await cb.message.answer(f"<b>{title}</b> uchun yangi qiymatni yozing ({unit}):", reply_markup=cancel_menu())
    await cb.answer()


@router.message(EditSetting.value)
async def save_value(message: Message, state: FSMContext, db) -> None:
    try:
        value = parse_number(message.text)
    except ValueError:
        await message.answer("Son kiriting, masalan: 1750 yoki 12,5")
        return
    key = (await state.get_data())["key"]
    await db.set_setting(key, value)
    await state.clear()
    await message.answer("✅ Saqlandi.", reply_markup=main_menu())
    text, markup = await _settings_view(db)
    await message.answer(text, reply_markup=markup)
