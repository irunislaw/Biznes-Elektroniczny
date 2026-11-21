# Scraper

Przechodzi po 5 wybranych kategoriach sklepu (z podkategoriami), zbiera adresy kart produktów,
pobiera każdą kartę, parsuje dane produktu, waliduje je schematem pydantic
i zapisuje do plików JSON w `scraper-results/`.

Uzasadnienie wyboru bibliotek: [ADR-001](../docs/adr/0001-biblioteka-scrapera.md).

## Wymagania
- Python 3.10+ (składnia `Decimal | None` w `models.py`)
- zależności w `requirements.txt` (requests, beautifulsoup4, pydantic, Pillow, pytest)

## Instalacja
    cd scraper
    python -m venv .venv
    .venv\Scripts\activate # Linux: source .venv/bin/activate
    pip install -r requirements.txt

## Konfiguracja (`config.py`)
- `SHOP_URL` - adres sklepu, z którego pobierany jest `robots.txt`,
- `CATEGORY_URLS` - adresy scrapowanych kategorii głównych (po zmianie uruchom `python main.py --od-nowa`,
  patrz „Przerwanie i wznawianie”),
- `USER_AGENT` - nazwa projektu i kontakt,
- `REQUESTS_PER_SECOND` - limit tempa (domyślnie 2),
- `MAX_ATTEMPTS` - liczba prób pobrania strony,
- `BATCH_SIZE` - co ile pobranych kart produktów zapisywać `results.json` (domyślnie 50),
- `SAVE_URLS_PATH`, `SAVE_PRODUCTS_PATH`, `SAVE_CATEGORY_TREE_PATH` - pliki wynikowe,
- `PAGES_CACHE_PATH` - katalog na pobrane karty produktów (`scraper-results/cache/`, w `.gitignore`),
- `LOGGING_PATH` - katalog na logi,
- `IMAGES_PATH` - katalog na zdjęcia (`scraper-results/images/`, w `.gitignore`),
- `IMAGE_MAX_SIDE_PX` (1600), `IMAGE_MAX_BYTES` (300 000 B), `IMAGE_MIN_SIDE_PX` (800) - limity zdjęć
  (dłuższy bok od 800 do 1600 px, plik ≤300 000 B).

## Uruchomienie
Wszystkie polecenia uruchamiaj z katalogu `scraper/`

    python main.py             # produkty -> scraper-results/results.json
    python main.py --od-nowa   # wszystko od zera: ignoruje results.json i category-tree.json, czyści cache/
    python download_images.py  # zdjęcia -> scraper-results/images/, ścieżki do results.json
    python check_images.py     # kontrola zdjęć 20 losowych produktów
    python uzupelnij_opisy.py  # krótki opis produktom zapisanym w results.json (patrz „Krótki opis”)

Pełny przebieg trwa ok. 12 minut (730,96 s przy 2 zapytaniach/s i 1288 adresach produktów).
Czas zależy od liczby produktów i ponowień.

## Przerwanie i wznawianie
Scraper można przerwać (Ctrl+C) i uruchomić ponownie. Nie pobiera drugi raz ani produktów
zapisanych w `results.json`, ani żadnej karty produktu, która jest już na dysku.

- `results.json` jest zapisywany co 50 pobranych kart produktów (`BATCH_SIZE` w `config.py`)
  i jeszcze raz przy przerwaniu. Zapis idzie przez plik tymczasowy, więc przerwanie
  nie zostawia uciętego JSON-a. Format pliku jest taki sam jak przy zapisie na końcu przebiegu.
- Każda pobrana karta produktu (HTML) trafia do `scraper-results/cache/<id produktu>.html`,
  też przez plik tymczasowy. Kolejne uruchomienie bierze ją z dysku zamiast ze sklepu – także
  karty produktów pominiętych (kategoria poza drzewem) i odrzuconych przez walidację, których
  nie ma w `results.json`. Nieudane pobranie i odpowiedź z pustą treścią (sklep potrafi
  odpowiedzieć tak kodem 200) nie trafiają na dysk, więc następnym razem są
  ponawiane. Katalog jest w `.gitignore`. Podsumowanie w logu pokazuje,
  ile kart wzięto z dysku, a ile pobrano, np. drugie uruchomienie po pełnym przebiegu:

      INFO    __main__: Karty produktów wzięte z dysku: 164
      INFO    __main__: Karty produktów pobrane ze sklepu: 0

- Po Ctrl+C log kończy się ostatnim zapisem i ostrzeżeniem (bez tracebacku):

      INFO    __main__: Zapisano 461 produktów do results.json
      WARNING __main__: Przerwano (Ctrl+C). Uruchom ponownie, aby wznowić od zapisanych wyników.

- Ponowne `python main.py` wczytuje drzewo kategorii z `category-tree.json` (bez zapytań
  o listy kategorii) i produkty z `results.json`, a pobiera tylko brakujące adresy:

      INFO    __main__: Drzewo kategorii wczytane z category-tree.json
      INFO    __main__: Wczytane z results.json: 461 produktów, do pobrania: 869 adresów

- `results.json` i `category-tree.json` są w repozytorium, więc samo `python main.py`
  po sklonowaniu też wznawia od nich. Żeby zebrać wszystko od zera, uruchom
  `python main.py --od-nowa`: ignoruje `results.json` i `category-tree.json`, a na starcie
  czyści `cache/`. Przerwany przebieg `--od-nowa` wznawia się zwykłym `python main.py`
  i korzysta już tylko z kart pobranych od nowa.
- Po zmianie `CATEGORY_URLS` w `config.py` uruchom `python main.py --od-nowa`. Zwykłe
  uruchomienie wczyta stare drzewo z `category-tree.json`, więc nowych kategorii nie pobierze.
- Drzewo kategorii zapisuje się dopiero w całości, na początku przebiegu od zera
  (ok. 1,5 min, 174 zapytania w ostatnim przebiegu). Przerwanie w tym czasie nie zmienia
  plików, więc wystarczy uruchomić to samo polecenie jeszcze raz.

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
| `description_short` | str | surowy HTML krótkiego opisu (na karcie produktu pod ceną); pusty, gdy sklep go nie ma; patrz „Krótki opis” |
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
| `image_files` | list[str] | lokalne zdjęcia względem `scraper-results/`, np. `images/487-1.jpg`; puste do uruchomienia `download_images.py` |

## Brakujące dane a import
Brak stawki VAT lub wagi jest zapisywany jako `null`. Import przyjmuje wtedy:

- VAT: 23%,
- waga: 0.

W ostatnim przebiegu VAT miały wszystkie produkty (23% – 1119, 5% – 5),
a wagi nie miał żaden, bo sklep jej nie publikuje.

## Krótki opis
`parse_product` zbiera krótki opis (`description_short` z `data-product`), czyli tekst, który
sklep pokazuje na karcie produktu pod ceną, osobno od pełnego opisu. `results.json`
w repozytorium powstał wcześniej, więc pole uzupełnia osobny skrypt:

    python uzupelnij_opisy.py

- Pobiera karty tylko tych produktów, które już są w `results.json`, tym samym `ShopClient`
  (User-Agent, `robots.txt`, ≤2 zapytania/s), i zmienia w nich tylko `description_short`.
  Ceny, promocje, zdjęcia i zbiór produktów zostają bez zmian. `python main.py --od-nowa`
  też zebrałby krótki opis, ale zmieniłby przy okazji pozostałe dane, a za nimi zdjęcia i zrzut sklepu.
- Karty idą przez `CachedClient`, więc po przerwaniu (Ctrl+C) kolejne uruchomienie nie pobiera
  ich drugi raz. `results.json` jest zapisywany na końcu, także po Ctrl+C.
- Karta, której nie udało się pobrać, bez danych produktu albo z innym id produktu jest
  logowana i pomijana, a krótki opis tego produktu zostaje bez zmian.
- Log: `scraper-results/opisy_RRRR-MM-DD_GG-MM-SS.log`. Na końcu jest liczba produktów
  z krótkim opisem, bez niego i nieudanych oraz ile kart wzięto z dysku, a ile pobrano.

## Zdjęcia
`download_images.py` czyta `results.json`, pobiera każdy adres z `image_urls` tym samym
`ShopClient` co scraper (ten sam User-Agent, `robots.txt` i limit ≤2 zapytania/s), skaluje
zdjęcie i dopisuje przy produkcie `image_files`.

- **Nazwy plików** są stałe: `<id produktu>-<n>.jpg`, gdzie `n` to pozycja adresu w `image_urls`
  (od 1). Import dopasowuje zdjęcie do produktu po samej nazwie. Jeśli któreś zdjęcie się nie
  pobierze, kolejne zachowują swoje numery.
- **Bez ponownego pobierania**: plik, który już jest w `scraper-results/images/`, jest pomijany.
  Zapis idzie przez plik tymczasowy, więc przerwanie (Ctrl+C) nie zostawia uciętego zdjęcia.
  Po ponownym `main.py` wystarczy znów uruchomić `download_images.py`: pobierze tylko
  brakujące zdjęcia, a pozostałym produktom uzupełni `image_files` bez zapytań do sklepu.
  Wyjątek: zapisane zdjęcie z dłuższym bokiem < 800 px (z wersji scrapera sprzed powiększania)
  jest powiększane z pliku na dysku, też bez zapytań do sklepu. Drugie uruchomienie już go nie zmienia.
- **Skalowanie** (`images.py`, Pillow): dłuższy bok od 800 do 1600 px. Większe zdjęcie jest
  zmniejszane do 1600 px, a mniejsze powiększane do 800 px (LANCZOS, proporcje zostają, więc
  krótszy bok może mieć mniej niż 800 px). Powiększenie nie dodaje szczegółów: najmniejsze zdjęcia
  (ok. 230 px) są po nim lekko miękkie. JPEG z jakością obniżaną od 90 co 5, aż plik ma ≤300 000 B, czyli ≤300 KB przy
  obu definicjach KB. Gdyby nie wystarczyła nawet jakość 20, obraz jest zmniejszany o 10%
  i próba się powtarza. Przezroczystość zamieniana jest na białe tło, metadane EXIF są usuwane.
- **Log** `scraper-results/images_RRRR-MM-DD_GG-MM-SS.log`: każde `GET`, wymiary przed i po
  skalowaniu, jakość i rozmiar, ostrzeżenie
  `Małe zdjęcie produktu <id>: <szer>x<wys>, dłuższy bok < 800 px, powiększone do <szer>x<wys> (<url>)`
  oraz podsumowanie: liczba pobranych, pominiętych, błędów i powiększonych zdjęć.
  W zbiorze z 21.11.2026 powiększonych zostało 2027 z 6588 zdjęć (dłuższy bok od 234 do 799 px),
  łącznie o 35 MB.

Pełny zbiór nie trafia do repozytorium. W `scraper-results/przyklady/` jest 20 przykładowych
zdjęć (tyle pozwala PDF) o tych samych nazwach co w `images/`.

### Kontrola zdjęć
`check_images.py` losuje 20 produktów z `results.json` i dla każdego zdjęcia wypisuje wymiary
w pikselach i rozmiar w KB (1 KB = 1024 B, jak w Eksploratorze Windows). Kod wyjścia 1
oznacza, że któreś zdjęcie łamie limit (brak pliku, nie JPEG, dłuższy bok < 800 px
albo > 1600 px, plik > 300 000 B). Podsumowanie podaje najkrótszy i najdłuższy dłuższy bok.

    python check_images.py                                     # 20 losowych produktów
    python check_images.py --seed 123                          # powtórzenie tego samego losowania
    python check_images.py --dir ../scraper-results/przyklady  # przykłady z repozytorium (bez pobierania)

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
2. **`main`** wczytuje drzewo kategorii z `category-tree.json`, a gdy pliku nie ma albo podano `--od-nowa`, buduje je dla każdego adresu z `CATEGORY_URLS`.
3. **`build_category_tree`** rekurencyjnie schodzi po podkategoriach, a w liściach zbiera produkty i liczy je.
4. **`collect_products`** przechodzi przez kolejne strony listy produktów (`?page=1`, `?page=2`, …), dopóki istnieje link „następna strona”.
5. **`collect_product_categories`** tworzy słownik produkt → kategorie. Kluczem jest adres, więc produkt z kilku kategorii występuje raz.
6. **`collect_category_ids`** zbiera id wszystkich kategorii z drzewa.
7. **`fetch_pages`** pobiera karty produktów (generator – strony nie są trzymane wszystkie w pamięci) przez **`CachedClient`** (`cached_client.py`): karta, która jest już w `scraper-results/cache/`, jest czytana z dysku, a nowa pobierana ze sklepu i zapisywana tam przez plik tymczasowy.
8. **`parse_product`** wyciąga dane z atrybutu `data-product` (JSON osadzony w HTML) i breadcrumbu.
9. **`parse_products`** pomija produkty z kategorią główną spoza drzewa, uzupełnia `other_category_ids` i waliduje rekord modelem `Product`; błędny rekord trafia do logu, nie do wyników.
10. **`scrape_products`** pomija adresy, które już są w `results.json`, pozostałe pobiera (`fetch_pages`) i parsuje (`parse_products`), a wynik zapisuje co 50 kart i przy przerwaniu.
11. **`log_summary`** po zapisaniu wyników wypisuje podsumowanie przebiegu, w tym ile kart wzięto z dysku, a ile pobrano ze sklepu.


## Testy i lint
Testy jednostkowe są w `tests/` i nie łączą się ze sklepem. CI uruchamia je w każdym PR razem z `ruff`.

```bash
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest
ruff check .
```

Testy działają bez internetu – używają zapisanych stron z `tests/fixtures/`
(`save_fixtures.py` służy do ich ponownego pobrania). `test_images.py` generuje obrazy
w Pillow (gradient z szumem, czysty szum, przezroczysty PNG) i podstawia sztucznego klienta
zamiast `ShopClient`, więc sprawdza zmniejszanie i powiększanie (także zdjęć już zapisanych,
bez pobierania), nazwy plików, pomijanie pobranych zdjęć i log powiększonych zdjęć bez połączenia ze sklepem. `fake-page-5.html` to ręcznie
zmodyfikowana strona z VAT 8%, atrybutami i wagą - sprawdza parsowanie innej stawki VAT
oraz pól, których prawdziwe strony sklepu nie mają.
`test_resume.py` używa tego samego sztucznego klienta (`tests/conftest.py`) i stron z `fixtures/`:
symuluje Ctrl+C przy 3. produkcie i sprawdza, że wznowienie pobiera tylko brakującą kartę,
że zapis idzie po każdej paczce i że `--od-nowa` zaczyna od pustej listy.
Kolejne testy sprawdzają cache kart (`CachedClient`): drugie uruchomienie na tych samych
adresach nie wysyła żadnego zapytania (także o kartę pominiętą), `--od-nowa` czyści cache
(także pliki `.tmp`) i pobiera wszystko od nowa, a nieudane pobranie i pusta odpowiedź nie trafiają na dysk.
`test_short_descriptions.py` sprawdza `uzupelnij_opisy.py`: stary `results.json` bez pola
wczytuje się z pustym krótkim opisem, skrypt zmienia tylko `description_short` (zapisana cena
zostaje), a brak karty, karta innego produktu i strona bez `data-product` nie zmieniają produktu.

## Znane ograniczenia
 
- Atrybuty (`attributes`) są puste - sklep nie udostępnia cech produktu (`features` w `data-product` jest pustą listą). Parser je obsługuje (patrz `fake-page-5.html`).
- Zdjęcia to oryginały ze sklepu; mniejsze niż 800 px są powiększane (patrz „Zdjęcia”), więc nie mają więcej szczegółów niż oryginał. large_default ze sklepu źródłowego nie byłby lepszy: dla małych oryginałów to ten sam obraz na białym płótnie 800×800.
- `category_path` to kategoria domyślna produktu, więc może się różnić od scrapowanej kategorii.
- Produkty zbierane są tylko z kategorii-liści.
- `Crawl-delay` z `robots.txt` nie jest uwzględniany.
- Działa tylko dla stron renderowanych po stronie serwera ([ADR-001](../docs/adr/0001-biblioteka-scrapera.md)).
- Produkt, którego kategoria główna jest poza wybranym drzewem, jest pomijany (161 w ostatnim przebiegu), bo import nie miałby go do czego przypisać.
- Produkt bez zdjęć odpada w walidacji (`image_urls` wymaga co najmniej 1 zdjęcia; 3 rekordy w ostatnim przebiegu).
- `other_category_ids` zawiera tylko kategorie z wybranego drzewa, więc nie jest to pełna lista kategorii produktu w sklepie.
- Zapisane karty w `scraper-results/cache/` i produkty w `results.json` nie są odświeżane: zmiany w sklepie (np. ceny) pokaże dopiero `python main.py --od-nowa`.
