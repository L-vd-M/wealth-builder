"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { fetchJson, postJson } from "../../lib/api";

type Template = { id: string; name: string; asset_class: string };
type Bot = { name: string; status: string; strategy: string };
type DraftStrategy = { name: string; thesis: string; signals: string[]; risk_rules: string[] };

export default function BotsStrategiesPage() {
  const { getToken } = useAuth();
  const { user } = useUser();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [bots, setBots] = useState<Bot[]>([]);
  const [draft, setDraft] = useState<DraftStrategy | null>(null);
  const [draftName, setDraftName] = useState("Momentum Breakout");
  const [draftThesis, setDraftThesis] = useState("Follow breakouts with volatility filter.");
  const [draftPreview, setDraftPreview] = useState("No strategy draft yet.");
  const [backtestResult, setBacktestResult] = useState("No backtest run yet.");
  const [saveStatus, setSaveStatus] = useState("No strategy saved yet.");
  const [botStatus, setBotStatus] = useState("No bot action yet.");

  useEffect(() => {
    fetchJson<{ templates: Template[] }>("/strategies/templates", { templates: [] }).then((d) => setTemplates(d.templates));
    const loadBots = async () => {
      const token = (await getToken()) ?? undefined;
      const response = await fetchJson<{ bots: Bot[] }>("/strategies/bots", { bots: [] }, token);
      setBots(response.bots);
    };
    loadBots();
  }, [getToken]);

  const createDraft = async () => {
    const result = await postJson<{ strategy: DraftStrategy }, { name: string; thesis: string }>(
      "/strategies/draft",
      { name: draftName, thesis: draftThesis },
      { strategy: { name: draftName, thesis: draftThesis, signals: [], risk_rules: [] } }
    );
    setDraft(result.strategy);
    setDraftPreview(
      `${result.strategy.name}: ${result.strategy.thesis}\nSignals: ${result.strategy.signals.join(" | ")}\nRisk: ${result.strategy.risk_rules.join(" | ")}`
    );
  };

  const runBacktest = async () => {
    const result = await postJson<
      { result: { cagr: number; sharpe: number; max_drawdown: number; win_rate: number; trades: number } },
      { name: string; symbol: string; timeframe: string; lookback_days: number }
    >(
      "/strategies/backtest",
      { name: draftName, symbol: "BTCUSD", timeframe: "1h", lookback_days: 365 },
      { result: { cagr: 0, sharpe: 0, max_drawdown: 0, win_rate: 0, trades: 0 } }
    );
    const metrics = result.result;
    setBacktestResult(
      `CAGR ${(metrics.cagr * 100).toFixed(1)}% | Sharpe ${metrics.sharpe.toFixed(2)} | MaxDD ${(metrics.max_drawdown * 100).toFixed(1)}% | Win ${(metrics.win_rate * 100).toFixed(1)}% | Trades ${metrics.trades}`
    );
  };

  const saveStrategy = async () => {
    if (!draft) {
      setSaveStatus("Draft a strategy first.");
      return;
    }
    const token = (await getToken()) ?? undefined;
    if (!token) {
      setSaveStatus("Sign in to save strategies.");
      return;
    }
    const result = await postJson<
      { status: string; strategy: { name: string; version: number } },
      { name: string; thesis: string; signals: string[]; risk_rules: string[]; user_email?: string }
    >(
      "/strategies/save",
      {
        name: draft.name,
        thesis: draft.thesis,
        signals: draft.signals,
        risk_rules: draft.risk_rules,
        user_email: user?.primaryEmailAddress?.emailAddress ?? undefined,
      },
      { status: "failed", strategy: { name: draft.name, version: 0 } },
      token
    );
    setSaveStatus(`${result.status}: ${result.strategy.name} v${result.strategy.version}`);
  };

  const createBot = async () => {
    if (!draft) {
      setBotStatus("Draft and save a strategy first.");
      return;
    }
    const token = (await getToken()) ?? undefined;
    if (!token) {
      setBotStatus("Sign in to create bots.");
      return;
    }
    const result = await postJson<{ status: string; bot?: Bot; detail?: string }, { strategy_name: string }>(
      "/strategies/bots",
      { strategy_name: draft.name },
      { status: "failed", detail: "Request failed" },
      token
    );
    if (result.status === "created" && result.bot) {
      setBotStatus(`created: ${result.bot.name}`);
      setBots((prev) => [...prev, result.bot as Bot]);
    } else {
      setBotStatus(result.detail ?? "Bot creation failed");
    }
  };

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Bots & Strategies</h1>
      <p className="text-sm text-slate-300">Create strategy drafts, run initial backtests, and monitor bot runtime state.</p>
      <div className="grid gap-3 md:grid-cols-2">
        <section className="panel p-3">
          <h2 className="mb-2 text-sm font-semibold">Bot Runtime Status</h2>
          <ul className="space-y-2 text-sm">
            {bots.map((bot) => (
              <li className="rounded border border-terminal-border p-2" key={bot.name}>
                <div className="font-medium">{bot.name}</div>
                <div className="text-xs text-slate-400">Strategy: {bot.strategy}</div>
                <div className={`text-xs uppercase ${bot.status === "running" ? "text-green-400" : "text-slate-300"}`}>{bot.status}</div>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel space-y-2 p-3">
          <h2 className="text-sm font-semibold">Strategy Workbench</h2>
          <div className="text-xs text-slate-400">Templates: {templates.map((template) => `${template.name} (${template.asset_class})`).join(" | ")}</div>
          <input className="w-full rounded bg-terminal-border px-2 py-1 text-sm" onChange={(e) => setDraftName(e.target.value)} value={draftName} />
          <textarea
            className="min-h-20 w-full rounded bg-terminal-border px-2 py-1 text-sm"
            onChange={(e) => setDraftThesis(e.target.value)}
            value={draftThesis}
          />
          <div className="flex flex-wrap gap-2">
            <button className="rounded bg-terminal-accent px-3 py-1 text-sm font-semibold text-black" onClick={createDraft} type="button">
              Draft Strategy
            </button>
            <button className="rounded bg-slate-300 px-3 py-1 text-sm font-semibold text-black" onClick={runBacktest} type="button">
              Run Backtest
            </button>
            <button className="rounded bg-emerald-300 px-3 py-1 text-sm font-semibold text-black" onClick={saveStrategy} type="button">
              Save Strategy
            </button>
            <button className="rounded bg-indigo-300 px-3 py-1 text-sm font-semibold text-black" onClick={createBot} type="button">
              Create Bot
            </button>
          </div>
          <pre className="whitespace-pre-wrap rounded border border-terminal-border p-2 text-xs text-slate-300">{draftPreview}</pre>
          <p className="text-xs text-terminal-accent">{backtestResult}</p>
          <p className="text-xs text-emerald-300">{saveStatus}</p>
          <p className="text-xs text-indigo-300">{botStatus}</p>
        </section>
      </div>
    </div>
  );
}
