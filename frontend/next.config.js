/** @type {import('next').NextConfig} */
const { withSentryConfig } = require("@sentry/nextjs/config");

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
if (process.env.VERCEL && !process.env.BACKEND_URL) {
  // On Vercel, localhost is nothing: every API call would fail until BACKEND_URL is set (docs/DEPLOY.md)
  console.warn("\n⚠ BACKEND_URL is not set: the dashboard has no API to talk to. Set it and redeploy.\n");
}

const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  poweredByHeader: false,
  experimental: {
    // A local AI model (Ollama) without a GPU can take minutes to answer (resume parsing, Test AI);
    // Next's default 30 s proxy timeout would cut those /api requests off.
    proxyTimeout: 15 * 60 * 1000,
  },
  // Same-origin proxy (BFF): the browser only talks to the dashboard's origin, so the
  // httpOnly session cookie is first-party in every deployment topology.
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${BACKEND_URL}/api/v1/:path*` },
      { source: "/docs", destination: `${BACKEND_URL}/docs` },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
        ],
      },
    ];
  },
};

// Sentry: errors are reported only when NEXT_PUBLIC_SENTRY_DSN / SENTRY_DSN are set (see src/instrumentation*.ts);
// source maps are uploaded only when SENTRY_AUTH_TOKEN (+ SENTRY_ORG, SENTRY_PROJECT) is set at build time.
module.exports = withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  sourcemaps: { disable: !process.env.SENTRY_AUTH_TOKEN },
  silent: !process.env.CI,
  telemetry: false,
});
