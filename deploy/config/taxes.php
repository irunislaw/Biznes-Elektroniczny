<?php

require_once '/var/www/html/config/config.inc.php';


if ((int) Configuration::get('PS_TAX') !== 1) {
    if (!Configuration::updateValue('PS_TAX', 1)) {
        throw new RuntimeException('Nie udalo sie wlaczyc podatkow');
    }

    echo "Naliczanie VAT: wlaczono\n";
} else {
    echo "Naliczanie VAT: juz wlaczone\n";
}


$requiredRates = [23, 8, 5, 0];

$languageId = (int) Language::getIdByIso('pl');
$taxes = Tax::getTaxes($languageId);

foreach ($requiredRates as $rate) {
    $found = false;

    foreach ($taxes as $tax) {
        if (abs((float) $tax['rate'] - $rate) < 0.001) {
            $found = true;
            break;
        }
    }

    if (!$found) {
        throw new RuntimeException("Brak aktywnej stawki VAT $rate%");
    }

    echo "VAT $rate%: istnieje\n";
}


$countryId = (int) Country::getByIso('PL');

if ($countryId <= 0) {
    throw new RuntimeException('Nie znaleziono kraju Polska');
}

$requiredGroups = [
    23 => 'PL Standard Rate (23%)',
    8 => 'PL Reduced Rate (8%)',
    5 => 'PL Reduced Rate (5%)',
    0 => 'PL Exempted Rate (0%)',
];

$groups = TaxRulesGroup::getTaxRulesGroups();

foreach ($requiredGroups as $rate => $groupName) {
    $found = false;

    foreach ($groups as $group) {
        if ($group['name'] !== $groupName) {
            continue;
        }

        $rules = TaxRule::getTaxRulesByGroupId(
            $languageId,
            (int) $group['id_tax_rules_group']
        );

        foreach ($rules as $rule) {
            if (
                (int) $rule['id_country'] === $countryId
                && (int) $rule['id_state'] === 0
                && abs((float) $rule['rate'] - $rate) < 0.001
            ) {
                $found = true;
                break;
            }
        }
    }

    if (!$found) {
        throw new RuntimeException(
            "Brak reguly VAT $rate% dla Polski"
        );
    }

    echo "Regula VAT $rate% dla Polski: istnieje\n";
}
