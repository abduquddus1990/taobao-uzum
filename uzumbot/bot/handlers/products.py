import json
from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..calc import calculate, fmt, input_from_dict
from ..db import STATUSES
from ..service import local_time, rebase
from ..uzum_tariffs import TARIFFS
from ..keyboards import BTN_PRODUCTS, ProductCb, confirm
from ..render import VERDICT_ICON, calc_report

router = Router(name="products")


@router.message(F.text == BTN_PRODUCTS)
async def list_products(message: Message, db) -> None:
    rows = await db.list_products()
    if not rows:
        await message.answer("Hali saqlangan tovar yo'q. «🧮 Tannarx hisoblash» dan boshlang.")
        return
    kb = InlineKeyboardBuilder()
    lines = ["<b>📦 Tovarlarim</b> (oxirgi 20 ta)\n"]
    for r in rows:
        icon = VERDICT_ICON.get(r["verdict"], "")
        link = f' · <a href="{escape(r["source_link"], quote=True)}">manba</a>' if r["source_link"] else ""
        lines.append(f"{icon} #{r['id']} {escape(r['name'])} — foyda {fmt(r['profit'])} so'm "
                     f"({r['margin_pct']:.0f}%){link}")
        kb.button(text=f"#{r['id']} {r['name'][:25]}", callback_data=ProductCb(action="view", pid=r["id"]))
    kb.adjust(2)
    await message.answer("\n".join(lines), reply_markup=kb.as_markup())


@router.callback_query(ProductCb.filter(F.action == "view"))
async def view_product(cb: CallbackQuery, callback_data: ProductCb, db) -> None:
    r = await db.get_product(callback_data.pid)
    if not r:
        await cb.answer("Topilmadi", show_alert=True)
        return
    inp = input_from_dict(json.loads(r["input_json"]))
    res = calculate(inp)
    today = calculate(rebase(inp, await db.get_settings()))
    cargo = await db.get_cargo(r["cargo_id"]) if r["cargo_id"] else None
    cargo_name = f"{cargo['name']} ({cargo['mode']})" if cargo else "qo'lda kiritilgan"
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 O'chirish", callback_data=ProductCb(action="del", pid=r["id"]))
    cat = TARIFFS.get(r["category_id"])
    text = calc_report(r["name"], r["source_link"], cargo_name, inp, res, cat["uz"] if cat else None)
    diff = today.profit - res.profit
    today_line = ""
    if abs(diff) >= 1:
        sign = "+" if diff >= 0 else "−"
        today_line = (f"\n\n📅 <b>Bugungi kurs bilan:</b> foyda {fmt(today.profit)} so'm "
                      f"({today.margin_pct:.1f}%, {sign}{fmt(abs(diff))}) {VERDICT_ICON.get(today.verdict, '')}")
    status = STATUSES.get(r["status"] or "idea", "")
    await cb.message.answer(
        f"<i>#{r['id']} · {status} · {local_time(r['created_at'])} dagi kurs bilan</i>\n\n{text}{today_line}",
        reply_markup=kb.as_markup())
    await cb.answer()


@router.callback_query(ProductCb.filter(F.action == "del"))
async def ask_delete_product(cb: CallbackQuery, callback_data: ProductCb) -> None:
    await cb.message.answer(f"#{callback_data.pid} o'chirilsinmi?",
                            reply_markup=confirm(ProductCb(action="delok", pid=callback_data.pid)))
    await cb.answer()


@router.callback_query(ProductCb.filter(F.action == "delok"))
async def delete_product(cb: CallbackQuery, callback_data: ProductCb, db) -> None:
    await db.delete_product(callback_data.pid)
    await cb.answer("O'chirildi")
    await cb.message.answer(f"#{callback_data.pid} o'chirildi.")
