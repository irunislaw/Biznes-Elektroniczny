# Scraper

Zbiera adresy kart wszystkich produktów z jednej kategorii sklepu i zapisuje je do pliku JSON w `scraper-results/`.

Uzasadnienie wyboru bibliotek: [ADR-001](../docs/adr/0001-biblioteka-scrapera.md).

## Wymagania
- Python 3.10+
- biblioteki: `requests`, `beautifulsoup4`

## Instalacja
```bash
cd scraper
python -m venv .venv
.venv\Scripts\activate # Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Uruchomienie
```bash
python main.py
```

## Wynik
 
Plik JSON (UTF-8) z listą unikalnych adresów kart produktów:
 
```json
[
  "https://gitara-sklep.pl/...produkt-1.html",
  "https://gitara-sklep.pl/...produkt-2.html"
]
```

## Log
 
Każde zapytanie jest logowane na standardowe wyjście z dokładnym czasem:
 
```
2026-10-19 18:23:50.469762: https://gitara-sklep.pl/340-sopranowe
2026-10-19 18:23:50.969891: https://gitara-sklep.pl/333-koncertowe
```
 
Odstępy między wpisami pozwalają sprawdzić, że limit zapytań jest przestrzegany (przy 2 zapytaniach/s co najmniej 0,5 s). Logowane są też strony zablokowane przez `robots.txt` oraz odpowiedzi z kodem innym niż 200.

## Jak to działa
 
1. **`ShopClient`** (`shop_client.py`) obsługuje wszystkie zapytania HTTP:
   - wysyła własny `User-Agent`,
   - przed każdym zapytaniem sprawdza `robots.txt` i pomija zablokowane adresy,
   - pilnuje limitu zapytań na sekundę,
   - zwraca `None` przy błędzie HTTP.
2. **`find_first_category_url`** pobiera stronę startową i wybiera pierwszą kategorię.
3. **`collect_category_tree`** rekurencyjnie schodzi po podkategoriach i zwraca listę kategorii-liści (bez dalszych podkategorii).
4. **`collect_products`** przechodzi przez kolejne strony listy produktów (`?page=1`, `?page=2`, …), dopóki istnieje link „następna strona”.
5. **`scrape_category`** łączy wyniki i usuwa duplikaty (ten sam produkt może być w kilku kategoriach).
Funkcje `parse_subcategory_urls` i `parse_product_urls` przyjmują sam HTML, bez zapytań sieciowych, więc można je testować na zapisanych stronach.

## Znane ograniczenia
 
- Produkty zbierane są tylko z kategorii-liści. Produkt przypisany wyłącznie do kategorii nadrzędnej nie zostanie znaleziony.
- Brak ponawiania nieudanych zapytań. Błąd na stronie listy kończy zbieranie produktów z tej kategorii.
- Dyrektywa `Crawl-delay` z `robots.txt` nie jest uwzględniana; tempo wyznacza tylko `REQUESTS_PER_SECOND`.
- Scraper działa tylko dla stron renderowanych po stronie serwera (patrz [ADR-001](../docs/adr/0001-biblioteka-scrapera.md)).
