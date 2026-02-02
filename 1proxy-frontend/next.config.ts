import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for GitHub Pages deployment
  output: 'export',
  
  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },
  
  // Remove basePath for simpler deployment
  // Will deploy to: https://username.github.io/1proxy/
  // basePath: '/1proxy',
  
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
