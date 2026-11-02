import { test, expect, ConsoleMessage } from '@playwright/test';

test('search product by name and add to cart', async({page}) => {
    await page.goto('/');

    //searching
    await page.getByRole('textbox', { name: 'Szukaj' }).click();
    await page.getByRole('textbox', { name: 'Szukaj' }).fill('frame');
    await page.getByRole('textbox', { name: 'Szukaj' }).press('Enter');

    //choosing random product
    const products =  page.locator('.product');
    const products_count = await products.count();
    expect(products_count).toBeGreaterThan(0);
    
    const chosen_product = products.nth(Math.floor(Math.random() * products_count));

    //getting product name
    const product_name = await chosen_product.locator('.product-title').textContent();
    const product_name_clean = product_name?.replace(/\.{3}/g, '').trim();

    //adding to cart
    await chosen_product.getByRole('link').first().click();
    await page.getByRole('button', { name: 'Dodaj do koszyka' }).click();

    //checking if its in cart
    await page.getByRole('link', { name: 'Przejdź do realizacji' }).click();
    await expect(page.getByRole('link', { name: product_name_clean})).toBeVisible();
});

test('register new user', async ({ page }) => {
  const name = 'Klient';
  const surname = 'Testowy';
  const full_name = `${name} ${surname}`;
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
  await expect(page.getByRole('link', { name: full_name })).toBeVisible();
});