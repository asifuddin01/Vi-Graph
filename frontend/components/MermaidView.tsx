"use client";

import { useEffect, useId, useState } from "react";

type Render = { kind: "rendering" } | { kind: "ok"; svg: string } | { kind: "error"; message: string };

/** Renders backend-generated Mermaid (labels already escaped, §10) and shows its source. */
export default function MermaidView({ source }: { source: string }) {
  const [render, setRender] = useState<Render>({ kind: "rendering" });
  const [copied, setCopied] = useState(false);
  const elementId = `mermaid-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const mermaid = (await import("mermaid")).default;
      const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "strict",
        theme: dark ? "dark" : "default",
      });
      try {
        const { svg } = await mermaid.render(elementId, source);
        if (!cancelled) setRender({ kind: "ok", svg });
      } catch (err) {
        if (!cancelled) {
          setRender({
            kind: "error",
            message: err instanceof Error ? err.message : "Could not render the diagram.",
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [source, elementId]);

  async function copy() {
    await navigator.clipboard.writeText(source);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="flex flex-col gap-2">
      <div
        data-testid="mermaid-diagram"
        className="flex min-h-40 items-center justify-center overflow-auto rounded-md border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-950"
      >
        {render.kind === "rendering" && <span className="text-xs text-zinc-500">Rendering…</span>}
        {render.kind === "error" && (
          <span className="text-xs text-red-700 dark:text-red-400">{render.message}</span>
        )}
        {render.kind === "ok" && (
          // Mermaid output with securityLevel "strict" is sanitized by Mermaid itself.
          <div className="max-w-full [&_svg]:h-auto [&_svg]:max-w-full" dangerouslySetInnerHTML={{ __html: render.svg }} />
        )}
      </div>
      <details className="rounded-md border border-zinc-200 px-3 py-2 dark:border-zinc-800">
        <summary className="cursor-pointer text-sm font-medium">Mermaid source</summary>
        <div className="mt-2 flex flex-col gap-2">
          <pre
            data-testid="mermaid-source"
            className="max-h-80 overflow-auto rounded bg-zinc-50 p-2 text-[11px] leading-relaxed dark:bg-zinc-900"
          >
            {source}
          </pre>
          <button
            type="button"
            onClick={copy}
            className="self-start rounded-md border border-zinc-300 px-3 py-1 text-xs font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            {copied ? "Copied" : "Copy source"}
          </button>
        </div>
      </details>
    </div>
  );
}
