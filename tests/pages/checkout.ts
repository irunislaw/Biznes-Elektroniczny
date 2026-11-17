import { expect, test, type Page } from '@playwright/test';

export async function proceedToDelivery(page: Page) {
  const address = 'ul. Testowa 15'
  const zipCode = '00-001'
  const city = 'Gdańsk'

  const checkoutLink = page.getByRole('link', { name: 'Przejdź do realizacji zamówienia', exact: true });
  await expectNoStockErrors(page);
  expect(
    await checkoutLink.isVisible() && await checkoutLink.isEnabled(),
    'Przejście z koszyka do realizacji zamówienia jest niedostępne',
  ).toBe(true);
  await checkoutLink.click();
  await expectNoStockErrors(page);

  const addressForm = page.locator('#checkout-addresses-step .js-address-form > form');
  await expect(addressForm, 'Po przejściu z koszyka powinien pojawić się formularz adresu').toBeVisible();
  await addressForm.getByRole('combobox', { name: 'Kraj' }).selectOption({ label: 'Polska' });
  await expect(addressForm.getByRole('combobox', { name: 'Stan' })).toBeHidden();
  await addressForm.getByRole('textbox', { name: 'Adres', exact: true }).fill(address);
  await addressForm.getByRole('textbox', { name: 'Kod pocztowy' }).fill(zipCode);
  await addressForm.getByRole('textbox', { name: 'Miasto' }).fill(city);
  await addressForm.getByRole('button', { name: 'Dalej', exact: true }).click();

  const deliveryForm = page.locator('#checkout-delivery-step form');
  await expect(deliveryForm).toBeVisible();
  await expect(addressForm).toBeHidden();
}

async function expectNoStockErrors(page: Page) {
  const stockErrors = await page.getByRole('alert')
    .filter({ hasText: 'Proszę dostosować ilość w koszyku' })
    .allTextContents();
  expect(stockErrors, 'Sklep zgłosił niewystarczający stan magazynowy').toEqual([]);
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
    // Jeśli zmienia się dostawa to czeka aż serwer ją zmieni
    if (!(await carrier.isChecked())) {
      await Promise.all([
        page.waitForEvent('requestfinished', request =>
          new URL(request.url()).searchParams.get('action') === 'selectDeliveryOption',
        ),
        carrier.check(),
      ]);
    }
    await expect(carrier).toBeChecked();

    const carrierPrice = (await deliveryOption.locator('.carrier-price').innerText()).trim();
    const shippingCost = carrierPrice.match(/\d[\d\s]*,\d{2}\s*zł/)?.[0] ?? carrierPrice;

    await deliveryForm.getByRole('button', { name: 'Dalej', exact: true }).click();
    await expect(deliveryForm).toBeHidden();
    await expect(page.locator('#cart-subtotal-shipping > span.value')).toHaveText(shippingCost);
  });
}

export async function selectCashOnDelivery(page: Page) {
  const paymentStep = page.locator('#checkout-payment-step');
  const cashOnDelivery = paymentStep.getByRole('radio', { name: 'Zapłać gotówką przy odbiorze' });
  await cashOnDelivery.check();
  await expect(cashOnDelivery).toBeChecked();

  const terms = paymentStep.getByRole('checkbox', { name: /Zgadzam się z warunkami/ });
  await terms.check();
  await expect(terms).toBeChecked();
}

export async function confirmOrder(page: Page) {
  const checkoutTotal = page.locator('#js-checkout-summary .cart-total .value');
  await expect(checkoutTotal).toHaveText(/\d/);
  const expectedTotal = await checkoutTotal.innerText();

  await page.getByRole('button', { name: 'Złóż zamówienie', exact: true }).click();

  const confirmation = page.getByRole('heading', { name: /Twoje zamówienie zostało potwierdzone/i });
  await expect(confirmation).toBeVisible({ timeout: 30_000 });
  const orderReferenceLabel = page.locator('#order-reference-value');
  await expect(orderReferenceLabel).toHaveText(/^Numer zamówienia:\s*[A-Z]{9}$/);
  await expect(page.locator('#order-details').getByText('Metoda płatności: Płatność przy odbiorze', {
    exact: true,
  })).toBeVisible();

  const confirmedTotal = page.locator('#order-items tr.total-value td:last-child');
  await expect(confirmedTotal, 'Łączna kwota zamówienia').toHaveText(expectedTotal);

  return (await orderReferenceLabel.innerText()).replace(/^Numer zamówienia:\s*/, '').trim();
}
