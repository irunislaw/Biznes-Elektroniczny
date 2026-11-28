# Kopia zapasowa sklepu

`make backup` zapisuje kopię działającego sklepu: bazę z klientami i zamówieniami, zdjęcia i pliki konfiguracyjne. `make restore` odtwarza z niej sklep na czystym środowisku.

```bash
make backup                                              # kopia do backups/sklep-<data>_<godzina>.tar
make reset                                               # usuwa kontenery i wolumeny (bazę i pliki sklepu)
make up
make restore PLIK=backups/sklep-2026-11-19_231958.tar    # sklep z kopii
```

Kopia to coś innego niż zrzut danych w repozytorium (`make zrzut`, [ADR-0002](adr/0002-inicjalizacja-danych.md)). Zrzut to katalog produktów bez klientów, zamówień i sekretów, wspólny dla całego zespołu. Kopia to cały stan jednego sklepu i zostaje na komputerze, na którym powstała.

## Co jest w kopii

Archiwum `backups/sklep-<data>_<godzina>.tar` to zwykły tar bez kompresji, bo zdjęcia JPG i tak się nie kompresują. Zrzut bazy w środku jest w gzip.

| Plik w archiwum | Co to jest |
|---|---|
| `kopia.txt` | opis kopii: data, wersja PrestaShop, domena oraz liczba produktów, zdjęć, klientów i zamówień |
| `baza.sql.gz` | pełny zrzut bazy (`mariadb-dump --single-transaction`): klienci, adresy, koszyki, zamówienia, faktury, konta pracowników, klucze Webservice i wszystkie ustawienia z panelu |
| `img/` | wszystkie zdjęcia sklepu: produkty ze wszystkimi miniaturami, kategorie, logo |
| `modules/ps_banner/img/` | baner strony głównej. Moduł `ps_banner` trzyma go u siebie, a nie w `img/` |
| `app/config/parameters.php` | połączenie z bazą i klucze sklepu (`cookie_key`, `new_cookie_key`, `secret`) |
| `.htaccess` | reguły Apache wygenerowane przez PrestaShop, razem z domeną sklepu |
| `config/themes/` | ustawienia motywu dla sklepu, zapisywane przy włączaniu motywu |

W kopii nie ma:
- kodu: PrestaShop pochodzi z obrazu Dockera, a moduł [`becookiebanner`](../shop/modules/becookiebanner/) i motyw [`gitara`](../shop/themes/gitara/) z repozytorium. `make restore` kopiuje je z repozytorium,
- szablonów e-maili. `make restore` generuje je tak samo jak `make init`,
- cache, logów i sesji PHP z `var/`. Sklep tworzy je sam,
- `upload/` i `download/`, bo są puste: sklep nie sprzedaje produktów wirtualnych ani personalizowanych,
- `.env`. Hasło do bazy i porty `make restore` bierze z `.env` komputera, na którym odtwarza kopię,
- wiadomości z Mailpit.

Pliki są wybrane na początku [`deploy/dane/kopia.sh`](../deploy/dane/kopia.sh) (`ZDJECIA`, `KONFIGURACJA`, `PARAMETRY`).

## Dlaczego kopia nie trafia do repozytorium

W kopii są dane osobowe klientów (imię, nazwisko, e-mail, adres, telefon), hasze haseł klientów i pracowników, klucze Webservice, klucze szyfrowania z `parameters.php` i hasło do bazy. Dlatego:
- `backups/` jest w [`.gitignore`](../.gitignore), podobnie jak wszystkie pliki `*.tar`. Nie używamy `git add -f`,
- gitleaks w CI nie rozpoznaje danych osobowych, więc `.gitignore` to jedyna blokada. Kopii nie wysyłamy też komunikatorem ani mailem,
- na Linuksie i macOS archiwum może czytać tylko jego właściciel (`umask 077` w [`backup.sh`](../deploy/scripts/backup.sh)). Na Windowsie plik ma uprawnienia katalogu, w którym leży repozytorium,
- niepotrzebną kopię usuwamy.

## Jak powstaje kopia (`make backup`)

Skrypt [`deploy/scripts/backup.sh`](../deploy/scripts/backup.sh) działa na uruchomionym sklepie, nie zatrzymuje go i niczego w nim nie zmienia:
1. zapisuje opis sklepu do `kopia.txt` ([`kopia.php opis`](../deploy/dane/kopia.php)),
2. zrzuca całą bazę w jednej transakcji ([`baza.sh kopia`](../deploy/dane/baza.sh)), więc zamówienie złożone w trakcie jest w kopii w całości albo wcale. Sprawdza, czy zrzut kończy się wierszem `-- Dump completed`, który `mariadb-dump` pisze na samym końcu. Bez tego przerwany zrzut wyglądałby na poprawny,
3. składa archiwum w kontenerze sklepu i zapisuje je do `backups/`. Niepełne archiwum (np. przy braku miejsca) ma końcówkę `.tmp` i jest usuwane.

Na Windows 11 z Docker Desktop kopia sklepu z pełnymi danymi trwa 28 s i ma 1,3 GB.

## Jak odtworzyć kopię (`make restore`)

Na czystym środowisku: `make reset` (jeśli są jakieś dane), `make up`, potem `make restore PLIK=backups/...`. `make init` nie jest potrzebny. Skrypt [`deploy/scripts/restore.sh`](../deploy/scripts/restore.sh):
1. czeka, aż instalator PrestaShop skończy pracę, i kopiuje moduł i motyw z repozytorium. Robi to przed wczytaniem bazy, bo baza z kopii ma włączony motyw `gitara` i bez jego plików PrestaShop się nie uruchamia,
2. rozpakowuje kopię do `var/kopia` w kontenerze sklepu (katalog jest zamknięty dla przeglądarki) i sprawdza, czy kopia jest z tej samej wersji PrestaShop. Zrzut bazy pasuje tylko do schematu tabel swojej wersji. Przy innej wersji albo uszkodzonym archiwum skrypt kończy się, zanim zmieni bazę,
3. zastępuje bazę zrzutem z kopii ([`baza.sh odtworz`](../deploy/dane/baza.sh)): usuwa ją i zakłada od nowa, więc nie zostają tabele, których w kopii nie było. Potem porównuje liczbę produktów, zdjęć, klientów i zamówień z `kopia.txt`,
4. zastępuje `img/`, `modules/ps_banner/img/`, `.htaccess` i `config/themes/` plikami z kopii. Z `parameters.php` bierze klucze sklepu, a połączenie z bazą zostawia z bieżącej instalacji, czyli z `.env` ([`kopia.php parametry`](../deploy/dane/kopia.php)),
5. ustawia domenę i SSL z `.env` ([`dopasuj.php domena`](../deploy/dane/dopasuj.php)): `PS_SHOP_DOMAIN`, `ps_shop_url`, linki menu górnego i `.htaccess`. Kopię można więc odtworzyć na innym porcie niż ten, na którym powstała,
6. generuje polskie szablony e-maili i czyści cache.

Po odtworzeniu:
- do panelu logujemy się kontem z kopii, z hasłem z chwili kopii, a nie z `ADMIN_MAIL` i `ADMIN_PASSWORD` z `.env`. Tak samo klucz Webservice jest z kopii,
- ustawienia sklepu są z kopii, a nie z `deploy/config/`, więc zmiany wprowadzone w panelu zostają,
- jeśli kopia jest z innej wersji danych niż `deploy/dane/sklep.sql.gz` w repozytorium, `make restore` wypisuje ostrzeżenie. Wtedy nie uruchamiamy `make init`, bo wczytałby zrzut z repozytorium i zastąpił nim całą bazę razem z klientami i zamówieniami z kopii.

`make restore` zastępuje bazę i zdjęcia także wtedy, gdy w sklepie są już dane. Służy do odtwarzania na czystym środowisku.

### Bez `make`

Archiwum to zwykły tar, więc kopię da się odtworzyć ręcznie, np. na innym serwerze z PrestaShop 8.2.8:
```bash
tar -xf sklep-2026-11-19_231958.tar
gunzip -c baza.sql.gz | mariadb -u <użytkownik> -p <baza>
```
Potem trzeba przenieść `img/` i `modules/ps_banner/img/` do katalogu sklepu, przepisać klucze z `parameters.php` i ustawić domenę w `ps_configuration` (`PS_SHOP_DOMAIN`, `PS_SHOP_DOMAIN_SSL`) oraz w `ps_shop_url`.

## Eksport ustawień: `deploy/config/`

Eksportem ustawień sklepu są skrypty w [`deploy/config/`](../deploy/config/). Są w repozytorium, a `make init` uruchamia je na każdym sklepie. Nie mają danych klientów ani sekretów: dane konta bankowego są fikcyjne, a Mailpit działa bez hasła.

| Skrypt | Co ustawia |
|---|---|
| [`theme.php`](../deploy/config/theme.php) | włącza motyw potomny `gitara` |
| [`locale.php`](../deploy/config/locale.php) | domyślny język polski, kraj Polska, waluta PLN |
| [`taxes.php`](../deploy/config/taxes.php) | włączone podatki, stawki VAT 23, 8, 5 i 0% i ich grupy reguł |
| [`payments.php`](../deploy/config/payments.php) | przelew (fikcyjne dane konta) i płatność przy odbiorze, faktury, wyłączona płatność czekiem |
| [`carriers.php`](../deploy/config/carriers.php) | Kurier (18,45 zł, logo `kurier.jpg`) i odbiór w sklepie (za darmo, logo sklepu), darmowa dostawa kurierem od 2000 zł, do 50 kg |
| [`mail.php`](../deploy/config/mail.php) | wysyłka e-maili przez SMTP do Mailpit |
| [`cookies.php`](../deploy/config/cookies.php) | instaluje i włącza moduł z informacją o cookies |
| [`cms.php`](../deploy/config/cms.php) | strony informacyjne (treść w [`cms/`](../deploy/config/cms/)), stopka, nazwa i adres sklepu, tekst na stronie głównej |
| [`uklad.php`](../deploy/config/uklad.php) | menu górne, moduły strony głównej, lewa kolumna, 16 produktów na stronę, logo, baner |

Czym to się różni od kopii:

| | Eksport ustawień (`deploy/config/`) | Kopia (`make backup`) |
|---|---|---|
| gdzie leży | w repozytorium | w `backups/` na jednym komputerze |
| co zawiera | ustawienia sklepu zapisane jako kod | cały sklep: dane, zdjęcia, ustawienia, pliki konfiguracyjne |
| dane klientów i sekrety | nie | tak |
| kiedy działa | przy każdym `make init` | przy `make restore` |
| ustawienie zmienione tylko w panelu | nie ma go, a następne `make init` je cofa | jest |

Ustawienie, które ma mieć każdy sklep zespołu, dopisujemy do skryptu w `deploy/config/`, a nie tylko klikamy w panelu. Sklep z samymi ustawieniami i katalogiem, bez klientów i zamówień, daje `make reset`, `make up`, `make init`.

## Próba odtworzenia

19.11.2026, Windows 11, Docker Desktop, obrazy Dockera pobrane wcześniej:
1. `make up`, `make init`: sklep z pełnymi danymi (1161 produktów, 6588 zdjęć).
2. Zamówienie złożone testem E2E w Chromium ([`e2eTests.spec.ts`](../tests/tests/e2eTests.spec.ts)): nowy klient, zamówienie `ZAMRTQFTD` na 1481,99 zł z płatnością przy odbiorze i fakturą.
3. `make backup`: 28 s, archiwum 1,3 GB, zrzut bazy 888 KB, 41 045 plików JPG.
4. `make reset`, `make up`, `make restore`: 164 s od `make reset` do działającego sklepu (7 + 23 + 134 s). Z tego ok. 45 s to czekanie na instalator PrestaShop, a ok. 50 s rozpakowanie 1,3 GB zdjęć do wolumenu.
5. Sprawdzenie:
   - sumy kontrolne (`CHECKSUM TABLE`) 275 z 276 tabel takie same jak przed kopią. Jedyna różnica to `ps_log` z wpisami o generowaniu szablonów e-maili w kroku 6,
   - klient loguje się swoim hasłem, zamówienie `ZAMRTQFTD` jest w historii zamówień, a faktura pobiera się jako PDF,
   - strona główna, zdjęcia produktów (także `large_default`), logo i baner zwracają 200.
6. Ta sama kopia odtworzona na porcie 9443 (`SHOP_HTTPS_PORT=9443`): strona główna, kategoria i zdjęcia działają pod `https://localhost:9443`, a domena w bazie i link „Katalog produktów” w menu to `localhost:9443`.

Pierwsza próba pokazała, że baza z kopii ma włączony motyw `gitara`, którego plików świeża instalacja nie ma, więc PrestaShop się nie uruchamiał. Dlatego moduł i motyw są kopiowane na samym początku, także w `make init`. Ten sam problem pojawiłby się w `make init` po następnym `make zrzut`. Druga próba na porcie 9443 pokazała, że link w menu górnym zostawał ze starą domeną, więc zmienia go teraz `dopasuj.php`.
