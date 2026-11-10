import { expect, test, type Page } from '@playwright/test';

export async function addProductToCart(page: Page, productUrl: string) {
  await page.goto(productUrl, { waitUntil: 'domcontentloaded' });

  const details = page.locator('#product-details');
  await expect(details).toHaveAttribute('data-product', /.+/);
  const product = JSON.parse(await details.getAttribute('data-product') ?? '') as {
    quantity: number;
    minimal_quantity: string;
    customization_required: boolean;
  };

  const minQuantity = Math.max(1, Number(product.minimal_quantity));
  const maxQuantity = Math.min(3, product.quantity);
  if (maxQuantity < minQuantity || product.customization_required) return;

  const form = page.locator('#add-to-cart-or-refresh');
  const addButton = form.getByRole('button', { name: /Dodaj do koszyka/i });
  if (!(await addButton.isVisible()) || !(await addButton.isEnabled())) return;

  const quantity = minQuantity + Math.floor(Math.random() * (maxQuantity - minQuantity + 1));
  const name = await page.getByRole('heading', { level: 1 }).innerText();

  await test.step(`Dodaj ${name} (${quantity} szt.)`, async () => {
    const quantityInput = form.getByRole('spinbutton', { name: 'Ilość' });
    await quantityInput.fill(String(quantity));
    await expect(quantityInput).toHaveValue(String(quantity));
    await addButton.click();

    const confirmation = page.locator('#blockcart-modal');
    const continueShopping = confirmation.getByRole('button', { name: 'Kontynuuj zakupy' });
    await expect(continueShopping).toBeVisible();
    await continueShopping.click();
    await expect(confirmation).toBeHidden();
  });

  return quantity;
}

export async function openCart(page: Page) {
  await page.locator('#_desktop_cart').getByRole('link', { name: /Koszyk/i }).click();
}

export async function removeProductFromCart(page: Page, productId: string) {
  await test.step(`Usuń pozycję produktu o ID ${productId}`, async () => {
    const removeLink = page.locator('.cart-overview').locator(
      `[data-link-action="delete-from-cart"][data-id-product="${productId}"]`,
    );
    await removeLink.click();
    await expect(removeLink).toHaveCount(0);
  });
}

export async function expectCartContents(page: Page, expectedProducts: ReadonlyMap<string, number>) {
  const cart = page.locator('.cart-overview');
  await expect(cart).toBeVisible();

  const rows = cart.locator('.cart-items > .cart-item');
  await expect(rows).toHaveCount(expectedProducts.size);
  for (const [id, quantity] of expectedProducts) {
    const quantityInput = rows.locator(`input[name="product-quantity-spin"][data-product-id="${id}"]`);
    await expect(quantityInput, `Ilość produktu o ID ${id}`).toHaveValue(String(quantity));
  }
}
