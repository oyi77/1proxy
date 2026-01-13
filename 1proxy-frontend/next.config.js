
/** @type {import('next').NextConfig} */

const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'flagcdn.com',
        pathname: '/**',
      },
    ],
  },
  experimental: {
    outputFileTracingRoot: '/Users/paijo/1proxy'
  }
}

module.exports = nextConfig
