"""
Super Productivity Watchdog
----------------------------
Runs at Windows logon. Reads app config from input/watchdawg.toml.
Every check_interval_sec, confirms each monitored app is in the process
list. If absent, waits relaunch_delay_sec (per-app or global), then
re-launches the executable.
"""

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger

import tomli as tomllib


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_TOML_PATH = Path(__file__).parent.parent / "input" / "watchdawg.toml"

_log_dir = os.path.join(os.environ["APPDATA"], "Watchdawg")
os.makedirs(_log_dir, exist_ok=True)
logger.add(os.path.join(_log_dir, "watchdog.log"), rotation="1 week", retention=2)
log = logger


@dataclass
class AppConfig:
    process_name: str
    exe_path: str
    relaunch_delay_sec: int  # resolved to global default if not set in TOML


def load_config(toml_path: Path) -> tuple[int, int, list[AppConfig]]:
    """
    Returns (check_interval_sec, initial_delay_sec, list[AppConfig]).
    Per-app relaunch_delay_sec falls back to the global value when omitted.
    """
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    g = data.get("global", {})
    check_interval  = g.get("check_interval_sec", 600)
    initial_delay   = g.get("initial_delay_sec",  60)
    global_relaunch = g.get("relaunch_delay_sec", 600)

    apps = [
        AppConfig(
            process_name=app["process_name"],
            exe_path=app["exe_path"],
            relaunch_delay_sec=app.get("relaunch_delay_sec", global_relaunch),
        )
        for app in data.get("apps", [])
    ]
    return check_interval, initial_delay, apps


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def is_running(process_name: str) -> bool:
    """Return True if a process with process_name is in the task list."""
    result = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return process_name.lower() in result.stdout.lower()


def launch(app: AppConfig) -> None:
    """Start the executable detached from this process."""
    subprocess.Popen(
        app.exe_path,
        shell=True,  # required to resolve .lnk shortcut files
        creationflags=subprocess.DETACHED_PROCESS
                      | subprocess.CREATE_NEW_PROCESS_GROUP
                      | subprocess.CREATE_NO_WINDOW,
        close_fds=True,
    )
    log.info("Launched: %s", app.exe_path)


def main() -> None:
    check_interval, initial_delay, apps = load_config(_TOML_PATH)

    log.info("Watchdawg started. Monitoring: %s", ", ".join(a.process_name for a in apps))
    log.info("Poll interval: %ds  |  Initial grace: %ds", check_interval, initial_delay)

    time.sleep(initial_delay)

    while True:
        for app in apps:
            if not is_running(app.process_name):
                log.info(
                    "%s not running. Waiting %ds before relaunch.",
                    app.process_name, app.relaunch_delay_sec,
                )
                time.sleep(app.relaunch_delay_sec)
                if not is_running(app.process_name):
                    launch(app)
        time.sleep(check_interval)


if __name__ == "__main__":
    main()
