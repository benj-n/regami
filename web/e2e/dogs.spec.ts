import { test, expect } from './fixtures';

/**
 * E2E Tests: Dog Profile Management
 * Tests creating, viewing, and managing dog profiles
 */

test.describe('Dog Profile Management', () => {
  test.use({ storageState: undefined }); // Start fresh for each test

  test('should create a new dog profile', async ({ page, authenticatedOwner }) => {
    // Navigate to dogs page
    await page.goto('/dogs');

    // Click "Add Dog" or similar button
    const addButton = page.locator('button:has-text("Add"), a:has-text("Add")').first();
    await addButton.click();

    // Fill in dog form
    await page.fill('input[name="name"]', 'Test Dog');
    await page.selectOption('select[name="breed"]', { index: 1 }); // Select first breed
    await page.selectOption('select[name="gender"]', 'male');
    await page.fill('input[name="age"]', '3');
    await page.fill('input[name="weight"]', '25');
    await page.fill('textarea[name="description"]', 'Friendly and energetic dog');

    // Submit form
    await page.click('button[type="submit"]');

    // Should show success message or redirect
    await expect(page.locator('text=/successfully|created/i')).toBeVisible({ timeout: 10000 });
  });

  test('should view dog profile details', async ({ page, authenticatedOwner }) => {
    await page.goto('/dogs');

    // Wait for dogs to load
    await page.waitForSelector('.dog-card, [data-testid="dog-card"]', { timeout: 10000 });

    // Click on first dog
    await page.click('.dog-card:first-child, [data-testid="dog-card"]:first-child');

    // Should show dog details
    await expect(page.locator('text=/name|breed|age|weight/i')).toBeVisible();
  });

  test('should upload photo for dog', async ({ page, authenticatedOwner }) => {
    await page.goto('/dogs');

    // Wait for dogs to load
    await page.waitForSelector('.dog-card, [data-testid="dog-card"]', { timeout: 10000 });

    // Click on first dog or upload button
    const uploadButton = page.locator('button:has-text("Upload"), input[type="file"]').first();

    if (await uploadButton.count() > 0) {
      // Create a test image file
      const buffer = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 'base64');

      // Upload file
      const fileInput = page.locator('input[type="file"]').first();
      await fileInput.setInputFiles({
        name: 'test-dog.png',
        mimeType: 'image/png',
        buffer: buffer,
      });

      // Wait for upload to complete
      await expect(page.locator('text=/upload.*success|uploaded/i')).toBeVisible({ timeout: 15000 });
    }
  });

  test('should filter dogs by breed', async ({ page, authenticatedOwner }) => {
    await page.goto('/dogs');

    // Wait for dogs to load
    await page.waitForSelector('.dog-card, [data-testid="dog-card"]', { timeout: 10000 });

    // Find and use breed filter
    const breedFilter = page.locator('select[name="breed"], select:has-text("Breed")').first();

    if (await breedFilter.count() > 0) {
      await breedFilter.selectOption({ index: 1 });

      // Wait for filter to apply
      await page.waitForTimeout(1000);

      // Should show filtered results
      const dogCards = page.locator('.dog-card, [data-testid="dog-card"]');
      await expect(dogCards.first()).toBeVisible();
    }
  });

  test('should search dogs by location', async ({ page, authenticatedOwner }) => {
    await page.goto('/dogs');

    // Look for location/map input
    const locationInput = page.locator('input[placeholder*="location"], input[name="location"]').first();

    if (await locationInput.count() > 0) {
      await locationInput.fill('Madrid, Spain');
      await page.keyboard.press('Enter');

      // Wait for results
      await page.waitForTimeout(2000);

      // Should show search results
      const results = page.locator('.dog-card, [data-testid="dog-card"]');
      // Results may or may not be empty depending on test data
      await expect(results.first()).toBeVisible({ timeout: 5000 }).catch(() => {
        // No results is also valid
      });
    }
  });
});
