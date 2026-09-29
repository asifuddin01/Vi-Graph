import AnalyzeWorkbench from "@/components/AnalyzeWorkbench";
import BackendStatus from "@/components/BackendStatus";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="flex items-center justify-between border-b border-zinc-200 px-6 py-4 dark:border-zinc-800">
        <h1 className="text-lg font-semibold tracking-tight">Vi-Graph</h1>
        <BackendStatus />
      </header>
      <main className="flex flex-1 flex-col">
        <AnalyzeWorkbench />
      </main>
    </div>
  );
}
