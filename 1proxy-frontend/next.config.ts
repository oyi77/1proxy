import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for GitHub Pages deployment
  output: 'export',
  
  // BasePath is mandatory for the Next.js runtime to handle subdirectories correctly
  // This affects internal routing, chunk loading, and React Server Component fetches
  basePath: '/1proxy',
  
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
