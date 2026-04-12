"use client";

import { useEffect, useState } from "react";
import { fetchJson, postJson } from "../../lib/api";

type Factor = { name: string; value: number; signal: string };
type Leader = { symbol: string; score: number };
type QuantStrategy = { id: string; name: string; thesis: string; signals: string[]; risk_rules: string[] };
type TradeResearch = { approved: boolean; research: { verdict: string; confidence: number; rationale: string; provider: string } };

const fallback = {
  factors: [{ name: "Momentum", value: 0.67, signal: "bullish" }],
  leaders: [{ symbol: "NVDA", score: 91 }]
};

export default function QuantAnalysisPage() {
  const [factors, setFactors] = useState<Factor[]>(fallback.factors);
  const [leaders, setLeaders] = useState<Leader[]>(fallback.leaders);
  const [strategies, setStrategies] = useState<QuantStrategy[]>([]);
  const [verifyResult, setVerifyResult] = useState("No trade verification run yet.");

  useEffect(() => {
    fetchJson<{ factors: Factor[]; leaders: Leader[] }>("/market/quant", fallback).then((data) => {
      setFactors(data.factors);
      setLeaders(data.leaders);
    });
    fetchJson<{ strategies: QuantStrategy[] }>("/strategies/predefined", { strategies: [] }).then((d) => {
      setStrategies(d.strategies);
    });
  }, []);

  const verifyTrade = async () => {
    const result = await postJson<TradeResearch, { symbol: string; side: string; entry_price: number; quantity: number; context: string }>(
      "/strategies/verify-trade",
      {
        symbol: "BTCUSD",
        side: "buy",
        entry_price: 65000,
        quantity: 0.1,
        context: "Momentum breakout + volume expansion",
      },
      { approved: false, research: { verdict: "reject", confidence: 0, rationale: "Unavailable", provider: "mock" } },
    );
    setVerifyResult(
      `${result.approved ? "APPROVED" : "REJECTED"} | ${result.research.confidence}% | ${result.research.provider} | ${result.research.rationale}`
    );
  };

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Quant Analysis</h1>
      <p className="text-sm text-slate-300">Factor models, screening tables, and early signal ranking.</p>
      <div className="grid gap-3 md:grid-cols-2">
        <section className="panel p-3">
          <h2 className="mb-2 text-sm font-semibold">Factor Board</h2>
          <ul className="space-y-2 text-sm">
            {factors.map((factor) => (
              <li className="flex items-center justify-between rounded border border-terminal-border p-2" key={factor.name}>
                <div>
                  <div>{factor.name}</div>
                  <div className="text-xs text-slate-400">{factor.signal}</div>
                </div>
                <div className="font-semibold">{factor.value.toFixed(2)}</div>
              </li>
            ))}
          </ul>
        </section>
        <section className="panel p-3">
          <h2 className="mb-2 text-sm font-semibold">Signal Leaders</h2>
          <ul className="space-y-2 text-sm">
            {leaders.map((leader) => (
              <li className="flex items-center justify-between rounded border border-terminal-border p-2" key={leader.symbol}>
                <span>{leader.symbol}</span>
                <span className="font-semibold">{leader.score}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="panel p-3">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold">Predefined Quant Strategies</h2>
          <button className="rounded bg-terminal-accent px-2 py-1 text-xs font-semibold text-black" onClick={verifyTrade} type="button">
            Verify Sample Trade via Agent
          </button>
        </div>
        <p className="mb-2 text-xs text-slate-400">{verifyResult}</p>
        <div className="grid gap-2 md:grid-cols-2">
          {strategies.map((strategy) => (
            <div key={strategy.id} className="rounded border border-terminal-border p-2 text-xs text-slate-300">
              <div className="text-sm font-semibold text-white">{strategy.name}</div>
              <div className="mt-1">{strategy.thesis}</div>
              <div className="mt-1">Signals: {strategy.signals.join(" | ")}</div>
              <div className="mt-1">Risk: {strategy.risk_rules.join(" | ")}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
