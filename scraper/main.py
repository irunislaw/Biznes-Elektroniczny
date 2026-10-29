import json
import logging
from datetime import datetime

import config
from bs4 import BeautifulSoup
from models import Product
from pydantic import ValidationError
from shop_client import ShopClient

logger = logging.getLogger(__name__)


def find_first_category_url(client, page_url):
    page = client.get(page_url)

    if not page:
        return None

    urls = parse_subcategory_urls(page.content)

    if urls:
        return urls[0]

    return None


def parse_subcategory_urls(html):
    soup = BeautifulSoup(html, "html.parser")
    return [li.find("a").get("href") for li in soup.select("li[data-depth='0']")]


def parse_product_urls(html):
    soup = BeautifulSoup(html, "html.parser")
    urls = [a.get("href") for a in soup.select("a.product-thumbnail")]
    has_next = bool(soup.select("a[rel='next']"))

    return urls, has_next


def collect_category_tree(client, page_url):
    page = client.get(page_url)

    if not page:
        return []

    subcategory_urls = []

    subcategories = parse_subcategory_urls(page.content)

    if not subcategories:
        return [page_url]

    for subcategory in subcategories:
        url = collect_category_tree(client, subcategory)
        subcategory_urls.extend(url)

    return subcategory_urls


def scrape_category(client, page_url):

    product_urls = set()
    category_tree = collect_category_tree(client, page_url)

    for url in category_tree:
        products = collect_products(client, url)
        for product in products:
            product_urls.add(product)

    return list(product_urls)


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


def parse_products(pages):
    results = []
    for url, html in pages:
        try:
            product = Product(**parse_product(url, html))
        except (ValidationError, ValueError, KeyError, TypeError) as e:
            logger.warning("Błędny rekord %s: %s", url, e)
            continue

        results.append(product)
    return results


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


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                config.LOGGING_PATH / f"scraper_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S.log')}",
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


def main():
    setup_logging()
    client = ShopClient(
        config.USER_AGENT,
        config.SHOP_URL,
        config.REQUESTS_PER_SECOND,
        config.MAX_ATTEMPTS,
    )

    first_category_url = find_first_category_url(client, config.SCRAPER_START_URL)
    links = scrape_category(client, first_category_url)

    with open(
        config.SAVE_URLS_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(links, file, ensure_ascii=False)

    pages = fetch_pages(client, links)
    products = parse_products(pages)
    products_json = [product.model_dump(mode="json") for product in products]

    with open(
        config.SAVE_PRODUCTS_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(products_json, file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
