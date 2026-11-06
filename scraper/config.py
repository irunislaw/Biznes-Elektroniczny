from pathlib import Path

DIRECTORY = Path(__file__).parent

SHOP_URL = "https://gitara-sklep.pl"

USER_AGENT = "gitarasiema-scraper (https://github.com/irunislaw/Biznes-Elektroniczny; s203878@student.pg.edu.pl)"
REQUESTS_PER_SECOND = 2
MAX_ATTEMPTS = 8

FIXTURES_PATH = DIRECTORY / "tests/fixtures"
SAVE_URLS_PATH = DIRECTORY.parent / "scraper-results/results_urls.json"
SAVE_PRODUCTS_PATH = DIRECTORY.parent / "scraper-results/results.json"
SAVE_CATEGORY_TREE_PATH = DIRECTORY.parent / "scraper-results/category-tree.json"
LOGGING_PATH = DIRECTORY.parent / "scraper-results"

# Zdjęcia produktów (download_images.py, check_images.py)
IMAGES_PATH = DIRECTORY.parent / "scraper-results/images"
IMAGE_MAX_SIDE_PX = 1600
IMAGE_MIN_SIDE_PX = 800
# 300 000 B to ≤300 KB niezależnie od tego, czy 1 KB = 1000 B, czy 1024 B
IMAGE_MAX_BYTES = 300_000

CATEGORY_URLS = [
    "https://gitara-sklep.pl/10-ukulele",
    "https://gitara-sklep.pl/17-syntezatory-i-keyboardy",
    "https://gitara-sklep.pl/308-perkusja",
    "https://gitara-sklep.pl/274-harmonijki-ustne",
    "https://gitara-sklep.pl/290-przewody",
]
