# Import kategorii i produktów
Skrypt `import.py` przenosi do sklepu dane zebrane przez scraper (`scraper-results/category-tree.json`, `scraper-results/results.json` oraz pobrane zdjęcia). Korzysta z Web Service API PrestaShopa (`https://localhost:8443/api`). Stałe (ziarno losowania, liczba wątków, mapowanie stawek VAT na grupy reguł) są w `config.py`.

## Uruchomienie
Wymagania:
- uruchomiony sklep po `make up` i `make init` (tworzy konto API),
- `PS_WEBSERVICE_KEY` ustawiony w `.env`,
- zdjęcia w `scraper-results/images/`, pobrane przez `python download_images.py` w katalogu `scraper/` (opis w [scraper/README.md](../../scraper/README.md)).

Z katalogu głównego repozytorium:
```bash
python -m venv deploy/import/.venv
source deploy/import/.venv/bin/activate   # Windows (Git Bash): source deploy/import/.venv/Scripts/activate
pip install -r deploy/import/requirements.txt
python deploy/import/import.py
```

## Klucz API
Klucz jest czytany ze zmiennej środowiskowej `PS_WEBSERVICE_KEY` (plik `.env`) i nie trafia do repozytorium. Konto API ma dostęp tylko do tych zasobów, których potrzebuje import:

| Zasób | Metody |
|---|---|
| `categories`, `products` | GET, POST, DELETE |
| `images` | GET, POST |
| `stock_availables` | GET, PATCH |
| `configurations` | GET, PATCH |

## Co robi skrypt
- **Kategorie**: odtwarza drzewo kategorii i podkategorii ze sklepu źródłowego pod kategorią „Strona główna”.
- **Produkty**: nazwa, opis, przyjazny URL, grupa reguł VAT (23/8/5/0%) i cena netto = brutto / (1 + VAT), zaokrąglona do 6 miejsc po przecinku. W polu `reference` jest identyfikator produktu ze sklepu źródłowego. Sklep źródłowy nie podaje wagi, więc przyjmujemy 0.
- **Przypisanie do kategorii**: produkt trafia do swojej podkategorii i do wszystkich kategorii nadrzędnych, więc żadna kategoria nie jest pusta.
- **Dane demo**: instalatora w obrazie nie da się uruchomić bez produktów i kategorii demo, dlatego usuwa je skrypt. Kasuje wszystko, czego nie ma w imporcie.
- **Zdjęcia**: wysyłane z lokalnych plików scrapera, w kilku wątkach równolegle (`MAX_WORKERS`).
- **Stany magazynowe**: losowane z zakresu 0–10 ze stałym ziarnem (`RANDOM_SEED`), więc każdy przebieg daje te same stany. Obecnie stan 0 ma ok. 8% produktów.
- **Menu górne** (`ps_mainmenu`): pokazuje zaimportowane kategorie główne zamiast kategorii demo.

Wyszukiwarka znajduje zaimportowane produkty bez przebudowy indeksu.

## Ponowne uruchomienie
Import można bezpiecznie uruchomić kilka razy. Istniejące kategorie są rozpoznawane po rodzicu i `link_rewrite`, a produkty po `reference`. Zdjęcia są wysyłane tylko produktom, które jeszcze ich nie mają.

## Logi
Każdy przebieg zapisuje log `import_<data>.log` z ostrzeżeniami, liczbą produktów o stanie 0 i całkowitym czasem importu. Import 1151 produktów do pustego sklepu trwa ok. 4–5 min (limit: 30 min), a ponowne uruchomienie ok. 23 s.