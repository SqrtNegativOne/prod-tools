"""
taskbar_autohide.pyw
Polls every POLL_INTERVAL_SEC seconds. Enables Windows taskbar auto-hide
when Anki or Obsidian has a maximised window; disables it otherwise.
Runs as a background tray-less process (.pyw = no console window).
"""

import ctypes
import ctypes.wintypes
import time
from pathlib import Path

from loguru import logger

_LOG_DIR = Path(__file__).parent.parent / "logs"
logger.add(_LOG_DIR / "taskbar_autohide.log", rotation="1 week", retention=2)

POLL_INTERVAL_SEC = 2
TARGET_APPS = {"anki", "obsidian"}

# ── Windows API constants ────────────────────────────────────────────────────
SW_SHOWMAXIMIZED = 3
ABM_GETSTATE     = 0x00000004
ABM_SETSTATE     = 0x0000000A
ABS_AUTOHIDE     = 0x00000001

user32  = ctypes.windll.user32
shell32 = ctypes.windll.shell32


class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length",           ctypes.wintypes.UINT),
        ("flags",            ctypes.wintypes.UINT),
        ("showCmd",          ctypes.wintypes.UINT),
        ("ptMinPosition",    ctypes.wintypes.POINT),
        ("ptMaxPosition",    ctypes.wintypes.POINT),
        ("rcNormalPosition", ctypes.wintypes.RECT),
    ]


class APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize",           ctypes.wintypes.DWORD),
        ("hWnd",             ctypes.wintypes.HWND),
        ("uCallbackMessage", ctypes.wintypes.UINT),
        ("uEdge",            ctypes.wintypes.UINT),
        ("rc",               ctypes.wintypes.RECT),
        ("lParam",           ctypes.wintypes.LPARAM),
    ]


_EnumWindowsProc = ctypes.WINFUNCTYPE(
    ctypes.c_bool,
    ctypes.wintypes.HWND,
    ctypes.wintypes.LPARAM,
)


def _set_taskbar_autohide(enable: bool) -> None:
    abd = APPBARDATA()
    abd.cbSize = ctypes.sizeof(APPBARDATA)
    abd.lParam = ABS_AUTOHIDE if enable else 0
    shell32.SHAppBarMessage(ABM_SETSTATE, ctypes.byref(abd))


def _any_target_maximised() -> bool:
    """Return True if any Anki or Obsidian window is currently maximised."""
    found: list[int] = []

    def _cb(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        placement = WINDOWPLACEMENT()
        placement.length = ctypes.sizeof(WINDOWPLACEMENT)
        if not user32.GetWindowPlacement(hwnd, ctypes.byref(placement)):
            return True
        if placement.showCmd != SW_SHOWMAXIMIZED:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.lower()
        if any(app in title for app in TARGET_APPS):
            found.append(hwnd)
        return True

    user32.EnumWindows(_EnumWindowsProc(_cb), 0)
    return bool(found)


def main() -> None:
    logger.info("taskbar_autohide starting.")
    last_state: bool | None = None

    while True:
        try:
            should_hide = _any_target_maximised()
            if should_hide != last_state:
                _set_taskbar_autohide(should_hide)
                logger.info("Taskbar auto-hide -> %s", should_hide)
                last_state = should_hide
        except Exception:
            logger.exception("Unexpected error in poll loop.")

        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
