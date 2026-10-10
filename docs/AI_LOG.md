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

## Refleksja zespołu

<!-- Uzupełniamy w sprincie 4, do 1 strony: gdzie AI realnie przyspieszyło pracę, gdzie wprowadziło w błąd i czego zespół musiał się nauczyć sam. Jeśli ktoś nie korzystał z AI, piszemy to tutaj. -->
