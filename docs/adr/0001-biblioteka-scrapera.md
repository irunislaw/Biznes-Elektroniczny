<!--
Jak używać: skopiuj ten plik jako docs/adr/NNNN-krotki-tytul.md (np. 0001-biblioteka-scrapera.md),
uzupełnij wszystkie sekcje i usuń ten komentarz. ADR dodajemy przez PR jak kod.

Planowane ADR-y:
- 0001 Biblioteka do scrapowania (S1-03)
- 0002 Inicjalizacja danych i konfiguracji sklepu (sprint 2)
- 0003 Architektura kontenerów i HTTPS (sprint 3)
-->

# ADR-0001: Biblioteka do scrapowania sklepu

- **Status:** przyjęta
- **Data:** 2026-10-26
- **Autor:** Tymon Dera
- **Zadanie:** BE-09

## Kontekst

Scraper ma za zadanie pobierać i wyciągać dane ze sklepu `gitara-sklep.pl`. Wybór dotyczący biblioteki scrapera jest istotny, ponieważ będzie rzutować na całą strukturę kodu.

Ograniczenia:
- 2 zapytania na sekundę.
- Playwright tylko gdy strona renderuje produkty w JavaScripcie.

Sklep tworzy drzewo kategorii i listy produktów po stronie serwera. Wszystkie potrzebne dane można znaleźć w HTML pozyskanym za pomocą zapytania GET.

## Rozważane opcje

### Opcja 1: requests + BeautifulSoup

`requests` pobiera strony, a `BeautifulSoup` wyciąga znaczniki HTML za pomocą CSS. Limit zapytań i obsługę `robots.txt` trzeba napisać samemu.

- plusy:
  - proste i popularne
  - kontrola nad tempem zapytań
- minusy:
  - limit zapytań i obsługę `robots.txt` trzeba napisać samemu
  - brak współbieżności
  - nie obsługuje stron tworzonych za pomocą JavaScript

### Opcja 2: Playwright

Sterowanie prawdziwą przeglądarką, która wykonuje JavaScript na stronie.

- plusy:
  - obsługuje strony renderowane przez JavaScript
- minusy:
  - wolny, bo uruchamia przeglądarkę
  - wymaga instalacji przeglądarek
  - niepotrzebny, bo dane są dostępne w HTML    

## Decyzja

Wybieramy opcję 1: requests + BeautifulSoup, ponieważ:
- dane są w HTML, więc Playwright nie jest potrzebny
- skala zadania jest mała
- prosty kod łatwiej przetestować bez internetu

Limit zapytań i sprawdzanie `robots.txt` są zaimplementowane w klasie `ShopClient`.

## Konsekwencje

- zyskujemy: prosty kod, funkcje parsujące, które przyjmują sam HTML, logi z czasem wykonania każdego zapytania, tempo 2 zapytań na sekundę
- na co uważać: ponawianie zapytań i obsługę `Crawl-delay` z `robots.txt` trzeba napisać samemu, jeżeli sklep zacznie renderować produkty w JavaScripcie scraper będzie trzeba przepisać na Playwright
- co trzeba zrobić dalej:
  - zapisanie 3-5 stron HTML jako fixture do testów
  - schemat danych - pydantic, rekord z błędem trafia do logów, zamiast do wyniku
  - testy jednostkowe (pytest), które działają bez internetu

