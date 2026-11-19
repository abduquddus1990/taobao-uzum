"""Tannarx va foyda hisob-kitobi. Faqat sof funksiyalar — test qilish oson.

MUHIM: webapp/calc.js bu faylning aynan nusxasi. Birini o'zgartirsangiz, ikkinchisini ham
o'zgartiring — tests/test_webapp.py ularni bir xil natija berishini tekshiradi.

Uzum qoidalari (seller.uzum.uz/manual/3.tariffs, 01.06.2026):
  * Komissiya toifaga bog'liq va EKVAYRINGNI O'Z ICHIGA OLADI (alohida ekvayring yo'q).
  * Logistika yig'imi hajm (litr) bo'yicha: 1 l gacha 5 250, har qo'shimcha litr +250, maks 50 000.
  * Saqlash faqat FBO uchun, aylanma 60 kundan oshsa.
"""
import math
from dataclasses import dataclass

LOGISTICS_BASE = 5250
LOGISTICS_PER_LITER = 250
LOGISTICS_MAX = 50000
STORAGE_STANDARD = ((60, 0), (180, 12), (360, 18), (10**9, 24))
STORAGE_SPECIAL = ((60, 0), (180, 12), (360, 14), (10**9, 18))
STORAGE_CAP_STANDARD = 5000
STORAGE_CAP_SPECIAL = 3000


@dataclass
class CalcInput:
    price_cny: float          # Xitoydagi narx, ¥ (1 dona)
    weight_g: float           # 1 dona vazni qadog'i bilan, gramm
    qty: int                  # partiyadagi dona
    tariff_usd_kg: float      # kargo tarifi, $/kg
    sell_price: float         # Uzumdagi sotuv narxi, so'm
    cny_rate: float           # 1 ¥ = ? so'm
    usd_rate: float           # 1 $ = ? so'm
    buyer_pct: float = 10     # bayer xizmati, %
    fx_spread_pct: float = 3  # konvertatsiya/karta xarajati, %
    trip_cost: float = 200_000  # kargodan uyga olib kelish (partiyaga), so'm
    commission_pct: float = 20  # Uzum komissiyasi (toifadan), %
    logistics_fee: float = 5_250  # o'lcham kiritilmaganda taxminiy logistika, so'm/dona
    tax_pct: float = 1        # aylanma solig'i, %
    payout_fee_pct: float = 0  # pul yechish xizmati: 2 haftada/oyda 0%, haftada 1%, har kuni 1.5%
    ads_pct: float = 10       # reklama, %
    returns_pct: float = 5    # brak va qaytarish, %
    target_margin_pct: float = 20  # maqsadli sof marja, %
    china_ship_cny: float = 0     # Xitoy ichida sotuvchidan kargo omborigacha, ¥ (partiyaga)
    pack_cost: float = 0          # qadoq, shtrix-kod stikeri, paket, so'm/dona
    length_cm: float = 0          # QADOG'I bilan o'lchamlari, sm
    width_cm: float = 0
    height_cm: float = 0
    vol_divisor: float = 6000     # kargo hajmiy vazni: sm³ / bo'luvchi = kg (0 — qo'llanmaydi)
    cargo_usd_m3: float = 0       # kargo kub metr narxi, $/m³ (0 — qo'llanmaydi)
    uzum_trip_cost: float = 0     # partiyani Uzum omboriga topshirish qatnovi, so'm
    uzum_vat_pct: float = 0       # Uzum xizmatlariga (komissiya, logistika) QQS ustama, %
    fbo: int = 1                  # 1 — Uzum omborida (FBO), 0 — o'z omborimizdan (FBS)
    sell_days: float = 0          # partiya necha kunda to'liq sotiladi (saqlash uchun)
    storage_special: int = 0      # toifa maxsus saqlash tarifidami
    storage_free_days: float = 30  # yangi stok bepul saqlanadigan kunlar


@dataclass
class CalcResult:
    goods: float
    buyer: float
    cargo: float
    trip: float               # kargodan olib kelish ulushi (1 dona)
    uzum_trip: float          # Uzum omboriga topshirish ulushi (1 dona)
    china_ship: float
    pack: float
    actual_kg: float
    volume_kg: float          # kargo hajmiy vazni
    charge_kg: float
    cargo_by_m3: bool         # kargo kub metr bo'yicha hisoblandimi
    liters: int               # Uzum hajmi (litr, yuqoriga yaxlitlangan); 0 — o'lcham yo'q
    landed: float             # 1 dona tannarx (uyimizgacha + Uzumga topshirish)
    commission: float
    logistics: float
    logistics_estimated: bool  # o'lcham yo'q — taxminiy
    tax: float
    payout: float
    ads: float
    returns: float
    storage: float            # FBO saqlash, 1 dona (taxminiy)
    fees: float               # sotuvdagi barcha xarajatlar
    profit: float
    margin_pct: float
    multiple: float
    breakeven_price: float
    target_price: float
    batch_cost: float
    batch_profit: float
    roi_pct: float
    verdict: str


def input_from_dict(d: dict) -> "CalcInput":
    """Saqlangan JSON'dan CalcInput (noma'lum/eskirgan kalitlarni e'tiborsiz qoldiradi)."""
    allowed = CalcInput.__dataclass_fields__.keys()
    return CalcInput(**{k: v for k, v in d.items() if k in allowed})


def _pct(x: float) -> float:
    return x / 100.0


def uzum_liters(l_cm: float, w_cm: float, h_cm: float) -> int:
    """Uzum qoidasi: U×E×B (mm) / 1 000 000, butunga yuqoriga. Sm'da: U×E×B / 1000."""
    if not (l_cm > 0 and w_cm > 0 and h_cm > 0):
        return 0
    return int(math.ceil(round(l_cm * w_cm * h_cm / 1000.0, 6)))


def uzum_logistics(liters: int) -> float:
    if liters <= 0:
        return 0.0
    return float(min(LOGISTICS_BASE + max(liters - 1, 0) * LOGISTICS_PER_LITER, LOGISTICS_MAX))


def storage_per_unit(liters: int, days: float, free_days: float, special: bool) -> float:
    """FBO saqlash, 1 donaga (taxminiy). Partiya `days` kunda tekis sotiladi deb olinadi:
    t-kuni qoldiq = 1 - t/days, aylanma = days - t kun. Yangi stok `free_days` kun bepul."""
    if liters <= 0 or days <= 0:
        return 0.0
    grid = STORAGE_SPECIAL if special else STORAGE_STANDARD
    cap = STORAGE_CAP_SPECIAL if special else STORAGE_CAP_STANDARD
    total = 0.0
    for t in range(int(math.ceil(days))):
        if t < free_days:
            continue
        turnover = math.ceil(days - t)
        rate = next(r for limit, r in grid if turnover <= limit)
        total += (1 - t / days) * min(rate * liters, cap)
    return total


def _price_for_margin(inp: CalcInput, landed: float, logistics: float, storage: float,
                      margin: float) -> float:
    vat = 1 + _pct(inp.uzum_vat_pct)
    c = _pct(inp.commission_pct) * vat
    t, p = _pct(inp.tax_pct), _pct(inp.payout_fee_pct)
    ads, ret = _pct(inp.ads_pct), _pct(inp.returns_pct)
    denom = 1 - c - t - ads - ret - p * (1 - c) - margin
    if denom <= 0:
        return float("inf")
    return (landed + logistics * (1 - p) + storage) / denom


def calculate(inp: CalcInput) -> CalcResult:
    if inp.qty <= 0:
        raise ValueError("Partiya soni 0 dan katta bo'lishi kerak")
    fx = 1 + _pct(inp.fx_spread_pct)
    goods = inp.price_cny * inp.cny_rate * fx
    buyer = goods * _pct(inp.buyer_pct)

    # --- kargo: haqiqiy vazn, hajmiy vazn yoki kub metr — qaysi biri qimmat bo'lsa ---
    actual_kg = inp.weight_g / 1000.0
    cm3 = inp.length_cm * inp.width_cm * inp.height_cm if (inp.length_cm > 0 and inp.width_cm > 0 and inp.height_cm > 0) else 0.0
    volume_kg = cm3 / inp.vol_divisor if (cm3 and inp.vol_divisor > 0) else 0.0
    charge_kg = max(actual_kg, volume_kg)
    cargo = charge_kg * inp.tariff_usd_kg * inp.usd_rate
    cargo_by_m3 = False
    if cm3 and inp.cargo_usd_m3 > 0:
        by_m3 = cm3 / 1_000_000 * inp.cargo_usd_m3 * inp.usd_rate
        if by_m3 > cargo:
            cargo, cargo_by_m3 = by_m3, True

    trip = inp.trip_cost / inp.qty
    uzum_trip = inp.uzum_trip_cost / inp.qty
    china_ship = inp.china_ship_cny * inp.cny_rate * fx / inp.qty
    pack = inp.pack_cost
    landed = goods + buyer + cargo + trip + uzum_trip + china_ship + pack

    # --- Uzum ---
    vat = 1 + _pct(inp.uzum_vat_pct)
    liters = uzum_liters(inp.length_cm, inp.width_cm, inp.height_cm)
    logistics_estimated = liters == 0
    logistics = (inp.logistics_fee if logistics_estimated else uzum_logistics(liters)) * vat
    storage = storage_per_unit(liters, inp.sell_days, inp.storage_free_days,
                               bool(inp.storage_special)) if inp.fbo else 0.0

    s = inp.sell_price
    commission = s * _pct(inp.commission_pct) * vat
    tax = s * _pct(inp.tax_pct)
    payout = max(s - commission - logistics, 0) * _pct(inp.payout_fee_pct)
    ads = s * _pct(inp.ads_pct)
    returns = s * _pct(inp.returns_pct)
    fees = commission + logistics + tax + payout + ads + returns + storage

    profit = s - landed - fees
    margin = profit / s * 100 if s else 0.0
    multiple = s / landed if landed else 0.0

    if margin >= 15 and multiple >= 3:
        verdict = "KIRAMIZ"
    elif margin >= 8:
        verdict = "EHTIYOT"
    else:
        verdict = "KIRMAYMIZ"

    return CalcResult(
        goods=goods, buyer=buyer, cargo=cargo, trip=trip, uzum_trip=uzum_trip, china_ship=china_ship,
        pack=pack, actual_kg=actual_kg, volume_kg=volume_kg, charge_kg=charge_kg, cargo_by_m3=cargo_by_m3,
        liters=liters, landed=landed, commission=commission, logistics=logistics,
        logistics_estimated=logistics_estimated, tax=tax, payout=payout, ads=ads, returns=returns,
        storage=storage, fees=fees, profit=profit, margin_pct=margin, multiple=multiple,
        breakeven_price=_price_for_margin(inp, landed, logistics, storage, 0.0),
        target_price=_price_for_margin(inp, landed, logistics, storage, _pct(inp.target_margin_pct)),
        batch_cost=landed * inp.qty,
        batch_profit=profit * inp.qty,
        roi_pct=(profit / landed * 100) if landed else 0.0,
        verdict=verdict,
    )


def fmt(x: float) -> str:
    """129000.4 -> '129 000'"""
    if x == float("inf"):
        return "∞"
    return f"{x:,.0f}".replace(",", " ")


def parse_number(text: str) -> float:
    """'129 000', '12,5', '1.5%' kabi kiritilgan qiymatni songa aylantiradi."""
    t = (text or "").strip().replace(" ", "").replace(" ", "").replace("%", "")
    t = t.replace("so'm", "").replace("som", "").replace("¥", "").replace("$", "")
    if t.count(",") == 1 and "." not in t:
        t = t.replace(",", ".")
    t = t.replace(",", "")
    value = float(t)
    if value < 0:
        raise ValueError("Manfiy son bo'lmaydi")
    return value
