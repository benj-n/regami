# Code Coverage Guide

## Overview

This project uses Vitest with V8 coverage provider to track test coverage. Coverage reports help ensure code quality and identify untested code paths.

## Running Coverage

```bash
# Run tests with coverage
npm run test:coverage

# View HTML report (opens in browser)
open coverage/index.html
```

## Coverage Thresholds

The project enforces minimum coverage thresholds:

- **Lines**: 80%
- **Functions**: 80%
- **Branches**: 75%
- **Statements**: 80%

Builds will fail in CI if coverage falls below these thresholds.

## Coverage Reports

Multiple report formats are generated:

- **Text**: Console output showing coverage summary
- **HTML**: Interactive browser-based report (`coverage/index.html`)
- **JSON**: Machine-readable format for CI tools (`coverage/coverage-final.json`)
- **LCOV**: Standard format for coverage tools (`coverage/lcov.info`)

## What's Excluded

The following are excluded from coverage requirements:

- `node_modules/` - Third-party dependencies
- `dist/` - Build output
- `e2e/` - End-to-end tests (tested via Playwright)
- `**/*.config.{ts,js}` - Configuration files
- `**/*.d.ts` - TypeScript declaration files
- `**/__tests__/**` - Test files themselves
- `vitest.setup.ts` - Test setup

## CI Integration

### GitHub Actions

Add coverage reporting to your CI workflow:

```yaml
- name: Run tests with coverage
  run: npm run test:coverage

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: ./web/coverage/lcov.info
    flags: web-frontend
    name: web-coverage
```

### Coverage Badge

Add a coverage badge to your README:

```markdown
[![codecov](https://codecov.io/gh/YOUR_ORG/regami/branch/main/graph/badge.svg?flag=web-frontend)](https://codecov.io/gh/YOUR_ORG/regami)
```

## Best Practices

### 1. Test What Matters

Focus coverage on:
- Business logic and utilities
- Complex component interactions
- Error handling paths
- Edge cases

### 2. Don't Chase 100%

100% coverage doesn't guarantee bug-free code. Focus on:
- Critical user paths
- Complex logic
- Error scenarios

### 3. Review Coverage Reports

Regularly review HTML reports to identify:
- Untested code paths
- Dead code (can be removed)
- Complex functions needing more tests

### 4. Use Coverage as a Guide

Coverage metrics are indicators, not goals:
- **80%+ coverage**: Good starting point
- **90%+ coverage**: Excellent
- **100% coverage**: Often not worth the effort

### 5. Watch for Coverage Drops

Set up PR comments showing coverage changes:
- Highlight new untested code
- Prevent coverage regressions
- Encourage testing new features

## Common Issues

### Coverage Too Low

If coverage is below thresholds:

1. Identify uncovered lines: `npm run test:coverage`
2. Open `coverage/index.html` to see which files need tests
3. Add unit tests for uncovered components/functions
4. Focus on high-value code first (business logic, utilities)

### False Positives

Some code may be correctly tested but show as uncovered:
- Type guards (covered by TypeScript)
- Default props (covered by React)
- Error handling for impossible states

Consider excluding these from coverage or adjusting thresholds.

### Slow Coverage Collection

V8 coverage is fast, but if tests are slow:
- Run coverage only in CI
- Use `--changed` flag in development
- Optimize slow tests

## Development Workflow

### Local Development

```bash
# Quick test without coverage
npm test

# Full test suite with coverage (before commit)
npm run test:coverage
```

### Before Pushing

```bash
# Ensure all tests pass with coverage
npm run test:coverage

# Review HTML report for any issues
open coverage/index.html
```

### In Pull Requests

Coverage reports will be:
1. Generated in CI
2. Uploaded to Codecov
3. Commented on PR with diff
4. Used to block merge if below threshold

## Troubleshooting

### Coverage Not Generated

Check that:
- `@vitest/coverage-v8` is installed
- `vitest.config.ts` has coverage configuration
- Tests are running successfully

### Coverage Reports Empty

Ensure:
- Test files use `.test.tsx` or `.test.ts` extension
- Coverage isn't excluding too much
- Tests are actually executing code

### Threshold Failures in CI

If CI fails on coverage thresholds:
1. Check which threshold failed (lines/functions/branches/statements)
2. Review coverage report to see uncovered code
3. Add tests to cover critical paths
4. Consider if threshold is too strict for your project phase

## References

- [Vitest Coverage Documentation](https://vitest.dev/guide/coverage.html)
- [V8 Coverage Provider](https://v8.dev/blog/javascript-code-coverage)
- [Codecov Documentation](https://docs.codecov.com/)
