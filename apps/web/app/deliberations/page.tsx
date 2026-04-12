"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { deleteRequest, fetchJson, postJson } from "../../lib/api";

type DeliberationSummary = {
  id: number;
  symbol: string;
  platform: string;
  status: string;
  verdict: string | null;
  confidence: number | null;
  created_at: string;
  completed_at: string | null;
};

type Message = {
  id: number;
  agent_slug: string;
  agent_name: string;
  role: string;
  content: string;
  sequence: number;
  created_at: string;
};

type DeliberationDetail = DeliberationSummary & { messages: Message[]; summary: string | null };

const PLATFORMS = ["alpaca", "binance", "coinbase", "ibkr", "kraken", "luno", "oanda", "valr"];

const verdictStyle: Record<string, string> = {
  BUY: "bg-green-900 text-green-300",
  SELL: "bg-red-900 text-red-300",
  HOLD: "bg-amber-900 text-amber-300",
};

const statusStyle: Record<string, string> = {
  pending: "text-slate-400",
  running: "text-blue-400 animate-pulse",
  completed: "text-green-400",
  failed: "text-red-400",
};

const roleLabel: Record<string, string> = {
  analysis: "Analysis",
  sentiment: "Sentiment",
  decision: "Decision",
  chart: "Chart",
};

export default function DeliberationsPage() {
  const { getToken } = useAuth();
  const [deliberations, setDeliberations] = useState<DeliberationSummary[]>([]);
  const [selected, setSelected] = useState<DeliberationDetail | null>(null);
  const [form, setForm] = useState({ symbol: "BTC/USD", platform: "binance", context: "" });
  const [status, setStatus] = useState("");
  const [polling, setPolling] = useState<number | null>(null);

  const load = async () => {
    const token = (await getToken()) ?? undefined;
    const data = await fetchJson<DeliberationSummary[]>("/deliberations", [], token);
    setDeliberations(data);
  };

  useEffect(() => { load(); }, []);

  // Poll the selected deliberation if it's still running
  useEffect(() => {
    if (!selected || (selected.status !== "pending" && selected.status !== "running")) {
      if (polling) { clearInterval(polling); setPolling(null); }
      return;
    }
    const id = window.setInterval(async () => {
      const token = (await getToken()) ?? undefined;
      const data = await fetchJson<DeliberationDetail>(`/deliberations/${selected.id}`, selected, token);
      setSelected(data);
      if (data.status !== "pending" && data.status !== "running") {
        clearInterval(id);
        setPolling(null);
        await load();
      }
    }, 3000) as unknown as number;
    setPolling(id);
    return () => clearInterval(id);
  }, [selected?.id, selected?.status]);

  const start = async () => {
    if (!form.symbol || !form.platform) { setStatus("Symbol and platform are required."); return; }
    const token = (await getToken()) ?? undefined;
    const result = await postJson<DeliberationSummary, typeof form>(
      "/deliberations/start",
      form,
      null as unknown as DeliberationSummary,
      token,
    );
    if (result?.id) {
      setStatus(`Deliberation started (ID ${result.id}). Agents are deliberating…`);
      await load();
      openDeliberation(result.id);
    } else {
      setStatus("Failed to start deliberation.");
    }
  };

  const openDeliberation = async (id: number) => {
    const token = (await getToken()) ?? undefined;
    const data = await fetchJson<DeliberationDetail>(`/deliberations/${id}`, null as unknown as DeliberationDetail, token);
    setSelected(data);
  };

  const remove = async (id: number) => {
    const token = (await getToken()) ?? undefined;
    await deleteRequest(`/deliberations/${id}`, token);
    if (selected?.id === id) setSelected(null);
    await load();
  };

  return (
    <div className="flex h-full gap-4 p-4">
      {/* Left column */}
      <div className="flex w-72 shrink-0 flex-col gap-4">
        {/* Start form */}
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold uppercase text-slate-400">New Deliberation</h2>
          <div className="flex flex-col gap-2">
            <div>
              <label className="text-xs text-slate-400">Symbol</label>
              <input
                className="mt-0.5 w-full rounded bg-terminal-border px-2 py-1 text-sm text-white"
                value={form.symbol}
                onChange={(e) => setForm({ ...form, symbol: e.target.value })}
                placeholder="BTC/USD"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Platform</label>
              <select
                className="mt-0.5 w-full rounded bg-terminal-border px-2 py-1 text-sm text-white"
                value={form.platform}
                onChange={(e) => setForm({ ...form, platform: e.target.value })}
              >
                {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400">Context (optional)</label>
              <textarea
                rows={2}
                className="mt-0.5 w-full rounded bg-terminal-border px-2 py-1 text-xs text-white"
                value={form.context}
                onChange={(e) => setForm({ ...form, context: e.target.value })}
                placeholder="Any relevant notes for the agents…"
              />
            </div>
          </div>
          <button
            onClick={start}
            className="mt-3 w-full rounded bg-terminal-accent px-4 py-1.5 text-sm font-semibold text-black"
          >
            Start Deliberation
          </button>
          {status && <p className="mt-2 text-xs text-slate-400">{status}</p>}
        </section>

        {/* History list */}
        <section className="panel flex flex-1 flex-col overflow-hidden p-4">
          <h2 className="mb-2 text-sm font-semibold uppercase text-slate-400">History</h2>
          <div className="flex flex-1 flex-col gap-1 overflow-y-auto">
            {deliberations.length === 0 && <p className="text-xs text-slate-500">No deliberations yet.</p>}
            {deliberations.map((d) => (
              <button
                key={d.id}
                onClick={() => openDeliberation(d.id)}
                className={`rounded border p-2 text-left transition-colors hover:border-terminal-accent ${
                  selected?.id === d.id ? "border-terminal-accent" : "border-terminal-border"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-white">{d.symbol}</span>
                  {d.verdict ? (
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${verdictStyle[d.verdict] ?? "bg-slate-700 text-slate-200"}`}>
                      {d.verdict}
                    </span>
                  ) : (
                    <span className={`text-[10px] ${statusStyle[d.status] ?? "text-slate-400"}`}>{d.status}</span>
                  )}
                </div>
                <div className="mt-0.5 flex items-center justify-between">
                  <span className="text-[10px] text-slate-500">{d.platform}</span>
                  {d.confidence != null && <span className="text-[10px] text-slate-400">conf {d.confidence}/10</span>}
                </div>
                <div className="mt-0.5 text-[10px] text-slate-600">{new Date(d.created_at).toLocaleString()}</div>
              </button>
            ))}
          </div>
        </section>
      </div>

      {/* Right column — detail view */}
      <div className="panel flex flex-1 flex-col overflow-hidden p-4">
        {!selected ? (
          <div className="flex h-full items-center justify-center text-slate-500">
            <p>Start a deliberation or select one from history to view the agent conversation.</p>
          </div>
        ) : (
          <>
            <div className="mb-3 flex items-start justify-between">
              <div>
                <h1 className="text-base font-bold text-terminal-accent">
                  {selected.symbol} · {selected.platform}
                </h1>
                <div className="mt-1 flex items-center gap-2">
                  <span className={`text-xs ${statusStyle[selected.status] ?? "text-slate-400"}`}>
                    {selected.status}
                    {selected.status === "running" && " (agents deliberating…)"}
                  </span>
                  {selected.verdict && (
                    <span className={`rounded px-2 py-0.5 text-xs font-bold ${verdictStyle[selected.verdict] ?? "bg-slate-700 text-white"}`}>
                      {selected.verdict}
                      {selected.confidence != null && ` · ${selected.confidence}/10`}
                    </span>
                  )}
                </div>
                {selected.summary && <p className="mt-1 text-xs text-slate-400">{selected.summary}</p>}
              </div>
              <button
                onClick={() => remove(selected.id)}
                className="text-xs text-red-400 hover:text-red-300"
              >
                Delete
              </button>
            </div>

            {/* Agent messages */}
            <div className="flex flex-1 flex-col gap-3 overflow-y-auto">
              {selected.messages.length === 0 && selected.status === "pending" && (
                <p className="text-xs text-slate-500">Agents are preparing…</p>
              )}
              {selected.messages.map((msg) => (
                <div key={msg.id} className="rounded border border-terminal-border bg-black/20 p-3">
                  <div className="mb-2 flex items-center gap-2">
                    <span className="text-xs font-semibold text-terminal-accent">{msg.agent_name}</span>
                    <span className="rounded bg-terminal-border px-1.5 py-0.5 text-[10px] text-slate-400">
                      {roleLabel[msg.role] ?? msg.role}
                    </span>
                    <span className="ml-auto text-[10px] text-slate-600">
                      {new Date(msg.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <pre className="whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-slate-300">
                    {msg.content}
                  </pre>
                </div>
              ))}
              {(selected.status === "pending" || selected.status === "running") && (
                <div className="flex items-center gap-2 text-xs text-blue-400">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-blue-400" />
                  Agents are deliberating…
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
