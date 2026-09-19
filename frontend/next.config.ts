import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    if (process.env.VERCEL) {
      return [];
    }
    const veilBackend = (process.env.VEIL_BACKEND_URL || "http://127.0.0.1:8000").replace(
      /\/$/,
      ""
    );
    return [
      {
        source: "/veil-api/:path*",
        destination: `${veilBackend}/:path*`,
      },
    ];
  },
};

export default nextConfig;
