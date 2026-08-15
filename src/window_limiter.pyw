import time
import win32gui
import win32process
import win32con
import psutil
from dataclasses import dataclass, field
from typing import Set

POLL_INTERVAL_SECONDS = 0.3

@dataclass
class AppConfig:
    name: str
    exe_name: str
    class_name: str
    limit: int
    known_windows: Set[int] = field(default_factory=set)

def is_target_window(hwnd, exe_name, class_name):
    if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd):
        return False
    if class_name and win32gui.GetClassName(hwnd) != class_name:
        return False
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        return psutil.Process(pid).name().lower() == exe_name.lower()
    except psutil.NoSuchProcess:
        return False

def get_app_windows(exe_name, class_name):
    windows = []
    win32gui.EnumWindows(
        lambda hwnd, _: windows.append(hwnd) if is_target_window(hwnd, exe_name, class_name) else None,
        None
    )
    return windows

def enforce_window_limits(apps):
    for app in apps:
        app.known_windows = set(get_app_windows(app.exe_name, app.class_name))
        print(f"Watching {app.name}. Limit: {app.limit}. Currently open: {len(app.known_windows)}")

    while True:
        time.sleep(POLL_INTERVAL_SECONDS)
        for app in apps:
            current = set(get_app_windows(app.exe_name, app.class_name))
            app.known_windows &= current
            new = current - app.known_windows

            if not new or len(current) <= app.limit:
                continue

            for hwnd in new:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                current.discard(hwnd)

            app.known_windows = current

if __name__ == "__main__":
    monitored_apps = [
        AppConfig(
            name="Firefox",
            exe_name="firefox.exe",
            class_name="MozillaWindowClass", 
            limit=8
        ),
    ]
    enforce_window_limits(monitored_apps)