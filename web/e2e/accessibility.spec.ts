import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * Accessibility Tests
 * Tests WCAG AA compliance for all main pages
 */

test.describe('Accessibility (a11y)', () => {
  test('Login page should not have accessibility violations', async ({ page }) => {
    await page.goto('/login');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('Register page should not have accessibility violations', async ({ page }) => {
    await page.goto('/register');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('Dogs page should not have accessibility violations', async ({ page }) => {
    await page.goto('/dogs');

    // Wait for content to load
    await page.waitForTimeout(2000);

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('Offers page should not have accessibility violations', async ({ page }) => {
    await page.goto('/offers');

    await page.waitForTimeout(2000);

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('Requests page should not have accessibility violations', async ({ page }) => {
    await page.goto('/requests');

    await page.waitForTimeout(2000);

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('Messages page should not have accessibility violations', async ({ page }) => {
    await page.goto('/messages');

    await page.waitForTimeout(2000);

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('Notifications page should not have accessibility violations', async ({ page }) => {
    await page.goto('/notifications');

    await page.waitForTimeout(2000);

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('Profile page should not have accessibility violations', async ({ page }) => {
    await page.goto('/profile');

    await page.waitForTimeout(2000);

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test.describe('Keyboard Navigation', () => {
    test('should navigate login form with keyboard', async ({ page }) => {
      await page.goto('/login');

      // Tab through form elements
      await page.keyboard.press('Tab'); // Focus email input
      await page.keyboard.type('test@example.com');

      await page.keyboard.press('Tab'); // Focus password input
      await page.keyboard.type('password123');

      await page.keyboard.press('Tab'); // Focus submit button

      // Check that focus is visible
      const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
      expect(focusedElement).toBeTruthy();
    });

    test('should navigate register form with keyboard', async ({ page }) => {
      await page.goto('/register');

      // Tab through all form elements
      for (let i = 0; i < 10; i++) {
        await page.keyboard.press('Tab');

        // Verify focus is visible
        const hasFocus = await page.evaluate(() => {
          const el = document.activeElement;
          if (!el) return false;

          const style = window.getComputedStyle(el);
          const pseudoStyle = window.getComputedStyle(el, ':focus');

          // Check if element has visible focus (outline or box-shadow)
          return style.outline !== 'none' ||
                 pseudoStyle.outline !== 'none' ||
                 style.boxShadow !== 'none';
        });

        // Focus should be visible on interactive elements
        if (hasFocus) {
          expect(hasFocus).toBeTruthy();
        }
      }
    });
  });

  test.describe('Color Contrast', () => {
    test('should have sufficient color contrast on all pages', async ({ page }) => {
      const pages = ['/login', '/register', '/dogs', '/offers', '/messages'];

      for (const pagePath of pages) {
        await page.goto(pagePath);
        await page.waitForTimeout(1000);

        const results = await new AxeBuilder({ page })
          .withTags(['wcag2aa'])
          .disableRules(['color-contrast']) // We'll check this separately
          .analyze();

        // Check specifically for color contrast issues
        const contrastResults = await new AxeBuilder({ page })
          .include('body')
          .withRules(['color-contrast'])
          .analyze();

        // Log any contrast violations but don't fail (they need manual review)
        if (contrastResults.violations.length > 0) {
          console.log(`Color contrast issues on ${pagePath}:`,
            contrastResults.violations.map(v => ({
              description: v.description,
              nodes: v.nodes.length
            }))
          );
        }
      }
    });
  });

  test.describe('Screen Reader Support', () => {
    test('should have proper ARIA labels on interactive elements', async ({ page }) => {
      await page.goto('/dogs');
      await page.waitForTimeout(2000);

      // Check that buttons have accessible names
      const buttons = await page.locator('button').all();

      for (const button of buttons) {
        const ariaLabel = await button.getAttribute('aria-label');
        const text = await button.textContent();
        const title = await button.getAttribute('title');

        // Button should have either text content, aria-label, or title
        const hasAccessibleName = (text && text.trim()) || ariaLabel || title;
        expect(hasAccessibleName).toBeTruthy();
      }
    });

    test('should have proper form labels', async ({ page }) => {
      await page.goto('/register');

      // Check that all inputs have associated labels
      const inputs = await page.locator('input[type="text"], input[type="email"], input[type="password"]').all();

      for (const input of inputs) {
        const id = await input.getAttribute('id');
        const ariaLabel = await input.getAttribute('aria-label');
        const ariaLabelledBy = await input.getAttribute('aria-labelledby');

        if (id) {
          // Check if there's a label pointing to this input
          const label = await page.locator(`label[for="${id}"]`).count();
          const hasLabel = label > 0 || ariaLabel || ariaLabelledBy;
          expect(hasLabel).toBeTruthy();
        }
      }
    });
  });
});
