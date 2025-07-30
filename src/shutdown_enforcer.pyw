from time import sleep
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path

import win32gui
import win32process
import psutil

# from windows_toasts import WindowsToaster, Toast
import tkinter

from config import logger

NOTIFY_AT_HOUR = 23; NOTIFY_AT_MIN = 15 # 24 hour format

SECONDS_BEFORE_APP_CLOSURE = 15 * 60
SECONDS_BEFORE_SHUTDOWN = 15 * 60

ANTICIPATION_SECONDS = 20

def notify(message):
    title = "SHUTDOWN ENFORCER"
    logger.info(f"Notification: {title} - {message}")
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
    logger.info('Shutting down computer.')
    if not sys.platform.startswith('win'):
        logger.error("Shutdown not supported.")
        notify("Shutdown not supported on this platform.")
        return
    
    os.system("shutdown /s /f /t 1")
    logger.critical("Fuck that didn't work")

def close_all_foreground_windows():
    if not sys.platform.startswith('win'):
        print("Foreground app closing only supported on Windows.")
        return


    def enum_window_callback(hwnd, _):
        if not win32gui.IsWindowEnabled(hwnd):
            return
        if win32gui.GetParent(hwnd):
            return
        
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)

            window_title = win32gui.GetWindowText(hwnd)
            if not window_title.strip():
                return
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return
        except Exception as e:
            logger.warning(f"Unexpected error retrieving process info: {e}")
            return

        logger.info(f"Closing window '{window_title}' from process '{proc.name()}' (PID: {pid})")
        try:
            win32gui.PostMessage(hwnd, 0x0010, 0, 0)  # WM_CLOSE
        except Exception as e:
            logger.error(f"Failed to send WM_CLOSE to window '{window_title}': {e}")

    win32gui.EnumWindows(enum_window_callback, None)

def main():
    notify(f"Shutdown scheduled for {NOTIFY_AT_HOUR}:{NOTIFY_AT_MIN}.")

    now = datetime.now()
    NOTIFY_AT = now.replace(hour=NOTIFY_AT_HOUR, minute=NOTIFY_AT_MIN, second=0, microsecond=0)
    SECONDS_BEFORE_NOTIF: int = int((NOTIFY_AT - now).total_seconds())

    if SECONDS_BEFORE_NOTIF <= 0:
        notify("It's late anyway. Giving up shutdown enforcer now.")
        return

    sleep(SECONDS_BEFORE_NOTIF)
    notify(f"All active apps will close soon in {SECONDS_BEFORE_APP_CLOSURE // 60} minutes. Save your work!")

    sleep(SECONDS_BEFORE_APP_CLOSURE)
    notify(f"Closing foreground apps in {ANTICIPATION_SECONDS} seconds!")
    sleep(ANTICIPATION_SECONDS)
    close_all_foreground_windows()
    notify("Apps should be closed now.")

    sleep(SECONDS_BEFORE_SHUTDOWN)
    notify(f"Shutting down in {ANTICIPATION_SECONDS} seconds!")
    sleep(ANTICIPATION_SECONDS)
    shutdown_computer()


if __name__ == "__main__":
    main()
