<?php

require_once '/var/www/html/config/config.inc.php';

$moduleName = 'becookiebanner';

// W CLI aktualizacja tłumaczeń po instalacji kończy się błędem (brak kontenera Symfony).
Module::updateTranslationsAfterInstall(false);

$module = Module::getInstanceByName($moduleName);

if (!$module) {
    throw new RuntimeException("Nie znaleziono modulu $moduleName w katalogu modules");
}

if (!Module::isInstalled($moduleName)) {
    if (!$module->install()) {
        throw new RuntimeException("Nie udalo sie zainstalowac modulu $moduleName: " . implode('; ', $module->getErrors()));
    }
} elseif (!Module::isEnabled($moduleName) && !$module->enable()) {
    throw new RuntimeException("Nie udalo sie wlaczyc modulu $moduleName");
}

if (!$module->registerHook(BeCookieBanner::HOOKS)) {
    throw new RuntimeException("Nie udalo sie podpiac modulu $moduleName do hookow");
}

echo "Informacja o cookies ($moduleName): OK\n";
