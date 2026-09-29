import BackendStatus from "@/components/BackendStatus";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="flex items-center justify-between border-b border-zinc-200 px-6 py-4 dark:border-zinc-800">
        <h1 className="text-lg font-semibold tracking-tight">Vi-Graph</h1>
        <BackendStatus />
      </header>
      <main className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
        <p className="max-w-xl text-zinc-600 dark:text-zinc-400">
          Upload a diagram, reconstruct its structure as a graph, and ask questions
          about its topology.
        </p>
        <p className="text-sm text-zinc-500">Diagram upload arrives in Phase 1.</p>
      </main>
    </div>
  );
}
