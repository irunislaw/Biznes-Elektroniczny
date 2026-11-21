"""Uzupełnianie krótkiego opisu (uzupelnij_opisy.py) na zapisanych stronach z fixtures/, bez internetu."""

from decimal import Decimal
from pathlib import Path

from conftest import FakeClient
from main import parse_product
from models import Product
from uzupelnij_opisy import fill_short_descriptions

FIXTURES = Path(__file__).parent / "fixtures"

UKULELE = "https://gitara-sklep.pl/koncertowe/1589-ukulele-koncertowe-uk10s-harley-benton.html"
KABEL = "https://gitara-sklep.pl/mikrofonowe/3916-quad410-kabel-mikrofonowy-starquad-4-zyly-czarny-proel.html"


def saved_product(url, page):
    """Produkt jak w starym results.json: bez krótkiego opisu."""
    data = parse_product(url, (FIXTURES / page).read_bytes())
    data.pop("description_short")
    return Product(**data, other_category_ids=[])


def test_old_results_without_field_load_with_empty_short_description():
    assert saved_product(UKULELE, "page-1.html").description_short == ""


def test_fills_only_short_description():
    product = saved_product(UKULELE, "page-1.html")
    # Zapisana cena różni się od karty: skrypt nie może jej nadpisać
    product.price_gross = Decimal("123.45")
    client = FakeClient({UKULELE: (FIXTURES / "page-1.html").read_bytes()})

    failed = fill_short_descriptions([product], client)

    assert failed == 0
    assert client.requested == [UKULELE]
    assert product.description_short.startswith("<p><strong>Ukulele koncertowe UK10S")
    assert product.price_gross == Decimal("123.45")


def test_missing_page_leaves_product_unchanged():
    product = saved_product(UKULELE, "page-1.html")

    failed = fill_short_descriptions([product], FakeClient({}))

    assert failed == 1
    assert product.description_short == ""


def test_page_of_other_product_is_not_used(caplog):
    product = saved_product(UKULELE, "page-1.html")
    # Pod adresem ukulele sklep zwraca kartę kabla (np. po przekierowaniu)
    client = FakeClient({UKULELE: (FIXTURES / "page-2.html").read_bytes()})

    failed = fill_short_descriptions([product], client)

    assert failed == 1
    assert product.description_short == ""
    assert "ma id 3916 zamiast 1589" in caplog.text


def test_page_without_product_data_is_skipped():
    product = saved_product(KABEL, "page-2.html")
    client = FakeClient({KABEL: (FIXTURES / "page-4.html").read_bytes()})

    failed = fill_short_descriptions([product], client)

    assert failed == 1
    assert product.description_short == ""
