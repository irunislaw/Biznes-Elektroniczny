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
| `categories`, `products` | GET, POST, PATCH, DELETE |
| `images` | GET, POST |
| `stock_availables` | GET, PATCH |
| `configurations` | GET, PATCH |

## Co robi skrypt
- **Kategorie**: odtwarza drzewo kategorii i podkategorii ze sklepu źródłowego pod kategorią „Strona główna”.
- **Produkty**: nazwa, opis, przyjazny URL, grupa reguł VAT (23/8/5/0%) i cena netto = brutto / (1 + VAT), zaokrąglona do 6 miejsc po przecinku. W polu `reference` jest identyfikator produktu ze sklepu źródłowego. Waga jest brana z pola `weight`; scraper jej nie zbiera (`null`), więc obecnie wynosi 0.
- **Przypisanie do kategorii**: produkt trafia do swojej podkategorii i do wszystkich kategorii nadrzędnych, więc żadna kategoria nie jest pusta.
- **Dane demo**: instalatora w obrazie nie da się uruchomić bez produktów i kategorii demo, dlatego usuwa je skrypt. Kasuje wszystko, czego nie ma w imporcie.
- **Zdjęcia**: wysyłane z lokalnych plików scrapera, w kilku wątkach równolegle (`MAX_WORKERS`).
- **Stany magazynowe**: losowane z zakresu 0–10 ze stałym ziarnem (`RANDOM_SEED`), więc każdy przebieg daje te same stany. Obecnie stan 0 ma ok. 8% produktów.
- **Menu górne** (`ps_mainmenu`): pokazuje zaimportowane kategorie główne zamiast kategorii demo.

Wyszukiwarka znajduje zaimportowane produkty bez przebudowy indeksu.

## Ponowne uruchomienie
Import można bezpiecznie uruchomić kilka razy:
- **Kategorie** są rozpoznawane po kategorii nadrzędnej i `link_rewrite` (pochodzi z adresu kategorii w sklepie źródłowym). Używamy `link_rewrite` zamiast nazwy, bo jest unikalny w obrębie rodzica i nie zmienia się, gdy w sklepie źródłowym zmieni się wyświetlana nazwa. Istniejącej kategorii aktualizowana jest nazwa.
- **Produkty** są rozpoznawane po `reference` (identyfikator ze sklepu źródłowego). Istniejącemu produktowi aktualizowane są cena, opis i waga. Stan magazynowy jest ustawiany przy każdym przebiegu.
- **Zdjęcia** są wysyłane tylko produktom, które jeszcze nie mają żadnego zdjęcia, więc się nie dublują.

## Raport i błędy
Każdy przebieg zapisuje log `deploy/import/import_<data>.log`. Rekord odrzucony przez API (np. błąd walidacji) jest logowany na poziomie `ERROR` razem z identyfikatorem ze sklepu źródłowego, a import przechodzi do następnego rekordu. Produkt, którego nie udało się zaktualizować, zostaje w sklepie.

Na końcu logu jest raport:

```
Kategorie: utworzono 0, zaktualizowano 61, odrzucono 0
Produkty: utworzono 0, zaktualizowano 1161, odrzucono 0
Czas importu: 69.30s
```

Czas importu 1161 produktów: do pustego sklepu ok. 3,5 min, ponownie ok. 1 min (limit: 30 min).

## Sprawdzenie, że nie ma duplikatów
1. Uruchom import drugi raz. Raport powinien pokazać `utworzono 0` dla kategorii i produktów.
2. Z katalogu głównego repozytorium uruchom zapytania:
   ```bash
    make duplikaty
   ```
Dwa pierwsze zapytania nie powinny zwrócić żadnego wiersza. Liczby z trzeciego (produkty, kategorie, zdjęcia) powinny być takie same przed i po ponownym imporcie.