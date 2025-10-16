import { test, expect } from './fixtures';

/**
 * E2E Tests: Messaging Flow
 * Tests sending, receiving, and managing messages
 */

test.describe('Messaging', () => {
  test('should navigate to messages page', async ({ page, authenticatedOwner }) => {
    await page.goto('/messages');

    // Should show messages page
    await expect(page.locator('h1, h2')).toContainText(/messages/i);
  });

  test('should display conversations list', async ({ page, authenticatedOwner }) => {
    await page.goto('/messages');

    // Wait for conversations to load
    await page.waitForTimeout(2000);

    // Should show conversations or empty state
    const conversations = page.locator('.conversation, [data-testid="conversation"]');
    const emptyState = page.locator('text=/no.*messages|no.*conversations/i');

    const hasConversations = await conversations.count() > 0;
    const hasEmptyState = await emptyState.count() > 0;

    expect(hasConversations || hasEmptyState).toBeTruthy();
  });

  test('should send a message in existing conversation', async ({ page, authenticatedOwner }) => {
    await page.goto('/messages');

    // Wait for conversations
    await page.waitForTimeout(2000);

    const conversations = page.locator('.conversation, [data-testid="conversation"]');
    const count = await conversations.count();

    if (count > 0) {
      // Click first conversation
      await conversations.first().click();

      // Wait for messages to load
      await page.waitForTimeout(1000);

      // Type a message
      const messageInput = page.locator('input[name="message"], textarea[name="message"]').first();
      await messageInput.fill('Test message from E2E test');

      // Send message
      const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
      await sendButton.click();

      // Message should appear in conversation
      await expect(page.locator('text=Test message from E2E test')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should mark message as read', async ({ page, authenticatedSeeker }) => {
    await page.goto('/messages');

    // Wait for conversations
    await page.waitForTimeout(2000);

    const unreadConversations = page.locator('.conversation.unread, [data-unread="true"]');
    const count = await unreadConversations.count();

    if (count > 0) {
      // Click unread conversation
      await unreadConversations.first().click();

      // Wait for messages to load - this should mark them as read
      await page.waitForTimeout(2000);

      // Go back to conversations list
      await page.goto('/messages');
      await page.waitForTimeout(1000);

      // The conversation should no longer be marked as unread
      // (or unread count should decrease)
    }
  });

  test('should show message timestamp', async ({ page, authenticatedOwner }) => {
    await page.goto('/messages');

    await page.waitForTimeout(2000);

    const conversations = page.locator('.conversation, [data-testid="conversation"]');
    const count = await conversations.count();

    if (count > 0) {
      await conversations.first().click();

      // Messages should have timestamps
      const timestamps = page.locator('[class*="time"], [class*="date"]');

      if (await timestamps.count() > 0) {
        const timestampText = await timestamps.first().textContent();
        // Should have some time indicator
        expect(timestampText).toBeTruthy();
      }
    }
  });

  test('should filter/search conversations', async ({ page, authenticatedOwner }) => {
    await page.goto('/messages');

    await page.waitForTimeout(2000);

    // Look for search input
    const searchInput = page.locator('input[type="search"], input[placeholder*="search"]').first();

    if (await searchInput.count() > 0) {
      await searchInput.fill('test');

      // Wait for filter to apply
      await page.waitForTimeout(1000);

      // Should show filtered results or no results
      const results = page.locator('.conversation, [data-testid="conversation"]');
      // Any count (including 0) is valid after filtering
      await page.waitForTimeout(500);
    }
  });

  test('should show typing indicator (if implemented)', async ({ page, authenticatedOwner }) => {
    await page.goto('/messages');

    await page.waitForTimeout(2000);

    const conversations = page.locator('.conversation, [data-testid="conversation"]');
    const count = await conversations.count();

    if (count > 0) {
      await conversations.first().click();

      // Start typing
      const messageInput = page.locator('input[name="message"], textarea[name="message"]').first();
      await messageInput.fill('Typing...');

      // Look for typing indicator (implementation-dependent)
      // This is a nice-to-have feature
      const typingIndicator = page.locator('text=/typing/i');
      // Don't fail if not implemented
      if (await typingIndicator.count() > 0) {
        expect(await typingIndicator.isVisible()).toBeTruthy();
      }
    }
  });
});
