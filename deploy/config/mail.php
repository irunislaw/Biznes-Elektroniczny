<?php

require_once '/var/www/html/config/config.inc.php';

$settings = [
    'PS_MAIL_METHOD' => '2',
    'PS_MAIL_SERVER' => 'mailpit',
    'PS_MAIL_SMTP_PORT' => '1025',
    'PS_MAIL_SMTP_ENCRYPTION' => 'off',
    'PS_MAIL_USER' => '',
    'PS_MAIL_PASSWD' => '',
];

foreach ($settings as $key => $value) {
    if ((string) Configuration::get($key) === $value) {
        continue;
    }

    if (!Configuration::updateValue($key, $value)) {
        throw new RuntimeException("Nie udalo sie ustawic $key");
    }
}

echo "SMTP (Mailpit): OK\n";