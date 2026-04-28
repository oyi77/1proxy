import type { NextConfig } from "next";

const nextOutput = process.env.NEXT_OUTPUT;
const isStandalone = nextOutput === "standalone";

const basePath = isStandalone
  ? process.env.NEXT_PUBLIC_BASE_PATH ?? ""
  : process.env.NEXT_PUBLIC_BASE_PATH ?? "/1proxy";

const nextConfig: NextConfig = {
  // GitHub Pages uses static export under /1proxy.
  // Docker/local runtime uses standalone output at /.
  output: isStandalone ? "standalone" : "export",
  basePath,
  
  // Disable image optimization for static export
  images: {
    unoptimized: true,
  },
  
  typescript: {
    tsconfigPath: './tsconfig.json',
  },
  
  outputFileTracingRoot: process.cwd(),

  turbopack: {
    resolveExtensions: ['.web.tsx', '.web.ts', '.tsx', '.ts', '.web.js', '.js'],
  },
};

export default nextConfig;
