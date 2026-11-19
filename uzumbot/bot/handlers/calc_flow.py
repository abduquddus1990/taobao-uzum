import re
from dataclasses import asdict
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..calc import calculate, fmt, parse_number
from ..keyboards import BTN_CALC, CargoCb, ChoiceCb, ProductCb, cancel_menu, main_menu
from ..render import calc_report, offers_report
from ..service import build_input, cargo_offers, result_dict
from ..uzum_tariffs import TARIFFS

router = Router(name="calc")

DIMS_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*[x×х*]\s*(\d+(?:[.,]\d+)?)\s*[x×х*]\s*(\d+(?:[.,]\d+)?)\s*$", re.I)


class Calc(StatesGroup):
    name = State()
    link = State()
    price = State()
    weight = State()
    dims = State()
    qty = State()
    category = State()
    sell = State()
    cargo = State()
    manual_tariff = State()


async def _num(message: Message, hint: str):
    try:
        return parse_number(message.text)
    except (ValueError, TypeError):
        await message.answer(f"Son kiriting. {hint}")
        return None


def parse_dims(text: str):
    m = DIMS_RE.match(text or "")
    if not m:
        return None
    vals = [float(x.replace(",", ".")) for x in m.groups()]
    return vals if all(v > 0 for v in vals) else None


@router.message(F.text == BTN_CALC)
async def start_calc(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Calc.name)
    await message.answer("Tovar nomi? (masalan: Mini zont UPF50+)", reply_markup=cancel_menu())


@router.message(Calc.name)
async def got_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=(message.text or "").strip()[:100])
    await state.set_state(Calc.link)
    await message.answer("Taobao/1688 linki? (yo'q bo'lsa «-»)")


@router.message(Calc.link)
async def got_link(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    link = next((t for t in text.split() if t.startswith("http")), None)
    if text != "-" and not link:
        await message.answer("Link http bilan boshlanishi kerak (yoki «-» yozing).")
        return
    await state.update_data(link=link)
    await state.set_state(Calc.price)
    await message.answer("1 dona narxi, ¥ (yuan)?")


@router.message(Calc.price)
async def got_price(message: Message, state: FSMContext) -> None:
    v = await _num(message, "Masalan: 15 yoki 12.5")
    if v is None:
        return
    await state.update_data(price_cny=v)
    await state.set_state(Calc.weight)
    await message.answer("1 dona vazni, gramm? (qadog'i bilan)\n"
                         "O'lchami bilan birga yozsangiz ham bo'ladi: <code>250 18x6x6</code>")


@router.message(Calc.weight)
async def got_weight(message: Message, state: FSMContext) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 2 and parse_dims(parts[1].replace("sm", "").replace("cm", "")):
        # "250 18x6x6" — vazn va o'lcham bir qatorda
        try:
            w = parse_number(parts[0].lower().replace("gr", "").replace("g", ""))
        except ValueError:
            w = 0
        if w > 0:
            d = parse_dims(parts[1].replace("sm", "").replace("cm", ""))
            await state.update_data(weight_g=w, length_cm=d[0], width_cm=d[1], height_cm=d[2])
            await state.set_state(Calc.qty)
            await message.answer("Partiyada nechta dona? (namuna uchun 15–20)")
            return
    v = await _num(message, "Masalan: 250 yoki o'lcham bilan: 250 18x6x6")
    if v is None:
        return
    await state.update_data(weight_g=v)
    await state.set_state(Calc.dims)
    await message.answer(
        "Qadog'i bilan o'lchami, sm: <b>uzunlik x eni x balandlik</b>\n"
        "Masalan: <code>30x20x15</code>\n\n"
        "Bu juda muhim: Uzum logistikani litr bo'yicha oladi, kargo esa katta yengil "
        "tovarni hajm bo'yicha. Bilmasangiz «-» (natija taxminiy bo'ladi).")


@router.message(Calc.dims)
async def got_dims(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text == "-":
        await state.update_data(length_cm=0, width_cm=0, height_cm=0)
    else:
        d = parse_dims(text)
        if not d:
            await message.answer("Format: 30x20x15 (sm) yoki «-»")
            return
        await state.update_data(length_cm=d[0], width_cm=d[1], height_cm=d[2])
    await state.set_state(Calc.qty)
    await message.answer("Partiyada nechta dona? (namuna uchun 15–20)")


@router.message(Calc.qty)
async def got_qty(message: Message, state: FSMContext) -> None:
    v = await _num(message, "Masalan: 50")
    if v is None or int(v) < 1:
        if v is not None:
            await message.answer("Kamida 1 dona.")
        return
    await state.update_data(qty=int(v))
    await state.set_state(Calc.category)
    kb = InlineKeyboardBuilder()
    kb.button(text="Toifasiz (standart komissiya)", callback_data=ChoiceCb(field="cat", value="0"))
    await message.answer("Uzumdagi toifa? Bir-ikki so'z yozing: <i>soyabon</i>, <i>ryukzak</i>, "
                         "<i>oshxona</i>… Komissiya rasmiy jadvaldan olinadi.", reply_markup=kb.as_markup())


@router.message(Calc.category)
async def search_category(message: Message, state: FSMContext) -> None:
    found = TARIFFS.search(message.text or "", limit=8)
    kb = InlineKeyboardBuilder()
    for c in found:
        comm = c["fbo"]
        label = c["uz"].split(" › ")
        short = " › ".join(label[-2:])
        kb.button(text=f"{short} — {comm:g}%" if comm is not None else f"{short} — FBO yo'q",
                  callback_data=ChoiceCb(field="cat", value=str(c["id"])))
    kb.button(text="Toifasiz (standart komissiya)", callback_data=ChoiceCb(field="cat", value="0"))
    kb.adjust(1)
    text = "Qaysi biri? (yoki boshqa so'z bilan qidiring)" if found else "Topilmadi. Boshqa so'z bilan yozing:"
    await message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(Calc.category, ChoiceCb.filter(F.field == "cat"))
async def pick_category(cb: CallbackQuery, callback_data: ChoiceCb, state: FSMContext) -> None:
    cid = int(callback_data.value)
    cat = TARIFFS.get(cid)
    if cat and cat["fbo"] is None:
        await cb.answer("Bu toifa Uzum omborida (FBO) sotilmaydi", show_alert=True)
        return
    await state.update_data(category_id=cid or None)
    await state.set_state(Calc.sell)
    note = f"✅ {escape(cat['uz'])} — komissiya {cat['fbo']:g}%\n\n" if cat else ""
    await cb.message.answer(f"{note}Uzumda qanchaga sotmoqchisiz, so'm?")
    await cb.answer()


@router.message(Calc.sell)
async def got_sell(message: Message, state: FSMContext, db) -> None:
    v = await _num(message, "Masalan: 129000")
    if v is None or v <= 0:
        return
    await state.update_data(sell_price=v)
    data = await state.get_data()
    s = await db.get_settings()
    cargos = await db.list_cargos()
    offers = cargo_offers(s, data, cargos, TARIFFS.get(data.get("category_id")))
    kb = InlineKeyboardBuilder()
    for x in [o for o in offers if o["ok"]][:8]:
        c, r = x["cargo"], x["result"]
        mark = x["badges"][0].split()[0] if x["badges"] else "•"
        kb.button(text=f"{mark} {c['name']} ({c['mode']}) · foyda {fmt(r.profit)}",
                  callback_data=CargoCb(action="pick", cargo_id=c["id"]))
    kb.button(text="✍️ Tarifni qo'lda yozaman", callback_data=CargoCb(action="manual"))
    kb.adjust(1)
    await state.set_state(Calc.cargo)
    text = offers_report(offers) or "Kargolar ro'yxati bo'sh — «🚚 Kargolar» da qo'shing."
    await message.answer(f"{text}\n\nQaysi kargo?", reply_markup=kb.as_markup())


@router.callback_query(Calc.cargo, CargoCb.filter(F.action == "pick"))
async def pick_cargo(cb: CallbackQuery, callback_data: CargoCb, state: FSMContext, db) -> None:
    c = await db.get_cargo(callback_data.cargo_id)
    if not c:
        await cb.answer("Kargo topilmadi", show_alert=True)
        return
    await state.update_data(cargo_id=c["id"], cargo_name=f"{c['name']} ({c['mode']})",
                            tariff_usd_kg=c["tariff_usd_kg"])
    await cb.answer()
    await _finish(cb.message, state, db, cb.from_user.id)


@router.callback_query(Calc.cargo, CargoCb.filter(F.action == "manual"))
async def manual_cargo(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Calc.manual_tariff)
    await cb.message.answer("Kargo tarifi, $ / kg?")
    await cb.answer()


@router.message(Calc.manual_tariff)
async def got_manual_tariff(message: Message, state: FSMContext, db) -> None:
    v = await _num(message, "Masalan: 6.7")
    if v is None:
        return
    await state.update_data(cargo_id=None, cargo_name="qo'lda kiritilgan", tariff_usd_kg=v)
    await _finish(message, state, db, message.from_user.id)


async def _finish(message: Message, state: FSMContext, db, user_id: int) -> None:
    data = await state.get_data()
    s = await db.get_settings()
    cargo = await db.get_cargo(data["cargo_id"]) if data.get("cargo_id") else None
    cat = TARIFFS.get(data.get("category_id"))
    try:
        inp = build_input(s, data, cargo, cat, "FBO")
    except ValueError as exc:
        await message.answer(f"Xato: {escape(str(exc))}", reply_markup=main_menu())
        await state.clear()
        return
    res = calculate(inp)
    await state.update_data(inp=asdict(inp), res=result_dict(inp), user_id=user_id)
    kb = InlineKeyboardBuilder()
    kb.button(text="💾 Saqlash", callback_data=ProductCb(action="save"))
    await message.answer(calc_report(data["name"], data.get("link"), data["cargo_name"], inp, res,
                                     cat["uz"] if cat else None),
                         reply_markup=kb.as_markup())
    await message.answer("Saqlash uchun tugmani bosing yoki menyudan davom eting.", reply_markup=main_menu())


@router.callback_query(ProductCb.filter(F.action == "save"))
async def save_product(cb: CallbackQuery, state: FSMContext, db) -> None:
    data = await state.get_data()
    if "res" not in data:
        await cb.answer("Hisob topilmadi — qaytadan hisoblang", show_alert=True)
        return
    pid = await db.save_product(data["name"], data.get("link"), data.get("cargo_id"),
                                data["inp"], data["res"], data["user_id"],
                                category_id=data.get("category_id"), scheme="FBO")
    await state.clear()
    await cb.answer("Saqlandi")
    await cb.message.answer(f"✅ «{escape(data['name'])}» #{pid} sifatida saqlandi. «📦 Tovarlarim» da ko'rasiz.")
