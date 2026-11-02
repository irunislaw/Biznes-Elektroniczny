
<?php

$key = getenv('PS_WEBSERVICE_KEY');

try {
    require_once '/var/www/html/config/config.inc.php';

    // Aktywacja Webservice
    if (!Configuration::updateValue('PS_WEBSERVICE', 1)) {
        throw new RuntimeException('Nie udalo sie wlaczyc Webservice.');
    }

    $db = Db::getInstance();

    // Pobranie lub utworzenie konta API
    $accountId = (int) $db->getValue(
        'SELECT id_webservice_account FROM `' . _DB_PREFIX_ . 'webservice_account`'
        . " WHERE `key` = '" . pSQL($key) . "'"
    );

    if (!$accountId) {
        if (!$db->insert('webservice_account', [
            'key' => $key,
            'description' => 'test',
            'active' => 1,
        ])) {
            throw new RuntimeException('Nie udalo sie utworzyc konta API.');
        }

        $accountId = (int) $db->Insert_ID();
    }

    if (!$db->update(
        'webservice_account',
        ['active' => 1],
        'id_webservice_account = ' . $accountId
    )) {
        throw new RuntimeException('Nie udalo sie aktywowac konta API.');
    }

    // Powiązanie konta z aktywnymi sklepami
    $shopIds = Shop::getShops(true, null, true);

    if (!$shopIds) {
        throw new RuntimeException('Nie znaleziono aktywnego sklepu.');
    }

    foreach ($shopIds as $shopId) {
        $where = 'id_webservice_account = ' . $accountId
            . ' AND id_shop = ' . (int) $shopId;

        if (!$db->getValue(
            'SELECT 1 FROM `' . _DB_PREFIX_ . 'webservice_account_shop` WHERE ' . $where
        )) {
            if (!$db->insert('webservice_account_shop', [
                'id_webservice_account' => $accountId,
                'id_shop' => (int) $shopId,
            ])) {
                throw new RuntimeException('Nie udalo sie powiazac konta ze sklepem.');
            }
        }
    }

    // Minimalne uprawnienia do importu produktów
    $permissions = [
        'categories' => ['GET' => 1, 'POST' => 1],
        'products' => ['GET' => 1, 'POST' => 1],
        'images' => ['GET' => 1, 'POST' => 1],
        'stock_availables' => ['GET' => 1, 'PATCH' => 1],
    ];

    if (!$db->delete(
        'webservice_permission',
        'id_webservice_account = ' . $accountId
    )) {
        throw new RuntimeException('Nie udalo sie usunac starych uprawnien.');
    }

    WebserviceKey::setPermissionForAccount($accountId, $permissions);

    echo "OK: Webservice i uprawnienia skonfigurowane.\n";

} catch (Throwable $e) {
    $message = str_replace($key, '[UKRYTY_KLUCZ]', $e->getMessage());
    fwrite(STDERR, "BLAD: " . $message . "\n");
    exit(1);
}