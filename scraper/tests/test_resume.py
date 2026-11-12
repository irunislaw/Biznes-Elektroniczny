"""Wznawianie scrapera (scrape_products) na zapisanych stronach z fixtures/, bez internetu."""

import json
from pathlib import Path

import pytest
from conftest import FakeClient
from main import CachedClient, scrape_products

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


def test_second_run_sends_no_requests(tmp_path, responses):
    path = tmp_path / "results.json"
    cache_dir = tmp_path / "cache"
    category_ids = {333, 292}  # skrzypce (241) poza drzewem: pominięte, więc nie trafią do results.json

    first = CachedClient(FakeClient(responses), cache_dir)
    scrape_products(first, PRODUCT_CATEGORIES, category_ids, path)

    assert first.stats == {"pobrane": 3}
    assert sorted(file.name for file in cache_dir.iterdir()) == ["1589.html", "2416.html", "3916.html"]

    shop = FakeClient(responses)
    second = CachedClient(shop, cache_dir)
    products, failed, skipped = scrape_products(second, PRODUCT_CATEGORIES, category_ids, path)

    assert shop.requested == []  # ani zapisanych, ani pominiętych kart nie pobiera drugi raz
    assert second.stats == {"z dysku": 1}  # pominięta karta z dysku, zapisane produkty z results.json
    assert (failed, skipped) == (0, 1)
    assert saved_urls(path) == [UKULELE, KABEL]


def test_od_nowa_ignores_cache(tmp_path, responses):
    cache_dir = tmp_path / "cache"
    first = CachedClient(FakeClient(responses), cache_dir)
    scrape_products(first, PRODUCT_CATEGORIES, CATEGORY_IDS, tmp_path / "results.json")

    shop = FakeClient(responses)
    second = CachedClient(shop, cache_dir, use_cache=False)
    scrape_products(second, PRODUCT_CATEGORIES, CATEGORY_IDS, tmp_path / "results.json", resume=False)

    assert shop.requested == [UKULELE, KABEL, SKRZYPCE]
    assert second.stats == {"pobrane": 3}


def test_failed_download_is_not_cached(tmp_path, responses):
    cache_dir = tmp_path / "cache"

    assert CachedClient(FakeClient({}), cache_dir).get(KABEL) is None
    assert list(cache_dir.iterdir()) == []  # nieudane pobranie nie trafia na dysk

    shop = FakeClient(responses)
    CachedClient(shop, cache_dir).get(KABEL)
    assert shop.requested == [KABEL]  # więc kolejne uruchomienie próbuje jeszcze raz
    assert [file.name for file in cache_dir.iterdir()] == ["3916.html"]
