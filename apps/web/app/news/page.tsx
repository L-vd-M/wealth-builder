"use client";

import { useEffect, useState } from "react";
import { fetchJson } from "../../lib/api";

type Headline = { title: string; source: string; sentiment: string };
type Feeds = { financial: Headline[]; crypto: Headline[]; world: Headline[] };

const fallback: Feeds = {
  financial: [{ title: "US Banks Rally Ahead of Earnings", source: "MarketWire", sentiment: "positive" }],
  crypto: [{ title: "BTC Options Open Interest Climbs", source: "ChainPulse", sentiment: "positive" }],
  world: [{ title: "Trade Talks Resume Across G20 Bloc", source: "WorldReport", sentiment: "neutral" }]
};

export default function NewsPage() {
  const [feeds, setFeeds] = useState<Feeds>(fallback);

  useEffect(() => {
    fetchJson<Feeds>("/news/headlines", fallback).then(setFeeds);
  }, []);

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">News Hub</h1>
      <p className="text-sm text-slate-300">Financial, crypto, and world news streams with sentiment labels.</p>
      <div className="grid gap-3 md:grid-cols-3">
        {(Object.entries(feeds) as Array<[keyof Feeds, Headline[]]>).map(([key, items]) => (
          <section className="panel p-3" key={key}>
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">{key}</h2>
            <ul className="space-y-2 text-sm">
              {items.map((item) => (
                <li className="rounded border border-terminal-border p-2" key={`${key}-${item.title}`}>
                  <div>{item.title}</div>
                  <div className="text-xs text-slate-400">{item.source}</div>
                  <div className="text-xs uppercase text-terminal-accent">{item.sentiment}</div>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
