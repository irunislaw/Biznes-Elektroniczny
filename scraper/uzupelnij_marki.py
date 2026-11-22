"""Uzupełnia markę (brand) produktom zapisanym w results.json.

Uruchomienie z katalogu scraper/:  python uzupelnij_marki.py,  potem python download_images.py (loga marek)

Działa jak uzupelnij_opisy.py: results.json powstał, zanim scraper zbierał markę, a przebieg od nowa
(main.py --od-nowa) zmieniłby też ceny, promocje i zbiór produktów. Ten skrypt pobiera tylko karty produktów,
które już są w results.json, i zmienia w nich jedno pole. Karty idą przez CachedClient (scraper-results/cache/),
więc ponowne uruchomienie nie wysyła zapytań do sklepu.
"""

import logging

import config
from cached_client import CachedClient
from main import load_saved_products, parse_product, save_products, setup_logging
from models import Brand
from shop_client import ShopClient

logger = logging.getLogger(__name__)


def fill_brands(products, client):
    """Ustawia brand z karty produktu; zwraca liczbę produktów, których karty nie udało się użyć.

    logo_file zostaje, gdy logo się nie zmieniło, więc ponowne uruchomienie po download_images.py go nie kasuje.
    """
    failed = 0
    for number, product in enumerate(products, 1):
        url = str(product.url)
        page = client.get(url)
        if page is None:
            logger.warning("Brak karty produktu %d, marka bez zmian: %s", product.id, url)
            failed += 1
            continue

        try:
            data = parse_product(url, page.content)
        except (ValueError, KeyError, TypeError) as e:
            logger.warning("Błędna karta produktu %d, marka bez zmian: %s (%s)", product.id, url, e)
            failed += 1
            continue

        if int(data["id"]) != product.id:
            logger.warning("Karta %s ma id %s zamiast %d, marka bez zmian", url, data["id"], product.id)
            failed += 1
            continue

        brand = Brand(**data["brand"]) if data["brand"] else None
        if brand and product.brand and brand.logo_url == product.brand.logo_url:
            brand.logo_file = product.brand.logo_file
        product.brand = brand
        if number % 100 == 0 or number == len(products):
            logger.info("Marki: %d/%d", number, len(products))
    return failed


def main():
    setup_logging("marki")
    products = load_saved_products(config.SAVE_PRODUCTS_PATH)
    client = ShopClient(
        config.USER_AGENT,
        config.SHOP_URL,
        config.REQUESTS_PER_SECOND,
        config.MAX_ATTEMPTS,
    )
    pages = CachedClient(client, config.PAGES_CACHE_PATH)

    try:
        failed = fill_brands(products, pages)
    finally:
        # Także po Ctrl+C: pobrane karty są w cache/, więc kolejne uruchomienie dokończy bez zapytań o nie
        save_products(config.SAVE_PRODUCTS_PATH, products)

    logger.info(
        "Koniec: produkty %d, z marką %d, bez marki %d, marki %d, nieudane %d",
        len(products),
        sum(p.brand is not None for p in products),
        sum(p.brand is None for p in products),
        len({p.brand.name for p in products if p.brand}),
        failed,
    )
    logger.info("Karty wzięte z dysku: %d, pobrane ze sklepu: %d", pages.stats["z dysku"], pages.stats["pobrane"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Przerwano (Ctrl+C). Uruchom ponownie, aby dokończyć.")
