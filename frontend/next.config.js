/** @type {import('next').NextConfig} */
const nextConfig = {
  // Use standalone output for Docker deployments
  // This creates a minimal production build that can run without node_modules
  output: 'standalone',

  // React strict mode for better development experience
  reactStrictMode: true,

  // Trailing slash configuration
  trailingSlash: false,

  // Image optimization settings
  images: {
    // Disable image optimization if not using a CDN
    unoptimized: process.env.NEXT_IMAGE_OPTIMIZATION !== 'true',
  },

  // Environment variables available in the browser
  // Note: NEXT_PUBLIC_ variables are embedded at build time
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
    NEXT_PUBLIC_APP_VERSION: process.env.npm_package_version || '2.0.0',
  },

  // Webpack configuration
  webpack: (config, { isServer }) => {
    // Fix for some packages that don't work well with webpack 5
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
      };
    }
    return config;
  },

  // Headers for security
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
