import subprocess
import ctypes
from datetime import datetime, timedelta
from tzlocal import get_localzone
import os
import sys
from loguru import logger
from utils import notif

WINDOW_TITLE = "Shutdown Enforcer"

INITIAL_NOTIF = "19:00"
APP_CLOSURE = "19:25"
SHUTDOWN = "19:30"
GIVE_UP_BEFORE = "05:00"
GIVE_UP_AFTER = "23:30"

CLOSURE_REACTION_SECONDS = 30
SHUTDOWN_REACTION_SECONDS = 30
POST_SHUTDOWN_REMINDER_WAIT_SECONDS = 60

TASK_PREFIX = "ShutdownEnforcer_"

from pathlib import Path
BASE_DIR = Path(__file__).parent
LOG_PATH = os.path.join(BASE_DIR, "ShutdownEnforcer.log")


def notify(message: str, ms: int = 800):
    notif(title=WINDOW_TITLE, message=message, logger=logger, ms=ms)

def close_all_foreground_windows():
    import win32gui
    import win32process
    import psutil
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

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def parse_time(t):
    """Accepts 'HH:MM' or datetime.time and returns timezone-aware datetime for today."""
    tz = get_localzone()
    if isinstance(t, str):
        t = datetime.strptime(t, "%H:%M").time()
    return datetime.now(tz).replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)

def run_cmd(args):
    """Run a command safely, log output, and raise on failure."""
    try:
        result = subprocess.run(args, check=True, capture_output=True, text=True)
        if result.stdout.strip():
            logger.info(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        logger.info(f"Command failed: {' '.join(args)}\nError: {e.stderr.strip()}")
        raise

def delete_existing_tasks():
    """Delete previously created ShutdownEnforcer tasks."""
    result = subprocess.run(["schtasks", "/query", "/fo", "TABLE"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if TASK_PREFIX in line:
            parts = line.split()
            if parts:
                task_name = parts[0]
                logger.info(f"Deleting old task {task_name}")
                subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def create_task(name, command, run_time):
    """Create a one-time scheduled task at a given datetime."""
    if isinstance(run_time, str):
        run_time = parse_time(run_time)

    date_str = run_time.strftime("%Y/%m/%d")
    time_str = run_time.strftime("%H:%M:%S")
    full_name = f"{TASK_PREFIX}{name}_{run_time.strftime('%Y%m%d')}"

    cmd = [
        "schtasks", "/create",
        "/tn", full_name,
        "/tr", command,
        "/sc", "once",
        "/sd", date_str,
        "/st", time_str,
        "/ru", "SYSTEM"
    ]

    logger.info(f"Creating task: {full_name} at {run_time.isoformat()}")
    run_cmd(cmd)

def main():
    if not is_admin():
        logger.info("Error: Script must be run as administrator.")
        raise PermissionError("This script must be run with administrative privileges.")

    tz = get_localzone()
    now = datetime.now(tz)

    give_up_after = parse_time(GIVE_UP_AFTER)
    give_up_before = parse_time(GIVE_UP_BEFORE)

    if now > give_up_after or now < give_up_before:
        logger.info("Outside active scheduling hours. Exiting.")
        return

    delete_existing_tasks()

    initial_notif = parse_time(INITIAL_NOTIF)
    app_closure = parse_time(APP_CLOSURE)
    shutdown = parse_time(SHUTDOWN)

    if not (initial_notif < app_closure < shutdown):
        raise ValueError("Invalid time configuration: expected INITIAL_NOTIF < APP_CLOSURE < SHUTDOWN")

    closure_diff = int((app_closure - initial_notif).total_seconds() // 60)
    shutdown_diff = int((shutdown - app_closure).total_seconds() // 60)

    create_task(
        "InitialNotif",
        notify(f"All active apps will close soon in {closure_diff} minutes. Save your work! (Apps close at {APP_CLOSURE})"),
        initial_notif
    )

    create_task(
        "PreClosure",
        notify(f"Closing apps in {CLOSURE_REACTION_SECONDS} seconds! (Closure at {APP_CLOSURE})"),
        app_closure - timedelta(seconds=CLOSURE_REACTION_SECONDS)
    )

    create_task(
        "Closure",
        close_all_foreground_windows(),
        app_closure
    )

    create_task(
        "PostClosureNotif",
        notify(f"Apps closed. Shutdown in {shutdown_diff} minutes (at {SHUTDOWN})."),
        app_closure + timedelta(seconds=CLOSURE_REACTION_SECONDS + 5)
    )

    create_task(
        "PreShutdown",
        notify(f"Shutting down in {SHUTDOWN_REACTION_SECONDS} seconds! (Shutdown at {SHUTDOWN})"),
        shutdown - timedelta(seconds=SHUTDOWN_REACTION_SECONDS)
    )

    create_task(
        "Shutdown",
        "shutdown /s /t 0",
        shutdown
    )

    create_task(
        "PostShutdownReminder",
        notify("Shutdown may have failed. Please shut down manually."),
        shutdown + timedelta(seconds=POST_SHUTDOWN_REMINDER_WAIT_SECONDS)
    )

    logger.info("All tasks created successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.info(f"Fatal error: {e}")
        sys.exit(1)
