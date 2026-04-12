"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "../../lib/api";

type Platform = {
  name: string;
  category: "crypto" | "forex" | "stocks";
  fee_bps: number;
  api_score: number;
  regions: string[];
};

const fallback = {
  platforms: [
    { name: "Binance", category: "crypto", fee_bps: 10, api_score: 9, regions: ["global"] },
    { name: "OANDA", category: "forex", fee_bps: 12, api_score: 8, regions: ["global"] },
    { name: "Alpaca", category: "stocks", fee_bps: 0, api_score: 8, regions: ["us"] }
  ] as Platform[]
};

export default function PlatformsPage() {
  const [category, setCategory] = useState<Platform["category"]>("crypto");
  const [platforms, setPlatforms] = useState<Platform[]>(fallback.platforms);

  useEffect(() => {
    fetchJson<{ platforms: Platform[] }>("/trading/platforms", fallback).then((data) => setPlatforms(data.platforms));
  }, []);

  const filtered = useMemo(() => platforms.filter((item) => item.category === category), [platforms, category]);

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Platforms Directory</h1>
      <p className="text-sm text-slate-300">Compare prominent trading platforms by crypto, forex, and stocks.</p>

      <div className="flex gap-2">
        {(["crypto", "forex", "stocks"] as const).map((tab) => (
          <button
            className={`rounded px-3 py-1 text-sm ${tab === category ? "bg-terminal-accent text-black" : "bg-terminal-border"}`}
            key={tab}
            onClick={() => setCategory(tab)}
            type="button"
          >
            {tab.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="panel overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-black/20 text-xs uppercase tracking-wide text-slate-300">
            <tr>
              <th className="px-3 py-2">Platform</th>
              <th className="px-3 py-2">Fee (bps)</th>
              <th className="px-3 py-2">API Score</th>
              <th className="px-3 py-2">Regions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr className="border-t border-terminal-border" key={`${item.category}-${item.name}`}>
                <td className="px-3 py-2">{item.name}</td>
                <td className="px-3 py-2">{item.fee_bps}</td>
                <td className="px-3 py-2">{item.api_score}/10</td>
                <td className="px-3 py-2">{item.regions.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
