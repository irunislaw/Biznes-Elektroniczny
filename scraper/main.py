import json
import logging
from datetime import datetime
from urllib.parse import urlsplit

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


def print_category_tree(tree, depth=0):
    print("\t" * depth, f"{tree['url']} {tree['count']}")
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


def main():
    setup_logging()
    client = ShopClient(
        config.USER_AGENT,
        config.SHOP_URL,
        config.REQUESTS_PER_SECOND,
        config.MAX_ATTEMPTS,
    )

    category_trees = [build_category_tree(client, tree) for tree in config.CATEGORY_URLS]
    root = {
        "url": None,
        "name": "glowna",
        "children": category_trees,
        "products": [],
        "count": sum([t["count"] for t in category_trees]),
    }

    with open(config.SAVE_CATEGORY_TREE_PATH, "w", encoding="utf-8") as file:
        json.dump(root, file, ensure_ascii=False, indent=2)

    product_categories = {}
    collect_product_categories(root, product_categories)

    category_ids = set()
    collect_category_ids(root, category_ids)

    with open(config.SAVE_URLS_PATH, "w", encoding="utf-8") as file:
        json.dump(product_categories, file, ensure_ascii=False, indent=2)

    pages = fetch_pages(client, product_categories.keys())
    products, failed, skipped = parse_products(pages, product_categories, category_ids)
    products_json = [product.model_dump(mode="json") for product in products]
    with open(config.SAVE_PRODUCTS_PATH, "w", encoding="utf-8") as save:
        json.dump(products_json, save, indent=2, ensure_ascii=False)

    saved_urls = {str(p.url) for p in products}
    count_saved(root, saved_urls)
    log_summary(root, products, product_categories, failed, skipped, client)


if __name__ == "__main__":
    main()
