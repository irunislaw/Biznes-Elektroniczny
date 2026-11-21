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
    // Instalacja zapisuje obecną cenę każdego produktu jako początek historii cen
    if (!$module->install()) {
        throw new RuntimeException("Nie udalo sie zainstalowac modulu $moduleName: " . implode('; ', $module->getErrors()));
    }
} elseif (!Module::isEnabled($moduleName) && !$module->enable()) {
    throw new RuntimeException("Nie udalo sie wlaczyc modulu $moduleName");
}

if (!$module->createTable() || !$module->registerHook(BeOmnibus::HOOKS)) {
    throw new RuntimeException("Nie udalo sie przygotowac modulu $moduleName (tabela historii cen, hooki)");
}

$rows = (int) Db::getInstance()->getValue('SELECT COUNT(*) FROM `' . _DB_PREFIX_ . BeOmnibus::TABLE . '`');
echo "Omnibus, najnizsza cena z 30 dni ($moduleName): OK, wpisow w historii cen: $rows\n";
