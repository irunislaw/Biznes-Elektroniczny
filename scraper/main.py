import json

import config
from bs4 import BeautifulSoup
from shop_client import ShopClient


def find_first_category_url(client, page_url):
    page = client.get(page_url)

    if not page:
        return None

    soup = BeautifulSoup(page.content, "html.parser")

    # Najpierw wyciągamy HTML pierwszego linka z kategorią a następnie wyciągamy sam link
    first_category_link = soup.select_one("li[data-depth='0'] a")
    first_category_url = first_category_link.get("href")

    return first_category_url


def collect_category_tree(client, page_url):
    page = client.get(page_url)

    if not page:
        return None

    soup = BeautifulSoup(page.content, "html.parser")
    subcategory_urls = []

    subcategories = soup.select("li[data-depth='0']")

    if not subcategories:
        return [page_url]

    for subcategory in subcategories:
        subcategory_url = subcategory.find("a").get("href")
        url = collect_category_tree(client, subcategory_url)

        if url:
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
    links = set()
    while True:
        page = client.get(page_url + f"?page={page_counter}")

        if not page:
            break

        soup = BeautifulSoup(page.content, "html.parser")

        links_html = soup.select("a.product-thumbnail")

        for link in links_html:
            links.add(link.get("href"))

        if not soup.select("a[rel='next']"):
            break

        page_counter += 1

    return list(links)


client = ShopClient(config.USER_AGENT, config.SHOP_URL, config.REQUESTS_PER_SECOND)
first_category_url = find_first_category_url(client, config.SCRAPER_START_URL)
links = scrape_category(client, first_category_url)

print(len(links))

with open(config.SAVE_PATH, "w", encoding="utf-8") as file:
    json.dump(links, file)
