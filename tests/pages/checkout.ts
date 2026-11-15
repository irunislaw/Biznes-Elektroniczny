import { expect, test, type Page } from '@playwright/test';

export async function proceedToDelivery(page: Page) {
  const address = 'ul. Testowa 15'
  const zipCode = '00-001'
  const city = 'Gdańsk'

  await page.getByRole('link', { name: 'Przejdź do realizacji zamówienia' }).click();

  const addressForm = page.locator('#checkout-addresses-step form');
  await addressForm.getByRole('combobox', { name: 'Kraj' }).selectOption({ label: 'Polska' });
  await expect(addressForm.getByRole('combobox', { name: 'Stan' })).toBeHidden();
  await addressForm.getByRole('textbox', { name: 'Adres', exact: true }).fill(address);
  await addressForm.getByRole('textbox', { name: 'Kod pocztowy' }).fill(zipCode);
  await addressForm.getByRole('textbox', { name: 'Miasto' }).fill(city);
  await addressForm.getByRole('button', { name: 'Dalej', exact: true }).click();

  const deliveryForm = page.locator('#checkout-delivery-step form');
  await expect(addressForm).toBeHidden();
  await expect(deliveryForm).toBeVisible();
}

export async function chooseRandomCarrier(page: Page) {
  const deliveryForm = page.locator('#checkout-delivery-step form');
  const carrierNames = ['Kurier', 'Kurier ekspres'];
  const carrierName = carrierNames[Math.floor(Math.random() * carrierNames.length)];

  await test.step(`Wybierz przewoźnika: ${carrierName}`, async () => {
    const deliveryOption = deliveryForm.locator('.delivery-option').filter({
      has: page.getByText(carrierName, { exact: true }),
    });
    const carrier = deliveryOption.getByRole('radio');
    await carrier.check();
    await expect(carrier).toBeChecked();

    const carrierPrice = (await deliveryOption.locator('.carrier-price').innerText()).trim();
    const shippingCost = carrierPrice.match(/\d[\d\s]*,\d{2}\s*zł/)?.[0] ?? carrierPrice;

    await deliveryForm.getByRole('button', { name: 'Dalej', exact: true }).click();
    await expect(deliveryForm).toBeHidden();
    await expect(page.locator('#cart-subtotal-shipping .value')).toHaveText(shippingCost);
  });
}
