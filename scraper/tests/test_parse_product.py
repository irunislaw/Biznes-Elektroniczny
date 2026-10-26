import logging
from decimal import Decimal

import pytest
from main import parse_product, parse_products
from models import Product

logger = logging.getLogger(__name__)


def load_fixture(path):
    with open(path, "rb") as file:
        return file.read()


@pytest.mark.parametrize(
    "path",
    [
        "tests/fixtures/page-1.html",
        "tests/fixtures/page-2.html",
        "tests/fixtures/page-3.html",
        "tests/fixtures/fake-page-5.html",
    ],
)
def test_pydantic_validation(path):
    product = parse_product(load_fixture(path))
    Product(**product)


def test_parse_regular_product():
    page = load_fixture("tests/fixtures/page-1.html")
    product = Product(**parse_product(page))
    assert product.name == "Ukulele koncertowe UK10S Harley Benton"
    assert product.price_gross == Decimal("270.00")
    assert product.category_path == ["Ukulele", "Koncertowe"]
    assert len(product.image_urls) == 3


def test_invalid_record_goes_to_log(caplog):

    paths = ["tests/fixtures/page-1.html", "tests/fixtures/page-4.html"]
    pages = [(path, load_fixture(path)) for path in paths]

    results = parse_products(pages)

    assert len(results) == 1
    assert "tests/fixtures/page-4.html" in caplog.text


def test_parse_fake_product():
    page = load_fixture("tests/fixtures/fake-page-5.html")
    product = Product(**parse_product(page))

    assert product.vat_rate_percent == Decimal(8)
    assert product.attributes == {"Kolor": "Żółty", "Materiał": "Mahoń"}
    assert product.weight == Decimal("0.05")
