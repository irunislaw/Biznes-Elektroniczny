<?php
// Dopasowuje sklep po wczytaniu zrzutu bazy do zmiennych z .env (przekazanych przez deploy/compose.yaml):
// - domena i SSL: PS_DOMAIN, PS_ENABLE_SSL. Zrzut ma adres z komputera, na którym powstał,
// - konto administratora: ADMIN_MAIL, ADMIN_PASSWD. Zrzut ma zaślepkę e-maila i puste hasło,
// - adresy e-mail sklepu i sekrety modułu newslettera, które zrzut wyczyścił.
// Zmienia tylko to, co się różni, więc kolejne uruchomienia niczego nie psują
// (np. hasło nie jest haszowane od nowa, więc zalogowany administrator nie zostaje wylogowany).

require_once '/var/www/html/config/config.inc.php';

use PrestaShop\PrestaShop\Adapter\ServiceLocator;

// Ten sam adres wpisuje zrzut (deploy/dane/baza.sh)
const ZASLEPKA_EMAIL = 'admin@example.com';

function env(string $name): string
{
    $value = getenv($name);

    if ($value === false || $value === '') {
        throw new RuntimeException("Brak zmiennej $name w kontenerze (sprawdz .env i uruchom make up)");
    }

    return $value;
}

function ustaw(string $key, string $value): bool
{
    if ((string) Configuration::get($key) === $value) {
        return false;
    }

    if (!Configuration::updateValue($key, $value)) {
        throw new RuntimeException("Nie udalo sie ustawic $key");
    }

    return true;
}

$domain = env('PS_DOMAIN');
$ssl = env('PS_ENABLE_SSL') === '1' ? '1' : '0';
$email = env('ADMIN_MAIL');
$password = env('ADMIN_PASSWD');

if (!Validate::isEmail($email)) {
    throw new RuntimeException('ADMIN_MAIL nie jest poprawnym adresem e-mail');
}

$db = Db::getInstance();

// Domena i SSL
$changed = false;

foreach ([
    'PS_SHOP_DOMAIN' => $domain,
    'PS_SHOP_DOMAIN_SSL' => $domain,
    'PS_SSL_ENABLED' => $ssl,
    'PS_SSL_ENABLED_EVERYWHERE' => $ssl,
] as $key => $value) {
    $changed = ustaw($key, $value) || $changed;
}

$where = "main = 1 AND (domain <> '" . pSQL($domain) . "' OR domain_ssl <> '" . pSQL($domain) . "')";

if ($db->getValue('SELECT COUNT(*) FROM `' . _DB_PREFIX_ . 'shop_url` WHERE ' . $where)) {
    if (!$db->update('shop_url', ['domain' => pSQL($domain), 'domain_ssl' => pSQL($domain)], $where)) {
        throw new RuntimeException('Nie udalo sie ustawic domeny w ps_shop_url');
    }
    $changed = true;
}

// .htaccess zawiera domenę sklepu
if ($changed && !Tools::generateHtaccess()) {
    throw new RuntimeException('Nie udalo sie wygenerowac .htaccess');
}

echo "Domena i SSL ($domain): OK\n";

// Administrator
$employeeId = (int) $db->getValue(
    'SELECT id_employee FROM `' . _DB_PREFIX_ . 'employee`'
    . ' WHERE id_profile = ' . (int) _PS_ADMIN_PROFILE_ . ' AND active = 1 ORDER BY id_employee'
);
$employee = new Employee($employeeId);

if (!Validate::isLoadedObject($employee)) {
    throw new RuntimeException('Nie znaleziono aktywnego superadministratora');
}

$crypto = ServiceLocator::get('\\PrestaShop\\PrestaShop\\Core\\Crypto\\Hashing');
$changed = false;

if ($employee->email !== $email) {
    $employee->email = $email;
    $changed = true;
}

if ($employee->passwd === '' || !$crypto->checkHash($password, $employee->passwd)) {
    $employee->passwd = $crypto->hash($password);
    $employee->last_passwd_gen = date('Y-m-d H:i:s');
    $changed = true;
}

if ($changed && !$employee->update()) {
    throw new RuntimeException('Nie udalo sie zapisac konta administratora');
}

echo "Administrator ($email): OK\n";

// E-maile sklepu: instalator ustawia je na ADMIN_MAIL, zrzut na zaślepkę.
// Wartości zmienione później ręcznie zostają.
foreach (['PS_SHOP_EMAIL', 'PS_LOGS_EMAIL_RECEIVERS', 'MA_MERCHANT_MAILS'] as $key) {
    if (Configuration::get($key) === ZASLEPKA_EMAIL) {
        ustaw($key, $email);
    }
}

if (!$db->update('contact', ['email' => pSQL($email)], "email = '" . pSQL(ZASLEPKA_EMAIL) . "'")) {
    throw new RuntimeException('Nie udalo sie ustawic e-maili kontaktowych');
}

// Sekrety modułu ps_emailsubscription, losowane tak samo jak przy jego instalacji
if ((string) Configuration::get('NW_SALT') === '') {
    ustaw('NW_SALT', Tools::passwdGen(16));
}

if ((string) Configuration::get('PS_NEWSLETTER_RAND') === '') {
    ustaw('PS_NEWSLETTER_RAND', mt_rand() . mt_rand());
}

echo "E-maile sklepu i newsletter: OK\n";
