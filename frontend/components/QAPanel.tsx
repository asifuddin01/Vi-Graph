"use client";

import { useEffect, useState } from "react";

import { askQuestion, getQAHistory, type Grounding, type QAResponse } from "@/lib/api";

// The quick actions of the §26 layout.
const QUICK_QUESTIONS = [
  { label: "Explain", question: "Explain the data flow from input to output." },
  { label: "Find branches", question: "Which branches operate in parallel?" },
  { label: "Analyze topology", question: "Analyze the topology" },
];

const SOURCE: Record<QAResponse["source"], { text: string; tone: string }> = {
  graph: {
    text: "From the graph",
    tone: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  },
  vlm: {
    text: "From the image",
    tone: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  },
  "graph+vlm": {
    text: "Graph + image",
    tone: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300",
  },
  none: {
    text: "Not answered",
    tone: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
  },
};

type Props = {
  diagramId: string;
  /** Called with the grounding to highlight in the editor, or null to clear it. */
  onHighlight: (grounding: Grounding | null) => void;
};

export default function QAPanel({ diagramId, onHighlight }: Props) {
  const [question, setQuestion] = useState("");
  const [answers, setAnswers] = useState<QAResponse[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getQAHistory(diagramId)
      .then((history) => {
        if (!cancelled) setAnswers(history);
      })
      .catch(() => {
        // History is a convenience; asking still works without it.
      });
    return () => {
      cancelled = true;
    };
  }, [diagramId]);

  function select(answer: QAResponse | null) {
    setSelected(answer?.id ?? null);
    onHighlight(answer && answer.grounding.nodes.length ? answer.grounding : null);
  }

  async function ask(text: string) {
    const q = text.trim();
    if (!q || pending) return;
    setPending(true);
    setError(null);
    try {
      const answer = await askQuestion(diagramId, q);
      setAnswers((previous) => [answer, ...previous]);
      select(answer);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not get an answer.");
    } finally {
      setPending(false);
    }
  }

  return (
    <section aria-labelledby="qa-heading" className="flex flex-col gap-3">
      <h3 id="qa-heading" className="text-sm font-semibold">
        Ask about this diagram
      </h3>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void ask(question);
        }}
      >
        <input
          aria-label="Question"
          value={question}
          maxLength={500}
          placeholder="e.g. What comes after the encoder?"
          onChange={(e) => setQuestion(e.target.value)}
          className="min-w-0 flex-1 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          disabled={pending || !question.trim()}
          className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          {pending ? "Asking…" : "Ask"}
        </button>
      </form>
      <div className="flex flex-wrap gap-1.5">
        {QUICK_QUESTIONS.map(({ label, question: q }) => (
          <button
            key={label}
            type="button"
            disabled={pending}
            onClick={() => void ask(q)}
            className="rounded-full border border-zinc-300 px-3 py-1 text-xs font-medium hover:bg-zinc-100 disabled:opacity-40 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            {label}
          </button>
        ))}
        {selected && (
          <button
            type="button"
            onClick={() => select(null)}
            className="ml-auto text-xs text-zinc-500 underline"
          >
            Clear highlight
          </button>
        )}
      </div>
      {error && (
        <p role="alert" data-testid="qa-error" className="text-sm text-red-700 dark:text-red-400">
          {error}
        </p>
      )}
      <p className="text-xs text-zinc-500">
        Answers use the last saved graph. Click an answer to highlight the nodes it is based on.
      </p>
      <ul aria-label="Answers" className="flex flex-col gap-2">
        {answers.map((answer) => {
          const source = SOURCE[answer.source];
          const active = answer.id === selected;
          return (
            <li key={answer.id}>
              <button
                type="button"
                data-testid="qa-answer"
                aria-pressed={active}
                onClick={() => select(active ? null : answer)}
                className={`flex w-full flex-col gap-1 rounded-md border px-3 py-2 text-left transition-colors ${
                  active
                    ? "border-amber-400 bg-amber-50 dark:border-amber-600 dark:bg-amber-950/30"
                    : "border-zinc-200 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-900"
                }`}
              >
                <span className="text-xs text-zinc-500">{answer.question}</span>
                <span className="text-sm">{answer.answer}</span>
                <span className="flex flex-wrap items-center gap-1.5 text-[11px]">
                  <span className={`rounded-full px-2 py-0.5 font-medium ${source.tone}`}>
                    {source.text}
                  </span>
                  <span className="text-zinc-500">
                    {answer.route.category} · {answer.route.intent.replaceAll("_", " ")}
                    {answer.grounding.nodes.length > 0 &&
                      ` · ${answer.grounding.nodes.length} node(s) grounded`}
                    {answer.graph_version !== null && ` · saved v${answer.graph_version}`}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
