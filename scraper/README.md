# Scraper

Przechodzi po 5 wybranych kategoriach sklepu (z podkategoriami), zbiera adresy kart produktów,
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
- `SHOP_URL` - adres sklepu, z którego pobierany jest `robots.txt`,
- `CATEGORY_URLS` - adresy scrapowanych kategorii głównych,
- `USER_AGENT` - nazwa projektu i kontakt,
- `REQUESTS_PER_SECOND` - limit tempa (domyślnie 2),
- `MAX_ATTEMPTS` - liczba prób pobrania strony,
- `SAVE_URLS_PATH`, `SAVE_PRODUCTS_PATH`, `SAVE_CATEGORY_TREE_PATH` - pliki wynikowe,
- `LOGGING_PATH` - katalog na logi.

## Uruchomienie
Wszystkie polecenia uruchamiaj z katalogu `scraper/`

    python main.py

Pełny przebieg trwa ok. 12 minut (730,96 s przy 2 zapytaniach/s i 1288 adresach produktów).
Czas zależy od liczby produktów i ponowień.

## Wynik
Wszystkie pliki są zapisywane w UTF-8:

- `scraper-results/results.json` – lista produktów zgodnych ze schematem `Product` (`models.py`),
- `scraper-results/category-tree.json` – drzewo kategorii (`url`, `name`, `children`, `products`, `count`),
- `scraper-results/results_urls.json` – słownik `{adres produktu: [adresy kategorii]}`.

`results.json` ma ok. 3,75 MB, więc mieści się w limicie 10 MB i nie wymaga podziału.
Produkt z kilku kategorii jest zapisany raz: z kategorią główną (`id_category_default`)
i listą pozostałych (`other_category_ids`).

| Pole | Typ | Uwagi |
|---|---|---|
| `id` | int | id produktu w sklepie |
| `name` | str | |
| `description` | str | surowy HTML opisu ze sklepu |
| `price_gross` | Decimal | cena regularna brutto (bez promocji) |
| `sale_price_gross` | Decimal \| null | cena promocyjna brutto; `null`, gdy brak promocji |
| `vat_rate_percent` | Decimal \| null | stawka VAT w %; patrz „Brakujące dane a import” |
| `weight` | Decimal \| null | patrz „Brakujące dane a import” |
| `attributes` | dict | patrz „Znane ograniczenia” |
| `url` | URL | adres źródłowy |
| `category_path` | list[str] | ścieżka z breadcrumbu (kategoria główna produktu) |
| `id_category_default` | int | id kategorii głównej |
| `other_category_ids` | list[int] | id pozostałych kategorii z wybranego drzewa |
| `image_urls` | list[URL] | oryginalne zdjęcia (bez skalowania przez sklep) |

## Brakujące dane a import
Brak stawki VAT lub wagi jest zapisywany jako `null`. Import przyjmuje wtedy:

- VAT: 23%,
- waga: 0.

W ostatnim przebiegu VAT miały wszystkie produkty (23% – 1119, 5% – 5),
a wagi nie miał żaden, bo sklep jej nie publikuje.

## Log
Log trafia na konsolę i do pliku `scraper-results/scraper_RRRR-MM-DD_GG-MM-SS.log`:

    16:49:52.478 INFO    shop_client: GET https://gitara-sklep.pl/10-ukulele (próba 1)
    16:49:52.978 INFO    shop_client: GET https://gitara-sklep.pl/340-sopranowe (próba 1)

Odstępy ≥0,5 s między `GET` potwierdzają limit 2 zapytań/s. Logowane są też: adresy
zablokowane przez `robots.txt`, nieudane próby i ponowienia oraz rekordy odrzucone
przez walidację oraz produkty pominięte, bo ich kategoria główna jest poza drzewem.

Na końcu przebiegu log zawiera podsumowanie, a w nim także liczbę zapisanych produktów
w każdej kategorii i podkategorii:

    === PODSUMOWANIE ===
    Znalezione na listach sklepu (unikalne adresy): 1288
    Pominięte (kategoria główna poza drzewem): 161
    Odrzucone przez walidację: 3
    Nieudane pobrania: 0
    Zapisane produkty: 1124
    Produkty z co najmniej 2 zdjęciami: 941
    Kategorie: 5
    Podkategorie: 56
    Zapisane produkty według kategorii:
    Ukulele: 150
      Sopranowe: 35
    ...
    Czas scrapowania: 730.96 s
    Średnie tempo: 2.00 zapytań/s

## Jak to działa
1. **`ShopClient`** - User-Agent, `robots.txt`, limit tempa, ponawianie
   (do `MAX_ATTEMPTS` prób przy błędzie sieci i kodach 429/5xx, z odstępem 2 s, 4 s…);
   po wyczerpaniu prób albo przy innym kodzie zwraca `None`.
2. **`main`** dla każdego adresu z `CATEGORY_URLS` buduje drzewo kategorii.
3. **`build_category_tree`** rekurencyjnie schodzi po podkategoriach, a w liściach zbiera produkty i liczy je.
4. **`collect_products`** przechodzi przez kolejne strony listy produktów (`?page=1`, `?page=2`, …), dopóki istnieje link „następna strona”.
5. **`collect_product_categories`** tworzy słownik produkt → kategorie. Kluczem jest adres, więc produkt z kilku kategorii występuje raz.
6. **`collect_category_ids`** zbiera id wszystkich kategorii z drzewa.
7. **`fetch_pages`** pobiera karty produktów (generator – strony nie są trzymane wszystkie w pamięci).
8. **`parse_product`** wyciąga dane z atrybutu `data-product` (JSON osadzony w HTML) i breadcrumbu.
9. **`parse_products`** pomija produkty z kategorią główną spoza drzewa, uzupełnia `other_category_ids` i waliduje rekord modelem `Product`; błędny rekord trafia do logu, nie do wyników.
10. **`log_summary`** po zapisaniu wyników wypisuje podsumowanie przebiegu.


## Testy i lint
Testy jednostkowe są w `tests/` i nie łączą się ze sklepem. CI uruchamia je w każdym PR razem z `ruff`.

```bash
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest
ruff check .
```

Testy działają bez internetu – używają zapisanych stron z `tests/fixtures/`
(`save_fixtures.py` służy do ich ponownego pobrania). `fake-page-5.html` to ręcznie
zmodyfikowana strona z VAT 8%, atrybutami i wagą - sprawdza parsowanie innej stawki VAT
oraz pól, których prawdziwe strony sklepu nie mają.

## Znane ograniczenia
 
- Atrybuty (`attributes`) są puste - sklep nie udostępnia cech produktu (`features` w `data-product` jest pustą listą). Parser je obsługuje (patrz `fake-page-5.html`).
- Zdjęcia to oryginały; large_default dla małych oryginałów to ten sam obraz na białym płótnie 800×800, więc nie zawiera więcej treści.
- `category_path` to kategoria domyślna produktu, więc może się różnić od scrapowanej kategorii.
- Produkty zbierane są tylko z kategorii-liści.
- `Crawl-delay` z `robots.txt` nie jest uwzględniany.
- Działa tylko dla stron renderowanych po stronie serwera ([ADR-001](../docs/adr/0001-biblioteka-scrapera.md)).
- Produkt, którego kategoria główna jest poza wybranym drzewem, jest pomijany (161 w ostatnim przebiegu), bo import nie miałby go do czego przypisać.
- Produkt bez zdjęć odpada w walidacji (`image_urls` wymaga co najmniej 1 zdjęcia; 3 rekordy w ostatnim przebiegu).
- `other_category_ids` zawiera tylko kategorie z wybranego drzewa, więc nie jest to pełna lista kategorii produktu w sklepie.
