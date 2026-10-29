from pathlib import Path

DIRECTORY = Path(__file__).parent

SHOP_URL = "https://gitara-sklep.pl"
SCRAPER_START_URL = "https://gitara-sklep.pl/2-katalog-produktow-gitara-no1"


USER_AGENT = "gitarasiema-scraper (https://github.com/irunislaw/Biznes-Elektroniczny; s203878@student.pg.edu.pl)"
REQUESTS_PER_SECOND = 2
MAX_ATTEMPTS = 3

FIXTURES_PATH = DIRECTORY / "tests/fixtures"
SAVE_URLS_PATH = DIRECTORY.parent / "scraper-results/results_urls.json"
SAVE_PRODUCTS_PATH = DIRECTORY.parent / "scraper-results/results.json"
LOGGING_PATH = DIRECTORY.parent / "scraper-results"
