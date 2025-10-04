from apscheduler.schedulers.background import BackgroundScheduler, BlockingScheduler
from datetime import datetime, timedelta, time
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

GIVE_UP_AFTER  = time(23, 30)
GIVE_UP_BEFORE = time(3, 0)

INITIAL_NOTIF = time(23, 15)
APP_CLOSURE   = time(23, 30)
SHUTDOWN      = time(23, 59, 59)

CLOSURE_REACTION_SECONDS  = 30
SHUTDOWN_REACTION_SECONDS = 30
POST_SHUTDOWN_REMINDER_WAIT_SECONDS = 30

def notify(message: str, ms: int = 800):
    notif(title=WINDOW_TITLE, message=message, logger=logger, ms=ms)

def shutdown_computer():
    logger.info('Shutting down computer.')
    if not sys.platform.startswith('win'):
        logger.error("Shutdown not supported.")
        notify("Shutdown not supported on this platform.")
        return
    
    os.system("shutdown /s /f /t 1")

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
    scheduler = BlockingScheduler(timezone=get_localzone())

    now = datetime.now().astimezone()
    today = now.date()

    give_up_after = datetime.combine(today, GIVE_UP_AFTER).replace(tzinfo=get_localzone())
    give_up_before = datetime.combine(today, GIVE_UP_BEFORE).replace(tzinfo=get_localzone())

    if now > give_up_after or now < give_up_before:
        logger.info("Giving up on shutdown enforcement.")
        return
    
    initial_notif = datetime.combine(today, INITIAL_NOTIF).replace(tzinfo=get_localzone())
    app_closure = datetime.combine(today, APP_CLOSURE).replace(tzinfo=get_localzone())
    shutdown = datetime.combine(today, SHUTDOWN).replace(tzinfo=get_localzone())

    # Initial notification
    scheduler.add_job(
        lambda: notify(f"All active apps will close soon in {int((app_closure - initial_notif).total_seconds() // 60)} minutes. Save your work!"),
        'date',
        run_date=initial_notif
    )

    # Pre-closure notification
    scheduler.add_job(
        lambda: notify(f"Closing apps in {CLOSURE_REACTION_SECONDS} seconds!"),
        'date',
        run_date=app_closure - timedelta(seconds=CLOSURE_REACTION_SECONDS)
    )

    # Closure
    scheduler.add_job(
        close_all_foreground_windows,
        'date',
        run_date=app_closure
    )

    # Post-closure notification
    scheduler.add_job(
        lambda: notify(f"Apps closed. Shutdown in {int((shutdown - app_closure).total_seconds() // 60)} minutes."),
        'date',
        run_date=app_closure + timedelta(seconds=CLOSURE_REACTION_SECONDS + 5)
    )

    # Pre-shutdown notification
    scheduler.add_job(
        lambda: notify(f"Shutting down in {SHUTDOWN_REACTION_SECONDS} seconds!"),
        'date',
        run_date=shutdown - timedelta(seconds=SHUTDOWN_REACTION_SECONDS)
    )

    # Shutdown.
    scheduler.add_job(
        shutdown_computer,
        'date',
        run_date=shutdown
    )

    # Post-shutdown.
    scheduler.add_job(
        lambda: notify('Shutdown failed for some reason. Can you just shut it down yourself?', ms=2000),
        'date',
        run_date=shutdown + timedelta(seconds=POST_SHUTDOWN_REMINDER_WAIT_SECONDS)
    )

    logger.info("Scheduled all jobs. Entering main loop.")
    # Note: scheduler.start() blocks and will not return until all jobs are finished or the scheduler is stopped.
    scheduler.start()

if __name__ == "__main__":
    main()