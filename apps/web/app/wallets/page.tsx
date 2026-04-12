"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { deleteRequest, fetchJson, postJson } from "../../lib/api";

type Account = {
  id: number;
  platform: string;
  nickname: string;
  created_at: string;
  last_synced: string | null;
};

type BalanceEntry = {
  asset: string;
  available: number;
  total: number;
  usd_value: number | null;
};

type AccountBalance = {
  account_id: number;
  platform: string;
  nickname: string;
  balances: BalanceEntry[];
  error: string | null;
  fetched_at: string;
};

const PLATFORMS = ["alpaca", "binance", "coinbase", "ibkr", "kraken", "luno", "oanda", "valr"];

const platformMeta: Record<string, { label: string; color: string; needsSecret: boolean; secretLabel: string }> = {
  alpaca: { label: "Alpaca", color: "text-yellow-400", needsSecret: true, secretLabel: "API Secret" },
  binance: { label: "Binance", color: "text-yellow-300", needsSecret: true, secretLabel: "API Secret" },
  coinbase: { label: "Coinbase", color: "text-blue-400", needsSecret: true, secretLabel: "API Secret" },
  ibkr: { label: "Interactive Brokers", color: "text-slate-300", needsSecret: false, secretLabel: "Password" },
  kraken: { label: "Kraken", color: "text-purple-400", needsSecret: true, secretLabel: "API Secret (base64)" },
  luno: { label: "Luno", color: "text-blue-300", needsSecret: true, secretLabel: "API Secret" },
  oanda: { label: "OANDA", color: "text-green-400", needsSecret: false, secretLabel: "—" },
  valr: { label: "VALR", color: "text-sky-400", needsSecret: true, secretLabel: "API Secret" },
};

const emptyForm = {
  platform: "alpaca",
  nickname: "",
  api_key: "",
  api_secret: "",
  coinbase_passphrase: "",
  ibkr_base_url: "https://localhost:5000/v1/api",
  ibkr_token: "",
  ibkr_account_id: "",
};

export default function WalletsPage() {
  const { getToken } = useAuth();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [balances, setBalances] = useState<AccountBalance[]>([]);
  const [form, setForm] = useState({ ...emptyForm });
  const [showForm, setShowForm] = useState(false);
  const [loadingBalances, setLoadingBalances] = useState(false);
  const [status, setStatus] = useState("");

  const load = async () => {
    const token = (await getToken()) ?? undefined;
    const data = await fetchJson<Account[]>("/wallets/accounts", [], token);
    setAccounts(data);
  };

  useEffect(() => { load(); }, []);

  const link = async () => {
    if (!form.nickname || !form.api_key) { setStatus("Nickname and API key are required."); return; }
    const token = (await getToken()) ?? undefined;
    const extra: Record<string, string> = {};
    if (form.platform === "coinbase" && form.coinbase_passphrase) {
      extra.passphrase = form.coinbase_passphrase;
    }
    if (form.platform === "ibkr") {
      if (form.ibkr_base_url) extra.base_url = form.ibkr_base_url;
      if (form.ibkr_token) extra.token = form.ibkr_token;
      if (form.ibkr_account_id) extra.account_id = form.ibkr_account_id;
    }
    const payload = {
      platform: form.platform,
      nickname: form.nickname,
      api_key: form.api_key,
      api_secret: form.api_secret || null,
      extra: Object.keys(extra).length ? extra : null,
    };
    const result = await postJson<Account, typeof payload>("/wallets/accounts", payload, null as unknown as Account, token);
    if (result?.id) {
      setStatus(`"${result.nickname}" linked successfully.`);
      setForm({ ...emptyForm });
      setShowForm(false);
      await load();
    } else {
      setStatus("Failed to link account. Check that ENCRYPTION_KEY is set on the API server.");
    }
  };

  const unlink = async (id: number) => {
    const token = (await getToken()) ?? undefined;
    await deleteRequest(`/wallets/accounts/${id}`, token);
    setBalances((prev) => prev.filter((b) => b.account_id !== id));
    await load();
  };

  const fetchAllBalances = async () => {
    setLoadingBalances(true);
    setStatus("");
    const token = (await getToken()) ?? undefined;
    const data = await fetchJson<AccountBalance[]>("/wallets/balances", [], token);
    setBalances(data);
    setLoadingBalances(false);
    if (data.length === 0) setStatus("No linked accounts to fetch balances for.");
    else await load(); // refresh last_synced
  };

  const fetchOneBalance = async (id: number) => {
    const token = (await getToken()) ?? undefined;
    const data = await fetchJson<AccountBalance>(`/wallets/accounts/${id}/balance`, null as unknown as AccountBalance, token);
    if (data) {
      setBalances((prev) => {
        const idx = prev.findIndex((b) => b.account_id === id);
        if (idx >= 0) { const next = [...prev]; next[idx] = data; return next; }
        return [...prev, data];
      });
      await load();
    }
  };

  const meta = (platform: string) => platformMeta[platform] ?? { label: platform, color: "text-slate-300", needsSecret: true, secretLabel: "API Secret" };

  const balanceFor = (id: number) => balances.find((b) => b.account_id === id);

  return (
    <div className="flex flex-col gap-6 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-terminal-accent">Wallets</h1>
        <div className="flex gap-2">
          <button
            onClick={fetchAllBalances}
            disabled={loadingBalances || accounts.length === 0}
            className="rounded bg-blue-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-40"
          >
            {loadingBalances ? "Fetching…" : "Refresh All Balances"}
          </button>
          <button
            onClick={() => setShowForm(!showForm)}
            className="rounded bg-terminal-accent px-3 py-1.5 text-xs font-semibold text-black"
          >
            + Link Account
          </button>
        </div>
      </div>

      {status && <p className="text-xs text-slate-400">{status}</p>}

      {/* Link account form */}
      {showForm && (
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold uppercase text-slate-400">Link Trading Account</h2>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400">Platform</label>
              <select
                className="rounded bg-terminal-border px-2 py-1 text-sm text-white"
                value={form.platform}
                onChange={(e) => setForm({ ...form, platform: e.target.value })}
              >
                {PLATFORMS.map((p) => <option key={p} value={p}>{meta(p).label}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400">Nickname</label>
              <input
                className="rounded bg-terminal-border px-2 py-1 text-sm text-white"
                placeholder="My Alpaca Paper"
                value={form.nickname}
                onChange={(e) => setForm({ ...form, nickname: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400">API Key</label>
              <input
                type="password"
                className="rounded bg-terminal-border px-2 py-1 font-mono text-sm text-white"
                value={form.api_key}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              />
            </div>
            {meta(form.platform).needsSecret && (
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">{meta(form.platform).secretLabel}</label>
                <input
                  type="password"
                  className="rounded bg-terminal-border px-2 py-1 font-mono text-sm text-white"
                  value={form.api_secret}
                  onChange={(e) => setForm({ ...form, api_secret: e.target.value })}
                />
              </div>
            )}

            {form.platform === "coinbase" && (
              <div className="flex flex-col gap-1 col-span-2">
                <label className="text-xs text-slate-400">Coinbase Passphrase</label>
                <input
                  type="password"
                  className="rounded bg-terminal-border px-2 py-1 font-mono text-sm text-white"
                  value={form.coinbase_passphrase}
                  onChange={(e) => setForm({ ...form, coinbase_passphrase: e.target.value })}
                />
              </div>
            )}

            {form.platform === "ibkr" && (
              <>
                <div className="flex flex-col gap-1 col-span-2">
                  <label className="text-xs text-slate-400">IBKR Gateway Base URL</label>
                  <input
                    className="rounded bg-terminal-border px-2 py-1 font-mono text-sm text-white"
                    value={form.ibkr_base_url}
                    onChange={(e) => setForm({ ...form, ibkr_base_url: e.target.value })}
                    placeholder="https://localhost:5000/v1/api"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-400">IBKR Bearer Token (optional)</label>
                  <input
                    type="password"
                    className="rounded bg-terminal-border px-2 py-1 font-mono text-sm text-white"
                    value={form.ibkr_token}
                    onChange={(e) => setForm({ ...form, ibkr_token: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-slate-400">IBKR Account ID (optional)</label>
                  <input
                    className="rounded bg-terminal-border px-2 py-1 font-mono text-sm text-white"
                    value={form.ibkr_account_id}
                    onChange={(e) => setForm({ ...form, ibkr_account_id: e.target.value })}
                    placeholder="U1234567"
                  />
                </div>
              </>
            )}
          </div>
          <p className="mt-2 text-[11px] text-slate-500">
            Keys are encrypted at rest using AES-256 (Fernet). They are never logged or exposed.
          </p>
          <div className="mt-3 flex items-center gap-3">
            <button onClick={link} className="rounded bg-terminal-accent px-4 py-1.5 text-xs font-semibold text-black">
              Save
            </button>
            <button onClick={() => setShowForm(false)} className="text-xs text-slate-400 hover:text-white">Cancel</button>
          </div>
        </section>
      )}

      {/* Account cards */}
      {accounts.length === 0 ? (
        <section className="panel p-8 text-center">
          <p className="text-slate-500">No accounts linked yet. Click "Link Account" to connect a trading platform.</p>
        </section>
      ) : (
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-3">
          {accounts.map((account) => {
            const m = meta(account.platform);
            const b = balanceFor(account.id);
            return (
              <section key={account.id} className="panel p-4">
                <div className="mb-2 flex items-start justify-between">
                  <div>
                    <p className={`text-sm font-semibold ${m.color}`}>{m.label}</p>
                    <p className="text-xs text-slate-300">{account.nickname}</p>
                  </div>
                  <button
                    onClick={() => unlink(account.id)}
                    className="text-[10px] text-red-400 hover:text-red-300"
                  >
                    Unlink
                  </button>
                </div>

                {account.last_synced && (
                  <p className="mb-2 text-[10px] text-slate-500">
                    Last synced: {new Date(account.last_synced).toLocaleString()}
                  </p>
                )}

                {b ? (
                  <>
                    {b.error ? (
                      <p className="rounded bg-red-900/30 p-2 text-xs text-red-400">{b.error}</p>
                    ) : b.balances.length === 0 ? (
                      <p className="text-xs text-slate-500">No balances found.</p>
                    ) : (
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-terminal-border text-slate-500">
                            <th className="pb-1 text-left">Asset</th>
                            <th className="pb-1 text-right">Available</th>
                            <th className="pb-1 text-right">Total</th>
                          </tr>
                        </thead>
                        <tbody>
                          {b.balances.map((entry) => (
                            <tr key={entry.asset} className="border-b border-terminal-border/30">
                              <td className="py-0.5 font-mono text-slate-200">{entry.asset}</td>
                              <td className="py-0.5 text-right font-mono text-slate-300">
                                {entry.available.toLocaleString(undefined, { maximumFractionDigits: 8 })}
                              </td>
                              <td className="py-0.5 text-right font-mono text-slate-300">
                                {entry.total.toLocaleString(undefined, { maximumFractionDigits: 8 })}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </>
                ) : (
                  <button
                    onClick={() => fetchOneBalance(account.id)}
                    className="rounded bg-terminal-border px-3 py-1 text-xs text-slate-300 hover:bg-slate-600"
                  >
                    Fetch Balance
                  </button>
                )}
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
