import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

API_URL = "https://localhost:8443/api"
SCRAPER_RESULTS_PATH = Path(__file__).resolve().parents[2] / "scraper-results"
LOGIN = (
    os.getenv("PS_WEBSERVICE_KEY"),
    "",
)  # API key as username, empty password

HOME_CATEGORY_ID = 2

TAX_RULES_GROUP_FOR_VAT_RATE = {23: 1, 8: 2, 5: 3, 0: 4}

RANDOM_SEED = 6112026

LOGGING_PATH = Path(__file__).parent

MAX_WORKERS = 8
TIMEOUT = 10
