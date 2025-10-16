import { test as base, expect } from '@playwright/test';

/**
 * Custom fixtures for Regami E2E tests
 * Provides authenticated user sessions and test data
 */

export type TestUser = {
  email: string;
  password: string;
  role: 'owner' | 'seeker';
};

type TestFixtures = {
  ownerUser: TestUser;
  seekerUser: TestUser;
  authenticatedOwner: void;
  authenticatedSeeker: void;
};

// Test users - these should exist in your test database
const TEST_OWNER: TestUser = {
  email: 'test-owner@regami.com',
  password: 'TestPassword123!',
  role: 'owner',
};

const TEST_SEEKER: TestUser = {
  email: 'test-seeker@regami.com',
  password: 'TestPassword123!',
  role: 'seeker',
};

export const test = base.extend<TestFixtures>({
  ownerUser: async ({}, use) => {
    await use(TEST_OWNER);
  },

  seekerUser: async ({}, use) => {
    await use(TEST_SEEKER);
  },

  // Fixture that logs in as owner before each test
  authenticatedOwner: async ({ page, ownerUser }, use) => {
    // Navigate to login page
    await page.goto('/login');

    // Fill in login form
    await page.fill('input[name="email"]', ownerUser.email);
    await page.fill('input[name="password"]', ownerUser.password);

    // Submit form
    await page.click('button[type="submit"]');

    // Wait for redirect to dogs page
    await page.waitForURL('/dogs');

    // Verify we're logged in
    await expect(page.locator('text=Logout')).toBeVisible();

    await use();
  },

  // Fixture that logs in as seeker before each test
  authenticatedSeeker: async ({ page, seekerUser }, use) => {
    // Navigate to login page
    await page.goto('/login');

    // Fill in login form
    await page.fill('input[name="email"]', seekerUser.email);
    await page.fill('input[name="password"]', seekerUser.password);

    // Submit form
    await page.click('button[type="submit"]');

    // Wait for redirect
    await page.waitForURL(/\/(dogs|requests)/);

    // Verify we're logged in
    await expect(page.locator('text=Logout')).toBeVisible();

    await use();
  },
});

export { expect };
