"use client";

import { useEffect, useState } from "react";

import { getHealth, type HealthResponse } from "@/lib/api";

type Status =
  | { kind: "loading" }
  | { kind: "ok"; health: HealthResponse }
  | { kind: "error"; message: string };

export default function BackendStatus() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    getHealth(controller.signal)
      .then((health) => setStatus({ kind: "ok", health }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setStatus({
          kind: "error",
          message: err instanceof Error ? err.message : "Backend unreachable",
        });
      });
    return () => controller.abort();
  }, []);

  if (status.kind === "loading") {
    return <StatusPill tone="muted" text="Checking backend…" />;
  }
  if (status.kind === "error") {
    return <StatusPill tone="error" text="Backend offline" title={status.message} />;
  }
  const { version, vlm_backend } = status.health;
  return <StatusPill tone="ok" text={`Backend v${version} · VLM: ${vlm_backend}`} />;
}

const TONES = {
  muted: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
  ok: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  error: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
} as const;

function StatusPill({
  tone,
  text,
  title,
}: {
  tone: keyof typeof TONES;
  text: string;
  title?: string;
}) {
  return (
    <span
      role="status"
      title={title}
      className={`rounded-full px-3 py-1 text-xs font-medium ${TONES[tone]}`}
    >
      {text}
    </span>
  );
}
