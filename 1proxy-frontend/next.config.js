
/** @type {import('next').NextConfig} */

const isStandalone = process.env.NEXT_OUTPUT === 'standalone'

// GitHub Pages uses static export under /1proxy.
// Docker/local runtime uses standalone output at /.
const basePath = isStandalone
  ? (process.env.NEXT_PUBLIC_BASE_PATH ?? '')
  : (process.env.NEXT_PUBLIC_BASE_PATH ?? '/1proxy')

const nextConfig = {
  output: isStandalone ? 'standalone' : 'export',
  basePath,

  images: {
    // Static export can't use Next.js image optimization.
    unoptimized: !isStandalone,
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'flagcdn.com',
        pathname: '/**',
      },
    ],
  },

  outputFileTracingRoot: undefined,
}

module.exports = nextConfig
