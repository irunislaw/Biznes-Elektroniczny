<?php

require_once '/var/www/html/config/config.inc.php';


const FREE_SHIPPING_ABOVE = 2000;
const MAX_WEIGHT = 50;
const WEIGHT_RANGE_TO = 1000;
const VAT_RATE = 23;
const TAX_RULES_GROUP = 'PL Standard Rate (23%)';
const PAYMENT_MODULES = ['ps_wirepayment', 'ps_cashondelivery'];

$carriers = [
    ['name' => 'Kurier', 'delay' => 'Dostawa w 2-3 dni robocze', 'fee_gross' => 14.99],
    ['name' => 'Kurier ekspres', 'delay' => 'Dostawa w 24 godziny', 'fee_gross' => 24.99],
];

$db = Db::getInstance();

$languageIds = Language::getIDs(false);
$groups = Group::getGroups((int) Configuration::get('PS_LANG_DEFAULT'));
$groupIds = array_column($groups, 'id_group');
$zoneId = (int) Country::getIdZone((int) Country::getByIso('PL'));
$taxRulesGroupId = TaxRulesGroup::getIdByName(TAX_RULES_GROUP);

if ($zoneId <= 0) {
    throw new RuntimeException('Nie znaleziono strefy dla Polski');
}

if ($taxRulesGroupId <= 0) {
    throw new RuntimeException('Nie znaleziono grupy podatkowej ' . TAX_RULES_GROUP);
}

$carrierIds = [];
$carrierReferences = [];

foreach ($carriers as $data) {
    $carrierId = (int) $db->getValue(
        'SELECT id_carrier FROM `' . _DB_PREFIX_ . 'carrier`'
        . " WHERE name = '" . pSQL($data['name']) . "' AND deleted = 0"
    );

    $carrier = new Carrier($carrierId);
    $carrier->name = $data['name'];

    $fields = [
        'active' => 1,
        'is_free' => 0,
        'shipping_handling' => 0,
        'shipping_method' => Carrier::SHIPPING_METHOD_WEIGHT,
        'range_behavior' => 1,
        'max_weight' => MAX_WEIGHT,
    ];

    $changed = false;

    foreach ($fields as $field => $value) {
        if ((float) $carrier->$field !== (float) $value) {
            $carrier->$field = $value;
            $changed = true;
        }
    }

    $delay = array_fill_keys($languageIds, $data['delay']);

    if ($carrier->delay != $delay) {
        $carrier->delay = $delay;
        $changed = true;
    }

    if (!$carrier->id) {
        if (!$carrier->add()) {
            throw new RuntimeException("Nie udalo sie dodac przewoznika {$data['name']}");
        }

        $carrier = new Carrier((int) $carrier->id);
    } elseif ($changed && !$carrier->update()) {
        throw new RuntimeException("Nie udalo sie zaktualizowac przewoznika {$data['name']}");
    }

    if (!$carrier->getZone($zoneId) && !$carrier->addZone($zoneId)) {
        throw new RuntimeException("Nie udalo sie dodac strefy dla {$data['name']}");
    }

    $missingGroups = array_diff($groupIds, array_column($carrier->getGroups(), 'id_group'));

    if ($missingGroups && !$carrier->setGroups($missingGroups, false)) {
        throw new RuntimeException("Nie udalo sie dodac grup klientow dla {$data['name']}");
    }

    if (
        (int) $carrier->getIdTaxRulesGroup() !== $taxRulesGroupId
        && !$carrier->setTaxRulesGroup($taxRulesGroupId, true)
    ) {
        throw new RuntimeException("Nie udalo sie ustawic podatku dla {$data['name']}");
    }

    $rangeId = (int) $db->getValue(
        'SELECT id_range_weight FROM `' . _DB_PREFIX_ . 'range_weight`'
        . ' WHERE id_carrier = ' . (int) $carrier->id
        . ' AND delimiter1 = 0 AND delimiter2 = ' . WEIGHT_RANGE_TO
    );

    if (!$rangeId) {
        $range = new RangeWeight();
        $range->id_carrier = (int) $carrier->id;
        $range->delimiter1 = 0;
        $range->delimiter2 = WEIGHT_RANGE_TO;

        if (!$range->add()) {
            throw new RuntimeException("Nie udalo sie dodac zakresu wagi dla {$data['name']}");
        }

        $rangeId = (int) $range->id;
    }

    $feeNet = round($data['fee_gross'] / (1 + VAT_RATE / 100), 6);
    $where = 'id_carrier = ' . (int) $carrier->id
        . ' AND id_range_weight = ' . $rangeId
        . ' AND id_zone = ' . $zoneId;

    $currentFee = $db->getValue('SELECT price FROM `' . _DB_PREFIX_ . 'delivery` WHERE ' . $where);

    if ($currentFee === false) {
        throw new RuntimeException("Brak wiersza oplaty dla {$data['name']}");
    }

    if (
        abs((float) $currentFee - $feeNet) > 0.000001
        && !$db->update('delivery', ['price' => $feeNet], $where)
    ) {
        throw new RuntimeException("Nie udalo sie ustawic oplaty dla {$data['name']}");
    }

    $carrierIds[] = (int) $carrier->id;
    $carrierReferences[] = (int) $carrier->id_reference;
}

if (!$db->update(
    'carrier',
    ['active' => 0],
    'active = 1 AND deleted = 0 AND id_carrier NOT IN (' . implode(',', $carrierIds) . ')'
)) {
    throw new RuntimeException('Nie udalo sie wylaczyc pozostalych przewoznikow');
}

 // prestashop liczy prog >=, a darmowa dostawa ma byc powyzej 2000 zl
$settings = [
    'PS_SHIPPING_FREE_PRICE' => number_format(FREE_SHIPPING_ABOVE + 0.01, 2, '.', ''),
    'PS_CARRIER_DEFAULT' => (string) $carrierIds[0],
];

foreach ($settings as $key => $value) {
    if ((string) Configuration::get($key) === $value) {
        continue;
    }

    if (!Configuration::updateValue($key, $value)) {
        throw new RuntimeException("Nie udalo sie ustawic $key");
    }
}

$shopIds = Shop::getShops(true, null, true);

foreach (PAYMENT_MODULES as $moduleName) {
    $moduleId = (int) Module::getModuleIdByName($moduleName);

    if ($moduleId <= 0) {
        throw new RuntimeException("Nie znaleziono modulu $moduleName");
    }

    if (!$db->delete(
        'module_carrier',
        'id_module = ' . $moduleId
        . ' AND id_reference NOT IN (' . implode(',', $carrierReferences) . ')'
    )) {
        throw new RuntimeException("Nie udalo sie usunac starych przewoznikow z $moduleName");
    }

    foreach ($shopIds as $shopId) {
        foreach ($carrierReferences as $carrierReference) {
            if (!$db->insert(
                'module_carrier',
                [
                    'id_module' => $moduleId,
                    'id_shop' => (int) $shopId,
                    'id_reference' => $carrierReference,
                ],
                false,
                true,
                Db::INSERT_IGNORE
            )) {
                throw new RuntimeException("Nie udalo sie przypisac przewoznika do $moduleName");
            }
        }
    }
}

echo "Przewoznicy i dostawa: OK\n";