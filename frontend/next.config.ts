import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  // Hide the floating Next.js badge shown during development. It sits in
  // the bottom-left corner, exactly on top of the "Home" tab of the mobile
  // navigation bar. Build and runtime errors are still shown.
  devIndicators: false,
  // Where build output goes. The browser tests build into their own folder
  // (.next-e2e) so they never overwrite a build you made yourself.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  experimental: {
    // In development Next.js warns when a page cannot appear instantly.
    // Every signed-in page waits, on purpose, until the account has loaded,
    // so that warning would fire on all of them. "manual-warning" limits
    // the check to pages that ask for it with `export const instant = true`.
    instantInsights: {
      validationLevel: "manual-warning",
    },
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
