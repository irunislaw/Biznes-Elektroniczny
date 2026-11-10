"""Pobiera zdjęcia produktów z results.json, skaluje je i dopisuje przy produktach listę lokalnych plików.

Uruchomienie z katalogu scraper/ po main.py:  python download_images.py
Zdjęcia, które już są w scraper-results/images/, nie są pobierane drugi raz.
"""

import json
import logging

import config
from images import ImageDownloader
from main import setup_logging
from models import Product
from shop_client import ShopClient

logger = logging.getLogger(__name__)


def load_products(path):
    with open(path, encoding="utf-8") as file:
        return [Product.model_validate(product) for product in json.load(file)]


def save_products(path, products):
    with open(path, "w", encoding="utf-8") as file:
        json.dump([product.model_dump(mode="json") for product in products], file, ensure_ascii=False, indent=2)


def main():
    setup_logging("images")
    products = load_products(config.SAVE_PRODUCTS_PATH)
    config.IMAGES_PATH.mkdir(parents=True, exist_ok=True)
    # Ścieżki w wynikach są względne wobec katalogu z results.json, np. "images/487-1.jpg"
    prefix = config.IMAGES_PATH.relative_to(config.SAVE_PRODUCTS_PATH.parent).as_posix()

    client = ShopClient(
        config.USER_AGENT,
        config.SHOP_URL,
        config.REQUESTS_PER_SECOND,
        config.MAX_ATTEMPTS,
    )
    downloader = ImageDownloader(client, config.IMAGES_PATH)

    try:
        for number, product in enumerate(products, 1):
            logger.info("Produkt %d/%d: id %d", number, len(products), product.id)
            files = downloader.download(product.id, product.image_urls)
            product.image_files = [f"{prefix}/{name}" for name in files]
    finally:
        # Także po Ctrl+C: zapisane zdjęcia i tak zostają na dysku, a kolejne uruchomienie je pominie
        save_products(config.SAVE_PRODUCTS_PATH, products)
        stats = downloader.stats
        logger.info(
            "Koniec: pobrane %d, pominięte (już były) %d, błędy %d, małe (< %d px) %d",
            stats["pobrane"],
            stats["pominięte"],
            stats["błędy"],
            config.IMAGE_MIN_SIDE_PX,
            stats["małe"],
        )


if __name__ == "__main__":
    main()
