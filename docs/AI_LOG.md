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
| 2026-10-22, Seweryn Grabowski | Gemini 3.1 Pro | BE-13: Konfiguracja testów Playwright w Docker Compose, błąd `ERR_CONNECTION_REFUSED` | Wyjaśnienie, że błąd wynika z wymuszania przez PrestaShop domeny localhost. Sugestia usunięcia biblioteki dotenv z konfiguracji i użycie socat do stworzenia tunelu przekierowującego port. | Pierwsza propozycja (użycie host-gateway) nie zadziała, bo PrestaShop odrzuca inne żądania niż "localhost". | Po zastosowaniu tunelu socat i usunięciu dotenv z konfiguracji playwright `make test` działa poprawnie i test przechodi bez błędów. |
| 2026-10-24, Maria Rek | ChatGPT (GPT-6) | BE-12: Automatyczna konfiguracja sklepu | Pomoc w przygotowaniu skryptów PHP konfigurujących język, walutę, podatki, płatności i SMTP oraz diagnoza błędu HTTP 500. | Proponowane uruchamianie wszystkich skryptów jako `www-data` powodowało problemy. Konieczna była naprawa uprawnień do katalogu cache PrestaShop. | Sprawdzenie logów kontenerów, ponowne uruchomienie `make init`, weryfikacja ustawień w panelu administracyjnym oraz metod płatności podczas składania zamówienia. |
| 2026-10-25, Maria Rek | OpenAI Codex (VS Code), ChatGPT (GPT-6) | BE-12: Konfiguracja polskich szablonów e-maili | Pomoc w znalezieniu sposobu na automatyczne generowanie polskich wiadomości HTML i TXT w PrestaShop. | Początkowo wiadomości nadal były po angielsku. Na świeżej instalacji generator zgłaszał też błąd z powodu braku katalogu `themes/classic/mails`. | Rejestracja nowego klienta, sprawdzenie polskich wiadomości i znaków w Mailpit oraz ponowne uruchomienie `make init`. |
| 2026-10-25, Michał Irek | Claude Opus 5.5 w Claude Code (VS Code) | BE-15: CI w GitHub Actions, gitleaks zgłasza sekrety w `scraper/tests/fixtures/*.html` | diagnoza: trafienia reguły `generic-api-key` to pola `static_token` i `token` z obiektu `var prestashop`, czyli publiczne tokeny CSRF, które sklep wstawia każdemu anonimowemu gościowi; wyjątek w `.gitleaks.toml` z opisem; instalacja binarki gitleaks z sumą SHA256 zamiast `gitleaks-action` | pierwsza propozycja wyjątku dodawała cały katalog `fixtures/` do `paths`, więc prawdziwy klucz wklejony do zapisanej strony też zostałby przepuszczony; zawężone do `condition = "AND"` z regexem tylko na te dwa pola | `gitleaks git --config .gitleaks.toml` lokalnie na całej historii bez trafień; kontrolnie dopisany do fixture fałszywy klucz w stylu AWS jest nadal wykrywany (zmiana cofnięta); zielony job gitleaks w PR |
| 2026-10-26, Maria Rek | ChatGPT (GPT-6) | BE-11: Konfiguracja Webservice API i napisanie skryptu do testowego importu produktu. | Kod PHP do automatycznej konfiguracji Webservice i uprawnień API oraz skrypt Python do importu kategorii, podkategorii i produktu wraz z jego danymi, zdjęciami i stanem magazynowym. | Początkowo skrypt nie obsługiwał stanu magazynowego, a po dodaniu tej funkcji pojawił się błąd `KeyError`, ponieważ w pliku JSON brakowało pola `quantity`. Poprawiono to, ustawiając domyślną wartość `0`. | Uruchomiłam `make init` i sprawdziłam, czy Webservice działa i ma odpowiednie uprawnienia. Następnie uruchomiłam skrypt importujący i sprawdziłam w sklepie, czy produkt ma poprawne dane, zdjęcia, stan magazynowy oraz cenę 130,00 zł brutto. |
| 2026-10-29, Tymon Dera | Claude Opus 5.5 w Claude Code CLI | BE-10: Parsować, walidować i testować kartę produktu, zaktualizowanie dokumentacji na temat scrapera | Gotowy plik `README.md` | Brak | Sprawdziłem poprawność znaczników w pliku `README.md` |

## Refleksja zespołu

<!-- Uzupełniamy w sprincie 4, do 1 strony: gdzie AI realnie przyspieszyło pracę, gdzie wprowadziło w błąd i czego zespół musiał się nauczyć sam. Jeśli ktoś nie korzystał z AI, piszemy to tutaj. -->
