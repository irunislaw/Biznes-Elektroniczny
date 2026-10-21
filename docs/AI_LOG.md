# Dziennik AI

Korzystanie z ChatGPT, Claude, Copilota i agentów kodujących jest dozwolone pod warunkiem jawności. Za każdą linię kodu w repozytorium odpowiada zespół, niezależnie od tego, kto lub co ją napisało.

## Zasady

- Wpis dodaje osoba, która korzystała z narzędzia, **w tym samym PR co kod**.
- PR z istotnymi fragmentami wygenerowanymi przez AI dostaje etykietę `ai-assisted`, a w opisie PR piszemy, jak sprawdziliśmy poprawność.
- Kod z AI traktujemy jak kod młodszego kolegi: trafia na `main` wyłącznie przez PR z merytorycznym przeglądem człowieka.
- Do narzędzi AI nie wklejamy haseł, kluczy API ani danych dostępowych.
- Minimum **2 wpisy na osobę** w etapie.
- Na obronie nie można się zasłaniać tym, że fragment napisało AI. Każdy musi rozumieć kod, który oddaje.

## Jak dodać wpis

Dopisz nowy wiersz na końcu tabeli. Przykład:

```markdown
| 2026-10-20, Jan Kowalski | Claude Sonnet w VS Code | EB-14 / #7: parsowanie karty produktu | funkcja wyciągająca cenę i atrybuty z HTML | zły selektor ceny promocyjnej, brak obsługi przecinka w cenie | testy na zapisanych stronach w `scraper/tests/fixtures/`, ręczne porównanie 5 produktów ze źródłem |
```

## Wpisy

| Data i autor | Narzędzie i model | Zadanie | Co otrzymano | Co było błędne | Weryfikacja |
|---|---|---|---|---|---|
| 2026-10-11, Michał Irek | Claude Opus 5.5 w Claude Code (VS Code) | BE-7: PrestaShop w docker compose, błąd `Cannot download language pack "pl"` | diagnoza: Norton przechwytuje HTTPS, więc instalacja przerywa się w połowie i blokuje ponowną; cel `make reset`, sekcja w README | pierwsza wskazówka, gdzie to wyłączyć w Nortonie, była zbyt ogólna (wyłączone zostało blokowanie elementów śledzących, a nie skanowanie HTTPS) | `openssl s_client` z kontenera pokazał wystawcę „Norton Web/Mail Shield Root”; po zmianie w Nortonie `curl` zwraca HTTP 400 zamiast błędu SSL; po `down -v` i `make up` w logach jest `Installation successful!` |
| 2026-10-19, Tymon Dera | Claude Opus 5.5 w przeglądarce | BE-9: Napisać szkielet scrapera, jak poradzić sobie z zwiększającą się ilością parametrów w funkcjach | Sugestia na stworzenie klasy `ShopClient` przechowującą istotne parametry (requests.session, robots.txt, itp.)| Brak | Nie dotyczy |
| 2026-10-21, Tymon Dera | Claude Opus 5.5 w przeglądarce | BE-9: Napisać szkielet scrapera, napisanie readme z instrukcją obsługi scrapera | Gotowy plik `README.md` | Brak | Sprawdziłem poprawność znaczników w pliku `README.md` |
## Refleksja zespołu

<!-- Uzupełniamy w sprincie 4, do 1 strony: gdzie AI realnie przyspieszyło pracę, gdzie wprowadziło w błąd i czego zespół musiał się nauczyć sam. Jeśli ktoś nie korzystał z AI, piszemy to tutaj. -->
