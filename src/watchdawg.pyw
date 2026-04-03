"""
Super Productivity Watchdog
----------------------------
Runs at Windows logon. Every CHECK_INTERVAL_SECONDS, confirms that
Super Productivity is in the process list. If absent, waits
RELAUNCH_DELAY_SECONDS, then launches the executable.

Edit SP_EXE_PATH if your install location differs.
"""

import os
import subprocess
import time
from loguru import logger

CHECK_INTERVAL_SEC  = 600   # how often to poll (10 min)
RELAUNCH_DELAY_SEC  = 600   # extra wait before launching after absence detected
INITIAL_DELAY_SEC   = 60    # grace period at system boot before first check

# Route logs to a file — required because .pyw has no console window
_log_dir = os.path.join(os.environ["APPDATA"], "Watchdawg")
os.makedirs(_log_dir, exist_ok=True)
logger.add(os.path.join(_log_dir, "watchdog.log"), rotation="1 week", retention=2)
log = logger

apps = { # process_name: exe_path
    'Super Productivity.exe': r"C:\Users\arkma\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Super Productivity.lnk"
}


def is_running(process_name: str) -> bool:
    """Return True if a process with process_name is in the task list."""
    result = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return process_name.lower() in result.stdout.lower()


def launch(exe_path: str) -> None:
    """Start the executable detached from this process."""
    subprocess.Popen(
        exe_path,
        shell=True,  # required to resolve .lnk shortcut files
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )
    log.info("Launched: %s", exe_path)

def main() -> None:
    log.info(f"Watchdawg started. Monitoring: {', '.join(apps.keys())}")
    log.info("Poll interval: %ds  |  Relaunch delay: %ds", CHECK_INTERVAL_SEC, RELAUNCH_DELAY_SEC)

    # Give the OS time to finish booting before the first check
    log.info("Initial grace period: %ds", INITIAL_DELAY_SEC)
    time.sleep(INITIAL_DELAY_SEC)

    while True:
        for app in apps:
             if not is_running(app):
                log.info(f"{app} not running. Waiting {RELAUNCH_DELAY_SEC}s before relaunch.")
                time.sleep(RELAUNCH_DELAY_SEC)
                if not is_running(app):   # still absent after the wait
                    launch(apps[app])
        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()