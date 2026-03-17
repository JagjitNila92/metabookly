/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      // Seed catalog placeholder covers
      { protocol: 'https', hostname: 'covers.seed.dev' },
      // Real cover image CDNs (add more as needed)
      { protocol: 'https', hostname: '*.amazonaws.com' },
      { protocol: 'https', hostname: 'covers.openlibrary.org' },
      { protocol: 'https', hostname: '*.googleapis.com' },
    ],
  },
}

export default nextConfig
