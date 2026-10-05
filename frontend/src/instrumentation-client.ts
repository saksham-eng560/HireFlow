import { PRIVATE_DATA_COLLECTION } from "@/lib/sentry";

// Error reporting from the browser, only when a DSN is configured (docs/DEPLOY.md): no session replay, no
// personal data. The SDK is loaded on demand, so a deployment without Sentry doesn't download it at all.
const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
if (dsn) {
  void import("@sentry/nextjs").then((Sentry) => Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || process.env.NODE_ENV,
    tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE || 0.1),
    dataCollection: { ...PRIVATE_DATA_COLLECTION, httpBodies: [] },
  }));
}
