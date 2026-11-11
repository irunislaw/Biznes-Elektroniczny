# ADR-0002: Inicjalizacja danych i konfiguracji sklepu

- **Status:** przyjęta
- **Data:** 2026-11-12
- **Autor:** Michał Irek
- **Zadanie:** BE-22 / #33

## Kontekst

Sklep ma po `git clone`, `make up` i `make init` działać z pełnymi danymi: 1161 produktów w 5 kategoriach głównych, 6588 zdjęć i stany magazynowe. Dane pochodzą ze scrapera (`scraper-results/`) i trafiają do sklepu przez import Web Service API (`deploy/import/import.py`). Trzeba zdecydować, jak te dane dostają się do sklepu u każdej osoby z zespołu, u prowadzącego i później na klastrze.

Ograniczenia:

- **W3:** `make init` trwa najwyżej 15 min. Celujemy w ≤10 min, żeby mieć zapas na wolniejsze komputery i łącza.
- **D2:** import przez API trwa najwyżej 30 min.
- Wymagania do uruchomienia to tylko Docker, `make` i git (README). Bez Pythona na komputerze i bez klucza API.
- Repozytorium ≤200 MB. Pełny zbiór zdjęć nie mieści się w repozytorium, w `scraper-results/przyklady/` jest tylko 20 przykładów.
- Sekret w repozytorium to 0 pkt za W1. Dane osobowe z testów też nie mogą trafić do repozytorium.
- Do sklepu źródłowego wysyłamy najwyżej 2 zapytania/s (scraper, ADR-0001), więc pobieranie ~6600 zdjęć trwa ok. 1 h.

Pomiary:

| Co | Wynik |
|---|---|
| pełny import przez API (`import.py`, 1161 produktów, 6588 zdjęć, pusty sklep) | 476 s (ok. 8 min) |
| instalacja PrestaShop przy pierwszym `make up` (obrazy już pobrane, Windows 11) | ok. 45 s |
| pełne `img/p`: oryginały / wszystkie miniatury / razem | 617 MB / 659 MB / 1276 MB |
| największy typ miniatur, `large_default` | 379 MB |
| tworzenie 5 typów miniatur z oryginału (GD w kontenerze, 1 proces) | 118 ms na zdjęcie, czyli ok. 13 min na 6588 zdjęć |

## Rozważane opcje

### Opcja 1: import przez API przy każdym `make init`

`make init` uruchamia `import.py` na świeżo zainstalowanym sklepie.

- plusy:
  - w repozytorium nie ma binarnego zrzutu, dane zawsze wynikają z aktualnego kodu importu i wyników scrapera,
  - zrzut nie jest związany z wersją PrestaShop,
  - import już istnieje i jest idempotentny (BE-19).
- minusy:
  - sam import trwa ok. 8 min. Razem z instalacją sklepu i konfiguracją to ok. 9–10 min na komputerze, na którym zmierzyliśmy import. To blisko limitu W3, a na wolniejszym komputerze ponad,
  - import potrzebuje zdjęć na dysku (`scraper-results/images/`, ok. 600 MB), których nie ma w repozytorium. Trzeba by je i tak pobierać z Releases albo przez godzinę ze sklepu źródłowego,
  - każdy potrzebuje Pythona z zależnościami (albo kontenera z nim) i klucza Webservice,
  - przerwany import zostawia sklep z częścią danych. Ponowne uruchomienie go naprawia, ale trwa kolejne minuty.

### Opcja 2: zrzut bazy zbudowany importem

Jedna osoba robi import na czystym sklepie i zapisuje zrzut bazy oraz zdjęć (`make zrzut`). `make init` u innych wczytuje zrzut zamiast importować.

- plusy:
  - `make init` nie zależy od czasu importu. Zmierzone od `git clone` do sklepu z danymi: 173 s (Windows 11, Docker Desktop),
  - wszyscy mają identyczne dane, łącznie z identyfikatorami produktów i zdjęć oraz stanami,
  - do uruchomienia wystarczą Docker, `make` i git, bez Pythona i klucza API,
  - wczytanie bazy jest powtarzalne: ten sam plik daje ten sam sklep,
  - import (D2) zostaje narzędziem do budowania zrzutu i dalej musi mieścić się w 30 min.
- minusy:
  - zrzut jest związany z wersją PrestaShop i jej schematem bazy,
  - po każdej zmianie importu albo wyników scrapera trzeba zrobić nowy zrzut i nowe wydanie zdjęć,
  - zrzut to plik binarny w repozytorium, więc każda wersja zostaje w historii,
  - trzeba pilnować, żeby w zrzucie nie było kluczy API ani danych osobowych z testów.

### Opcja 3: import CSV z panelu PrestaShop

Wyniki scrapera zamieniamy na pliki CSV (kategorie, produkty) i wczytujemy je w panelu: Zaawansowane → Importuj.

- plusy:
  - wbudowana funkcja PrestaShop, nie trzeba pisać kodu API,
  - dobrze znany format, łatwo obejrzeć dane w arkuszu.
- minusy:
  - import CSV wykonuje się w panelu. PrestaShop 8 nie ma do niego polecenia CLI, więc żeby wpiąć go w `make init`, trzeba by udawać przeglądarkę (formularze z tokenami panelu),
  - zdjęcia podaje się jako adresy URL, które sklep pobiera sam. Ze sklepu źródłowego oznaczałoby to pobieranie bez limitu 2 zapytań/s i bez `robots.txt`, a z lokalnego serwera kolejny element do uruchomienia,
  - każdy typ danych to osobny plik i osobny przebieg z mapowaniem kolumn. Stany magazynowe i drzewo kategorii trzeba odtworzyć dokładnie tak jak w imporcie API,
  - czasu dla pełnych danych nie mierzyliśmy, ale sklep i tak pobiera oraz skaluje 6588 zdjęć, więc nie będzie szybszy niż opcja 1.

## Decyzja

Wybieramy opcję 2, ponieważ jako jedyna daje zapas do limitu 15 min niezależnie od czasu importu (173 s zamiast ok. 9–10 min) i nie wymaga od nikogo Pythona ani klucza API. Import przez API zostaje sposobem budowania zrzutu.

```
scraper → import.py (API) → sklep autora zrzutu ── make zrzut ──┬─► deploy/dane/sklep.sql.gz + zdjecia.sha256 (repozytorium)
                                                                 └─► zdjecia.tar (GitHub Releases, tag dane-vN)
git clone → make up → make init: zrzut bazy → archiwum zdjęć → domena i admin z .env → deploy/config/ → cache
```

### Co jest w zrzucie

Cała baza, a nie tylko katalog. Tabele katalogu są powiązane z resztą bazy: produkty z opisami w `_lang` i `_shop`, kategorie z drzewem `nleft`/`nright`, zdjęcia, stany, indeks wyszukiwarki i filtrów, menu górne w `ps_configuration`. Do tego świeża instalacja ma dane demo z tymi samymi identyfikatorami. Zrzut samego katalogu wymagałby scalania z bazą po instalacji. Zrzut całej bazy z tej samej wersji PrestaShop jest spójny i wczytuje się jednym poleceniem, zastępując dane demo.

W zrzucie nie ma (`deploy/dane/baza.sh`, lista `BEZ_DANYCH` i czyszczenie SQL):

- kluczy Webservice (`ps_webservice_account`, `ps_webservice_account_shop`, `ps_webservice_permission`). `make init` tworzy konto API z `PS_WEBSERVICE_KEY` z `.env`,
- klientów, adresów klientów, koszyków, zamówień, wiadomości, list życzeń, sesji, logów i statystyk odwiedzin. Zostaje tylko klient „Anonymous” modułu psgdpr, któremu moduł przypisuje zamówienia usuniętych klientów,
- e-maila, hasła i imienia administratora (w zrzucie jest `admin@example.com` i puste hasło), e-maili sklepu i sekretów modułu newslettera (`NW_SALT`, `PS_NEWSLETTER_RAND`).

Czyszczenie odbywa się na kopii w tymczasowej bazie, więc działający sklep autora zrzutu się nie zmienia. Na koniec `make zrzut` sprawdza, czy w zrzucie nie ma żadnego klucza Webservice ani e-maila pracownika lub klienta ze sklepu. Jeśli jest, usuwa zrzut i kończy się błędem. Rozmiar: 883 KB po kompresji.

### Gdzie leży zrzut i jak `make init` pobiera zdjęcia

- Zrzut bazy (`deploy/dane/sklep.sql.gz`, 883 KB) leży w repozytorium. Jest mały, a jego wersja zmienia się razem z kodem importu w tym samym PR.
- Zdjęcia (`zdjecia.tar`, 946 MB) leżą w GitHub Releases pod tagiem `dane-vN`, bo nie mieszczą się w limicie repozytorium. Adres jest w `ZDJECIA_URL` w `.env.example`, a suma SHA-256 archiwum w `deploy/dane/zdjecia.sha256` w repozytorium.
- `make init` pobiera archiwum `curl` w kontenerze sklepu, sprawdza sumę i rozpakowuje je do `img/p`. Inna suma oznacza, że `.env` wskazuje wydanie z innej wersji danych. Wtedy `make init` zatrzymuje się z komunikatem, zamiast wczytać zdjęcia niepasujące do bazy.
- Przy prywatnym repozytorium adres pliku z Releases wymaga zalogowania w przeglądarce. Wtedy w `.env` jest `GITHUB_TOKEN` (token fine-grained z prawem Contents: Read-only), a archiwum jest pobierane przez API GitHuba (`/repos/…/releases/assets/<id>`). Token jest tylko w `.env`.
- Gdy archiwum jest niedostępne, `make init` pobiera zdjęcia z adresów w `scraper-results/results.json` kodem scrapera (`download_images.py --bez-zapisu`): z tym samym limitem 2 zapytań/s, `robots.txt` i skalowaniem. To trwa ok. 1 h. Zdjęcie na pozycji N w sklepie to N-ty plik z `image_files` produktu, bo w tej kolejności wysyła je import. W teście oryginały z tej ścieżki były identyczne bajt w bajt z archiwum (767/767).

### Gotowe miniatury czy same zdjęcia

| Wariant | Archiwum | Praca przy `make init` |
|---|---|---|
| pełne `img/p` z miniaturami | 1276 MB, ponad limit 1 GB | tylko rozpakowanie |
| same oryginały | 617 MB | 5 typów miniatur dla 6588 zdjęć, ok. 13 min na jednym rdzeniu |
| **oryginały i miniatury bez największego typu** (wybrany) | **946 MB** | tylko `large_default`, równolegle na wszystkich rdzeniach Dockera |

Archiwum zawiera gotowy katalog `img/p`: oryginały i miniatury, ale bez typów, które nie zmieściłyby się w limicie 1 GB. `make zrzut` pomija typy od największego, aż archiwum się zmieści (teraz tylko `large_default`). `make init` tworzy brakujące miniatury tym samym kodem PrestaShop co Web Service przy imporcie (`ImageManager::resize`), w tylu procesach, ile rdzeni ma Docker. W zmierzonych 173 s mieści się pobranie archiwum, rozpakowanie i utworzenie `large_default`. Same oryginały dałyby mniejsze archiwum, ale ok. 13 min pracy procesora przy każdym `make init`, co na 4 rdzeniach przekracza 3 min.

### Jak skrypty z `deploy/config/` współpracują ze zrzutem

Kolejność w `make init` (`deploy/scripts/init.sh`):

1. czekanie na koniec instalacji PrestaShop,
2. wczytanie zrzutu bazy,
3. zdjęcia,
4. `deploy/dane/dopasuj.php`: domena i SSL z `PS_DOMAIN` (`PS_SHOP_DOMAIN`, `PS_SHOP_DOMAIN_SSL`, `ps_shop_url`, `.htaccess`) oraz e-mail i hasło administratora z `ADMIN_MAIL` i `ADMIN_PASSWORD`. Zrzut ma domenę z komputera, na którym powstał, i zaślepkę zamiast administratora,
5. skrypty z `deploy/config/` (język i waluta, podatki, płatności, przewoźnicy, poczta), szablony e-maili, konto Webservice z `.env`, czyszczenie cache.

Skrypty z `deploy/config/` działają po wczytaniu zrzutu, więc to one, a nie zrzut, decydują o konfiguracji. Zmiana w `deploy/config/` działa przy następnym `make init` bez nowego zrzutu. Zrzut powstaje na sklepie, na którym te skrypty już działały, więc zwykle nie mają nic do zmiany. Wszystkie skrypty zmieniają tylko to, co się różni, dlatego drugie `make init` niczego nie psuje. Zrzut i zdjęcia wczytują się tylko przy innej wersji danych: suma SHA-256 zrzutu jest zapisana w `ps_configuration`, a suma archiwum w `img/p/.zdjecia`.

### Jak odbudować zrzut, gdy zmieni się import (D3 w sprincie 3)

1. Nowe wyniki scrapera i zdjęcia (`main.py`, `download_images.py`).
2. `make reset`, `make up`, `make init DANE=0`. `DANE=0` pomija wczytanie starego zrzutu, bo import nie aktualizuje produktów, które już są w sklepie.
3. Import (`deploy/import/import.py`), potem `make sprawdz`.
4. Od razu `make zrzut`, przed testami w sklepie (zamówienia zmieniają stany magazynowe).
5. W jednym PR: zmiana importu, `scraper-results/*.json`, `deploy/dane/sklep.sql.gz`, `deploy/dane/zdjecia.sha256` i nowy tag w `ZDJECIA_URL` w `.env.example`.
6. Nowe wydanie w Releases (`dane-v2`, `dane-v3`…) z `zdjecia.tar`.

Po scaleniu `make init` u innych wykrywa nową sumę zrzutu, wczytuje go i pobiera nowe zdjęcia. Kto nie zmieni `ZDJECIA_URL` w swoim `.env`, dostaje komunikat, że archiwum nie pasuje do zrzutu.

## Konsekwencje

- zyskujemy:
  - sklep z pełnymi danymi w ok. 3 min od `git clone` (173 s na Windows 11), z dużym zapasem do 15 min,
  - te same dane u wszystkich, w testach E2E i u prowadzącego,
  - brak Pythona, klucza API i ruchu do sklepu źródłowego przy zwykłym uruchomieniu,
  - zrzut bez sekretów i danych osobowych, sprawdzany automatycznie przy każdym `make zrzut`.
- tracimy albo musimy uważać:
  - zrzut jest związany z wersją PrestaShop (`prestashop/prestashop:8.2.8-8.1-apache`) i MariaDB 10.11. Po zmianie obrazu sklepu trzeba zrobić nowy zrzut, bo stary może nie pasować do schematu bazy,
  - po każdej zmianie importu albo wyników scrapera trzeba zrobić nowy zrzut i wydanie. Zrzut, `results.json` i archiwum muszą być z tego samego przebiegu, bo zapasowa ścieżka zdjęć dopasowuje je po `image_files`,
  - każda wersja zrzutu zostaje w historii repozytorium (ok. 0,9 MB). Przy limicie 200 MB to setki wersji, ale nie generujemy ich bez potrzeby,
  - wczytanie nowej wersji zrzutu zastępuje bazę, więc konta i zamówienia z testów znikają,
  - każdy musi mieć w `.env` aktualny `ZDJECIA_URL`, a przy prywatnym repozytorium także `GITHUB_TOKEN`,
  - antywirus skanujący HTTPS (np. Norton) blokuje pobieranie z kontenerów. Lista adresów do wykluczeń jest w README.
- co trzeba zrobić dalej:
  - przy zmianie importu w sprincie 3 (D3) odbudować zrzut według procedury wyżej,
  - przy zmianie wersji PrestaShop zrobić nowy zrzut w tym samym PR,
  - w etapie 2 inicjalizacja na klastrze wczyta ten sam zrzut i to samo archiwum zdjęć. Skrypty działające w kontenerach (`deploy/dane/zdjecia.sh`, `zdjecia.php`, `dopasuj.php`) biorą ustawienia ze zmiennych środowiskowych (`PS_DOMAIN`, `ADMIN_MAIL`, `ZDJECIA_URL` itd.), więc można je uruchomić w zadaniu inicjalizującym klastra. `baza.sh` łączy się z bazą lokalnie w kontenerze `db`, więc na klastrze musi dostać adres serwera bazy. Trzeba też zastąpić część uruchamianą na komputerze (`deploy/scripts/init.sh`, który używa `docker compose exec`), zapewnić trwały wolumen na `img/p` i dostęp klastra do archiwum w Releases.
