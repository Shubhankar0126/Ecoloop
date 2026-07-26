import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const dashboardRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  reactStrictMode: true,
  typedRoutes: true,
  outputFileTracingRoot: dashboardRoot
};

export default nextConfig;
