<?php
// Kopia zapasowa sklepu, część w PHP. Uruchamia go deploy/dane/kopia.sh:
//   php kopia.php opis                  opis bieżącego sklepu do kopia.txt (make backup)
//   php kopia.php wersja <kopia.txt>    kod 1, gdy kopia jest z innej wersji PrestaShop niż ten sklep (make restore)
//   php kopia.php sprawdz <kopia.txt>   liczba produktów, zdjęć, klientów i zamówień w bazie i w kopii (make restore)
//   php kopia.php parametry <plik>      app/config/parameters.php z kopii, z połączeniem z bazą tej instalacji (make restore)

require_once '/var/www/html/config/config.inc.php';

// Liczone przy kopii i porównywane po wczytaniu bazy
const TABELE = [
    'produkty' => 'product',
    'zdjecia' => 'image',
    'klienci' => 'customer',
    'zamowienia' => 'orders',
];

// Te wartości parameters.php zostają z bieżącej instalacji, bo pochodzą z .env tego komputera.
// Reszta jest z kopii, bo pasuje do jej bazy: klucze ciasteczek i szyfrowania (cookie_key,
// new_cookie_key, secret), prefiks tabel i data założenia sklepu.
const POLACZENIE = ['database_host', 'database_port', 'database_name', 'database_user', 'database_password'];

function liczby(): array
{
    $wynik = [];

    foreach (TABELE as $nazwa => $tabela) {
        $wynik[$nazwa] = (int) Db::getInstance()->getValue('SELECT COUNT(*) FROM `' . _DB_PREFIX_ . $tabela . '`');
    }

    return $wynik;
}

function opis(): void
{
    echo "# Kopia sklepu z make backup. Zawartość i odtwarzanie: docs/backup.md\n";
    echo 'utworzona=' . date('Y-m-d H:i:s T') . "\n";
    echo 'prestashop=' . _PS_VERSION_ . "\n";
    echo 'domena=' . Configuration::get('PS_SHOP_DOMAIN_SSL') . "\n";

    foreach (liczby() as $nazwa => $liczba) {
        echo "$nazwa=$liczba\n";
    }
}

function wczytajOpis(string $plik): array
{
    $opis = [];

    foreach (file($plik, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $wiersz) {
        if ($wiersz[0] !== '#' && str_contains($wiersz, '=')) {
            [$klucz, $wartosc] = explode('=', $wiersz, 2);
            $opis[$klucz] = $wartosc;
        }
    }

    return $opis;
}

// Zrzut bazy pasuje tylko do tej wersji PrestaShop, z której pochodzi (schemat tabel)
function wersja(array $opis): void
{
    $wersjaKopii = $opis['prestashop'] ?? '?';

    if ($wersjaKopii !== _PS_VERSION_) {
        fwrite(STDERR, "BLAD: kopia jest z PrestaShop $wersjaKopii, a sklep ma " . _PS_VERSION_ . ".\n"
            . "Odtwórz ją na tej samej wersji (obraz prestashop w deploy/compose.yaml). Sklep się nie zmienił.\n");
        exit(1);
    }

    echo "Kopia z {$opis['utworzona']}, sklep {$opis['domena']}, PrestaShop $wersjaKopii: OK\n";
}

function sprawdz(array $opis): void
{
    $rozne = false;
    printf("%-11s %7s %7s\n", '', 'kopia', 'sklep');

    foreach (liczby() as $nazwa => $liczba) {
        $wKopii = (int) ($opis[$nazwa] ?? -1);
        $rozne = $rozne || $wKopii !== $liczba;
        printf("%-11s %7d %7d  %s\n", $nazwa, $wKopii, $liczba, $wKopii === $liczba ? 'OK' : 'INNE');
    }

    // Liczby są z chwili tuż przed zrzutem bazy, więc różnica bywa też wtedy, gdy ktoś coś zmienił
    // w sklepie w trakcie make backup.
    if ($rozne) {
        fwrite(STDERR, "UWAGA: baza po odtworzeniu ma inną liczbę rekordów niż opis kopii.\n");
    }
}

function parametry(string $plikZKopii): void
{
    $biezacy = _PS_ROOT_DIR_ . '/app/config/parameters.php';
    $kopia = require $plikZKopii;
    $teraz = require $biezacy;

    foreach (POLACZENIE as $klucz) {
        $kopia['parameters'][$klucz] = $teraz['parameters'][$klucz] ?? '';
    }

    // Najpierw obok, potem podmiana, żeby sklep nigdy nie czytał niepełnego pliku
    $nowy = "$biezacy.nowy";

    if (file_put_contents($nowy, '<?php return ' . var_export($kopia, true) . ";\n") === false
        || !rename($nowy, $biezacy)) {
        throw new RuntimeException('Nie udalo sie zapisac app/config/parameters.php');
    }

    echo "parameters.php: klucze sklepu z kopii, połączenie z bazą z .env\n";
}

match ($argv[1] ?? '') {
    'opis' => opis(),
    'wersja' => wersja(wczytajOpis($argv[2])),
    'sprawdz' => sprawdz(wczytajOpis($argv[2])),
    'parametry' => parametry($argv[2]),
    default => throw new InvalidArgumentException('Uzycie: php kopia.php opis|wersja|sprawdz|parametry [plik]'),
};
