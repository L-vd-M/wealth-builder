"use client";

import { useEffect, useState } from "react";
import { fetchJson } from "../../lib/api";

type FinancialResponse = {
  valuation: { forward_pe: number; ev_ebitda: number; fcf_yield: number };
  balance_sheet: { cash_ratio: number; debt_to_equity: number; interest_coverage: number };
  events: Array<{ date: string; name: string; type: string }>;
};

const fallback: FinancialResponse = {
  valuation: { forward_pe: 19.7, ev_ebitda: 13.2, fcf_yield: 3.9 },
  balance_sheet: { cash_ratio: 1.34, debt_to_equity: 0.58, interest_coverage: 8.1 },
  events: [{ date: "2026-04-15", name: "Earnings: JPM, C", type: "earnings" }]
};

export default function FinancialAnalysisPage() {
  const [data, setData] = useState<FinancialResponse>(fallback);

  useEffect(() => {
    fetchJson<FinancialResponse>("/market/financial", fallback).then(setData);
  }, []);

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Financial Analysis</h1>
      <p className="text-sm text-slate-300">Fundamentals, valuation panels, and macro-sensitive KPI blocks.</p>
      <div className="grid gap-3 md:grid-cols-3">
        <section className="panel p-3 text-sm">
          <h2 className="mb-2 font-semibold">Valuation Snapshot</h2>
          <div>Forward P/E: {data.valuation.forward_pe.toFixed(1)}</div>
          <div>EV/EBITDA: {data.valuation.ev_ebitda.toFixed(1)}</div>
          <div>FCF Yield: {data.valuation.fcf_yield.toFixed(1)}%</div>
        </section>
        <section className="panel p-3 text-sm">
          <h2 className="mb-2 font-semibold">Balance Sheet</h2>
          <div>Cash Ratio: {data.balance_sheet.cash_ratio.toFixed(2)}</div>
          <div>Debt/Equity: {data.balance_sheet.debt_to_equity.toFixed(2)}</div>
          <div>Interest Coverage: {data.balance_sheet.interest_coverage.toFixed(1)}</div>
        </section>
        <section className="panel p-3 text-sm">
          <h2 className="mb-2 font-semibold">Event Calendar</h2>
          <ul className="space-y-2">
            {data.events.map((event) => (
              <li className="rounded border border-terminal-border p-2" key={`${event.date}-${event.name}`}>
                <div className="text-xs text-slate-400">{event.date}</div>
                <div>{event.name}</div>
                <div className="text-xs uppercase text-terminal-accent">{event.type}</div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
