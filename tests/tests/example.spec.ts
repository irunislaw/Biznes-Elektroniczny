import { test, expect, ConsoleMessage } from '@playwright/test';

test('main page loads without errors', async({page}) => {
  const errors: ConsoleMessage[] = [];

  //console error listeners
  page.on('console', msg => {
    if (msg.type() === 'error')
      errors.push(msg);
  })

  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Popularne produkty'})).toBeVisible();

  //await page.evaluate(() => {console.error('test error');});

  expect(errors).toHaveLength(0);
});
