export default function HomePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">MarketCommand Terminal</h1>
      <p className="text-sm text-slate-300">
        Unified workspace for world context, quant research, execution, platform discovery, news intelligence, strategy engineering, and AI-assisted overlays.
      </p>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {[
          "World Map",
          "Quant Analysis",
          "Financial Analysis",
          "Trading Workspace",
          "Platforms Directory",
          "News Hub",
          "Bots & Strategies",
          "AI Agents Console"
        ].map((item) => (
          <article className="panel p-3" key={item}>
            <h2 className="text-sm font-semibold">{item}</h2>
            <p className="text-xs text-slate-400">Initial scaffold ready for implementation.</p>
          </article>
        ))}
      </div>
    </div>
  );
}
