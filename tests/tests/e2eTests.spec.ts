import { test, expect } from '@playwright/test';
import { addProductToCart, expectCartContents, openCart } from '../pages/cart';

test('search product by name and add to cart', async({page}) => {
    await page.goto('/');

    //searching
    const searchBar = page.getByRole('textbox', { name: 'Szukaj' })
    await searchBar.fill('frame');

    await Promise.all([
      page.waitForURL(/controller=search/),
      searchBar.press('Enter')
    ]);

    //choosing random product
    const products = page.locator('.product');
    const productsCount = await products.count();
    expect(productsCount).toBeGreaterThan(0);
    
    const chosenProduct = products.nth(Math.floor(Math.random() * productsCount));

    //getting product name
    const productName = await chosenProduct.locator('.product-title').textContent();
    const productNameClean = productName?.replace(/\.{3}/g, '').trim();

    //adding to cart
    await chosenProduct.getByRole('link').first().click();
    await page.getByRole('button', { name: 'Dodaj do koszyka' }).click();

    //checking if its in cart
    await page.getByRole('link', { name: 'Przejdź do realizacji' }).click();
    await expect(page.getByRole('link', { name: productNameClean})).toBeVisible();
});

test('register new user', async ({ page }) => {
  const name = 'Klient';
  const surname = 'Testowy';
  const fullName = `${name} ${surname}`;
  const email = `${name}.${surname}+${Date.now()}@test-email.com`;

  await page.goto('/');

  await page.locator('header').getByRole('link', { name: 'Zaloguj się' }).click();
  await page.getByRole('link', { name: 'Nie masz konta? Załóż je tutaj' }).click();

  //client data
  await page.getByRole('radio', { name: 'Pan', exact: true }).check();
  await page.getByRole('textbox', { name: 'Imię' }).fill(name);
  await page.getByRole('textbox', { name: 'Nazwisko' }).fill(surname);
  await page.getByRole('textbox', { name: 'E-mail' }).fill(email);
  await page.getByRole('textbox', { name: 'Pole wprowadzania hasła' }).fill('Haslo Klienta Do Testow');

  //permissions
  await page.getByRole('checkbox', { name: 'Akceptuję ogólne warunki' }).check();
  await page.getByRole('checkbox', { name: 'Wiadomość o przetwarzaniu' }).check();


  await page.getByRole('button', { name: 'Zapisz' }).click();
  await expect(page.getByRole('link', { name: fullName })).toBeVisible();
});

test('add 10 products', async ({ page }) => {
  test.setTimeout(120_000);
  const targetCount = 10;
  const maxPerCategory = 5;
  const addedProducts = new Map<string, number>();

  const categories = await test.step('Pobierz kategorie z katalogu', async () => {
    await page.goto('/');
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

    await test.step(`Kategoria: ${categoryName}`, async () => {
      let remainingInCategory = Math.min(maxPerCategory, targetCount - addedProducts.size);
      await page.goto(categoryUrl);
      await expect(page.locator('body')).toHaveAttribute('id', 'category');

      const products = await page.locator('#js-product-list article[data-id-product]').evaluateAll(cards =>
        cards.flatMap(card => {
          const id = card.getAttribute('data-id-product');
          const link = card.querySelector<HTMLAnchorElement>('.product-title a');
          return id && link ? [{ id, url: link.href }] : [];
        }),
      );

      for (const product of products) {
        if (remainingInCategory === 0) break;
        if (addedProducts.has(product.id)) continue;

        const quantity = await addProductToCart(page, product.url);
        if (quantity === undefined) continue;

        addedProducts.set(product.id, quantity);
        remainingInCategory--;
      }
    });
  }

  await test.step('Sprawdź pozycje i ilości w koszyku', async () => {
    expect(addedProducts.size, 'Po sprawdzeniu kategorii zabrakło dostępnych produktów').toBe(targetCount);

    await openCart(page);
    await expectCartContents(page, addedProducts);
  });
});

test('remove 3 products', async ({page}) => {});
