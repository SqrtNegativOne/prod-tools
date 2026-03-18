"""
Pomodoro timer: alternates between configurable work and break intervals,
notifying you at each transition. Run it once to start the cycle; it loops
until the process is killed.
"""
from pathlib import Path
from time import sleep

from loguru import logger

from utils import notif

LOG_PATH = Path(__file__).parent.parent / 'log' / 'pomodoro.log'
logger.add(LOG_PATH)

WORK_MINUTES  = 25
SHORT_BREAK_MINUTES = 5
LONG_BREAK_MINUTES  = 15
SESSIONS_BEFORE_LONG_BREAK = 4  # after this many work sessions, take a long break


def notify(title, message):
    notif(title=title, message=message, logger=logger)


def run():
    session = 0
    while True:
        session += 1
        logger.info(f"Starting work session {session} ({WORK_MINUTES} min).")
        notify("Pomodoro: Work", f"Session {session} — focus for {WORK_MINUTES} minutes.")
        sleep(WORK_MINUTES * 60)

        if session % SESSIONS_BEFORE_LONG_BREAK == 0:
            logger.info(f"Long break ({LONG_BREAK_MINUTES} min) after session {session}.")
            notify("Pomodoro: Long Break", f"Great work! Take a {LONG_BREAK_MINUTES}-minute break.")
            sleep(LONG_BREAK_MINUTES * 60)
        else:
            logger.info(f"Short break ({SHORT_BREAK_MINUTES} min) after session {session}.")
            notify("Pomodoro: Short Break", f"Take a {SHORT_BREAK_MINUTES}-minute break.")
            sleep(SHORT_BREAK_MINUTES * 60)


if __name__ == '__main__':
    logger.info("Pomodoro timer started.")
    notify("Pomodoro: Starting", f"Timer started. First session: {WORK_MINUTES} minutes.")
    try:
        run()
    except KeyboardInterrupt:
        logger.info("Pomodoro timer stopped by user.")
    except Exception as e:
        logger.exception(f"Pomodoro timer crashed: {e}")
