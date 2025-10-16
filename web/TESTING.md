# Web Frontend Testing & Quality Assurance

## Overview

The Regami web frontend has comprehensive testing and quality assurance implemented:

- **E2E Testing** - Playwright tests for critical user flows
- **Code Coverage** - 80% minimum threshold with automated tracking
- **Accessibility** - WCAG 2.1 AA compliance testing
- **Bundle Optimization** - Lazy loading and code splitting
- **CI/CD** - Automated testing on every commit

---

## Quick Start

```bash
# Install dependencies
npm install

# Install Playwright browsers (first time only)
npx playwright install

# Run all tests
npm test                    # Unit tests
npm run test:coverage       # Unit tests with coverage
npm run test:e2e           # E2E tests
npm run test:a11y          # Accessibility tests

# Build and analyze bundle
npm run build
npm run analyze
```

---

## Test Suites

### 1. Unit Tests (Vitest)

**Location:** `src/__tests__/`
**Framework:** Vitest + React Testing Library
**Coverage:** 80% minimum threshold

```bash
# Run unit tests
npm test

# Run with coverage
npm run test:coverage

# View coverage report
open coverage/index.html
```

**What's tested:**
- Component rendering
- User interactions
- State management
- API service functions
- Utility functions

**Documentation:** [COVERAGE.md](./COVERAGE.md)

---

### 2. E2E Tests (Playwright)

**Location:** `e2e/`
**Framework:** Playwright
**Browsers:** Chromium, Firefox, WebKit, Mobile

```bash
# Run E2E tests
npm run test:e2e

# Run with browser UI
npm run test:e2e:headed

# Run with Playwright UI (debugging)
npm run test:e2e:ui

# Run specific test
npx playwright test auth.spec.ts
```

**What's tested:**
- User authentication (register, login, logout)
- Dog profile management (CRUD, photos)
- Matching flows (offers, requests, confirmations)
- Messaging (conversations, send, read)
- Navigation and routing

**Documentation:** [e2e/README.md](./e2e/README.md)

---

### 3. Accessibility Tests (axe-core)

**Location:** `e2e/accessibility.spec.ts`
**Framework:** @axe-core/playwright
**Standard:** WCAG 2.1 AA

```bash
# Run a11y tests
npm run test:a11y

# View results
open playwright-report/index.html
```

**What's tested:**
- Color contrast ratios
- Keyboard navigation
- ARIA labels and roles
- Form labels and associations
- Semantic HTML structure
- Screen reader support

**Documentation:** [e2e/README.md](./e2e/README.md#accessibility-testing)

---

## Bundle Optimization

**Tools:** Vite + rollup-plugin-visualizer
**Target:** < 200KB initial bundle (gzipped)

```bash
# Build with bundle analysis
npm run build

# View bundle visualization
open dist/stats.html
```

**Optimizations implemented:**
- Lazy loading for all routes
- Vendor chunking (React, Leaflet, forms, dates)
- Tree-shaking
- Minification (Terser)
- Console.log removal in production
- Source maps for debugging

**Documentation:** [BUNDLE_OPTIMIZATION.md](./BUNDLE_OPTIMIZATION.md)

---

## CI/CD Pipeline

**Workflow:** `.github/workflows/web-ci.yml`
**Triggers:** Push to main/develop, Pull Requests

### Pipeline Stages

1. **Lint and Test** (3-5 min)
   - Run unit tests with coverage
   - Upload coverage to Codecov
   - Enforce 80% threshold

2. **Build** (2-3 min)
   - Production build
   - Bundle size check
   - Upload bundle stats

3. **E2E Tests** (5-10 min)
   - Matrix: Chromium, Firefox, WebKit
   - Upload Playwright reports
   - Screenshot/video on failure

4. **Accessibility** (2-3 min)
   - WCAG 2.1 AA compliance
   - Upload a11y reports

5. **PR Comment**
   - Coverage summary
   - Bundle size info
   - Links to artifacts

**Total time:** 10-20 minutes

---

## Coverage Requirements

### Thresholds

| Metric      | Threshold | Current |
|-------------|-----------|---------|
| Lines       | 80%       | TBD     |
| Functions   | 80%       | TBD     |
| Branches    | 75%       | TBD     |
| Statements  | 80%       | TBD     |

### Exclusions

- `node_modules/` - Third-party code
- `dist/` - Build output
- `e2e/` - E2E tests (tested separately)
- `**/*.config.ts` - Configuration files
- `**/__tests__/**` - Test files themselves

---

## Development Workflow

### Before Committing

```bash
# 1. Run tests locally
npm test

# 2. Check coverage (optional but recommended)
npm run test:coverage

# 3. Run E2E tests for critical changes
npm run test:e2e:headed

# 4. Check accessibility for UI changes
npm run test:a11y

# 5. Verify bundle size for new dependencies
npm run build && ls -lh dist/assets/*.js
```

### During PR Review

- CI pipeline must pass
- Coverage must be >= 80%
- No accessibility violations
- Bundle size within limits
- E2E tests pass on all browsers

---

## Test Data

E2E tests require test users in the database:

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

**Setup:**
```bash
# Option 1: Seed script
cd backend && python scripts/seed_test_users.py

# Option 2: Manual registration
# Visit http://localhost:5173/register and create users

# Option 3: API calls
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test-owner@regami.com","password":"TestPassword123!","name":"Test Owner","role":"owner"}'
```

---

## Debugging

### Unit Tests

```bash
# Run tests in watch mode
npm test

# Run specific test file
npm test Dogs.test.tsx

# Run tests matching pattern
npm test -- -t "should render"
```

### E2E Tests

```bash
# Playwright UI (best for debugging)
npm run test:e2e:ui

# Debug mode (step-through)
npx playwright test --debug

# Run with trace
npx playwright test --trace on
npx playwright show-trace trace.zip
```

### Coverage

```bash
# Generate coverage report
npm run test:coverage

# Open HTML report
open coverage/index.html

# Check specific file coverage
open coverage/index.html#file=/src/components/Dogs.tsx
```

---

## Common Issues

### E2E Tests Failing

1. **Test users don't exist**
   - Solution: Run seed script or create users manually

2. **Flaky tests**
   - Solution: Add proper wait conditions, avoid `waitForTimeout`

3. **Browser not found**
   - Solution: `npx playwright install --force`

### Coverage Below Threshold

1. **Identify gaps**
   - Open `coverage/index.html`
   - Look for red lines (untested code)

2. **Add tests**
   - Focus on high-value code (business logic, utilities)
   - Don't chase 100% coverage

3. **Adjust thresholds** (if needed)
   - Edit `vitest.config.ts` → `coverage.thresholds`

### Bundle Too Large

1. **Identify culprits**
   - Run `npm run build`
   - Open `dist/stats.html`

2. **Optimize**
   - Use dynamic imports for large components
   - Check for duplicate dependencies
   - Consider lighter alternatives

3. **Monitor**
   - CI warns if bundle > 500KB

---

## Best Practices

### Testing

**Do:**
- Test user behavior, not implementation
- Use semantic selectors (text, role, label)
- Keep tests independent and isolated
- Use fixtures for common setup
- Test critical paths with E2E
- Test edge cases with unit tests

**Don't:**
- Test internal component state
- Use fragile CSS selectors
- Rely on previous test state
- Over-test simple components
- Skip accessibility testing

### Coverage

**Do:**
- Focus on high-value code
- Use coverage to find gaps
- Review HTML reports
- Maintain 80%+ coverage

**Don't:**
- Chase 100% coverage
- Test trivial code
- Skip error paths
- Ignore coverage drops

### Bundle Size

**Do:**
- Lazy load routes
- Split vendor chunks
- Use tree-shakeable imports
- Monitor bundle size

**Don't:**
- Import entire libraries
- Skip bundle analysis
- Ignore size warnings
- Inline large dependencies

---

## Resources

### Documentation
- [Coverage Guide](./COVERAGE.md)
- [E2E Testing Guide](./e2e/README.md)
- [Bundle Optimization](./BUNDLE_OPTIMIZATION.md)

### External Resources
- [Playwright Docs](https://playwright.dev)
- [Vitest Docs](https://vitest.dev)
- [axe-core Rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)
- [WCAG Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Web Vitals](https://web.dev/vitals/)

---

## Metrics & Goals

### Current Status

| Metric            | Target  | Status |
|-------------------|---------|--------|
| Unit Test Coverage | 80%     | Done   |
| E2E Test Coverage  | Critical paths | Done   |
| A11y Compliance    | WCAG AA | Done   |
| Bundle Size        | < 200KB | Done   |
| CI Pipeline        | < 20min | Done   |

### Future Improvements

- [ ] Visual regression testing (Percy/Chromatic)
- [ ] Performance monitoring (web-vitals)
- [ ] Load testing (k6/Artillery)
- [ ] Service worker (PWA)
- [ ] Further bundle optimization

---

## Support

For questions or issues:
1. Check documentation in this directory
2. Review CI logs in GitHub Actions
3. Open issue with `web-frontend` label
4. Ask in `#frontend` Slack channel
