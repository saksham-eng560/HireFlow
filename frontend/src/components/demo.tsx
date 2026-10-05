"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { FlaskConical, Sparkles } from "lucide-react";
import { Button, type ButtonProps } from "@/components/ui/button";
import { ApiError, fetcher, post } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export interface AuthConfig {
  google_enabled: boolean;
  registration_enabled: boolean;
  demo_mode?: boolean;
}

export function useAuthConfig() {
  return useSWR<AuthConfig>("/auth/config", fetcher, { revalidateOnFocus: false });
}

/** Set on the public demo's dashboard build: show "Try the demo" before (or without) the API's answer. */
const DEMO_SITE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

/** "Try the demo": one click signs in to the shared demo account (shown when the server runs the demo). On the
 * public demo's build it shows straight away, so the main button never vanishes while the API wakes up or is down:
 * clicking it then says the server can't be reached. */
export function TryDemoButton({ className, size = "lg", variant = "outline", label = "Try the demo" }: {
  className?: string;
  size?: ButtonProps["size"];
  variant?: ButtonProps["variant"];
  label?: string;
}) {
  const router = useRouter();
  const { data: config } = useAuthConfig();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!(config ? config.demo_mode : DEMO_SITE)) return null;
  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      await post("/auth/demo");
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't open the demo. Try again in a moment.");
      setBusy(false);
    }
  };
  return (
    <span className={cn("inline-flex flex-col gap-1", className)}>
      <Button type="button" size={size} variant={variant} loading={busy} onClick={start}>
        {!busy && <Sparkles />} {label}
      </Button>
      {error && <span role="alert" className="text-xs text-destructive">{error}</span>}
    </span>
  );
}

/** On every dashboard page in the demo, so nobody mistakes it for the real thing. */
export function DemoBanner() {
  const { data: config } = useAuthConfig();
  if (!config?.demo_mode) return null;
  return (
    <div role="note" className="flex items-center gap-2 border-b border-primary/20 bg-secondary px-4 py-2 text-xs text-secondary-foreground sm:text-sm lg:px-8">
      <FlaskConical className="h-4 w-4 shrink-0 text-primary" aria-hidden />
      <p><span className="font-semibold">Demo — nothing is really sent.</span> Applications go to a sample careers site with
        fictional companies, and everything resets every night.</p>
    </div>
  );
}

/** For settings that can't work in the demo (Google, the extension, job-site logins, passwords). */
export function DemoNotice({ children }: { children: React.ReactNode }) {
  const { data: config } = useAuthConfig();
  if (!config?.demo_mode) return null;
  return (
    <p role="note" className="mb-4 flex items-start gap-2 rounded-lg bg-secondary px-3 py-2 text-sm text-secondary-foreground">
      <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden /> <span>{children}</span>
    </p>
  );
}
