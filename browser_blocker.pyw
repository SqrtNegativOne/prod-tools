import os
from dotenv import load_dotenv
import sys
import psutil
import wmi
import threading
from datetime import datetime, timezone, time
from time import sleep
from notion_client import Client
from pathlib import Path

import pythoncom

#from windows_toasts import WindowsToaster, Toast
import tkinter

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GIVE_UP_AFTER_THIS_HOUR   = 13 # 24 hour time format
DONT_TRY_BEFORE_THIS_HOUR =  6 # 24 hour time format
CAL_ITEMS_REQUIRED = 5

BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR / ".env"
SECRETS_DIR = BASE_DIR / "secrets"
CREDENTIALS_PATH = SECRETS_DIR / "credentials.json"
TOKENS_PATH = SECRETS_DIR / "token.json"

load_dotenv(ENV_PATH)

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

TODAY = datetime.now(timezone.utc).date()
TODAY_START = datetime.combine(TODAY, time.min, tzinfo=timezone.utc).isoformat()
TODAY_END = datetime.combine(TODAY, time.max, tzinfo=timezone.utc).isoformat()

DEBUG_MODE: bool = True # Set to False in production

ALL_NOTION_TASKS_SORTED: bool = False
ADEQUATE_GOOGLE_CAL_TASKS_SCHEDULED: bool = False


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

def no_notion_tasks_to_sort() -> bool:
    if ALL_NOTION_TASKS_SORTED: # Means we have already checked this before; no need to make another API call
        return True
    # Else, we have to check.

    NOTION_KEY = os.getenv("NOTION_KEY")
    if not NOTION_KEY:
        raise ValueError("NOTION_KEY environment variable is not set.")
    
    NOTION_TASKS_DATABASE_ID = os.getenv("NOTION_TASKS_DATABASE_ID")
    if not NOTION_TASKS_DATABASE_ID:
        raise ValueError("NOTION_TASKS_DATABASE_ID environment variable is not set.")

    notion = Client(auth=NOTION_KEY)
    response = notion.databases.query(
        database_id=NOTION_TASKS_DATABASE_ID,
        filter={
            "and": [
                {"property": "Status", "status": {"equals": "Todo"}},
                {"property": "Expected ROI", "select": {"is_empty": True}},
                {"property": "Scheduled", "date": {"is_empty": True}}
            ]
        }
    )
    try:
        to_sort_tasks = response.get("results", None) # type: ignore
    except Exception as e:
        notify(
            title="Failed to query Notion database",
            message=f"{e}",
        )
        raise ValueError(f"Failed to query Notion database: {e}")
    if to_sort_tasks is None:
        notify(
            title="Failed to retrieve tasks from Notion",
            message=f"Check your database ID and API key.",
        )
        raise ValueError("Failed to retrieve tasks from Notion. Check your database ID and API key.")
    if not isinstance(to_sort_tasks, list):
        notify(
            title="Unexpected response from Notion",
            message=f"Expected a list of tasks, got {type(to_sort_tasks)}.",
        )
        raise ValueError(f"Unexpected response from Notion: expected a list, got {type(to_sort_tasks)}.")
    
    if len(to_sort_tasks) == 0:
        return True
    
    notify(
        title="Sort tasks in Notion",
        message=f"You have {len(to_sort_tasks)} tasks to sort.",
    )
    return False

def get_credentials():
    creds = None
    if TOKENS_PATH.exists():
        creds = Credentials.from_authorized_user_file(TOKENS_PATH, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKENS_PATH, 'w') as token:
            token.write(creds.to_json())
    return creds

def fetch_num_calendar_items_for_one_calendar(service, calendar_id: str) -> int:
    """Fetch the number of calendar items for a single calendar."""
    try:
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=TODAY_START,
                timeMax=TODAY_END,
                maxResults=CAL_ITEMS_REQUIRED,  # Don't fetch more than we need
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get('items', None)
        return len(events) if events else 0
    except HttpError as error:
        notify(
            title="HttpError while retrieving calendar items",
            message=f"Error: {error}",
        )
        return 0

def adequate_google_cal_tasks_scheduled() -> bool:
    if ADEQUATE_GOOGLE_CAL_TASKS_SCHEDULED: # Means we have already checked this before; no need to make another API call
        return True
    # Else, we have to check.

    service = build('calendar', 'v3', credentials=get_credentials())
    calendar_list = service.calendarList().list().execute()
    calendar_ids = [calendar['id'] for calendar in calendar_list.get('items', [])]

    items_count = 0
    for calendar_id in calendar_ids:
        items_count += fetch_num_calendar_items_for_one_calendar(service, calendar_id)
        logging.info(f"Calendar ID: {calendar_id}, Items Count: {items_count}")
        if items_count >= CAL_ITEMS_REQUIRED:
            return True
    
    notify(
        title="Schedule tasks in Google Calendar",
        message=f"You have {items_count} tasks scheduled in Google Calendar, but you need {CAL_ITEMS_REQUIRED}."
    )
    return False

def sys_exit_if_requirements_fulfilled() -> None:
    current_hour: int = datetime.now().hour
    if not DEBUG_MODE and current_hour in range(GIVE_UP_AFTER_THIS_HOUR, DONT_TRY_BEFORE_THIS_HOUR):
        notify(
            title="It's late anyway.",
            message="You can use Brave.",
        )
        sys.exit(0)

    requirements = [
        no_notion_tasks_to_sort,
        adequate_google_cal_tasks_scheduled
    ]

    if all(req() for req in requirements):
        sys.exit(0)

def monitor_brave():
    pythoncom.CoInitialize()  # initialize COM for this thread

    c = wmi.WMI()
    watcher = c.Win32_Process.watch_for("creation")

    logging.info("Monitoring process creation.")

    while True:
        process_detected = watcher()

        name = process_detected.Caption.lower()
        if name != 'brave.exe':
            continue

        pid = process_detected.ProcessId
        try:
            p = psutil.Process(pid)
            parent = p.parent()
            if parent and parent.name().lower() == 'brave.exe':
                logging.info("Child brave process detected. Ignoring.")
                # If you kill the child, the parent will simply spawn a new one. Like Hydra.
                continue
            logging.info("Parent brave process detected.")

            sys_exit_if_requirements_fulfilled()

            logging.info("Requirements not satisfied, killing Brave process.")
            p.kill()
        except psutil.NoSuchProcess:
            logging.error(f"Process with PID {pid} no longer exists.")
            continue
        except psutil.AccessDenied:
            logging.error(f"Access denied when trying to kill Brave process {pid}.")
            continue
    
        sleep(1)

if __name__ == '__main__':
    notify(title="Brave Blocker Started", message="Monitoring Brave browser process.")
    threading.Thread(target=monitor_brave, daemon=True).start()
    threading.Event().wait()  # Keep main thread alive