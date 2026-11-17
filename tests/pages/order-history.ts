import { readFile } from 'node:fs/promises';
import { expect, test, type Page } from '@playwright/test';

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

export async function downloadOrderInvoice(page: Page, orderNumber: string) {
  const invoiceLink = orderRowByNumber(page, orderNumber).getByRole('link').filter({ hasText: '' });
  await expect(invoiceLink, `Brak widocznego linku do faktury VAT dla zamówienia ${orderNumber}`).toBeVisible();
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    invoiceLink.click(),
  ]);

  const invoicePath = test.info().outputPath(download.suggestedFilename());
  await download.saveAs(invoicePath);

  const invoice = await readFile(invoicePath);
  expect(invoice.length, 'Rozmiar pobranej faktury').toBeGreaterThan(0);
  expect(invoice.toString('utf8', 0, 4), 'Sygnatura pobranej faktury').toBe('%PDF');
}

function orderRowByNumber(page: Page, orderNumber: string) {
  return page.getByRole('row').filter({
    has: page.getByRole('rowheader', { name: orderNumber, exact: true }),
  });
}
