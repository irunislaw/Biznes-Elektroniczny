# ADR-0003: Architektura kontenerów i HTTPS

- **Status:** przyjęta
- **Data:** 2026-10-12
- **Autor:** Michał Irek
- **Zadanie:** BE-8 / #NN

## Kontekst

Sklep uruchamiamy lokalnie z `deploy/compose.yaml`. Są tam MariaDB (`db`), PrestaShop 8.2 z Apache (`prestashop`, oficjalny obraz z automatyczną instalacją) i Mailpit. Po BE-7 sklep działał tylko po HTTP na porcie 8080.

Wymagania (BE-8, W1):

- sklep i panel działają po HTTPS, SSL jest włączony na wszystkich stronach sklepu,
- `http://…` odpowiada 301 na `https://…`,
- certyfikat powstaje skryptem przy `make up`, jeśli jeszcze go nie ma. Klucz prywatny nie może trafić do repozytorium, bo sekret w repo to 0 pkt za W1,
- `make up` działa tak samo na Windowsie (Docker Desktop, Git Bash) i na Linuksie,
- nie przekraczamy limitów projektu: uruchomienie ≤15 min, repozytorium ≤200 MB.

Główne ryzyko to pętla przekierowań. Przy wymuszonym SSL PrestaShop przekierowuje na HTTPS każde żądanie, które uważa za niezabezpieczone. Za reverse proxy każde żądanie dociera do sklepu po HTTP, więc bez dodatkowej informacji sklep przekierowuje bez końca. Do tego część panelu oparta na Symfony nie ufa żadnemu proxy (`Request::setTrustedProxies([], …)` w `admin-dev/index.php`), więc sam nagłówek `X-Forwarded-Proto` nie wystarcza.

## Rozważane opcje

### Opcja 1: nginx jako reverse proxy kończący TLS

Osobny kontener `nginx` przyjmuje ruch na portach 80 i 443, odpowiada 301 z HTTP na HTTPS, kończy TLS i przekazuje żądania do `prestashop:80` po HTTP w sieci Dockera.

- plusy:
  - obraz `prestashop/prestashop` zostaje bez zmian i bez własnego Dockerfile, więc aktualizacja sklepu to zmiana tagu,
  - TLS i przekierowanie są w konfiguracji nginx, a nie w `.htaccess`, który PrestaShop nadpisuje przy zmianie ustawień przyjaznych URL-i,
  - jedno wejście z zewnątrz, kontener sklepu nie wystawia portów,
  - ten sam układ pasuje do serwera: certyfikat self-signed można później zastąpić certyfikatem z Let's Encrypt bez ruszania sklepu.
- minusy:
  - dodatkowy kontener,
  - sklepowi trzeba przekazać, że klient łączył się po HTTPS, inaczej powstaje pętla przekierowań.

### Opcja 2: TLS w Apache w kontenerze sklepu

Włączamy `mod_ssl` i vhost na 443 w kontenerze PrestaShop, a przekierowanie 301 robi vhost na 80.

- plusy:
  - o jeden kontener mniej,
  - PrestaShop widzi HTTPS bezpośrednio, więc problem pętli za proxy nie występuje.
- minusy:
  - potrzebny własny obraz (`a2enmod ssl`, `a2ensite default-ssl`, vhost z przekierowaniem), bo `/etc/apache2` nie leży w wolumenie i zmiany znikają przy odtworzeniu kontenera,
  - konfiguracja serwera WWW miesza się z aplikacją, a każda aktualizacja obrazu sklepu wymaga przebudowy naszego obrazu,
  - przekierowania nie można trzymać w `.htaccess` (PrestaShop go nadpisuje), więc i tak trzeba utrzymywać własny vhost.

### Opcja 3: Caddy albo Traefik jako reverse proxy

Proxy, które same wystawiają certyfikaty. Caddy ma wbudowane lokalne CA.

- plusy:
  - mniej konfiguracji TLS.
- minusy:
  - ticket wymaga certyfikatu generowanego naszym skryptem, więc główna zaleta tych narzędzi, czyli automatyczne certyfikaty, nic nie daje,
  - pętla przekierowań w PrestaShop zostaje taka sama jak przy nginx.

## Decyzja

Wybieramy opcję 1 (nginx), ponieważ spełnia wszystkie wymagania bez modyfikowania obrazu sklepu. Jej jedyny istotny koszt, czyli pętla przekierowań, rozwiązuje jedna linia konfiguracji Apache.

```
przeglądarka / curl
  ├─ http://localhost:8080  ──► nginx :80  ──► 301 Location: https://localhost:8443/…
  ├─ https://localhost:8443 ──► nginx :443 (TLS, certyfikat z deploy/certs/)
  │                               │ HTTP + X-Forwarded-Proto: https
  │                               ▼
  │                             prestashop :80 (Apache, HTTPS=on) ──► db :3306 (MariaDB)
  └─ http://localhost:8025  ──► mailpit
```

Porty na hoście wystawiają tylko `nginx` i `mailpit`.

Szczegóły:

- **Certyfikat.** `deploy/scripts/gen-cert.sh` tworzy self-signed certyfikat dla `localhost`: RSA 2048, ważny 365 dni, z `subjectAltName: DNS:localhost, IP:127.0.0.1`, bez którego przeglądarki odrzucają certyfikat. Skrypt nic nie robi, gdy certyfikat już istnieje.
- **Generowanie w kontenerze.** `make up` zależy od celu `make certs`, który uruchamia skrypt w kontenerze `alpine/openssl:3.5.8`. Dzięki temu na hoście nie trzeba mieć openssl i wszędzie działa ta sama wersja. Openssl z Git Bash zamienia argumenty typu `/CN=localhost` na ścieżki Windows, a wersje openssl różnią się między systemami. Na Linuksie kontener działa z UID/GID użytkownika, żeby pliki w `deploy/certs/` nie należały do roota.
- **Alternatywa dla certyfikatu.** mkcert dałby certyfikat bez ostrzeżenia w przeglądarce, ale wymaga instalacji narzędzia i lokalnego CA na każdym komputerze.
- **Sekrety.** Katalog `deploy/certs/` jest w `.gitignore`.
- **Końce linii.** `.gitattributes` wymusza LF w plikach `*.sh`. Skrypt działa w kontenerze Linuksa także na Windowsie, a z końcami CRLF `sh` się na nim wywraca.
- **Porty.** HTTP `SHOP_PORT=8080`, HTTPS `SHOP_HTTPS_PORT=8443`, obie wartości w `.env`. Porty powyżej 1024 nie wymagają roota i rzadziej kolidują z innymi programami niż 80 i 443 na Windowsie. Mailpit zostaje na `8025` po HTTP, poza proxy, bo to narzędzie deweloperskie.
- **nginx** (`deploy/nginx/default.conf.template`).
  - Na porcie 80 odpowiada `return 301 https://$host:${SHOP_HTTPS_PORT}$request_uri`.
  - Na porcie 443 obsługuje TLS 1.2 i 1.3 i przekazuje żądania przez `proxy_pass http://prestashop:80`.
  - Wysyła `Host $http_host` (z portem) i `X-Forwarded-Proto: https`. Port w nagłówku Host jest potrzebny, bo PrestaShop porównuje go z domeną sklepu i przy niezgodności sam przekierowuje.
- **Informacja o HTTPS dla sklepu.** Plik `deploy/apache/forwarded-https.conf`, montowany do `conf-enabled`, zawiera `SetEnvIf X-Forwarded-Proto "^https$" HTTPS=on`. Dzięki temu `$_SERVER['HTTPS']` widzą zarówno starsza część sklepu (`Tools::usingSecureMode()`), jak i część panelu oparta na Symfony.
- **SSL w sklepie.** Ustawiamy `PS_ENABLE_SSL=1` i `PS_DOMAIN=localhost:${SHOP_HTTPS_PORT}`. Instalator ustawia wtedy `PS_SSL_ENABLED` i `PS_SSL_ENABLED_EVERYWHERE`, więc nic nie trzeba klikać w panelu.

## Konsekwencje

- zyskujemy:
  - HTTPS bez własnego obrazu sklepu. Cała konfiguracja to trzy pliki w `deploy/` i zmiany w `compose.yaml` oraz `Makefile`,
  - `make up` na czystym klonie samo generuje certyfikat, na Windowsie i na Linuksie,
  - miejsce na kolejne zadania proxy (np. kompresja, cache, certyfikat produkcyjny) bez zmian w kontenerze sklepu.
- tracimy albo musimy uważać:
  - przeglądarka pokazuje ostrzeżenie o certyfikacie, a `curl` wymaga `-k`. To koszt certyfikatu self-signed,
  - domena i SSL zapisują się w bazie tylko przy instalacji, podobnie jak reguły w `.htaccess`, więc zmiana portu HTTPS wymaga `make reset`,
  - `SetEnvIf` ufa nagłówkowi `X-Forwarded-Proto` od każdego, kto połączy się z Apache. To jest bezpieczne tylko dlatego, że kontener `prestashop` nie wystawia portów. Nie dodajemy mu z powrotem sekcji `ports`,
  - nie dodajemy nagłówka HSTS, bo przy certyfikacie self-signed na `localhost` potrafi na długo zablokować stronę w przeglądarce,
  - na Fedorze i RHEL z SELinuxem montowane pliki wymagają opcji `:z`, np. `./certs:/etc/nginx/certs:ro,z`.
- co trzeba zrobić dalej:
  - każdy po scaleniu tego zadania: dopisać `SHOP_HTTPS_PORT=8443` do `.env`, potem `make reset` i `make up`,
  - przy wdrożeniu na serwer zastąpić certyfikat self-signed certyfikatem z Let's Encrypt w tym samym nginx.
