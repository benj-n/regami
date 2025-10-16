import { test, expect } from './fixtures';

/**
 * E2E Tests: Authentication Flow
 * Tests user registration and login
 */

test.describe('Authentication', () => {
  test.describe('Registration', () => {
    test('should register a new owner successfully', async ({ page }) => {
      await page.goto('/register');

      // Generate unique email for this test run
      const timestamp = Date.now();
      const email = `owner-${timestamp}@test.com`;

      // Fill in registration form
      await page.fill('input[name="email"]', email);
      await page.fill('input[name="password"]', 'TestPassword123!');
      await page.fill('input[name="confirm_password"]', 'TestPassword123!');
      await page.fill('input[name="name"]', 'Test Owner');

      // Select owner role
      await page.click('input[value="owner"]');

      // Submit form
      await page.click('button[type="submit"]');

      // Should redirect to dogs page
      await page.waitForURL('/dogs', { timeout: 10000 });

      // Should show welcome message or empty state
      await expect(page.locator('h1')).toContainText(/Dogs|My Dogs/i);
    });

    test('should register a new seeker successfully', async ({ page }) => {
      await page.goto('/register');

      const timestamp = Date.now();
      const email = `seeker-${timestamp}@test.com`;

      await page.fill('input[name="email"]', email);
      await page.fill('input[name="password"]', 'TestPassword123!');
      await page.fill('input[name="confirm_password"]', 'TestPassword123!');
      await page.fill('input[name="name"]', 'Test Seeker');

      // Select seeker role
      await page.click('input[value="seeker"]');

      await page.click('button[type="submit"]');

      // Should redirect
      await page.waitForURL(/\/(dogs|requests)/, { timeout: 10000 });
    });

    test('should show error for mismatched passwords', async ({ page }) => {
      await page.goto('/register');

      await page.fill('input[name="email"]', 'test@test.com');
      await page.fill('input[name="password"]', 'TestPassword123!');
      await page.fill('input[name="confirm_password"]', 'DifferentPassword123!');
      await page.fill('input[name="name"]', 'Test User');
      await page.click('input[value="owner"]');

      await page.click('button[type="submit"]');

      // Should show error message
      await expect(page.locator('text=/password.*match/i')).toBeVisible();
    });

    test('should show error for existing email', async ({ page }) => {
      await page.goto('/register');

      // Use existing test user email
      await page.fill('input[name="email"]', 'test-owner@regami.com');
      await page.fill('input[name="password"]', 'TestPassword123!');
      await page.fill('input[name="confirm_password"]', 'TestPassword123!');
      await page.fill('input[name="name"]', 'Test User');
      await page.click('input[value="owner"]');

      await page.click('button[type="submit"]');

      // Should show error message
      await expect(page.locator('text=/already.*exists|already.*registered/i')).toBeVisible();
    });
  });

  test.describe('Login', () => {
    test('should login owner successfully', async ({ page, ownerUser }) => {
      await page.goto('/login');

      await page.fill('input[name="email"]', ownerUser.email);
      await page.fill('input[name="password"]', ownerUser.password);
      await page.click('button[type="submit"]');

      // Should redirect to dogs page
      await page.waitForURL('/dogs', { timeout: 10000 });

      // Should show logout button
      await expect(page.locator('text=Logout')).toBeVisible();
    });

    test('should login seeker successfully', async ({ page, seekerUser }) => {
      await page.goto('/login');

      await page.fill('input[name="email"]', seekerUser.email);
      await page.fill('input[name="password"]', seekerUser.password);
      await page.click('button[type="submit"]');

      // Should redirect
      await page.waitForURL(/\/(dogs|requests)/, { timeout: 10000 });

      // Should show logout button
      await expect(page.locator('text=Logout')).toBeVisible();
    });

    test('should show error for invalid credentials', async ({ page }) => {
      await page.goto('/login');

      await page.fill('input[name="email"]', 'invalid@test.com');
      await page.fill('input[name="password"]', 'WrongPassword123!');
      await page.click('button[type="submit"]');

      // Should show error message
      await expect(page.locator('text=/invalid.*credentials|incorrect.*password/i')).toBeVisible();
    });

    test('should logout successfully', async ({ page, authenticatedOwner }) => {
      // Already logged in via fixture
      await expect(page.locator('text=Logout')).toBeVisible();

      // Click logout
      await page.click('text=Logout');

      // Should redirect to login page
      await page.waitForURL('/login', { timeout: 10000 });

      // Should show login form
      await expect(page.locator('input[name="email"]')).toBeVisible();
    });
  });
});
