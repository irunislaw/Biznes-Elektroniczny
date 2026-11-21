import { test, expect } from '@playwright/test';
import { acceptCookies } from '../pages/shopping';

// Dyrektywa Omnibus (moduł beomnibus): przy obniżce sklep podaje najniższą cenę z 30 dni przed nią.
const LOWEST_PRICE = /Najniższa cena z 30 dni przed obniżką: \d[\d\s]*,\d{2}\s*zł/;

test('Omnibus: przy każdej promocji najniższa cena z 30 dni, bez promocji brak informacji', async ({ page }) => {
  await page.goto('/index.php?controller=prices-drop', { waitUntil: 'domcontentloaded' });
  await acceptCookies(page);

  const cards = page.locator('#js-product-list article[data-id-product]');
  const promoCards = cards.filter({ has: page.locator('.regular-price') });

  await test.step('Lista „Promocje”: każdy produkt z obniżką ma informację', async () => {
    await expect(promoCards.first()).toBeVisible();
    const count = await promoCards.count();
    for (let i = 0; i < count; i++) {
      await expect(promoCards.nth(i).locator('.beomnibus-lowest-price')).toHaveText(LOWEST_PRICE);
    }
  });

  await test.step('Karta produktu w promocji pokazuje informację pod ceną', async () => {
    await promoCards.first().locator('.product-title a').click();
    const prices = page.locator('.product-prices');
    await expect(prices.locator('.regular-price')).toBeVisible();
    await expect(prices.locator('.beomnibus-lowest-price')).toHaveText(LOWEST_PRICE);
  });

  await test.step('Produkt bez promocji nie ma informacji', async () => {
    await page.goto('/index.php?controller=category&id_category=2', { waitUntil: 'domcontentloaded' });
    const regularCard = cards.filter({ hasNot: page.locator('.regular-price') }).first();
    await expect(regularCard).toBeVisible();
    await expect(regularCard.locator('.beomnibus-lowest-price')).toHaveCount(0);

    await regularCard.locator('.product-title a').click();
    const prices = page.locator('.product-prices');
    await expect(prices).toBeVisible();
    await expect(prices.locator('.beomnibus-lowest-price')).toHaveCount(0);
  });
});
