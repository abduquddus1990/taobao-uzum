"""Botni doimiy ishlatish: qulasa yoki internet uzilib xato bersa — qayta ishga tushiradi.

Windows ishga tushganda Vazifalar rejalashtiruvchisi (Task Scheduler) shu faylni yashirin
(pythonw) ishga tushiradi — server/setup_server.ps1 ga qarang. Loglar: data/bot.log
"""
import datetime as dt
import os
import subprocess
import sys
import time
from logging.handlers import RotatingFileHandler
import logging
from pathlib import Path

BASE = Path(__file__).resolve().parent
LOG_DIR = BASE / "data"
LOG_DIR.mkdir(exist_ok=True)

log = logging.getLogger("supervisor")
handler = RotatingFileHandler(LOG_DIR / "supervisor.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
log.addHandler(handler)
log.setLevel(logging.INFO)


def python_exe() -> str:
    """Konsol oynasisiz ishlash uchun python.exe (pythonw bo'lsa ham bola jarayon python bo'ladi)."""
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        cand = exe.with_name("python.exe")
        if cand.exists():
            return str(cand)
    return str(exe)


_JOB = None


def kill_children_with_me() -> None:
    """Windows "Job Object": supervisor to'xtatilsa (Stop-ScheduledTask, qayta yuklash), uning bola
    jarayonlari — run.py va cloudflared — ham avtomatik o'ladi. Aks holda eski nusxa portni band
    qilib, osilib qoladi."""
    global _JOB
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes as w

    class BASIC(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", w.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", w.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD)]

    class IOC(ctypes.Structure):
        _fields_ = [(n, ctypes.c_uint64) for n in ("r", "w", "o", "rb", "wb", "ob")]

    class EXT(ctypes.Structure):
        _fields_ = [("Basic", BASIC), ("Io", IOC), ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = w.HANDLE
    k32.GetCurrentProcess.restype = w.HANDLE
    job = k32.CreateJobObjectW(None, None)
    info = EXT()
    info.Basic.LimitFlags = 0x2000            # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    ok = job and k32.SetInformationJobObject(w.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info)) \
        and k32.AssignProcessToJobObject(w.HANDLE(job), w.HANDLE(k32.GetCurrentProcess()))
    if ok:
        _JOB = job                             # handle ochiq tursin — yopilganda bolalar o'ladi
    else:
        log.warning("Job Object o'rnatilmadi (xato %s)", ctypes.get_last_error())


def main() -> None:
    kill_children_with_me()
    delay = 5
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    while True:
        started = time.time()
        log.info("Bot ishga tushirilmoqda")
        with open(LOG_DIR / "bot.log", "a", encoding="utf-8") as out:
            out.write(f"\n===== {dt.datetime.now():%Y-%m-%d %H:%M:%S} start =====\n")
            out.flush()
            env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
            code = subprocess.call([python_exe(), str(BASE / "run.py")], cwd=BASE, stdout=out,
                                   stderr=subprocess.STDOUT, env=env, creationflags=flags)
        ran = time.time() - started
        # uzoq ishlagan bo'lsa — tez qayta, tez-tez qulasa — kutish oshadi (5 s -> 5 daq)
        delay = 5 if ran > 600 else min(delay * 2, 300)
        log.info("Bot to'xtadi (kod %s, %.0f s ishladi). %s s dan keyin qayta ishga tushadi", code, ran, delay)
        time.sleep(delay)


if __name__ == "__main__":
    main()
