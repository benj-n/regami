# Storybook Component Library

Interactive component documentation and testing for Regami React components.

## What is Storybook?

Storybook is a development environment for UI components. It allows you to:
- Browse component library
- View different component states
- Develop components in isolation
- Test components interactively
- Document component APIs
- Share components with team

## Installation

Storybook dependencies should be installed automatically. If not:

```bash
cd web
npm install --save-dev @storybook/react-vite @storybook/addon-essentials \
  @storybook/addon-interactions @storybook/addon-a11y @chromatic-com/storybook
```

## Usage

### Run Storybook Development Server

```bash
cd web
npm run storybook
```

Opens at http://localhost:6006

### Build Static Storybook

```bash
cd web
npm run build-storybook
```

Outputs to `web/storybook-static/`

## Creating Stories

### Basic Story

Create a file `src/components/MyComponent.stories.tsx`:

```typescript
import type { Meta, StoryObj } from '@storybook/react';
import MyComponent from './MyComponent';

const meta = {
  title: 'Components/MyComponent',
  component: MyComponent,
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
} satisfies Meta<typeof MyComponent>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    // component props
  },
};
```

### Story with Multiple Variants

```typescript
export const Primary: Story = {
  args: {
    variant: 'primary',
    label: 'Click me',
  },
};

export const Secondary: Story = {
  args: {
    variant: 'secondary',
    label: 'Click me',
  },
};

export const Disabled: Story = {
  args: {
    disabled: true,
    label: 'Disabled',
  },
};
```

### Story with Interactions

```typescript
import { within, userEvent } from '@storybook/test';

export const WithInteraction: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const button = canvas.getByRole('button');
    await userEvent.click(button);
  },
};
```

## Component Categories

Organize stories by category using the `title` field:

- `Components/Forms` - Form inputs, buttons, checkboxes
- `Components/Layout` - Headers, footers, sidebars
- `Components/Navigation` - Menus, breadcrumbs, tabs
- `Components/Feedback` - Alerts, modals, tooltips
- `Components/Data` - Tables, lists, cards
- `Pages` - Full page compositions

## Addons

### Essentials (Included)

- **Controls**: Dynamically edit props
- **Actions**: Log event handlers
- **Viewport**: Test responsive designs
- **Backgrounds**: Change background colors
- **Toolbars**: Custom toolbar buttons

### Accessibility (a11y)

Check accessibility issues in real-time:

```typescript
export const WithA11y: Story = {
  parameters: {
    a11y: {
      element: '#root',
      config: {
        rules: [
          { id: 'color-contrast', enabled: true },
        ],
      },
    },
  },
};
```

## Best Practices

### 1. Cover All States

Create stories for:
- Default state
- Loading state
- Error state
- Empty state
- Disabled state

### 2. Use Args

Pass data via `args` instead of hardcoding:

```typescript
// Good
export const Default: Story = {
  args: {
    title: 'Hello',
  },
};

// Avoid
export const Default: Story = {
  render: () => <Component title="Hello" />,
};
```

### 3. Document Props

Use JSDoc comments on component props:

```typescript
interface ButtonProps {
  /** Button label text */
  label: string;
  /** Button variant style */
  variant?: 'primary' | 'secondary';
  /** Click handler */
  onClick?: () => void;
}
```

Storybook will automatically generate documentation.

### 4. Mock API Calls

Use Mock Service Worker (MSW) for API mocking:

```typescript
import { http, HttpResponse } from 'msw';

export const WithApiData: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get('/api/users', () => {
          return HttpResponse.json([
            { id: 1, name: 'Alice' },
            { id: 2, name: 'Bob' },
          ]);
        }),
      ],
    },
  },
};
```

### 5. Test Interactions

Add interaction tests using `play` function:

```typescript
export const FilledForm: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);

    await userEvent.type(canvas.getByLabelText('Email'), 'test@example.com');
    await userEvent.type(canvas.getByLabelText('Password'), 'password123');
    await userEvent.click(canvas.getByRole('button', { name: /submit/i }));
  },
};
```

## Deployment

### Deploy to Chromatic

Chromatic provides free hosting for Storybook with visual regression testing:

```bash
npx chromatic --project-token=YOUR_TOKEN
```

### Deploy to GitHub Pages

```bash
npm run build-storybook
gh-pages -d storybook-static
```

### Deploy to Netlify/Vercel

1. Build: `npm run build-storybook`
2. Publish directory: `storybook-static`

## Integration with CI/CD

Add to GitHub Actions workflow:

```yaml
- name: Build Storybook
  run: |
    cd web
    npm run build-storybook

- name: Run Storybook Tests
  run: |
    cd web
    npm run test-storybook
```

## Troubleshooting

### Storybook not loading components

Check that imports resolve correctly:
- Use absolute imports with `@/` prefix
- Verify `tsconfig.json` paths configuration

### Styles not working

Ensure CSS is imported in `.storybook/preview.ts`:

```typescript
import '../src/index.css';
```

### TypeScript errors

Update `.storybook/main.ts`:

```typescript
framework: {
  name: '@storybook/react-vite',
  options: {
    builder: {
      viteConfigPath: '../vite.config.ts',
    },
  },
},
```

## Resources

- [Storybook Documentation](https://storybook.js.org/docs)
- [Storybook for React](https://storybook.js.org/docs/react/get-started/introduction)
- [Component Story Format (CSF)](https://storybook.js.org/docs/react/api/csf)
- [Storybook Addons](https://storybook.js.org/addons)
