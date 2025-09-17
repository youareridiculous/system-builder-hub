/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true
  },
  env: {
    SBH_API_URL: process.env.SBH_API_URL || 'https://sbh.umbervale.com'
  }
}

module.exports = nextConfig
