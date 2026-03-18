"""
Weekly review opener: opens the most recent weekly review page in Notion,
mirroring daily_opener but for the weekly review database.
Requires NOTION_WEEKLY_REVIEW_DATABASE_ID in .env.
"""
import os
import webbrowser
from dotenv import load_dotenv
from notion_client import Client
from pathlib import Path
from loguru import logger

LOG_PATH = Path(__file__).parent.parent / 'log' / 'weekly_review_opener.log'
logger.add(LOG_PATH)


def get_latest_weekly_review_page_id():
    NOTION_KEY = os.getenv("NOTION_KEY")
    if not NOTION_KEY:
        raise ValueError("NOTION_KEY environment variable is not set.")

    NOTION_WEEKLY_REVIEW_DATABASE_ID = os.getenv("NOTION_WEEKLY_REVIEW_DATABASE_ID")
    if not NOTION_WEEKLY_REVIEW_DATABASE_ID:
        raise ValueError("NOTION_WEEKLY_REVIEW_DATABASE_ID environment variable is not set.")

    notion = Client(auth=NOTION_KEY)
    response = notion.databases.query(
        database_id=NOTION_WEEKLY_REVIEW_DATABASE_ID,
        sorts=[{"property": "Date", "direction": "descending"}],
        page_size=1
    )
    pages = response.get("results", [])  # type: ignore
    logger.info(f"Weekly review pages: {pages}")

    if not pages:
        raise ValueError("No pages found in the weekly review database.")

    page_id = pages[0]['id'].replace("-", "")
    logger.info(f"Latest weekly review page ID: {page_id}")
    return page_id


def main():
    load_dotenv()
    page_id = get_latest_weekly_review_page_id()
    notion_deep_link = f"notion://www.notion.so/{page_id}"
    https_url        = f"https://www.notion.so/{page_id}"

    if not webbrowser.open(notion_deep_link):
        logger.error("Deep link failed, falling back to HTTPS.")
        if not webbrowser.open(https_url):
            logger.error("Failed to open weekly review page via HTTPS.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
