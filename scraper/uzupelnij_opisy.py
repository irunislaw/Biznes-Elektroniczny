"""Uzupełnia krótki opis (description_short) produktom zapisanym w results.json.

Uruchomienie z katalogu scraper/:  python uzupelnij_opisy.py

results.json powstał, zanim scraper zbierał krótki opis. Przebieg od nowa (main.py --od-nowa) zebrałby go,
ale zmieniłby też ceny, promocje i zbiór produktów, a za nimi zdjęcia i zrzut sklepu. Ten skrypt pobiera
tylko karty produktów, które już są w results.json, i zmienia w nich jedno pole. Karty idą przez
CachedClient (scraper-results/cache/), więc ponowne uruchomienie nie wysyła zapytań do sklepu.
"""

import logging

import config
from cached_client import CachedClient
from main import load_saved_products, parse_product, save_products, setup_logging
from shop_client import ShopClient

logger = logging.getLogger(__name__)


def fill_short_descriptions(products, client):
    """Ustawia description_short z karty produktu; zwraca liczbę produktów, których karty nie udało się użyć."""
    failed = 0
    for number, product in enumerate(products, 1):
        url = str(product.url)
        page = client.get(url)
        if page is None:
            logger.warning("Brak karty produktu %d, krótki opis bez zmian: %s", product.id, url)
            failed += 1
            continue

        try:
            data = parse_product(url, page.content)
        except (ValueError, KeyError, TypeError) as e:
            logger.warning("Błędna karta produktu %d, krótki opis bez zmian: %s (%s)", product.id, url, e)
            failed += 1
            continue

        if int(data["id"]) != product.id:
            logger.warning("Karta %s ma id %s zamiast %d, krótki opis bez zmian", url, data["id"], product.id)
            failed += 1
            continue

        product.description_short = data["description_short"]
        if number % 100 == 0 or number == len(products):
            logger.info("Krótkie opisy: %d/%d", number, len(products))
    return failed


def main():
    setup_logging("opisy")
    products = load_saved_products(config.SAVE_PRODUCTS_PATH)
    client = ShopClient(
        config.USER_AGENT,
        config.SHOP_URL,
        config.REQUESTS_PER_SECOND,
        config.MAX_ATTEMPTS,
    )
    pages = CachedClient(client, config.PAGES_CACHE_PATH)

    try:
        failed = fill_short_descriptions(products, pages)
    finally:
        # Także po Ctrl+C: pobrane karty są w cache/, więc kolejne uruchomienie dokończy bez zapytań o nie
        save_products(config.SAVE_PRODUCTS_PATH, products)

    logger.info(
        "Koniec: produkty %d, z krótkim opisem %d, bez krótkiego opisu %d, nieudane %d",
        len(products),
        sum(bool(p.description_short.strip()) for p in products),
        sum(not p.description_short.strip() for p in products),
        failed,
    )
    logger.info("Karty wzięte z dysku: %d, pobrane ze sklepu: %d", pages.stats["z dysku"], pages.stats["pobrane"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Przerwano (Ctrl+C). Uruchom ponownie, aby dokończyć.")
