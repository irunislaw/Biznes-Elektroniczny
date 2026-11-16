import json
import logging
import random
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        timeout=config.TIMEOUT,
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
        timeout=config.TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def api_delete(resource):
    response = requests.delete(config.API_URL + "/" + resource, auth=config.LOGIN, verify=False, timeout=config.TIMEOUT)
    response.raise_for_status()


def api_patch(resource, xml):
    response = requests.patch(
        config.API_URL + "/" + resource,
        params={"output_format": "JSON"},
        auth=config.LOGIN,
        data=xml.encode("utf-8"),
        verify=False,
        timeout=config.TIMEOUT,
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
    deleted = 0
    for product in products:
        if product["id"] not in id_in_database:
            api_delete("products" + "/" + str(product["id"]))
            deleted += 1
    logger.info("Usunięto %d produktów spoza importu", deleted)


def clear_categories(category_id_map):
    categories = get_categories()
    id_in_database = category_id_map.values()
    deleted = 0
    for category in categories:
        if category["id"] not in id_in_database:
            try:
                api_delete("categories" + "/" + str(category["id"]))
                deleted += 1
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    continue
                raise

    logger.info("Usunięto %d kategorii spoza importu", deleted)


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
    price_netto_quantized = net_price(product)
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
                <weight><![CDATA[{product.get("weight") or 0}]]></weight>
        </product>
    </prestashop>
    """

    return xml


def create_product_update_xml(ps_product_id, product):
    tax_rules_group = config.TAX_RULES_GROUP_FOR_VAT_RATE[int(product["vat_rate_percent"])]
    return f"""
        <prestashop>
            <product>
                <id>{ps_product_id}</id>
                <id_tax_rules_group><![CDATA[{tax_rules_group}]]></id_tax_rules_group>
                <price><![CDATA[{net_price(product)}]]></price>
                <description>
                    <language id="1"><![CDATA[{product["description"]}]]></language>
                </description>
                <weight><![CDATA[{product.get("weight") or 0}]]></weight>
            </product>
        </prestashop>
    """


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


def net_price(product):
    gross = Decimal(product["price_gross"])
    vat = Decimal(product["vat_rate_percent"])
    return (gross / (1 + vat / 100)).quantize(Decimal("0.000001"))


def update_product(ps_product_id, product):
    xml = create_product_update_xml(ps_product_id, product)
    api_patch(f"products/{ps_product_id}", xml)


def add_products(products, products_in_database, category_id_map, category_parent_map):
    products_id_map = {}
    added = updated = rejected = 0
    for i, product in enumerate(products, 1):
        if str(product["id"]) in products_in_database:
            try:
                product_id = products_in_database[str(product["id"])]
                update_product(product_id, product)
                updated += 1
            except (requests.RequestException, KeyError, ValueError, TypeError) as e:
                logger.error("Nie zaktualizowano produktu %d: %s", product["id"], e)
                rejected += 1
        else:
            original_category_ids = [product["id_category_default"]] + product["other_category_ids"]
            categories = set()
            for original_category_id in original_category_ids:
                if original_category_id in category_id_map:
                    ps_category_id = category_id_map[original_category_id]
                    categories.update(get_category_with_ancestors(ps_category_id, category_parent_map))
                else:
                    logger.warning(
                        "Produkt %d: kategoria %d spoza drzewa, pomijam przypisanie",
                        product["id"],
                        original_category_id,
                    )

            try:
                default_id = category_id_map[product["id_category_default"]]
                product_id = add_product(product, default_id, categories)
                added += 1
            except (requests.RequestException, KeyError, ValueError, TypeError) as e:
                logger.error("Nie dodano produktu: %d. Powód: %s", product["id"], e)
                rejected += 1
                continue

        products_id_map[product["id"]] = product_id
        if i % 100 == 0 or i == len(products):
            logger.info("Produkty: %d/%d", i, len(products))

    return products_id_map, added, updated, rejected


def add_product(product, category_id, categories):
    xml = create_product_xml(product, category_id, categories)
    response = api_post("products", xml)

    product_id = response["product"]["id"]

    return int(product_id)


def create_category_update_xml(ps_category_id, category):
    return f"""
        <prestashop>
            <category>
                <id>{ps_category_id}</id>
                <name>
                    <language id="1"><![CDATA[{category["name"]}]]></language>
                </name>
            </category>
        </prestashop>
    """


def update_category(ps_category_id, category):
    xml = create_category_update_xml(ps_category_id, category)
    api_patch(f"categories/{ps_category_id}", xml)


def add_categories(root, categories_in_database, category_parent_map, category_id_map):
    counter = {"added": 0, "updated": 0, "rejected": 0}
    categories = root["children"]
    for category in categories:
        add_category(category, categories_in_database, category_parent_map, category_id_map, counter)

    return counter


def count_descendants(category):
    return sum(1 + count_descendants(child) for child in category["children"])


def add_category(
    category, categories_in_database, category_parent_map, category_id_map, counter, parent_id=config.HOME_CATEGORY_ID
):
    category_tuple = (parent_id, get_category_link_rewrite(category["url"]))
    subcategories = category["children"]

    if category_tuple in categories_in_database:
        try:
            category_id = categories_in_database[category_tuple]
            update_category(category_id, category)
            counter["updated"] += 1
        except (requests.RequestException, KeyError, ValueError) as e:
            logger.error("Nie zaktualizowano kategorii %s: %s", category["name"], e)
            counter["rejected"] += 1

    else:
        try:
            xml = create_category_xml(category, parent_id)
            response = api_post("categories", xml)
            category_id = int(response["category"]["id"])
            counter["added"] += 1
        except (requests.RequestException, KeyError, ValueError) as e:
            logger.error("Nie dodano kategorii: %s. Powód: %s", category["name"], e)
            counter["rejected"] += 1
            skipped = count_descendants(category)
            if skipped:
                logger.error("Pominięto %d podkategorii kategorii %s", skipped, category["name"])
                counter["rejected"] += skipped
            return

    category_id_map[get_category_id(category["url"])] = category_id
    category_parent_map[category_id] = parent_id
    for subcategory in subcategories:
        add_category(
            subcategory, categories_in_database, category_parent_map, category_id_map, counter, parent_id=category_id
        )


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
    for i, product in enumerate(products, 1):
        if i % 100 == 0 or i == len(products):
            logger.info("Stany: %d/%d", i, len(products))

        source_id = product["id"]
        ps_id = product_id_map.get(source_id)

        if ps_id is None:
            continue

        try:
            stock_id = stocks_in_database[ps_id]
            rng = random.Random(config.RANDOM_SEED - source_id)
            stock_amount = rng.randint(0, 10)
            if stock_amount == 0:
                empty_stocks += 1
            xml = create_stock_xml(stock_id, stock_amount)
            api_patch(f"stock_availables/{stock_id}", xml)
        except (requests.RequestException, KeyError, ValueError) as e:
            logger.error("Nie ustawiono stanu produktu %d: %s", source_id, e)

    logger.info("Produktów o stanie 0: %d", empty_stocks)
    logger.info("Procentowo: %.2f%%", ((empty_stocks / len(products)) * 100))


def create_specific_price_xml(ps_product_id, reduction, sp_id=None):
    id_xml = f"<id>{sp_id}</id>" if sp_id else ""
    return f"""
        <prestashop>
            <specific_price>
                {id_xml}
                <id_product>{ps_product_id}</id_product>
                <id_product_attribute>0</id_product_attribute>
                <id_shop>0</id_shop>
                <id_cart>0</id_cart>
                <id_currency>0</id_currency>
                <id_country>0</id_country>
                <id_group>0</id_group>
                <id_customer>0</id_customer>
                <from_quantity>1</from_quantity>
                <price>-1</price>
                <reduction>{reduction}</reduction>
                <reduction_tax>1</reduction_tax>
                <reduction_type>amount</reduction_type>
                <from>0000-00-00 00:00:00</from>
                <to>0000-00-00 00:00:00</to>
            </specific_price>
        </prestashop>
    """


def set_promotions(products, product_id_map):
    counter = {"added": 0, "updated": 0, "deleted": 0, "rejected": 0}

    planned = {}
    for p in products:
        ps_id = product_id_map.get(p["id"])
        if ps_id is not None and p.get("sale_price_gross") is not None:
            planned[ps_id] = Decimal(p["price_gross"]) - Decimal(p["sale_price_gross"])

    existing = api_get("specific_prices", {"display": "[id,id_product]", "filter[id_cart]": "[0]"})
    existing = {int(sp["id_product"]): int(sp["id"]) for sp in (existing or {}).get("specific_prices", [])}

    for ps_id, reduction in planned.items():
        try:
            if ps_id in existing:
                sp_id = existing[ps_id]
                api_patch(f"specific_prices/{sp_id}", create_specific_price_xml(ps_id, reduction, sp_id))
                counter["updated"] += 1
            else:
                api_post("specific_prices", create_specific_price_xml(ps_id, reduction))
                counter["added"] += 1
        except (requests.RequestException, KeyError, ValueError) as e:
            logger.error("Nie ustawiono promocji produktu %d: %s", ps_id, e)
            counter["rejected"] += 1

    for ps_id, sp_id in existing.items():
        if ps_id not in planned:
            try:
                api_delete(f"specific_prices/{sp_id}")
                counter["deleted"] += 1
            except requests.RequestException as e:
                logger.error("Nie usunięto promocji %d: %s", sp_id, e)

    return counter


def add_image(product_id, image_path):
    with open(config.SCRAPER_RESULTS_PATH / image_path, "rb") as image:
        response = requests.post(
            config.API_URL + "/images/products/" + str(product_id),
            auth=config.LOGIN,
            files={"image": ("image.jpg", image, "image/jpeg")},
            verify=False,
            timeout=config.TIMEOUT,
        )

        response.raise_for_status()


def add_product_images(ps_product_id, image_files):
    for image_file in image_files:
        add_image(ps_product_id, image_file)


def add_images(products, product_id_map):
    response = requests.get(
        config.API_URL + "/images/products", auth=config.LOGIN, verify=False, timeout=config.TIMEOUT
    )
    response.raise_for_status()

    products_with_images = set()
    root = ET.fromstring(response.content)
    for el in root.findall("images/image"):
        products_with_images.add(int(el.get("id")))

    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        futures = {}
        for product in products:
            ps_product_id = product_id_map.get(product["id"])

            if ps_product_id is None:
                continue

            if ps_product_id in products_with_images:
                continue

            futures[executor.submit(add_product_images, ps_product_id, product["image_files"])] = ps_product_id

        for done, future in enumerate(as_completed(futures), 1):
            try:
                future.result()
            except (requests.RequestException, OSError) as e:
                logger.error("Nie udało się dodać zdjęć dla produktu: %d %s", futures[future], e)

            if done % 100 == 0 or done == len(futures):
                logger.info("Zdjęcia: %d/%d", done, len(futures))


def create_ps_menu_xml(id_menu, value, date):
    xml = f"""
        <prestashop>
            <configuration>
                <id>{id_menu}</id>
                <value>{value}</value>
                <date_add>{date}</date_add>
            </configuration>
        </prestashop>

    """

    return xml


def setup_ps_main_menu(category_parent_map):
    response = api_get(
        "configurations",
        {"filter[name]": "[MOD_BLOCKTOPMENU_ITEMS]", "display": "full"},
    )

    id_main_menu = int(response["configurations"][0]["id"])
    main_categories = [c_id for c_id in category_parent_map if category_parent_map[c_id] == config.HOME_CATEGORY_ID]

    value = ",".join(f"CAT{category}" for category in main_categories)

    date = time.strftime("%Y-%m-%d %H:%M:%S")

    xml = create_ps_menu_xml(id_main_menu, value, date)
    api_patch(f"configurations/{id_main_menu}", xml)


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

        category_counter = add_categories(root, categories_in_database, category_parent_map, category_id_map)
        setup_ps_main_menu(category_parent_map)
    with open(config.SCRAPER_RESULTS_PATH / "results.json", encoding="utf-8") as file:
        products = json.load(file)
        products_display = get_products({"display": "[id,reference]"})
        products_in_database = {p["reference"]: int(p["id"]) for p in products_display}

        product_id_map, added, updated, rejected = add_products(
            products, products_in_database, category_id_map, category_parent_map
        )

        clear_sample_data(category_id_map, product_id_map)
        add_images(products, product_id_map)
        set_stocks(products, product_id_map)
        promo_counter = set_promotions(products, product_id_map)

    end_time = time.perf_counter()
    logger.info(
        "Kategorie: utworzono %d, zaktualizowano %d, odrzucono %d",
        category_counter["added"],
        category_counter["updated"],
        category_counter["rejected"],
    )
    logger.info("Produkty: utworzono %d, zaktualizowano %d, odrzucono %d", added, updated, rejected)
    logger.info(
        "Promocje: utworzono %d, zaktualizowano %d, usunięto %d, odrzucono %d",
        promo_counter["added"],
        promo_counter["updated"],
        promo_counter["deleted"],
        promo_counter["rejected"],
    )
    logger.info("Czas importu: %.2fs", end_time - start_time)


if __name__ == "__main__":
    setup_logging()
    main()
