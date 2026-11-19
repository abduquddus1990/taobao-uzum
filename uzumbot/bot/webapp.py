"""Mini App serveri: statik sahifa + JSON API.

Har bir so'rov Telegram imzolagan initData bilan keladi (X-Init-Data sarlavhasi).
Imzo bot tokeni bilan tekshiriladi — shuning uchun manzilni bilgan begona odam ham
hech narsani o'qiy yoki o'zgartira olmaydi: faqat bazadagi foydalanuvchilar o'tadi.
"""
import json
import logging
import time
from dataclasses import asdict
from html import escape
from pathlib import Path
from typing import Any, Optional

from aiogram import Bot
from aiogram.utils.web_app import safe_parse_webapp_init_data
from aiohttp import web

from .calc import fmt
from .db import SETTINGS, STATUSES, Database
from .keyboards import app_button
from .render import VERDICT_ICON
from .cargo_import import cargos_context, guide_text, import_cargos
from .service import build_input, cargo_dict, product_dict, result_dict, stats
from .uzum_tariffs import MANUAL_URL, SOURCE_URL, TARIFFS

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent.parent / "webapp"
INIT_DATA_MAX_AGE = 7 * 24 * 3600   # ilova uzoq ochiq tursa ham ishlasin

DB_KEY = web.AppKey("db", Database)
BOT_KEY = web.AppKey("bot", Bot)
GEMINI_KEY = web.AppKey("gemini", object)
TOKEN_KEY = web.AppKey("token", str)


_ERRORS = {400: web.HTTPBadRequest, 401: web.HTTPUnauthorized, 403: web.HTTPForbidden,
           404: web.HTTPNotFound}


def ApiError(status: int, message: str) -> web.HTTPException:
    return _ERRORS[status](text=json.dumps({"error": message}, ensure_ascii=False),
                           content_type="application/json")


def _json(data: Any, status: int = 200) -> web.Response:
    return web.json_response(data, status=status, dumps=lambda o: json.dumps(o, ensure_ascii=False))


@web.middleware
async def auth_middleware(request: web.Request, handler):
    if not request.path.startswith("/api/"):
        return await handler(request)
    raw = request.headers.get("X-Init-Data", "")
    try:
        data = safe_parse_webapp_init_data(request.app[TOKEN_KEY], raw)
    except ValueError:
        raise ApiError(401, "Telegram imzosi noto'g'ri. Ilovani bot orqali oching.")
    if time.time() - data.auth_date.timestamp() > INIT_DATA_MAX_AGE:
        raise ApiError(401, "Sessiya eskirgan — ilovani qayta oching.")
    if not data.user:
        raise ApiError(401, "Foydalanuvchi aniqlanmadi")
    db = request.app[DB_KEY]
    row = await db.get_user(data.user.id)
    if not row:
        raise ApiError(403, f"Ruxsat yo'q. ID: {data.user.id}")
    request["user"] = {"id": row["tg_id"], "name": row["name"] or data.user.first_name, "role": row["role"]}
    try:
        return await handler(request)
    except ValueError as exc:
        raise ApiError(400, str(exc))


def _owner(request: web.Request) -> None:
    if request["user"]["role"] != "owner":
        raise ApiError(403, "Bu amal faqat admin uchun")


async def _body(request: web.Request) -> dict[str, Any]:
    try:
        data = await request.json()
    except Exception:
        raise ApiError(400, "JSON noto'g'ri")
    if not isinstance(data, dict):
        raise ApiError(400, "JSON obyekt kutilgan")
    return data


def _link(v: Optional[str]) -> Optional[str]:
    v = (v or "").strip()
    if not v:
        return None
    if not (v.startswith("http://") or v.startswith("https://")):
        raise ValueError("Link http(s):// bilan boshlanishi kerak")
    return v[:1000]


async def _cargo_id(db: Database, v) -> Optional[int]:
    if v in (None, "", 0):
        return None
    cid = int(v)
    return cid if await db.get_cargo(cid) else None


async def _cargo_names(db: Database) -> dict[int, str]:
    return {c["id"]: f"{c['name']} ({c['mode']})" for c in await db.list_cargos()}


async def _products(db: Database, settings: dict) -> list[dict]:
    names = await db.user_names()
    cargos = await _cargo_names(db)
    rows = await db.list_products(limit=500)
    return [product_dict(r, settings, names, cargos.get(r["cargo_id"], "qo'lda kiritilgan"),
                         TARIFFS.get(r["category_id"])) for r in rows]


async def _input_for(db: Database, body: dict):
    """So'rovdan CalcInput: tanlangan kargo va Uzum toifasi bilan (service.build_input)."""
    s = await db.get_settings()
    cargo_id = await _cargo_id(db, body.get("cargo_id"))
    cargo = await db.get_cargo(cargo_id) if cargo_id else None
    cat_id = body.get("category_id") or None
    cat = TARIFFS.get(cat_id) if cat_id else None
    if cat_id and not cat:
        raise ValueError("Uzum toifasi topilmadi")
    scheme = body.get("scheme") if body.get("scheme") in ("FBO", "FBS") else "FBO"
    if cat and cat["fbs" if scheme == "FBS" else "fbo"] is None:
        raise ValueError(f"Bu toifa {scheme} sxemasida sotilmaydi")
    inp = build_input(s, body.get("item") or {}, cargo, cat, scheme)
    return inp, cargo_id, (cat["id"] if cat else None), scheme


# ---------- handlers ----------

async def index(request: web.Request) -> web.FileResponse:
    resp = web.FileResponse(STATIC_DIR / "index.html")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


async def boot(request: web.Request) -> web.Response:
    db = request.app[DB_KEY]
    s = await db.get_settings()
    products = await _products(db, s)
    return _json({
        "me": request["user"],
        "settings": s,
        "settings_meta": [{"key": k, "title": t, "unit": u} for k, (t, _, u) in SETTINGS.items()],
        "statuses": STATUSES,
        "cargos": [cargo_dict(c) for c in await db.list_cargos()],
        "products": products,
        "stats": stats(products, s),
        "ai": bool(getattr(request.app[GEMINI_KEY], "enabled", False)),
        "tariffs": {"fetched_at": TARIFFS.fetched_at, "count": len(TARIFFS.by_id),
                    "source": SOURCE_URL, "manual": MANUAL_URL},
    })


async def get_categories(request: web.Request) -> web.Response:
    q = request.query.get("q", "")
    return _json({"categories": TARIFFS.search(q, limit=30)})


async def refresh_tariffs(request: web.Request) -> web.Response:
    _owner(request)
    ok, msg, changed = await TARIFFS.refresh()
    if not ok:
        raise ApiError(400, msg)
    return _json({"message": msg, "changed": len(changed), "fetched_at": TARIFFS.fetched_at})


async def post_import_cargos(request: web.Request) -> web.Response:
    """data_seed/cargos.json -> baza (nomi bo'yicha yangilanadi, takrorlanmaydi)."""
    _owner(request)
    res = await import_cargos(request.app[DB_KEY])
    return _json({"added": sum(1 for _, st in res if st == "yangi"),
                  "updated": sum(1 for _, st in res if st == "yangilandi"), "total": len(res)})


async def put_settings(request: web.Request) -> web.Response:
    _owner(request)
    body = await _body(request)
    db = request.app[DB_KEY]
    for key, value in body.items():
        if key not in SETTINGS:
            raise ApiError(400, f"Noma'lum sozlama: {key}")
        v = float(value)
        if v < 0:
            raise ValueError("Manfiy qiymat bo'lmaydi")
        await db.set_setting(key, v)
    return _json({"settings": await db.get_settings()})


def _cargo_payload(body: dict) -> dict[str, Any]:
    name = str(body.get("name") or "").strip()[:60]
    if not name:
        raise ValueError("Kargo nomi kerak")
    mode = body.get("mode") if body.get("mode") in ("avia", "avto") else "avto"
    tariff = float(body.get("tariff_usd_kg") or 0)
    if tariff <= 0:
        raise ValueError("Tarif 0 dan katta bo'lsin")

    def _int(v):
        return int(v) if v not in (None, "") else None

    def _num(v):
        if v in (None, ""):
            return None
        f = float(v)
        if f < 0:
            raise ValueError("Manfiy qiymat bo'lmaydi")
        return f
    dmin, dmax = _int(body.get("days_min")), _int(body.get("days_max"))
    if dmin and not dmax:
        dmax = dmin
    if dmin and dmax and dmax < dmin:
        dmin, dmax = dmax, dmin
    rating = _int(body.get("rating")) or 3
    return {"name": name, "mode": mode, "tariff_usd_kg": tariff, "days_min": dmin, "days_max": dmax,
            "white_docs": 1 if body.get("white_docs") else 0, "olmaliq": 1 if body.get("olmaliq") else 0,
            "note": (str(body.get("note") or "").strip()[:300] or None),
            "usd_m3": _num(body.get("usd_m3")), "vol_divisor": _num(body.get("vol_divisor")),
            "pickup_cost": _num(body.get("pickup_cost")), "rating": max(1, min(5, rating)),
            "verified": 1 if body.get("verified", True) else 0,
            "source": (str(body.get("source") or "").strip()[:300] or None),
            "series_ok": None if body.get("series_ok") is None else (1 if body.get("series_ok") else 0),
            "min_kg": _num(body.get("min_kg")),
            "checked_at": (str(body.get("checked_at") or "").strip()[:20] or None)}


async def post_cargo(request: web.Request) -> web.Response:
    db = request.app[DB_KEY]
    cid = await db.add_cargo(_cargo_payload(await _body(request)))
    return _json({"cargo": cargo_dict(await db.get_cargo(cid))}, 201)


async def put_cargo(request: web.Request) -> web.Response:
    db = request.app[DB_KEY]
    cid = int(request.match_info["id"])
    if not await db.get_cargo(cid):
        raise ApiError(404, "Kargo topilmadi")
    await db.update_cargo(cid, _cargo_payload(await _body(request)))
    return _json({"cargo": cargo_dict(await db.get_cargo(cid))})


async def delete_cargo(request: web.Request) -> web.Response:
    await request.app[DB_KEY].delete_cargo(int(request.match_info["id"]))
    return _json({"ok": True})


async def post_calc(request: web.Request) -> web.Response:
    inp, *_ = await _input_for(request.app[DB_KEY], await _body(request))
    return _json({"result": result_dict(inp)})


async def _notify_others(request: web.Request, text: str) -> None:
    db, bot, me = request.app[DB_KEY], request.app[BOT_KEY], request["user"]
    for u in await db.list_users():
        if u["tg_id"] == me["id"] or u["role"] != "owner":
            continue
        try:
            await bot.send_message(u["tg_id"], text, reply_markup=app_button("📱 Ilovada ko'rish"),
                                   disable_notification=True)
        except Exception as exc:
            log.info("Xabar yuborilmadi (%s): %s", u["tg_id"], exc)


async def _product_out(db: Database, pid: int) -> dict:
    s = await db.get_settings()
    row = await db.get_product(pid)
    cargos = await _cargo_names(db)
    return product_dict(row, s, await db.user_names(), cargos.get(row["cargo_id"], "qo'lda kiritilgan"),
                        TARIFFS.get(row["category_id"]))


async def post_product(request: web.Request) -> web.Response:
    db = request.app[DB_KEY]
    body = await _body(request)
    name = str(body.get("name") or "").strip()[:100]
    if not name:
        raise ValueError("Tovar nomini yozing")
    inp, cargo_id, cat_id, scheme = await _input_for(db, body)
    res = result_dict(inp)
    pid = await db.save_product(name, _link(body.get("source_link")), cargo_id, asdict(inp), res,
                                request["user"]["id"], body.get("status") or "idea",
                                (str(body.get("note") or "").strip()[:1000] or None), cat_id, scheme)
    me = request["user"]["name"]
    await _notify_others(request, f"🆕 <b>{escape(me)}</b> yangi tovar hisobladi: <b>{escape(name)}</b>\n"
                                  f"{VERDICT_ICON.get(res['verdict'], '')} foyda {fmt(res['profit'])} so'm "
                                  f"({res['margin_pct']:.0f}%), tannarx {fmt(res['landed'])} so'm")
    return _json({"product": await _product_out(db, pid)}, 201)


async def put_product(request: web.Request) -> web.Response:
    db = request.app[DB_KEY]
    pid = int(request.match_info["id"])
    old = await db.get_product(pid)
    if not old:
        raise ApiError(404, "Tovar topilmadi")
    body = await _body(request)
    fields: dict[str, Any] = {}
    if "name" in body:
        fields["name"] = str(body["name"] or "").strip()[:100] or old["name"]
    if "source_link" in body:
        fields["source_link"] = _link(body["source_link"])
    if "cargo_id" in body:
        fields["cargo_id"] = await _cargo_id(db, body["cargo_id"])
    if "note" in body:
        fields["note"] = str(body["note"] or "").strip()[:1000] or None
    if "status" in body:
        fields["status"] = body["status"]
    inp = res = None
    if body.get("item"):
        built, cargo_id, cat_id, scheme = await _input_for(db, body)
        inp, res = asdict(built), result_dict(built)
        fields.update(cargo_id=cargo_id, category_id=cat_id, scheme=scheme)
    await db.update_product(pid, fields, inp, res)
    if "status" in fields and fields["status"] != old["status"]:
        me = request["user"]["name"]
        await _notify_others(request, f"🔄 <b>{escape(me)}</b>: «{escape(old['name'])}» → "
                                      f"{STATUSES.get(fields['status'], fields['status'])}")
    return _json({"product": await _product_out(db, pid)})


async def delete_product(request: web.Request) -> web.Response:
    await request.app[DB_KEY].delete_product(int(request.match_info["id"]))
    return _json({"ok": True})


async def post_ai(request: web.Request) -> web.Response:
    gemini = request.app[GEMINI_KEY]
    if not getattr(gemini, "enabled", False):
        raise ApiError(400, "Gemini kaliti kiritilmagan")
    body = await _body(request)
    text = str(body.get("text") or "").strip()
    if not text:
        raise ValueError("Matn bo'sh")
    if len(text) > 8000:
        raise ValueError("Matn juda uzun (8000 belgigacha)")
    mode = body.get("mode")
    if mode == "tr":
        answer = await gemini.translate(text)
    elif mode == "card":
        answer = await gemini.card_text(text)
    elif mode == "seller":
        answer = await gemini.seller_message(text)
    elif mode == "cargo":
        ctx = cargos_context(await request.app[DB_KEY].list_cargos())
        answer = await gemini.cargo_answer(text, guide_text(), ctx)
    else:
        raise ValueError("Noma'lum rejim")
    return _json({"text": answer})


def create_app(db: Database, bot: Bot, gemini, token: str) -> web.Application:
    app = web.Application(middlewares=[auth_middleware], client_max_size=256 * 1024)
    app[DB_KEY] = db
    app[BOT_KEY] = bot
    app[GEMINI_KEY] = gemini
    app[TOKEN_KEY] = token
    app.router.add_get("/", index)
    app.router.add_static("/static/", STATIC_DIR, append_version=False)
    app.router.add_get("/api/boot", boot)
    app.router.add_put("/api/settings", put_settings)
    app.router.add_post("/api/cargos", post_cargo)
    app.router.add_put("/api/cargos/{id:\\d+}", put_cargo)
    app.router.add_delete("/api/cargos/{id:\\d+}", delete_cargo)
    app.router.add_post("/api/calc", post_calc)
    app.router.add_post("/api/products", post_product)
    app.router.add_put("/api/products/{id:\\d+}", put_product)
    app.router.add_delete("/api/products/{id:\\d+}", delete_product)
    app.router.add_post("/api/ai", post_ai)
    app.router.add_get("/api/categories", get_categories)
    app.router.add_post("/api/tariffs/refresh", refresh_tariffs)
    app.router.add_post("/api/cargos/import", post_import_cargos)
    return app


async def start_server(app: web.Application, port: int) -> web.AppRunner:
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()
    log.info("Mini App serveri: http://127.0.0.1:%s", port)
    return runner
