import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';
import path from 'path';

// Zrzuty ekranu do porównania wyglądu (docs/wyglad/), osobno od testów E2E.
// Uruchamiane przez `make wyglad`; `make test` ich nie obejmuje, bo ma testDir './tests'.
dotenv.config({ path: path.resolve(__dirname, '..', '.env'), quiet: true });

export default defineConfig({
  testDir: './zrzuty',
  outputDir: './test-results/zrzuty',
  fullyParallel: true,
  // Sklep źródłowy to cudza produkcja: najwyżej dwie przeglądarki naraz.
  workers: 2,
  retries: 0,
  timeout: 180_000,
  reporter: 'list',
  use: {
    baseURL: process.env.BASE_URL,
    headless: true,
    ignoreHTTPSErrors: true,
    locale: 'pl-PL',
  },
  projects: [
    {
      name: 'komputer',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: '360',
      use: { ...devices['Pixel 5'], viewport: { width: 360, height: 780 }, deviceScaleFactor: 2 },
    },
  ],
});
