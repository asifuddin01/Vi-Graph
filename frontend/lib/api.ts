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

// --- Canonical graph, schema v2 (spec §7) --------------------------------------------

export type GraphNode = {
  id: string;
  label: string;
  type: string;
  group_id: string | null;
  bbox?: [number, number, number, number];
  confidence?: number;
};

export type GraphEdge = {
  source: string;
  target: string;
  relation: string;
  label: string | null;
  condition: string | null;
};

export type DiagramGraph = {
  schema_version: string;
  diagram_type: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
};

// --- POST /api/analyze ---------------------------------------------------------------

export type ExtractionStatus =
  | "valid_first_attempt"
  | "valid_after_retry"
  | "repaired"
  | "failed";

export type Attempt = {
  number: number;
  valid: boolean;
  json_method: "direct" | "fenced" | "embedded" | null;
  problems: string[];
  raw_output: string;
  finish_reason: "stop" | "length" | null;
  latency_ms: number;
};

export type Change = { code: string; message: string };

export type EditedGraph = {
  version: number;
  saved_at: string;
  graph: DiagramGraph;
  mermaid: string;
  layout: Record<string, [number, number]> | null;
};

export type AnalyzeResponse = {
  diagram_id: string;
  schema_version: string;
  status: ExtractionStatus;
  graph: DiagramGraph | null;
  mermaid: string | null;
  metrics: {
    latency_ms: number;
    attempts: number;
    repairs: number;
    normalization_changes: number;
    nodes: number | null;
    edges: number | null;
    cached: boolean;
  };
  attempts: Attempt[];
  repairs: Change[];
  normalization_changes: Change[];
  failure_reason: string | null;
  model: {
    backend: string;
    model_id: string;
    revision: string | null;
    adapter_path: string | null;
  };
  image: {
    sha256: string;
    format: string;
    original_size: [number, number];
    size: [number, number];
  };
  created_at: string;
  edited: EditedGraph | null;
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    /** Specific validation problems, when the server lists them (e.g. an invalid graph). */
    readonly problems: string[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`, { signal, cache: "no-store" });
  if (!res.ok) {
    throw new ApiError(res.status, `Health check failed: HTTP ${res.status}`);
  }
  return (await res.json()) as HealthResponse;
}

export async function analyzeDiagram(
  file: File,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    body: form,
    signal,
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as AnalyzeResponse;
}

/** Save an edited graph as the analysis's next version (spec §11). */
export async function saveGraph(
  diagramId: string,
  graph: DiagramGraph,
  layout: Record<string, [number, number]>,
): Promise<EditedGraph> {
  const res = await fetch(`${API_BASE_URL}/api/analyses/${diagramId}/graph`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ graph, layout }),
  });
  if (!res.ok) throw await apiError(res);
  return (await res.json()) as EditedGraph;
}

async function apiError(res: Response): Promise<ApiError> {
  const fallback = `Request failed (HTTP ${res.status})`;
  try {
    const body: unknown = await res.json();
    if (body && typeof body === "object" && "detail" in body) {
      const { detail } = body as { detail: unknown };
      if (typeof detail === "string") return new ApiError(res.status, detail);
      if (Array.isArray(detail)) {
        const problems = detail
          .map((item) =>
            typeof item === "string"
              ? item
              : item && typeof item === "object" && "msg" in item
                ? String(item.msg)
                : "",
          )
          .filter(Boolean);
        return new ApiError(res.status, problems.join("; ") || fallback, problems);
      }
    }
  } catch {
    // Not JSON; fall through to the generic message.
  }
  return new ApiError(res.status, fallback);
}
