// Typed client for the Vi-Graph FastAPI backend (spec §28).

// Inlined at build time (NEXT_PUBLIC_*). Next.js reads it from frontend/.env.local
// in development, or from the build environment (see docker-compose.yml).
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type HealthResponse = {
  status: "ok";
  version: string;
  env: string;
  vlm_backend: string;
};

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`, { signal, cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Health check failed: HTTP ${res.status}`);
  }
  return (await res.json()) as HealthResponse;
}
