import { test, expect } from '@playwright/test';
import { expectCartContents, openCart, removeProductFromCart } from '../pages/cart';
import { chooseRandomCarrier, confirmOrder, proceedToDelivery, selectCashOnDelivery } from '../pages/checkout';
import { checkOrderInHistory, downloadOrderInvoice } from '../pages/order-history';
import { acceptCookies, prepareCartWithTenProducts, searchAndAddNewProduct } from '../pages/shopping';
import { registerNewUser } from '../pages/registration';

test('zakup z płatnością przy odbiorze, sprawdzenie statusu zamówienia i pobranie faktury VAT', async ({ page }) => {
  test.setTimeout(90_000);

  await page.goto('/', { waitUntil: 'domcontentloaded' });

  await test.step('0. Zaakceptowanie ciasteczek', () => acceptCookies(page));

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

  const customerName = await test.step('4. Rejestracja nowego konta', async () => {
    const name = await registerNewUser(page);
    await openCart(page);
    await expectCartContents(page, cart);
    return name;
  });

  await test.step('5. Złożenie zamówienia na zawartość koszyka.', () => proceedToDelivery(page));

  await test.step('7. Wybór sposobu dostawy.', () => chooseRandomCarrier(page));

  await test.step('6. Wybór płatności przy odbiorze.', () => selectCashOnDelivery(page));

  const orderNumber = await test.step('8. Zatwierdzenie zamówienia.', () => confirmOrder(page));

  await test.step('9. Sprawdzenie zamówienia w historii.', () =>
    checkOrderInHistory(page, customerName, orderNumber),
  );

  await test.step('10. Pobranie faktury VAT.', () => downloadOrderInvoice(page, orderNumber));
});
