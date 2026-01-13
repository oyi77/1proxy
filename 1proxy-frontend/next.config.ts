import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  typescript: {
    tsconfigPath: './tsconfig.json',
  },
};

export default nextConfig;
