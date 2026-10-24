<?php

require_once '/var/www/html/config/config.inc.php';

$moduleName = 'ps_checkpayment';

if (!Module::isEnabled($moduleName)) {
    echo "Platnosc czekiem: juz wylaczona\n";
    exit(0);
}

$module = Module::getInstanceByName($moduleName);

if (!$module || !$module->disable()) {
    throw new RuntimeException('Nie udalo sie wylaczyc platnosci czekiem');
}

echo "Platnosc czekiem: wylaczono\n";