from apscheduler.schedulers.background import BackgroundScheduler, BlockingScheduler
from datetime import datetime, timedelta
from tzlocal import get_localzone
import os
import sys
from pathlib import Path

import win32gui
import win32process
import psutil

from utils import notif

from loguru import logger
LOG_PATH = Path(__file__).parent.parent / 'log' / 'shutdown_enforcer.log'
logger.add(LOG_PATH)

WINDOW_TITLE = 'SHUTDOWN ENFORCER'

NOTIFY_AT_HOUR = 23; NOTIFY_AT_MIN = 15 # 24 hour format

SECONDS_BEFORE_APP_CLOSURE = 15 * 60
SECONDS_BEFORE_SHUTDOWN = 15 * 60

ANTICIPATION_SECONDS = 20

def notify(message: str):
    notif(title=WINDOW_TITLE, message=message, logger=logger)

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

def schedule_tasks():
    scheduler = BlockingScheduler(timezone=get_localzone())

    now = datetime.now().astimezone()
    target_time = now.replace(
        hour=NOTIFY_AT_HOUR,
        minute=NOTIFY_AT_MIN,
        second=0,
        microsecond=0
    )
    if target_time < now:
        logger.info("It's too late to be running this script. giving up.")
        return

    scheduler.add_job(
        lambda: notify(f"All active apps will close soon in {SECONDS_BEFORE_APP_CLOSURE // 60} minutes. Save your work!"),
        'date',
        run_date=target_time
    )

    scheduler.add_job(
        lambda: [
            notify(f"Closing apps in {ANTICIPATION_SECONDS} seconds!"), 
            close_all_foreground_windows(),
            notify("Apps closed.")
        ],
        'date',
        run_date=target_time + timedelta(seconds=SECONDS_BEFORE_APP_CLOSURE)
    )

    scheduler.add_job(
        lambda: [
            notify(f"Shutting down in {ANTICIPATION_SECONDS} seconds!"),
            shutdown_computer()
        ],
        'date',
        run_date=target_time + timedelta(seconds=SECONDS_BEFORE_APP_CLOSURE + SECONDS_BEFORE_SHUTDOWN)
    )

    scheduler.start()

if __name__ == "__main__":
    notify('SE started.')
    schedule_tasks()