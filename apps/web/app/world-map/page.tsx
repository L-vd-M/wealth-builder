"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "../../lib/api";

type Region = { name: string; change: number; sentiment: string };
type MacroEvent = { time: string; event: string; impact: string };

const fallback = {
  regions: [
    { name: "North America", change: 0.74, sentiment: "risk-on" },
    { name: "Europe", change: 0.31, sentiment: "neutral" },
    { name: "Asia Pacific", change: -0.42, sentiment: "risk-off" }
  ],
  macro_events: [{ time: "08:30 UTC", event: "US CPI Release", impact: "high" }]
};

export default function WorldMapPage() {
  const [regions, setRegions] = useState<Region[]>(fallback.regions);
  const [events, setEvents] = useState<MacroEvent[]>(fallback.macro_events);

  useEffect(() => {
    fetchJson<{ regions: Region[]; macro_events: MacroEvent[] }>("/market/regions", fallback).then((data) => {
      setRegions(data.regions);
      setEvents(data.macro_events);
    });
  }, []);

  const strongest = useMemo(
    () => regions.reduce((best, current) => (current.change > best.change ? current : best), regions[0]),
    [regions]
  );

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">World Map</h1>
      <p className="text-sm text-slate-300">Global market heat overlays and macro events for regional context.</p>
      <div className="grid gap-3 lg:grid-cols-[2fr_1fr]">
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Regional Heat Map</h2>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {regions.map((region) => (
              <article
                className="rounded border border-terminal-border px-3 py-2"
                key={region.name}
                style={{
                  background: region.change >= 0 ? "rgba(34, 197, 94, 0.12)" : "rgba(239, 68, 68, 0.12)"
                }}
              >
                <div className="text-sm font-medium">{region.name}</div>
                <div className="text-xs text-slate-300">{region.sentiment}</div>
                <div className="mt-1 text-sm font-semibold">{region.change > 0 ? "+" : ""}{region.change.toFixed(2)}%</div>
              </article>
            ))}
          </div>
        </section>
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Macro Events</h2>
          <ul className="space-y-2 text-sm">
            {events.map((evt) => (
              <li className="rounded border border-terminal-border p-2" key={`${evt.time}-${evt.event}`}>
                <div className="text-xs text-slate-400">{evt.time}</div>
                <div>{evt.event}</div>
                <div className="text-xs uppercase tracking-wide text-terminal-accent">{evt.impact}</div>
              </li>
            ))}
          </ul>
          {strongest && <p className="mt-3 text-xs text-slate-300">Strongest region: {strongest.name}</p>}
        </section>
      </div>
    </div>
  );
}
