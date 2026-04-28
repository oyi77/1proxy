import '@testing-library/jest-dom'
import { vi } from 'vitest'

type MockImageProps = React.ImgHTMLAttributes<HTMLImageElement> & {
  src: string;
  alt: string;
};

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn(),
  }),
  usePathname: () => '/',
}))

// Mock next/image
vi.mock('next/image', () => ({
  __esModule: true,
  default: ({ src, alt, ...props }: MockImageProps) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={alt} {...props} />
  },
}))

// Mock theme provider
vi.mock('@/app/theme-provider', () => ({
  useTheme: () => ({
    theme: 'light',
    toggleTheme: vi.fn(),
  }),
}))

// Mock fetch globally
global.fetch = vi.fn() as unknown as typeof fetch

// Mock clipboard
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: vi.fn(),
  },
})
