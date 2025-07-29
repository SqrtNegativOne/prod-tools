import os
from notion_client import Client
import webbrowser
from dotenv import load_dotenv

from config import logger

def get_latest_journal_page_id():
    NOTION_KEY = os.getenv("NOTION_KEY")
    if not NOTION_KEY:
        raise ValueError("NOTION_KEY environment variable is not set.")
    
    NOTION_JOURNAL_DATABASE_ID = os.getenv("NOTION_JOURNAL_DATABASE_ID")
    if not NOTION_JOURNAL_DATABASE_ID:
        raise ValueError("NOTION_JOURNAL_DATABASE_ID environment variable is not set.")
    
    notion = Client(auth=NOTION_KEY)
    response = notion.databases.query(
        database_id=NOTION_JOURNAL_DATABASE_ID,
        sorts=[
            {"property": "Date", "direction": "descending"}
        ],
        page_size=1
    )
    pages = response.get("results", []) # type: ignore
    logger.info(f"Here are the pages: {pages}")
    
    if not pages:
        raise ValueError("No pages found in the journal database.")
    
    page_id = pages[0]['id'].replace("-", "")
    logger.info(f"Latest journal page ID: {page_id}")
    return page_id

def main():
    load_dotenv()
    page_id = get_latest_journal_page_id()
    notion_deep_link = f"notion://www.notion.so/{page_id}"
    https_url        = f"https://www.notion.so/{page_id}"

    if not webbrowser.open(notion_deep_link):
        logger.error("Deep link failed, falling back to HTTPS.")
        if not webbrowser.open(https_url):
            logger.error("Failed to open Notion page via HTTPS.")

if __name__ == "__main__":
    main()