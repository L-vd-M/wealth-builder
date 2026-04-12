"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { deleteRequest, fetchJson, postJson } from "../../lib/api";

type Agent = {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  platform: string | null;
  role: string | null;
  tools_json: string[] | null;
  is_system: boolean;
};

const PLATFORMS = ["alpaca", "binance", "coinbase", "ibkr", "kraken", "luno", "oanda", "valr", "market-data", "general"];
const ROLES = ["analysis", "chart", "decision", "execution", "data", "sentiment", "analyst", "orchestrator"];

const platformLabel: Record<string, string> = {
  alpaca: "Alpaca", binance: "Binance", coinbase: "Coinbase", ibkr: "Interactive Brokers",
  kraken: "Kraken", luno: "Luno", oanda: "OANDA", valr: "VALR",
  "market-data": "Market Data", general: "General",
};

const roleColor: Record<string, string> = {
  analysis: "bg-blue-900 text-blue-200",
  chart: "bg-purple-900 text-purple-200",
  decision: "bg-amber-900 text-amber-200",
  execution: "bg-green-900 text-green-200",
  data: "bg-slate-700 text-slate-200",
  sentiment: "bg-pink-900 text-pink-200",
  analyst: "bg-indigo-900 text-indigo-200",
  orchestrator: "bg-teal-900 text-teal-200",
};

const emptyForm = { slug: "", name: "", description: "", platform: "", role: "", system_prompt: "", tools_json: "read,search" };

export default function AgentsPage() {
  const { getToken } = useAuth();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [filter, setFilter] = useState({ platform: "", role: "" });
  const [selected, setSelected] = useState<Agent | null>(null);
  const [form, setForm] = useState({ ...emptyForm });
  const [showForm, setShowForm] = useState(false);
  const [status, setStatus] = useState("");

  const load = async (platform = "", role = "") => {
    const token = (await getToken()) ?? undefined;
    let path = "/registry";
    const params: string[] = [];
    if (platform) params.push(`platform=${encodeURIComponent(platform)}`);
    if (role) params.push(`role=${encodeURIComponent(role)}`);
    if (params.length) path += "?" + params.join("&");
    const data = await fetchJson<Agent[]>(path, [], token);
    setAgents(data);
  };

  useEffect(() => { load(filter.platform, filter.role); }, [filter]);

  const addAgent = async () => {
    if (!form.slug || !form.name) { setStatus("Slug and name are required."); return; }
    const token = (await getToken()) ?? undefined;
    const payload = {
      slug: form.slug,
      name: form.name,
      description: form.description || null,
      platform: form.platform || null,
      role: form.role || null,
      system_prompt: form.system_prompt || null,
      tools_json: form.tools_json ? form.tools_json.split(",").map((t) => t.trim()) : null,
    };
    const result = await postJson<Agent, typeof payload>("/registry", payload, null as unknown as Agent, token);
    if (result?.id) {
      setStatus(`Agent "${result.name}" added.`);
      setForm({ ...emptyForm });
      setShowForm(false);
      await load(filter.platform, filter.role);
    } else {
      setStatus("Failed to add agent. Slug may already exist.");
    }
  };

  const removeAgent = async (slug: string) => {
    const token = (await getToken()) ?? undefined;
    const ok = await deleteRequest(`/registry/${slug}`, token);
    if (ok) { await load(filter.platform, filter.role); }
    else { setStatus("Cannot delete system agents."); }
  };

  // Group agents by platform
  const grouped = agents.reduce<Record<string, Agent[]>>((acc, a) => {
    const key = a.platform ?? "general";
    if (!acc[key]) acc[key] = [];
    acc[key].push(a);
    return acc;
  }, {});

  return (
    <div className="flex h-full gap-4 p-4">
      {/* Left panel — catalogue */}
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-bold text-terminal-accent">Agent Catalogue</h1>
          <button
            onClick={() => setShowForm(!showForm)}
            className="rounded bg-terminal-accent px-3 py-1 text-xs font-semibold text-black"
          >
            + Add Custom Agent
          </button>
        </div>

        {/* Filters */}
        <div className="flex gap-2">
          <select
            className="rounded bg-terminal-border px-2 py-1 text-xs text-white"
            value={filter.platform}
            onChange={(e) => setFilter({ ...filter, platform: e.target.value })}
          >
            <option value="">All Platforms</option>
            {PLATFORMS.map((p) => <option key={p} value={p}>{platformLabel[p] ?? p}</option>)}
          </select>
          <select
            className="rounded bg-terminal-border px-2 py-1 text-xs text-white"
            value={filter.role}
            onChange={(e) => setFilter({ ...filter, role: e.target.value })}
          >
            <option value="">All Roles</option>
            {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>

        {/* Add form */}
        {showForm && (
          <section className="panel p-4">
            <h2 className="mb-3 text-sm font-semibold uppercase text-slate-400">New Custom Agent</h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Slug (unique identifier)", key: "slug", placeholder: "my-btc-analyst" },
                { label: "Name", key: "name", placeholder: "My BTC Analyst" },
                { label: "Platform", key: "platform", placeholder: "binance" },
                { label: "Role", key: "role", placeholder: "analysis" },
                { label: "Tools (comma-separated)", key: "tools_json", placeholder: "read,search,web" },
              ].map(({ label, key, placeholder }) => (
                <div key={key} className="flex flex-col gap-1">
                  <label className="text-xs text-slate-400">{label}</label>
                  <input
                    className="rounded bg-terminal-border px-2 py-1 text-xs text-white"
                    placeholder={placeholder}
                    value={form[key as keyof typeof form]}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  />
                </div>
              ))}
              <div className="col-span-2 flex flex-col gap-1">
                <label className="text-xs text-slate-400">Description</label>
                <input
                  className="rounded bg-terminal-border px-2 py-1 text-xs text-white"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
              <div className="col-span-2 flex flex-col gap-1">
                <label className="text-xs text-slate-400">System Prompt</label>
                <textarea
                  rows={5}
                  className="rounded bg-terminal-border px-2 py-1 font-mono text-xs text-white"
                  value={form.system_prompt}
                  onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                  placeholder="You are a trading agent specialising in..."
                />
              </div>
            </div>
            <div className="mt-3 flex items-center gap-3">
              <button onClick={addAgent} className="rounded bg-terminal-accent px-4 py-1.5 text-xs font-semibold text-black">Save Agent</button>
              <button onClick={() => setShowForm(false)} className="text-xs text-slate-400 hover:text-white">Cancel</button>
              {status && <span className="text-xs text-slate-400">{status}</span>}
            </div>
          </section>
        )}

        {/* Agent cards grouped by platform */}
        {Object.entries(grouped).map(([platform, list]) => (
          <section key={platform} className="panel p-4">
            <h2 className="mb-3 text-sm font-semibold text-slate-300">{platformLabel[platform] ?? platform}</h2>
            <div className="grid grid-cols-2 gap-2">
              {list.map((agent) => (
                <button
                  key={agent.slug}
                  onClick={() => setSelected(agent)}
                  className={`rounded border p-3 text-left transition-colors hover:border-terminal-accent ${
                    selected?.slug === agent.slug ? "border-terminal-accent" : "border-terminal-border"
                  }`}
                >
                  <div className="flex items-start justify-between gap-1">
                    <span className="text-xs font-medium text-white">{agent.name}</span>
                    {agent.role && (
                      <span className={`shrink-0 rounded px-1 py-0.5 text-[10px] font-medium ${roleColor[agent.role] ?? "bg-slate-700 text-slate-200"}`}>
                        {agent.role}
                      </span>
                    )}
                  </div>
                  {agent.description && (
                    <p className="mt-1 text-[11px] leading-snug text-slate-400 line-clamp-2">{agent.description}</p>
                  )}
                  {!agent.is_system && (
                    <button
                      onClick={(e) => { e.stopPropagation(); removeAgent(agent.slug); }}
                      className="mt-1 text-[10px] text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  )}
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>

      {/* Right panel — detail */}
      {selected && (
        <aside className="panel w-80 shrink-0 overflow-y-auto p-4">
          <div className="mb-2 flex items-start justify-between">
            <h2 className="text-sm font-semibold text-terminal-accent">{selected.name}</h2>
            <button onClick={() => setSelected(null)} className="text-xs text-slate-500 hover:text-white">✕</button>
          </div>
          <div className="mb-3 flex flex-wrap gap-1">
            {selected.platform && <span className="rounded bg-terminal-border px-1.5 py-0.5 text-[10px] text-slate-300">{selected.platform}</span>}
            {selected.role && <span className={`rounded px-1.5 py-0.5 text-[10px] ${roleColor[selected.role] ?? "bg-slate-700 text-slate-200"}`}>{selected.role}</span>}
            {selected.is_system && <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] text-slate-300">system</span>}
          </div>
          {selected.description && <p className="mb-3 text-xs text-slate-400">{selected.description}</p>}
          {selected.tools_json && (
            <div className="mb-3">
              <p className="mb-1 text-[10px] font-semibold uppercase text-slate-500">Tools</p>
              <div className="flex flex-wrap gap-1">
                {selected.tools_json.map((t) => (
                  <span key={t} className="rounded bg-terminal-border px-1.5 py-0.5 font-mono text-[10px] text-slate-300">{t}</span>
                ))}
              </div>
            </div>
          )}
          <ViewPrompt slug={selected.slug} />
        </aside>
      )}
    </div>
  );
}

function ViewPrompt({ slug }: { slug: string }) {
  const { getToken } = useAuth();
  const [prompt, setPrompt] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const load = async () => {
    const token = (await getToken()) ?? undefined;
    const data = await fetchJson<{ system_prompt: string | null }>(`/registry/${slug}`, { system_prompt: null }, token);
    setPrompt(data.system_prompt ?? "No system prompt available.");
    setOpen(true);
  };

  return (
    <>
      {!open ? (
        <button onClick={load} className="text-xs text-terminal-accent hover:underline">View system prompt</button>
      ) : (
        <div>
          <button onClick={() => setOpen(false)} className="mb-1 text-xs text-slate-500 hover:text-white">Hide prompt</button>
          <pre className="max-h-60 overflow-y-auto whitespace-pre-wrap break-words rounded bg-black/40 p-2 text-[10px] text-slate-300">{prompt}</pre>
        </div>
      )}
    </>
  );
}
