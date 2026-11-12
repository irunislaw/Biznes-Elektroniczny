import argparse
import json
import logging
import os
from datetime import datetime
from urllib.parse import urlsplit

import config
from bs4 import BeautifulSoup
from models import Product
from pydantic import ValidationError
from shop_client import ShopClient

logger = logging.getLogger(__name__)

# Co ile pobranych kart produktów zapisywać results.json
BATCH_SIZE = 50


def parse_subcategory_urls(html):
    soup = BeautifulSoup(html, "html.parser")
    return [li.find("a").get("href") for li in soup.select("li[data-depth='0']")]


def parse_product_urls(html):
    soup = BeautifulSoup(html, "html.parser")
    urls = [a.get("href") for a in soup.select("a.product-thumbnail")]
    has_next = bool(soup.select("a[rel='next']"))

    return urls, has_next


def parse_category_name(html):
    soup = BeautifulSoup(html, "html.parser")
    category_name = soup.select_one("h1").text

    return category_name


def build_category_tree(client, page_url):
    page = client.get(page_url)

    if not page:
        return {"url": page_url, "name": "", "children": [], "products": [], "count": 0}

    subcategories = parse_subcategory_urls(page.content)

    if not subcategories:
        products = collect_products(client, page_url)
        return {
            "url": page_url,
            "name": parse_category_name(page.content),
            "children": [],
            "products": products,
            "count": len(products),
        }

    children = []
    for subcategory in subcategories:
        children.append(
            build_category_tree(
                client,
                subcategory,
            )
        )

    return {
        "url": page_url,
        "name": parse_category_name(page.content),
        "children": children,
        "products": [],
        "count": sum(child["count"] for child in children),
    }


def collect_products(client, page_url):
    page_counter = 1
    links = []
    while True:
        page = client.get(page_url + f"?page={page_counter}")

        if not page:
            break

        product_urls, has_next_page = parse_product_urls(page.content)
        links.extend(product_urls)

        if not has_next_page:
            break

        page_counter += 1

    return links


def collect_product_categories(node, product_categories):
    for product_url in node["products"]:
        if product_url not in product_categories:
            product_categories[product_url] = []
        product_categories[product_url].append(node["url"])

    for child in node["children"]:
        collect_product_categories(child, product_categories)


def collect_category_ids(node, category_ids):
    if node["url"]:
        category_ids.add(parse_category_id(node["url"]))
    for child in node["children"]:
        collect_category_ids(child, category_ids)


def parse_products(pages, product_categories, category_ids):
    results = []
    failed = 0
    skipped = 0
    for url, html in pages:
        try:
            data = parse_product(url, html)

            if int(data["id_category_default"]) not in category_ids:
                skipped += 1
                logger.warning("Pominięte (kategoria główna poza drzewem): %s", url)
                continue

            categories = product_categories[url]
            other_category_ids = [
                parse_category_id(category)
                for category in categories
                if parse_category_id(category) != int(data["id_category_default"])
            ]

            data["other_category_ids"] = other_category_ids
            product = Product(**data)
        except (ValidationError, ValueError, KeyError, TypeError) as e:
            logger.warning("Błędny rekord %s: %s", url, e)
            failed += 1
            continue

        results.append(product)
    return results, failed, skipped


def original_img_url(url):
    return url.replace("-large_default", "")


def parse_product(url, html):
    soup = BeautifulSoup(html, "html.parser")

    details = soup.select_one("#product-details")

    if details is None or not details.get("data-product"):
        raise ValueError("Brak details albo data-product")

    data = json.loads(details["data-product"])

    breadcrumb = [a.get_text() for a in soup.select("nav.breadcrumb li a span")]

    return {
        "id": data["id_product"],
        "name": data["name"],
        "description": data["description"],
        "price_gross": data["price_without_reduction"],
        "sale_price_gross": data["price_amount"] if data["has_discount"] else None,
        "vat_rate_percent": data.get("rate"),
        "attributes": {f["name"]: f["value"] for f in data["features"]},
        "url": url if url else data.get("link"),
        "image_urls": [original_img_url(img["large"]["url"]) for img in data["images"]],
        "category_path": breadcrumb[1:-1],
        "id_category_default": data["id_category_default"],
        "weight": data.get("weight"),
    }


def parse_category_id(url):
    path = urlsplit(url).path

    path_without_dash = path[1:]
    category_id = int(path_without_dash.split("-")[0])

    return category_id


def setup_logging(name="scraper"):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                config.LOGGING_PATH / f"{name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S.log')}",
                encoding="utf-8",
            ),
        ],
    )


def fetch_pages(client, urls):
    for url in urls:
        page = client.get(url)

        if not page:
            continue

        yield (url, page.content)


def save_json(path, data):
    """Zapis przez plik tymczasowy (jak write_atomic w images.py): przerwanie nie zostawia uciętego JSON-a.

    Tryb tekstowy i te same parametry json.dump co wcześniej, więc format pliku się nie zmienia.
    """
    tmp_path = path.with_name(path.name + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def load_saved_products(path):
    """Produkty z poprzedniego (np. przerwanego) przebiegu; bez pliku zaczynamy od zera."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as file:
        return [Product.model_validate(product) for product in json.load(file)]


def save_products(path, products):
    save_json(path, [product.model_dump(mode="json") for product in products])


def scrape_products(client, product_categories, category_ids, path, resume=True, batch_size=BATCH_SIZE):
    """Pobiera karty produktów, których jeszcze nie ma w path, i dopisuje je do tego pliku.

    Zapis idzie co batch_size pobranych kart oraz na końcu, także po Ctrl+C,
    więc kolejne uruchomienie nie pobiera już zapisanych produktów. resume=False zaczyna od pustej listy.
    """
    products = load_saved_products(path) if resume else []
    saved_urls = {str(product.url) for product in products}
    urls = [url for url in product_categories if url not in saved_urls]
    logger.info("Wczytane z %s: %d produktów, do pobrania: %d adresów", path.name, len(products), len(urls))

    failed = 0
    skipped = 0
    try:
        for number, page in enumerate(fetch_pages(client, urls), 1):
            parsed, page_failed, page_skipped = parse_products([page], product_categories, category_ids)
            products.extend(parsed)
            failed += page_failed
            skipped += page_skipped
            if number % batch_size == 0:
                save_products(path, products)
                logger.info("Zapisano %d produktów do %s", len(products), path.name)
    finally:
        # Także po Ctrl+C: kolejne uruchomienie pominie wszystko, co tu zapisano
        save_products(path, products)
        logger.info("Zapisano %d produktów do %s", len(products), path.name)

    return products, failed, skipped


def print_category_tree(tree, depth=0):
    print("\t" * depth, f"{tree['name']} {tree['count']}")
    if len(tree["children"]) == 0:
        for product in tree["products"]:
            print("\t" * (depth + 1), product)
    for child in tree["children"]:
        print_category_tree(child, depth=depth + 1)


def select_categories_without_empty_leaves_helper(tree):

    if tree["count"] < 5:
        return True

    for child in tree["children"]:
        has_empty_leaf = select_categories_without_empty_leaves_helper(child)
        if has_empty_leaf:
            return True

    return False


def select_categories_without_empty_leaves(tree):

    categories_without_empty_leaves = []

    for child in tree["children"]:
        has_empty_leaves = select_categories_without_empty_leaves_helper(child)
        if has_empty_leaves:
            continue

        categories_without_empty_leaves.append(child)

    return categories_without_empty_leaves


def count_products_in_categories():

    with open(config.SAVE_CATEGORY_TREE_PATH, encoding="utf-8") as file:
        categories = json.load(file)
        not_empty = select_categories_without_empty_leaves(categories)

        print(not_empty)


def count_saved(node, saved_urls):
    urls = {u for u in node["products"] if u in saved_urls}
    for child in node["children"]:
        urls |= count_saved(child, saved_urls)
    node["saved_count"] = len(urls)
    return urls


def count_subcategories(node):
    return sum(1 + count_subcategories(child) for child in node["children"])


def log_subcategories(node, depth=1):
    for child in node["children"]:
        logger.info("%s%s: %d", "  " * depth, child["name"], child["saved_count"])
        log_subcategories(child, depth + 1)


def log_summary(root, products, product_categories, rejected, skipped, client):
    categories = root["children"]
    time_elapsed, tempo = client.client_stats()

    logger.info("=== PODSUMOWANIE ===")
    logger.info("Znalezione na listach sklepu (unikalne adresy): %d", len(product_categories))
    logger.info("Pominięte (kategoria główna poza drzewem): %d", skipped)
    logger.info("Odrzucone przez walidację: %d", rejected)
    logger.info("Nieudane pobrania: %d", len(client.failed_urls))
    logger.info("Zapisane produkty: %d", len(products))
    logger.info("Produkty z co najmniej 2 zdjęciami: %d", sum(len(p.image_urls) >= 2 for p in products))
    logger.info("Kategorie: %d", len(categories))
    logger.info("Podkategorie: %d", count_subcategories(root) - len(categories))
    logger.info("Zapisane produkty według kategorii:")
    for category in categories:
        logger.info("%s: %d", category["name"], category["saved_count"])
        log_subcategories(category)

    logger.info("Czas scrapowania: %.2f s", time_elapsed)
    logger.info("Średnie tempo: %.2f zapytań/s", tempo)


def main(resume=True):
    setup_logging()
    client = ShopClient(
        config.USER_AGENT,
        config.SHOP_URL,
        config.REQUESTS_PER_SECOND,
        config.MAX_ATTEMPTS,
    )

    if resume and config.SAVE_CATEGORY_TREE_PATH.exists():
        # Drzewo z poprzedniego przebiegu: wznowienie nie pobiera list kategorii drugi raz
        logger.info("Drzewo kategorii wczytane z %s", config.SAVE_CATEGORY_TREE_PATH.name)
        with open(config.SAVE_CATEGORY_TREE_PATH, encoding="utf-8") as file:
            root = json.load(file)
    else:
        category_trees = [build_category_tree(client, tree) for tree in config.CATEGORY_URLS]
        root = {
            "url": None,
            "name": "glowna",
            "children": category_trees,
            "products": [],
            "count": sum([t["count"] for t in category_trees]),
        }
        save_json(config.SAVE_CATEGORY_TREE_PATH, root)

    product_categories = {}
    collect_product_categories(root, product_categories)

    category_ids = set()
    collect_category_ids(root, category_ids)

    save_json(config.SAVE_URLS_PATH, product_categories)

    products, failed, skipped = scrape_products(
        client, product_categories, category_ids, config.SAVE_PRODUCTS_PATH, resume=resume
    )

    saved_urls = {str(p.url) for p in products}
    count_saved(root, saved_urls)
    log_summary(root, products, product_categories, failed, skipped, client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pobiera produkty ze sklepu; wznawia od zapisanego results.json.")
    parser.add_argument("--od-nowa", action="store_true", help="ignoruje zapisane wyniki, pobiera wszystko od zera")
    try:
        main(resume=not parser.parse_args().od_nowa)
    except KeyboardInterrupt:
        logger.warning("Przerwano (Ctrl+C). Uruchom ponownie, aby wznowić od zapisanych wyników.")
