import * as Sentry from "@sentry/nextjs";
import { PRIVATE_DATA_COLLECTION } from "@/lib/sentry";

/** Error reporting from the dashboard's server (Node and edge), only when a DSN is configured. */
export async function register() {
  const dsn = process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (!dsn) return;
  Sentry.init({
    dsn,
    environment: process.env.SENTRY_ENVIRONMENT || process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || process.env.NODE_ENV,
    tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE || 0.1),
    dataCollection: { ...PRIVATE_DATA_COLLECTION, httpBodies: [] },
  });
}

export const onRequestError = Sentry.captureRequestError;
