from aiogram.filters.callback_data import CallbackData
from typing import Optional

from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
                           ReplyKeyboardMarkup, WebAppInfo)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Mini App manzili ishga tushganda aniqlanadi (tunnel har safar yangi manzil beradi)
WEBAPP: dict[str, Optional[str]] = {"url": None}

BTN_CALC = "🧮 Tannarx hisoblash"
BTN_PRODUCTS = "📦 Tovarlarim"
BTN_CARGOS = "🚚 Kargolar"
BTN_SETTINGS = "⚙️ Sozlamalar"
BTN_AI = "🤖 AI yordamchi"
BTN_APP = "📱 Ilova"
BTN_CANCEL = "❌ Bekor qilish"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CALC), KeyboardButton(text=BTN_PRODUCTS)],
            [KeyboardButton(text=BTN_CARGOS), KeyboardButton(text=BTN_SETTINGS)],
            [KeyboardButton(text=BTN_AI), KeyboardButton(text=BTN_APP)],
        ],
        resize_keyboard=True,
    )


def app_button(text: str = "📱 Ilovani ochish", path: str = "") -> Optional[InlineKeyboardMarkup]:
    """Inline web_app tugma (initData faqat inline/menyu tugmasida to'liq keladi)."""
    if not WEBAPP["url"]:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, web_app=WebAppInfo(url=WEBAPP["url"] + path))
    ]])


def confirm(cb_yes, cb_no=None):
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Ha, o'chirilsin", callback_data=cb_yes)
    kb.button(text="Yo'q", callback_data=cb_no or ChoiceCb(field="noop", value="0"))
    return kb.as_markup()


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_CANCEL)]], resize_keyboard=True)


class SettingCb(CallbackData, prefix="set"):
    key: str


class CargoCb(CallbackData, prefix="cargo"):
    action: str   # pick / del / delok / add / manual
    cargo_id: int = 0


class ProductCb(CallbackData, prefix="prod"):
    action: str   # view / del / delok / save
    pid: int = 0


class ChoiceCb(CallbackData, prefix="ch"):
    field: str
    value: str


def yes_no(field: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="Ha", callback_data=ChoiceCb(field=field, value="1"))
    kb.button(text="Yo'q", callback_data=ChoiceCb(field=field, value="0"))
    return kb.as_markup()
