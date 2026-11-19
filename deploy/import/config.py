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

# Marki dla produktów, które w sklepie źródłowym nie mają producenta (brand = null w results.json).
# Klucz: id produktu ze sklepu źródłowego (reference w sklepie), wartość: nazwa marki.
BRAND_BY_PRODUCT_ID = {
    6949: "Aquila",  # Aquila Thundergut 68U Struny do ukulele basowego
    6950: "Aquila",  # Aquila New Nylgut 10U Struny do ukulele tenorowego
}
# Klucz: id kategorii głównej ze sklepu źródłowego (id_category_default), wartość: nazwa marki.
# Używane, gdy produktu nie ma w BRAND_BY_PRODUCT_ID.
BRAND_BY_CATEGORY_ID = {}
