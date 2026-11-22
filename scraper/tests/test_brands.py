"""Uzupełnianie marki (uzupelnij_marki.py) na zapisanych stronach z fixtures/, bez internetu."""

from decimal import Decimal
from pathlib import Path

from conftest import FakeClient
from main import parse_product
from models import Product
from uzupelnij_marki import fill_brands

FIXTURES = Path(__file__).parent / "fixtures"

UKULELE = "https://gitara-sklep.pl/koncertowe/1589-ukulele-koncertowe-uk10s-harley-benton.html"


def saved_product(url, page):
    """Produkt jak w starym results.json: bez marki."""
    data = parse_product(url, (FIXTURES / page).read_bytes())
    data.pop("brand")
    return Product(**data, other_category_ids=[])


def test_fills_only_brand():
    product = saved_product(UKULELE, "page-1.html")
    product.price_gross = Decimal("123.45")
    client = FakeClient({UKULELE: (FIXTURES / "page-1.html").read_bytes()})

    failed = fill_brands([product], client)

    assert failed == 0
    assert product.brand.name == "Harley Benton"
    assert str(product.brand.logo_url) == "https://gitara-sklep.pl/img/m/3.jpg"
    assert product.price_gross == Decimal("123.45")


def test_rerun_keeps_downloaded_logo_file():
    product = saved_product(UKULELE, "page-1.html")
    client = FakeClient({UKULELE: (FIXTURES / "page-1.html").read_bytes()})
    fill_brands([product], client)
    product.brand.logo_file = "images/brands/3.jpg"

    fill_brands([product], client)

    assert product.brand.logo_file == "images/brands/3.jpg"


def test_page_of_other_product_is_not_used(caplog):
    product = saved_product(UKULELE, "page-1.html")
    client = FakeClient({UKULELE: (FIXTURES / "page-2.html").read_bytes()})

    failed = fill_brands([product], client)

    assert failed == 1
    assert product.brand is None
    assert "ma id 3916 zamiast 1589" in caplog.text
