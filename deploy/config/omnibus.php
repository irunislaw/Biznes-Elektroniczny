<?php

require_once '/var/www/html/config/config.inc.php';

$moduleName = 'beomnibus';

// W CLI aktualizacja tłumaczeń po instalacji kończy się błędem (brak kontenera Symfony).
Module::updateTranslationsAfterInstall(false);

$module = Module::getInstanceByName($moduleName);

if (!$module) {
    throw new RuntimeException("Nie znaleziono modulu $moduleName w katalogu modules");
}

if (!Module::isInstalled($moduleName)) {
    // Instalacja tworzy tabelę, podpina hooki i zapisuje obecną cenę każdego produktu jako początek historii cen.
    // Drugiego registerHook w tym samym procesie nie robimy: PrestaShop 8.2 nie czyści cache id hooków z aliasami
    // po utworzeniu nowego hooka, więc nie widzi świeżego podpięcia i wstawia je jeszcze raz (Duplicate entry).
    if (!$module->install()) {
        throw new RuntimeException("Nie udalo sie zainstalowac modulu $moduleName: " . implode('; ', $module->getErrors()));
    }
} else {
    if (!Module::isEnabled($moduleName) && !$module->enable()) {
        throw new RuntimeException("Nie udalo sie wlaczyc modulu $moduleName");
    }
    // Moduł już był: dopina hooki i tabelę dodane w nowszej wersji kodu
    if (!$module->createTable() || !$module->registerHook(BeOmnibus::HOOKS)) {
        throw new RuntimeException("Nie udalo sie przygotowac modulu $moduleName (tabela historii cen, hooki)");
    }
}

$rows = (int) Db::getInstance()->getValue('SELECT COUNT(*) FROM `' . _DB_PREFIX_ . BeOmnibus::TABLE . '`');
echo "Omnibus, najnizsza cena z 30 dni ($moduleName): OK, wpisow w historii cen: $rows\n";
