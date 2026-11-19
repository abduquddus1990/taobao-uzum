from aiogram import Router

from . import ai, calc_flow, cargos, common, market, products, quote, settings


def all_routers() -> list[Router]:
    # common birinchi: «Bekor qilish» har qanday holatda ishlashi uchun
    return [common.router, settings.router, cargos.router, calc_flow.router, products.router, market.router, ai.router,
            quote.router]
