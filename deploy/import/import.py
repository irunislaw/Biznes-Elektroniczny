import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings()
load_dotenv()

API_URL = "https://localhost:8443/api"
SCRAPER_RESULTS_PATH = Path(__file__).resolve().parents[2] / "scraper-results"
LOGIN = (
    os.getenv("PS_WEBSERVICE_KEY"),
    "",
)  # API key as username, empty password

HOME_CATEGORY_ID = 2

TAX_RULES_GROUP_FOR_VAT_RATE = {23: 1, 8: 2, 5: 3, 0: 4}


def api_get(resource, parameters=None):
    if parameters is None:
        parameters = {}
    response = requests.get(
        API_URL + "/" + resource,
        auth=LOGIN,
        params=parameters | {"output_format": "JSON"},
        verify=False,
    )
    response.raise_for_status()
    return response.json()


def api_post(resource, xml):
    response = requests.post(
        API_URL + "/" + resource,
        auth=LOGIN,
        params={"output_format": "JSON"},
        data=xml.encode("utf-8"),
        verify=False,
    )
    response.raise_for_status()
    return response.json()


def api_delete(resource):
    response = requests.delete(API_URL + "/" + resource, auth=LOGIN, verify=False)
    response.raise_for_status()


def get_products():
    products_get = api_get("products")
    if not products_get:
        return []

    return products_get["products"]


def get_categories(params=None):
    if params is None:
        params = {}
    categories_get = api_get("categories", params | {"filter[id]": ">[2]"})
    if not categories_get:
        return []

    return categories_get["categories"]


def get_category_id(category_url):
    path = urlsplit(category_url).path

    path_without_dash = path[1:]
    category_id = int(path_without_dash.split("-")[0])

    return category_id


def get_category_link_rewrite(category_url):
    path = urlsplit(category_url).path
    path_without_dash = path[1:]
    link_rewrite_list = path_without_dash.split("-")[1:]
    link_rewrite = "-".join(link_rewrite_list)

    return link_rewrite


def clear_products():
    products = get_products()
    for product in products:
        api_delete("products" + "/" + str(product["id"]))


def clear_categories():
    categories = get_categories()
    for category in categories:
        try:
            api_delete("categories" + "/" + str(category["id"]))
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                continue


def clear_sample_data():
    clear_products()
    clear_categories()


def create_category_xml(category, parent_id=2):
    link_rewrite = get_category_link_rewrite(category["url"])
    xml = f"""
        <prestashop>
            <category>
                <id_parent>{parent_id}</id_parent>
                <active>1</active>
                <name>
                <language id="1"><![CDATA[{category["name"]}]]></language>
                </name>
                <link_rewrite>
                <language id="1"><![CDATA[{link_rewrite}]]></language>
                </link_rewrite>
            </category>
        </prestashop>
    """

    return xml


def add_products(products):
    pass


def add_categories(root, categories_in_database, category_id_map):
    categories = root["children"]
    for category in categories:
        add_category(category, categories_in_database, category_id_map)


def add_category(category, categories_in_database, category_id_map, parent_id=2):
    category_tuple = (parent_id, get_category_link_rewrite(category["url"]))
    subcategories = category["children"]

    if category_tuple in categories_in_database:
        category_id = categories_in_database[category_tuple]
    else:
        xml = create_category_xml(category, parent_id)
        response = api_post("categories", xml)
        category_id = response["category"]["id"]

    category_id_map[get_category_id(category["url"])] = category_id
    for subcategory in subcategories:
        add_category(subcategory, categories_in_database, category_id_map, category_id)


def main():
    with open(SCRAPER_RESULTS_PATH / "category-tree.json", encoding="utf-8") as file:
        root = json.load(file)

        category_id_map = {}
        categories_display = get_categories({"display": "[id,id_parent,link_rewrite]"})
        categories_in_database = {(int(c["id_parent"]), c["link_rewrite"]): c["id"] for c in categories_display}

        add_categories(root, categories_in_database, category_id_map)
    with open(SCRAPER_RESULTS_PATH / "results.json", encoding="utf-8") as file:
        products = json.load(file)
        add_products(products)

    print(len(category_id_map))
    print(category_id_map)


if __name__ == "__main__":
    # clear_sample_data()
    main()
