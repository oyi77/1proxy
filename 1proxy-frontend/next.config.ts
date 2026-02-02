import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for GitHub Pages deployment
  output: 'export',
  
  // Set empty basePath and handle pathing in post-build script
  // This produces standard paths that are easy to make relative/portable
  basePath: '',
  
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
