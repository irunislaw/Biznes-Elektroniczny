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