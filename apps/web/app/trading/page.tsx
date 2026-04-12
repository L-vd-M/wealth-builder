"use client";

import { useEffect, useState } from "react";
import { fetchJson, postJson } from "../../lib/api";

type WatchItem = { symbol: string; price: number; change: number };
type Position = { symbol: string; qty: number; entry: number; mark: number; pnl: number };
type Risk = { gross_exposure: number; daily_var_95: number; max_drawdown_limit: number; portfolio_beta: number };

export default function TradingPage() {
  const [watchlist, setWatchlist] = useState<WatchItem[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [risk, setRisk] = useState<Risk | null>(null);
  const [symbol, setSymbol] = useState("BTCUSD");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = useState(1);
  const [ticketResult, setTicketResult] = useState("No order submitted yet.");

  useEffect(() => {
    fetchJson<{ watchlist: WatchItem[] }>("/trading/watchlist", { watchlist: [] }).then((d) => setWatchlist(d.watchlist));
    fetchJson<{ positions: Position[] }>("/trading/positions", { positions: [] }).then((d) => setPositions(d.positions));
    fetchJson<Risk>("/trading/risk", {
      gross_exposure: 0,
      daily_var_95: 0,
      max_drawdown_limit: 0,
      portfolio_beta: 0
    }).then(setRisk);
  }, []);

  const submitOrder = async () => {
    const result = await postJson<{ status: string; order: { symbol: string; side: string; quantity: number } }, { symbol: string; side: string; quantity: number; order_type: string }>(
      "/trading/order",
      { symbol, side, quantity, order_type: "market" },
      { status: "rejected", order: { symbol, side, quantity } }
    );
    setTicketResult(`${result.status.toUpperCase()}: ${result.order.side.toUpperCase()} ${result.order.quantity} ${result.order.symbol}`);
  };

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold">Trading Workspace</h1>
      <p className="text-sm text-slate-300">Paper execution, live watchlist, and portfolio risk snapshot.</p>

      <div className="grid gap-3 lg:grid-cols-[2fr_1fr]">
        <section className="panel p-3">
          <h2 className="mb-2 text-sm font-semibold">Watchlist</h2>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {watchlist.map((item) => (
              <button
                className="rounded border border-terminal-border p-2 text-left"
                key={item.symbol}
                onClick={() => setSymbol(item.symbol)}
                type="button"
              >
                <div className="font-semibold">{item.symbol}</div>
                <div className="text-xs text-slate-400">{item.price}</div>
                <div className={`text-xs ${item.change >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {item.change >= 0 ? "+" : ""}{item.change.toFixed(2)}%
                </div>
              </button>
            ))}
          </div>

          <h2 className="mb-2 mt-4 text-sm font-semibold">Open Positions</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-slate-400">
                <tr>
                  <th className="py-1 text-left">Symbol</th>
                  <th className="py-1 text-left">Qty</th>
                  <th className="py-1 text-left">Entry</th>
                  <th className="py-1 text-left">Mark</th>
                  <th className="py-1 text-left">PnL</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((position) => (
                  <tr className="border-t border-terminal-border" key={position.symbol}>
                    <td className="py-1">{position.symbol}</td>
                    <td className="py-1">{position.qty}</td>
                    <td className="py-1">{position.entry}</td>
                    <td className="py-1">{position.mark}</td>
                    <td className={`py-1 ${position.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>{position.pnl}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel space-y-3 p-3">
          <h2 className="text-sm font-semibold">Order Ticket (Paper)</h2>
          <label className="block text-xs text-slate-300">
            Symbol
            <input className="mt-1 w-full rounded bg-terminal-border px-2 py-1" onChange={(e) => setSymbol(e.target.value.toUpperCase())} value={symbol} />
          </label>
          <label className="block text-xs text-slate-300">
            Side
            <select className="mt-1 w-full rounded bg-terminal-border px-2 py-1" onChange={(e) => setSide(e.target.value as "buy" | "sell")} value={side}>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
            </select>
          </label>
          <label className="block text-xs text-slate-300">
            Quantity
            <input className="mt-1 w-full rounded bg-terminal-border px-2 py-1" min={0.001} onChange={(e) => setQuantity(Number(e.target.value))} type="number" value={quantity} />
          </label>
          <button className="w-full rounded bg-terminal-accent px-3 py-2 text-sm font-semibold text-black" onClick={submitOrder} type="button">
            Submit Paper Order
          </button>
          <p className="text-xs text-slate-300">{ticketResult}</p>

          <h3 className="pt-2 text-sm font-semibold">Risk Panel</h3>
          {risk && (
            <div className="space-y-1 text-xs text-slate-300">
              <div>Gross Exposure: {risk.gross_exposure}</div>
              <div>Daily VaR 95: {risk.daily_var_95}</div>
              <div>Max Drawdown Limit: {(risk.max_drawdown_limit * 100).toFixed(1)}%</div>
              <div>Portfolio Beta: {risk.portfolio_beta.toFixed(2)}</div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
