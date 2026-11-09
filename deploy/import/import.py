import json
import logging
import random
import time
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlsplit

import config
import requests
import urllib3

urllib3.disable_warnings()

logger = logging.getLogger(__name__)


def api_get(resource, parameters=None):
    if parameters is None:
        parameters = {}
    response = requests.get(
        config.API_URL + "/" + resource,
        auth=config.LOGIN,
        params=parameters | {"output_format": "JSON"},
        verify=False,
    )
    response.raise_for_status()
    return response.json()


def api_post(resource, xml):
    response = requests.post(
        config.API_URL + "/" + resource,
        auth=config.LOGIN,
        params={"output_format": "JSON"},
        data=xml.encode("utf-8"),
        verify=False,
    )
    response.raise_for_status()
    return response.json()


def api_delete(resource):
    response = requests.delete(config.API_URL + "/" + resource, auth=config.LOGIN, verify=False)
    response.raise_for_status()


def api_patch(resource, xml):
    response = requests.patch(
        config.API_URL + "/" + resource,
        params={"output_format": "JSON"},
        auth=config.LOGIN,
        data=xml.encode("utf-8"),
        verify=False,
    )

    response.raise_for_status()
    return response.json()


def get_products(params=None):
    if params is None:
        params = {}
    products_get = api_get("products", params)
    if not products_get:
        return []

    return products_get["products"]


def get_categories(params=None):
    if params is None:
        params = {}
    categories_get = api_get("categories", params | {"filter[id]": f">[{config.HOME_CATEGORY_ID}]"})
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


def clear_products(product_id_map):
    products = get_products()
    id_in_database = product_id_map.values()
    for product in products:
        if product["id"] not in id_in_database:
            api_delete("products" + "/" + str(product["id"]))


def clear_categories(category_id_map):
    categories = get_categories()
    id_in_database = category_id_map.values()
    for category in categories:
        if category["id"] not in id_in_database:
            try:
                api_delete("categories" + "/" + str(category["id"]))
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    continue
                raise


def clear_sample_data(category_id_map, product_id_map):
    clear_products(product_id_map)
    clear_categories(category_id_map)


def create_category_xml(category, parent_id=config.HOME_CATEGORY_ID):
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


def create_product_xml(product, category_id, categories):
    price_netto_unquantized = Decimal(product["price_gross"]) / (1 + (Decimal(product["vat_rate_percent"])) / 100)
    price_netto_quantized = price_netto_unquantized.quantize(Decimal("0.000001"))
    tax_rules_group = config.TAX_RULES_GROUP_FOR_VAT_RATE[int(product["vat_rate_percent"])]
    categories_xml = "".join(f"<category><id>{c}</id></category>" for c in categories)
    xml = f"""
        <prestashop>
            <product>
                <id_category_default><![CDATA[{category_id}]]></id_category_default>
                <id_tax_rules_group><![CDATA[{tax_rules_group}]]></id_tax_rules_group>
                <reference><![CDATA[{product["id"]}]]></reference>
                <state><![CDATA[1]]></state>
                <product_type><![CDATA[standard]]></product_type>
                <price><![CDATA[{price_netto_quantized}]]></price>
                <active><![CDATA[1]]></active>
                <available_for_order>1</available_for_order>
                <show_price>1</show_price>
                <link_rewrite>
                    <language id="1"><![CDATA[{get_product_link_rewrite(product["url"])}]]></language>
                </link_rewrite>
                <name>
                    <language id="1"><![CDATA[{product["name"]}]]></language>
                </name>
                <description>
                    <language id="1"><![CDATA[{product["description"]}]]></language>
                </description>
                <associations>
                    <categories>
                    {categories_xml}
                    </categories>
                </associations>
                <weight><![CDATA[0]]></weight>
        </product>
    </prestashop>
    """

    return xml


def get_product_link_rewrite(product_url):
    path = urlsplit(product_url).path
    path_last_part = path.split("/")[-1]
    link_rewrite_without_html_ending = path_last_part.removesuffix(".html")
    link_rewrite_without_category_number = link_rewrite_without_html_ending.split("-")[1:]
    link_rewrite = "-".join(link_rewrite_without_category_number)

    return link_rewrite


def get_category_with_ancestors(category_id, category_parent_map):
    categories = []

    category = category_id
    while category != config.HOME_CATEGORY_ID:
        categories.append(category)
        category = category_parent_map[category]

    return categories


def add_products(products, products_in_database, category_id_map, category_parent_map):
    products_id_map = {}
    for product in products:
        if str(product["id"]) in products_in_database:
            product_id = products_in_database[str(product["id"])]
        else:
            original_category_ids = [product["id_category_default"]] + product["other_category_ids"]
            categories = set()
            for original_category_id in original_category_ids:
                if original_category_id in category_id_map:
                    ps_category_id = category_id_map[original_category_id]
                    categories.update(get_category_with_ancestors(ps_category_id, category_parent_map))
                else:
                    logger.warning(
                        "Produkt %d pominięty: kategoria %d spoza drzewa", product["id"], original_category_id
                    )

            default_id = category_id_map[product["id_category_default"]]
            product_id = add_product(product, default_id, categories)

        products_id_map[product["id"]] = product_id

    return products_id_map


def add_product(product, category_id, categories):
    xml = create_product_xml(product, category_id, categories)
    response = api_post("products", xml)

    product_id = response["product"]["id"]

    return int(product_id)


def add_categories(root, categories_in_database, category_parent_map, category_id_map):
    categories = root["children"]
    for category in categories:
        add_category(category, categories_in_database, category_parent_map, category_id_map)


def add_category(
    category, categories_in_database, category_parent_map, category_id_map, parent_id=config.HOME_CATEGORY_ID
):
    category_tuple = (parent_id, get_category_link_rewrite(category["url"]))
    subcategories = category["children"]

    if category_tuple in categories_in_database:
        category_id = categories_in_database[category_tuple]
    else:
        xml = create_category_xml(category, parent_id)
        response = api_post("categories", xml)
        category_id = int(response["category"]["id"])

    category_id_map[get_category_id(category["url"])] = category_id
    category_parent_map[category_id] = parent_id
    for subcategory in subcategories:
        add_category(subcategory, categories_in_database, category_parent_map, category_id_map, parent_id=category_id)


def create_stock_xml(stock_id, amount):
    xml = f"""
    <prestashop>
      <stock_available>
        <id>{stock_id}</id>
        <quantity>{amount}</quantity>
      </stock_available>
    </prestashop>
    """

    return xml


def set_stocks(products, product_id_map):
    stocks = api_get("stock_availables", {"display": "[id,id_product]"})["stock_availables"]
    stocks_in_database = {int(s["id_product"]): int(s["id"]) for s in stocks}
    empty_stocks = 0
    for product in products:
        source_id = product["id"]
        ps_id = product_id_map[source_id]
        stock_id = stocks_in_database[ps_id]
        rng = random.Random(config.RANDOM_SEED - source_id)
        stock_amount = rng.randint(0, 10)
        if stock_amount == 0:
            empty_stocks += 1
        xml = create_stock_xml(stock_id, stock_amount)
        api_patch(f"stock_availables/{stock_id}", xml)

    logger.info("Produktów o stanie 0: %d", empty_stocks)
    logger.info("Procentowo: %.2f%%", ((empty_stocks / len(products)) * 100))


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                config.LOGGING_PATH / f"import_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S.log')}",
                encoding="utf-8",
            ),
        ],
    )


def main():
    start_time = time.perf_counter()
    with open(config.SCRAPER_RESULTS_PATH / "category-tree.json", encoding="utf-8") as file:
        root = json.load(file)

        category_id_map = {}
        category_parent_map = {}
        categories_display = get_categories({"display": "[id,id_parent,link_rewrite]"})
        categories_in_database = {(int(c["id_parent"]), c["link_rewrite"]): int(c["id"]) for c in categories_display}

        add_categories(root, categories_in_database, category_parent_map, category_id_map)
    with open(config.SCRAPER_RESULTS_PATH / "results.json", encoding="utf-8") as file:
        products = json.load(file)
        products_display = get_products({"display": "[id,reference]"})
        products_in_database = {p["reference"]: int(p["id"]) for p in products_display}

        product_id_map = add_products(products, products_in_database, category_id_map, category_parent_map)

        set_stocks(products, product_id_map)

    clear_sample_data(category_id_map, product_id_map)

    end_time = time.perf_counter()
    logger.info("Czas importu: %.2fs", end_time - start_time)


if __name__ == "__main__":
    setup_logging()
    main()
