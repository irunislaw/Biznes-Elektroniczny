import logging
from collections import Counter
from types import SimpleNamespace
from urllib.parse import urlsplit

from images import write_atomic

logger = logging.getLogger(__name__)


class CachedClient:
    """Zapisuje każdą pobraną kartę na dysk, a przy kolejnym uruchomieniu bierze ją z dysku zamiast ze sklepu.

    Ma tę samą metodę get co ShopClient, więc scrape_products i fetch_pages działają bez zmian.
    clear=True (--od-nowa) na starcie usuwa zapisane karty, więc wszystko jest pobierane od nowa.
    """

    def __init__(self, client, cache_dir, clear=False):
        self.client = client
        self.cache_dir = cache_dir
        self.stats = Counter()
        cache_dir.mkdir(parents=True, exist_ok=True)
        if clear:
            # Tylko karty i ewentualne .tmp z przerwanego zapisu, nie cały katalog
            files = list(cache_dir.glob("*.html*"))
            for file in files:
                file.unlink()
            logger.info("Wyczyszczono %s (usunięte pliki: %d)", cache_dir.name, len(files))

    def get(self, url):
        # Adres .../koncertowe/1589-ukulele-....html -> plik 1589.html (id produktu)
        product_id = urlsplit(url).path.rsplit("/", 1)[-1].split("-")[0]
        path = self.cache_dir / f"{product_id}.html"

        if path.exists():
            self.stats["z dysku"] += 1
            return SimpleNamespace(content=path.read_bytes())

        page = self.client.get(url)
        if page is not None:
            # Przez plik tymczasowy: przerwanie nie zostawi uciętej strony, którą kolejny przebieg uznałby za pobraną
            write_atomic(path, page.content)
            self.stats["pobrane"] += 1
        return page
