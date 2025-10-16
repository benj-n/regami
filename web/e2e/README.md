# E2E Testing with Playwright

## Overview

This directory contains end-to-end (E2E) tests for the Regami web frontend using Playwright. Tests verify critical user flows work correctly across multiple browsers.

## Quick Start

```bash
# Install Playwright browsers (first time only)
npx playwright install

# Run all E2E tests
npm run test:e2e

# Run tests with browser UI (for debugging)
npm run test:e2e:headed

# Run tests with Playwright UI (interactive debugging)
npm run test:e2e:ui

# Run only accessibility tests
npm run test:a11y
```

## Test Files

### Core Test Suites

1. **`auth.spec.ts`** - Authentication flows
   - User registration (owner/seeker roles)
   - Login/logout
   - Error handling (mismatched passwords, existing email, invalid credentials)

2. **`dogs.spec.ts`** - Dog profile management
   - Create dog profile
   - View dog details
   - Upload photos
   - Filter by breed
   - Search by location

3. **`matching.spec.ts`** - Matching flows
   - Create/view offers (owners)
   - Create/browse requests (seekers)
   - Accept matches
   - Confirm matches
   - Match status updates

4. **`messaging.spec.ts`** - Messaging functionality
   - View conversations
   - Send messages
   - Mark as read
   - Filter/search conversations
   - Timestamps

5. **`accessibility.spec.ts`** - WCAG 2.1 AA compliance
   - All 8 main pages tested
   - Keyboard navigation
   - Color contrast
   - ARIA labels
   - Screen reader support

### Test Fixtures

**`fixtures.ts`** - Custom test fixtures
- `ownerUser`: Test owner credentials
- `seekerUser`: Test seeker credentials
- `authenticatedOwner`: Auto-login as owner before test
- `authenticatedSeeker`: Auto-login as seeker before test

## Test Data Requirements

Tests require specific test users to exist in the database:

```json
{
  "owner": {
    "email": "test-owner@regami.com",
    "password": "TestPassword123!",
    "role": "owner"
  },
  "seeker": {
    "email": "test-seeker@regami.com",
    "password": "TestPassword123!",
    "role": "seeker"
  }
}
```

### Setting Up Test Data

**Option 1: Seed Script**
```bash
cd backend
python scripts/seed_test_users.py
```

**Option 2: Manual Registration**
1. Start the app: `npm run dev`
2. Navigate to http://localhost:5173/register
3. Create users with credentials above

**Option 3: API Calls**
```bash
# Create test owner
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-owner@regami.com",
    "password": "TestPassword123!",
    "name": "Test Owner",
    "role": "owner"
  }'

# Create test seeker
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test-seeker@regami.com",
    "password": "TestPassword123!",
    "name": "Test Seeker",
    "role": "seeker"
  }'
```

## Running Tests

### Local Development

```bash
# Run all tests
npm run test:e2e

# Run specific test file
npx playwright test auth.spec.ts

# Run specific test by name
npx playwright test -g "should login owner successfully"

# Run in headed mode (see browser)
npm run test:e2e:headed

# Run in debug mode
npx playwright test --debug
```

### CI/CD

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

See `.github/workflows/web-ci.yml` for CI configuration.

## Browser Support

Tests run on:
- **Desktop:** Chromium, Firefox, WebKit (Safari)
- **Mobile:** Pixel 5 (Chrome), iPhone 12 (Safari)

To run on specific browser:
```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
npx playwright test --project="Mobile Chrome"
npx playwright test --project="Mobile Safari"
```

## Debugging

### Playwright UI Mode (Recommended)

```bash
npm run test:e2e:ui
```

Features:
- Watch tests run in real-time
- Time travel debugging (step through actions)
- Inspect DOM at each step
- View network requests
- Modify and re-run tests

### Debug Mode

```bash
npx playwright test --debug
```

Opens Playwright Inspector for step-by-step debugging.

### Screenshots and Videos

On test failure:
- Screenshots saved to `test-results/`
- Videos saved to `test-results/`

To always capture:
```typescript
test.use({ screenshot: 'on', video: 'on' })
```

### Trace Viewer

Traces are captured on first retry. View with:
```bash
npx playwright show-trace trace.zip
```

## Writing New Tests

### Basic Test Structure

```typescript
import { test, expect } from './fixtures';

test.describe('Feature Name', () => {
  test('should do something', async ({ page }) => {
    await page.goto('/path');
    await page.click('button');
    await expect(page.locator('text=Success')).toBeVisible();
  });
});
```

### Using Authentication Fixtures

```typescript
test('should create dog', async ({ page, authenticatedOwner }) => {
  // User is already logged in as owner
  await page.goto('/dogs');
  // ... test steps
});
```

### Best Practices

1. **Use semantic selectors**
   ```typescript
   // Good
   await page.click('button:has-text("Submit")')
   await page.locator('text=Welcome').isVisible()

   // Avoid (brittle)
   await page.click('.btn-primary')
   ```

2. **Wait for conditions, not time**
   ```typescript
   // Good
   await page.waitForSelector('text=Loaded')
   await page.waitForURL('/dashboard')

   // Avoid
   await page.waitForTimeout(5000)
   ```

3. **Keep tests independent**
   - Don't rely on previous test state
   - Clean up test data after test
   - Use unique test data (timestamps, UUIDs)

4. **Test user flows, not implementation**
   - Test what users do, not how it's coded
   - Focus on critical paths
   - Don't test every edge case in E2E (use unit tests)

5. **Handle async properly**
   - Always `await` Playwright actions
   - Use `waitFor*` methods for timing
   - Set reasonable timeouts

## Accessibility Testing

### Running a11y Tests

```bash
npm run test:a11y
```

### Interpreting Results

Violations are grouped by:
- **impact**: critical, serious, moderate, minor
- **tags**: wcag2a, wcag2aa, wcag21a, wcag21aa

Example violation:
```json
{
  "id": "color-contrast",
  "impact": "serious",
  "description": "Elements must have sufficient color contrast",
  "nodes": [
    {
      "html": "<button>Submit</button>",
      "target": ["button"]
    }
  ]
}
```

### Common Issues

1. **Missing ARIA labels**
   ```html
   <!-- Bad -->
   <button><Icon /></button>

   <!-- Good -->
   <button aria-label="Close"><Icon /></button>
   ```

2. **Low color contrast**
   - Check contrast ratios at https://webaim.org/resources/contrastchecker/
   - WCAG AA requires 4.5:1 for normal text, 3:1 for large text

3. **Missing form labels**
   ```html
   <!-- Bad -->
   <input name="email" />

   <!-- Good -->
   <label for="email">Email</label>
   <input id="email" name="email" />
   ```

## Performance

### Test Speed

- Average test: 2-5 seconds
- Full suite: 2-5 minutes (parallel)
- With retries: Up to 15 minutes

### Optimization Tips

1. **Run in parallel**
   - Configured in `playwright.config.ts`
   - Default: All available CPU cores

2. **Use test fixtures**
   - Reuse authentication state
   - Avoid redundant setup

3. **Limit browser instances**
   - CI: 1 worker (sequential)
   - Local: Unlimited (parallel)

4. **Skip slow tests locally**
   ```typescript
   test.skip(process.env.CI !== 'true', 'slow test')
   ```

## Troubleshooting

### Tests Fail Locally but Pass in CI

- Check Node.js version (use same as CI)
- Clear Playwright cache: `npx playwright install --force`
- Check for timing issues (add explicit waits)

### Flaky Tests

- Add proper wait conditions (`waitForSelector`)
- Increase timeout for slow operations
- Check for race conditions
- Use `test.retry(2)` for known flaky tests

### Can't Find Element

- Check if element is visible (`isVisible()`)
- Wait for element to load (`waitForSelector`)
- Use more specific selector
- Check browser console for errors

### Test Users Don't Exist

- Run seed script or create users manually
- Check database connection
- Verify credentials match `fixtures.ts`

## CI Integration

### GitHub Actions

See `.github/workflows/web-ci.yml` for full workflow.

Key steps:
1. Install dependencies
2. Install Playwright browsers
3. Run E2E tests (matrix: chromium, firefox, webkit)
4. Upload reports as artifacts
5. Run accessibility tests
6. Comment on PR with results

### Artifacts

After CI run, download:
- Playwright HTML report
- Screenshots (on failure)
- Videos (on failure)
- Accessibility report

## Resources

- [Playwright Documentation](https://playwright.dev)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [axe-core Rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
