# E-commerce website
E-commerce project to create 1:1 representation of existing shop in PrestaShop 8.x

# authors
 Tymon Dera, Maria Rek, Seweryn Grabowski, Aleksandra Wiśniewska, Michał Irek

# Uruchomienie
Wymagania: Docker z Docker Compose v2 (na Windowsie Docker Desktop), `make`, git. Na Windowsie polecenia wpisujemy w Git Bash. Porty 8080 i 8025 muszą być wolne.

1. Sklonuj repozytorium i wejdź do jego katalogu.
2. `cp .env.example .env` (opcjonalnie zmień hasła w `.env`).
3. `make up`, a postęp instalacji śledź przez `make logs`. Pierwszy start trwa kilka minut; gotowe, gdy w logach pojawi się `-- Installation successful! --`.
4. `make init` (na razie nic nie konfiguruje, kroki dojdą w kolejnych ticketach).
5. Adresy:
   - sklep: http://localhost:8080
   - panel administracyjny: http://localhost:8080/admin-panel (login `ADMIN_MAIL` / `ADMIN_PASSWORD` z `.env`)
   - Mailpit: http://localhost:8025

`make down` zatrzymuje kontenery, dane zostają w wolumenach. `make reset` usuwa kontenery razem z wolumenami (baza i pliki sklepu), więc następne `make up` instaluje sklep od zera.

# Scraper
Scraper zbierający produkty z oryginalnego sklepu znajduje się w katalogu [`scraper/`](scraper/) i działa niezależnie od kontenerów (wymaga Pythona).

- instalacja, konfiguracja i uruchomienie: [scraper/README.md](scraper/README.md)
- wyniki: katalog `scraper-results/`
- uzasadnienie wyboru bibliotek: [ADR-0001](docs/adr/0001-biblioteka-scrapera.md)

# Testowanie
`make test` - uruchamia testy E2E sklepu w Playwright i generuje raport HTML z wynikami.

- Uruchamia testy end-to-end w izolowanym kontenerze (nie wymaga instalacji Node.js ani przeglądarek).
- Automatycznie generuje i udostępnia interaktywny raport HTML pod adresem http://localhost:9323.
- Zapisuje zrzuty ekranu z ewentualnych błędów w folderze test-results/.

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

