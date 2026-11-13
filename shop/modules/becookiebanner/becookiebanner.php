<?php

if (!defined('_PS_VERSION_')) {
    exit;
}

class BeCookieBanner extends Module
{
    private const COOKIE_NAME = 'be_cookie_consent';
    private const PRIVACY_LINK_REWRITE = 'polityka-prywatnosci';
    public const HOOKS = ['actionFrontControllerSetMedia', 'displayBeforeBodyClosingTag'];

    public function __construct()
    {
        $this->name = 'becookiebanner';
        $this->tab = 'front_office_features';
        $this->version = '1.0.0';
        $this->author = 'Zespol BE';
        $this->need_instance = 0;
        $this->ps_versions_compliancy = ['min' => '8.0.0', 'max' => _PS_VERSION_];

        parent::__construct();

        $this->displayName = 'Informacja o plikach cookies';
        $this->description = 'Pasek z informacją o plikach cookies i linkiem do Polityki prywatności.';
    }

    public function install()
    {
        return parent::install() && $this->registerHook(self::HOOKS);
    }

    public function hookActionFrontControllerSetMedia()
    {
        if ($this->isAccepted()) {
            return;
        }

        $this->context->controller->registerStylesheet(
            'module-becookiebanner-style',
            'modules/' . $this->name . '/views/css/becookiebanner.css',
            ['media' => 'all', 'priority' => 200]
        );
        $this->context->controller->registerJavascript(
            'module-becookiebanner-script',
            'modules/' . $this->name . '/views/js/becookiebanner.js',
            ['position' => 'bottom', 'priority' => 200]
        );
    }

    public function hookDisplayBeforeBodyClosingTag()
    {
        // Bez cache Smarty: ciasteczko sprawdzane przy każdym żądaniu.
        if ($this->isAccepted()) {
            return '';
        }

        $this->context->smarty->assign('becookiebanner_privacy_url', $this->getPrivacyPolicyUrl());

        return $this->fetch('module:' . $this->name . '/views/templates/hook/banner.tpl');
    }

    private function isAccepted(): bool
    {
        return ($_COOKIE[self::COOKIE_NAME] ?? '') === '1';
    }

    private function getPrivacyPolicyUrl(): string
    {
        $query = new DbQuery();
        $query->select('c.id_cms')
            ->from('cms', 'c')
            ->innerJoin(
                'cms_lang',
                'cl',
                'cl.id_cms = c.id_cms'
                . ' AND cl.id_lang = ' . (int) $this->context->language->id
                . ' AND cl.id_shop = ' . (int) $this->context->shop->id
            )
            ->where('c.active = 1')
            ->where("cl.link_rewrite = '" . pSQL(self::PRIVACY_LINK_REWRITE) . "'");

        $idCms = (int) Db::getInstance(_PS_USE_SQL_SLAVE_)->getValue($query);

        return $idCms > 0 ? $this->context->link->getCMSLink($idCms) : '';
    }
}
