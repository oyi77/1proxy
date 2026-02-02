import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for GitHub Pages deployment
  output: 'export',
  
  // BasePath is essential for the Next.js runtime to handle subdirectories
  // Default to /1proxy for oyi77.is-a.dev/1proxy deployment
  basePath: process.env.NEXT_PUBLIC_BASE_PATH || '/1proxy',
  
  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },
  
  typescript: {
    tsconfigPath: './tsconfig.json',
  },
  
  experimental: {
    turbo: {
      resolveExtensions: ['.web.tsx', '.web.ts', '.tsx', '.ts', '.web.js', '.js'] as any,
    } as any,
  },
};

export default nextConfig;
