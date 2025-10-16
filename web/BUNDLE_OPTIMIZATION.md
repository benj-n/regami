# Bundle Size Optimization Guide

## Overview

This project uses code splitting, lazy loading, and bundle analysis to optimize the web frontend bundle size for faster load times.

## Bundle Strategy

### Code Splitting

Routes are lazy-loaded using `React.lazy()` and `Suspense`:

```tsx
const Dogs = lazy(() => import('./pages/Dogs'))
const Messages = lazy(() => import('./pages/Messages'))
```

**Benefits:**
- Initial bundle only loads authentication pages
- Other pages load on-demand when navigated to
- Faster initial page load (especially on mobile)

### Vendor Chunks

Large dependencies are split into separate chunks for better caching:

- `react-vendor`: React core libraries
- `map-vendor`: Leaflet mapping libraries
- `form-vendor`: Form handling (react-hook-form, zod)
- `date-vendor`: Date utilities (date-fns, react-datepicker)

**Benefits:**
- Vendor code changes infrequently → better cache hit rate
- Users download vendor bundle once, then use cached version
- App code updates don't invalidate vendor cache

## Bundle Analysis

### Generate Bundle Report

```bash
# Build with bundle analysis
npm run build

# View bundle visualization
open dist/stats.html
```

The report shows:
- Size of each chunk (gzipped and brotli)
- Which files are in which chunks
- Dependency relationships
- Large dependencies to optimize

### Bundle Size Targets

| Bundle Type | Target Size (Gzipped) | Warning Threshold |
|-------------|----------------------|-------------------|
| Initial JS  | < 150 KB             | 200 KB            |
| Initial CSS | < 30 KB              | 50 KB             |
| Vendor chunks | < 200 KB each       | 300 KB            |
| Route chunks  | < 50 KB each        | 100 KB            |

### Current Bundle Sizes

Run `npm run build` and check console output:

```
dist/assets/index-abc123.js      45.2 kB │ gzip: 15.8 kB
dist/assets/react-vendor-def456.js   156.3 kB │ gzip: 52.1 kB
dist/assets/map-vendor-ghi789.js     87.4 kB │ gzip: 28.3 kB
...
```

## Optimization Techniques

### 1. Lazy Loading (Implemented)

**Pages:** All routes are lazy-loaded
**Heavy Components:** Can be lazy-loaded on-demand

Example:
```tsx
const HeavyMap = lazy(() => import('./components/Map'))

// Use with Suspense
<Suspense fallback={<div>Loading map...</div>}>
  {showMap && <HeavyMap />}
</Suspense>
```

### 2. Tree Shaking (Automatic)

Vite automatically removes unused code:

```tsx
// Good: Import only what you need
import { format } from 'date-fns'

// Avoid: Imports entire library
import * as dateFns from 'date-fns'
```

### 3. Dynamic Imports (Recommended)

For components used conditionally:

```tsx
// Before: Always in bundle
import { DatePicker } from 'react-datepicker'

// After: Load only when needed
const showDatePicker = async () => {
  const { DatePicker } = await import('react-datepicker')
  // Use DatePicker
}
```

### 4. Image Optimization

Images are often the largest assets:

```tsx
// Use modern formats (WebP, AVIF)
<img src="photo.webp" alt="Dog" />

// Lazy load images below the fold
<img loading="lazy" src="photo.jpg" alt="Dog" />

// Use responsive images
<img
  srcSet="photo-320w.jpg 320w, photo-640w.jpg 640w"
  sizes="(max-width: 640px) 100vw, 640px"
  src="photo-640w.jpg"
  alt="Dog"
/>
```

### 5. Remove Duplicate Dependencies

Check for duplicate packages:

```bash
npm ls <package-name>
```

If multiple versions exist, use `npm dedupe` or update to consistent versions.

### 6. Production Optimizations (Configured)

- **Minification**: Terser removes whitespace, shortens names
- **Drop console**: `console.log` removed in production
- **Compression**: Gzip and Brotli for smaller transfer sizes

## CI Integration

### GitHub Actions Bundle Size Check

Add to `.github/workflows/web-ci.yml`:

```yaml
- name: Build web frontend
  run: |
    cd web
    npm run build

- name: Check bundle size
  run: |
    cd web
    # Check if any JS bundle exceeds 500KB (gzipped)
    find dist/assets -name '*.js' -size +500k -print -quit | grep -q . && echo "Bundle too large!" && exit 1 || echo "Bundle size OK"

- name: Upload bundle stats
  uses: actions/upload-artifact@v3
  with:
    name: bundle-stats
    path: web/dist/stats.html
```

### Bundle Size Bot (Optional)

Use [bundlesize](https://github.com/siddharthkp/bundlesize) or [size-limit](https://github.com/ai/size-limit) for PR comments:

```json
{
  "bundlesize": [
    {
      "path": "dist/assets/*.js",
      "maxSize": "200 kB"
    }
  ]
}
```

## Monitoring in Production

### 1. Web Vitals

Monitor real user metrics:

```tsx
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals'

getCLS(console.log)
getFID(console.log)
getFCP(console.log)
getLCP(console.log)
getTTFB(console.log)
```

### 2. Lighthouse CI

Automate Lighthouse audits:

```yaml
- name: Lighthouse CI
  uses: treosh/lighthouse-ci-action@v9
  with:
    urls: |
      https://staging.regami.com
    uploadArtifacts: true
```

### 3. CloudFront Metrics

Monitor CDN performance:
- Cache hit rate (target: >80%)
- Origin response time
- Bytes downloaded per request

## Troubleshooting

### Large Bundle Warnings

If you see warnings like "chunk size exceeds 500 KB":

1. Check `dist/stats.html` to identify the large dependency
2. Consider alternatives:
   - Leaflet maps: Already in separate chunk ✓
   - Date libraries: Use native `Intl.DateTimeFormat` instead
   - Icon libraries: Import only needed icons
3. Split large chunks further with dynamic imports

### Slow Initial Load

If initial load is slow:

1. Check Network tab in DevTools
2. Verify lazy loading is working (chunks load on navigation)
3. Enable compression on server (Gzip/Brotli)
4. Use CDN for static assets (CloudFront)
5. Implement service worker for caching

### Cache Busting Not Working

Vite adds content hashes to filenames automatically:
- `index-abc123.js` changes when content changes
- Users always get the latest version
- Old versions cached until content changes

## Best Practices

### Do's

- Use `React.lazy()` for route components
- Split vendor libraries into separate chunks
- Use `loading="lazy"` for images
- Import only what you need from libraries
- Monitor bundle size in CI
- Analyze bundle regularly with visualizer

### Don'ts

- Don't import entire libraries (`import *`)
- Don't inline large dependencies
- Don't load all routes eagerly
- Don't skip bundle analysis
- Don't ignore bundle size warnings

## Resources

- [Vite Code Splitting](https://vitejs.dev/guide/build.html#chunking-strategy)
- [React Code Splitting](https://react.dev/reference/react/lazy)
- [Web.dev: Reduce JavaScript Payloads](https://web.dev/reduce-javascript-payloads-with-code-splitting/)
- [Bundle Phobia](https://bundlephobia.com/) - Check package sizes before installing
