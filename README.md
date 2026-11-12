# E-commerce website
E-commerce project to create 1:1 representation of existing shop in PrestaShop 8.x

# authors
 Tymon Dera, Maria Rek, Seweryn Grabowski, Aleksandra Wiśniewska, Michał Irek

# Uruchomienie
Wymagania: Docker z Docker Compose v2 (na Windowsie Docker Desktop), `make`, git. Na Windowsie polecenia wpisujemy w Git Bash. Porty 8080 i 8025 muszą być wolne.

1. Sklonuj repozytorium i wejdź do jego katalogu.
2. `cp .env.example .env` (opcjonalnie zmień hasła w `.env`).
3. `make up`, a postęp instalacji śledź przez `make logs`. Pierwszy start trwa kilka minut; gotowe, gdy w logach pojawi się `-- Installation successful! --`.
4. `make init` automatycznie konfiguruje język, walutę, podatki, płatności, przewoźników i pocztę sklepu.
5. Adresy:
   - sklep: http://localhost:8080
   - panel administracyjny: http://localhost:8080/admin-panel (login `ADMIN_MAIL` / `ADMIN_PASSWORD` z `.env`)
   - Mailpit: http://localhost:8025

`make down` zatrzymuje kontenery, dane zostają w wolumenach. `make reset` usuwa kontenery razem z wolumenami (baza i pliki sklepu), więc następne `make up` instaluje sklep od zera.

## Czas uruchomienia
Pomiar od `git clone` do działającego sklepu z pełnymi danymi: `git clone`, `cp .env.example .env`, `make up`, `make init`. Limit: 15 min, cel: ≤10 min.

| Osoba | System | Łącze | Obrazy Dockera pobrane wcześniej? | Czas |
|---|---|---|---|---|
| Michał Irek | Windows 11, Docker Desktop | około 700 mb/s | tak | 173 s (2 min 53 s) |
| _do uzupełnienia_ | Linux albo macOS | | | |

# Dane sklepu
Produkty nie są importowane na każdym komputerze. Osoba, która zrobiła import, zapisuje zrzut sklepu (`make zrzut`), a `make init` odtwarza go u innych. Uzasadnienie i rozważane opcje są w [ADR-0002](docs/adr/0002-inicjalizacja-danych.md). Pliki z danymi:

| Co | Gdzie | Rozmiar |
|---|---|---|
| zrzut bazy | [`deploy/dane/sklep.sql.gz`](deploy/dane/) w repozytorium | do kilku MB |
| zdjęcia produktów (`img/p`) | archiwum `zdjecia.tar` w [GitHub Releases](https://github.com/irunislaw/Biznes-Elektroniczny/releases), tag `dane-v1` | do 1 GB |
| suma SHA-256 archiwum | [`deploy/dane/zdjecia.sha256`](deploy/dane/) w repozytorium | |

Releases to zakładka GitHuba z plikami do pobrania przypiętymi do tagu. Adres archiwum jest w `ZDJECIA_URL` w `.env`.

## Co robi `make init`
Skrypt [`deploy/scripts/init.sh`](deploy/scripts/init.sh):
1. czeka, aż instalator PrestaShop skończy pracę,
2. wczytuje zrzut bazy ([`baza.sh wczytaj`](deploy/dane/baza.sh)),
3. pobiera archiwum zdjęć spod `ZDJECIA_URL`, sprawdza jego sumę SHA-256 i rozpakowuje je do `img/p` ([`zdjecia.sh`](deploy/dane/zdjecia.sh)). Potem tworzy brakujące miniatury w tylu procesach, ile rdzeni ma Docker ([`zdjecia.php`](deploy/dane/zdjecia.php)),
4. ustawia z `.env` domenę i SSL (`PS_SHOP_DOMAIN`, `PS_SHOP_DOMAIN_SSL`, tabela `ps_shop_url`), bo zrzut ma adres z komputera, na którym powstał. Ustawia też e-mail i hasło administratora (`ADMIN_MAIL`, `ADMIN_PASSWORD`) ([`dopasuj.php`](deploy/dane/dopasuj.php)),
5. uruchamia skrypty z [`deploy/config/`](deploy/config/), generuje polskie szablony e-maili, konfiguruje Webservice i czyści cache sklepu.

**Drugie uruchomienie niczego nie psuje.** Zrzut i zdjęcia wczytują się tylko wtedy, gdy w sklepie jest inna wersja danych (suma SHA-256 zrzutu jest zapisana w `ps_configuration`, a suma archiwum w `img/p/.zdjecia`). Konta i zamówienia z testów zostają, a hasło administratora nie jest haszowane od nowa. Po zmianie `sklep.sql.gz` w repozytorium (`git pull`) `make init` wczytuje nową wersję i zastępuje nią bazę. Żeby wrócić do czystych danych, wystarczy `make reset`, `make up` i `make init`.

**Gdy archiwum jest niedostępne** (brak sieci do GitHuba, plik usunięty, prywatne repozytorium bez tokenu), `make init` pobiera zdjęcia z adresów zapisanych przez scraper w `scraper-results/results.json`. Robi to tym samym kodem co scraper (`download_images.py --bez-zapisu` w kontenerze Pythona), więc z tym samym User-Agentem, `robots.txt`, limitem 2 zapytań/s i skalowaniem. Pełny zbiór to ok. 6500 zdjęć, czyli ok. 1 h. Zdjęcia, które już są w `scraper-results/images/`, nie są pobierane. Import wysyła zdjęcia produktu w kolejności `image_files`, więc zdjęcie na pozycji N w sklepie to N-ty plik z `image_files` produktu o `reference` równym id ze sklepu źródłowego.

**Archiwum ma mniej niż 1 GB** (946 MB), choć pełne `img/p` ma 1276 MB. `make zrzut` pomija w archiwum największe typy miniatur (zwykle `large_default`), aż archiwum zmieści się w limicie, a `make init` tworzy je z oryginałów. Oryginały są w archiwum zawsze.

## Prywatne repozytorium
Plik z Releases prywatnego repozytorium nie pobierze się bez logowania. Wtedy w `.env` trzeba wpisać token:
1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token.
2. Resource owner: właściciel repozytorium (`irunislaw`). Repository access: Only select repositories → to repozytorium. Permissions → Repository permissions → Contents: Read-only.
3. Token wpisać w `.env` jako `GITHUB_TOKEN=...`, potem `make up` i `make init`.

Jeśli repozytorium nie ma na liście (token fine-grained obejmuje tylko repozytoria wybranego właściciela), token może wygenerować właściciel repozytorium. Można też użyć tokenu classic z zakresem `repo`, ale on daje dostęp do wszystkich Twoich repozytoriów.

Sprawdzenie tokenu (w Git Bash, token nie trafia do historii poleceń):
```bash
read -rs T && curl -s -H "Authorization: Bearer $T" \
  https://api.github.com/repos/irunislaw/Biznes-Elektroniczny/releases/tags/dane-v1 | grep '"name"'
```
Na liście powinno być `"name": "zdjecia.tar"`.

Z tokenem archiwum jest pobierane przez API GitHuba (`/repos/.../releases/assets/<id>`), bo adres ze strony wymaga zalogowania w przeglądarce. Token jest tylko w `.env`, który nie trafia do repozytorium.

## Odświeżenie danych (`make zrzut`)
Po zmianie wyników scrapera albo importu:
1. Pobierz zdjęcia (`python download_images.py` w `scraper/`).
2. `make reset`, `make up`, `make init DANE=0`. `DANE=0` pomija wczytanie starego zrzutu, więc sklep ma tylko dane demo instalatora. Import usuwa je sam, a istniejących produktów nie aktualizuje.
3. Import (`deploy/import/`).
4. Od razu po imporcie, przed testami w sklepie (zamówienia zmieniają stany magazynowe) i przed kolejnym `make init` (wczytałby stary zrzut), uruchom `make zrzut`. Skrypt [`deploy/scripts/zrzut.sh`](deploy/scripts/zrzut.sh) zapisuje `deploy/dane/sklep.sql.gz`, `deploy/dane/zdjecia.tar` i `deploy/dane/zdjecia.sha256`.
5. Commit `sklep.sql.gz` i `zdjecia.sha256`. `zdjecia.tar` jest w `.gitignore`.
6. Na GitHubie: Releases → Create a new release → nowy tag (`dane-v2`, `dane-v3`…) → załącz `zdjecia.tar` → Publish release.
7. Zmień tag w `ZDJECIA_URL` w `.env.example`. Każdy, kto ma już `.env`, musi zmienić go też u siebie. Jeśli zapomni, `make init` zatrzyma się z komunikatem, że archiwum nie pasuje do zrzutu.

Co zrzut pomija ([`baza.sh`](deploy/dane/baza.sh), lista `BEZ_DANYCH`):
- klucze Webservice (`ps_webservice_account` i powiązane tabele), bo klucz API w repozytorium to 0 pkt za W1,
- klientów, adresy klientów, koszyki, zamówienia, wiadomości, listy życzeń, sesje, logi i statystyki odwiedzin. Zostaje tylko klient „Anonymous” modułu psgdpr,
- e-mail, hasło i imię administratora (w zrzucie jest `admin@example.com` i puste hasło) oraz pozostałe e-maile sklepu i sekrety modułu newslettera. `make init` ustawia je od nowa.

Na koniec skrypt sprawdza, czy w zrzucie nie ma żadnego klucza Webservice ani e-maila pracownika lub klienta ze sklepu. Jeśli jest, usuwa zrzut i kończy się błędem.

# Scraper
Scraper zbierający produkty z oryginalnego sklepu znajduje się w katalogu [`scraper/`](scraper/) i działa niezależnie od kontenerów (wymaga Pythona).

- instalacja, konfiguracja i uruchomienie: [scraper/README.md](scraper/README.md)
- wyniki: katalog `scraper-results/`
- uzasadnienie wyboru bibliotek: [ADR-0001](docs/adr/0001-biblioteka-scrapera.md)

# Import
Skrypt [`deploy/import/import.py`](deploy/import/import.py) wgrywa do sklepu kategorie, produkty, zdjęcia i stany magazynowe z wyników scrapera przez Web Service API. Wymaga uruchomionego sklepu po `make init` oraz klucza `PS_WEBSERVICE_KEY` w `.env`.

- uruchomienie i szczegóły działania: [deploy/import/README.md](deploy/import/README.md)

# Testowanie
`make test` - uruchamia testy E2E sklepu w Playwright i generuje raport HTML z wynikami.

- Uruchamia testy end-to-end w izolowanym kontenerze (nie wymaga instalacji Node.js ani przeglądarek).
- Automatycznie generuje i udostępnia interaktywny raport HTML pod adresem http://localhost:9323.
- Zapisuje zrzuty ekranu z ewentualnych błędów w folderze test-results/.

`make sprawdz` - sprawdza metryki danych sklepu i przy każdej pokazuje wynik oraz `OK` albo `BŁĄD`, gdy dane nie spełniają wymagania.

# CI
Każdy PR (i każdy push na master) uruchamia [`.github/workflows/ci.yml`](.github/workflows/ci.yml) w GitHub Actions:

| Zadanie | Co sprawdza |
|---|---|
| Python (ruff, pytest) | ruff check na kodzie Pythona w scraper/ i deploy/ oraz testy jednostkowe scrapera z scraper/tests/ |
| gitleaks (cała historia) | sekrety we wszystkich commitach ze wszystkich gałęzi; wyjątki z uzasadnieniem w [`.gitleaks.toml`](.gitleaks.toml) |
| ESLint (tests/) | kod testów E2E w tests/ |

**Nie scalamy PR z czerwonym pipeline.** Prowadzący sprawdza to na liście PR. Jeśli CI nie przechodzi, poprawiamy kod w tym samym PR, a nie wyłączamy sprawdzenia.

Jeśli gitleaks znajdzie prawdziwy sekret, nie wystarczy go usunąć kolejnym commitem, bo zostaje w historii. Hasło lub klucz trzeba unieważnić i wygenerować nowy.

Te same sprawdzenia lokalnie, przed pushem:
```bash
pip install -r scraper/requirements-dev.txt   # najlepiej w venv
ruff check scraper deploy
python -m pytest
cd tests && npm ci && npm run lint
```

# Problemy
## `Cannot download language pack "pl"`
Instalator pobiera polską paczkę językową z `https://i18n.prestashop-project.org`. Jeśli antywirus (Norton, Avast, AVG, ESET…) skanuje ruch HTTPS, podmienia certyfikat i kontener odrzuca połączenie. Instalacja zatrzymuje się w połowie, a sklep zostaje zepsuty: po restarcie w logach widać `PrestaShop Core already installed`, ale nie ma języków ani konta admina.

Sprawdzenie (przy uruchomionym kontenerze):
```
docker compose --env-file .env -f deploy/compose.yaml exec prestashop curl -sS -o /dev/null -w "%{http_code}\n" https://i18n.prestashop-project.org/
```
`SSL certificate problem` oznacza, że winny jest antywirus. Kod HTTP (np. `400`) oznacza, że połączenie działa.

Naprawa:
1. Wyłącz skanowanie HTTPS w antywirusie albo dodaj `i18n.prestashop-project.org` do wykluczeń. W Nortonie: Zabezpieczenia → Zaawansowane → Safe Web → HTTPS Scanning / zakładka Wykluczenia. Samo wyłączenie blokowania elementów śledzących nie pomaga.
2. `make reset`, a potem `make up`.

