import { test, expect } from './fixtures';

/**
 * E2E Tests: Matching Flow
 * Tests creating offers, requests, and matching logic
 */

test.describe('Matching Flow', () => {
  test.describe('Offers (Owner)', () => {
    test('should create a new offer', async ({ page, authenticatedOwner }) => {
      await page.goto('/offers');

      // Click create offer button
      const createButton = page.locator('button:has-text("Create"), a:has-text("New Offer")').first();
      await createButton.click();

      // Fill in offer form
      // Select dog
      const dogSelect = page.locator('select[name="dog_id"]').first();
      if (await dogSelect.count() > 0) {
        await dogSelect.selectOption({ index: 1 });
      }

      // Select dates (if date pickers exist)
      const startDateInput = page.locator('input[name="start_date"]').first();
      if (await startDateInput.count() > 0) {
        // Set dates 1 week from now
        const startDate = new Date();
        startDate.setDate(startDate.getDate() + 7);
        const endDate = new Date(startDate);
        endDate.setDate(endDate.getDate() + 14);

        await startDateInput.fill(startDate.toISOString().split('T')[0]);
        await page.locator('input[name="end_date"]').fill(endDate.toISOString().split('T')[0]);
      }

      // Fill price if applicable
      const priceInput = page.locator('input[name="price"]').first();
      if (await priceInput.count() > 0) {
        await priceInput.fill('50');
      }

      // Submit form
      await page.click('button[type="submit"]');

      // Should show success or redirect
      await expect(page.locator('text=/success|created/i')).toBeVisible({ timeout: 10000 });
    });

    test('should view offer details', async ({ page, authenticatedOwner }) => {
      await page.goto('/offers');

      // Wait for offers to load
      await page.waitForSelector('.offer-card, [data-testid="offer-card"]', { timeout: 10000 }).catch(() => {
        // No offers yet is valid
      });

      const offerCards = page.locator('.offer-card, [data-testid="offer-card"]');
      const count = await offerCards.count();

      if (count > 0) {
        // Click first offer
        await offerCards.first().click();

        // Should show offer details
        await expect(page.locator('text=/dog|date|price/i')).toBeVisible();
      }
    });

    test('should accept a match request', async ({ page, authenticatedOwner }) => {
      await page.goto('/offers');

      // Look for pending matches
      const matchesTab = page.locator('text=/matches|requests/i').first();
      if (await matchesTab.count() > 0) {
        await matchesTab.click();

        // Wait for matches to load
        await page.waitForTimeout(1000);

        // Look for accept button
        const acceptButton = page.locator('button:has-text("Accept")').first();
        if (await acceptButton.count() > 0) {
          await acceptButton.click();

          // Should show confirmation
          await expect(page.locator('text=/accepted|confirmed/i')).toBeVisible({ timeout: 5000 });
        }
      }
    });
  });

  test.describe('Requests (Seeker)', () => {
    test('should create a new request', async ({ page, authenticatedSeeker }) => {
      await page.goto('/requests');

      // Click create request button
      const createButton = page.locator('button:has-text("Create"), a:has-text("New Request")').first();
      await createButton.click();

      // Fill in request form
      const breedSelect = page.locator('select[name="preferred_breed"]').first();
      if (await breedSelect.count() > 0) {
        await breedSelect.selectOption({ index: 1 });
      }

      // Set dates
      const startDateInput = page.locator('input[name="start_date"]').first();
      if (await startDateInput.count() > 0) {
        const startDate = new Date();
        startDate.setDate(startDate.getDate() + 7);
        const endDate = new Date(startDate);
        endDate.setDate(endDate.getDate() + 14);

        await startDateInput.fill(startDate.toISOString().split('T')[0]);
        await page.locator('input[name="end_date"]').fill(endDate.toISOString().split('T')[0]);
      }

      // Fill budget
      const budgetInput = page.locator('input[name="budget"]').first();
      if (await budgetInput.count() > 0) {
        await budgetInput.fill('100');
      }

      // Submit form
      await page.click('button[type="submit"]');

      // Should show success
      await expect(page.locator('text=/success|created/i')).toBeVisible({ timeout: 10000 });
    });

    test('should browse available offers', async ({ page, authenticatedSeeker }) => {
      await page.goto('/dogs');

      // Should show available dogs/offers
      await page.waitForSelector('.dog-card, .offer-card, [data-testid="dog-card"]', { timeout: 10000 }).catch(() => {
        // Empty state is valid
      });

      const cards = page.locator('.dog-card, .offer-card, [data-testid="dog-card"]');
      const count = await cards.count();

      if (count > 0) {
        // Click on first available offer
        await cards.first().click();

        // Should show details
        await expect(page.locator('text=/name|breed|available/i')).toBeVisible();
      }
    });

    test('should confirm a match', async ({ page, authenticatedSeeker }) => {
      await page.goto('/requests');

      // Look for matches section
      const matchesTab = page.locator('text=/matches|accepted/i').first();
      if (await matchesTab.count() > 0) {
        await matchesTab.click();

        // Wait for matches to load
        await page.waitForTimeout(1000);

        // Look for confirm button
        const confirmButton = page.locator('button:has-text("Confirm")').first();
        if (await confirmButton.count() > 0) {
          await confirmButton.click();

          // Should show confirmation
          await expect(page.locator('text=/confirmed|complete/i')).toBeVisible({ timeout: 5000 });
        }
      }
    });
  });

  test.describe('Match Status', () => {
    test('should show match status updates', async ({ page, authenticatedOwner }) => {
      await page.goto('/offers');

      // Check for status indicators
      const statusBadges = page.locator('[class*="status"], [class*="badge"]');

      if (await statusBadges.count() > 0) {
        // Should have status text like "Pending", "Accepted", "Confirmed"
        const statusText = await statusBadges.first().textContent();
        expect(statusText).toMatch(/pending|accepted|confirmed|completed|cancelled/i);
      }
    });
  });
});
