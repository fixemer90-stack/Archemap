import type { NextConfig } from "next";

const defaultBackendUrl = "http://127.0.0.1:8000";
const playwrightDevOrigin = process.env.PLAYWRIGHT_BASE_URL
  ? new URL(process.env.PLAYWRIGHT_BASE_URL).hostname
  : undefined;

const nextConfig: NextConfig = {
  output: "standalone",
  allowedDevOrigins: playwrightDevOrigin ? [playwrightDevOrigin] : undefined,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL || defaultBackendUrl}/api/:path*`,
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },
};

export default nextConfig;
