import { test, expect } from '@playwright/test';
import { expectCartContents, openCart, removeProductFromCart } from '../pages/cart';
import { prepareCartWithTenProducts, searchAndAddNewProduct } from '../pages/shopping';
import { registerNewUser } from '../pages/registration';

test('koszyk i rejestracja klienta', async ({ page }) => {
  test.setTimeout(150_000);

  const cart = await test.step('1. Dodanie do koszyka 10 produktów', () => prepareCartWithTenProducts(page));

  await test.step('2. Wyszukanie produktu po nazwie i dodanie do koszyka losowego', async () => {
    const { id, quantity } = await searchAndAddNewProduct(page, cart);
    cart.set(id, quantity);
    expect(cart.size).toBe(11);
    await openCart(page);
    await expectCartContents(page, cart);
  });

  await test.step('3. Usunięcie z koszyka 3 produktów', async () => {
    const total = page.locator('.cart-summary-totals .cart-total .value').last();
    await expect(total).toHaveText(/\d/);
    const totalBefore = await total.innerText();

    for (const id of [...cart.keys()].slice(0, 3)) {
      await removeProductFromCart(page, id);
      cart.delete(id);
    }

    expect(cart.size).toBe(8);
    await expectCartContents(page, cart);
    await expect(total, 'Łączna cena po usunięciu produktów').not.toHaveText(totalBefore);
    await expect(total).toHaveText(/\d/);
  });

  await test.step('4. Rejestracja nowego konta', async () => {
    await registerNewUser(page);
    await openCart(page);
    await expectCartContents(page, cart);
  });
});
