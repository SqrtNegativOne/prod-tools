from pathlib import Path
from loguru import logger
LOG_PATH = Path(__file__).parent.parent / 'log' / 'out.log'
logger.add(LOG_PATH)