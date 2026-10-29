import logging
from decimal import Decimal
from pathlib import Path

import pytest
from main import parse_product, parse_products
from models import Product

logger = logging.getLogger(__name__)

DIRECTORY = Path(__file__).parent


def load_fixture(path):
    with open(path, "rb") as file:
        return file.read()


@pytest.mark.parametrize(
    "path",
    [
        DIRECTORY / "fixtures/page-1.html",
        DIRECTORY / "fixtures/page-2.html",
        DIRECTORY / "fixtures/page-3.html",
        DIRECTORY / "fixtures/fake-page-5.html",
    ],
)
def test_pydantic_validation(path):
    product = parse_product("", load_fixture(path))
    Product(**product)


def test_parse_regular_product():
    url = DIRECTORY / "fixtures/page-1.html"
    page = load_fixture(url)
    product = Product(**parse_product("", page))
    assert product.name == "Ukulele koncertowe UK10S Harley Benton"
    assert product.price_gross == Decimal("270.00")
    assert product.category_path == ["Ukulele", "Koncertowe"]
    assert len(product.image_urls) == 3
    assert (
        str(product.image_urls[0])
        == "https://gitara-sklep.pl/14508/ukulele-koncertowe-uk10s-harley-benton.jpg"
    )


def test_invalid_record_goes_to_log(caplog):

    pages = [
        (
            "https://gitara-sklep.pl/koncertowe/1589-ukulele-koncertowe-uk10s-harley-benton.html",
            load_fixture(DIRECTORY / "fixtures/page-1.html"),
        ),
        (
            "https://gitara-sklep.pl/138-kostki",
            load_fixture(DIRECTORY / "fixtures/page-4.html"),
        ),
    ]

    results = parse_products(pages)

    assert len(results) == 1
    assert "Błędny rekord https://gitara-sklep.pl/138-kostki" in caplog.text


def test_parse_fake_product():
    url = DIRECTORY / "fixtures/fake-page-5.html"
    page = load_fixture(url)
    product = Product(**parse_product("", page))

    assert product.vat_rate_percent == Decimal(8)
    assert product.attributes == {"Kolor": "Żółty", "Materiał": "Mahoń"}
    assert product.weight == Decimal("0.05")
