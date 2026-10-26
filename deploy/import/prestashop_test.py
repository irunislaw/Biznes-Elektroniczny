import json
import os
import time

import requests
import urllib3
from dotenv import load_dotenv

# Local Webservice configuration
urllib3.disable_warnings()
load_dotenv()
API_URL = "https://localhost:8443/api"
LOGIN = (
    os.getenv("PS_WEBSERVICE_KEY"),
    "",
)  # API key as username, empty password

HOME_CATEGORY_ID = 2
PARENT_CATEGORY_NAME = "Mikrofony"
PARENT_CATEGORY_LINK = "mikrofony"

# VAT rates mapped to PrestaShop tax rules groups
TAX_RULES_GROUP_FOR_VAT_RATE = {23: 1, 8: 2, 5: 3, 0: 4}


def send_to_api(resource, xml_body):
    response = requests.post(
        API_URL + "/" + resource,
        auth=LOGIN,
        params={"output_format": "JSON"},
        data=xml_body.encode("utf-8"),
        verify=False,
    )
    response.raise_for_status()
    return response.json()


def create_category(name, link_rewrite, parent_id):
    xml_body = f"""
    <prestashop>
      <category>
        <id_parent>{parent_id}</id_parent>
        <active>1</active>
        <name><language id="1"><![CDATA[{name}]]></language></name>
        <link_rewrite><language id="1"><![CDATA[{link_rewrite}]]></language></link_rewrite>
      </category>
    </prestashop>"""
    return send_to_api("categories", xml_body)["category"]["id"]


def create_product(product, category_id):
    # Convert gross price to net price
    net_price = round(product["price"] / (1 + product["rate"] / 100), 6)
    tax_rules_group_id = TAX_RULES_GROUP_FOR_VAT_RATE[product["rate"]]

    xml_body = f"""
    <prestashop>
      <product>
        <id_category_default>{category_id}</id_category_default>
        <id_tax_rules_group>{tax_rules_group_id}</id_tax_rules_group>
        <price>{net_price}</price>
        <weight>{product["weight"]}</weight>
        <condition>{product["condition"]}</condition>
        <active>1</active>
        <state>1</state>
        <name><language id="1"><![CDATA[{product["name"]}]]></language></name>
        <description><language id="1"><![CDATA[{product["description"]}]]></language></description>
        <description_short><language id="1"><![CDATA[{product["description_short"]}]]></language></description_short>
        <link_rewrite><language id="1"><![CDATA[{product["link_rewrite"]}]]></language></link_rewrite>
        <associations>
          <categories>
            <category><id>{category_id}</id></category>
          </categories>
        </associations>
      </product>
    </prestashop>"""
    return send_to_api("products", xml_body)["product"]["id"]


def add_image(product_id, image_url):
    image_file = requests.get(image_url).content
    response = requests.post(
        API_URL + "/images/products/" + str(product_id),
        auth=LOGIN,
        files={"image": ("image.jpg", image_file, "image/jpeg")},
        verify=False,
    )
    response.raise_for_status()


def set_stock(product_id, quantity):
    response = requests.get(
        API_URL + "/stock_availables",
        auth=LOGIN,
        params={
            "filter[id_product]": f"[{product_id}]",
            "display": "full",
            "output_format": "JSON",
        },
        verify=False,
    )
    response.raise_for_status()

    stock_id = response.json()["stock_availables"][0]["id"]

    xml_body = f"""
    <prestashop>
      <stock_available>
        <id>{stock_id}</id>
        <quantity>{quantity}</quantity>
      </stock_available>
    </prestashop>"""

    response = requests.patch(
        API_URL + "/stock_availables/" + str(stock_id),
        auth=LOGIN,
        data=xml_body.encode("utf-8"),
        verify=False,
    )
    response.raise_for_status()


with open("data.json", encoding="utf-8") as file:
    product = json.load(file)

parent_category_id = create_category(PARENT_CATEGORY_NAME, PARENT_CATEGORY_LINK, HOME_CATEGORY_ID)
subcategory_id = create_category(product["category_name"], product["category"], parent_category_id)
print("Category:", parent_category_id, "| Subcategory:", subcategory_id)

# Measure product creation, image uploads and stock update
start_time = time.time()

product_id = create_product(product, subcategory_id)

for image_url in product["images"]:
    add_image(product_id, image_url)

set_stock(product_id, product.get("quantity", 0))

duration = time.time() - start_time

print("Product:", product_id)
print(f"Time to create one product with images and stock: {duration:.2f} s")
