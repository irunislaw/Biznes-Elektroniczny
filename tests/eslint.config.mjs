// ESLint dla testów E2E (TypeScript + Playwright). Uruchamiany w CI przez `npm run lint`.
import js from '@eslint/js';
import playwright from 'eslint-plugin-playwright';
import { defineConfig } from 'eslint/config';
import tseslint from 'typescript-eslint';

export default defineConfig(
  { ignores: ['test-results/', 'playwright-report/', 'blob-report/', 'playwright/.cache/'] },
  js.configs.recommended,
  tseslint.configs.recommended,
  {
    files: ['tests/**/*.ts'],
    extends: [playwright.configs['flat/recommended']],
  },
);