import { expect, type Page } from '@playwright/test';

export async function registerNewUser(page: Page) {
  const name = 'Klient';
  const surname = 'Testowy';
  const fullName = `${name} ${surname}`;
  const email = `${name}.${surname}+${Date.now()}@test-email.com`;

  await page.locator('header').getByRole('link', { name: 'Zaloguj się' }).click();
  await page.getByRole('link', { name: 'Nie masz konta? Załóż je tutaj' }).click();
  await page.getByRole('radio', { name: 'Pan', exact: true }).check();
  await page.getByRole('textbox', { name: 'Imię' }).fill(name);
  await page.getByRole('textbox', { name: 'Nazwisko' }).fill(surname);
  await page.getByRole('textbox', { name: 'E-mail' }).fill(email);
  await page.getByRole('textbox', { name: 'Pole wprowadzania hasła' }).fill('Haslo Klienta Do Testow');
  await page.getByRole('checkbox', { name: 'Akceptuję ogólne warunki' }).check();
  await page.getByRole('checkbox', { name: 'Wiadomość o przetwarzaniu' }).check();

  await page.getByRole('button', { name: 'Zapisz' }).click();
  await expect(page.getByRole('link', { name: fullName })).toBeVisible();
}
