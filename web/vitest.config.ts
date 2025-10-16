import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
    exclude: [
      'node_modules/**',
      'dist/**',
      'e2e/**',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
      exclude: [
        'node_modules/',
        'dist/',
        'e2e/',
        '**/*.config.{ts,js}',
        '**/*.d.ts',
        '**/__tests__/**',
        '**/test-utils/**',
        'vitest.setup.ts',
        // Exclude entry points and config files
        'src/main.tsx',
        'src/i18n.ts',
        'src/env.ts',
        // Exclude storybook
        '.storybook/**',
        'src/stories/**',
        // Exclude service worker and PWA
        '**/sw.ts',
        '**/registerSW.ts',
      ],
      thresholds: {
        lines: 35,
        functions: 30,
        branches: 50,
        statements: 35,
      },
      // Only measure coverage for files touched by tests
      all: false,
      clean: true,
    },
  },
})
