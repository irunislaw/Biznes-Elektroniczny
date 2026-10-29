# Scraper

Zbiera adresy kart wszystkich produktów z jednej kategorii sklepu (z podkategoriami),
pobiera każdą kartę, parsuje dane produktu, waliduje je schematem pydantic
i zapisuje do plików JSON w `scraper-results/`.

Uzasadnienie wyboru bibliotek: [ADR-001](../docs/adr/0001-biblioteka-scrapera.md).

## Wymagania
- Python 3.10+ (składnia `Decimal | None` w `models.py`)
- zależności w `requirements.txt` (requests, beautifulsoup4, pydantic, pytest)

## Instalacja
    cd scraper
    python -m venv .venv
    .venv\Scripts\activate # Linux: source .venv/bin/activate
    pip install -r requirements.txt

## Konfiguracja (`config.py`)
- `SCRAPER_START_URL` - strona startowa; scraper bierze z niej **pierwszą** kategorię,
- `USER_AGENT` - nazwa projektu i kontakt,
- `REQUESTS_PER_SECOND` - limit tempa (domyślnie 2),
- `MAX_ATTEMPTS` - liczba prób pobrania strony,
- `SAVE_URLS_PATH`, `SAVE_PRODUCTS_PATH` - pliki wynikowe.

## Uruchomienie
Wszystkie polecenia uruchamiaj z katalogu `scraper/`

    python main.py

## Wynik
- `scraper-results/results_urls.json` – lista unikalnych adresów kart produktów,
- `scraper-results/results.json` – lista produktów zgodnych ze schematem `Product` (`models.py`):

| Pole | Typ | Uwagi |
|---|---|---|
| `id` | int | id produktu w sklepie |
| `name` | str | |
| `description` | str | surowy HTML opisu ze sklepu |
| `price_gross` | Decimal | cena regularna brutto (bez promocji) |
| `sale_price_gross` | Decimal \| null | cena promocyjna brutto; `null`, gdy brak promocji |
| `vat_rate_percent` | Decimal \| null | stawka VAT w % |
| `weight` | Decimal \| null | patrz „Znane ograniczenia” |
| `attributes` | dict | patrz „Znane ograniczenia” |
| `url` | URL | adres źródłowy |
| `category_path` | list[str] | ścieżka z breadcrumbu (kategoria domyślna produktu) |
| `id_category_default` | int | |
| `image_urls` | list[URL] | oryginalne zdjęcia (bez skalowania przez sklep) |

## Log
Log trafia na konsolę i do pliku `scraper-results/scraper_RRRR-MM-DD_GG-MM-SS.log`:

    16:49:52.478 INFO    shop_client: GET https://gitara-sklep.pl/10-ukulele (próba 1)
    16:49:52.978 INFO    shop_client: GET https://gitara-sklep.pl/340-sopranowe (próba 1)

Odstępy ≥0,5 s między `GET` potwierdzają limit 2 zapytań/s. Logowane są też: adresy
zablokowane przez `robots.txt`, nieudane próby i ponowienia oraz rekordy odrzucone
przez walidację (`Błędny rekord <url>: <powód>`).

## Jak to działa
1. **`ShopClient`** - User-Agent, `robots.txt`, limit tempa, ponawianie
   (do `MAX_ATTEMPTS` prób przy błędzie sieci i kodach 429/5xx, z odstępem 2 s, 4 s…);
   po wyczerpaniu prób albo przy innym kodzie zwraca `None`.
2. **`find_first_category_url`** pobiera stronę startową i wybiera pierwszą kategorię.
3. **`collect_category_tree`** rekurencyjnie schodzi po podkategoriach i zwraca listę kategorii-liści (bez dalszych podkategorii).
4. **`collect_products`** przechodzi przez kolejne strony listy produktów (`?page=1`, `?page=2`, …), dopóki istnieje link „następna strona”.
5. **`scrape_category`** łączy wyniki i usuwa duplikaty (ten sam produkt może być w kilku kategoriach).
6. **`fetch_pages`** pobiera karty produktów (generator – strony nie są trzymane wszystkie w pamięci).
7. **`parse_product`** wyciąga dane z atrybutu `data-product` (JSON osadzony w HTML) i breadcrumbu.
8. **`parse_products`** waliduje każdy rekord modelem `Product`; błędny rekord trafia do logu, nie do wyników.


## Testy i lint
Testy jednostkowe są w `tests/` i nie łączą się ze sklepem. CI uruchamia je w każdym PR razem z `ruff`.

```bash
pip install -r requirements-dev.txt
pytest
ruff check .
```

Testy działają bez internetu – używają zapisanych stron z `tests/fixtures/`
(`save_fixtures.py` służy do ich ponownego pobrania). `fake-page-5.html` to ręcznie
zmodyfikowana strona z VAT 8%, atrybutami i wagą - sprawdza parsowanie innej stawki VAT
oraz pól, których prawdziwe strony sklepu nie mają.

## Znane ograniczenia
 
- Atrybuty (`attributes`) są puste - sklep nie udostępnia cech produktu (`features` w `data-product` jest pustą listą). Parser je obsługuje (patrz `fake-page-5.html`).
- Waga (`weight`) jest zawsze `null` - sklep jej nie publikuje.
- Zdjęcia to oryginały; large_default dla małych oryginałów to ten sam obraz na białym płótnie 800×800, więc nie zawiera więcej treści.
- `category_path` to kategoria domyślna produktu, więc może się różnić od scrapowanej kategorii.
- Produkty zbierane są tylko z kategorii-liści.
- `Crawl-delay` z `robots.txt` nie jest uwzględniany.
- Działa tylko dla stron renderowanych po stronie serwera ([ADR-001](../docs/adr/0001-biblioteka-scrapera.md)).
