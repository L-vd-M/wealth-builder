"use client";

import { useEffect, useState } from "react";
import { fetchJson } from "../../lib/api";

type Factor = { name: string; value: number; signal: string };
type Leader = { symbol: string; score: number };

const fallback = {
  factors: [{ name: "Momentum", value: 0.67, signal: "bullish" }],
  leaders: [{ symbol: "NVDA", score: 91 }]
};

export default function QuantAnalysisPage() {
  const [factors, setFactors] = useState<Factor[]>(fallback.factors);
  const [leaders, setLeaders] = useState<Leader[]>(fallback.leaders);

  useEffect(() => {
    fetchJson<{ factors: Factor[]; leaders: Leader[] }>("/market/quant", fallback).then((data) => {
      setFactors(data.factors);
      setLeaders(data.leaders);
    });
  }, []);

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
    </div>
  );
}
