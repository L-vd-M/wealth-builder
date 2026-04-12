"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { TradingChart } from "../../components/trading-chart";
import { fetchJson, postJson } from "../../lib/api";

type AgentResponse = {
  response: string;
  provider?: string;
  strategy?: { name: string; thesis: string; signals: string[]; risk_rules: string[] };
  actions?: Array<{ type: string; endpoint: string; payload?: unknown }>;
};

type Candle = { t: number; o: number; h: number; l: number; c: number; v: number };
type OverlayPoint = { x: number; fast: number; slow: number };

export default function AIAgentsPage() {
  const { getToken } = useAuth();
  const { user } = useUser();

  const [agent, setAgent] = useState("quant-researcher");
  const [prompt, setPrompt] = useState("Design a momentum strategy for BTCUSD with overlays.");
  const [chatResult, setChatResult] = useState("No agent response yet.");
  const [provider, setProvider] = useState("mock");
  const [strategy, setStrategy] = useState<AgentResponse["strategy"]>();
  const [overlaySchema, setOverlaySchema] = useState("No overlay generated.");
  const [saveResult, setSaveResult] = useState("No strategy saved yet.");
  const [historyResult, setHistoryResult] = useState("No history loaded.");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [overlayPoints, setOverlayPoints] = useState<OverlayPoint[]>([]);

  useEffect(() => {
    fetchJson<{ symbol: string; points: Candle[] }>(
      "/market/candles?symbol=BTCUSD&points=80",
      { symbol: "BTCUSD", points: [] }
    ).then((data) => setCandles(data.points));
  }, []);

  const askAgent = async () => {
    const result = await postJson<AgentResponse, { agent: string; prompt: string }>(
      "/agents/chat",
      { agent, prompt },
      { response: "Agent unavailable." }
    );
    setChatResult(result.response);
    setProvider(result.provider ?? "mock");
    setStrategy(result.strategy);
  };

  const generateOverlay = async () => {
    const result = await postJson<
      { tv_overlay_schema: unknown; points?: OverlayPoint[] },
      { symbol: string; timeframe: string; type: string; params: Record<string, number> }
    >(
      "/overlays/generate",
      { symbol: "BTCUSD", timeframe: "1h", type: "ema_ribbon", params: { fast: 20, slow: 50 } },
      { tv_overlay_schema: "No schema" }
    );
    setOverlaySchema(JSON.stringify(result.tv_overlay_schema, null, 2));
    setOverlayPoints(result.points ?? []);
  };

  const saveStrategy = async () => {
    if (!strategy) {
      setSaveResult("Generate a strategy first.");
      return;
    }

    const token = (await getToken()) ?? undefined;
    const userEmail = user?.primaryEmailAddress?.emailAddress ?? undefined;

    const result = await postJson<
      { status: string; strategy: { name: string; version: number } },
      { name: string; thesis: string; signals: string[]; risk_rules: string[]; user_email?: string }
    >(
      "/strategies/save",
      {
        name: strategy.name,
        thesis: strategy.thesis,
        signals: strategy.signals,
        risk_rules: strategy.risk_rules,
        user_email: userEmail,
      },
      { status: "failed", strategy: { name: strategy.name, version: 0 } },
      token
    );

    setSaveResult(`${result.status}: ${result.strategy.name} v${result.strategy.version}`);
  };

  const loadHistory = async () => {
    if (!strategy) {
      setHistoryResult("Generate a strategy first.");
      return;
    }

    const token = (await getToken()) ?? undefined;
    const result = await fetchJson<{ name: string; versions: Array<{ version: number }> }>(
      `/strategies/history/${encodeURIComponent(strategy.name)}`,
      { name: strategy.name, versions: [] },
      token
    );
    setHistoryResult(`${result.name}: ${result.versions.length} version(s)`);
  };

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">AI Agents Console</h1>
      <p className="text-sm text-slate-300">Chat with agents to generate quant strategy drafts and chart overlays.</p>
      <div className="grid gap-3 lg:grid-cols-[2fr_1fr]">
        <section className="panel space-y-2 p-3">
          <h2 className="text-sm font-semibold">Agent Chat</h2>
          <input className="w-full rounded bg-terminal-border px-2 py-1 text-sm" onChange={(e) => setAgent(e.target.value)} value={agent} />
          <textarea className="min-h-24 w-full rounded bg-terminal-border px-2 py-1 text-sm" onChange={(e) => setPrompt(e.target.value)} value={prompt} />
          <div className="flex gap-2">
            <button className="rounded bg-terminal-accent px-3 py-1 text-sm font-semibold text-black" onClick={askAgent} type="button">
              Ask Agent
            </button>
            <button className="rounded bg-slate-300 px-3 py-1 text-sm font-semibold text-black" onClick={generateOverlay} type="button">
              Generate Overlay
            </button>
            <button className="rounded bg-emerald-300 px-3 py-1 text-sm font-semibold text-black" onClick={saveStrategy} type="button">
              Save Strategy
            </button>
            <button className="rounded bg-indigo-300 px-3 py-1 text-sm font-semibold text-black" onClick={loadHistory} type="button">
              Load History
            </button>
          </div>
          <p className="text-sm text-slate-300">{chatResult}</p>
          <p className="text-xs text-terminal-accent">Provider: {provider}</p>
          <p className="text-xs text-slate-300">{saveResult}</p>
          <p className="text-xs text-slate-300">{historyResult}</p>

          <div className="panel p-2">
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide">Plot Preview</h3>
            <TradingChart candles={candles} overlayPoints={overlayPoints} />
          </div>
        </section>

        <section className="panel space-y-2 p-3">
          <h2 className="text-sm font-semibold">Generated Strategy</h2>
          {strategy ? (
            <div className="space-y-1 text-xs text-slate-300">
              <div className="font-semibold text-sm">{strategy.name}</div>
              <div>{strategy.thesis}</div>
              <div>Signals: {strategy.signals.join(" | ")}</div>
              <div>Risk: {strategy.risk_rules.join(" | ")}</div>
            </div>
          ) : (
            <p className="text-xs text-slate-400">No strategy generated yet.</p>
          )}
          <h3 className="pt-2 text-sm font-semibold">Overlay Schema</h3>
          <pre className="max-h-52 overflow-auto whitespace-pre-wrap rounded border border-terminal-border p-2 text-xs text-slate-300">{overlaySchema}</pre>
        </section>
      </div>
    </div>
  );
}
