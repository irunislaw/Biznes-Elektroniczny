import { expect, type Page } from '@playwright/test';

export async function proceedToDelivery(page: Page) {
  const address = 'ul. Testowa 15'
  const zipCode = '00-001'
  const city = 'Gdańsk'

  await page.getByRole('link', { name: 'Przejdź do realizacji zamówienia' }).click();

  const addressForm = page.locator('#checkout-addresses-step');
  await addressForm.getByRole('combobox', { name: 'Kraj' }).selectOption({ label: 'Polska' });
  await expect(addressForm.getByRole('combobox', { name: 'Stan' })).toBeHidden();
  await addressForm.getByRole('textbox', { name: 'Adres', exact: true }).fill(address);
  await addressForm.getByRole('textbox', { name: 'Kod pocztowy' }).fill(zipCode);
  await addressForm.getByRole('textbox', { name: 'Miasto' }).fill(city);
  await addressForm.getByRole('button', { name: 'Dalej', exact: true }).click();

  const deliveryForm = page.locator('#checkout-delivery-step');
  await expect(addressForm.locator('form')).toBeHidden();
  await expect(deliveryForm.locator('form')).toBeVisible();
}
