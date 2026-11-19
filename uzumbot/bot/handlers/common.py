from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, MenuButtonWebApp, Message, WebAppInfo

from ..backup import send_backup
from ..uzum_tariffs import MANUAL_URL, TARIFFS, notify_changes
from ..keyboards import BTN_APP, BTN_CANCEL, WEBAPP, ChoiceCb, app_button, main_menu

router = Router(name="common")

HELP = (
    "📱 <b>Ilova</b> — hammasi bitta chiroyli oynada (pastdagi «Ilova» tugmasi)\n\n"
    "🧮 <b>Tannarx hisoblash</b> — Taobao narxi, vazn va kargo bo'yicha foyda hisobi\n"
    "📦 <b>Tovarlarim</b> — saqlangan hisoblar (linklari bilan)\n"
    "🚚 <b>Kargolar</b> — kargo xizmatlari ro'yxati va tariflari\n"
    "⚙️ <b>Sozlamalar</b> — kurs, komissiya, qatnov narxi va boshqalar\n"
    "🤖 <b>AI yordamchi</b> — xitoycha tarjima, kartochka matni\n\n"
    "Buyruqlar:\n"
    "/bozor — Uzum bozor tahlili: narxlar, raqobat, foydangiz\n"
    "/backup — bazaning zaxira nusxasini olish\n"
    "/tariflar — Uzum komissiya jadvalini hozir yangilash\n"
    "/users — foydalanuvchilar ro'yxati\n"
    "/id — o'z Telegram ID raqamingiz"
)

GREET = {"Gulim": "🌷"}


@router.message(StateFilter("*"), F.text == BTN_CANCEL)
@router.message(StateFilter("*"), Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu())


@router.callback_query(StateFilter("*"), ChoiceCb.filter(F.field == "noop"))
async def noop(cb: CallbackQuery) -> None:
    await cb.answer("Bekor qilindi")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, user_name: str = "") -> None:
    await state.clear()
    name = user_name or message.from_user.first_name or ""
    icon = GREET.get(name, "👋")
    await message.answer(f"Assalomu alaykum, <b>{escape(name)}</b>! {icon}\n\n{HELP}",
                         reply_markup=main_menu())
    markup = app_button("✨ Ilovani ochish")
    if markup:
        await message.answer("Hammasini ilovada qilish qulayroq:", reply_markup=markup)
        await set_menu_button(message)


async def set_menu_button(message: Message) -> None:
    """Chap pastdagi «📱 Ilova» tugmasi. Bot ishga tushganda odam hali /start bosmagan bo'lsa,
    Telegram uni o'rnatishga ruxsat bermaydi — shuning uchun /start va /app da ham o'rnatamiz."""
    if not WEBAPP["url"]:
        return
    try:
        await message.bot.set_chat_menu_button(
            chat_id=message.chat.id,
            menu_button=MenuButtonWebApp(text="📱 Ilova", web_app=WebAppInfo(url=WEBAPP["url"])))
    except Exception:
        pass


@router.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await message.answer(HELP, reply_markup=main_menu())


@router.message(F.text == BTN_APP)
@router.message(Command("app"))
async def open_app(message: Message) -> None:
    markup = app_button()
    if not markup:
        await message.answer("Ilova hozircha ishga tushmagan (HTTPS manzil yo'q). "
                             "Kompyuterda cloudflared o'rnatilganini tekshiring — README, 9-bo'lim.")
        return
    await message.answer("Ilova tayyor 👇", reply_markup=markup)
    await set_menu_button(message)


@router.message(Command("id"))
async def my_id(message: Message) -> None:
    await message.answer(f"Sizning ID: <code>{message.from_user.id}</code>")


@router.message(Command("backup"))
async def backup_cmd(message: Message, db, role: str) -> None:
    if role != "owner":
        await message.answer("Bu buyruq faqat adminlar uchun.")
        return
    await send_backup(message.bot, db, [message.chat.id], "Qo'lda so'ralgan nusxa")


@router.message(Command("tariflar"))
async def tariffs_cmd(message: Message, db, role: str) -> None:
    if role != "owner":
        await message.answer("Bu buyruq faqat adminlar uchun.")
        return
    await message.answer("⏳ Uzum rasmiy jadvali yuklanmoqda…")
    ok, msg, changed = await TARIFFS.refresh()
    icon = "✅" if ok else "⚠️"
    await message.answer(f"{icon} {escape(msg)}\n"
                         f"Oxirgi yangilanish: {TARIFFS.fetched_at}\n"
                         f'<a href="{MANUAL_URL}">Uzum qo\'llanmasi: tariflar</a>')
    if ok and changed:
        await notify_changes(message.bot, db, [message.chat.id], changed)


@router.message(Command("adduser"))
async def add_user(message: Message, db, role: str) -> None:
    if role != "owner":
        await message.answer("Bu buyruq faqat ega uchun.")
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Format: /adduser 123456789 Ism\n(ID ni u odam botga /id yozib biladi)")
        return
    name = parts[2] if len(parts) > 2 else "A'zo"
    await db.add_user(int(parts[1]), name, "member")
    await message.answer(f"✅ {escape(name)} qo'shildi. Endi u /start bosishi mumkin.")


@router.message(Command("users"))
async def list_users(message: Message, db) -> None:
    rows = await db.list_users()
    roles = {"owner": "admin", "member": "a'zo"}
    lines = [f"• {escape(r['name'] or '')} — <code>{r['tg_id']}</code> ({roles.get(r['role'], r['role'])})"
             for r in rows]
    await message.answer("<b>Foydalanuvchilar</b>\n" + "\n".join(lines))

