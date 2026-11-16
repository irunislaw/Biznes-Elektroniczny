import { expect, type Page } from '@playwright/test';

export async function checkOrderInHistory(page: Page, customerName: string, orderNumber: string) {
  await page.locator('header').getByRole('link', { name: customerName }).click();
  await page.getByRole('link', { name: /Historia i szczegóły zamówień/i }).click();

  const orderRow = orderRowByNumber(page, orderNumber);
  await expect(orderRow, `Zamówienie ${orderNumber} w historii`).toBeVisible();
  await expect(orderRow.getByRole('cell', {
    name: 'Oczekiwanie na płatność przy odbiorze',
    exact: true,
  })).toBeVisible();
}

function orderRowByNumber(page: Page, orderNumber: string) {
  return page.getByRole('row').filter({
    has: page.getByRole('rowheader', { name: orderNumber, exact: true }),
  });
}
