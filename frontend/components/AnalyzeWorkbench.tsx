"use client";

import { useEffect, useRef, useState } from "react";

import ResultPanel from "@/components/ResultPanel";
import { analyzeDiagram, type AnalyzeResponse } from "@/lib/api";

const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp"];
// Mirrors the server default; the server remains the authority (VIGRAPH_MAX_UPLOAD_MB).
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

type State =
  | { kind: "idle" }
  | { kind: "analyzing" }
  | { kind: "done"; result: AnalyzeResponse }
  | { kind: "error"; message: string };

export default function AnalyzeWorkbench() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [state, setState] = useState<State>({ kind: "idle" });
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => () => abortRef.current?.abort(), []);

  function choose(candidate: File | undefined) {
    if (!candidate) return;
    abortRef.current?.abort();
    if (!ACCEPTED_TYPES.includes(candidate.type)) {
      setState({ kind: "error", message: "Please choose a PNG, JPEG, or WebP image." });
      return;
    }
    if (candidate.size > MAX_UPLOAD_BYTES) {
      setState({ kind: "error", message: "That image is larger than 10 MB." });
      return;
    }
    setFile(candidate);
    setPreviewUrl(URL.createObjectURL(candidate));
    setState({ kind: "idle" });
  }

  async function analyze() {
    if (!file) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setState({ kind: "analyzing" });
    try {
      const result = await analyzeDiagram(file, controller.signal);
      setState({ kind: "done", result });
    } catch (err) {
      if (controller.signal.aborted) return;
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "Analysis failed.",
      });
    }
  }

  function reset() {
    abortRef.current?.abort();
    setFile(null);
    setPreviewUrl(null);
    setState({ kind: "idle" });
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="grid flex-1 gap-6 p-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <section aria-labelledby="input-heading" className="flex flex-col gap-4">
        <h2 id="input-heading" className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
          Input image
        </h2>
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            choose(e.dataTransfer.files[0]);
          }}
          className={`flex min-h-72 cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-4 text-center transition-colors ${
            dragging
              ? "border-sky-500 bg-sky-50 dark:bg-sky-950/30"
              : "border-zinc-300 hover:border-zinc-400 dark:border-zinc-700"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_TYPES.join(",")}
            className="sr-only"
            data-testid="file-input"
            onChange={(e) => choose(e.target.files?.[0])}
          />
          {previewUrl ? (
            // A blob: URL of the user's own file; next/image optimization doesn't apply.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={previewUrl}
              alt="Uploaded diagram"
              className="max-h-[28rem] w-full object-contain"
            />
          ) : (
            <>
              <span className="text-sm font-medium">Drop a diagram here, or click to choose</span>
              <span className="text-xs text-zinc-500">PNG, JPEG, or WebP · up to 10 MB</span>
            </>
          )}
        </label>
        {file && <p className="truncate text-xs text-zinc-500">{file.name}</p>}
        <div className="flex gap-2">
          <button
            type="button"
            onClick={analyze}
            disabled={!file || state.kind === "analyzing"}
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            {state.kind === "analyzing" ? "Analyzing…" : "Analyze"}
          </button>
          <button
            type="button"
            onClick={reset}
            disabled={!file && state.kind !== "error"}
            className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium transition-colors hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            Reset
          </button>
        </div>
      </section>

      <section aria-labelledby="graph-heading" aria-live="polite" className="flex flex-col gap-4">
        <h2 id="graph-heading" className="text-sm font-semibold uppercase tracking-wide text-zinc-500">
          Reconstructed graph
        </h2>
        {state.kind === "idle" && (
          <p className="text-sm text-zinc-500">
            Upload a diagram and click Analyze to reconstruct its structure.
          </p>
        )}
        {state.kind === "analyzing" && (
          <p className="text-sm text-zinc-500">Running the model and validating its output…</p>
        )}
        {state.kind === "error" && (
          <p
            role="alert"
            data-testid="analyze-error"
            className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
          >
            {state.message}
          </p>
        )}
        {state.kind === "done" && (
          <ResultPanel key={state.result.diagram_id} result={state.result} />
        )}
      </section>
    </div>
  );
}
