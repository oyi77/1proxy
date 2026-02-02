import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for GitHub Pages deployment
  output: 'export',
  
  // Note: basePath is NOT used here because we handle path prefixing
  // in the post-build script (scripts/gh-pages-export.js)
  // This allows proper static export while still supporting subdirectory deployment
  
  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },
  
  typescript: {
    tsconfigPath: './tsconfig.json',
  },
  
  // Suppress Turbopack workspace detection warning when parent dirs have lockfiles
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  experimental: {
    turbo: {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      resolveExtensions: ['.web.tsx', '.web.ts', '.tsx', '.ts', '.web.js', '.js'] as any,
    } as any,
  },
};

export default nextConfig;
