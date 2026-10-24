<?php

require_once '/var/www/html/config/config.inc.php';

$settings = [
    'PS_LANG_DEFAULT' => Language::getIdByIso('pl'),
    'PS_COUNTRY_DEFAULT' => Country::getByIso('PL'),
    'PS_CURRENCY_DEFAULT' => Currency::getIdByIsoCode('PLN'),
];

foreach ($settings as $key => $id) {
    $id = (int) $id;

    if ($id <= 0) {
        throw new RuntimeException("Nie znaleziono wymaganej wartosci dla $key");
    }

    if ((int) Configuration::get($key) === $id) {
        echo "$key: juz skonfigurowano\n";
        continue;
    }

    if (!Configuration::updateValue($key, $id)) {
        throw new RuntimeException("Nie udalo sie ustawic $key");
    }

    echo "$key: ustawiono ID $id\n";
}