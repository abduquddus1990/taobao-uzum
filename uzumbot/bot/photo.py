"""📸 Foto studiya: Taobao rasmidan Uzum kartochkasi uchun toza rasm.

1) rembg bilan fon olib tashlanadi (bepul, kompyuterda ishlaydi, internet kerak emas);
2) tovar kesib olinib, oq fonli 3:4 (1080×1440) kartochka markaziga joylanadi;
3) natija: JPG (Uzum'ga yuklash uchun) + shaffof PNG (Canva/banner uchun).

rembg o'rnatilmagan bo'lsa ham ishlaydi — fonni olmaydi, faqat 3:4 oq kartochkaga moslaydi.
O'rnatish:  pip install "rembg[cpu]"   (birinchi ishga tushishda model ~170 MB yuklanadi)
"""
import io
import logging
import os
import threading
from dataclasses import dataclass
from typing import Optional

from PIL import Image, ImageFilter, ImageOps

log = logging.getLogger(__name__)

CARD_SIZE = (1080, 1440)     # Uzum: 3:4
PADDING = 0.07               # chetdan bo'sh joy
MODEL = os.getenv("REMBG_MODEL", "isnet-general-use")

_session = None
_lock = threading.Lock()


def rembg_available() -> bool:
    try:
        import rembg  # noqa: F401
        return True
    except Exception:
        return False


def _remove_bg(img: Image.Image) -> Image.Image:
    global _session
    from rembg import new_session, remove
    with _lock:                       # model bitta, CPU og'ir — navbat bilan
        if _session is None:
            log.info("rembg modeli yuklanmoqda: %s", MODEL)
            _session = new_session(MODEL)
        return remove(img, session=_session, post_process_mask=True)


@dataclass
class CardResult:
    jpg: bytes
    png: Optional[bytes]       # shaffof fonli tovar (fon olingan bo'lsa)
    bg_removed: bool
    src_size: tuple[int, int]


def _fit(obj: Image.Image, size: tuple[int, int], padding: float) -> tuple[Image.Image, tuple[int, int]]:
    w, h = size
    box_w, box_h = int(w * (1 - 2 * padding)), int(h * (1 - 2 * padding))
    scale = min(box_w / obj.width, box_h / obj.height)
    new = obj.resize((max(1, int(obj.width * scale)), max(1, int(obj.height * scale))), Image.LANCZOS)
    return new, ((w - new.width) // 2, (h - new.height) // 2)


def make_card(data: bytes, remove_bg: bool = True, size: tuple[int, int] = CARD_SIZE,
              padding: float = PADDING, shadow: bool = True, remover=None) -> CardResult:
    src = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGBA")
    remover = remover or (_remove_bg if remove_bg and rembg_available() else None)
    bg_removed = False
    obj = src
    if remove_bg and remover:
        try:
            cut = remover(src).convert("RGBA")
            bbox = cut.getchannel("A").point(lambda a: 255 if a > 10 else 0).getbbox()
            if bbox and (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) > 0.02 * src.width * src.height:
                obj, bg_removed = cut.crop(bbox), True
            else:
                log.warning("rembg tovarni topmadi — asl rasm ishlatiladi")
        except Exception as exc:
            log.warning("Fon olinmadi: %s", exc)

    canvas = Image.new("RGBA", size, (255, 255, 255, 255))
    fitted, pos = _fit(obj, size, padding)
    if bg_removed and shadow:
        # yumshoq soya: tovar "havoda" emas, stolda turgandek ko'rinadi
        alpha = fitted.getchannel("A")
        sh = Image.new("RGBA", fitted.size, (0, 0, 0, 0))
        sh.putalpha(alpha.point(lambda a: int(a * 0.22)))
        sh = sh.filter(ImageFilter.GaussianBlur(18))
        canvas.alpha_composite(sh, (pos[0] + 10, pos[1] + 16))
    canvas.alpha_composite(fitted, pos)

    out = io.BytesIO()
    canvas.convert("RGB").save(out, "JPEG", quality=92, optimize=True, progressive=True)
    png = None
    if bg_removed:
        buf = io.BytesIO()
        obj.save(buf, "PNG", optimize=True)
        png = buf.getvalue()
    return CardResult(out.getvalue(), png, bg_removed, src.size)
