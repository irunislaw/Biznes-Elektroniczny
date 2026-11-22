import { expect, test, type Page } from '@playwright/test';
import path from 'path';

// Zrzuty całych stron sklepu źródłowego i naszego, w tych samych miejscach, do porównania układu.
// Wynik: docs/wyglad/<sklep>/<szerokość>-<strona>.jpg, np. docs/wyglad/zrodlo/360-produkt.jpg.
//
// Obie strony to PrestaShop z motywem Classic, więc selektory są wspólne. ID kategorii i produktów
// po imporcie są inne niż w źródle, dlatego adresy są podane osobno dla każdego sklepu.
// Produkt: UKU-701S NT Ever Play z kategorii Ukulele > Sopranowe (dostępny, kilka zdjęć).

type Sklep = {
  katalog: string;
  adres: string;
  kategoria: string;
  produkt: string;
  zrzutZamowienia?: boolean;
};

const SKLEPY: Sklep[] = [
  {
    katalog: 'zrodlo',
    adres: 'https://gitara-sklep.pl',
    kategoria: '/340-sopranowe',
    produkt: '/sopranowe/1755-ukulele-sopranowe-uku-701s-nt-ever-play.html',
  },
  {
    katalog: 'nasz',
    adres: process.env.BASE_URL ?? 'https://localhost:8443',
    kategoria: '/11-sopranowe',
    produkt: '/sopranowe/21-ukulele-sopranowe-uku-701s-nt-ever-play.html',
    zrzutZamowienia: true,
  },
];

const KATALOG_WYNIKOW = path.resolve(__dirname, '..', '..', 'docs', 'wyglad');

for (const sklep of SKLEPY) {
  test(sklep.katalog, async ({ page, context }, testInfo) => {
    const szerokosc = testInfo.project.name;
    const zapisz = (strona: string) =>
      zrzut(page, path.join(KATALOG_WYNIKOW, sklep.katalog, `${szerokosc}-${strona}.jpg`));

    // Nasz baner cookies zasłaniałby dół strony, a w źródle go nie ma: zgoda jak po kliknięciu „Akceptuję”.
    await context.addCookies([{ name: 'be_cookie_consent', value: '1', url: sklep.adres }]);

    await test.step('Strona główna', async () => {
      await page.goto(sklep.adres + '/', { waitUntil: 'domcontentloaded' });
      await expect(page.locator('body')).toHaveAttribute('id', 'index');
      await zapisz('1-glowna');
    });

    await test.step('Kategoria', async () => {
      await page.goto(sklep.adres + sklep.kategoria, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('body')).toHaveAttribute('id', 'category');
      await expect(page.locator('.js-product-miniature').first()).toBeVisible();
      await zapisz('2-kategoria');
    });

    await test.step('Karta produktu', async () => {
      await page.goto(sklep.adres + sklep.produkt, { waitUntil: 'domcontentloaded' });
      await expect(page.locator('body')).toHaveAttribute('id', 'product');
      await zapisz('3-produkt');
    });

    await test.step('Koszyk', async () => {
      await dodajDoKoszyka(page, sklep);
      await page.goto(sklep.adres + '/index.php?controller=cart&action=show', { waitUntil: 'domcontentloaded' });
      await expect(page.locator('.cart-item').first()).toBeVisible();
      await zapisz('4-koszyk');
    });

    // Zrzut zamówienia jest wymagany dla naszego sklepu. Porównanie ze źródłem kończy się na koszyku.
    if (sklep.zrzutZamowienia) {
      await test.step('Zamówienie', async () => {
        const link = page.getByRole('link', { name: 'Przejdź do realizacji zamówienia', exact: true });
        await expect(link).toBeVisible();
        await link.click();
        await expect(page.locator('body')).toHaveAttribute('id', 'checkout');
        await expect(page.locator('#checkout-personal-information-step')).toBeVisible();
        await zapisz('5-zamowienie');
      });
    }
  });
}

// Dodaje produkt z karty. Gdy w sklepie zabraknie go na stanie (przycisk wyłączony),
// bierze pierwszy dostępny produkt z tej samej kategorii.
async function dodajDoKoszyka(page: Page, sklep: Sklep) {
  const kandydaci = [sklep.adres + sklep.produkt];
  for (let i = 0; i < 6; i++) {
    if (i === 1) {
      await page.goto(sklep.adres + sklep.kategoria, { waitUntil: 'domcontentloaded' });
      kandydaci.push(...await page.locator('.js-product-miniature .product-title a')
        .evaluateAll(linki => linki.map(link => (link as HTMLAnchorElement).href)));
    }
    if (i >= kandydaci.length) break;

    await page.goto(kandydaci[i], { waitUntil: 'domcontentloaded' });
    const przycisk = page.locator('#add-to-cart-or-refresh [data-button-action="add-to-cart"]');
    if (await przycisk.isEnabled()) {
      await przycisk.click();
      await expect(page.locator('#blockcart-modal')).toBeVisible();
      return;
    }
  }
  throw new Error(`Nie znaleziono dostępnego produktu do koszyka w ${sklep.adres}${sklep.kategoria}`);
}

async function zrzut(page: Page, plik: string) {
  await page.waitForLoadState('load');
  // Przewinięcie do końca ładuje obrazki z loading="lazy", potem powrót na górę strony.
  await page.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 400) {
      window.scrollTo(0, y);
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    window.scrollTo(0, 0);
  });
  await page.waitForFunction(() => Array.from(document.images).every(img => img.complete), undefined, { timeout: 15_000 })
    .catch(() => console.warn(`Nie wszystkie obrazki się wczytały: ${page.url()}`));
  // Slider i animacje zatrzymane, żeby kolejne uruchomienia dawały ten sam obraz.
  await page.screenshot({ path: plik, fullPage: true, type: 'jpeg', quality: 80, animations: 'disabled' });
}
