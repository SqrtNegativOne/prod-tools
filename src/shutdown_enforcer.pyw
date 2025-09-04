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

INITIAL_NOTIFY_AT_HOUR = 23; INITIAL_NOTIFY_AT_MIN = 15 # 24 hour format

SECONDS_BEFORE_APP_CLOSURE = 15 * 60
SECONDS_BEFORE_SHUTDOWN = 15 * 60

CLOSURE_REACTION_SECONDS = 20
SHUTDOWN_REACTION_SECONDS = 20

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
        hour=INITIAL_NOTIFY_AT_HOUR,
        minute=INITIAL_NOTIFY_AT_MIN,
        second=0,
        microsecond=0
    )
    if target_time < now:
        logger.info("It's too late to be running this script. giving up.")
        return

    # Initial notification
    scheduler.add_job(
        lambda: notify(f"All active apps will close soon in {SECONDS_BEFORE_APP_CLOSURE // 60} minutes. Save your work!"),
        'date',
        run_date=target_time
    )

    # Pre-closure notification
    scheduler.add_job(
        lambda: notify(f"Closing apps in {CLOSURE_REACTION_SECONDS} seconds!"),
        'date',
        run_date=target_time + timedelta(seconds=SECONDS_BEFORE_APP_CLOSURE)
    )

    # Closure
    scheduler.add_job(
        close_all_foreground_windows,
        'date',
        run_date=target_time + timedelta(seconds=SECONDS_BEFORE_APP_CLOSURE + CLOSURE_REACTION_SECONDS)
    )

    # Post-closure notification
    scheduler.add_job(
        lambda: notify(f"Apps closed. Shutdown in {SECONDS_BEFORE_SHUTDOWN // 60} minutes."),
        'date',
        run_date=target_time + timedelta(seconds=SECONDS_BEFORE_APP_CLOSURE + CLOSURE_REACTION_SECONDS + 5)
    )

    # Pre-shutdown notification
    scheduler.add_job(
        lambda: [
            notify(f"Shutting down in {SHUTDOWN_REACTION_SECONDS} seconds!"),
        ],
        'date',
        run_date=target_time + timedelta(seconds=SECONDS_BEFORE_APP_CLOSURE + SECONDS_BEFORE_SHUTDOWN)
    )

    # Shutdown.
    scheduler.add_job(
        shutdown_computer,
        'date',
        run_date=target_time + timedelta(seconds=SECONDS_BEFORE_APP_CLOSURE + SECONDS_BEFORE_SHUTDOWN + SHUTDOWN_REACTION_SECONDS)
    )

    scheduler.start()

if __name__ == "__main__":
    notify('SE started.')
    schedule_tasks()