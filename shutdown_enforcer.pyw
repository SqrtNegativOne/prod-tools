from time import sleep
from datetime import datetime, timedelta
import os
import sys
from plyer import notification
from pathlib import Path

import win32gui
import win32process
import psutil

# from windows_toasts import WindowsToaster, Toast
import tkinter

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


NOTIFY_AT = datetime.now().replace(hour=23, minute=15, second=0, microsecond=0)
CLOSE_APPS_AT = datetime.now().replace(hour=23, minute=30, second=0, microsecond=0)
SHUTDOWN_AT = datetime.now().replace(hour=23, minute=45, second=0, microsecond=0)

DAILY_OPENER_PATH = Path(__file__).parent / "daily-opener.pyw"


def notify(title, message):
    logging.info(f"Notification: {title} - {message}")
    # toaster = WindowsToaster('Brave Blocker')
    # newToast = Toast()
    # newToast.text_fields = [title, message]
    # toaster.show_toast(newToast)

    # Show a tkinter window with the notice for 2 seconds
    root = tkinter.Tk()
    root.title(title)
    root.geometry("350x100")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    label = tkinter.Label(root, text=message, font=("Segoe UI", 16), wraplength=320, justify="center")
    label.pack(expand=True, fill="both", padx=10, pady=10)
    root.after(1000, root.destroy)
    root.mainloop()

def shutdown_computer():
    if not sys.platform.startswith('win'):
        logger.error("Shutdown not supported.")
        notify("Shutdown Enforcer", "Shutdown not supported on this platform.")
        return
    
    os.system("shutdown /s /f /t 1")

def sleep_until(target_time: datetime):
    now = datetime.now()
    delta = (target_time - now).total_seconds()
    if delta > 0:
        sleep(delta)

def close_all_visible_windows():
    if not sys.platform.startswith('win'):
        print("Foreground app closing only supported on Windows.")
        return

    def enum_window_callback(hwnd, _):
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            username = proc.username()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return

        # Skip system processes and background services
        if username in ('SYSTEM', 'LOCAL SERVICE', 'NETWORK SERVICE'):
            return

        window_title = win32gui.GetWindowText(hwnd)
        if not window_title:
            # Likely background or untitled windows; skip
            return

        # Attempt to close the window
        logging.info(f"Closing window '{window_title}' from process '{proc.name()}' (PID: {pid})")
        win32gui.PostMessage(hwnd, 0x0010, 0, 0)  # WM_CLOSE

    win32gui.EnumWindows(enum_window_callback, None)

def monitor_time():
    now = datetime.now()

    if now < NOTIFY_AT:
        sleep_until(NOTIFY_AT)
        notify("Shutdown Enforcer", "All active apps will close at 23:30. Save your work!")

    if now < CLOSE_APPS_AT:
        sleep_until(CLOSE_APPS_AT)
        notify("Shutdown Enforcer", "Closing foreground apps in 20 seconds!")
        sleep(20)
        close_all_visible_windows()
        notify("Shutdown Enforcer", "Apps should be closed now.")

    if now < SHUTDOWN_AT:
        sleep_until(SHUTDOWN_AT)
        notify("Shutdown Enforcer", "Shutting down in 20 seconds!")
        sleep(20)
        shutdown_computer()
        notify("Shutdown Enforcer", "Computer should be closed now. how are you reading this???")
    
    if now > SHUTDOWN_AT + timedelta(minutes=5):
        return


if __name__ == "__main__":
    notify("Shutdown enforcer.", "Shutdown enforcer has started.")
    monitor_time()
