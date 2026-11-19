from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..calc import parse_number
from ..cargo_import import import_cargos
from ..keyboards import BTN_CARGOS, CargoCb, ChoiceCb, cancel_menu, confirm, main_menu, yes_no

router = Router(name="cargos")


class AddCargo(StatesGroup):
    name = State()
    mode = State()
    tariff = State()
    days = State()
    white_docs = State()
    olmaliq = State()
    note = State()


class EditTariff(StatesGroup):
    value = State()


def _yn(v, yes: str, no: str, unknown: str) -> str:
    return unknown if v is None else (yes if v else no)


def cargo_line(c) -> str:
    days = f"{c['days_min'] or '?'}–{c['days_max']} kun" if c["days_max"] else "muddat ?"
    flags = [
        _yn(c["white_docs"], "oq hujjat ✅", "oq hujjat ❌", "oq hujjat ?"),
        "📍 Olmaliq ✅" if c["olmaliq"] else "Olmaliq ❌",
        _yn(c["series_ok"], "partiya ✅", "faqat namuna", "partiya ?"),
        "★" * int(c["rating"] or 3),
    ]
    if c["min_kg"]:
        flags.append(f"min {c['min_kg']:g} kg")
    if c["usd_m3"]:
        flags.append(f"{c['usd_m3']:g} $/m³")
    if not c["verified"]:
        flags.append("❔ saytdan")
    tariff = f"{c['tariff_usd_kg']:g} $/kg" if c["tariff_usd_kg"] > 0 else "⚠️ tarif kiritilmagan"
    note = f"\n   <i>{escape(c['note'])}</i>" if c["note"] else ""
    src = ""
    if c["source"]:
        src = f'\n   🔗 <a href="{escape(c["source"], quote=True)}">manba</a>'
        if c["checked_at"]:
            src += f" · tekshirilgan {escape(c['checked_at'])}"
    return (f"<b>{escape(c['name'])}</b> ({c['mode']}) — {tariff}, {days}\n"
            f"   {' · '.join(flags)}{note}{src}")


@router.message(F.text == BTN_CARGOS)
async def list_cargos(message: Message, db) -> None:
    rows = await db.list_cargos()
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Kargo qo'shish", callback_data=CargoCb(action="add"))
    for c in rows:
        kb.button(text=f"✏️ {c['name']}", callback_data=CargoCb(action="edit", cargo_id=c["id"]))
        kb.button(text="🗑", callback_data=CargoCb(action="del", cargo_id=c["id"]))
    kb.adjust(1, *([2] * len(rows)))
    if not rows:
        await message.answer("Hali kargo kiritilmagan. Tayyor ro'yxat uchun /import_kargo yozing.",
                             reply_markup=kb.as_markup())
        return
    chunks, cur = [], "<b>🚚 Kargolar</b> (arzonidan boshlab)\n\n"
    for ln in (cargo_line(c) for c in rows):
        if len(cur) + len(ln) > 3800:
            chunks.append(cur)
            cur = ""
        cur += ln + "\n\n"
    chunks.append(cur)
    for i, ch in enumerate(chunks):
        await message.answer(ch, reply_markup=kb.as_markup() if i == len(chunks) - 1 else None)


@router.message(Command("import_kargo"))
async def import_cmd(message: Message, db, role: str) -> None:
    if role != "owner":
        await message.answer("Bu buyruq faqat adminlar uchun.")
        return
    try:
        res = await import_cargos(db)
    except (OSError, ValueError, KeyError) as exc:
        await message.answer(f"data_seed/cargos.json o'qilmadi: {escape(str(exc))}")
        return
    lines = [f"• {escape(n)}: {s}" for n, s in res]
    await message.answer(f"✅ {len(res)} ta tarif yuklandi:\n" + "\n".join(lines)
                         + "\n\n«🚚 Kargolar» da ko'ring. ⚠️ belgili tariflarni ✏️ orqali kiriting.")


@router.callback_query(CargoCb.filter(F.action == "edit"))
async def edit_tariff_start(cb: CallbackQuery, callback_data: CargoCb, state: FSMContext, db) -> None:
    c = await db.get_cargo(callback_data.cargo_id)
    if not c:
        await cb.answer("Topilmadi", show_alert=True)
        return
    await state.set_state(EditTariff.value)
    await state.update_data(cargo_id=c["id"])
    await cb.message.answer(f"<b>{escape(c['name'])}</b> — yangi tarif, $ / kg?\n"
                            "(so'mda bo'lsa: <code>83880 som</code> deb yozing — kurs bo'yicha o'giraman)\n"
                            "Qolgan maydonlar (muddat, reyting, Olmaliq…) — ilovada.",
                            reply_markup=cancel_menu())
    await cb.answer()


@router.message(EditTariff.value)
async def edit_tariff_save(message: Message, state: FSMContext, db) -> None:
    text = (message.text or "").lower()
    try:
        v = parse_number(text)
    except ValueError:
        await message.answer("Son kiriting, masalan: 7.5 yoki 83880 som")
        return
    if "som" in text or "so'm" in text or v > 500:
        v = round(v / (await db.get_settings())["usd_rate"], 2)
    await db.set_cargo_tariff((await state.get_data())["cargo_id"], v)
    await state.clear()
    await message.answer(f"✅ Tarif yangilandi: {v:g} $/kg (✅ tasdiqlangan).", reply_markup=main_menu())


@router.callback_query(CargoCb.filter(F.action == "del"))
async def ask_delete_cargo(cb: CallbackQuery, callback_data: CargoCb, db) -> None:
    c = await db.get_cargo(callback_data.cargo_id)
    if not c:
        await cb.answer("Topilmadi", show_alert=True)
        return
    await cb.message.answer(f"«{escape(c['name'])}» kargosi o'chirilsinmi?",
                            reply_markup=confirm(CargoCb(action="delok", cargo_id=c["id"])))
    await cb.answer()


@router.callback_query(CargoCb.filter(F.action == "delok"))
async def delete_cargo(cb: CallbackQuery, callback_data: CargoCb, db) -> None:
    await db.delete_cargo(callback_data.cargo_id)
    await cb.answer("O'chirildi")
    await cb.message.answer("Kargo o'chirildi. Ro'yxat uchun «🚚 Kargolar» ni bosing.")


@router.callback_query(CargoCb.filter(F.action == "add"))
async def add_start(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddCargo.name)
    await cb.message.answer("Kargo nomi? (masalan: iPost, MK Express)", reply_markup=cancel_menu())
    await cb.answer()


@router.message(AddCargo.name)
async def add_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=(message.text or "").strip()[:60])
    kb = InlineKeyboardBuilder()
    kb.button(text="✈️ Avia", callback_data=ChoiceCb(field="mode", value="avia"))
    kb.button(text="🚛 Avto", callback_data=ChoiceCb(field="mode", value="avto"))
    await state.set_state(AddCargo.mode)
    await message.answer("Turi?", reply_markup=kb.as_markup())


@router.callback_query(AddCargo.mode, ChoiceCb.filter(F.field == "mode"))
async def add_mode(cb: CallbackQuery, callback_data: ChoiceCb, state: FSMContext) -> None:
    await state.update_data(mode=callback_data.value)
    await state.set_state(AddCargo.tariff)
    await cb.message.answer("Tarif, $ / kg? (so'mda bo'lsa, dollarga o'girib yozing)")
    await cb.answer()


@router.message(AddCargo.tariff)
async def add_tariff(message: Message, state: FSMContext) -> None:
    try:
        tariff = parse_number(message.text)
    except ValueError:
        await message.answer("Son kiriting, masalan: 6.7")
        return
    await state.update_data(tariff_usd_kg=tariff)
    await state.set_state(AddCargo.days)
    await message.answer("Yetkazish muddati, kun? Masalan: 12-15 (bilmasangiz «-»)")


@router.message(AddCargo.days)
async def add_days(message: Message, state: FSMContext) -> None:
    text = (message.text or "").replace("–", "-").replace(" ", "")
    dmin = dmax = None
    if text != "-":
        try:
            a, _, b = text.partition("-")
            dmin = int(a)
            dmax = int(b) if b else dmin
        except ValueError:
            await message.answer("Masalan: 12-15 yoki 7 yoki «-»")
            return
    await state.update_data(days_min=dmin, days_max=dmax)
    await state.set_state(AddCargo.white_docs)
    await message.answer("«Oq» hujjat (invoys, GTD) beradimi?", reply_markup=yes_no("white_docs"))


@router.callback_query(AddCargo.white_docs, ChoiceCb.filter(F.field == "white_docs"))
async def add_docs(cb: CallbackQuery, callback_data: ChoiceCb, state: FSMContext) -> None:
    await state.update_data(white_docs=int(callback_data.value))
    await state.set_state(AddCargo.olmaliq)
    await cb.message.answer("Olmaliqda olib ketish punkti bormi?", reply_markup=yes_no("olmaliq"))
    await cb.answer()


@router.callback_query(AddCargo.olmaliq, ChoiceCb.filter(F.field == "olmaliq"))
async def add_olmaliq(cb: CallbackQuery, callback_data: ChoiceCb, state: FSMContext) -> None:
    await state.update_data(olmaliq=int(callback_data.value))
    await state.set_state(AddCargo.note)
    await cb.message.answer("Izoh yoki telefon/link? (yo'q bo'lsa «-»)")
    await cb.answer()


@router.message(AddCargo.note)
async def add_note(message: Message, state: FSMContext, db) -> None:
    note = (message.text or "").strip()
    data = await state.get_data()
    data["note"] = None if note == "-" else note[:300]
    await db.add_cargo(data)
    await state.clear()
    await message.answer(f"✅ Kargo saqlandi: {escape(data['name'])}", reply_markup=main_menu())
