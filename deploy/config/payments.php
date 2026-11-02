<?php

require_once '/var/www/html/config/config.inc.php';

$moduleName = 'ps_checkpayment';

if (Module::isEnabled($moduleName)) {
    $module = Module::getInstanceByName($moduleName);

    if (!$module || !$module->disable()) {
        throw new RuntimeException('Nie udalo sie wylaczyc platnosci czekiem');
    }
}

echo "Platnosc czekiem: OK\n";

//fikcyjne dane
$settings = [
    'BANK_WIRE_OWNER' => 'Sklep Test Sp. z o.o.',
    'BANK_WIRE_DETAILS' => 'Bank Test, nr konta PL00 0000 0000 0000 0000 0000 0000',
    'BANK_WIRE_ADDRESS' => 'ul. Test 1, 00-001 Warszawa',
    'PS_INVOICE' => '1',
];

foreach ($settings as $key => $value) {
    if ((string) Configuration::get($key) === $value) {
        continue;
    }

    if (!Configuration::updateValue($key, $value)) {
        throw new RuntimeException("Nie udalo sie ustawic $key");
    }
}

echo "Dane konta i faktury: OK\n";

$codState = new OrderState((int) Configuration::get('PS_OS_COD_VALIDATION'));

if (!Validate::isLoadedObject($codState)) {
    throw new RuntimeException('Nie znaleziono statusu platnosci przy odbiorze');
}

if (!$codState->invoice) {
    $codState->invoice = true;

    if (!$codState->update()) {
        throw new RuntimeException('Nie udalo sie wlaczyc faktury dla platnosci przy odbiorze');
    }
}

echo "Faktura przy platnosci przy odbiorze: OK\n";