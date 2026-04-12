"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import { deleteRequest, fetchJson, patchJson, postJson } from "../../lib/api";

type CronJob = {
  id: number;
  name: string;
  description: string | null;
  cron_expr: string;
  target_route: string;
  enabled: boolean;
  last_run: string | null;
  run_count: number;
  next_run: string | null;
};

const emptyForm = { name: "", description: "", cron_expr: "0 * * * *", target_route: "", enabled: true };

export default function SchedulerPage() {
  const { getToken } = useAuth();
  const [jobs, setJobs] = useState<CronJob[]>([]);
  const [form, setForm] = useState({ ...emptyForm });
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async () => {
    const token = (await getToken()) ?? undefined;
    const data = await fetchJson<CronJob[]>("/cron/jobs", [], token);
    setJobs(data);
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.name || !form.cron_expr || !form.target_route) {
      setStatus("Name, cron expression, and target route are required.");
      return;
    }
    setLoading(true);
    const token = (await getToken()) ?? undefined;
    const result = await postJson<CronJob, typeof form>("/cron/jobs", form, null as unknown as CronJob, token);
    if (result?.id) {
      setStatus(`Job "${result.name}" created.`);
      setForm({ ...emptyForm });
      await load();
    } else {
      setStatus("Failed to create job.");
    }
    setLoading(false);
  };

  const toggle = async (job: CronJob) => {
    const token = (await getToken()) ?? undefined;
    await patchJson(`/cron/jobs/${job.id}`, { enabled: !job.enabled }, null, token);
    await load();
  };

  const remove = async (id: number) => {
    const token = (await getToken()) ?? undefined;
    await deleteRequest(`/cron/jobs/${id}`, token);
    await load();
  };

  const trigger = async (id: number) => {
    const token = (await getToken()) ?? undefined;
    await postJson(`/cron/jobs/${id}/run`, {}, null, token);
    setStatus(`Job ${id} triggered manually.`);
    setTimeout(load, 2000);
  };

  return (
    <div className="flex flex-col gap-6 p-4">
      <h1 className="text-lg font-bold text-terminal-accent">Scheduler</h1>

      {/* Job list */}
      <section className="panel p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase text-slate-400">Scheduled Jobs</h2>
        {jobs.length === 0 ? (
          <p className="text-sm text-slate-500">No jobs scheduled yet.</p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-terminal-border text-slate-400">
                <th className="py-1 text-left">Name</th>
                <th className="py-1 text-left">Cron</th>
                <th className="py-1 text-left">Target</th>
                <th className="py-1 text-left">Runs</th>
                <th className="py-1 text-left">Next</th>
                <th className="py-1 text-left">Last</th>
                <th className="py-1 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} className="border-b border-terminal-border/40">
                  <td className="py-1 font-medium">
                    {job.name}
                    {!job.enabled && <span className="ml-1 text-slate-500">(disabled)</span>}
                  </td>
                  <td className="py-1 font-mono text-slate-300">{job.cron_expr}</td>
                  <td className="py-1 font-mono text-slate-300">{job.target_route}</td>
                  <td className="py-1 text-slate-400">{job.run_count}</td>
                  <td className="py-1 text-slate-400">{job.next_run ? new Date(job.next_run).toLocaleString() : "—"}</td>
                  <td className="py-1 text-slate-400">{job.last_run ? new Date(job.last_run).toLocaleString() : "—"}</td>
                  <td className="flex gap-1 py-1">
                    <button
                      onClick={() => toggle(job)}
                      className="rounded bg-terminal-border px-2 py-0.5 text-xs hover:bg-slate-600"
                    >
                      {job.enabled ? "Disable" : "Enable"}
                    </button>
                    <button
                      onClick={() => trigger(job.id)}
                      className="rounded bg-blue-900 px-2 py-0.5 text-xs hover:bg-blue-700"
                    >
                      Run
                    </button>
                    <button
                      onClick={() => remove(job.id)}
                      className="rounded bg-red-900 px-2 py-0.5 text-xs hover:bg-red-700"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Add job form */}
      <section className="panel p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase text-slate-400">Add Job</h2>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Name</label>
            <input
              className="rounded bg-terminal-border px-2 py-1 text-sm text-white"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Daily market scan"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Cron Expression (UTC)</label>
            <input
              className="rounded bg-terminal-border px-2 py-1 font-mono text-sm text-white"
              value={form.cron_expr}
              onChange={(e) => setForm({ ...form, cron_expr: e.target.value })}
              placeholder="0 9 * * 1-5"
            />
          </div>
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Target Route (internal API path)</label>
            <input
              className="rounded bg-terminal-border px-2 py-1 font-mono text-sm text-white"
              value={form.target_route}
              onChange={(e) => setForm({ ...form, target_route: e.target.value })}
              placeholder="/market/snapshot"
            />
          </div>
          <div className="flex flex-col gap-1 col-span-2">
            <label className="text-xs text-slate-400">Description (optional)</label>
            <input
              className="rounded bg-terminal-border px-2 py-1 text-sm text-white"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
        </div>
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={create}
            disabled={loading}
            className="rounded bg-terminal-accent px-4 py-1.5 text-sm font-semibold text-black disabled:opacity-50"
          >
            {loading ? "Creating…" : "Add Job"}
          </button>
          {status && <span className="text-xs text-slate-400">{status}</span>}
        </div>

        <p className="mt-3 text-xs text-slate-500">
          Cron syntax: <code className="font-mono">minute hour day month weekday</code> — e.g.{" "}
          <code className="font-mono">0 9 * * 1-5</code> = every weekday at 09:00 UTC.
        </p>
      </section>
    </div>
  );
}
