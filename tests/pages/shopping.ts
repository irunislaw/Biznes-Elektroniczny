import { test, expect, type Page } from '@playwright/test';
import { addProductToCart, expectCartContents, openCart } from './cart';

export async function prepareCartWithTenProducts(page: Page) {
  const targetCount = 10;
  const maxPerCategory = 5;
  const addedProducts = new Map<string, number>();

  const categories = await test.step('Pobierz kategorie z katalogu', async () => {
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await page.getByRole('link', { name: /^Wszystkie produkty\s*?$/ }).click();

    const categoryLinks = page.locator('#left-column .category-sub-menu li > a');
    await expect(categoryLinks.first()).toBeVisible();
    const entries = await categoryLinks.evaluateAll(links => links.map(link => [
      (link as HTMLAnchorElement).href,
      link.textContent?.trim() ?? '',
    ] as const));
    return [...new Map(entries)];
  });

  while (categories.length > 0 && addedProducts.size < targetCount) {
    const index = Math.floor(Math.random() * categories.length);
    const [[categoryUrl, categoryName]] = categories.splice(index, 1);

    const limit = Math.min(maxPerCategory, targetCount - addedProducts.size);

    await test.step(`Kategoria: ${categoryName}`, () => addCategoryProducts(page, categoryUrl, addedProducts, limit));
  }

  await test.step('Sprawdź pozycje i ilości w koszyku', async () => {
    expect(addedProducts.size, 'Po sprawdzeniu kategorii zabrakło dostępnych produktów').toBe(targetCount);

    await openCart(page);
    await expectCartContents(page, addedProducts);
  });

  return addedProducts;
}

async function addCategoryProducts(page: Page, categoryUrl: string, cart: Map<string, number>, limit: number) {
  await page.goto(categoryUrl, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('body')).toHaveAttribute('id', 'category');

  const targetSize = cart.size + limit;
  for (const product of await readCatalogProducts(page)) {
    if (cart.size === targetSize) break;
    if (cart.has(product.id)) continue;

    const quantity = await addProductToCart(page, product.url);
    if (quantity !== undefined) cart.set(product.id, quantity);
  }
}

export async function searchAndAddNewProduct(page: Page, cart: ReadonlyMap<string, number>) {
  const searchTerm = 'Hummingbird';
  const searchBar = page.getByRole('textbox', { name: 'Szukaj' });
  await searchBar.fill(searchTerm);
  await Promise.all([
    page.waitForURL(/controller=search/, { waitUntil: 'domcontentloaded' }),
    searchBar.press('Enter'),
  ]);

  const results = await readCatalogProducts(page);
  while (results.length > 0) {
    const index = Math.floor(Math.random() * results.length);
    const [product] = results.splice(index, 1);
    if (cart.has(product.id)) continue;

    const quantity = await addProductToCart(page, product.url);
    if (quantity !== undefined) return { id: product.id, quantity };
  }

  throw new Error(`Brak dostępnego produktu spoza koszyka w wynikach dla „${searchTerm}”`);
}

async function readCatalogProducts(page: Page) {
  return page.locator('#js-product-list article[data-id-product]').evaluateAll(cards =>
    cards.flatMap(card => {
      const id = card.getAttribute('data-id-product');
      const link = card.querySelector<HTMLAnchorElement>('.product-title a');
      return id && link ? [{ id, url: link.href }] : [];
    }),
  );
}
