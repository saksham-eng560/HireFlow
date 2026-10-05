import { PRIVATE_DATA_COLLECTION } from "@/lib/sentry";

// Error reporting from the browser, only when a DSN is configured (docs/DEPLOY.md): no session replay, no
// personal data. The SDK is loaded on demand, so a deployment without Sentry doesn't download it at all.
type TransitionHook = (href: string, navigationType: string) => void;
let captureTransition: TransitionHook | undefined;

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
if (dsn) {
  void import("@sentry/nextjs").then((Sentry) => {
    Sentry.init({
      dsn,
      environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || process.env.NODE_ENV,
      tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE || 0.1),
      dataCollection: { ...PRIVATE_DATA_COLLECTION, httpBodies: [] },
    });
    captureTransition = Sentry.captureRouterTransitionStart;
  });
}

/** Page-to-page navigations, for Sentry's performance view (a no-op until the SDK has loaded). */
export const onRouterTransitionStart: TransitionHook = (href, navigationType) => captureTransition?.(href, navigationType);
