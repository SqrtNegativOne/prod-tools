"""
Watchdawg
Runs at Windows logon. Reads app config from input/watchdawg.toml.
Every check_interval_sec, confirms each monitored app is in the process
list. If absent, waits relaunch_delay_sec (per-app or global), then
re-launches the executable.
"""

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from loguru import logger
import psutil

import tomli as tomllib


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SRC_DIR = Path(__file__).parent
ROOT_DIR = SRC_DIR.parent
_TOML_PATH = ROOT_DIR / "input" / "watchdawg.toml"
_LOG_DIR = ROOT_DIR / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
logger.add(_LOG_DIR / "watchdawg.log", rotation="1 week", retention=2)
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
    """Return True if a process with process_name is running."""
    target = process_name.lower()
    for p in psutil.process_iter(['name']):
        try:
            if p.info['name'] and p.info['name'].lower() == target:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


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
    log.info("Watchdawg initializing.")

    if not _TOML_PATH.exists():
        log.error("Config not found: %s", _TOML_PATH)
        return

    check_interval, initial_delay, apps = load_config(_TOML_PATH)

    log.info("Watchdawg started. Monitoring: %s", ", ".join(a.process_name for a in apps))
    log.info("Poll interval: %ds  |  Initial grace: %ds", check_interval, initial_delay)

    time.sleep(initial_delay)

    log.info("Watchdawg entering main loop.")

    while True:
        try:
            for app in apps:
                if is_running(app.process_name):
                    log.debug(f"{app.process_name} is running.")
                    continue

                log.info(
                    f"{app.process_name} not running. Waiting {app.relaunch_delay_sec}s before relaunch."
                )
                time.sleep(app.relaunch_delay_sec)
                if not is_running(app.process_name):
                    launch(app)
            
            time.sleep(check_interval)
        except Exception as e:
            log.exception(f"Unhandled exception in watchdawg main loop: {e}")
            time.sleep(60) # Prevent tight crash loops


if __name__ == "__main__":
    main()
