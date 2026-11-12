"""Wznawianie scrapera (scrape_products) na zapisanych stronach z fixtures/, bez internetu."""

import json
from pathlib import Path

import pytest
from conftest import FakeClient
from main import scrape_products

FIXTURES = Path(__file__).parent / "fixtures"

UKULELE = "https://gitara-sklep.pl/koncertowe/1589-ukulele-koncertowe-uk10s-harley-benton.html"
KABEL = "https://gitara-sklep.pl/mikrofonowe/3916-quad410-kabel-mikrofonowy-starquad-4-zyly-czarny-proel.html"
SKRZYPCE = "https://gitara-sklep.pl/skrzypce/2416-hv-300-skrzypce-44-futeral-smyczek-ars-nova.html"

PRODUCT_CATEGORIES = {
    UKULELE: ["https://gitara-sklep.pl/333-koncertowe"],
    KABEL: ["https://gitara-sklep.pl/292-mikrofonowe"],
    SKRZYPCE: ["https://gitara-sklep.pl/241-skrzypce"],
}
CATEGORY_IDS = {333, 292, 241}


@pytest.fixture
def responses():
    return {
        UKULELE: (FIXTURES / "page-1.html").read_bytes(),
        KABEL: (FIXTURES / "page-2.html").read_bytes(),
        SKRZYPCE: (FIXTURES / "page-3.html").read_bytes(),
    }


def saved_urls(path):
    with open(path, encoding="utf-8") as file:
        return [product["url"] for product in json.load(file)]


class InterruptedClient(FakeClient):
    """Udaje Ctrl+C w chwili pobierania adresu stop_url."""

    def __init__(self, responses, stop_url):
        super().__init__(responses)
        self.stop_url = stop_url

    def get(self, url):
        if url == self.stop_url:
            raise KeyboardInterrupt
        return super().get(url)


class SnapshotClient(FakeClient):
    """Przy każdym pobraniu zapamiętuje, ile produktów jest już zapisanych w pliku."""

    def __init__(self, responses, path):
        super().__init__(responses)
        self.path = path
        self.saved_counts = []

    def get(self, url):
        self.saved_counts.append(len(saved_urls(self.path)) if self.path.exists() else 0)
        return super().get(url)


def test_resume_after_ctrl_c_skips_saved_products(tmp_path, responses):
    path = tmp_path / "results.json"

    with pytest.raises(KeyboardInterrupt):
        scrape_products(InterruptedClient(responses, SKRZYPCE), PRODUCT_CATEGORIES, CATEGORY_IDS, path)

    # finally zapisał produkty sprzed przerwania, choć paczka 50 się nie zapełniła
    assert saved_urls(path) == [UKULELE, KABEL]

    client = FakeClient(responses)
    products, failed, skipped = scrape_products(client, PRODUCT_CATEGORIES, CATEGORY_IDS, path)

    assert client.requested == [SKRZYPCE]  # zapisanych kart nie pobiera drugi raz
    assert [str(product.url) for product in products] == [UKULELE, KABEL, SKRZYPCE]
    assert saved_urls(path) == [UKULELE, KABEL, SKRZYPCE]
    assert (failed, skipped) == (0, 0)


def test_saves_after_each_batch(tmp_path, responses):
    path = tmp_path / "results.json"
    client = SnapshotClient(responses, path)

    scrape_products(client, PRODUCT_CATEGORIES, CATEGORY_IDS, path, batch_size=2)

    # Przed 3. pobraniem plik ma już 2 produkty z pierwszej paczki
    assert client.saved_counts == [0, 0, 2]
    assert saved_urls(path) == [UKULELE, KABEL, SKRZYPCE]


def test_resume_false_starts_from_scratch(tmp_path, responses):
    path = tmp_path / "results.json"
    scrape_products(FakeClient(responses), PRODUCT_CATEGORIES, CATEGORY_IDS, path)

    client = FakeClient(responses)
    scrape_products(client, PRODUCT_CATEGORIES, CATEGORY_IDS, path, resume=False)

    assert client.requested == [UKULELE, KABEL, SKRZYPCE]  # --od-nowa pobiera wszystko
    assert saved_urls(path) == [UKULELE, KABEL, SKRZYPCE]  # bez duplikatów ze starego pliku
