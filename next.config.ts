import type { NextConfig } from "next";

// Production: '/arcana-paddhati'. The staging build (branch `staging`, see
// .github/workflows/deploy.yml) sets NEXT_PUBLIC_BASE_PATH=/arcana-paddhati/staging.
// lib/basePath.ts and scripts/build-precache.mjs read the same variable.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || '/arcana-paddhati';

const nextConfig: NextConfig = {
  output: 'export',
  basePath,
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
