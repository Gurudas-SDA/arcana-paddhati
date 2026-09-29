import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  basePath: '/arcana-paddhati',
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
