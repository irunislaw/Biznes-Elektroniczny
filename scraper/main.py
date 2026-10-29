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


def parse_product(html):
    soup = BeautifulSoup(html, "html.parser")

    data = json.loads(soup.select_one("#product-details")["data-product"])

    breadcrumb = [a.get_text() for a in soup.select("nav.breadcrumb li a span")]

    return {
        "id": data["id_product"],
        "name": data["name"],
        "description": data["description"],
        "price_brutto": data["price_amount"],
        "tax_rate": data["rate"],
        "attributes": data["features"],
        "url": data["link"],
        "image_urls": [img["bySize"]["large_default"]["url"] for img in data["images"]],
        "categories_path": breadcrumb[1:-1],
        "id_category_default": data["id_category_default"],
    }


def main():

    page = open("tests/fixtures/page-2.html", "rb").read()

    print(parse_product(page))

    # client = ShopClient(config.USER_AGENT, config.SHOP_URL, config.REQUESTS_PER_SECOND)
    # first_category_url = find_first_category_url(client, config.SCRAPER_START_URL)
    # links = scrape_category(client, first_category_url)

    # with open(config.SAVE_PATH, "w", encoding="utf-8") as file:
    #     json.dump(links, file)


if __name__ == "__main__":
    main()
