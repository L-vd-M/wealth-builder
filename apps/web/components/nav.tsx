import { SignedIn, SignedOut, SignInButton, UserButton } from "@clerk/nextjs";
import Link from "next/link";

const links = [
  ["/", "Home"],
  ["/world-map", "World Map"],
  ["/quant-analysis", "Quant"],
  ["/financial-analysis", "Financial"],
  ["/trading", "Trading"],
  ["/platforms", "Platforms"],
  ["/news", "News"],
  ["/bots-strategies", "Bots & Strategies"],
  ["/ai-agents", "AI Agents"],
  ["/agents", "Agent Catalogue"],
  ["/deliberations", "Deliberations"],
  ["/wallets", "Wallets"],
  ["/scheduler", "Scheduler"],
] as const;

export function Nav() {
  return (
    <aside className="panel flex flex-col p-3">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-terminal-accent">MarketCommand</h2>
      <nav className="flex flex-col gap-2 text-sm">
        {links.map(([href, label]) => (
          <Link key={href} className="rounded px-2 py-1 hover:bg-terminal-border" href={href as never}>
            {label}
          </Link>
        ))}
      </nav>
      <div className="mt-auto border-t border-terminal-border pt-3 text-sm">
        <SignedIn>
          <div className="flex items-center gap-2">
            <UserButton afterSignOutUrl="/" />
            <span className="text-xs text-slate-400">Account</span>
          </div>
        </SignedIn>
        <SignedOut>
          <SignInButton mode="modal">
            <button
              type="button"
              className="w-full rounded bg-terminal-accent px-3 py-1.5 text-xs font-semibold text-black"
            >
              Sign In
            </button>
          </SignInButton>
        </SignedOut>
      </div>
    </aside>
  );
}
