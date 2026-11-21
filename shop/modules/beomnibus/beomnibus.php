<?php

if (!defined('_PS_VERSION_')) {
    exit;
}

/**
 * Dyrektywa Omnibus: przy produkcie w promocji pokazuje najniższą cenę z 30 dni przed obniżką.
 *
 * Historia cen jest w tabeli beomnibus_price: cena końcowa brutto (z promocją) produktu i chwila, od której
 * obowiązuje. Pierwszy wpis powstaje przy instalacji modułu, kolejne przy zmianie produktu albo jego promocji
 * (także przez Web Service, np. przy imporcie), tylko gdy cena się zmieniła.
 */
class BeOmnibus extends Module
{
    public const HOOKS = [
        'actionFrontControllerSetMedia',
        'displayProductPriceBlock',
        'actionObjectProductAddAfter',
        'actionObjectProductUpdateAfter',
        'actionObjectProductDeleteAfter',
        'actionObjectSpecificPriceAddAfter',
        'actionObjectSpecificPriceUpdateAfter',
        'actionObjectSpecificPriceDeleteAfter',
    ];
    public const TABLE = 'beomnibus_price';
    public const DAYS = 30;
    // Miejsca w szablonach Classic: karta produktu (after_price) oraz listy produktów i koszyk (unit_price)
    private const PRICE_BLOCK_TYPES = ['after_price', 'unit_price'];

    public function __construct()
    {
        $this->name = 'beomnibus';
        $this->tab = 'pricing_promotion';
        $this->version = '1.0.0';
        $this->author = 'Zespol BE';
        $this->need_instance = 0;
        $this->ps_versions_compliancy = ['min' => '8.0.0', 'max' => _PS_VERSION_];

        parent::__construct();

        $this->displayName = 'Omnibus: najniższa cena z 30 dni';
        $this->description = 'Przy produkcie w promocji pokazuje najniższą cenę z 30 dni przed obniżką.';
    }

    public function install()
    {
        return parent::install()
            && $this->createTable()
            && $this->registerHook(self::HOOKS)
            && $this->recordAllPrices();
    }

    public function uninstall()
    {
        return parent::uninstall()
            && Db::getInstance()->execute('DROP TABLE IF EXISTS `' . _DB_PREFIX_ . self::TABLE . '`');
    }

    public function createTable(): bool
    {
        return Db::getInstance()->execute(
            'CREATE TABLE IF NOT EXISTS `' . _DB_PREFIX_ . self::TABLE . '` (
                `id_beomnibus_price` INT UNSIGNED NOT NULL AUTO_INCREMENT,
                `id_product` INT UNSIGNED NOT NULL,
                `price` DECIMAL(20,6) NOT NULL,
                `date_add` DATETIME NOT NULL,
                PRIMARY KEY (`id_beomnibus_price`),
                KEY `product_date` (`id_product`, `date_add`)
            ) ENGINE=' . _MYSQL_ENGINE_ . ' DEFAULT CHARSET=utf8mb4'
        );
    }

    /** Cena każdego produktu w chwili instalacji, czyli początek historii. */
    public function recordAllPrices(): bool
    {
        $products = Db::getInstance()->executeS('SELECT id_product FROM `' . _DB_PREFIX_ . 'product`');
        foreach ($products ?: [] as $row) {
            $this->recordPrice((int) $row['id_product']);
        }

        return true;
    }

    public function hookActionObjectProductAddAfter($params)
    {
        $this->recordPrice((int) $params['object']->id);
    }

    public function hookActionObjectProductUpdateAfter($params)
    {
        $this->recordPrice((int) $params['object']->id);
    }

    public function hookActionObjectProductDeleteAfter($params)
    {
        Db::getInstance()->delete(self::TABLE, 'id_product = ' . (int) $params['object']->id);
    }

    public function hookActionObjectSpecificPriceAddAfter($params)
    {
        $this->recordSpecificPrice($params['object']);
    }

    public function hookActionObjectSpecificPriceUpdateAfter($params)
    {
        $this->recordSpecificPrice($params['object']);
    }

    public function hookActionObjectSpecificPriceDeleteAfter($params)
    {
        $this->recordSpecificPrice($params['object']);
    }

    private function recordSpecificPrice(SpecificPrice $specificPrice): void
    {
        // Cena specyficzna z id_cart dotyczy jednego koszyka, a nie promocji widocznej w sklepie
        if ((int) $specificPrice->id_cart === 0) {
            $this->recordPrice((int) $specificPrice->id_product);
        }
    }

    /** Dopisuje obecną cenę końcową produktu, jeśli różni się od ostatniej zapisanej. */
    public function recordPrice(int $idProduct): void
    {
        if ($idProduct <= 0) {
            return;
        }

        $price = round($this->getCurrentPrice($idProduct), 2);

        $db = Db::getInstance();
        // getValue sam dopisuje LIMIT 1
        $last = $db->getValue(
            'SELECT price FROM `' . _DB_PREFIX_ . self::TABLE . '`
            WHERE id_product = ' . $idProduct . '
            ORDER BY date_add DESC, id_beomnibus_price DESC',
            false
        );
        if ($last !== false && abs((float) $last - $price) < 0.005) {
            return;
        }

        $db->insert(self::TABLE, ['id_product' => $idProduct, 'price' => $price, 'date_add' => date('Y-m-d H:i:s')]);
    }

    /** Cena końcowa brutto z promocją, jaką widzi klient bez konta (domyślny kraj, grupa i waluta). */
    private function getCurrentPrice(int $idProduct): float
    {
        // Ceny i promocje są zapamiętywane w obrębie żądania, a tu liczymy cenę zaraz po zmianie promocji
        SpecificPrice::flushCache();
        Product::flushPriceCache();

        // Bez koszyka i pracownika w kontekście (CLI, Web Service) getPriceStatic kończy skrypt przez die(),
        // więc liczymy na kopii kontekstu z pustym koszykiem
        $context = Context::getContext()->cloneContext();
        if (!is_object($context->cart)) {
            $context->cart = new Cart();
        }

        return (float) Product::getPriceStatic($idProduct, true, null, 6, context: $context);
    }

    /**
     * Najniższa cena z DAYS dni przed początkiem obecnej obniżki.
     *
     * Początek obniżki to najstarszy z ostatnich wpisów historii z obecną ceną. Pod uwagę idą ceny z okna
     * DAYS dni przed nim oraz cena, która obowiązywała na początku okna. Gdy sprzed obniżki nie ma żadnego
     * wpisu (produkt jest w promocji od początku historii), wynikiem jest cena regularna.
     */
    public function getLowestPriceBeforeDiscount(int $idProduct, float $currentPrice, float $regularPrice): float
    {
        $history = Db::getInstance(_PS_USE_SQL_SLAVE_)->executeS(
            'SELECT price, date_add FROM `' . _DB_PREFIX_ . self::TABLE . '`
            WHERE id_product = ' . $idProduct . '
            ORDER BY date_add, id_beomnibus_price'
        ) ?: [];

        $currentPrice = round($currentPrice, 2);
        $start = count($history);
        while ($start > 0 && abs((float) $history[$start - 1]['price'] - $currentPrice) < 0.005) {
            --$start;
        }
        $discountStart = $start < count($history) ? strtotime($history[$start]['date_add']) : time();
        $windowStart = $discountStart - self::DAYS * 86400;

        $prices = [];
        $priceAtWindowStart = null;
        foreach (array_slice($history, 0, $start) as $row) {
            if (strtotime($row['date_add']) >= $windowStart) {
                $prices[] = (float) $row['price'];
            } else {
                $priceAtWindowStart = (float) $row['price'];
            }
        }
        if ($priceAtWindowStart !== null) {
            $prices[] = $priceAtWindowStart;
        }

        return $prices ? min($prices) : $regularPrice;
    }

    public function hookActionFrontControllerSetMedia()
    {
        $this->context->controller->registerStylesheet(
            'module-beomnibus-style',
            'modules/' . $this->name . '/views/css/beomnibus.css',
            ['media' => 'all', 'priority' => 200]
        );
    }

    public function hookDisplayProductPriceBlock($params)
    {
        $product = $params['product'] ?? null;
        if (!in_array($params['type'] ?? '', self::PRICE_BLOCK_TYPES, true) || empty($product['has_discount'])) {
            return '';
        }

        $lowest = $this->getLowestPriceBeforeDiscount(
            (int) $product['id_product'],
            (float) $product['price_amount'],
            (float) $product['regular_price_amount']
        );
        $this->context->smarty->assign([
            'beomnibus_days' => self::DAYS,
            'beomnibus_price' => $this->context->getCurrentLocale()->formatPrice($lowest, $this->context->currency->iso_code),
        ]);

        return $this->fetch('module:' . $this->name . '/views/templates/hook/price.tpl');
    }
}
